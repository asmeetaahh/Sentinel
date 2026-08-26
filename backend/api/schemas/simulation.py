from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from .common import Provenance

# ---------------------------------------------------------------------------
# GET /merchants/{id}/simulation/controls
# ---------------------------------------------------------------------------


class ControlMeta(BaseModel):
    control_id: str
    label: str
    feature: str
    group: str
    unit: str
    description: str
    min_value: float
    max_value: float
    baseline_value: float


class ControlsListResponse(BaseModel):
    merchant_id: str
    as_of_date: date
    day_index: int
    controls: list[ControlMeta]


# ---------------------------------------------------------------------------
# POST /merchants/{id}/simulation
# ---------------------------------------------------------------------------


class SimulationRequest(BaseModel):
    """Exactly the three controls in backend/simulation/controls.py, each
    optional so a caller can vary just one at a time — but at least one
    must be set (see _at_least_one_control below). Deliberately NOT a
    generic dict[str, float]: a fixed, explicit shape is safer (Pydantic
    rejects unknown fields outright) and self-documents in /docs.
    """

    model_config = ConfigDict(extra="forbid")

    as_of_date: date
    horizon_days: int = 30
    refund_rate_28d: float | None = Field(default=None, allow_inf_nan=False)
    fulfillment_on_time_rate_28d: float | None = Field(default=None, allow_inf_nan=False)
    new_customer_rate_28d: float | None = Field(default=None, allow_inf_nan=False)

    @model_validator(mode="after")
    def _at_least_one_control(self) -> SimulationRequest:
        if self.refund_rate_28d is None and self.fulfillment_on_time_rate_28d is None and self.new_customer_rate_28d is None:
            raise ValueError(
                "At least one control must be set: refund_rate_28d, fulfillment_on_time_rate_28d, "
                "or new_customer_rate_28d."
            )
        return self

    def to_interventions(self) -> dict[str, float]:
        interventions: dict[str, float] = {}
        if self.refund_rate_28d is not None:
            interventions["refund_rate_28d"] = self.refund_rate_28d
        if self.fulfillment_on_time_rate_28d is not None:
            interventions["fulfillment_on_time_rate_28d"] = self.fulfillment_on_time_rate_28d
        if self.new_customer_rate_28d is not None:
            interventions["new_customer_rate_28d"] = self.new_customer_rate_28d
        return interventions


class AppliedControl(BaseModel):
    control_id: str
    label: str
    feature: str
    group: str
    min_value: float
    max_value: float
    baseline_value: float
    simulated_value: float


class SimulationModelOutcome(BaseModel):
    probability_calibrated: float
    probability_raw_rf: float
    risk_state: Literal["elevated", "normal"]
    decision_threshold: float
    provenance: Provenance


class Delta(BaseModel):
    absolute: float
    relative: float | None


class SimulationExposureValue(BaseModel):
    value: float
    provenance: Provenance
    method: str


class SimulationExposureSection(BaseModel):
    current: SimulationExposureValue
    simulated: SimulationExposureValue
    delta: Delta


class LiquidityStressValue(BaseModel):
    value: float | None
    provenance: Provenance
    note: str
    formula: str | None = None


class SimulationLiquidityStressSection(BaseModel):
    current: LiquidityStressValue
    simulated: LiquidityStressValue
    delta: Delta | None


class SimulationResponse(BaseModel):
    merchant_id: str
    as_of_date: date
    day_index: int
    horizon_days: int
    controls: list[AppliedControl]
    current: SimulationModelOutcome
    simulated: SimulationModelOutcome
    probability_delta: Delta
    exposure: SimulationExposureSection
    liquidity_stress: SimulationLiquidityStressSection
    modeled_impact_disclaimer: str
