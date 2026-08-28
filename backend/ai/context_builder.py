"""
Assembles the ONE authoritative SentinelAIContext (backend/api/schemas/ai.py)
from existing, unmodified services — backend/risk/, backend/simulation/,
backend/incidents/. This module computes nothing itself: every numeric
value here is a pass-through of an already-verified service call, with
provenance preserved. See docs/architecture/ai_orchestrator.md.
"""

from __future__ import annotations

from datetime import date

from backend.api.schemas.ai import (
    DataQualityAIContext,
    ExposureAIContext,
    IncidentAIContext,
    InterventionRecommendationAIContext,
    LiquidityAIContext,
    MerchantAIContext,
    ObservedStateContext,
    RiskAIContext,
    SentinelAIContext,
    SimulationAIContext,
)
from backend.api.schemas.explainability import Driver
from backend.api.schemas.simulation import SimulationRequest
from backend.api.state import AppState
from backend.incidents.incident_service import IncidentNotFoundError, get_incident
from backend.interventions import recommendation_service
from backend.risk import explainability_service, risk_service
from backend.services.lookups import require_merchant, resolve_day_index
from backend.simulation import simulation_service

STANDING_LIMITATIONS_BASE = [
    "Sentinel is an independent merchant-facing AI Risk Manager prototype. Its risk intelligence is "
    "built and evaluated on a synthetic benchmark, and it has no access to real Razorpay systems, "
    "proprietary data, settlement decisions, or enforcement decisions.",
]

STANDING_LIMITATIONS_RISK = [
    "The modeled probability is a synthetic-benchmark model output, not a validated real-world probability.",
    "The provisional candidate is a Random Forest at a 30-day horizon: 30 days showed the strongest "
    "discrimination among the evaluated horizons (7/14/30), but temporal stress testing showed degraded "
    "performance over time, sigmoid calibration did not clearly improve the candidate, and a separate "
    "exposure-regression model did not outperform a simple trailing-average baseline and is not used as a "
    "product prediction — see docs/research/baseline_ml_report.md.",
]

STANDING_LIMITATIONS_CONFIDENCE = [
    "The confidence/data-quality level is a deterministic prototype heuristic based on observed history length "
    "and feature completeness — not a statistical confidence interval, not a model-calibrated probability, and "
    "not independently validated. Sentinel does not report a numeric or percentage confidence score.",
]

STANDING_LIMITATIONS_INTERVENTIONS = [
    "Intervention recommendations are produced by a deterministic, rule-based decision layer — not an ML "
    "model and not an LLM-generated suggestion. They identify which bounded simulator control deviates from "
    "this merchant's own recent baseline; they do not claim that acting on one guarantees a change in "
    "real-world risk, and testing one's modeled impact requires the simulator.",
]

STANDING_LIMITATIONS_SIMULATION = [
    "Simulator output is a MODELED IMPACT under a bounded, single/few-feature what-if edit — not a causal or "
    "guaranteed outcome, and not a forecast of what would actually happen to this merchant's real operations.",
]

STANDING_LIMITATIONS_INCIDENT = [
    "Evidence readiness reflects observed benchmark signals or explicitly documented prototype assumptions — "
    "never a real document, tracking number, invoice, or message.",
    "Sentinel does not submit disputes and has no access to Razorpay's actual dispute infrastructure. Any "
    "drafted material is a draft only and requires explicit merchant review and confirmation.",
]


def _merchant_context(merchant_row) -> MerchantAIContext:
    return MerchantAIContext(
        merchant_id=merchant_row["merchant_id"],
        archetype=merchant_row["archetype"],
        business_tier=merchant_row["business_tier"],
        signup_date=merchant_row["signup_date"].date(),
    )


def _observed_state_context(state: AppState, merchant_id: str, as_of_date: date) -> ObservedStateContext:
    merchant_daily = state.daily_observations[state.daily_observations["merchant_id"] == merchant_id]
    row = merchant_daily[merchant_daily["date"].dt.date == as_of_date].iloc[0]
    return ObservedStateContext(
        as_of_date=as_of_date,
        gmv=float(row["gmv"]),
        transaction_count=int(row["transaction_count"]),
        chargeback_rate=float(row["chargeback_rate"]),
        refund_rate=float(row["refund_rate"]),
        fulfillment_on_time_rate=float(row["fulfillment_on_time_rate"]),
    )


def _simulation_context(state: AppState, merchant_id: str, simulation_request: SimulationRequest) -> SimulationAIContext:
    result = simulation_service.simulate(
        state,
        merchant_id,
        simulation_request.as_of_date,
        simulation_request.horizon_days,
        simulation_request.to_interventions(),
    )
    return SimulationAIContext(
        controls_changed={c["control_id"]: c["simulated_value"] for c in result["controls"]},
        current_probability=result["current"]["probability_calibrated"],
        simulated_probability=result["simulated"]["probability_calibrated"],
        probability_delta_absolute=result["probability_delta"]["absolute"],
        exposure_current=result["exposure"]["current"]["value"],
        exposure_simulated=result["exposure"]["simulated"]["value"],
        liquidity_stress_current=result["liquidity_stress"]["current"]["value"],
        liquidity_stress_simulated=result["liquidity_stress"]["simulated"]["value"],
        disclaimer=result["modeled_impact_disclaimer"],
    )


def _incident_context(state: AppState, merchant_id: str, incident_id: str) -> IncidentAIContext:
    incident = get_incident(state, incident_id)
    if incident["merchant_id"] != merchant_id:
        # Never leak another merchant's incident into this context — treat
        # a cross-merchant id exactly like an unknown one.
        raise IncidentNotFoundError(incident_id)
    return IncidentAIContext(
        incident_id=incident["incident_id"],
        event_type=incident["event_type"],
        status=incident["status"],
        priority=incident["priority"],
        priority_reasons=incident["priority_reasons"],
        reason_code=incident["reason_code"]["code"],
        reason_code_label=incident["reason_code"]["label"],
        reason_code_taxonomy_disclaimer=incident["reason_code"]["taxonomy_disclaimer"],
        evidence_readiness_status=incident["evidence_readiness"]["readiness_status"],
        missing_evidence=incident["evidence_readiness"]["missing_evidence"],
        estimated_case_count=incident["case_summary"]["estimated_case_count"],
    )


def build_context(
    state: AppState,
    merchant_id: str,
    as_of_date: date | None = None,
    incident_id: str | None = None,
    simulation_request: SimulationRequest | None = None,
) -> SentinelAIContext:
    merchant_row = require_merchant(state.merchants, merchant_id)

    if as_of_date is None:
        merchant_daily = state.daily_observations[state.daily_observations["merchant_id"] == merchant_id]
        as_of_date = merchant_daily["date"].max().date()
    else:
        resolve_day_index(state.daily_observations, merchant_id, as_of_date)  # raises DateNotAvailableError if invalid

    risk_result = risk_service.assess_risk(state, merchant_id, as_of_date, state.artifact.horizon_days)
    explanation = explainability_service.explain(state, merchant_id, as_of_date, top_k=5)
    drivers = [
        Driver(**d) for d in [*explanation["drivers"]["top_positive_contributors"], *explanation["drivers"]["top_negative_contributors"]]
    ]

    limitations = list(STANDING_LIMITATIONS_BASE) + list(STANDING_LIMITATIONS_RISK) + list(STANDING_LIMITATIONS_CONFIDENCE)

    intervention_result = recommendation_service.get_recommendations(state, merchant_id, as_of_date)
    interventions = [
        InterventionRecommendationAIContext(
            intervention_id=rec["intervention_id"],
            control_id=rec["control_id"],
            title=rec["title"],
            reason=rec["reason"],
            priority=rec["priority"],
        )
        for rec in intervention_result["recommendations"]
    ]
    if interventions:
        limitations += STANDING_LIMITATIONS_INTERVENTIONS

    simulation_context = None
    if simulation_request is not None:
        simulation_context = _simulation_context(state, merchant_id, simulation_request)
        limitations += STANDING_LIMITATIONS_SIMULATION

    incident_context = None
    if incident_id is not None:
        incident_context = _incident_context(state, merchant_id, incident_id)
        limitations += STANDING_LIMITATIONS_INCIDENT

    return SentinelAIContext(
        merchant=_merchant_context(merchant_row),
        observed_state=_observed_state_context(state, merchant_id, as_of_date),
        risk=RiskAIContext(
            as_of_date=as_of_date,
            horizon_days=risk_result["horizon_days"],
            probability_calibrated=risk_result["model"]["probability_calibrated"],
            risk_state=risk_result["model"]["risk_state"],
            decision_threshold=risk_result["model"]["decision_threshold"],
            disclaimer=risk_result["model"]["disclaimer"],
        ),
        exposure=ExposureAIContext(
            value=risk_result["exposure"]["estimate"]["value"],
            method=risk_result["exposure"]["estimate"]["method"],
        ),
        liquidity=LiquidityAIContext(
            available_liquidity=risk_result["liquidity"]["available_liquidity"]["value"],
            liquidity_stress=risk_result["liquidity"]["liquidity_stress"]["value"],
            note=risk_result["liquidity"]["liquidity_stress"]["note"],
        ),
        data_quality=DataQualityAIContext(
            confidence_level=risk_result["data_quality"]["confidence_level"],
            history_days=risk_result["data_quality"]["history_days"],
            feature_coverage_status=risk_result["data_quality"]["feature_coverage_status"],
            reasons=risk_result["data_quality"]["reasons"],
            limitations=risk_result["data_quality"]["limitations"],
            basis=risk_result["data_quality"]["basis"],
        ),
        drivers=drivers,
        interventions=interventions,
        simulation=simulation_context,
        incident=incident_context,
        standing_limitations=limitations,
    )
