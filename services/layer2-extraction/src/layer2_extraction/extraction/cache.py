"""Content-hash-based LLM response cache for Layer 2 extraction.

Uses Redis when available, with an in-memory LRU fallback for local dev.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
from collections import OrderedDict
from typing import Any

from pydantic import BaseModel, Field, JsonValue, ValidationError

from layer2_extraction.metrics import get_metrics

LLM_CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL_SECONDS", "3600"))
CACHE_FORMAT_VERSION: int = 1

logger = logging.getLogger(__name__)

try:
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - optional dependency fallback
    RedisError = Exception

_REDIS_ERRORS = (RedisError,)


class ExtractionCacheEnvelope(BaseModel):
    """Safe serialization envelope for Layer 2 extraction cache entries."""

    version: int = Field(default=CACHE_FORMAT_VERSION)
    tenant_id: str
    endpoint: str
    data: JsonValue


class _InMemoryLRUCache:
    """Thread-safe-ish in-memory LRU cache with TTL emulation."""

    def __init__(self, maxsize: int = 1000):
        self._store: OrderedDict[str, Any] = OrderedDict()
        self._maxsize = maxsize

    def get(self, key: str) -> Any | None:
        if key in self._store:
            self._store.move_to_end(key)
            return self._store[key]
        return None

    def set(self, key: str, value: Any) -> None:
        if key in self._store:
            self._store.move_to_end(key)
        self._store[key] = value
        while len(self._store) > self._maxsize:
            self._store.popitem(last=False)


class _Unset:
    """Sentinel distinguishing "redis_url not supplied" from "redis_url explicitly None"."""


_UNSET: _Unset = _Unset()


class ExtractionCache:
    """Cache for LLM extraction responses keyed by content hash.

    Cache key = SHA256(content + model + temperature + extraction_type + endpoint)
    """

    def __init__(
        self,
        redis_url: str | None | _Unset = _UNSET,
        default_ttl: int = LLM_CACHE_TTL_SECONDS,
    ) -> None:
        self._redis = None
        self._fallback: _InMemoryLRUCache | None = _InMemoryLRUCache()
        self._default_ttl = default_ttl

        if redis_url is _UNSET:
            redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(redis_url, decode_responses=False)
            except (ImportError,) + _REDIS_ERRORS as exc:
                logger.warning(
                    "Cache backend unavailable; falling back to in-memory cache",
                    extra={
                        "operation": "connect",
                        "tenant_id": None,
                        "job_id": None,
                        "correlation_id": None,
                        "exception_class": type(exc).__name__,
                    },
                )

    @staticmethod
    def _log_cache_failure(operation: str, exc: Exception, context: dict[str, str | None] | None = None) -> None:
        context = context or {}
        tenant_id = context.get("tenant_id") or ""  # Use empty string as fallback for metrics

        is_decode_failure = isinstance(
            exc,
            (ValidationError, ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError, AttributeError, EOFError),
        )

        # Always record metrics even without tenant context for observability
        metrics = get_metrics()
        if metrics:
            metrics.record_cache_failure(
                failure_type="decode" if is_decode_failure else "corruption",
                tenant_id=tenant_id,
                ingestion_id=context.get("ingestion_id", ""),
                extraction_job_id=context.get("extraction_job_id") or context.get("job_id") or "",
                model_version=context.get("model_version", ""),
                schema_version=context.get("schema_version", ""),
                value_pack_id=context.get("value_pack_id", ""),
                operation=operation,
            )

        # For decode/validation failures, omit exc_info to prevent logging sensitive cached payloads
        # present in ValidationError representations or JSONDecodeError context.
        logger.warning(
            "Cache operation failed; continuing without cache",
            exc_info=None if is_decode_failure else exc,
            extra={
                "operation": operation,
                "tenant_id": tenant_id or None,  # Use None in logs if empty
                "job_id": context.get("job_id"),
                "correlation_id": context.get("correlation_id"),
                "exception_class": type(exc).__name__,
            },
        )

    def _make_key(
        self,
        tenant_id: str,
        source_hash: str,
        extraction_version: str,
        value_pack_id: str,
        endpoint: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        model = model or os.getenv("EXTRACTION_MODEL", "gpt-4o-mini")
        temperature = temperature if temperature is not None else 0.0
        payload = json.dumps(
            [tenant_id, source_hash, extraction_version, value_pack_id, model, str(temperature), endpoint],
            separators=(",", ":"),
        )
        return f"l2_cache:{hashlib.sha256(payload.encode()).hexdigest()}"

    async def get(
        self,
        tenant_id: str,
        source_hash: str,
        extraction_version: str,
        value_pack_id: str,
        endpoint: str,
        model: str | None = None,
        temperature: float | None = None,
        context: dict[str, str | None] | None = None,
    ) -> Any | None:
        if not tenant_id:
            raise ValueError("tenant_id is required for cache operations")
        key = self._make_key(
            tenant_id,
            source_hash,
            extraction_version,
            value_pack_id,
            endpoint,
            model,
            temperature,
        )
        if self._redis is not None:
            try:
                raw = await self._redis.get(key)
                if raw:
                    if isinstance(raw, bytes):
                        raw_str = raw.decode("utf-8")
                    elif isinstance(raw, str):
                        raw_str = raw
                    else:
                        raise ValueError(f"Unexpected cache entry type: {type(raw).__name__}")
                    envelope = ExtractionCacheEnvelope.model_validate_json(raw_str)
                    if envelope.version != CACHE_FORMAT_VERSION:
                        raise ValueError(f"Unsupported cache envelope version: {envelope.version}")
                    if envelope.tenant_id != tenant_id:
                        raise ValueError(f"Tenant mismatch in cache envelope: expected {tenant_id}, got {envelope.tenant_id}")
                    return envelope.data
            except RedisError as exc:
                self._log_cache_failure("read", exc, context)
            except (ValidationError, ValueError, TypeError, json.JSONDecodeError, UnicodeDecodeError) as exc:
                self._log_cache_failure("read", exc, context)
            except (RuntimeError, OSError) as exc:
                self._log_cache_failure("read", exc, context)
        if self._fallback is not None:
            return self._fallback.get(key)
        return None

    async def set(
        self,
        tenant_id: str,
        source_hash: str,
        extraction_version: str,
        value_pack_id: str,
        endpoint: str,
        value: Any,
        model: str | None = None,
        temperature: float | None = None,
        ttl: int | None = None,
        context: dict[str, str | None] | None = None,
    ) -> None:
        if not tenant_id:
            raise ValueError("tenant_id is required for cache operations")
        key = self._make_key(tenant_id, source_hash, extraction_version, value_pack_id, endpoint, model, temperature)
        ttl = ttl or self._default_ttl
        if self._redis is not None:
            try:
                envelope = ExtractionCacheEnvelope(
                    version=CACHE_FORMAT_VERSION,
                    tenant_id=tenant_id,
                    endpoint=endpoint,
                    data=value,
                )
                serialized = envelope.model_dump_json().encode("utf-8")
                await self._redis.setex(key, ttl, serialized)
                return
            except RedisError as exc:
                self._log_cache_failure("write", exc, context)
            except (ValidationError, TypeError, AttributeError, ValueError) as exc:
                self._log_cache_failure("write", exc, context)
            except (RuntimeError, OSError) as exc:
                self._log_cache_failure("write", exc, context)
        if self._fallback is not None:
            self._fallback.set(key, value)

    async def close(self) -> None:
        if self._redis is not None:
            try:
                await self._redis.close()
            except RedisError as exc:
                self._log_cache_failure("invalidate", exc)
            except (RuntimeError, OSError) as exc:
                self._log_cache_failure("invalidate", exc)
