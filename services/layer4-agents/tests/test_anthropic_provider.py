from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

from layer4_agents.services.anthropic_provider import AnthropicProvider, get_anthropic_provider
from layer4_agents.services.llm_adapter_interfaces import (
    AdapterError,
    CompletionRequest,
    CompletionResult,
    ErrorCategory,
)


def request() -> CompletionRequest:
    return CompletionRequest(
        model="claude-test",
        messages=[
            {"role": "system", "content": "Be precise."},
            {"role": "system", "content": "Use evidence."},
            {"role": "user", "content": "Summarize."},
        ],
        temperature=0.2,
        max_tokens=256,
    )


def anthropic_response(*blocks, input_tokens: int = 3, output_tokens: int = 5):
    return SimpleNamespace(
        content=list(blocks),
        usage=SimpleNamespace(input_tokens=input_tokens, output_tokens=output_tokens),
    )


def openai_response(
    content: str, *, tool_calls=(), prompt_tokens: int = 2, completion_tokens: int = 4
):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=list(tool_calls)))
        ],
        usage=SimpleNamespace(
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    )


def test_build_messages_extracts_and_combines_system_prompts() -> None:
    system, messages = AnthropicProvider()._build_anthropic_messages(request().messages)

    assert system == "Be precise.\nUse evidence."
    assert messages == [{"role": "user", "content": "Summarize."}]


@pytest.mark.parametrize(
    ("message", "category", "code", "retryable"),
    [
        ("request timeout", ErrorCategory.TIMEOUT, "anthropic_timeout", True),
        ("rate limit exceeded", ErrorCategory.RATE_LIMIT, "anthropic_rate_limited", True),
        ("authentication failed", ErrorCategory.AUTH, "anthropic_auth_error", False),
        ("invalid request", ErrorCategory.INVALID_REQUEST, "anthropic_bad_request", False),
        ("provider exploded", ErrorCategory.PROVIDER, "anthropic_error", False),
    ],
)
def test_normalize_error(message: str, category: ErrorCategory, code: str, retryable: bool) -> None:
    result = AnthropicProvider()._normalize_error(RuntimeError(message))

    assert result == AdapterError(category, code, retryable=retryable)


@pytest.mark.asyncio
@pytest.mark.parametrize("shape", ["messages", "chat", "direct"])
async def test_create_message_supports_provider_client_shapes(shape: str) -> None:
    calls: list[dict] = []

    async def create(**kwargs):
        calls.append(kwargs)
        return "response"

    provider = AnthropicProvider()
    if shape == "messages":
        provider._client = SimpleNamespace(messages=SimpleNamespace(create=create))
    elif shape == "chat":
        provider._client = SimpleNamespace(
            chat=SimpleNamespace(completions=SimpleNamespace(create=create))
        )
    else:
        provider._client = SimpleNamespace(create=create)

    assert await provider._create_message(model="claude") == "response"
    assert calls == [{"model": "claude"}]


def test_response_helpers_support_anthropic_and_openai_shapes() -> None:
    anthropic = anthropic_response(SimpleNamespace(type="text", text="anthropic"))
    openai = openai_response("openai")

    assert AnthropicProvider._response_text(anthropic) == "anthropic"
    assert AnthropicProvider._response_text(openai) == "openai"
    assert AnthropicProvider._response_text(SimpleNamespace(), "fallback") == "fallback"
    assert AnthropicProvider._response_usage(anthropic) == {
        "prompt_tokens": 3,
        "completion_tokens": 5,
    }
    assert AnthropicProvider._response_usage(openai) == {
        "prompt_tokens": 2,
        "completion_tokens": 4,
    }
    assert AnthropicProvider._response_usage(SimpleNamespace()) == {
        "prompt_tokens": 0,
        "completion_tokens": 0,
    }


@pytest.mark.asyncio
async def test_complete_builds_request_and_strips_response() -> None:
    provider = AnthropicProvider()
    calls = []

    async def create(**kwargs):
        calls.append(kwargs)
        return anthropic_response(SimpleNamespace(type="text", text="  answer  "))

    provider._create_message = create

    result = await provider.complete(request())

    assert result == CompletionResult(content="answer")
    assert calls[0]["system"] == "Be precise.\nUse evidence."
    assert calls[0]["messages"] == [{"role": "user", "content": "Summarize."}]


@pytest.mark.asyncio
async def test_complete_normalizes_provider_error() -> None:
    provider = AnthropicProvider()

    async def create(**kwargs):
        raise RuntimeError("rate limit exceeded")

    provider._create_message = create
    result = await provider.complete(request())

    assert isinstance(result, AdapterError)
    assert result.category is ErrorCategory.RATE_LIMIT


@pytest.mark.asyncio
async def test_complete_propagates_cancellation() -> None:
    provider = AnthropicProvider()

    async def create(**kwargs):
        raise asyncio.CancelledError

    provider._create_message = create
    with pytest.raises(asyncio.CancelledError):
        await provider.complete(request())


@pytest.mark.asyncio
async def test_complete_text_preserves_usage() -> None:
    provider = AnthropicProvider()

    async def create(**kwargs):
        return anthropic_response(SimpleNamespace(type="text", text=" answer "))

    provider._create_message = create
    result = await provider.complete_text(
        model="claude-test", messages=request().messages, temperature=0.1, max_tokens=None
    )

    assert result.content == "answer"
    assert result.usage.prompt_tokens == 3
    assert result.usage.completion_tokens == 5


@pytest.mark.asyncio
async def test_embed_explains_unsupported_capability() -> None:
    with pytest.raises(NotImplementedError, match="does not provide a native embedding API"):
        await AnthropicProvider().embed(model="embed", text="value")


@pytest.mark.asyncio
async def test_complete_with_tools_normalizes_anthropic_blocks() -> None:
    provider = AnthropicProvider()
    calls = []

    async def create(**kwargs):
        calls.append(kwargs)
        return anthropic_response(
            SimpleNamespace(type="text", text="Use the result."),
            SimpleNamespace(type="tool_use", id="call-1", name="lookup", input={"id": 7}),
        )

    provider._create_message = create
    result = await provider.complete_with_tools(
        request(),
        [
            {
                "type": "function",
                "function": {
                    "name": "lookup",
                    "description": "Lookup evidence",
                    "parameters": {"type": "object"},
                },
            }
        ],
    )

    assert isinstance(result, CompletionResult)
    assert result.content == "Use the result."
    assert result.tool_calls[0].name == "lookup"
    assert result.tool_calls[0].arguments_json == '{"id": 7}'
    assert calls[0]["tools"][0]["input_schema"] == {"type": "object"}


@pytest.mark.asyncio
async def test_complete_with_tools_normalizes_openai_shape() -> None:
    provider = AnthropicProvider()
    tool_call = SimpleNamespace(
        id="call-2",
        function=SimpleNamespace(name="lookup", arguments='{"id":8}'),
    )

    async def create(**kwargs):
        return openai_response("OpenAI-compatible", tool_calls=[tool_call])

    provider._create_message = create
    result = await provider.complete_with_tools(request(), [{"name": "lookup"}])

    assert isinstance(result, CompletionResult)
    assert result.content == "OpenAI-compatible"
    assert result.tool_calls[0].arguments_json == '{"id":8}'


@pytest.mark.asyncio
async def test_complete_with_tools_normalizes_errors_and_cancellation() -> None:
    provider = AnthropicProvider()

    async def failed(**kwargs):
        raise RuntimeError("bad request")

    provider._create_message = failed
    result = await provider.complete_with_tools(request(), [])
    assert isinstance(result, AdapterError)
    assert result.category is ErrorCategory.INVALID_REQUEST

    async def cancelled(**kwargs):
        raise asyncio.CancelledError

    provider._create_message = cancelled
    with pytest.raises(asyncio.CancelledError):
        await provider.complete_with_tools(request(), [])


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("content", "expected"),
    [
        ('{"score": 9}', {"score": 9}),
        ('```json\n{"score": 9}\n```', {"score": 9}),
        ('```\n{"score": 9}\n```', {"score": 9}),
    ],
)
async def test_extract_structured_accepts_json_and_code_fences(
    content: str, expected: dict
) -> None:
    provider = AnthropicProvider()

    async def create(**kwargs):
        assert "matching this schema" in kwargs["system"]
        return anthropic_response(SimpleNamespace(type="text", text=content))

    provider._create_message = create
    assert (
        await provider.extract_structured(
            request(), schema={"type": "object", "properties": {"score": {"type": "integer"}}}
        )
        == expected
    )


@pytest.mark.asyncio
async def test_extract_structured_rejects_non_object_and_invalid_json() -> None:
    provider = AnthropicProvider()

    async def array_response(**kwargs):
        return anthropic_response(SimpleNamespace(type="text", text="[]"))

    provider._create_message = array_response
    result = await provider.extract_structured(request(), schema={"type": "object"})
    assert isinstance(result, AdapterError)
    assert result.category is ErrorCategory.INVALID_REQUEST

    async def invalid_response(**kwargs):
        return anthropic_response(SimpleNamespace(type="text", text="not-json"))

    provider._create_message = invalid_response
    result = await provider.extract_structured(request(), schema={"type": "object"})
    assert isinstance(result, AdapterError)


@pytest.mark.asyncio
async def test_extract_structured_propagates_cancellation() -> None:
    provider = AnthropicProvider()

    async def create(**kwargs):
        raise asyncio.CancelledError

    provider._create_message = create
    with pytest.raises(asyncio.CancelledError):
        await provider.extract_structured(request(), schema={})


def test_get_anthropic_provider_uses_environment_precedence(monkeypatch) -> None:
    monkeypatch.setenv("ANTHROPIC_API_KEY", "env-key")
    monkeypatch.setenv("ANTHROPIC_BASE_URL", "https://env.example")
    monkeypatch.setenv("LAYER4_ANTHROPIC_TIMEOUT_SECONDS", "12.5")

    provider = get_anthropic_provider(
        {
            "anthropic_api_key": "config-key",
            "anthropic_base_url": "https://config.example",
            "anthropic_timeout_seconds": "30",
        }
    )

    assert provider._api_key == "env-key"
    assert provider._base_url == "https://env.example"
    assert provider._timeout == 12.5


def test_get_client_constructs_and_caches_anthropic_client(monkeypatch) -> None:
    created = []

    def client(**kwargs):
        created.append(kwargs)
        return SimpleNamespace()

    monkeypatch.setitem(sys.modules, "anthropic", SimpleNamespace(AsyncAnthropic=client))
    provider = AnthropicProvider(api_key="key", base_url="https://anthropic.example", timeout=7)

    first = provider._get_client()
    second = provider._get_client()

    assert first is second
    assert created == [{"api_key": "key", "timeout": 7, "base_url": "https://anthropic.example"}]
