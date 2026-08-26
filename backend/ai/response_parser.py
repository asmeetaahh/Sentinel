"""
Parses raw provider output defensively. A provider's raw text is untrusted
and may not be valid JSON (a real LLM can drift from the instructed format;
network/SDK layers can also return unexpected wrapping). This never raises
on malformed input — it degrades to using the raw text as the answer with
no suggested actions, so a parsing hiccup never turns into a user-facing
500. See docs/architecture/ai_orchestrator.md "Numerical safety" — this
module only ever extracts prose text and short follow-up strings, never a
number that could be mistaken for a verified value.
"""

from __future__ import annotations

import json

MAX_SUGGESTED_ACTIONS = 4
MAX_SUGGESTED_ACTION_LENGTH = 200


def parse_llm_output(raw: str) -> tuple[str, list[str]]:
    raw = raw.strip()
    if not raw:
        return "", []

    try:
        parsed = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        return raw, []

    if not isinstance(parsed, dict):
        return raw, []

    answer = parsed.get("answer")
    if not isinstance(answer, str) or not answer.strip():
        return raw, []

    raw_actions = parsed.get("suggested_next_actions", [])
    actions: list[str] = []
    if isinstance(raw_actions, list):
        for action in raw_actions:
            if isinstance(action, str) and action.strip():
                actions.append(action.strip()[:MAX_SUGGESTED_ACTION_LENGTH])
            if len(actions) >= MAX_SUGGESTED_ACTIONS:
                break

    return answer.strip(), actions
