from __future__ import annotations

from datetime import date, datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict

from .common import Provenance
from .simulation import ControlMeta, SimulationRequest

Priority = Literal["high", "medium"]
ActionStatus = Literal["reviewed", "simulated", "acknowledged", "dismissed"]
OutcomeStatus = Literal["not_observed"]

# ---------------------------------------------------------------------------
# GET /merchants/{id}/interventions
# ---------------------------------------------------------------------------


class ValueWithProvenance(BaseModel):
    value: float
    provenance: Provenance


class DeviationInfo(BaseModel):
    value: float
    provenance: Provenance
    method: str


class ShapCorroboration(BaseModel):
    corroborated: bool
    provenance: Provenance
    note: str


class InterventionRecommendation(BaseModel):
    intervention_id: str
    merchant_id: str
    as_of_date: date
    control_id: str
    title: str
    reason: str
    priority: Priority
    priority_rank: int
    current_value: ValueWithProvenance
    deviation_z: DeviationInfo
    shap_corroboration: ShapCorroboration
    simulator_control: ControlMeta
    modeled_impact_reminder: str


class InterventionRecommendationsResponse(BaseModel):
    merchant_id: str
    as_of_date: date
    relevance_threshold_z: float
    count: int
    recommendations: list[InterventionRecommendation]
    empty_state_note: str | None


# ---------------------------------------------------------------------------
# Merchant Risk Memory
# ---------------------------------------------------------------------------


class SimulatedImpactSummary(BaseModel):
    current_probability: float
    simulated_probability: float
    probability_delta_absolute: float
    exposure_current: float
    exposure_simulated: float
    liquidity_stress_current: float | None
    liquidity_stress_simulated: float | None
    disclaimer: str
    provenance: Provenance = "modeled"


class InterventionMemoryRecord(BaseModel):
    intervention_id: str
    merchant_id: str
    control_id: str
    recommendation_title: str
    action_status: ActionStatus
    timestamp: datetime
    simulated_impact: SimulatedImpactSummary | None
    outcome_status: OutcomeStatus
    outcome_note: str


class InterventionMemoryListResponse(BaseModel):
    merchant_id: str
    count: int
    records: list[InterventionMemoryRecord]
    empty_state_note: str | None


class RecordInterventionRequest(BaseModel):
    """`intervention_id` must be one this backend itself could have produced
    (backend/interventions/recommendation_service.py's
    f"{merchant_id}:{control_id}:{as_of_date}" format) — never an arbitrary
    client string. `recommendation_title` is deliberately NOT accepted here;
    it is always looked up server-side from the control's own rule
    (backend/interventions/rules.py), so a client can never inject
    fabricated recommendation text into memory. `simulation` is required
    (and re-run through the real simulator, never trusted as a client-
    supplied number) when action_status == "simulated".
    """

    model_config = ConfigDict(extra="forbid")

    intervention_id: str
    action_status: ActionStatus
    simulation: SimulationRequest | None = None
