"""
Selects a provider from environment configuration. Building a provider here
NEVER raises — a misconfigured or absent AI provider must never prevent the
rest of Sentinel (backend startup, /risk, /simulation, /incidents, ...)
from working. An unavailable real provider only fails lazily, the first
time `.complete()` is actually called, with a clear, safe message.

Environment variables (see docs/architecture/ai_orchestrator.md):
    SENTINEL_AI_PROVIDER   "mock" (default), "openai", or "featherless"
    OPENAI_API_KEY         required only when SENTINEL_AI_PROVIDER=openai
    SENTINEL_AI_MODEL      optional, defaults to openai_provider.DEFAULT_MODEL
                           (openai path only)
    FEATHERLESS_API_KEY    required only when SENTINEL_AI_PROVIDER=featherless
    FEATHERLESS_BASE_URL   required only when SENTINEL_AI_PROVIDER=featherless
                           (e.g. https://api.featherless.ai/v1)
    FEATHERLESS_MODEL      required only when SENTINEL_AI_PROVIDER=featherless
                           (e.g. openai/gpt-oss-20b)

There is deliberately no separate `AI_PROVIDER` variable: `SENTINEL_AI_PROVIDER`
already exists as this project's one provider-selection switch (used by the
"mock"/"openai" values above since the AI Orchestrator was first built), so
Featherless is added as a third value of the SAME variable rather than a
second, competing configuration mechanism.
"""

from __future__ import annotations

import os

from backend.api.schemas.ai import SentinelAIContext

from .base import LLMProvider, ProviderUnavailableError
from .mock_provider import MockProvider


class UnavailableProvider:
    """Placeholder for a configured-but-unusable real provider (e.g.
    SENTINEL_AI_PROVIDER=openai with no API key). Constructing this never
    raises; `.complete()` raises ProviderUnavailableError with a safe,
    non-secret message.
    """

    identifier = "unavailable"

    def __init__(self, reason: str):
        self._reason = reason

    def complete(self, system_prompt: str, user_message: str, context: SentinelAIContext) -> str:
        del system_prompt, user_message, context
        raise ProviderUnavailableError(self._reason)


def build_provider() -> LLMProvider:
    provider_name = os.environ.get("SENTINEL_AI_PROVIDER", "mock").strip().lower()

    if provider_name == "mock":
        return MockProvider()

    if provider_name == "openai":
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            return UnavailableProvider(
                "SENTINEL_AI_PROVIDER=openai but OPENAI_API_KEY is not set. Set the key, or set "
                "SENTINEL_AI_PROVIDER=mock for local development."
            )
        model = os.environ.get("SENTINEL_AI_MODEL", "").strip()
        try:
            from .openai_provider import DEFAULT_MODEL, OpenAIProvider

            return OpenAIProvider(api_key=api_key, model=model or DEFAULT_MODEL)
        except ProviderUnavailableError as exc:
            return UnavailableProvider(str(exc))

    if provider_name == "featherless":
        api_key = os.environ.get("FEATHERLESS_API_KEY", "").strip()
        base_url = os.environ.get("FEATHERLESS_BASE_URL", "").strip()
        model = os.environ.get("FEATHERLESS_MODEL", "").strip()
        missing = [
            name
            for name, value in (
                ("FEATHERLESS_API_KEY", api_key),
                ("FEATHERLESS_BASE_URL", base_url),
                ("FEATHERLESS_MODEL", model),
            )
            if not value
        ]
        if missing:
            return UnavailableProvider(
                f"SENTINEL_AI_PROVIDER=featherless but {', '.join(missing)} "
                f"{'is' if len(missing) == 1 else 'are'} not set. Set "
                f"{'it' if len(missing) == 1 else 'them'}, or set SENTINEL_AI_PROVIDER=mock for local development."
            )
        try:
            from .featherless_provider import FeatherlessProvider

            return FeatherlessProvider(api_key=api_key, base_url=base_url, model=model)
        except ProviderUnavailableError as exc:
            return UnavailableProvider(str(exc))

    return UnavailableProvider(
        f"Unknown SENTINEL_AI_PROVIDER={provider_name!r}. Expected 'mock', 'openai', or 'featherless'."
    )
