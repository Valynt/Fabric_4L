"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Redis caching layer for Value Fabric Layer 3 API.
"""

import asyncio
import hashlib
import json
import time
from collections.abc import Callable
from functools import wraps
from typing import Any, Optional

from pydantic import BaseModel

try:
    import redis.asyncio as redis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

from value_fabric.shared.models.typed_dict import TypedDictModel

from logging_config import get_logger


class RedisCache_get_statsResult(TypedDictModel):
    connected_clients: Any | None = None
    keyspace_hits: Any | None = None
    keyspace_misses: Any | None = None
    total_commands_processed: Any | None = None
    used_memory: Any | None = None
    used_memory_human: Any | None = None

logger = get_logger(__name__)


class CacheConfig:
    """Configuration for caching behavior."""

    def __init__(
        self,
        default_ttl: int = 300,  # 5 minutes
        max_ttl: int = 3600,  # 1 hour
        key_prefix: str = "value_fabric:",
        serializer: str = "json",  # json, pickle
        compression: bool = True,
    ):
        """Initialize cache configuration.

        Args:
            default_ttl: Default time-to-live in seconds
            max_ttl: Maximum allowed TTL in seconds
            key_prefix: Prefix for all cache keys
            serializer: Serialization method (json or pickle)
            compression: Whether to compress cached data
        """
        self.default_ttl = default_ttl
        self.max_ttl = max_ttl
        self.key_prefix = key_prefix
        self.serializer = serializer
        self.compression = compression


class CacheKey:
    """Utility class for generating cache keys."""

    @staticmethod
    def generate(prefix: str, *args, **kwargs) -> str:
        """Generate a cache key from arguments.

        Args:
            prefix: Key prefix
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Cache key string
        """
        # Create a deterministic string representation
        key_parts = [prefix]

        # Add positional arguments
        for arg in args:
            if isinstance(arg, BaseModel):
                key_parts.append(arg.model_dump_json())
            elif isinstance(arg, (dict, list)):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                key_parts.append(str(arg))

        # Add keyword arguments (sorted for consistency)
        for key in sorted(kwargs.keys()):
            value = kwargs[key]
            if isinstance(value, BaseModel):
                key_parts.append(f"{key}={value.model_dump_json()}")
            elif isinstance(value, (dict, list)):
                key_parts.append(f"{key}={json.dumps(value, sort_keys=True)}")
            else:
                key_parts.append(f"{key}={value}")

        # Create hash for long keys
        key_string = ":".join(key_parts)
        if len(key_string) > 200:
            key_hash = hashlib.sha256(key_string.encode()).hexdigest()[:16]
            return f"{prefix}:{key_hash}"

        return key_string


class RedisCache:
    """Redis-based cache implementation."""

    def __init__(
        self, redis_url: str, config: CacheConfig | None = None, **redis_kwargs
    ):
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            config: Cache configuration
            **redis_kwargs: Additional Redis connection parameters
        """
        if not REDIS_AVAILABLE:
            raise ImportError("redis library is required for RedisCache")

        self.config = config or CacheConfig()
        self.redis_url = redis_url
        self.redis_kwargs = redis_kwargs
        self._redis_client = None
        self._connected = False

    async def connect(self) -> None:
        """Connect to Redis."""
        if self._connected:
            return

        try:
            self._redis_client = redis.from_url(self.redis_url, **self.redis_kwargs)
            # Test connection
            await self._redis_client.ping()
            self._connected = True
            logger.info("Connected to Redis cache")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self._redis_client and self._connected:
            await self._redis_client.close()
            self._connected = False
            logger.info("Disconnected from Redis cache")

    def _serialize(self, data: Any) -> str | bytes:
        """Serialize data for caching.

        Args:
            data: Data to serialize

        Returns:
            Serialized data

        Raises:
            ValueError: If pickle serializer is requested (disabled for security)
        """
        if self.config.serializer == "pickle":
            raise ValueError("pickle serializer is disabled for security — use json or msgpack")
        else:
            return json.dumps(data, default=str)

    def _deserialize(self, data: str | bytes) -> Any:
        """Deserialize cached data.

        Args:
            data: Serialized data

        Returns:
            Deserialized data

        Raises:
            ValueError: If pickle serializer is requested (disabled for security)
        """
        if self.config.serializer == "pickle":
            raise ValueError("pickle serializer is disabled for security — use json or msgpack")
        else:
            return json.loads(data)

    def _make_key(self, key: str) -> str:
        """Add prefix to cache key.

        Args:
            key: Original key

        Returns:
            Prefixed key
        """
        return f"{self.config.key_prefix}{key}"

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self._connected:
            await self.connect()

        try:
            prefixed_key = self._make_key(key)
            data = await self._redis_client.get(prefixed_key)

            if data is None:
                return None

            return self._deserialize(data)
        except Exception as e:
            logger.warning(f"Cache get error for key {key}: {e}")
            return None

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds

        Returns:
            True if successful
        """
        if not self._connected:
            await self.connect()

        try:
            prefixed_key = self._make_key(key)
            serialized_value = self._serialize(value)

            # Use provided TTL or default
            cache_ttl = ttl or self.config.default_ttl
            cache_ttl = min(cache_ttl, self.config.max_ttl)

            await self._redis_client.setex(prefixed_key, cache_ttl, serialized_value)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete value from cache.

        Args:
            key: Cache key

        Returns:
            True if successful
        """
        if not self._connected:
            await self.connect()

        try:
            prefixed_key = self._make_key(key)
            result = await self._redis_client.delete(prefixed_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache delete error for key {key}: {e}")
            return False

    async def clear_pattern(self, pattern: str) -> int:
        """Clear keys matching pattern.

        Args:
            pattern: Key pattern (with * wildcard)

        Returns:
            Number of keys deleted
        """
        if not self._connected:
            await self.connect()

        try:
            prefixed_pattern = self._make_key(pattern)
            keys = await self._redis_client.keys(prefixed_pattern)
            if keys:
                return await self._redis_client.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache clear pattern error for {pattern}: {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        if not self._connected:
            await self.connect()

        try:
            prefixed_key = self._make_key(key)
            result = await self._redis_client.exists(prefixed_key)
            return result > 0
        except Exception as e:
            logger.warning(f"Cache exists error for key {key}: {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int | None:
        """Increment numeric value in cache.

        Args:
            key: Cache key
            amount: Increment amount

        Returns:
            New value or None
        """
        if not self._connected:
            await self.connect()

        try:
            prefixed_key = self._make_key(key)
            result = await self._redis_client.incrby(prefixed_key, amount)
            return result
        except Exception as e:
            logger.warning(f"Cache increment error for key {key}: {e}")
            return None

    async def get_stats(self) -> dict[str, Any]:
        """Get Redis statistics.

        Returns:
            Redis statistics
        """
        if not self._connected:
            await self.connect()

        try:
            info = await self._redis_client.info()
            return RedisCache_get_statsResult.model_validate({
                "connected_clients": info.get("connected_clients", 0),
                "used_memory": info.get("used_memory", 0),
                "used_memory_human": info.get("used_memory_human", "0B"),
                "keyspace_hits": info.get("keyspace_hits", 0),
                "keyspace_misses": info.get("keyspace_misses", 0),
                "total_commands_processed": info.get("total_commands_processed", 0),
            })


        except Exception as e:
            logger.warning(f"Cache stats error: {e}")
            return RedisCache_get_statsResult.model_validate({})


class CacheManager:
    """High-level cache manager with decorators and utilities."""

    def __init__(self, cache: RedisCache):
        """Initialize cache manager.

        Args:
            cache: Redis cache instance
        """
        self.cache = cache
        # Lock dictionary for per-key locking to prevent cache stampedes
        self._locks: dict[str, asyncio.Lock] = {}
        # Lock for thread-safe lock creation
        self._lock_creation_lock = asyncio.Lock()

    async def disconnect(self) -> None:
        """Disconnect from Redis cache."""
        await self.cache.disconnect()

    async def get_or_set(
        self, key: str, factory: Callable, ttl: int | None = None, *args, **kwargs
    ) -> Any:
        """Get value from cache or set using factory function.

        Uses per-key locking to prevent cache stampedes (thundering herd).

        Args:
            key: Cache key
            factory: Function to generate value if not cached
            ttl: Time-to-live in seconds
            *args: Arguments for factory function
            **kwargs: Keyword arguments for factory function

        Returns:
            Cached or generated value
        """
        # Try to get from cache first (fast path)
        cached_value = await self.cache.get(key)
        if cached_value is not None:
            return cached_value

        # Use per-key lock to prevent multiple concurrent factory executions
        async with self._lock_creation_lock:
            if key not in self._locks:
                self._locks[key] = asyncio.Lock()

        lock = self._locks[key]
        async with lock:
            # Double-check after acquiring lock
            cached_value = await self.cache.get(key)
            if cached_value is not None:
                return cached_value

            # Generate value using factory
            try:
                if asyncio.iscoroutinefunction(factory):
                    value = await factory(*args, **kwargs)
                else:
                    value = factory(*args, **kwargs)
            except Exception:
                logger.exception(f"Factory function failed for key {key}")
                raise

            # Cache the generated value
            await self.cache.set(key, value, ttl)

            # Lock cleanup: attempt to remove lock if not contested
            # This prevents unbounded memory growth with many unique keys
            try:
                async with self._lock_creation_lock:
                    # Only remove if lock exists and is not currently locked
                    if key in self._locks and not self._locks[key].locked():
                        del self._locks[key]
            except Exception:
                # Cleanup errors are non-fatal, ignore them
                pass

            return value

    def cache_result(
        self,
        ttl: int | None = None,
        key_prefix: str = "",
        key_generator: Callable | None = None,
    ):
        """Decorator to cache function results.

        Args:
            ttl: Time-to-live in seconds
            key_prefix: Prefix for cache keys
            key_generator: Custom key generator function

        Returns:
            Decorated function
        """

        def decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                # Generate cache key
                if key_generator:
                    cache_key = key_generator(*args, **kwargs)
                else:
                    cache_key = CacheKey.generate(
                        f"{key_prefix}{func.__name__}", *args, **kwargs
                    )

                # Use get_or_set pattern
                return await self.get_or_set(cache_key, func, ttl, *args, **kwargs)

            return wrapper

        return decorator

    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate cache keys matching pattern.

        Args:
            pattern: Pattern to match

        Returns:
            Number of keys invalidated
        """
        return await self.cache.clear_pattern(pattern)

    async def warm_cache(self, cache_entries: list[dict[str, Any]]) -> dict[str, bool]:
        """Warm cache with predefined entries.

        Args:
            cache_entries: List of cache entries with keys, values, and TTLs

        Returns:
            Results of cache warming
        """
        results = {}

        for entry in cache_entries:
            key = entry["key"]
            value = entry["value"]
            ttl = entry.get("ttl")

            success = await self.cache.set(key, value, ttl)
            results[key] = success

        return results


# Global cache instance (using string annotations for forward references)
_cache_manager: CacheManager | None = None
_request_deduplicator: Optional["RequestDeduplicator"] = None


def get_cache_manager() -> CacheManager | None:
    """Get global cache manager instance.

    Returns:
        Cache manager instance or None if not configured
    """
    return _cache_manager


def get_request_deduplicator() -> Optional["RequestDeduplicator"]:
    """Get global request deduplicator instance.

    Returns:
        Request deduplicator instance or None if not configured
    """
    return _request_deduplicator


def initialize_cache(
    redis_url: str, config: CacheConfig | None = None, **redis_kwargs
) -> CacheManager:
    """Initialize global cache manager.

    Args:
        redis_url: Redis connection URL
        config: Cache configuration
        **redis_kwargs: Additional Redis connection parameters

    Returns:
        Cache manager instance
    """
    global _cache_manager, _request_deduplicator

    cache = RedisCache(redis_url, config, **redis_kwargs)
    _cache_manager = CacheManager(cache)
    _request_deduplicator = RequestDeduplicator(cache)

    logger.info("Cache manager and request deduplicator initialized")
    return _cache_manager


def cache_result(
    ttl: int | None = None,
    key_prefix: str = "",
    key_generator: Callable | None = None,
):
    """Decorator to cache function results using global cache manager.

    Args:
        ttl: Time-to-live in seconds
        key_prefix: Prefix for cache keys
        key_generator: Custom key generator function

    Returns:
        Decorated function
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            cache_manager = get_cache_manager()
            if not cache_manager:
                # Fallback to direct execution if cache not available
                if asyncio.iscoroutinefunction(func):
                    return await func(*args, **kwargs)
                else:
                    return func(*args, **kwargs)

            # Generate cache key
            if key_generator:
                cache_key = key_generator(*args, **kwargs)
            else:
                cache_key = CacheKey.generate(
                    f"{key_prefix}{func.__name__}", *args, **kwargs
                )

            # Use get_or_set pattern
            return await cache_manager.get_or_set(cache_key, func, ttl, *args, **kwargs)

        return wrapper

    return decorator


class RequestDeduplicator:
    """Deduplicates concurrent identical requests to prevent redundant computation.

    Implements the "coalescing" pattern where multiple identical concurrent requests
    are merged into a single backend request. First request executes, subsequent requests
    wait for and share the result.

    This is particularly effective for expensive operations like:
    - GraphRAG multi-hop queries
    - Hybrid search with vector + graph components
    - Analytics computations (community detection, centrality)
    """

    # Constants for deduplication behavior
    DEFAULT_LOCK_TTL = 30  # seconds to hold deduplication lock
    RESULT_CACHE_TTL = 10  # seconds to cache result for late arrivals
    MAX_FUTURE_WAIT = 60  # seconds to wait for in-flight request
    POLL_INTERVAL_BASE = 0.05  # base poll interval (exponential backoff)
    MAX_POLL_INTERVAL = 1.0  # max poll interval

    def __init__(self, cache: RedisCache):
        """Initialize request deduplicator.

        Args:
            cache: Redis cache instance for distributed deduplication
        """
        self.cache = cache
        # In-memory pending request tracking for same-process deduplication
        self._pending: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    def _generate_request_key(self, operation: str, params: dict[str, Any]) -> str:
        """Generate unique key for request deduplication.

        Args:
            operation: Operation type (e.g., 'graphrag_query', 'hybrid_search')
            params: Request parameters dict

        Returns:
            Deduplication key
        """
        # Sort params for consistent hashing
        params_str = json.dumps(params, sort_keys=True, default=str)
        key_hash = hashlib.sha256(params_str.encode()).hexdigest()[:16]
        return f"dedup:{operation}:{key_hash}"

    async def execute(
        self,
        operation: str,
        params: dict[str, Any],
        executor: Callable,
        ttl: int | None = None,
        *args,
        **kwargs,
    ) -> Any:
        """Execute operation with request deduplication.

        If an identical request is already in flight, wait for its result
        instead of executing a new one.

        Args:
            operation: Operation type identifier
            params: Request parameters for deduplication key
            executor: Async function to execute
            ttl: TTL for the deduplication lock (defaults to DEFAULT_LOCK_TTL)
            *args: Arguments for executor
            **kwargs: Keyword arguments for executor

        Returns:
            Execution result (shared if deduplicated)

        Raises:
            asyncio.TimeoutError: If waiting for deduplicated request exceeds MAX_FUTURE_WAIT
        """
        ttl = ttl or self.DEFAULT_LOCK_TTL
        dedup_key = self._generate_request_key(operation, params)

        # Check for in-flight request in memory (fast path)
        async with self._lock:
            if dedup_key in self._pending:
                future = self._pending[dedup_key]
                logger.debug(f"Request deduplicated: {operation}, waiting for result")
                # Wait with timeout to prevent hanging forever
                try:
                    return await asyncio.wait_for(future, timeout=self.MAX_FUTURE_WAIT)
                except TimeoutError:
                    logger.warning(
                        f"Timeout waiting for deduplicated {operation}, executing"
                    )
                    # Remove stale future and proceed with execution
                    self._pending.pop(dedup_key, None)

        # Check distributed cache for cross-process deduplication
        try:
            pending_result = await self.cache.get(dedup_key)
            if pending_result:
                # Another process is handling this request - poll with exponential backoff
                poll_interval = self.POLL_INTERVAL_BASE
                wait_start = time.monotonic()

                while time.monotonic() - wait_start < ttl:
                    result = await self.cache.get(f"{dedup_key}:result")
                    if result:
                        logger.debug(
                            f"Retrieved deduplicated result from cache: {operation}"
                        )
                        return result
                    await asyncio.sleep(poll_interval)
                    poll_interval = min(poll_interval * 2, self.MAX_POLL_INTERVAL)

                # Timeout waiting for other process, proceed with execution
                logger.warning(
                    f"Deduplication timeout for {operation}, executing anyway"
                )
        except Exception as e:
            logger.warning(f"Deduplication check error: {e}")

        # Create future and mark as in-flight
        future = asyncio.get_event_loop().create_future()

        async with self._lock:
            # Double-check after acquiring lock
            if dedup_key in self._pending:
                try:
                    return await asyncio.wait_for(
                        self._pending[dedup_key], timeout=self.MAX_FUTURE_WAIT
                    )
                except TimeoutError:
                    self._pending.pop(dedup_key, None)
            self._pending[dedup_key] = future

        # Set distributed lock
        try:
            await self.cache.set(dedup_key, {"started": time.time()}, ttl=ttl)
        except Exception as e:
            logger.warning(f"Failed to set deduplication lock: {e}")

        try:
            # Execute the operation
            if asyncio.iscoroutinefunction(executor):
                result = await executor(*args, **kwargs)
            else:
                result = executor(*args, **kwargs)

            # Cache result briefly for late-arriving deduplicated requests
            try:
                await self.cache.set(
                    f"{dedup_key}:result", result, ttl=self.RESULT_CACHE_TTL
                )
            except Exception:
                pass

            # Complete the future
            future.set_result(result)
            return result

        except Exception as e:
            future.set_exception(e)
            raise

        finally:
            # Cleanup
            async with self._lock:
                self._pending.pop(dedup_key, None)

            try:
                await self.cache.delete(dedup_key)
            except Exception:
                pass
