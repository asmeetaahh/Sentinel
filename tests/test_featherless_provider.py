"""
Tests for the Featherless.ai provider (backend/ai/providers/featherless_provider.py)
and its factory wiring (backend/ai/providers/factory.py).

Per the task's explicit constraints: the `openai.OpenAI` client is always
mocked here — this suite NEVER calls the real Featherless API, and no test
requires FEATHERLESS_API_KEY to be set in the environment. See
docs/architecture/ai_orchestrator.md "Provider abstraction".
"""

from __future__ import annotations

import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

import openai  # noqa: E402

from backend.ai.providers.base import ProviderUnavailableError  # noqa: E402
from backend.ai.providers.factory import UnavailableProvider, build_provider  # noqa: E402
from backend.ai.providers.featherless_provider import FeatherlessProvider  # noqa: E402


class _FakeChatCompletions:
    """Stands in for `client.chat.completions` — never makes a real HTTP call."""

    def __init__(self, *, content: str | None = "(fake) OK", raise_exc: Exception | None = None):
        self._content = content
        self._raise_exc = raise_exc
        self.last_call_kwargs: dict | None = None

    def create(self, **kwargs):
        self.last_call_kwargs = kwargs
        if self._raise_exc is not None:
            raise self._raise_exc
        if self._content is None:
            return SimpleNamespace(choices=[])
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=self._content))])


class _FakeOpenAIClient:
    """Stands in for `openai.OpenAI(...)` — captures constructor kwargs and
    exposes a `.chat.completions` fake instead of touching the network.
    """

    def __init__(self, **init_kwargs):
        self.init_kwargs = init_kwargs
        self.completions = _FakeChatCompletions()
        self.chat = SimpleNamespace(completions=self.completions)


@pytest.fixture
def fake_openai_client(monkeypatch):
    """Patches `openai.OpenAI` (the exact symbol FeatherlessProvider imports
    lazily via `from openai import OpenAI`) with the fake client class above,
    and returns the class so tests can inspect instances created from it.
    """
    monkeypatch.setattr(openai, "OpenAI", _FakeOpenAIClient)
    return _FakeOpenAIClient


# ---------------------------------------------------------------------------
# 1. Provider configuration / construction
# ---------------------------------------------------------------------------


def test_provider_reads_api_key_base_url_and_model_into_the_client(fake_openai_client):
    provider = FeatherlessProvider(
        api_key="test-key-not-real",
        base_url="https://api.featherless.ai/v1",
        model="openai/gpt-oss-20b",
    )
    assert provider._client.init_kwargs["api_key"] == "test-key-not-real"
    assert provider._client.init_kwargs["base_url"] == "https://api.featherless.ai/v1"


def test_provider_identifier_names_both_vendor_and_model(fake_openai_client):
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    assert provider.identifier == "featherless:openai/gpt-oss-20b"


def test_provider_sets_a_bounded_timeout(fake_openai_client):
    from backend.ai.providers.featherless_provider import REQUEST_TIMEOUT_SECONDS

    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    assert provider._client.init_kwargs["timeout"] == REQUEST_TIMEOUT_SECONDS
    assert REQUEST_TIMEOUT_SECONDS > 0


# ---------------------------------------------------------------------------
# 2 & 3. Missing API key / missing model surfaced by the FACTORY, not a crash
# ---------------------------------------------------------------------------


def test_factory_returns_unavailable_when_featherless_requested_without_api_key(monkeypatch):
    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "featherless")
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    monkeypatch.setenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
    monkeypatch.setenv("FEATHERLESS_MODEL", "openai/gpt-oss-20b")

    provider = build_provider()
    assert isinstance(provider, UnavailableProvider)
    with pytest.raises(ProviderUnavailableError, match="FEATHERLESS_API_KEY"):
        provider.complete("sys", "hi", None)


def test_factory_returns_unavailable_when_featherless_requested_without_model(monkeypatch):
    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "featherless")
    monkeypatch.setenv("FEATHERLESS_API_KEY", "test-key-not-real")
    monkeypatch.setenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
    monkeypatch.delenv("FEATHERLESS_MODEL", raising=False)

    provider = build_provider()
    assert isinstance(provider, UnavailableProvider)
    with pytest.raises(ProviderUnavailableError, match="FEATHERLESS_MODEL"):
        provider.complete("sys", "hi", None)


def test_factory_returns_unavailable_when_featherless_requested_without_base_url(monkeypatch):
    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "featherless")
    monkeypatch.setenv("FEATHERLESS_API_KEY", "test-key-not-real")
    monkeypatch.delenv("FEATHERLESS_BASE_URL", raising=False)
    monkeypatch.setenv("FEATHERLESS_MODEL", "openai/gpt-oss-20b")

    provider = build_provider()
    assert isinstance(provider, UnavailableProvider)
    with pytest.raises(ProviderUnavailableError, match="FEATHERLESS_BASE_URL"):
        provider.complete("sys", "hi", None)


def test_factory_reports_all_missing_vars_when_none_are_set(monkeypatch):
    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "featherless")
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    monkeypatch.delenv("FEATHERLESS_BASE_URL", raising=False)
    monkeypatch.delenv("FEATHERLESS_MODEL", raising=False)

    provider = build_provider()
    with pytest.raises(ProviderUnavailableError) as exc_info:
        provider.complete("sys", "hi", None)
    message = str(exc_info.value)
    assert "FEATHERLESS_API_KEY" in message
    assert "FEATHERLESS_BASE_URL" in message
    assert "FEATHERLESS_MODEL" in message


def test_building_a_provider_never_raises_even_when_featherless_misconfigured(monkeypatch):
    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "featherless")
    monkeypatch.delenv("FEATHERLESS_API_KEY", raising=False)
    monkeypatch.delenv("FEATHERLESS_BASE_URL", raising=False)
    monkeypatch.delenv("FEATHERLESS_MODEL", raising=False)
    build_provider()  # must not raise


# ---------------------------------------------------------------------------
# 4 & 5. Correct base URL and model name reach the real client/request
# ---------------------------------------------------------------------------


def test_correct_base_url_is_passed_to_the_client(fake_openai_client, monkeypatch):
    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "featherless")
    monkeypatch.setenv("FEATHERLESS_API_KEY", "test-key-not-real")
    monkeypatch.setenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
    monkeypatch.setenv("FEATHERLESS_MODEL", "openai/gpt-oss-20b")

    provider = build_provider()
    assert isinstance(provider, FeatherlessProvider)
    assert provider._client.init_kwargs["base_url"] == "https://api.featherless.ai/v1"


def test_correct_model_name_is_used_in_the_chat_completion_request(fake_openai_client):
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    provider.complete("system prompt text", "user question text", context=None)
    assert provider._client.completions.last_call_kwargs["model"] == "openai/gpt-oss-20b"


# ---------------------------------------------------------------------------
# 6. Request construction
# ---------------------------------------------------------------------------


def test_request_sends_exactly_the_system_and_user_messages_given(fake_openai_client):
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    provider.complete("SYSTEM_PROMPT_TEXT", "USER_QUESTION_TEXT", context=None)

    messages = provider._client.completions.last_call_kwargs["messages"]
    assert messages == [
        {"role": "system", "content": "SYSTEM_PROMPT_TEXT"},
        {"role": "user", "content": "USER_QUESTION_TEXT"},
    ]


def test_request_does_not_force_json_response_format(fake_openai_client):
    """Unlike OpenAIProvider, Featherless is not guaranteed to support
    response_format={"type": "json_object"} for every hosted open-weight
    model — forcing it risks a hard request failure for no safety benefit,
    since response_parser.py already handles non-JSON output defensively.
    """
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    provider.complete("sys", "hi", context=None)
    assert "response_format" not in provider._client.completions.last_call_kwargs


def test_successful_response_content_is_returned_verbatim(fake_openai_client):
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    provider._client.completions._content = '{"answer": "hello", "suggested_next_actions": []}'
    result = provider.complete("sys", "hi", context=None)
    assert result == '{"answer": "hello", "suggested_next_actions": []}'


def test_context_argument_is_never_sent_to_the_provider(fake_openai_client):
    """The verified SentinelAIContext is used to build the system prompt
    upstream (backend/ai/prompt.py) — the provider itself never receives or
    forwards it as a separate request field; it exists on this method's
    signature only to satisfy the shared LLMProvider Protocol.
    """
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    provider.complete("sys", "hi", context={"fake": "context object, deliberately not a real SentinelAIContext"})
    assert "context" not in provider._client.completions.last_call_kwargs


# ---------------------------------------------------------------------------
# 7 & 8. Timeout / connectivity / authentication failure mapping
# ---------------------------------------------------------------------------


def test_sdk_exception_is_mapped_to_provider_unavailable_error(fake_openai_client):
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    provider._client.completions._raise_exc = TimeoutError("simulated network timeout")

    with pytest.raises(ProviderUnavailableError):
        provider.complete("sys", "hi", context=None)


def test_authentication_failure_is_mapped_to_provider_unavailable_error_without_leaking_details(fake_openai_client):
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    provider._client.completions._raise_exc = RuntimeError("401 Unauthorized: invalid API key sk-secret-value-xyz")

    with pytest.raises(ProviderUnavailableError) as exc_info:
        provider.complete("sys", "hi", context=None)

    # The raw SDK exception text (which could contain request/credential
    # details) must never appear in the exception Sentinel raises upward.
    assert "sk-secret-value-xyz" not in str(exc_info.value)
    assert "401" not in str(exc_info.value)


def test_empty_response_content_is_mapped_to_provider_unavailable_error(fake_openai_client):
    provider = FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")
    provider._client.completions._content = None

    with pytest.raises(ProviderUnavailableError, match="empty response"):
        provider.complete("sys", "hi", context=None)


def test_missing_openai_package_is_mapped_to_provider_unavailable_error(monkeypatch):
    import builtins

    real_import = builtins.__import__

    def _blocked_import(name, *args, **kwargs):
        if name == "openai":
            raise ImportError("simulated: openai package not installed")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(builtins, "__import__", _blocked_import)

    with pytest.raises(ProviderUnavailableError, match="not installed"):
        FeatherlessProvider(api_key="k", base_url="https://api.featherless.ai/v1", model="openai/gpt-oss-20b")


# ---------------------------------------------------------------------------
# 9. Provider factory selection
# ---------------------------------------------------------------------------


def test_factory_selects_featherless_provider_when_fully_configured(fake_openai_client, monkeypatch):
    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "featherless")
    monkeypatch.setenv("FEATHERLESS_API_KEY", "test-key-not-real")
    monkeypatch.setenv("FEATHERLESS_BASE_URL", "https://api.featherless.ai/v1")
    monkeypatch.setenv("FEATHERLESS_MODEL", "openai/gpt-oss-20b")

    provider = build_provider()
    assert isinstance(provider, FeatherlessProvider)
    assert provider.identifier == "featherless:openai/gpt-oss-20b"


def test_factory_still_selects_mock_when_provider_var_is_mock(monkeypatch):
    """MockProvider must remain fully available and unaffected by the
    Featherless integration — the default, deterministic, no-network path.
    """
    from backend.ai.providers.mock_provider import MockProvider

    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "mock")
    monkeypatch.setenv("FEATHERLESS_API_KEY", "test-key-not-real")  # present but irrelevant when provider=mock
    provider = build_provider()
    assert isinstance(provider, MockProvider)
    assert provider.identifier == "mock"


def test_factory_still_selects_openai_path_unaffected_by_featherless_vars(monkeypatch):
    """Adding Featherless support must not change openai-path behavior."""
    from backend.ai.providers.factory import UnavailableProvider as _Unavailable

    monkeypatch.setenv("SENTINEL_AI_PROVIDER", "openai")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    monkeypatch.setenv("FEATHERLESS_API_KEY", "test-key-not-real")  # present but irrelevant when provider=openai
    provider = build_provider()
    assert isinstance(provider, _Unavailable)
