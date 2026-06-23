from __future__ import annotations

from types import SimpleNamespace

import pytest

from layer4_agents.services.llm_adapter_interfaces import (
    AdapterError,
    CompletionRequest,
    ErrorCategory,
)
from layer4_agents.services.llm_provider import get_provider_adapters


class _FakeCreate:
    def __init__(self, response=None, error: Exception | None = None):
        self._response = response
        self._error = error

    async def create(self, **_: object):
        if self._error is not None:
            raise self._error
        return self._response


class _FakeClient:
    def __init__(self, response=None, error: Exception | None = None):
        self.chat = SimpleNamespace(completions=_FakeCreate(response=response, error=error))


def _tool_call_response() -> object:
    return SimpleNamespace(
        choices=[
            SimpleNamespace(
                message=SimpleNamespace(
                    content="",
                    tool_calls=[
                        SimpleNamespace(
                            id="tc_1",
                            function=SimpleNamespace(name="lookup", arguments='{"q":"acme"}'),
                        )
                    ],
                )
            )
        ]
    )


def _structured_response() -> object:
    return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content='{"status":"ok"}'))])


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", sorted(get_provider_adapters().keys()))
async def test_adapter_structured_output_extraction(provider_name: str) -> None:
    adapter = get_provider_adapters()[provider_name]
    adapter._client = _FakeClient(response=_structured_response())
    result = await adapter.extract_structured(
        CompletionRequest(model="gpt-test", messages=[{"role": "user", "content": "x"}]),
        schema={"name": "x", "schema": {"type": "object"}},
    )
    assert result == {"status": "ok"}


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", sorted(get_provider_adapters().keys()))
async def test_adapter_tool_call_representation(provider_name: str) -> None:
    adapter = get_provider_adapters()[provider_name]
    adapter._client = _FakeClient(response=_tool_call_response())
    result = await adapter.complete_with_tools(
        CompletionRequest(model="gpt-test", messages=[{"role": "user", "content": "x"}]),
        tools=[{"type": "function", "function": {"name": "lookup", "parameters": {"type": "object"}}}],
    )
    assert not isinstance(result, AdapterError)
    assert result.tool_calls[0].name == "lookup"
    assert result.tool_calls[0].arguments_json == '{"q":"acme"}'


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", sorted(get_provider_adapters().keys()))
async def test_adapter_retry_timeout_semantics(provider_name: str) -> None:
    adapter = get_provider_adapters()[provider_name]
    adapter._client = _FakeClient(error=TimeoutError("request timeout"))
    result = await adapter.complete(
        CompletionRequest(
            model="gpt-test",
            messages=[{"role": "user", "content": "x"}],
        )
    )
    assert isinstance(result, AdapterError)
    assert result.category is ErrorCategory.TIMEOUT
    assert result.retryable is True


@pytest.mark.asyncio
@pytest.mark.parametrize("provider_name", sorted(get_provider_adapters().keys()))
async def test_adapter_error_normalization(provider_name: str) -> None:
    adapter = get_provider_adapters()[provider_name]
    adapter._client = _FakeClient(error=RuntimeError("rate limit exceeded"))
    result = await adapter.complete(
        CompletionRequest(model="gpt-test", messages=[{"role": "user", "content": "x"}])
    )
    assert isinstance(result, AdapterError)
    assert result.category is ErrorCategory.RATE_LIMIT
    assert result.retryable is True
