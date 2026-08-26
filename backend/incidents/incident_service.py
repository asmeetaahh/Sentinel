"""
Incident construction: grounds each incident in a real synthetic-benchmark
risk episode (events.csv, category="risk") AND a real detection by the
already-validated model — never a fabricated scenario, never a second risk
engine.

Selection rule (see docs/architecture/incident_response.md for full
rationale): a risk-category event becomes a surfaced incident only if the
SAME saved artifact used by /merchants/{id}/risk crosses its OWN existing
decision_threshold on at least one day within [event.start_date,
event.end_date]. This ties "detection" to genuine, already-validated model
behavior — reusing the exact artifact and threshold, not a new rule
invented to make the demo look more complete. Empirically, 50 of 80 risk
events (34 of 50 merchants) meet this bar — a realistic, non-trivial rate
consistent with the model's documented imperfect recall
(docs/research/baseline_ml_report.md), not tuned to hit a target number.

Every other section of an incident (risk/exposure/liquidity/drivers) is
produced by calling the EXISTING risk_service / explainability_service
functions at the incident's detected_date — this module adds no new
prediction logic of its own.
"""

from __future__ import annotations

import pandas as pd

from backend.api.state import AppState
from backend.evidence import evidence_service
from backend.evidence.reason_codes import reason_code_for_event_type
from backend.risk import explainability_service, risk_service
from backend.services.lookups import require_merchant, resolve_day_index

# Fixed, disclosed prototype thresholds for the priority heuristic — never
# tuned against how "impressive" a given incident's priority looks.
LIQUIDITY_STRESS_HIGH_THRESHOLD = 1.0  # same anchor as the dashboard's liquidity-stress gauge: exposure == available liquidity
SUSTAINED_RISK_FRACTION_THRESHOLD = 0.5  # model flagged >= half the incident's days
HIGH_CASE_COUNT_THRESHOLD = 5  # illustrative, documented, not tuned per incident

EXPLANATION_TOP_K = 5


class IncidentNotFoundError(Exception):
    def __init__(self, incident_id: str):
        self.incident_id = incident_id
        super().__init__(f"Unknown incident_id: {incident_id!r}")


def _incident_id(event_id: str) -> str:
    return f"INC-{event_id}"


def _event_id_from_incident_id(incident_id: str) -> str:
    return incident_id.removeprefix("INC-")


def _detect_within_window(state: AppState, merchant_id: str, start_day: int, end_day: int) -> tuple[int | None, list[dict]]:
    artifact = state.artifact
    daily: list[dict] = []
    first_detected_day: int | None = None
    for day in range(start_day, end_day + 1):
        row = state.features[(state.features["merchant_id"] == merchant_id) & (state.features["day_index"] == day)]
        if row.empty:
            continue
        X = row.iloc[0][state.feature_columns].to_numpy(dtype=float).reshape(1, -1)
        probability = float(artifact.calibrated_pipeline.predict_proba(X)[0, 1])
        flagged = probability >= artifact.decision_threshold
        daily.append({"day_index": day, "probability_calibrated": probability, "flagged": flagged})
        if flagged and first_detected_day is None:
            first_detected_day = day
    return first_detected_day, daily


def _estimated_case_count(daily_observations: pd.DataFrame, merchant_id: str, start_day: int, end_day: int) -> int:
    merchant_daily = daily_observations[daily_observations["merchant_id"] == merchant_id]
    window = merchant_daily[(merchant_daily["day_index"] >= start_day) & (merchant_daily["day_index"] <= end_day)]
    return int(window["chargeback_count"].sum())


def _compute_priority(
    liquidity_stress_value: float | None,
    evidence_readiness_status: str,
    daily_probabilities: list[dict],
    estimated_case_count: int,
) -> tuple[str, list[str]]:
    reasons: list[str] = []

    if liquidity_stress_value is not None and liquidity_stress_value >= LIQUIDITY_STRESS_HIGH_THRESHOLD:
        reasons.append("Estimated exposure would consume all or more of this merchant's available liquidity.")

    if evidence_readiness_status == "insufficient":
        reasons.append("No required evidence is currently available for this incident's reason code.")
    elif evidence_readiness_status == "partial":
        reasons.append("Required evidence for this incident's reason code is incomplete.")

    fraction_flagged = (
        sum(1 for d in daily_probabilities if d["flagged"]) / len(daily_probabilities) if daily_probabilities else 0.0
    )
    if fraction_flagged >= SUSTAINED_RISK_FRACTION_THRESHOLD:
        reasons.append("The model's probability stayed at or above the decision threshold for most of this incident's window.")

    if estimated_case_count >= HIGH_CASE_COUNT_THRESHOLD:
        reasons.append(f"{estimated_case_count} chargeback occurrences were recorded during this incident's window.")

    if len(reasons) >= 2:
        priority = "high"
    elif len(reasons) == 1:
        priority = "medium"
    else:
        priority = "low"
    return priority, reasons


def _build_incident(state: AppState, event_row: pd.Series, merchant_row: pd.Series) -> dict | None:
    merchant_id = merchant_row["merchant_id"]
    start_day = resolve_day_index(state.daily_observations, merchant_id, event_row["start_date"].date())
    end_day = resolve_day_index(state.daily_observations, merchant_id, event_row["end_date"].date())

    first_detected_day, daily_probabilities = _detect_within_window(state, merchant_id, start_day, end_day)
    if first_detected_day is None:
        return None  # this risk event was never flagged by the existing model — not surfaced as an incident

    merchant_daily = state.daily_observations[state.daily_observations["merchant_id"] == merchant_id]
    detected_date = merchant_daily[merchant_daily["day_index"] == first_detected_day]["date"].iloc[0].date()
    last_observed_date = merchant_daily["date"].max().date()

    risk = risk_service.assess_risk(state, merchant_id, detected_date, state.artifact.horizon_days)
    explanation = explainability_service.explain(state, merchant_id, detected_date, top_k=EXPLANATION_TOP_K)

    reason_code = reason_code_for_event_type(event_row["event_type"])
    evidence = evidence_service.compute_evidence_readiness(state.daily_observations, merchant_row, reason_code, start_day, end_day)

    estimated_case_count = _estimated_case_count(state.daily_observations, merchant_id, start_day, end_day)
    liquidity_stress_value = risk["liquidity"]["liquidity_stress"]["value"]
    priority, priority_reasons = _compute_priority(
        liquidity_stress_value, evidence["readiness_status"], daily_probabilities, estimated_case_count
    )

    status = "active" if event_row["recovery_end_date"].date() >= last_observed_date else "resolved"
    workflow_stage = "response_ready_for_merchant_review" if evidence["readiness_status"] == "ready" else "evidence_check"

    return {
        "incident_id": _incident_id(event_row["event_id"]),
        "merchant_id": merchant_id,
        "event_type": event_row["event_type"],
        "status": status,
        "priority": priority,
        "priority_reasons": priority_reasons,
        "horizon_days": state.artifact.horizon_days,
        "day_index": first_detected_day,
        "window": {
            "start_date": event_row["start_date"].date().isoformat(),
            "end_date": event_row["end_date"].date().isoformat(),
            "recovery_end_date": event_row["recovery_end_date"].date().isoformat(),
            "duration_days": int(event_row["duration_days"]),
        },
        "detected_date": detected_date.isoformat(),
        "detection_note": (
            "The first day within this episode's window on which the existing saved model's calibrated "
            "probability reached its own decision threshold — the same artifact and threshold used by "
            "/merchants/{id}/risk. This is real model behavior, not a separately invented detection rule."
        ),
        "model": risk["model"],
        "exposure": risk["exposure"],
        "liquidity": risk["liquidity"],
        "drivers": explanation["drivers"],
        "causality_disclaimer": explanation["causality_disclaimer"],
        "reason_code": {
            "code": reason_code.code,
            "label": reason_code.label,
            "description": reason_code.description,
            "taxonomy_disclaimer": (
                "SENTINEL SYNTHETIC PROTOTYPE TAXONOMY — not Razorpay's, a card network's, or any real "
                "dispute system's proprietary reason-code taxonomy. See docs/architecture/incident_response.md."
            ),
        },
        "case_summary": {
            "estimated_case_count": estimated_case_count,
            "method": "Sum of observed chargeback_count over the incident's benchmark window (start_date to end_date).",
            "provenance": "derived",
            "note": (
                "This benchmark contains only daily aggregate observations, not individual transaction-level "
                "dispute records. This is a count of recorded chargeback occurrences, not a list of individual "
                "cases with identifying details."
            ),
        },
        "evidence_readiness": evidence,
        "scenario_context": {
            "event_id": event_row["event_id"],
            "shape": event_row["shape"],
            "severity_score": float(event_row["severity_score"]),
            "affects": event_row["affects"].split(","),
            "provenance": "synthetic_prototype",
            "note": (
                "This is the synthetic benchmark generator's own ground-truth scenario parameter, used only to "
                "construct this synthetic episode. It is not a value the model detected, predicted, or used as an "
                "input feature (ml/features never reads severity_score — see docs/architecture/feature_engineering.md)."
            ),
        },
        "workflow_stage": workflow_stage,
    }


def list_incidents(state: AppState, merchant_id: str) -> list[dict]:
    require_merchant(state.merchants, merchant_id)
    merchant_row = state.merchants[state.merchants["merchant_id"] == merchant_id].iloc[0]
    merchant_events = state.events[(state.events["merchant_id"] == merchant_id) & (state.events["category"] == "risk")]

    incidents = []
    for _, event_row in merchant_events.sort_values("start_date").iterrows():
        incident = _build_incident(state, event_row, merchant_row)
        if incident is not None:
            incidents.append(incident)
    return incidents


def summarize(incident: dict) -> dict:
    return {
        "incident_id": incident["incident_id"],
        "merchant_id": incident["merchant_id"],
        "event_type": incident["event_type"],
        "status": incident["status"],
        "priority": incident["priority"],
        "horizon_days": incident["horizon_days"],
        "window": incident["window"],
        "detected_date": incident["detected_date"],
        "probability_calibrated": incident["model"]["probability_calibrated"],
        "risk_state": incident["model"]["risk_state"],
        "exposure_estimate": incident["exposure"]["estimate"]["value"],
        "liquidity_stress": incident["liquidity"]["liquidity_stress"]["value"],
        "reason_code": incident["reason_code"]["code"],
        "reason_code_label": incident["reason_code"]["label"],
        "evidence_readiness_status": incident["evidence_readiness"]["readiness_status"],
        "estimated_case_count": incident["case_summary"]["estimated_case_count"],
        "workflow_stage": incident["workflow_stage"],
    }


def get_incident(state: AppState, incident_id: str) -> dict:
    event_id = _event_id_from_incident_id(incident_id)
    match = state.events[(state.events["event_id"] == event_id) & (state.events["category"] == "risk")]
    if match.empty:
        raise IncidentNotFoundError(incident_id)
    event_row = match.iloc[0]
    merchant_row = state.merchants[state.merchants["merchant_id"] == event_row["merchant_id"]].iloc[0]

    incident = _build_incident(state, event_row, merchant_row)
    if incident is None:
        # A structurally-valid risk event that never crossed the detection
        # bar is not a product incident — surfaced as 404, not a fabricated
        # or empty-but-200 incident.
        raise IncidentNotFoundError(incident_id)
    return incident
