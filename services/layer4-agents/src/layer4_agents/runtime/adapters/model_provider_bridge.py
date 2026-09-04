"""Bridge legacy LLM providers behind the runtime ``ModelProviderPort``.

The legacy ``layer4_agents.services`` providers expose ``complete_text``
(keyword-only, ``dict`` messages) and ``embed`` (single ``text``). This adapter
maps the runtime ``Message``/``ModelConfig`` contracts onto those shapes and
wraps ``LLMTextResponse``/``LLMEmbeddingResponse`` results into the canonical
runtime ``ModelResponse``/``list[list[float]]`` types, so the execution spine
stays provider-agnostic. Provider-specific behavior (e.g. Anthropic/Thesys
raising ``NotImplementedError`` for embeddings) propagates unchanged and is
the caller's configuration concern.
"""

from __future__ import annotations

from typing import Any

from ...services.llm_adapter_interfaces import LLMEmbeddingResponse, LLMTextResponse
from ...services.llm_provider import LLMProvider
from ..errors import TenantRequiredError
from ..models import Message, ModelConfig, ModelResponse, RuntimeContext
from ..ports import ModelProviderPort


class ModelProviderBridge(ModelProviderPort):
    """Adapt a legacy ``LLMProvider`` onto the runtime ``ModelProviderPort``."""

    def __init__(self, provider_name: str, provider: LLMProvider) -> None:
        self._provider_name = provider_name
        self._provider = provider

    @property
    def provider_name(self) -> str:
        """Canonical provider name for registry lookup and observability labels."""
        return self._provider_name

    async def complete(
        self, messages: list[Message], config: ModelConfig, ctx: RuntimeContext
    ) -> ModelResponse:
        """Generate a completion, mapping runtime messages/config to the legacy shape."""
        self._require_tenant(ctx)
        legacy_messages = [self._to_legacy_message(m) for m in messages]
        kwargs = self._completion_kwargs(config)
        response: LLMTextResponse = await self._provider.complete_text(
            messages=legacy_messages, **kwargs
        )
        return self._to_model_response(response)

    async def embed(
        self, texts: list[str], config: ModelConfig, ctx: RuntimeContext
    ) -> list[list[float]]:
        """Return one embedding vector per input text.

        Legacy providers embed a single text per call, so this loops the input
        and concatenates results in order. Providers without a native embedding
        API (Anthropic, Thesys) raise ``NotImplementedError``, which propagates.
        """
        self._require_tenant(ctx)
        vectors: list[list[float]] = []
        for text in texts:
            response: LLMEmbeddingResponse = await self._provider.embed(
                model=config.model, text=text
            )
            vectors.extend(response.embeddings)
        return vectors

    def _require_tenant(self, ctx: RuntimeContext) -> None:
        if not ctx.tenant_id:
            raise TenantRequiredError()

    @staticmethod
    def _to_legacy_message(message: Message) -> dict[str, str]:
        legacy: dict[str, str] = {"role": message.role, "content": message.content}
        if message.name is not None:
            legacy["name"] = message.name
        if message.tool_call_id is not None:
            legacy["tool_call_id"] = message.tool_call_id
        return legacy

    @staticmethod
    def _completion_kwargs(config: ModelConfig) -> dict[str, Any]:
        kwargs: dict[str, Any] = {
            "model": config.model,
            "temperature": config.temperature if config.temperature is not None else 0.3,
        }
        if config.max_tokens is not None:
            kwargs["max_tokens"] = config.max_tokens
        extra = config.extra or {}
        if extra.get("response_format") is not None:
            kwargs["response_format"] = extra["response_format"]
        return kwargs

    @staticmethod
    def _to_model_response(response: LLMTextResponse) -> ModelResponse:
        usage = response.usage
        total = usage.total_tokens or (usage.prompt_tokens + usage.completion_tokens)
        return ModelResponse(
            content=response.content,
            usage={
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": total,
            },
        )
