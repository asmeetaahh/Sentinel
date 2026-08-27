"""
The AI Orchestrator's schemas — request, the ONE authoritative verified
context contract, and the structured response. See
docs/architecture/ai_orchestrator.md.

CRITICAL: every numeric field here is populated by an existing, unmodified
backend service (backend/risk/*, backend/simulation/*, backend/incidents/*)
— never computed by this module, and never by the LLM. The LLM only ever
sees this object serialized as read-only context; it never produces any
field on this page except AssistantResponse.answer and
AssistantResponse.suggested_next_actions (backend/ai/response_parser.py).
"""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from .common import Provenance
from .explainability import Driver
from .risk import ConfidenceLevel, FeatureCoverageStatus
from .simulation import SimulationRequest

# ---------------------------------------------------------------------------
# Verified context — assembled by backend/ai/context_builder.py from
# existing services only.
# ---------------------------------------------------------------------------


class MerchantAIContext(BaseModel):
    merchant_id: str
    archetype: str
    business_tier: str
    signup_date: date
    provenance: Provenance = "observed"


class ObservedStateContext(BaseModel):
    as_of_date: date
    gmv: float
    transaction_count: int
    chargeback_rate: float
    refund_rate: float
    fulfillment_on_time_rate: float
    provenance: Provenance = "observed"


class RiskAIContext(BaseModel):
    as_of_date: date
    horizon_days: int
    probability_calibrated: float
    risk_state: Literal["elevated", "normal"]
    decision_threshold: float
    disclaimer: str
    provenance: Provenance = "modeled"


class ExposureAIContext(BaseModel):
    value: float
    method: str
    provenance: Provenance = "derived"


class LiquidityAIContext(BaseModel):
    available_liquidity: float
    liquidity_stress: float | None
    note: str
    provenance: Provenance = "derived"


class DataQualityAIContext(BaseModel):
    """Mirrors backend/risk/confidence_service.py's output exactly — the
    LLM may explain confidence_level using these already-provided reasons/
    limitations, but must never invent a numeric/percentage confidence
    score (none exists) and must never upgrade or downgrade the level
    itself. See docs/architecture/confidence_data_quality.md.
    """

    confidence_level: ConfidenceLevel
    history_days: int
    feature_coverage_status: FeatureCoverageStatus
    reasons: list[str]
    limitations: list[str]
    basis: str
    provenance: Provenance = "derived"


class SimulationAIContext(BaseModel):
    controls_changed: dict[str, float]
    current_probability: float
    simulated_probability: float
    probability_delta_absolute: float
    exposure_current: float
    exposure_simulated: float
    liquidity_stress_current: float | None
    liquidity_stress_simulated: float | None
    disclaimer: str
    provenance: Provenance = "modeled"


class IncidentAIContext(BaseModel):
    incident_id: str
    event_type: str
    status: Literal["active", "resolved"]
    priority: Literal["high", "medium", "low"]
    priority_reasons: list[str]
    reason_code: str
    reason_code_label: str
    reason_code_taxonomy_disclaimer: str
    evidence_readiness_status: Literal["ready", "partial", "insufficient"]
    missing_evidence: list[str]
    estimated_case_count: int
    provenance: Provenance = "derived"


class InterventionRecommendationAIContext(BaseModel):
    """One entry per candidate from backend/interventions/recommendation_service.py
    — never computed here. The LLM may summarize `reason` verbatim; the
    system prompt (backend/ai/prompt.py) forbids inventing a different one
    or a different control. See docs/architecture/intervention_intelligence.md.
    """

    intervention_id: str
    control_id: str
    title: str
    reason: str
    priority: Literal["high", "medium"]
    provenance: Provenance = "derived"


class SentinelAIContext(BaseModel):
    """The one authoritative structure passed to the LLM and echoed back to
    the frontend as `AssistantResponse.cited_context`. Sub-sections are
    optional/None when not requested or not available — the LLM is
    instructed to say so rather than guess (backend/ai/prompt.py).
    """

    merchant: MerchantAIContext
    observed_state: ObservedStateContext | None = None
    risk: RiskAIContext | None = None
    exposure: ExposureAIContext | None = None
    liquidity: LiquidityAIContext | None = None
    data_quality: DataQualityAIContext | None = None
    drivers: list[Driver] = Field(default_factory=list)
    interventions: list[InterventionRecommendationAIContext] = Field(default_factory=list)
    simulation: SimulationAIContext | None = None
    incident: IncidentAIContext | None = None
    standing_limitations: list[str]


# ---------------------------------------------------------------------------
# Request / response
# ---------------------------------------------------------------------------


class AssistantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=2000)
    as_of_date: date | None = None
    incident_id: str | None = None
    # Reuses the EXISTING simulator request schema exactly — the assistant
    # never accepts a client-computed simulation result, only the same
    # bounded controls /simulation itself accepts, and recomputes the
    # outcome via the real simulation_service.simulate() (see
    # backend/ai/context_builder.py). This is a deliberate trust boundary:
    # numbers in context are always freshly authoritative, never relayed
    # from a value the caller merely asserts.
    simulation: SimulationRequest | None = None


class AssistantResponse(BaseModel):
    merchant_id: str
    answer: str
    cited_context: SentinelAIContext
    provenance: dict[str, Provenance]
    limitations: list[str]
    disclaimer: str
    suggested_next_actions: list[str]
    provider: str
    guardrail_triggered: bool = False
