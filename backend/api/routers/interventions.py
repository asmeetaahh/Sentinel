from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_state
from backend.api.schemas.interventions import (
    InterventionMemoryListResponse,
    InterventionMemoryRecord,
    InterventionRecommendationsResponse,
    RecordInterventionRequest,
)
from backend.api.state import AppState
from backend.interventions import recommendation_service
from backend.memory import risk_memory_service
from backend.memory.risk_memory_service import (
    InvalidInterventionIdError,
    SimulationControlMismatchError,
    SimulationDateMismatchError,
    SimulationNotApplicableError,
    SimulationRequiredError,
)
from backend.services.lookups import DateNotAvailableError, MerchantNotFoundError, UnsupportedHorizonError
from backend.simulation.controls import ControlOutOfRangeError, NoInterventionProvidedError, UnknownControlError

router = APIRouter(prefix="/merchants", tags=["interventions"])


@router.get("/{merchant_id}/interventions", response_model=InterventionRecommendationsResponse)
def get_interventions(
    merchant_id: str,
    as_of_date: date | None = Query(default=None),
    state: AppState = Depends(get_state),
) -> InterventionRecommendationsResponse:
    try:
        result = recommendation_service.get_recommendations(state, merchant_id, as_of_date)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DateNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return InterventionRecommendationsResponse(**result)


@router.get("/{merchant_id}/interventions/memory", response_model=InterventionMemoryListResponse)
def get_intervention_memory(merchant_id: str, state: AppState = Depends(get_state)) -> InterventionMemoryListResponse:
    try:
        result = risk_memory_service.list_memory(state, merchant_id)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return InterventionMemoryListResponse(**result)


@router.post("/{merchant_id}/interventions/memory", response_model=InterventionMemoryRecord)
def post_intervention_memory(
    merchant_id: str,
    request: RecordInterventionRequest,
    state: AppState = Depends(get_state),
) -> InterventionMemoryRecord:
    try:
        record = risk_memory_service.record_intervention(
            state,
            merchant_id,
            request.intervention_id,
            request.action_status,
            request.simulation,
        )
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DateNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedHorizonError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (
        InvalidInterventionIdError,
        SimulationRequiredError,
        SimulationNotApplicableError,
        SimulationControlMismatchError,
        SimulationDateMismatchError,
        UnknownControlError,
        ControlOutOfRangeError,
        NoInterventionProvidedError,
    ) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return InterventionMemoryRecord(**record)
