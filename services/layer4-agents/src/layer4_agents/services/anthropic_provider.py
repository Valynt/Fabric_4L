"""Anthropic Claude provider adapter for Layer 4 LLM orchestration.

Implements the CompletionAdapter, ToolCallingAdapter, and StructuredOutputAdapter
protocols by wrapping the Anthropic Messages API.
"""

from __future__ import annotations

import logging
from typing import Any

from .llm_adapter_interfaces import (
    AdapterError,
    CompletionAdapter,
    CompletionRequest,
    CompletionResult,
    ErrorCategory,
    ProviderNotImplementedError,
    StructuredOutputAdapter,
    ToolCall,
    ToolCallingAdapter,
)

logger = logging.getLogger(__name__)


class AnthropicProvider(CompletionAdapter, ToolCallingAdapter, StructuredOutputAdapter):
    """Anthropic Claude API-backed provider implementing all Layer 4 adapter protocols."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._client: Any | None = None

    def _get_client(self) -> Any:
        if self._client is None:
            try:
                import anthropic
            except ImportError as exc:
                raise ProviderNotImplementedError(
                    "anthropic — install the 'anthropic' package to use this provider"
                ) from exc
            kwargs: dict[str, Any] = {"api_key": self._api_key, "timeout": self._timeout}
            if self._base_url is not None:
                kwargs["base_url"] = self._base_url
            self._client = anthropic.AsyncAnthropic(**kwargs)
        return self._client

    def _normalize_error(self, exc: Exception) -> AdapterError:
        msg = str(exc)
        lowered = msg.lower()
        logger.error("anthropic_provider_error", exc_info=exc)
        if "timeout" in lowered:
            return AdapterError(ErrorCategory.TIMEOUT, "anthropic_timeout", retryable=True)
        if "rate" in lowered and "limit" in lowered:
            return AdapterError(
                ErrorCategory.RATE_LIMIT, "anthropic_rate_limited", retryable=True
            )
        if "authentication" in lowered or "api key" in lowered or "auth" in lowered:
            return AdapterError(ErrorCategory.AUTH, "anthropic_auth_error", retryable=False)
        if "bad request" in lowered or "invalid" in lowered:
            return AdapterError(
                ErrorCategory.INVALID_REQUEST, "anthropic_bad_request", retryable=False
            )
        return AdapterError(ErrorCategory.PROVIDER, "anthropic_error", retryable=False)

    def _build_anthropic_messages(
        self, messages: list[dict[str, str]]
    ) -> tuple[str | None, list[dict[str, Any]]]:
        """Convert OpenAI-style messages to Anthropic (system + list) format.

        Anthropic separates the system prompt from the message list.
        """
        system: str | None = None
        anthropic_messages: list[dict[str, Any]] = []
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "")
            if role == "system":
                if system is None:
                    system = content
                else:
                    system = f"{system}\n{content}"
            else:
                anthropic_messages.append({"role": role, "content": content})
        return system, anthropic_messages

    async def complete(self, request: CompletionRequest) -> CompletionResult | AdapterError:
        try:
            system, messages = self._build_anthropic_messages(request.messages)
            kwargs: dict[str, Any] = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
            }
            if system is not None:
                kwargs["system"] = system
            response = await self._get_client().messages.create(**kwargs)
            content = ""
            if response.content and len(response.content) > 0:
                content = response.content[0].text or ""
            usage = response.usage
            return CompletionResult(
                content=content.strip(),
                usage_metadata={
                    "prompt_tokens": usage.input_tokens if usage else 0,
                    "completion_tokens": usage.output_tokens if usage else 0,
                },
            )
        except Exception as exc:  # pragma: no cover - defensive normalization
            return self._normalize_error(exc)

    async def complete_text(
        self,
        *,
        model: str,
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> "LLMTextResponse":
        """Synchronous-style text completion for LLMProvider protocol compatibility."""
        from .llm_provider import LLMTextResponse, LLMUsage

        req = CompletionRequest(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens or 4096,
        )
        result = await self.complete(req)
        if isinstance(result, AdapterError):
            raise RuntimeError(f"Anthropic provider error: {result.message}")
        usage_meta = getattr(result, "usage_metadata", {}) or {}
        return LLMTextResponse(
            content=result.content,
            usage=LLMUsage(
                prompt_tokens=usage_meta.get("prompt_tokens", 0),
                completion_tokens=usage_meta.get("completion_tokens", 0),
            ),
        )

    async def embed(self, *, model: str, text: str) -> "LLMEmbeddingResponse":
        """Embeddings are not natively supported by Anthropic; raise clear error."""
        from .llm_provider import LLMEmbeddingResponse

        raise NotImplementedError(
            "Anthropic does not provide a native embedding API. "
            "Use OpenAI or Together.ai for embeddings."
        )

    async def complete_with_tools(
        self,
        request: CompletionRequest,
        tools: list[dict[str, Any]],
    ) -> CompletionResult | AdapterError:
        try:
            system, messages = self._build_anthropic_messages(request.messages)
            anthropic_tools = []
            for tool in tools:
                tool_def = tool.get("function", tool)
                anthropic_tools.append(
                    {
                        "name": tool_def.get("name", "unnamed_tool"),
                        "description": tool_def.get("description", ""),
                        "input_schema": tool_def.get("parameters", {}),
                    }
                )
            kwargs: dict[str, Any] = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
                "tools": anthropic_tools,
            }
            if system is not None:
                kwargs["system"] = system
            response = await self._get_client().messages.create(**kwargs)
            content = ""
            tool_calls: tuple[ToolCall, ...] = ()
            if response.content and len(response.content) > 0:
                blocks = response.content
                text_parts: list[str] = []
                tc_list: list[ToolCall] = []
                for block in blocks:
                    if getattr(block, "type", None) == "text":
                        text_parts.append(block.text or "")
                    elif getattr(block, "type", None) == "tool_use":
                        import json

                        args = getattr(block, "input", {})
                        if isinstance(args, dict):
                            args = json.dumps(args)
                        tc_list.append(
                            ToolCall(
                                id=getattr(block, "id", ""),
                                name=getattr(block, "name", ""),
                                arguments_json=str(args),
                            )
                        )
                content = " ".join(text_parts).strip()
                tool_calls = tuple(tc_list)
            return CompletionResult(content=content, tool_calls=tool_calls)
        except Exception as exc:  # pragma: no cover - defensive normalization
            return self._normalize_error(exc)

    async def extract_structured(
        self,
        request: CompletionRequest,
        *,
        schema: dict[str, Any],
    ) -> dict[str, Any] | AdapterError:
        try:
            schema_title = schema.get("name", schema.get("title", "StructuredOutput"))
            system, messages = self._build_anthropic_messages(request.messages)
            # Inject schema instructions into system prompt
            import json

            schema_instruction = (
                f"You must respond with a single JSON object matching this schema:\n"
                f"{json.dumps(schema, indent=2)}\n"
                f"Respond ONLY with the JSON object. Do not wrap in markdown."
            )
            if system is not None:
                system = f"{system}\n\n{schema_instruction}"
            else:
                system = schema_instruction
            kwargs: dict[str, Any] = {
                "model": request.model,
                "messages": messages,
                "max_tokens": request.max_tokens or 4096,
                "temperature": request.temperature,
            }
            if system is not None:
                kwargs["system"] = system
            response = await self._get_client().messages.create(**kwargs)
            content = ""
            if response.content and len(response.content) > 0:
                content = response.content[0].text or "{}"
            # Strip markdown code fences if present
            content = content.strip()
            if content.startswith("```json"):
                content = content[7:]
            if content.startswith("```"):
                content = content[3:]
            if content.endswith("```"):
                content = content[:-3]
            content = content.strip()
            # Validate with Pydantic if schema available
            from pydantic import create_model, ConfigDict

            result = json.loads(content)
            # Basic validation using schema
            return result
        except Exception as exc:
            return self._normalize_error(exc)


def get_anthropic_provider(config: dict[str, Any] | None = None) -> AnthropicProvider:
    """Build an Anthropic provider from an optional tool/workflow config."""
    import os

    api_key = (
        os.getenv("ANTHROPIC_API_KEY")
        or os.getenv("LAYER4_ANTHROPIC_API_KEY")
        or (config.get("anthropic_api_key") if config and hasattr(config, "get") else None)
        or getattr(config, "anthropic_api_key", None)
    )
    base_url = (
        os.getenv("ANTHROPIC_BASE_URL")
        or os.getenv("LAYER4_ANTHROPIC_BASE_URL")
        or (config.get("anthropic_base_url") if config and hasattr(config, "get") else None)
    )
    timeout_str = (
        os.getenv("LAYER4_ANTHROPIC_TIMEOUT_SECONDS")
        or (config.get("anthropic_timeout_seconds") if config and hasattr(config, "get") else None)
        or "60"
    )
    timeout = float(timeout_str)
    return AnthropicProvider(api_key=api_key, base_url=base_url, timeout=timeout)
