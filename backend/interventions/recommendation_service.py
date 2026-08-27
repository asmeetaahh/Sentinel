"""
Deterministic intervention recommendations: which of the three existing
bounded simulator controls are meaningful for THIS merchant to consider
right now, why, and in what order. See
docs/architecture/intervention_intelligence.md for the full design.

This module computes nothing that isn't already produced by an existing,
unmodified service:
    - control bounds/baseline: backend/simulation/simulation_service.list_controls
      (backend/simulation/controls.py's own CONTROLS registry — never
      redeclared here)
    - deviation-from-baseline z-scores: ml/features' own existing
      "deviation from merchant-specific baseline" feature group, read
      directly off the already-built features table
    - SHAP corroboration: backend/risk/explainability_service.explain's
      existing all_contributors list

No new model, no new statistic, no re-derivation of anything the feature
pipeline or SHAP already computed.
"""

from __future__ import annotations

from datetime import date

from backend.api.state import AppState
from backend.interventions.rules import RULES, RELEVANCE_Z_THRESHOLD, InterventionRule, is_relevant, signed_badness
from backend.risk import explainability_service
from backend.services.lookups import require_merchant, resolve_day_index
from backend.simulation import simulation_service
from backend.simulation.controls import CONTROLS

MODELED_IMPACT_REMINDER = (
    "This is an observed deviation from the merchant's own recent baseline, computed by the existing feature "
    "pipeline — not a claim that changing it will reduce real-world risk, and not a causal or guaranteed "
    "outcome. Test the modeled impact of adjusting this control in the simulator."
)

EMPTY_STATE_NOTE = (
    "No intervention is currently justified: none of the three bounded simulator controls show a material "
    "deviation from this merchant's own recent baseline as of this date."
)


def ranking_sort_key(candidate: dict) -> tuple:
    """Isolated from the loop that builds candidates so the ranking rule —
    high priority before medium, then larger deviation magnitude first,
    then a fixed control_id tiebreak — can be tested directly against
    synthetic inputs, independent of any real merchant's data.
    """
    return (candidate["priority"] != "high", -candidate["_sort_badness"], candidate["control_id"])


def _build_reason(rule: InterventionRule, current_value: float, deviation_z: float, shap_corroborated: bool) -> str:
    direction_word = "above" if rule.direction == "high_is_bad" else "below"
    sentence = (
        f"{rule.metric_label} is currently {current_value:.1%}, which is {abs(deviation_z):.1f} standard "
        f"deviations {direction_word} this merchant's own recent historical baseline."
    )
    if shap_corroborated:
        sentence += (
            " This behavior group is also among the model's currently verified SHAP contributors pushing "
            "risk higher for this merchant."
        )
    return sentence


def get_recommendations(state: AppState, merchant_id: str, as_of_date: date | None = None) -> dict:
    require_merchant(state.merchants, merchant_id)

    if as_of_date is None:
        merchant_daily = state.daily_observations[state.daily_observations["merchant_id"] == merchant_id]
        as_of_date = merchant_daily["date"].max().date()
    day_index = resolve_day_index(state.daily_observations, merchant_id, as_of_date)

    feature_rows = state.features[(state.features["merchant_id"] == merchant_id) & (state.features["day_index"] == day_index)]
    if feature_rows.empty:
        raise ValueError(f"No feature row for merchant_id={merchant_id} day_index={day_index}.")
    feature_row = feature_rows.iloc[0]

    controls_listing = simulation_service.list_controls(state, merchant_id, as_of_date)
    controls_by_id = {c["control_id"]: c for c in controls_listing["controls"]}

    explanation = explainability_service.explain(state, merchant_id, as_of_date, top_k=5)
    risk_elevating_groups = {driver["group"] for driver in explanation["all_contributors"] if driver["direction"] == "increases_risk"}

    candidates = []
    for control_id, rule in RULES.items():
        deviation_z = float(feature_row[rule.deviation_feature])
        if not is_relevant(rule, deviation_z):
            continue

        control_meta = controls_by_id[control_id]
        shap_corroborated = CONTROLS[control_id].group in risk_elevating_groups
        candidates.append(
            {
                "intervention_id": f"{merchant_id}:{control_id}:{as_of_date.isoformat()}",
                "merchant_id": merchant_id,
                "as_of_date": as_of_date.isoformat(),
                "control_id": control_id,
                "title": rule.title,
                "reason": _build_reason(rule, control_meta["baseline_value"], deviation_z, shap_corroborated),
                "priority": "high" if shap_corroborated else "medium",
                "_sort_badness": signed_badness(rule, deviation_z),
                "current_value": {"value": control_meta["baseline_value"], "provenance": "observed"},
                "deviation_z": {
                    "value": deviation_z,
                    "provenance": "derived",
                    "method": (
                        f"{rule.deviation_feature} — the existing causal feature-engineering deviation-from-"
                        "baseline z-score (this merchant's own expanding-history mean/std, clipped to "
                        "[-10, 10]). See docs/architecture/feature_engineering.md."
                    ),
                },
                "shap_corroboration": {
                    "corroborated": shap_corroborated,
                    "provenance": "modeled",
                    "note": (
                        "Whether any feature in this control's behavior group currently appears among this "
                        "merchant's verified SHAP contributors pushing risk higher (used only to set "
                        "priority, not relevance)."
                    ),
                },
                "simulator_control": control_meta,
                "modeled_impact_reminder": MODELED_IMPACT_REMINDER,
            }
        )

    # Rank: high priority before medium; within a tier, larger deviation
    # first; final deterministic tiebreak by control_id (fixed alphabetic
    # order — ties are only possible with a coincidental exact float
    # match, but the tiebreak makes ordering fully deterministic either way).
    candidates.sort(key=ranking_sort_key)
    for rank, candidate in enumerate(candidates, start=1):
        candidate["priority_rank"] = rank
        del candidate["_sort_badness"]

    return {
        "merchant_id": merchant_id,
        "as_of_date": as_of_date.isoformat(),
        "relevance_threshold_z": RELEVANCE_Z_THRESHOLD,
        "count": len(candidates),
        "recommendations": candidates,
        "empty_state_note": None if candidates else EMPTY_STATE_NOTE,
    }
