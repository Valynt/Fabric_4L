from __future__ import annotations

import asyncio
import sys
from types import SimpleNamespace

import pytest

from layer4_agents.services.llm_adapter_interfaces import (
    AdapterError,
    CompletionRequest,
    CompletionResult,
    ErrorCategory,
)
from layer4_agents.services.llm_intent_classifier import LLMIntentClassifier
from layer4_agents.services.llm_provider import (
    OpenAIProvider,
    UnknownLLMProviderError,
    get_llm_provider,
    get_openai_provider,
    get_provider_adapters,
)
from layer4_agents.services.together_provider import TogetherAIProvider, _is_400_error


def request(*, model: str = "model") -> CompletionRequest:
    return CompletionRequest(
        model=model,
        messages=[{"role": "user", "content": "classify this"}],
        temperature=0.2,
        max_tokens=32,
    )


def response(content: str = " result ", *, usage=True, tool_calls=()):
    return SimpleNamespace(
        choices=[
            SimpleNamespace(message=SimpleNamespace(content=content, tool_calls=list(tool_calls)))
        ],
        usage=(SimpleNamespace(prompt_tokens=3, completion_tokens=5) if usage else None),
    )


class FakeCompletions:
    def __init__(self, outcomes):
        self.outcomes = list(outcomes)
        self.calls = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, BaseException):
            raise outcome
        return outcome


class FakeClient:
    def __init__(self, outcomes):
        self.chat = SimpleNamespace(completions=FakeCompletions(outcomes))
        self.embeddings = SimpleNamespace(create=self.create_embedding)
        self.embedding_calls = []

    async def create_embedding(self, **kwargs):
        self.embedding_calls.append(kwargs)
        return SimpleNamespace(data=[SimpleNamespace(embedding=[0.1, 0.2])])


@pytest.mark.asyncio
async def test_intent_classifier_uses_governed_client_and_normalizes_result() -> None:
    class Governed:
        async def call_structured(self, **kwargs):
            self.kwargs = kwargs
            return {
                "intent": " VALUE_ANALYSIS ",
                "confidence": 2,
                "entities": {"account": "Acme"},
            }, {"model": "test"}

    governed = Governed()
    result = await LLMIntentClassifier(governed_client=governed).classify("show ROI")

    assert result.model_dump() == {
        "intent": "value_analysis",
        "confidence": 1.0,
        "entities": {"account": "Acme"},
    }
    assert governed.kwargs["call_id"] == "intent_classifier"
    assert governed.kwargs["messages"][-1]["content"] == "show ROI"


@pytest.mark.asyncio
async def test_intent_classifier_uses_adapter_and_parses_json() -> None:
    class Adapter:
        async def complete(self, completion_request):
            self.request = completion_request
            return CompletionResult(
                content='{"intent":"promote_signal","confidence":0.8,"entities":{"signal_id":"s1"}}'
            )

    adapter = Adapter()
    result = await LLMIntentClassifier(model="intent-model", adapter=adapter).classify("promote s1")

    assert result["intent"] == "promote_signal"
    assert adapter.request.model == "intent-model"
    assert adapter.request.retry_policy.max_attempts == 2


@pytest.mark.parametrize(
    ("parsed", "expected"),
    [
        ({"intent": "unknown", "confidence": -2, "entities": []}, ("general_question", 0.0, {})),
        ({}, ("general_question", 0.5, {})),
    ],
)
def test_intent_classifier_validates_untrusted_provider_output(parsed, expected) -> None:
    result = LLMIntentClassifier()._validate_and_build(parsed)
    assert (result["intent"], result["confidence"], result["entities"]) == expected


@pytest.mark.asyncio
async def test_intent_classifier_falls_back_on_adapter_error() -> None:
    class Adapter:
        async def complete(self, _request):
            return AdapterError(ErrorCategory.PROVIDER, "failed", False)

    result = await LLMIntentClassifier(adapter=Adapter()).classify("anything")
    assert result.model_dump() == {
        "intent": "general_question",
        "confidence": 0.5,
        "entities": {},
    }


@pytest.mark.asyncio
async def test_intent_classifier_propagates_cancellation() -> None:
    class Adapter:
        async def complete(self, _request):
            raise asyncio.CancelledError

    with pytest.raises(asyncio.CancelledError):
        await LLMIntentClassifier(adapter=Adapter()).classify("anything")


def test_intent_classifier_resolves_and_caches_default_provider(monkeypatch) -> None:
    sentinel = object()
    monkeypatch.setattr(
        "layer4_agents.services.llm_provider.get_llm_provider", lambda config: sentinel
    )
    classifier = LLMIntentClassifier(api_key="secret")
    assert classifier._get_default_adapter() is sentinel
    assert classifier._get_default_adapter() is sentinel


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (SimpleNamespace(status_code=400), True),
        (SimpleNamespace(response=SimpleNamespace(status_code=400)), True),
        (RuntimeError("HTTP 400 bad request"), True),
        (RuntimeError("HTTP 500"), False),
    ],
)
def test_together_detects_bad_request_shapes(exc, expected) -> None:
    if not isinstance(exc, Exception):
        exc = type("ProviderError", (Exception,), vars(exc))("failure")
    assert _is_400_error(exc) is expected


@pytest.mark.asyncio
async def test_together_text_embedding_and_complete_contracts() -> None:
    client = FakeClient([response(), response("complete")])
    provider = TogetherAIProvider()
    provider._client = client

    text = await provider.complete_text(
        model="unsupported",
        messages=request().messages,
        max_tokens=10,
        response_format={"type": "json_object"},
    )
    embedding = await provider.embed(model="embed", text="value")
    completed = await provider.complete(request())

    assert text.content == "result"
    assert text.usage.prompt_tokens == 3
    assert "response_format" not in client.chat.completions.calls[0]
    assert embedding.embeddings == [[0.1, 0.2]]
    assert completed == CompletionResult(content="complete")


@pytest.mark.asyncio
async def test_together_supported_json_mode_is_forwarded() -> None:
    model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    client = FakeClient([response("{}", usage=False)])
    provider = TogetherAIProvider()
    provider._client = client
    await provider.complete_text(
        model=model, messages=request().messages, response_format={"type": "json_object"}
    )
    assert client.chat.completions.calls[0]["response_format"] == {"type": "json_object"}


@pytest.mark.asyncio
async def test_together_structured_appends_instruction_without_mutating_input() -> None:
    original = [{"role": "system", "content": "system"}]
    client = FakeClient([response('{"score": 3}')])
    provider = TogetherAIProvider()
    provider._client = client
    result = await provider.extract_structured(
        CompletionRequest(model="unsupported", messages=original),
        schema={"type": "object", "properties": {"score": {"type": "integer"}}},
    )
    assert result == {"score": 3}
    assert original == [{"role": "system", "content": "system"}]
    assert (
        "Respond with valid JSON only"
        in client.chat.completions.calls[0]["messages"][-1]["content"]
    )


@pytest.mark.asyncio
async def test_together_structured_retries_rejected_json_mode() -> None:
    model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    bad = type("BadRequest", (Exception,), {"status_code": 400})("bad")
    client = FakeClient([bad, response('{"ok": true}')])
    provider = TogetherAIProvider()
    provider._client = client
    result = await provider.extract_structured(request(model=model), schema={"type": "object"})
    assert result == {"ok": True}
    assert "response_format" in client.chat.completions.calls[0]
    assert "response_format" not in client.chat.completions.calls[1]


@pytest.mark.asyncio
async def test_together_structured_normalizes_retry_failure() -> None:
    model = "meta-llama/Llama-3.3-70B-Instruct-Turbo"
    bad = type("BadRequest", (Exception,), {"status_code": 400})("bad")
    provider = TogetherAIProvider()
    provider._client = FakeClient([bad, RuntimeError("timeout")])
    result = await provider.extract_structured(request(model=model), schema={})
    assert result == AdapterError(ErrorCategory.TIMEOUT, "provider_timeout", True)


@pytest.mark.asyncio
async def test_together_tool_calls_and_errors() -> None:
    call = SimpleNamespace(
        id="call-1", function=SimpleNamespace(name="lookup", arguments='{"id":1}')
    )
    provider = TogetherAIProvider()
    provider._client = FakeClient(
        [response(" done ", tool_calls=[call]), RuntimeError("rate limit")]
    )
    result = await provider.complete_with_tools(request(), [{"type": "function"}])
    error = await provider.complete_with_tools(request(), [])
    assert result.content == "done"
    assert result.tool_calls[0].name == "lookup"
    assert error == AdapterError(ErrorCategory.RATE_LIMIT, "provider_rate_limited", True)


@pytest.mark.parametrize(
    ("message", "category", "retryable"),
    [
        ("timeout", ErrorCategory.TIMEOUT, True),
        ("rate limit", ErrorCategory.RATE_LIMIT, True),
        ("401 unauthorized", ErrorCategory.AUTH, False),
        ("bad gateway", ErrorCategory.PROVIDER, False),
    ],
)
def test_together_normalizes_safe_errors(message, category, retryable) -> None:
    result = TogetherAIProvider()._normalize_error(RuntimeError(message))
    assert (result.category, result.retryable) == (category, retryable)


def test_together_client_is_lazy_and_cached(monkeypatch) -> None:
    created = []

    def client(**kwargs):
        created.append(kwargs)
        return object()

    monkeypatch.setitem(sys.modules, "openai", SimpleNamespace(AsyncOpenAI=client))
    provider = TogetherAIProvider(api_key="key", base_url="https://example", timeout=7)
    assert provider._get_client() is provider._get_client()
    assert created == [{"api_key": "key", "base_url": "https://example", "timeout": 7}]


@pytest.mark.asyncio
async def test_openai_provider_text_embedding_tools_and_structured() -> None:
    tool_call = SimpleNamespace(id="call", function=SimpleNamespace(name="lookup", arguments="{}"))
    client = FakeClient(
        [
            response(" text "),
            response(" tool ", tool_calls=[tool_call]),
            response('{"name":"Acme","score":2}'),
        ]
    )
    provider = OpenAIProvider()
    provider._client = client
    text = await provider.complete_text(
        model="m", messages=[], max_tokens=3, response_format={"type": "json_object"}
    )
    embedding = await provider.embed(model="e", text="x")
    tools = await provider.complete_with_tools(request(), [])
    structured = await provider.extract_structured(
        request(),
        schema={
            "name": "Result",
            "schema": {
                "title": "Result",
                "type": "object",
                "properties": {"name": {"type": "string"}, "score": {"type": "integer"}},
                "required": ["name", "score"],
            },
        },
    )
    assert text.content == "text"
    assert embedding.embeddings == [[0.1, 0.2]]
    assert tools.tool_calls[0].name == "lookup"
    assert structured["name"] == "Acme"


@pytest.mark.parametrize(
    ("schema", "value"),
    [
        ({"type": "string", "enum": ["a", "b"]}, "a"),
        ({"type": "number"}, 1.2),
        ({"type": "boolean"}, True),
        ({"type": "array", "items": {"type": "integer"}}, [1]),
        ({"type": "object", "properties": {"x": {"type": "string"}}}, {"x": "ok"}),
        ({"type": "unknown"}, object()),
    ],
)
def test_openai_schema_type_resolution(schema, value) -> None:
    resolved = OpenAIProvider()._resolve_schema_type(schema)
    if schema["type"] != "unknown":
        assert resolved is not None
        assert value is not None


def test_provider_factories_respect_config_and_environment(monkeypatch) -> None:
    assert get_openai_provider({"openai_api_key": "key"})._api_key == "key"
    assert get_openai_provider(SimpleNamespace(openai_api_key="attr"))._api_key == "attr"
    monkeypatch.setenv("LAYER4_LLM_PROVIDER", "together")
    monkeypatch.setenv("LAYER4_TOGETHER_API_KEY", "together-key")
    monkeypatch.setenv("LAYER4_TOGETHER_BASE_URL", "https://together")
    monkeypatch.setenv("LAYER4_TOGETHER_TIMEOUT_SECONDS", "9")
    together = get_llm_provider({})
    assert (together._api_key, together._base_url, together._timeout) == (
        "together-key",
        "https://together",
        9.0,
    )
    monkeypatch.setenv("LAYER4_LLM_PROVIDER", "openai")
    assert isinstance(get_llm_provider({}), OpenAIProvider)


def test_provider_registry_and_unknown_provider_fails_closed(monkeypatch) -> None:
    adapters = get_provider_adapters({})
    assert {"openai", "anthropic"} <= adapters.keys()
    monkeypatch.setenv("LAYER4_LLM_PROVIDER", "unknown")
    with pytest.raises(UnknownLLMProviderError, match="Unsupported LLM provider"):
        get_llm_provider({"together_api_key": "must-not-be-used"})


@pytest.mark.parametrize("provider_cls", [OpenAIProvider, TogetherAIProvider])
@pytest.mark.asyncio
async def test_provider_operations_propagate_cancellation(provider_cls) -> None:
    provider = provider_cls()
    provider._client = FakeClient([asyncio.CancelledError()])
    with pytest.raises(asyncio.CancelledError):
        await provider.complete(request())
