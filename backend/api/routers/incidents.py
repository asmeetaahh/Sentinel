from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.api.dependencies import get_state
from backend.api.schemas.incidents import IncidentDetail, IncidentEvidenceResponse, IncidentListResponse, IncidentSummary
from backend.api.state import AppState
from backend.incidents import incident_service
from backend.incidents.incident_service import IncidentNotFoundError
from backend.services.lookups import MerchantNotFoundError

router = APIRouter(tags=["incidents"])


@router.get("/merchants/{merchant_id}/incidents", response_model=IncidentListResponse)
def list_merchant_incidents(merchant_id: str, state: AppState = Depends(get_state)) -> IncidentListResponse:
    try:
        incidents = incident_service.list_incidents(state, merchant_id)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    summaries = [incident_service.summarize(incident) for incident in incidents]
    return IncidentListResponse(merchant_id=merchant_id, count=len(summaries), incidents=summaries)


@router.get("/incidents/{incident_id}", response_model=IncidentDetail)
def get_incident(incident_id: str, state: AppState = Depends(get_state)) -> IncidentDetail:
    try:
        incident = incident_service.get_incident(state, incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return IncidentDetail(**incident)


@router.get("/incidents/{incident_id}/evidence", response_model=IncidentEvidenceResponse)
def get_incident_evidence(incident_id: str, state: AppState = Depends(get_state)) -> IncidentEvidenceResponse:
    try:
        incident = incident_service.get_incident(state, incident_id)
    except IncidentNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return IncidentEvidenceResponse(
        incident_id=incident["incident_id"],
        merchant_id=incident["merchant_id"],
        evidence_readiness=incident["evidence_readiness"],
    )
