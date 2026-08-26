from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_state
from backend.api.schemas.simulation import ControlsListResponse, SimulationRequest, SimulationResponse
from backend.api.state import AppState
from backend.services.lookups import DateNotAvailableError, MerchantNotFoundError, UnsupportedHorizonError
from backend.simulation import simulation_service
from backend.simulation.controls import ControlOutOfRangeError, NoInterventionProvidedError, UnknownControlError

router = APIRouter(prefix="/merchants", tags=["simulator"])


@router.get("/{merchant_id}/simulation/controls", response_model=ControlsListResponse)
def get_simulation_controls(
    merchant_id: str,
    as_of_date: date = Query(...),
    state: AppState = Depends(get_state),
) -> ControlsListResponse:
    try:
        result = simulation_service.list_controls(state, merchant_id, as_of_date)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DateNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ControlsListResponse(**result)


@router.post("/{merchant_id}/simulation", response_model=SimulationResponse)
def post_simulation(
    merchant_id: str,
    request: SimulationRequest,
    state: AppState = Depends(get_state),
) -> SimulationResponse:
    try:
        result = simulation_service.simulate(
            state,
            merchant_id,
            request.as_of_date,
            request.horizon_days,
            request.to_interventions(),
        )
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DateNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedHorizonError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (UnknownControlError, ControlOutOfRangeError, NoInterventionProvidedError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    return SimulationResponse(**result)
