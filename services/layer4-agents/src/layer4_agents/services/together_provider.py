from __future__ import annotations

"""Together.ai LLM provider.

Uses the OpenAI-compatible API at https://api.together.ai/v1.
Drop-in replacement for OpenAIProvider — implements the same LLMProvider
protocol plus StructuredOutputAdapter and ToolCallingAdapter.

Together.ai does not support OpenAI's ``response_format: json_schema`` mode.
``extract_structured`` falls back to prompt-level JSON instruction + manual
parse, which is sufficient for all Layer 4 extraction prompts.
"""
import asyncio
import json
import logging
from typing import Any

from .llm_adapter_interfaces import (
    AdapterError,
    CompletionRequest,
    CompletionResult,
    ErrorCategory,
    StructuredOutputAdapter,
    ToolCall,
    ToolCallingAdapter,
)
from .llm_output_parser import parse_llm_json
from .llm_provider import LLMEmbeddingResponse, LLMTextResponse, LLMUsage

logger = logging.getLogger(__name__)

_TOGETHER_BASE_URL = "https://api.together.ai/v1"

# Default model for each task type — overridden by harness.runtime.yaml
_DEFAULT_MODELS: dict[str, str] = {
    "reasoning": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "extraction": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "narrative": "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "embedding": "togethercomputer/m2-bert-80M-8k-retrieval",
}

# Together.ai models that support response_format={"type": "json_object"}.
# Models not in this set receive JSON instructions via the prompt only.
# Source: https://docs.together.ai/docs/json-mode
_JSON_MODE_SUPPORTED_MODELS: frozenset[str] = frozenset({
    "meta-llama/Llama-3.3-70B-Instruct-Turbo",
    "meta-llama/Llama-3.1-8B-Instruct-Turbo",
    "meta-llama/Llama-3.1-70B-Instruct-Turbo",
    "meta-llama/Llama-3.1-405B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-8B-Instruct-Turbo",
    "meta-llama/Meta-Llama-3.1-70B-Instruct-Turbo",
    "mistralai/Mixtral-8x7B-Instruct-v0.1",
    "mistralai/Mistral-7B-Instruct-v0.3",
    "Qwen/Qwen2.5-72B-Instruct-Turbo",
})


def _is_400_error(exc: Exception) -> bool:
    """Detect 400/BadRequest across different exception wrappers."""
    status = getattr(exc, "status_code", None)
    if status == 400:
        return True
    response = getattr(exc, "response", None)
    if response is not None:
        status = getattr(response, "status_code", None)
        if status == 400:
            return True
    # Safe text fallback for wrappers that don't expose status_code
    return "400" in str(exc)  # ban-str-e-allow: error-classification


class TogetherAIProvider(StructuredOutputAdapter, ToolCallingAdapter):
    """Together.ai-backed provider using the OpenAI-compatible API."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str = _TOGETHER_BASE_URL,
        timeout: float = 60.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout
        self._client: Any | None = None

    # ------------------------------------------------------------------
    # Client lifecycle
    # ------------------------------------------------------------------

    def _get_client(self) -> Any:
        if self._client is None:
            from openai import AsyncOpenAI

            self._client = AsyncOpenAI(
                api_key=self._api_key,
                base_url=self._base_url,
                timeout=self._timeout,
            )
        return self._client

    # ------------------------------------------------------------------
    # LLMProvider protocol
    # ------------------------------------------------------------------

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
        # Together.ai supports {"type": "json_object"} only for models in the allowlist.
        # Callers that need JSON should use extract_structured() instead.
        if response_format is not None and response_format.get("type") == "json_object":
            if model in _JSON_MODE_SUPPORTED_MODELS:
                kwargs["response_format"] = response_format
            else:
                logger.debug(
                    "Skipping json_object response_format for unsupported model %s", model
                )

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
        return LLMEmbeddingResponse(embedding=response.data[0].embedding)

    # ------------------------------------------------------------------
    # StructuredOutputAdapter
    # ------------------------------------------------------------------

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
        except Exception as exc:
            return self._normalize_error(exc)

    async def extract_structured(
        self,
        request: CompletionRequest,
        *,
        schema: dict[str, Any],
    ) -> dict[str, Any] | AdapterError:
        """Extract structured JSON from Together.ai.

        Together.ai does not support OpenAI's ``json_schema`` response format.
        We instruct the model to return JSON via the prompt and parse the
        response manually, extracting the first valid JSON object/array found.
        """
        # Append a JSON instruction to the last user message
        messages = list(request.messages)
        schema_hint = json.dumps(schema.get("schema", schema), indent=2)
        json_instruction = (
            f"\n\nRespond with valid JSON only. "
            f"Your response must conform to this schema:\n{schema_hint}"
        )
        if messages and messages[-1].get("role") == "user":
            messages[-1] = {
                **messages[-1],
                "content": messages[-1]["content"] + json_instruction,
            }
        else:
            messages.append({"role": "user", "content": json_instruction})

        # Only request json_object mode for models known to support it.
        # For unsupported models the JSON instruction in the prompt is sufficient.
        use_json_mode = request.model in _JSON_MODE_SUPPORTED_MODELS

        kwargs: dict[str, Any] = {
            "model": request.model,
            "messages": messages,
            "temperature": request.temperature,
        }
        if request.max_tokens:
            kwargs["max_tokens"] = request.max_tokens
        if use_json_mode:
            kwargs["response_format"] = {"type": "json_object"}

        try:
            response = await self._get_client().chat.completions.create(**kwargs)
            content = (response.choices[0].message.content or "{}").strip()
            return parse_llm_json(content, call_site="together_provider.extract_structured")
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            # If json_object mode caused a 400, retry without it
            if use_json_mode and _is_400_error(exc):
                logger.warning(
                    "json_object mode rejected for model %s, retrying without it",
                    request.model,
                )
                kwargs.pop("response_format", None)
                try:
                    response = await self._get_client().chat.completions.create(**kwargs)
                    content = (response.choices[0].message.content or "{}").strip()
                    return parse_llm_json(content, call_site="together_provider.extract_structured_retry")
                except asyncio.CancelledError:
                    raise
                except Exception as retry_exc:
                    return self._normalize_error(retry_exc)
            return self._normalize_error(exc)

    # ------------------------------------------------------------------
    # ToolCallingAdapter
    # ------------------------------------------------------------------

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
            return CompletionResult(
                content=(message.content or "").strip(),
                tool_calls=tool_calls,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return self._normalize_error(exc)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    # _parse_json_response removed — use parse_llm_json (services.llm_output_parser) per §2.5

    def _normalize_error(self, exc: Exception) -> AdapterError:
        msg = str(exc)  # ban-str-e-allow: error-classification
        lowered = msg.lower()
        if "timeout" in lowered:
            return AdapterError(ErrorCategory.TIMEOUT, "provider_timeout", retryable=True)
        if "rate" in lowered and "limit" in lowered:
            return AdapterError(ErrorCategory.RATE_LIMIT, "provider_rate_limited", retryable=True)
        if "401" in msg or "unauthorized" in lowered:
            return AdapterError(ErrorCategory.AUTH, "provider_auth_failed", retryable=False)
        return AdapterError(ErrorCategory.PROVIDER, "provider_error", retryable=False)
