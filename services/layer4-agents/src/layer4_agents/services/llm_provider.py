from __future__ import annotations

"""Minimal LLM provider abstraction for Layer 4 runtime calls."""
import asyncio
import logging
import os
from typing import Any, Protocol

logger = logging.getLogger(__name__)

SUPPORTED_LLM_PROVIDERS = frozenset({"together", "openai", "anthropic"})


class UnknownLLMProviderError(ValueError):
    """Raised when runtime configuration names an unsupported LLM provider.

    Provider configuration is a deployment contract. Silently substituting a
    different provider can violate tenant residency policy, change cost, and
    make model behavior non-reproducible, so resolution must fail closed.
    """

    def __init__(self, provider_name: str) -> None:
        supported = ", ".join(sorted(SUPPORTED_LLM_PROVIDERS))
        super().__init__(
            f"Unsupported LLM provider {provider_name!r}; expected one of: {supported}"
        )
        self.provider_name = provider_name

from pydantic import ConfigDict, create_model

from .llm_adapter_interfaces import (
    AdapterError,
    CompletionRequest,
    CompletionResult,
    ErrorCategory,
    LLMEmbeddingResponse,
    LLMTextResponse,
    LLMUsage,
    StructuredOutputAdapter,
    ToolCall,
    ToolCallingAdapter,
)


class LLMProvider(Protocol):
    """Provider contract used by workflows and tools."""

    async def complete_text(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMTextResponse:
        """Return a text completion."""

    async def embed(self, *, model: str, text: str) -> LLMEmbeddingResponse:
        """Return an embedding for the given text."""


class OpenAIProvider(StructuredOutputAdapter, ToolCallingAdapter):
    """OpenAI-backed provider implementation."""

    def __init__(self, *, api_key: str | None = None) -> None:
        self._api_key = api_key
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(api_key=self._api_key)
        return self._client

    async def complete_text(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> LLMTextResponse:
        kwargs: dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if response_format is not None:
            kwargs["response_format"] = response_format

        response = await self._get_client().chat.completions.create(**kwargs)
        usage = response.usage
        return LLMTextResponse(
            content=(response.choices[0].message.content or "").strip(),
            usage=LLMUsage(
                prompt_tokens=usage.prompt_tokens if usage else 0,
                completion_tokens=usage.completion_tokens if usage else 0,
            ),
        )

    async def embed(self, *, model: str, text: str) -> LLMEmbeddingResponse:
        response = await self._get_client().embeddings.create(model=model, input=text)
        return LLMEmbeddingResponse(embeddings=[response.data[0].embedding])

    async def complete(self, request: CompletionRequest) -> CompletionResult | AdapterError:
        try:
            result = await self.complete_text(
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            return CompletionResult(content=result.content)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive normalization
            return self._normalize_error(exc)

    async def complete_with_tools(
        self,
        request: CompletionRequest,
        tools: list[dict[str, Any]],
    ) -> CompletionResult | AdapterError:
        try:
            kwargs: dict[str, Any] = {
                "model": request.model,
                "messages": request.messages,
                "temperature": request.temperature,
                "tools": tools,
            }
            if request.max_tokens is not None:
                kwargs["max_tokens"] = request.max_tokens
            response = await self._get_client().chat.completions.create(**kwargs)
            message = response.choices[0].message
            tool_calls = tuple(
                ToolCall(
                    id=call.id,
                    name=call.function.name,
                    arguments_json=call.function.arguments,
                )
                for call in (message.tool_calls or [])
            )
            return CompletionResult(content=(message.content or "").strip(), tool_calls=tool_calls)
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive normalization
            return self._normalize_error(exc)

    def _resolve_schema_type(self, prop: dict[str, Any]) -> type:
        """Map a JSON schema property to a Python type."""
        ptype = prop.get("type", "any")
        if ptype == "string":
            enum = prop.get("enum")
            if enum:
                from typing import Literal
                return Literal[tuple(enum)]
            return str
        elif ptype == "integer":
            return int
        elif ptype == "number":
            return float
        elif ptype == "boolean":
            return bool
        elif ptype == "array":
            items = prop.get("items")
            if isinstance(items, dict):
                item_type = self._resolve_schema_type(items)
                return list[item_type]
            return list
        elif ptype == "object":
            nested = prop.get("properties")
            if isinstance(nested, dict):
                return self._build_model_from_schema(prop)
            return dict
        return Any

    def _build_model_from_schema(self, schema: dict[str, Any]) -> type:
        """Build a minimal Pydantic model from a JSON schema dict for validation."""
        schema_def = schema.get("schema", schema)
        properties = schema_def.get("properties", {})
        required = set(schema_def.get("required", []))

        annotations: dict[str, Any] = {}
        defaults: dict[str, Any] = {}
        for name, prop in properties.items():
            pytype = self._resolve_schema_type(prop)
            annotations[name] = pytype
            if name not in required:
                annotations[name] = pytype | None
                defaults[name] = None

        return create_model(
            schema_def.get("title", "StructuredOutput"),
            __annotations__=annotations,
            __config__=ConfigDict(extra="allow"),
            **defaults,
        )

    async def extract_structured(
        self,
        request: CompletionRequest,
        *,
        schema: dict[str, Any],
    ) -> dict[str, Any] | AdapterError:
        try:
            response = await self._get_client().chat.completions.create(
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                response_format={"type": "json_schema", "json_schema": schema},
            )
            # CONTRACT §2.5: Validate structured LLM output with Pydantic, not raw JSON.parse
            content = response.choices[0].message.content or "{}"
            model_cls = self._build_model_from_schema(schema)
            return model_cls.model_validate_json(content).model_dump()
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # pragma: no cover - defensive normalization
            return self._normalize_error(exc)

    def _normalize_error(self, exc: Exception) -> AdapterError:
        msg = str(exc)  # ban-str-e-allow: error-classification
        lowered = msg.lower()
        logger.error("llm_provider_error", exc_info=exc)
        if "timeout" in lowered:
            return AdapterError(ErrorCategory.TIMEOUT, "provider_timeout", retryable=True)
        if "rate" in lowered and "limit" in lowered:
            return AdapterError(ErrorCategory.RATE_LIMIT, "provider_rate_limited", retryable=True)
        return AdapterError(ErrorCategory.PROVIDER, "provider_error", retryable=False)


def get_openai_provider(config: dict[str, Any] | None = None) -> OpenAIProvider:
    """Build the default OpenAI provider from an optional tool/workflow config."""
    if config is None:
        api_key = None
    elif hasattr(config, "get"):
        api_key = config.get("openai_api_key")
    else:
        api_key = getattr(config, "openai_api_key", None)
    return OpenAIProvider(api_key=api_key)


def get_provider_adapters(config: dict[str, Any] | None = None) -> dict[str, Any]:
    """Registry of configured provider adapters for conformance tests and orchestration wiring."""
    adapters: dict[str, Any] = {"openai": get_openai_provider(config)}
    try:
        from .anthropic_provider import get_anthropic_provider
        adapters["anthropic"] = get_anthropic_provider(config)
    except asyncio.CancelledError:
        raise
    except Exception:
        pass  # anthropic optional
    return adapters


def get_llm_provider(config: dict[str, Any] | None = None) -> Any:
    """Return the active LLM provider based on ``LAYER4_LLM_PROVIDER`` env var.

    Provider resolution order:
    1. ``LAYER4_LLM_PROVIDER`` environment variable
    2. ``config["llm_provider"]`` if present
    3. Default: ``"together"``

    Supported values: ``"together"``, ``"openai"``, ``"anthropic"``

    Returns an instance implementing the ``LLMProvider`` protocol.
    """
    provider_name = (
        os.getenv("LAYER4_LLM_PROVIDER")
        or (config.get("llm_provider") if config and hasattr(config, "get") else None)
        or getattr(config, "llm_provider", None)
        or "together"
    ).strip().lower()

    if provider_name not in SUPPORTED_LLM_PROVIDERS:
        logger.error(
            "llm_provider_configuration_rejected",
            extra={"provider": provider_name, "supported": sorted(SUPPORTED_LLM_PROVIDERS)},
        )
        raise UnknownLLMProviderError(provider_name)

    if provider_name == "together":
        from .together_provider import TogetherAIProvider

        api_key = (
            os.getenv("LAYER4_TOGETHER_API_KEY")
            or (config.get("together_api_key") if config and hasattr(config, "get") else None)
            or getattr(config, "together_api_key", None)
        )
        base_url = (
            os.getenv("LAYER4_TOGETHER_BASE_URL", "https://api.together.ai/v1")
        )
        timeout = float(os.getenv("LAYER4_TOGETHER_TIMEOUT_SECONDS", "60"))
        return TogetherAIProvider(api_key=api_key, base_url=base_url, timeout=timeout)

    if provider_name == "openai":
        return get_openai_provider(config)

    if provider_name == "anthropic":
        from .anthropic_provider import get_anthropic_provider

        return get_anthropic_provider(config)

    raise AssertionError("validated provider dispatch is not exhaustive")
