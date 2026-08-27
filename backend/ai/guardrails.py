"""
Deterministic safety layer, independent of any provider's actual behavior:

1. A pre-filter that catches blatant prompt-injection attempts BEFORE any
   provider is called — a real, testable layer of defense, not just a hope
   that the model complies with the system prompt.
2. Deterministic construction of `provenance`, `limitations`, and
   `disclaimer` for the response — never left to LLM discretion, so these
   are guaranteed correct regardless of what the provider returns.

See docs/architecture/ai_orchestrator.md "Prompt-injection defense" and
"Numerical safety" for the full rationale.
"""

from __future__ import annotations

import re

from backend.api.schemas.ai import AssistantResponse, SentinelAIContext

STANDING_DISCLAIMER = (
    "Sentinel's assistant explains verified model, exposure, liquidity, simulator, and incident outputs that "
    "were already computed by deterministic backend services. It does not independently calculate risk, "
    "exposure, liquidity stress, SHAP values, or simulator results, and its answers are not a validated "
    "real-world prediction, a causal claim, or access to Razorpay's proprietary systems."
)

GUARDRAIL_REFUSAL_ANSWER = (
    "I can't act on that request. Sentinel's assistant only explains verified, already-computed model, "
    "exposure, liquidity, simulator, and incident data — it can't be instructed to ignore its safety rules, "
    "reveal internal instructions, claim a dispute was submitted, claim access to Razorpay's proprietary "
    "systems, or invent evidence. Ask me about the risk, exposure, liquidity, simulation, or incident data "
    "already shown for this merchant instead."
)

# A first line of defense, not a complete solution — a determined adversarial
# prompt aimed at a real provider can still only be constrained by the
# system prompt's own rules (backend/ai/prompt.py). This pattern list
# catches the common, blatant phrasings named explicitly in
# docs/architecture/ai_orchestrator.md, and is deliberately conservative
# (prefers a few precise patterns over broad ones that would also block
# legitimate questions).
_INJECTION_PATTERNS = [
    r"ignore (all |any )?(the |your )?previous instructions",
    r"disregard (all |any )?(the |your )?(previous|prior) instructions",
    r"forget (all |your )?(previous |prior )?instructions",
    r"reveal (your|the) system prompt",
    r"show (me )?(your|the) (system )?prompt",
    r"what (is|are) your (system )?(instructions|prompt)",
    r"pretend (that )?you (are|have|can)",
    r"act as (if )?you",
    r"you are now",
    r"jailbreak",
    r"bypass (your|the|any) (rules|instructions|guardrails|safety)",
    r"the dispute (was|has been|is) (submitted|filed|won)",
    r"confirm (that )?the dispute",
    r"you have access to razorpay",
    r"razorpay('s)? (internal|proprietary)",
    r"invent (some )?evidence",
    r"make up (some )?evidence",
    r"fabricate (some )?evidence",
]
_INJECTION_RE = re.compile("|".join(_INJECTION_PATTERNS), re.IGNORECASE)


def contains_injection_attempt(question: str) -> bool:
    return bool(_INJECTION_RE.search(question))


def summarize_provenance(context: SentinelAIContext) -> dict[str, str]:
    provenance: dict[str, str] = {"merchant": context.merchant.provenance}
    if context.observed_state is not None:
        provenance["observed_state"] = context.observed_state.provenance
    if context.risk is not None:
        provenance["risk"] = context.risk.provenance
    if context.exposure is not None:
        provenance["exposure"] = context.exposure.provenance
    if context.liquidity is not None:
        provenance["liquidity"] = context.liquidity.provenance
    if context.data_quality is not None:
        provenance["data_quality"] = context.data_quality.provenance
    if context.drivers:
        provenance["drivers"] = "modeled"
    if context.interventions:
        provenance["interventions"] = "derived"
    if context.simulation is not None:
        provenance["simulation"] = context.simulation.provenance
    if context.incident is not None:
        provenance["incident"] = context.incident.provenance
    return provenance


def default_suggested_actions(context: SentinelAIContext) -> list[str]:
    """Deterministic fallback suggestions, used when the provider's own
    suggestions are missing/malformed — never left blank in the UI.
    """
    actions = ["Why is my risk elevated?", "What does this mean for liquidity?"]
    if context.data_quality is not None:
        actions.append("How confident is this assessment?")
    if context.interventions:
        actions.append("What should I consider reviewing?")
    if context.simulation is not None:
        actions.append("Explain the modeled impact of my simulation.")
    if context.incident is not None:
        actions.append("What evidence is still missing?")
    return actions[:4]


def refusal_response(merchant_id: str, context: SentinelAIContext) -> AssistantResponse:
    return AssistantResponse(
        merchant_id=merchant_id,
        answer=GUARDRAIL_REFUSAL_ANSWER,
        cited_context=context,
        provenance=summarize_provenance(context),
        limitations=context.standing_limitations,
        disclaimer=STANDING_DISCLAIMER,
        suggested_next_actions=default_suggested_actions(context),
        provider="guardrail",
        guardrail_triggered=True,
    )
