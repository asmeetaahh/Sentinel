"""
Risk assessment for a merchant/prediction date: the verified classification
model's output, plus the transparently-derived exposure/liquidity view.

Reuses the existing loaded artifact (backend/api/state.py) and feature
matrix exactly as built by ml.modeling.datasets / ml.features — no
retraining, no re-derivation of feature values, no duplicate feature
engineering logic here.
"""

from __future__ import annotations

from datetime import date

import numpy as np

from backend.api.state import AppState
from backend.risk import confidence_service, liquidity_service
from backend.services.lookups import UnsupportedHorizonError, require_merchant, resolve_day_index

SUPPORTED_HORIZONS = [30]

MODEL_PROBABILITY_DISCLAIMER = (
    "This is a synthetic-benchmark model output, not a validated real-world probability. "
    "It has not been calibrated against, or validated on, real merchant/transaction data. "
    "See docs/research/baseline_ml_report.md and docs/architecture/explainability.md."
)


def _feature_row(state: AppState, merchant_id: str, day_index: int) -> np.ndarray:
    row = state.features[(state.features["merchant_id"] == merchant_id) & (state.features["day_index"] == day_index)]
    if row.empty:
        raise ValueError(f"No feature row for merchant_id={merchant_id} day_index={day_index}.")
    return row.iloc[0][state.feature_columns].to_numpy(dtype=float)


def assess_risk(state: AppState, merchant_id: str, as_of_date: date, horizon_days: int = 30) -> dict:
    if horizon_days not in SUPPORTED_HORIZONS:
        raise UnsupportedHorizonError(horizon_days, SUPPORTED_HORIZONS)

    require_merchant(state.merchants, merchant_id)
    day_index = resolve_day_index(state.daily_observations, merchant_id, as_of_date)

    X_row = _feature_row(state, merchant_id, day_index).reshape(1, -1)
    artifact = state.artifact

    calibrated_probability = float(artifact.calibrated_pipeline.predict_proba(X_row)[0, 1])
    raw_rf_probability = float(artifact.base_random_forest.predict_proba(X_row)[0, 1])
    predicted_elevated = calibrated_probability >= artifact.decision_threshold

    exposure_estimate = liquidity_service.naive_exposure_estimate(state, merchant_id, day_index, horizon_days)
    retrospective = liquidity_service.retrospective_actual_exposure(state, merchant_id, as_of_date, horizon_days)
    liquidity = liquidity_service.available_liquidity(state, merchant_id, day_index)
    stress = liquidity_service.liquidity_stress(exposure_estimate["value"], liquidity["value"])

    data_quality = confidence_service.assess_confidence(state, merchant_id, day_index)

    return {
        "merchant_id": merchant_id,
        "as_of_date": as_of_date.isoformat(),
        "day_index": day_index,
        "horizon_days": horizon_days,
        "model": {
            "artifact_id": "random_forest_calibrated_30d",
            "probability_calibrated": calibrated_probability,
            "probability_raw_rf": raw_rf_probability,
            "decision_threshold": artifact.decision_threshold,
            "risk_state": "elevated" if predicted_elevated else "normal",
            "provenance": "modeled",
            "disclaimer": MODEL_PROBABILITY_DISCLAIMER,
        },
        "exposure": {
            "estimate": exposure_estimate,
            "retrospective_actual": retrospective,
        },
        "liquidity": {
            "available_liquidity": liquidity,
            "liquidity_stress": stress,
        },
        "data_quality": data_quality,
    }
