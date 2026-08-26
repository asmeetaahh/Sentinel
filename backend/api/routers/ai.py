from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from backend.ai import orchestrator
from backend.ai.providers.base import ProviderUnavailableError
from backend.api.dependencies import get_state
from backend.api.schemas.ai import AssistantRequest, AssistantResponse
from backend.api.state import AppState
from backend.incidents.incident_service import IncidentNotFoundError
from backend.services.lookups import DateNotAvailableError, MerchantNotFoundError, UnsupportedHorizonError
from backend.simulation.controls import ControlOutOfRangeError, NoInterventionProvidedError, UnknownControlError

router = APIRouter(prefix="/merchants", tags=["ai"])


@router.post("/{merchant_id}/assistant", response_model=AssistantResponse)
def post_assistant(
    merchant_id: str,
    request: AssistantRequest,
    state: AppState = Depends(get_state),
) -> AssistantResponse:
    try:
        return orchestrator.handle_assistant_request(state, merchant_id, request)
    except MerchantNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except (DateNotAvailableError, IncidentNotFoundError) as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except UnsupportedHorizonError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except (UnknownControlError, ControlOutOfRangeError, NoInterventionProvidedError) as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except ProviderUnavailableError:
        # Never leak the underlying provider exception (may reference
        # request/credential details) — a fixed, safe message only.
        raise HTTPException(
            status_code=503,
            detail="The AI assistant provider is currently unavailable. Try again later, or configure "
            "SENTINEL_AI_PROVIDER=mock for local development.",
        ) from None
    except RuntimeError as exc:
        # SHAP faithfulness failure inside explainability_service — same
        # handling as /merchants/{id}/explanation.
        raise HTTPException(status_code=500, detail=str(exc)) from exc
