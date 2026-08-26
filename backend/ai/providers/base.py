"""
Provider-agnostic LLM interface. The orchestrator (backend/ai/orchestrator.py)
depends only on this Protocol — never on a specific vendor SDK — so swapping
or adding a provider never touches context assembly, guardrails, or the
response schema. See docs/architecture/ai_orchestrator.md.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol

if TYPE_CHECKING:
    from backend.api.schemas.ai import SentinelAIContext


class ProviderUnavailableError(Exception):
    """Raised when a provider is configured but cannot actually be used
    (missing credentials, the SDK package isn't installed, or a live call
    failed). Routers translate this to a clean 503 — never the raw
    underlying exception or any credential material.
    """


class LLMProvider(Protocol):
    identifier: str

    def complete(self, system_prompt: str, user_message: str, context: "SentinelAIContext") -> str:
        """Returns raw provider output — expected to be a JSON string per
        backend/ai/prompt.py's instructed shape, but callers must treat it as
        untrusted text and parse defensively (backend/ai/response_parser.py).
        """
        ...
