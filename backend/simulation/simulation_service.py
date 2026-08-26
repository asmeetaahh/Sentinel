"""
What-if / counterfactual simulation: apply a small, bounded edit to one or
more of the merchant's OWN current feature values, run the exact same
saved model artifact used by /merchants/{id}/risk, and report how its
output — and the transparently-derived exposure/liquidity-stress view —
responds. See docs/architecture/simulator.md for the full design rationale
and its limitations.

Flow (mirrors PROJECT_CONTEXT's own framing):
    current feature vector (observed)
        -> bounded user intervention on 1-3 controls (backend/simulation/controls.py)
        -> modified feature vector (every other of the 55 features held fixed)
        -> the SAME artifact.calibrated_pipeline / artifact.base_random_forest
        -> new model output
        -> modeled exposure (illustrative scaling of the same trailing-average
           baseline used by /risk, tied to the model's own probability shift)
        -> liquidity stress (same formula as /risk)
        -> comparison against the current state

No new model is trained or loaded here. No transaction-level data is
fabricated. Nothing outside the requested controls is modified.
"""

from __future__ import annotations

from datetime import date

import numpy as np

from backend.api.state import AppState
from backend.risk import liquidity_service, risk_service
from backend.services.lookups import UnsupportedHorizonError, require_merchant, resolve_day_index
from backend.simulation.controls import CONTROLS, ControlOutOfRangeError, NoInterventionProvidedError, UnknownControlError, control_bounds

# Floors the denominator when scaling the exposure baseline by a probability
# ratio, so a current probability at or near zero cannot blow the ratio up
# to an arbitrarily large (and meaningless) number. Documented, fixed,
# never tuned per-request.
MIN_PROBABILITY_FLOOR = 1e-4

MODELED_IMPACT_DISCLAIMER = (
    "This is a MODELED IMPACT, not a guaranteed or causal outcome. It shows how the same "
    "synthetic-benchmark Random Forest model responds when one or more of the merchant's own "
    "trailing 28-day operational metrics are set to a different, bounded value, holding every "
    "other observed feature fixed. It is not a forecast of what would actually happen if this "
    "merchant changed its operations, and it does not establish that any control causes a "
    "change in real-world risk. See docs/architecture/simulator.md."
)

EXPOSURE_SIMULATED_METHOD = (
    "Illustrative scaling of the same observed trailing-28-day mean daily chargeback_amount "
    "baseline used by /merchants/{id}/risk, multiplied by the ratio of simulated-to-current "
    "MODELED probability (denominator floored at "
    f"{MIN_PROBABILITY_FLOOR} to avoid division blowups near zero). This is NOT a separate "
    "regression prediction — no exposure-regression model is saved (see "
    "docs/research/baseline_ml_report.md section I) — it is a transparent, deterministic "
    "reuse of the classifier's own probability shift. See docs/architecture/simulator.md."
)


def _feature_row(state: AppState, merchant_id: str, day_index: int) -> np.ndarray:
    row = state.features[(state.features["merchant_id"] == merchant_id) & (state.features["day_index"] == day_index)]
    if row.empty:
        raise ValueError(f"No feature row for merchant_id={merchant_id} day_index={day_index}.")
    return row.iloc[0][state.feature_columns].to_numpy(dtype=float)


def list_controls(state: AppState, merchant_id: str, as_of_date: date) -> dict:
    require_merchant(state.merchants, merchant_id)
    day_index = resolve_day_index(state.daily_observations, merchant_id, as_of_date)
    base_row = _feature_row(state, merchant_id, day_index)
    col_index = {name: i for i, name in enumerate(state.feature_columns)}

    controls_out = []
    for control in CONTROLS.values():
        min_value, max_value = control_bounds(state, control)
        controls_out.append(
            {
                "control_id": control.control_id,
                "label": control.label,
                "feature": control.feature,
                "group": control.group,
                "unit": control.unit,
                "description": control.description,
                "min_value": min_value,
                "max_value": max_value,
                "baseline_value": float(base_row[col_index[control.feature]]),
            }
        )

    return {
        "merchant_id": merchant_id,
        "as_of_date": as_of_date.isoformat(),
        "day_index": day_index,
        "controls": controls_out,
    }


def _validate_interventions(state: AppState, interventions: dict[str, float]) -> None:
    for control_id, value in interventions.items():
        if control_id not in CONTROLS:
            raise UnknownControlError(control_id, list(CONTROLS))
        control = CONTROLS[control_id]
        min_value, max_value = control_bounds(state, control)
        if not (min_value <= value <= max_value):
            raise ControlOutOfRangeError(control_id, value, min_value, max_value)


def _delta(current_value: float, simulated_value: float) -> dict:
    relative = None if current_value == 0 else (simulated_value - current_value) / current_value
    return {"absolute": simulated_value - current_value, "relative": relative}


def simulate(
    state: AppState,
    merchant_id: str,
    as_of_date: date,
    horizon_days: int,
    interventions: dict[str, float],
) -> dict:
    if horizon_days not in risk_service.SUPPORTED_HORIZONS:
        raise UnsupportedHorizonError(horizon_days, risk_service.SUPPORTED_HORIZONS)
    if not interventions:
        raise NoInterventionProvidedError()

    require_merchant(state.merchants, merchant_id)
    day_index = resolve_day_index(state.daily_observations, merchant_id, as_of_date)
    _validate_interventions(state, interventions)

    # Reuses risk_service.assess_risk verbatim for the "current" state — the
    # exact same code path /merchants/{id}/risk uses — rather than
    # re-deriving current model/exposure/liquidity numbers here.
    current = risk_service.assess_risk(state, merchant_id, as_of_date, horizon_days)

    base_row = _feature_row(state, merchant_id, day_index)
    col_index = {name: i for i, name in enumerate(state.feature_columns)}
    modified_row = base_row.copy()

    applied_controls = []
    for control_id, value in interventions.items():
        control = CONTROLS[control_id]
        idx = col_index[control.feature]
        baseline_value = float(base_row[idx])
        modified_row[idx] = float(value)
        min_value, max_value = control_bounds(state, control)
        applied_controls.append(
            {
                "control_id": control_id,
                "label": control.label,
                "feature": control.feature,
                "group": control.group,
                "min_value": min_value,
                "max_value": max_value,
                "baseline_value": baseline_value,
                "simulated_value": float(value),
            }
        )

    artifact = state.artifact
    X_simulated = modified_row.reshape(1, -1)

    current_calibrated = current["model"]["probability_calibrated"]
    current_raw = current["model"]["probability_raw_rf"]
    simulated_calibrated = float(artifact.calibrated_pipeline.predict_proba(X_simulated)[0, 1])
    simulated_raw = float(artifact.base_random_forest.predict_proba(X_simulated)[0, 1])
    simulated_risk_state = "elevated" if simulated_calibrated >= artifact.decision_threshold else "normal"

    exposure_current_value = current["exposure"]["estimate"]["value"]
    liquidity_value = current["liquidity"]["available_liquidity"]["value"]

    probability_floor = max(current_calibrated, MIN_PROBABILITY_FLOOR)
    risk_ratio = simulated_calibrated / probability_floor
    exposure_simulated_value = exposure_current_value * risk_ratio

    liquidity_stress_current = current["liquidity"]["liquidity_stress"]
    liquidity_stress_simulated = liquidity_service.liquidity_stress(exposure_simulated_value, liquidity_value)

    liquidity_stress_delta = None
    if liquidity_stress_current["value"] is not None and liquidity_stress_simulated["value"] is not None:
        liquidity_stress_delta = _delta(liquidity_stress_current["value"], liquidity_stress_simulated["value"])

    return {
        "merchant_id": merchant_id,
        "as_of_date": as_of_date.isoformat(),
        "day_index": day_index,
        "horizon_days": horizon_days,
        "controls": applied_controls,
        "current": {
            "probability_calibrated": current_calibrated,
            "probability_raw_rf": current_raw,
            "risk_state": current["model"]["risk_state"],
            "decision_threshold": artifact.decision_threshold,
            "provenance": "modeled",
        },
        "simulated": {
            "probability_calibrated": simulated_calibrated,
            "probability_raw_rf": simulated_raw,
            "risk_state": simulated_risk_state,
            "decision_threshold": artifact.decision_threshold,
            "provenance": "modeled",
        },
        "probability_delta": _delta(current_calibrated, simulated_calibrated),
        "exposure": {
            "current": {
                "value": exposure_current_value,
                "provenance": "derived",
                "method": current["exposure"]["estimate"]["method"],
            },
            "simulated": {
                "value": exposure_simulated_value,
                "provenance": "derived",
                "method": EXPOSURE_SIMULATED_METHOD,
            },
            "delta": _delta(exposure_current_value, exposure_simulated_value),
        },
        "liquidity_stress": {
            "current": liquidity_stress_current,
            "simulated": liquidity_stress_simulated,
            "delta": liquidity_stress_delta,
        },
        "modeled_impact_disclaimer": MODELED_IMPACT_DISCLAIMER,
    }
