from __future__ import annotations

"""Thesys C1 provider adapter for Layer 4 LLM orchestration.

Implements the CompletionAdapter and LLMProvider protocols for Thesys C1,
providing governed streaming and non-streaming text completion with prompt
safety checks, error normalization, timeout handling, and telemetry.
"""

import asyncio
import json
import logging
import os
import time
from collections.abc import AsyncIterator
from typing import Any

import httpx
from value_fabric.shared.llm_safety import PromptGuard

from .llm_adapter_interfaces import (
    AdapterError,
    CompletionAdapter,
    CompletionRequest,
    CompletionResult,
    ErrorCategory,
    LLMEmbeddingResponse,
    LLMTextResponse,
    LLMUsage,
)

logger = logging.getLogger(__name__)

THESYS_API_KEY: str = os.getenv("THESYS_API_KEY", "")
THESYS_BASE_URL: str = os.getenv(
    "THESYS_BASE_URL", "https://api.thesys.dev/v1/embed"
)


class ThesysProvider(CompletionAdapter):
    """Thesys C1 API-backed provider adapter."""

    def __init__(
        self,
        *,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout: float = 60.0,
    ) -> None:
        if api_key is not None:
            self._api_key = api_key
        else:
            self._api_key = os.getenv("THESYS_API_KEY", "") or THESYS_API_KEY
        if base_url is not None:
            self._base_url = base_url
        else:
            self._base_url = os.getenv("THESYS_BASE_URL", "") or THESYS_BASE_URL or "https://api.thesys.dev/v1/embed"
        self._timeout = timeout

    def is_configured(self) -> bool:
        """Check if Thesys API key is configured."""
        return bool(self._api_key and self._api_key.strip())

    def is_available(self) -> bool:
        """Alias for is_configured."""
        return self.is_configured()

    def _get_headers(self, accept: str = "application/json") -> dict[str, str]:
        auth = self._api_key.strip() if self._api_key else ""
        if auth and not auth.startswith("Bearer "):
            auth = f"Bearer {auth}"
        return {
            "Authorization": auth,
            "Content-Type": "application/json",
            "Accept": accept,
        }

    def _normalize_error(self, exc: Exception) -> AdapterError:
        """Normalize exceptions to Layer 4 standard AdapterError."""
        msg = str(exc)
        lowered = msg.lower()
        logger.error("thesys_provider_error", exc_info=exc)
        if "prompt injection" in lowered or "injection" in lowered:
            return AdapterError(ErrorCategory.INVALID_REQUEST, "thesys_prompt_injection", retryable=False)
        if isinstance(exc, httpx.TimeoutException) or "timeout" in lowered:
            return AdapterError(ErrorCategory.TIMEOUT, "thesys_timeout", retryable=True)
        if isinstance(exc, httpx.ConnectError) or "connect" in lowered:
            return AdapterError(ErrorCategory.TRANSIENT, "thesys_connect_error", retryable=True)
        if "401" in lowered or "403" in lowered or "unauthorized" in lowered or "forbidden" in lowered:
            return AdapterError(ErrorCategory.AUTH, "thesys_auth_error", retryable=False)
        if "429" in lowered or "rate" in lowered and "limit" in lowered:
            return AdapterError(ErrorCategory.RATE_LIMIT, "thesys_rate_limited", retryable=True)
        if "400" in lowered or "bad request" in lowered or "invalid" in lowered:
            return AdapterError(ErrorCategory.INVALID_REQUEST, "thesys_bad_request", retryable=False)
        return AdapterError(ErrorCategory.PROVIDER, "thesys_error", retryable=False)

    def _scan_messages(self, messages: list[dict[str, Any]], tenant_id: str | None = None) -> bool:
        """Scan messages for prompt injection using PromptGuard.
        
        Returns True if safe, False if injection detected.
        """
        guard = PromptGuard(fail_closed=False)
        for msg in messages:
            if not isinstance(msg, dict) or msg.get("role") == "system":
                continue
            content = msg.get("content")
            if isinstance(content, str) and content.strip():
                result = guard.check(content, context={"tenant_id": tenant_id, "provider": "thesys"})
                if result.is_injection:
                    logger.warning(
                        "Prompt injection detected in Thesys C1 payload",
                        extra={"tenant_id": tenant_id, "risk_score": getattr(result, "risk_score", None)},
                    )
                    return False
        return True

    async def complete_text(
        self,
        *,
        model: str = "thesys-c1",
        messages: list[dict[str, str]],
        temperature: float = 0.3,
        max_tokens: int | None = None,
        response_format: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> LLMTextResponse:
        """Execute a non-streaming text completion against Thesys C1."""
        if not self.is_configured():
            raise RuntimeError("Thesys C1 integration is not configured. Set THESYS_API_KEY.")

        if not self._scan_messages(messages, tenant_id=tenant_id):
            raise ValueError("Prompt injection detected in input messages")

        meta = dict(metadata or {})
        if user_id and "user_id" not in meta:
            meta["user_id"] = user_id
        if trace_id and "trace_id" not in meta:
            meta["trace_id"] = trace_id
        if run_id and "run_id" not in meta:
            meta["run_id"] = run_id

        payload: dict[str, Any] = {
            "messages": messages,
            "stream": False,
            "metadata": meta,
        }
        if temperature is not None:
            payload["temperature"] = temperature
        if max_tokens is not None:
            payload["max_tokens"] = max_tokens

        prompt_chars = sum(len(m.get("content", "")) for m in messages if isinstance(m, dict))
        estimated_prompt_tokens = max(1, prompt_chars // 4)

        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=10.0)
            ) as client:
                response = await client.post(
                    self._base_url,
                    json=payload,
                    headers=self._get_headers(),
                )
                response.raise_for_status()
                data = response.json()

            content = ""
            if isinstance(data, dict):
                content = (
                    data.get("content", "")
                    or data.get("choices", [{}])[0].get("message", {}).get("content", "")
                    or data.get("text", "")
                )
            elif isinstance(data, str):
                content = data
            else:
                content = str(data)

            completion_tokens = max(1, len(content) // 4) if content else 0
            usage = LLMUsage(
                prompt_tokens=estimated_prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=estimated_prompt_tokens + completion_tokens,
            )
            return LLMTextResponse(content=content, usage=usage)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.error("Thesys complete_text failed: %s", exc, exc_info=True)
            raise

    async def complete(self, request: CompletionRequest) -> CompletionResult | AdapterError:
        """CompletionAdapter protocol implementation."""
        try:
            res = await self.complete_text(
                model=request.model,
                messages=request.messages,
                temperature=request.temperature,
                max_tokens=request.max_tokens,
            )
            return CompletionResult(content=res.content)
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            return self._normalize_error(exc)

    async def embed(self, *, model: str, text: str) -> LLMEmbeddingResponse:
        """Thesys does not provide an embedding API."""
        raise NotImplementedError("Thesys C1 does not provide a native embedding API")

    async def stream_c1_chunks(
        self,
        *,
        messages: list[dict[str, Any]],
        business_case_id: str | None = None,
        business_case_data: dict[str, Any] | None = None,
        metadata: dict[str, Any] | None = None,
        tenant_id: str | None = None,
        user_id: str | None = None,
        trace_id: str | None = None,
        run_id: str | None = None,
    ) -> AsyncIterator[str]:
        """Stream chunks from Thesys C1 as SSE strings with governance checks."""
        if not self.is_configured():
            yield f"data: {json.dumps({'type': 'error', 'error': 'Thesys C1 integration is not configured. Set THESYS_API_KEY.'})}\n\n"
            return

        if not self._scan_messages(messages, tenant_id=tenant_id):
            yield f"data: {json.dumps({'type': 'error', 'error': 'Prompt injection detected in input messages'})}\n\n"
            return

        meta = dict(metadata or {})
        if business_case_id is not None:
            meta["business_case_id"] = business_case_id
        elif "business_case_id" not in meta:
            meta["business_case_id"] = "default"
        if business_case_data:
            meta.update(business_case_data)

        payload = {
            "messages": messages,
            "stream": True,
            "metadata": meta,
        }

        t0 = time.monotonic()
        chunk_count = 0
        try:
            async with httpx.AsyncClient(
                timeout=httpx.Timeout(self._timeout, connect=10.0)
            ) as client:
                async with client.stream(
                    "POST",
                    self._base_url,
                    json=payload,
                    headers=self._get_headers(accept="text/event-stream"),
                ) as upstream:
                    if upstream.status_code != 200:
                        body = await upstream.aread()
                        error_msg = body.decode("utf-8", errors="replace")
                        logger.warning(
                            "Thesys API returned %s: %s",
                            upstream.status_code,
                            error_msg[:500],
                            extra={
                                "tenant_id": tenant_id,
                                "status_code": upstream.status_code,
                                "trace_id": trace_id,
                            },
                        )
                        yield f"data: {json.dumps({'type': 'error', 'error': f'Thesys API error ({upstream.status_code})'})}\n\n"
                        return

                    async for line in upstream.aiter_lines():
                        if not line.strip():
                            continue
                        chunk_count += 1
                        yield f"{line}\n\n"

            elapsed_ms = (time.monotonic() - t0) * 1000
            logger.info(
                "Thesys C1 stream completed",
                extra={
                    "tenant_id": tenant_id,
                    "chunks": chunk_count,
                    "elapsed_ms": round(elapsed_ms, 2),
                    "trace_id": trace_id,
                },
            )
            yield f"data: {json.dumps({'type': 'done'})}\n\n"
        except httpx.ConnectError:
            logger.exception("Failed to connect to Thesys API at %s", self._base_url)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Unable to reach Thesys API'})}\n\n"
        except httpx.TimeoutException:
            logger.exception("Thesys API request timed out")
            yield f"data: {json.dumps({'type': 'error', 'error': 'Thesys API request timed out'})}\n\n"
        except asyncio.CancelledError:
            logger.info("Thesys C1 stream cancelled by client", extra={"tenant_id": tenant_id, "trace_id": trace_id})
            raise
        except Exception as exc:
            logger.exception("Unexpected error while streaming from Thesys API: %s", exc)
            yield f"data: {json.dumps({'type': 'error', 'error': 'Internal streaming error'})}\n\n"
