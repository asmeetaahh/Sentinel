from __future__ import annotations

from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query

from backend.api.dependencies import get_state
from backend.api.schemas.explainability import ExplanationResponse
from backend.api.schemas.risk import RiskResponse
from backend.api.state import AppState
from backend.risk import explainability_service, risk_service
from backend.services.lookups import DateNotAvailableError, MerchantNotFoundError, UnsupportedHorizonError

router = APIRouter(prefix="/merchants", tags=["risk"])


@router.get("/{merchant_id}/risk", response_model=RiskResponse)
def get_risk(
    merchant_id: str,
    as_of_date: date = Query(...),
    horizon_days: int = Query(default=30),
    state: AppState = Depends(get_state),
) -> RiskResponse:
    try:
        result = risk_service.assess_risk(state, merchant_id, as_of_date, horizon_days)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DateNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedHorizonError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RiskResponse(**result)


@router.get("/{merchant_id}/explanation", response_model=ExplanationResponse)
def get_explanation(
    merchant_id: str,
    as_of_date: date = Query(...),
    top_k: int = Query(default=6, ge=1, le=55),
    state: AppState = Depends(get_state),
) -> ExplanationResponse:
    try:
        result = explainability_service.explain(state, merchant_id, as_of_date, top_k=top_k)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except DateNotAvailableError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return ExplanationResponse(**result)
