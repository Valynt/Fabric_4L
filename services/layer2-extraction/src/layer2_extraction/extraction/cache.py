"""Content-hash-based LLM response cache for Layer 2 extraction.

Uses Redis when available, with an in-memory LRU fallback for local dev.
"""

from __future__ import annotations

import hashlib
import logging
import os
import pickle
from collections import OrderedDict
from typing import Any

LLM_CACHE_TTL_SECONDS = int(os.getenv("LLM_CACHE_TTL_SECONDS", "3600"))

logger = logging.getLogger(__name__)

try:
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - optional dependency fallback
    RedisError = Exception


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


class ExtractionCache:
    """Cache for LLM extraction responses keyed by content hash.

    Cache key = SHA256(content + model + temperature + extraction_type + endpoint)
    """

    def __init__(self, redis_url: str | None = None, default_ttl: int = LLM_CACHE_TTL_SECONDS) -> None:
        self._redis = None
        self._fallback: _InMemoryLRUCache | None = _InMemoryLRUCache()
        self._default_ttl = default_ttl

        redis_url = redis_url or os.getenv("REDIS_URL")
        if redis_url:
            try:
                import redis.asyncio as aioredis
                self._redis = aioredis.from_url(redis_url, decode_responses=False)
            except (ImportError, RedisError) as exc:
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
            except (ValueError, TypeError, OSError) as exc:
                logger.exception(
                    "Unexpected cache initialization failure; using in-memory fallback",
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
        logger.warning(
            "Cache operation failed; continuing without cache",
            exc_info=exc,
            extra={
                "operation": operation,
                "tenant_id": context.get("tenant_id"),
                "job_id": context.get("job_id"),
                "correlation_id": context.get("correlation_id"),
                "exception_class": type(exc).__name__,
            },
        )

    def _make_key(
        self,
        text: str,
        endpoint: str,
        model: str | None = None,
        temperature: float | None = None,
    ) -> str:
        model = model or os.getenv("EXTRACTION_MODEL", "gpt-4o-mini")
        temperature = temperature if temperature is not None else 0.0
        payload = f"{text}:{model}:{temperature}:{endpoint}"
        return f"l2_cache:{hashlib.sha256(payload.encode()).hexdigest()}"

    async def get(
        self,
        text: str,
        endpoint: str,
        model: str | None = None,
        temperature: float | None = None,
        context: dict[str, str | None] | None = None,
    ) -> Any | None:
        key = self._make_key(text, endpoint, model, temperature)
        if self._redis is not None:
            try:
                raw = await self._redis.get(key)
                if raw:
                    return pickle.loads(raw)
            except RedisError as exc:
                self._log_cache_failure("read", exc, context)
            except (pickle.UnpicklingError, AttributeError, EOFError, ValueError, TypeError) as exc:
                self._log_cache_failure("read", exc, context)
            except (RuntimeError, OSError) as exc:
                self._log_cache_failure("read", exc, context)
        if self._fallback is not None:
            return self._fallback.get(key)
        return None

    async def set(
        self,
        text: str,
        endpoint: str,
        value: Any,
        model: str | None = None,
        temperature: float | None = None,
        ttl: int | None = None,
        context: dict[str, str | None] | None = None,
    ) -> None:
        key = self._make_key(text, endpoint, model, temperature)
        ttl = ttl or self._default_ttl
        if self._redis is not None:
            try:
                await self._redis.setex(key, ttl, pickle.dumps(value))
                return
            except RedisError as exc:
                self._log_cache_failure("write", exc, context)
            except (pickle.PickleError, TypeError, AttributeError, ValueError) as exc:
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
