from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_state
from backend.api.schemas.merchants import (
    FeatureVectorResponse,
    MerchantListResponse,
    MerchantProfileResponse,
    ObservationsResponse,
)
from backend.api.state import AppState
from backend.services import merchant_service
from backend.services.lookups import DateNotAvailableError, MerchantNotFoundError

router = APIRouter(prefix="/merchants", tags=["merchants"])


@router.get("", response_model=MerchantListResponse)
def list_merchants(archetype: str | None = Query(default=None), state: AppState = Depends(get_state)) -> MerchantListResponse:
    merchants = merchant_service.list_merchants(state, archetype=archetype)
    return MerchantListResponse(count=len(merchants), merchants=merchants)


@router.get("/{merchant_id}", response_model=MerchantProfileResponse)
def get_merchant(merchant_id: str, state: AppState = Depends(get_state)) -> MerchantProfileResponse:
    try:
        profile = merchant_service.get_merchant_profile(state, merchant_id)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return MerchantProfileResponse(**profile)


@router.get("/{merchant_id}/observations", response_model=ObservationsResponse)
def get_observations(
    merchant_id: str,
    start_date: date | None = Query(default=None),
    end_date: date | None = Query(default=None),
    limit: int | None = Query(default=None, ge=1, le=180),
    state: AppState = Depends(get_state),
) -> ObservationsResponse:
    try:
        observations = merchant_service.get_observations(state, merchant_id, start_date, end_date, limit)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return ObservationsResponse(merchant_id=merchant_id, count=len(observations), observations=observations)


@router.get("/{merchant_id}/features", response_model=FeatureVectorResponse)
def get_features(merchant_id: str, as_of_date: date = Query(...), state: AppState = Depends(get_state)) -> FeatureVectorResponse:
    try:
        result = merchant_service.get_feature_vector(state, merchant_id, as_of_date)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DateNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return FeatureVectorResponse(**result)
