from __future__ import annotations

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Cache ports for OSS-0 substitution scaffolding.

The port expresses Fabric's cache contract without exposing Redis-specific APIs. The
legacy adapter delegates to the current RedisCache implementation so runtime defaults
remain unchanged while future OSS-backed adapters can be tested against the same
interface.
"""


from typing import Any, Protocol, runtime_checkable

from ..cache.redis_cache import RedisCache


@runtime_checkable
class CachePort(Protocol):
    """Application-owned cache contract used for OSS-backed parity tests."""

    async def get(self, key: str) -> Any | None:
        """Return a cached value, or ``None`` on misses and safe cache failures."""

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Store a value and return whether the write succeeded."""

    async def delete(self, key: str) -> bool:
        """Delete a key and return whether deletion succeeded."""

    async def clear_pattern(self, pattern: str) -> int:
        """Delete keys matching a pattern and return the number deleted."""

    async def exists(self, key: str) -> bool:
        """Return whether a key exists."""

    async def increment(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        """Increment a numeric key by ``amount`` and return its new value."""

    async def get_stats(self) -> dict[str, Any]:
        """Return implementation statistics in the current operational shape."""


class LegacyCacheAdapter:
    """CachePort adapter around the existing RedisCache implementation."""

    def __init__(self, cache: RedisCache) -> None:
        self._cache = cache

    async def get(self, key: str) -> Any | None:
        return await self._cache.get(key)

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        return await self._cache.set(key, value, ttl)

    async def delete(self, key: str) -> bool:
        return await self._cache.delete(key)

    async def clear_pattern(self, pattern: str) -> int:
        return await self._cache.clear_pattern(pattern)

    async def exists(self, key: str) -> bool:
        return await self._cache.exists(key)

    async def increment(self, key: str, amount: int = 1, ttl: int | None = None) -> int:
        return await self._cache.increment(key, amount, ttl)

    async def get_stats(self) -> dict[str, Any]:
        return await self._cache.get_stats()


def as_cache_port(cache: RedisCache) -> CachePort:
    """Return the legacy cache through the stable CachePort boundary."""

    return LegacyCacheAdapter(cache)
