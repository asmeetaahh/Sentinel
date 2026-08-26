"""
The real provider. Imports the `openai` SDK lazily (inside __init__, not at
module load time) so the rest of the application — including every other
Sentinel feature and the test suite — never fails to start or import just
because the package isn't installed. See docs/architecture/ai_orchestrator.md.
"""

from __future__ import annotations

from backend.api.schemas.ai import SentinelAIContext

from .base import ProviderUnavailableError

DEFAULT_MODEL = "gpt-4o-mini"
REQUEST_TIMEOUT_SECONDS = 20


class OpenAIProvider:
    def __init__(self, api_key: str, model: str = DEFAULT_MODEL):
        try:
            from openai import OpenAI
        except ImportError as exc:
            raise ProviderUnavailableError(
                "The 'openai' package is not installed. Install it (see requirements.txt) or set "
                "SENTINEL_AI_PROVIDER=mock."
            ) from exc

        self._model = model
        self.identifier = f"openai:{model}"
        self._client = OpenAI(api_key=api_key, timeout=REQUEST_TIMEOUT_SECONDS)

    def complete(self, system_prompt: str, user_message: str, context: SentinelAIContext) -> str:
        del context  # the OpenAI provider only needs the already-serialized system_prompt
        try:
            response = self._client.chat.completions.create(
                model=self._model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.2,
                max_tokens=800,
                response_format={"type": "json_object"},
            )
        except Exception as exc:
            # Never surface the raw SDK exception (may include request
            # details) to callers — routers must not leak this upstream.
            raise ProviderUnavailableError("The configured AI provider request failed.") from exc

        content = response.choices[0].message.content if response.choices else None
        if not content:
            raise ProviderUnavailableError("The configured AI provider returned an empty response.")
        return content
