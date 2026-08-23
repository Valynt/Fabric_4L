"""Simple Redis caching utility for reference data.

Cache Invalidation Strategy:
- This module provides time-based cache invalidation via TTL (Time To Live)
- Cached entries automatically expire after their configured TTL
- For manual invalidation, use the delete() method on the CacheManager
- When applying @cached to functions that access mutable data:
  * Ensure the TTL is shorter than the acceptable staleness window
  * Consider calling cache.delete() after data mutations
  * For tenant-specific data, include tenant_id in the function arguments
    to ensure proper cache key separation

Usage Example:
    @cached(ttl=3600, key_prefix="my_func")
    async def my_function(tenant_id: UUID, param: str):
        # Function will be cached with key including tenant_id and param
        return expensive_computation(tenant_id, param)
"""

import functools
import hashlib
import inspect
import json
import logging
from collections.abc import Callable
from typing import Any, TypeVar

import redis.asyncio as redis

from .config import get_settings

logger = logging.getLogger(__name__)
T = TypeVar("T")


class CacheManager:
    """Simple async Redis cache manager."""

    def __init__(self):
        self._client: redis.Redis | None = None
        self._connection_pool: redis.ConnectionPool | None = None
        self._settings = get_settings()

    async def get_client(self) -> redis.Redis:
        """Get or create Redis client with connection pooling."""
        if self._client is None:
            self._connection_pool = redis.ConnectionPool.from_url(
                self._settings.redis_url,
                decode_responses=True,
            )
            self._client = redis.Redis(connection_pool=self._connection_pool)
        return self._client

    async def get(self, key: str) -> Any | None:
        """Get value from cache."""
        try:
            client = await self.get_client()
            value = await client.get(key)
            if value:
                return json.loads(value)
        except Exception as e:
            logger.warning("Cache get failed for key %s: %s", key, e)
        return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache with TTL."""
        try:
            client = await self.get_client()
            ttl = ttl or self._settings.redis_cache_ttl_seconds
            await client.set(key, json.dumps(value), ex=ttl)
            return True
        except Exception as e:
            logger.warning("Cache set failed for key %s: %s", key, e)
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            client = await self.get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.warning("Cache delete failed for key %s: %s", key, e)
            return False

    async def close(self) -> None:
        """Close Redis client connection and connection pool."""
        if self._client:
            await self._client.close()
            self._client = None
        if self._connection_pool:
            await self._connection_pool.disconnect()
            self._connection_pool = None


# Global cache manager instance
_cache_manager: CacheManager | None = None


def get_cache_manager() -> CacheManager:
    """Get global cache manager instance."""
    global _cache_manager
    if _cache_manager is None:
        _cache_manager = CacheManager()
    return _cache_manager


def cached(ttl: int | None = None, key_prefix: str = ""):
    """Decorator for caching async function results.

    Args:
        ttl: Time to live in seconds. If None, uses default from settings.
        key_prefix: Prefix for cache key. If empty, uses function name.

    Note:
        Cache keys include function arguments to prevent collisions.
        Functions with different arguments will have separate cache entries.
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            cache = get_cache_manager()

            # Generate cache key including arguments
            func_name = key_prefix or func.__name__
            # Hash args and kwargs to create unique key for different arguments
            key_data = {"args": args, "kwargs": kwargs}
            key_hash = hashlib.sha256(
                json.dumps(key_data, sort_keys=True, default=str).encode()
            ).hexdigest()[
                :16
            ]  # Use first 16 chars for shorter keys
            cache_key = f"{func_name}:{key_hash}"

            # Try to get from cache
            cached_value = await cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Cache the result
            await cache.set(cache_key, result, ttl)

            return result

        # Preserve original signature for FastAPI dependency injection
        wrapper.__signature__ = inspect.signature(func)  # type: ignore[attr-defined]
        return wrapper

    return decorator
