"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: aiocache-backed implementation of the stable CachePort contract.

The adapter is intentionally non-default for OSS-1.  It mirrors the current
RedisCache logical behavior at the CachePort boundary while avoiding direct
application imports of aiocache.
"""

from __future__ import annotations

import fnmatch
import json
import logging
import os
from typing import Any

try:
    from aiocache import Cache
except ModuleNotFoundError:  # pragma: no cover - exercised by import-only suites
    Cache = None

from .redis_cache import CacheConfig, RedisCache_get_statsResult

logger = logging.getLogger(__name__)

# Security: Disable pickle serializer to prevent code injection attacks
PICKLE_DISABLED_ERROR = "pickle serializer is disabled for security — use json or msgpack"


class AiocacheCacheAdapter:
    """CachePort-compatible adapter backed by an aiocache cache instance."""

    provider_name = "aiocache"
    _NON_PROD_ENVS = {"development", "dev", "local", "test", "testing", "ci", "debug"}

    def __init__(
        self,
        cache: Any | None = None,
        config: CacheConfig | None = None,
        *,
        namespace: str | None = None,
        allow_memory_fallback: bool = False,
    ) -> None:
        self.config = config or CacheConfig()
        self.namespace = namespace
        # Fail closed by default when no backend is supplied.
        # MEMORY is allowed only with explicit opt-in in non-production-like environments.
        if cache is None:
            env_name = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development").strip().lower()
            if not allow_memory_fallback or env_name not in self._NON_PROD_ENVS:
                raise ValueError(
                    "AiocacheCacheAdapter requires an explicit cache backend. "
                    "MEMORY fallback is disabled by default; it can only be enabled with "
                    "allow_memory_fallback=True in local/test/debug environments."
                )
            logger.warning(
                "No aiocache backend provided; using in-memory fallback for non-production environment '%s'.",
                env_name,
            )
        if cache is None and Cache is None:
            raise ImportError(
                "aiocache is required when AiocacheCacheAdapter is constructed "
                "without an explicit cache backend"
            )
        self._cache = cache or Cache(Cache.MEMORY, namespace=namespace)
        # _known_keys tracks keys set through this adapter instance only.
        # LIMITATION: This becomes stale if keys expire via TTL, are deleted externally,
        # or in multi-process/container deployments. clear_pattern will miss such keys.
        self._known_keys: set[str] = set()
        self._hits = 0
        self._misses = 0
        self._commands = 0

    def _make_key(self, key: str) -> str:
        return f"{self.config.key_prefix}{key}"

    def _ttl(self, ttl: int | None = None) -> int:
        cache_ttl = ttl or self.config.default_ttl
        return min(cache_ttl, self.config.max_ttl)

    def _serialize(self, value: Any) -> str:
        if self.config.serializer == "pickle":
            raise ValueError(PICKLE_DISABLED_ERROR)
        return json.dumps(value, default=str)

    def _deserialize(self, value: Any) -> Any:
        if value is None:
            return None
        if self.config.serializer == "pickle":
            raise ValueError(PICKLE_DISABLED_ERROR)
        if isinstance(value, bytes):
            value = value.decode("utf-8")
        if isinstance(value, str):
            try:
                return json.loads(value)
            except json.JSONDecodeError as exc:
                logger.warning("Failed to deserialize cached value as JSON: %s", exc)
                return None
        return value

    async def close(self) -> None:
        """Close backend resources when the selected aiocache backend supports it."""

        close = getattr(self._cache, "close", None)
        if close is not None:
            await close()

    async def get(self, key: str) -> Any | None:
        self._commands += 1
        try:
            value = await self._cache.get(self._make_key(key))
            if value is None:
                self._misses += 1
                return None
            self._hits += 1
            return self._deserialize(value)
        except Exception as exc:  # pragma: no cover - defensive parity behavior
            logger.warning("aiocache get error for key %s: %s", key, exc)
            self._misses += 1
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        self._commands += 1
        try:
            prefixed_key = self._make_key(key)
            await self._cache.set(prefixed_key, self._serialize(value), ttl=self._ttl(ttl))
            self._known_keys.add(prefixed_key)
            return True
        except Exception as exc:  # pragma: no cover - defensive parity behavior
            logger.warning("aiocache set error for key %s: %s", key, exc)
            return False

    async def delete(self, key: str) -> bool:
        self._commands += 1
        try:
            prefixed_key = self._make_key(key)
            deleted = await self._cache.delete(prefixed_key)
            self._known_keys.discard(prefixed_key)
            return deleted > 0
        except Exception as exc:  # pragma: no cover - defensive parity behavior
            logger.warning("aiocache delete error for key %s: %s", key, exc)
            return False

    async def clear_pattern(self, pattern: str) -> int:
        self._commands += 1
        prefixed_pattern = self._make_key(pattern)
        # NOTE: This only clears keys tracked in _known_keys (set through this adapter).
        # Keys expired via TTL, deleted externally, or in other processes will be missed.
        # For production use with pattern clearing, use Redis backend with native pattern support.
        matching_keys = [key for key in self._known_keys if fnmatch.fnmatch(key, prefixed_pattern)]
        deleted = 0
        for prefixed_key in matching_keys:
            try:
                result = await self._cache.delete(prefixed_key)
                if result > 0:
                    deleted += 1
                self._known_keys.discard(prefixed_key)
            except Exception as exc:  # pragma: no cover - defensive parity behavior
                logger.warning("aiocache clear-pattern error for key %s: %s", prefixed_key, exc)
        return deleted

    async def exists(self, key: str) -> bool:
        self._commands += 1
        try:
            return bool(await self._cache.exists(self._make_key(key)))
        except Exception as exc:  # pragma: no cover - defensive parity behavior
            logger.warning("aiocache exists error for key %s: %s", key, exc)
            return False

    async def increment(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        self._commands += 1
        prefixed_key = self._make_key(key)
        
        # Try to use aiocache's atomic increment if backend supports it
        increment_fn = getattr(self._cache, 'increment', None)
        if increment_fn is not None:
            try:
                # aiocache's increment returns the new value directly
                result = await increment_fn(prefixed_key, amount, ttl=self._ttl(ttl))
                self._known_keys.add(prefixed_key)
                return result
            except Exception as exc:
                logger.warning("aiocache atomic increment failed for key %s, falling back to read-modify-write: %s", key, exc)
        
        # Fallback: read-modify-write (NOT atomic - has race condition)
        # WARNING: This fallback is NOT safe for production use in multi-worker deployments.
        # Concurrent increments will lose updates. Use Redis backend with atomic increment for production.
        logger.warning("Using non-atomic increment fallback for key %s - this is NOT safe for production", key)
        raw_current = await self._cache.get(prefixed_key)
        current = self._deserialize(raw_current) if raw_current is not None else 0
        try:
            next_value = int(current or 0) + amount
        except (ValueError, TypeError) as exc:
            logger.warning("Cannot increment non-numeric cached value %r for key %s: %s. Resetting to %d.", current, key, exc, amount)
            next_value = amount
        await self._cache.set(prefixed_key, self._serialize(next_value), ttl=self._ttl(ttl))
        self._known_keys.add(prefixed_key)
        return next_value

    async def get_stats(self) -> dict[str, Any]:
        self._commands += 1
        # Return only metrics that are accurately tracked by this adapter.
        # Omit connected_clients and used_memory as they don't apply to MEMORY backend
        # and would be misleading if hardcoded.
        return RedisCache_get_statsResult.model_validate(
            {
                "connected_clients": None,
                "used_memory": None,
                "used_memory_human": None,
                "keyspace_hits": self._hits,
                "keyspace_misses": self._misses,
                "total_commands_processed": self._commands,
            }
        )
