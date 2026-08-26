from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel

from .common import Provenance


class ModelSection(BaseModel):
    artifact_id: str
    probability_calibrated: float
    probability_raw_rf: float
    decision_threshold: float
    risk_state: Literal["elevated", "normal"]
    provenance: Provenance
    disclaimer: str


class ExposureEstimate(BaseModel):
    value: float
    provenance: Provenance
    method: str
    note: str


class RetrospectiveActual(BaseModel):
    value: float | None
    available: bool
    provenance: Provenance
    note: str


class ExposureSection(BaseModel):
    estimate: ExposureEstimate
    retrospective_actual: RetrospectiveActual


class AvailableLiquidity(BaseModel):
    value: float
    provenance: Provenance
    note: str


class LiquidityStress(BaseModel):
    value: float | None
    provenance: Provenance
    note: str
    formula: str | None = None


class LiquiditySection(BaseModel):
    available_liquidity: AvailableLiquidity
    liquidity_stress: LiquidityStress


class RiskResponse(BaseModel):
    merchant_id: str
    as_of_date: date
    day_index: int
    horizon_days: int
    model: ModelSection
    exposure: ExposureSection
    liquidity: LiquiditySection
