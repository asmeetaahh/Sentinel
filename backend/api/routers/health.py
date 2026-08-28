from __future__ import annotations

from fastapi import APIRouter, Depends

from backend.api.dependencies import get_state
from backend.api.schemas.metadata import HealthResponse, ModelMetadataResponse
from backend.api.state import AppState

router = APIRouter(tags=["health"])

DISCLAIMER = (
    "Sentinel's risk intelligence is built and evaluated on a synthetic benchmark. Model outputs are not "
    "validated against, or calibrated to, real-world merchant or transaction data, and Sentinel has no "
    "access to real Razorpay systems or data."
)


@router.get("/health", response_model=HealthResponse)
def health() -> HealthResponse:
    return HealthResponse(status="ok")


@router.get("/metadata", response_model=ModelMetadataResponse)
def metadata(state: AppState = Depends(get_state)) -> ModelMetadataResponse:
    config = state.artifact.config
    return ModelMetadataResponse(
        artifact_id="random_forest_calibrated_30d",
        horizon_days=state.artifact.horizon_days,
        decision_threshold=state.artifact.decision_threshold,
        calibration_method=config.get("calibration_method", "unknown"),
        n_features=len(state.feature_columns),
        seed=config.get("seed", -1),
        dataset_fingerprint_sha256_16=config.get("input_file_hashes_sha256_16", {}),
        disclaimer=DISCLAIMER,
    )
