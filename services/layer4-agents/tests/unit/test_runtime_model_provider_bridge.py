"""Phase 6 tests for the ModelProviderPort provider-adapter bridge and accessor."""

from __future__ import annotations

from typing import Any

import pytest

from layer4_agents.runtime import (
    AgentRuntimeImpl,
    Message,
    ModelConfig,
    ModelResponse,
    ProviderNotFoundError,
    RuntimeContext,
    TenantRequiredError,
)
from layer4_agents.runtime.adapters import ModelProviderBridge
from layer4_agents.runtime.ports import ModelProviderPort
from layer4_agents.services.llm_adapter_interfaces import (
    LLMEmbeddingResponse,
    LLMTextResponse,
    LLMUsage,
)


def _ctx(tenant_id: str = "tenant-a", **overrides: Any) -> RuntimeContext:
    base = {
        "tenant_id": tenant_id,
        "trace_id": "trace-1",
        "run_id": "run-1",
        "workflow_id": "wf-1",
        "workflow_type": "demo",
    }
    base.update(overrides)
    return RuntimeContext(**base)


def _config(**overrides: Any) -> ModelConfig:
    base: dict[str, Any] = {"provider": "openai", "model": "gpt-4o"}
    base.update(overrides)
    return ModelConfig(**base)


class _FakeProvider:
    """Scriptable legacy ``LLMProvider`` double that records its calls."""

    def __init__(self) -> None:
        self.complete_calls: list[dict[str, Any]] = []
        self.embed_calls: list[dict[str, Any]] = []
        self.complete_result: LLMTextResponse = LLMTextResponse(
            content="", usage=LLMUsage()
        )
        self.embed_results: list[list[list[float]]] = []
        self.embed_error: Exception | None = None

    async def complete_text(self, **kwargs: Any) -> LLMTextResponse:
        self.complete_calls.append(kwargs)
        return self.complete_result

    async def embed(self, *, model: str, text: str) -> LLMEmbeddingResponse:
        self.embed_calls.append({"model": model, "text": text})
        if self.embed_error is not None:
            raise self.embed_error
        if self.embed_results:
            return LLMEmbeddingResponse(embeddings=self.embed_results.pop(0))
        return LLMEmbeddingResponse(embeddings=[])


@pytest.mark.unit
def test_bridge_satisfies_model_provider_port() -> None:
    bridge = ModelProviderBridge("openai", _FakeProvider())

    assert isinstance(bridge, ModelProviderPort)
    assert bridge.provider_name == "openai"


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_maps_messages_and_config_to_legacy_shape() -> None:
    provider = _FakeProvider()
    provider.complete_result = LLMTextResponse(
        content="hello", usage=LLMUsage(prompt_tokens=10, completion_tokens=5)
    )
    bridge = ModelProviderBridge("openai", provider)
    messages = [
        Message(role="system", content="You are helpful."),
        Message(role="user", content="hi"),
        Message(role="tool", content="x", name="calc", tool_call_id="call-1"),
    ]
    config = _config(
        temperature=0.7, max_tokens=100, extra={"response_format": {"type": "json_object"}}
    )

    result = await bridge.complete(messages, config, _ctx())

    assert result.content == "hello"
    call = provider.complete_calls[0]
    assert call["model"] == "gpt-4o"
    assert call["temperature"] == 0.7
    assert call["max_tokens"] == 100
    assert call["response_format"] == {"type": "json_object"}
    assert call["messages"] == [
        {"role": "system", "content": "You are helpful."},
        {"role": "user", "content": "hi"},
        {"role": "tool", "content": "x", "name": "calc", "tool_call_id": "call-1"},
    ]


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_wraps_response_and_computes_usage_total() -> None:
    provider = _FakeProvider()
    provider.complete_result = LLMTextResponse(
        content="hello", usage=LLMUsage(prompt_tokens=10, completion_tokens=5)
    )
    bridge = ModelProviderBridge("openai", provider)

    result = await bridge.complete(
        [Message(role="user", content="hi")], _config(temperature=None), _ctx()
    )

    assert isinstance(result, ModelResponse)
    assert result.content == "hello"
    assert result.usage == {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_respects_explicit_usage_total() -> None:
    provider = _FakeProvider()
    provider.complete_result = LLMTextResponse(
        content="hi", usage=LLMUsage(prompt_tokens=1, completion_tokens=1, total_tokens=7)
    )
    bridge = ModelProviderBridge("openai", provider)

    result = await bridge.complete([Message(role="user", content="hi")], _config(), _ctx())

    assert result.usage == {"prompt_tokens": 1, "completion_tokens": 1, "total_tokens": 7}


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_defaults_temperature_when_unset() -> None:
    provider = _FakeProvider()
    bridge = ModelProviderBridge("openai", provider)

    await bridge.complete([Message(role="user", content="hi")], _config(temperature=None), _ctx())

    assert provider.complete_calls[0]["temperature"] == 0.3


@pytest.mark.unit
@pytest.mark.asyncio
async def test_complete_fails_closed_on_missing_tenant() -> None:
    bridge = ModelProviderBridge("openai", _FakeProvider())

    with pytest.raises(TenantRequiredError):
        await bridge.complete(
            [Message(role="user", content="hi")], _config(), _ctx(tenant_id="")
        )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_loops_texts_and_concatenates_vectors_in_order() -> None:
    provider = _FakeProvider()
    provider.embed_results = [[[0.1, 0.2]], [[0.3, 0.4]], [[0.5]]]
    bridge = ModelProviderBridge("together", provider)

    vectors = await bridge.embed(["a", "b", "c"], _config(model="embed-model"), _ctx())

    assert vectors == [[0.1, 0.2], [0.3, 0.4], [0.5]]
    assert [c["text"] for c in provider.embed_calls] == ["a", "b", "c"]
    assert all(c["model"] == "embed-model" for c in provider.embed_calls)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_fails_closed_on_missing_tenant() -> None:
    bridge = ModelProviderBridge("together", _FakeProvider())

    with pytest.raises(TenantRequiredError):
        await bridge.embed(["a"], _config(), _ctx(tenant_id=""))


@pytest.mark.unit
@pytest.mark.asyncio
async def test_embed_propagates_provider_not_implemented() -> None:
    provider = _FakeProvider()
    provider.embed_error = NotImplementedError("no embedding API")
    bridge = ModelProviderBridge("anthropic", provider)

    with pytest.raises(NotImplementedError):
        await bridge.embed(["a"], _config(), _ctx())


@pytest.mark.unit
def test_get_model_provider_returns_registered_provider() -> None:
    runtime = AgentRuntimeImpl()
    bridge = ModelProviderBridge("openai", _FakeProvider())
    runtime.register_model_provider("openai", bridge)

    assert runtime.get_model_provider("openai") is bridge


@pytest.mark.unit
def test_get_model_provider_fails_closed_on_unknown() -> None:
    runtime = AgentRuntimeImpl()

    with pytest.raises(ProviderNotFoundError) as exc:
        runtime.get_model_provider("missing")

    assert exc.value.code == "PROVIDER_NOT_FOUND"
