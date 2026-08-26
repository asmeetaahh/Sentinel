from __future__ import annotations

from pydantic import BaseModel


class HealthResponse(BaseModel):
    status: str


class ModelMetadataResponse(BaseModel):
    artifact_id: str
    horizon_days: int
    decision_threshold: float
    calibration_method: str
    n_features: int
    seed: int
    dataset_fingerprint_sha256_16: dict[str, str]
    disclaimer: str
