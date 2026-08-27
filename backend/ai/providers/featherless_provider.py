"""
The Featherless.ai provider — a real LLM reached through an OpenAI-
compatible Chat Completions API at a custom `base_url`. Imports the
`openai` SDK lazily (inside `__init__`, not at module load time), exactly
like `backend/ai/providers/openai_provider.py`, so the rest of the
application — including every other Sentinel feature and the test suite —
never fails to start or import just because the package isn't installed
or the provider isn't configured. See docs/architecture/ai_orchestrator.md.

Featherless (https://featherless.ai) hosts open-weight models (e.g.
`openai/gpt-oss-20b`) behind an OpenAI-compatible Chat Completions API —
the same `openai` SDK already used for the real OpenAI provider works
unmodified against it, simply pointed at Featherless's own `base_url`.
This is why Sentinel does not need a custom HTTP stack for Featherless: it
is a second, independent implementation of the existing `LLMProvider`
Protocol (`backend/ai/providers/base.py`), not a new abstraction.

Unlike `OpenAIProvider`, this provider does NOT request
`response_format={"type": "json_object"}`. Featherless's OpenAI-
compatible proxy is not guaranteed to support that parameter for every
hosted open-weight model, and forcing it risks a hard request failure
for a cosmetic benefit — `backend/ai/prompt.py`'s own instructions already
ask the model for the JSON shape, and `backend/ai/response_parser.py` is
already defensively built to fall back to using raw text as the answer if
the response isn't valid JSON. Omitting the constraint here is the more
broadly-compatible choice, not a relaxation of any safety property: the
response still passes through the exact same parser/validation path as
every other provider.
"""

from __future__ import annotations

from backend.api.schemas.ai import SentinelAIContext

from .base import ProviderUnavailableError

REQUEST_TIMEOUT_SECONDS = 20

# Empirically higher than OpenAIProvider's 800: Sentinel's real system
# prompt is large (it embeds the full serialized SentinelAIContext, often
# 3000+ prompt tokens), and gpt-oss-20b tends to produce a thorough,
# multi-paragraph answer in response — live testing against the actual
# Featherless API showed `finish_reason: "length"` (silently truncated
# mid-sentence, before the closing JSON brace) at 800 tokens, and a clean
# `finish_reason: "stop"` with valid JSON at this value. Still an explicit,
# bounded ceiling, not unlimited.
MAX_COMPLETION_TOKENS = 1600


class FeatherlessProvider:
    def __init__(self, api_key: str, base_url: str, model: str):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderUnavailableError(
                "The 'openai' package is not installed. Install it (see requirements.txt) or set "
                "SENTINEL_AI_PROVIDER=mock."
            ) from exc

        self._model = model
        self.identifier = f"featherless:{model}"
        self._client = OpenAI(api_key=api_key, base_url=base_url, timeout=REQUEST_TIMEOUT_SECONDS)

    def complete(self, system_prompt: str, user_message: str, context: SentinelAIContext) -> str:
        del context  # Featherless, like OpenAIProvider, only needs the already-serialized system_prompt
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2,
                max_tokens=MAX_COMPLETION_TOKENS,
            )
        except Exception as exc:
            # Never surface the raw SDK exception (may include request or
            # credential details) to callers — routers must not leak this
            # upstream. This single handler covers authentication failures,
            # timeouts, and connectivity errors alike; all map to the same
            # safe, generic message, exactly like OpenAIProvider.
            raise ProviderUnavailableError("The configured AI provider request failed.") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ProviderUnavailableError("The configured AI provider returned an empty response.")
        return content
