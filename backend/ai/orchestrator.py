"""
Ties context assembly, guardrails, prompt construction, the provider call,
and response parsing into one function. This is the ONLY place that calls
`provider.complete()` — see docs/architecture/ai_orchestrator.md for the
full request flow.

Domain exceptions (MerchantNotFoundError, DateNotAvailableError,
IncidentNotFoundError, UnsupportedHorizonError, ControlOutOfRangeError,
ProviderUnavailableError, ...) all propagate up to the router
(backend/api/routers/ai.py) exactly like every other Sentinel service —
this module does not catch or reinterpret them.
"""

from __future__ import annotations

from backend.ai import context_builder, guardrails, prompt, response_parser
from backend.ai.providers.base import ProviderUnavailableError
from backend.api.schemas.ai import AssistantRequest, AssistantResponse
from backend.api.state import AppState


def handle_assistant_request(state: AppState, merchant_id: str, request: AssistantRequest) -> AssistantResponse:
    # Deterministic pre-filter FIRST — a blatant injection attempt never
    # reaches the provider at all, real or mock.
    if guardrails.contains_injection_attempt(request.question):
        context = context_builder.build_context(
            state,
            merchant_id,
            as_of_date=request.as_of_date,
            incident_id=request.incident_id,
            simulation_request=request.simulation,
        )
        return guardrails.refusal_response(merchant_id, context)

    context = context_builder.build_context(
        state,
        merchant_id,
        as_of_date=request.as_of_date,
        incident_id=request.incident_id,
        simulation_request=request.simulation,
    )

    system_prompt = prompt.build_system_prompt(context)
    provider = state.ai_provider
    raw_output = provider.complete(system_prompt=system_prompt, user_message=request.question, context=context)

    answer, suggested_actions = response_parser.parse_llm_output(raw_output)
    if not answer:
        raise ProviderUnavailableError("The AI provider did not return a usable response.")
    if not suggested_actions:
        suggested_actions = guardrails.default_suggested_actions(context)

    return AssistantResponse(
        merchant_id=merchant_id,
        answer=answer,
        cited_context=context,
        provenance=guardrails.summarize_provenance(context),
        limitations=context.standing_limitations,
        disclaimer=guardrails.STANDING_DISCLAIMER,
        suggested_next_actions=suggested_actions,
        provider=provider.identifier,
    )
