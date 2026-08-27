"""
A fully deterministic, no-network provider — the default when
SENTINEL_AI_PROVIDER is unset, and the ONLY provider used in the test
suite (see docs/architecture/ai_orchestrator.md "Mock provider"). Every
answer it produces:

  - is built from `context` fields only — never invents a fact, number, or
    document that isn't already in the verified context;
  - is explicitly labeled as a mock response, so it can never be confused
    with a real provider's output (backend/ai orchestrator also tags the
    response's `provider` field as "mock");
  - is a plain string keyword router, not a language model — it has no
    "creativity" to fabricate anything with.

This is intentionally simple. It exists to make the rest of the
orchestrator (context assembly, guardrails, response schema, API,
frontend) fully testable and runnable without any external dependency or
API key — not to simulate what a real model would say.
"""

from __future__ import annotations

import json

from backend.api.schemas.ai import SentinelAIContext

MOCK_LABEL = "(Mock assistant response — for local development and testing, not a real AI-generated answer.)"

_OUT_OF_SCOPE_MARKERS = (
    "settlement hold",
    "enforcement",
    "internal risk score",
    "bank decision",
    "will i be approved",
    "will this be approved",
    "guarantee",
    "next year",
    "real world",
    "real-world probability",
    "production ready",
    "production-ready",
    "success rate",
    "learned from",
    "has sentinel learned",
    "outcome rate",
)


def _risk_answer(context: SentinelAIContext) -> str:
    risk = context.risk
    if risk is None:
        return "I don't have a verified risk assessment in the current context to explain."
    lines = [
        f"As of {risk.as_of_date}, the modeled {risk.horizon_days}-day probability is "
        f"{risk.probability_calibrated:.1%}, which the model classifies as '{risk.risk_state}' "
        f"against its decision threshold of {risk.decision_threshold:.1%}.",
        risk.disclaimer,
    ]
    if context.drivers:
        top = context.drivers[0]
        lines.append(
            f"The largest verified contributor is '{top.feature}' (group: {top.group}), which is "
            f"{'contributing to' if top.direction == 'increases_risk' else 'reducing' if top.direction == 'decreases_risk' else 'a negligible contributor to'} "
            "modeled risk — this is a SHAP association with the model's own output, not a causal claim."
        )
    return "\n".join(lines)


def _liquidity_answer(context: SentinelAIContext) -> str:
    if context.liquidity is None or context.exposure is None:
        return "I don't have verified exposure or liquidity figures in the current context to explain."
    liquidity, exposure = context.liquidity, context.exposure
    stress_text = (
        f"a liquidity stress ratio of {liquidity.liquidity_stress:.2f} (estimated exposure divided by "
        "available liquidity — a transparent derived ratio, not an ML prediction)"
        if liquidity.liquidity_stress is not None
        else "no computable liquidity stress ratio (available liquidity was zero or exposure wasn't available)"
    )
    return (
        f"Estimated exposure is {exposure.value:,.0f} units ({exposure.method}), against observed available "
        f"liquidity of {liquidity.available_liquidity:,.0f} units. That gives {stress_text}. {liquidity.note} "
        "The model does not predict liquidity directly — this figure is a transparent derived calculation."
    )


def _simulation_answer(context: SentinelAIContext) -> str:
    sim = context.simulation
    if sim is None:
        return "There's no simulation result in the current context to explain."
    changed = ", ".join(f"{k}={v:.3f}" for k, v in sim.controls_changed.items())
    return (
        f"Under the simulated control values ({changed}), the modeled probability moved from "
        f"{sim.current_probability:.1%} to {sim.simulated_probability:.1%} "
        f"({sim.probability_delta_absolute:+.1%}), and the illustrative exposure scaling moved from "
        f"{sim.exposure_current:,.0f} to {sim.exposure_simulated:,.0f} units. {sim.disclaimer}"
    )


def _incident_answer(context: SentinelAIContext) -> str:
    incident = context.incident
    if incident is None:
        return "There's no incident selected in the current context to summarize."
    missing = ", ".join(incident.missing_evidence) if incident.missing_evidence else "none — all required evidence is available"
    return (
        f"Incident {incident.incident_id} ({incident.event_type}) is '{incident.status}' with '{incident.priority}' "
        f"priority. Reason code: {incident.reason_code_label} ({incident.reason_code}). "
        f"{incident.reason_code_taxonomy_disclaimer} Evidence readiness is '{incident.evidence_readiness_status}'; "
        f"missing evidence: {missing}. Missing evidence is not fabricated — it is reported as unavailable until "
        "genuinely provided."
    )


def _draft_answer(context: SentinelAIContext) -> str:
    incident = context.incident
    header = f" for incident {incident.incident_id} ({incident.reason_code_label})" if incident else ""
    body = [
        f"DRAFT — internal preparation note{header}. Not submitted anywhere; requires merchant review and "
        "explicit confirmation before any real-world use.",
    ]
    if incident is not None:
        body.append(f"Status: {incident.status}. Evidence readiness: {incident.evidence_readiness_status}.")
        if incident.missing_evidence:
            body.append("Outstanding items to gather before this draft can be considered complete: " + ", ".join(incident.missing_evidence) + ".")
    if context.risk is not None:
        body.append(
            f"Modeled context: {context.risk.probability_calibrated:.1%} modeled {context.risk.horizon_days}-day "
            "probability (synthetic-benchmark model output, not a validated real-world probability)."
        )
    return "\n".join(body)


def _intervention_answer(context: SentinelAIContext) -> str:
    if not context.interventions:
        return (
            "No intervention is currently recommended for this merchant — none of the three bounded "
            "simulator controls (refund rate, on-time fulfillment rate, new-customer share) show a "
            "material deviation from this merchant's own recent baseline as of this date."
        )
    lines = ["Current intervention recommendations, in priority order:"]
    for rec in context.interventions:
        lines.append(f"- [{rec.priority}] {rec.title} — {rec.reason}")
    lines.append(
        "These are deterministic, rule-based candidates grounded in this merchant's own observed "
        "deviation from baseline — not an ML prediction and not an LLM-generated suggestion. They do not "
        "guarantee a change in real-world risk. Test a control's modeled impact in the simulator before "
        "drawing any conclusion."
    )
    return "\n".join(lines)


def _out_of_scope_answer() -> str:
    return (
        "That's not something I can answer from Sentinel's verified context — this prototype has no access to "
        "real Razorpay systems, settlement or enforcement decisions, or any real-world validated probability. "
        "I can only explain the modeled/derived figures already computed for this merchant."
    )


def _general_answer(context: SentinelAIContext) -> str:
    parts = [f"Here's what's currently verified for {context.merchant.merchant_id} ({context.merchant.archetype})."]
    if context.risk is not None:
        parts.append(f"Modeled {context.risk.horizon_days}-day risk: {context.risk.risk_state} ({context.risk.probability_calibrated:.1%}).")
    if context.liquidity is not None and context.liquidity.liquidity_stress is not None:
        parts.append(f"Liquidity stress: {context.liquidity.liquidity_stress:.2f}x (derived).")
    if context.interventions:
        parts.append(f"{len(context.interventions)} intervention recommendation(s) are currently grounded for this merchant.")
    if context.incident is not None:
        parts.append(f"Selected incident: {context.incident.incident_id}, evidence {context.incident.evidence_readiness_status}.")
    if context.simulation is not None:
        parts.append("A simulation result is also loaded — ask me to explain its modeled impact.")
    parts.append("Ask about risk drivers, liquidity, recommended interventions, a simulation, or incident evidence for more detail.")
    return " ".join(parts)


class MockProvider:
    identifier = "mock"

    def complete(self, system_prompt: str, user_message: str, context: SentinelAIContext) -> str:
        del system_prompt  # the mock doesn't need the serialized prompt — it reads `context` directly
        question = user_message.lower()

        if any(marker in question for marker in _OUT_OF_SCOPE_MARKERS):
            body = _out_of_scope_answer()
        elif context.incident is not None and any(k in question for k in ("draft", "prepare", "response material")):
            body = _draft_answer(context)
        elif context.incident is not None and any(k in question for k in ("incident", "evidence", "missing", "summarize")):
            body = _incident_answer(context)
        elif context.simulation is not None and any(k in question for k in ("simulat", "what if", "modeled impact")):
            body = _simulation_answer(context)
        elif any(k in question for k in ("recommend", "intervention", "should i", "what should", "consider")):
            body = _intervention_answer(context)
        elif any(k in question for k in ("liquidity", "cash", "buffer")):
            body = _liquidity_answer(context)
        elif any(k in question for k in ("risk", "driver", "why", "elevated", "flag")):
            body = _risk_answer(context)
        else:
            body = _general_answer(context)

        answer = f"{MOCK_LABEL} {body}"
        suggested = ["Why is my risk elevated?", "What does this mean for liquidity?"]
        if context.interventions:
            suggested.append("What should I consider reviewing?")
        if context.simulation is not None:
            suggested.append("Explain the modeled impact of my simulation.")
        if context.incident is not None:
            suggested.append("What evidence is still missing?")

        return json.dumps({"answer": answer, "suggested_next_actions": suggested[:4]})
