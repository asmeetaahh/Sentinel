from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel


class Driver(BaseModel):
    feature: str
    group: str
    definition: str
    window: str | None
    kind: str
    value: float
    shap_value: float
    direction: Literal["increases_risk", "decreases_risk", "neutral"]


class PredictionInfo(BaseModel):
    model_probability_calibrated: float
    model_probability_raw_rf: float
    decision_threshold: float
    predicted_positive: bool
    note: str


class FaithfulnessInfo(BaseModel):
    shap_base_value: float
    shap_reconstructed_probability: float
    reconstruction_error: float
    faithful: bool


class DriversSection(BaseModel):
    top_positive_contributors: list[Driver]
    top_negative_contributors: list[Driver]


class ExplanationResponse(BaseModel):
    merchant_id: str
    as_of_date: date
    day_index: int
    horizon_days: int
    prediction: PredictionInfo
    faithfulness: FaithfulnessInfo
    drivers: DriversSection
    all_contributors: list[Driver]
    causality_disclaimer: str
