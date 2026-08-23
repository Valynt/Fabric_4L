"""Comprehensive API performance optimization and caching strategies."""

import asyncio
import builtins
import gzip
import hashlib
import json
import logging
import lzma
import zlib
from collections import OrderedDict, defaultdict
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any

try:
    import msgpack
except ImportError:
    msgpack: Any = None
import redis.asyncio as redis
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.testability import Clock, SystemClock

logger = logging.getLogger(__name__)


class CacheStrategy(str, Enum):
    """Cache strategy types."""

    LRU = "lru"
    LFU = "lfu"
    FIFO = "fifo"
    TTL = "ttl"
    ADAPTIVE = "adaptive"


class CompressionType(str, Enum):
    """Compression algorithms."""

    NONE = "none"
    GZIP = "gzip"
    ZLIB = "zlib"
    LZMA = "lzma"
    PICKLE = "pickle"


class SerializationType(str, Enum):
    """Serialization formats."""

    JSON = "json"
    PICKLE = "pickle"
    MSGPACK = "msgpack"
    BINARY = "binary"


@dataclass
class CacheEntry:
    """Cache entry with metadata."""

    key: str
    value: Any
    created_at: datetime
    last_accessed: datetime
    access_count: int = 0
    size_bytes: int = 0
    ttl: int | None = None
    tags: set[str] = field(default_factory=set)
    metadata: dict[str, Any] = field(default_factory=dict)
    _clock: Clock = field(default_factory=SystemClock, repr=False, compare=False)

    def is_expired(self) -> bool:
        """Check if cache entry is expired."""
        if self.ttl is None:
            return False
        return (self._clock.now() - self.created_at).total_seconds() > self.ttl

    def update_access(self):
        """Update access statistics."""
        self.last_accessed = self._clock.now()
        self.access_count += 1


class CacheConfig(BaseModel):
    """Cache configuration."""

    enabled: bool = Field(default=True, description="Enable caching")
    strategy: CacheStrategy = Field(
        default=CacheStrategy.LRU, description="Cache eviction strategy"
    )
    max_size: int = Field(default=1000, description="Maximum cache size")
    max_memory_mb: int = Field(default=512, description="Maximum memory usage in MB")
    default_ttl: int = Field(default=300, description="Default TTL in seconds")
    compression: CompressionType = Field(
        default=CompressionType.GZIP, description="Compression algorithm"
    )
    serialization: SerializationType = Field(
        default=SerializationType.JSON, description="Serialization format"
    )
    compression_threshold: int = Field(
        default=1024, description="Compression threshold in bytes"
    )
    enable_stats: bool = Field(default=True, description="Enable cache statistics")
    enable_background_cleanup: bool = Field(
        default=True, description="Enable background cleanup"
    )
    cleanup_interval: int = Field(
        default=300, description="Cleanup interval in seconds"
    )

    model_config = ConfigDict(use_enum_values=True)


class CacheStats(BaseModel):
    """Cache statistics."""

    hits: int = Field(default=0, description="Cache hits")
    misses: int = Field(default=0, description="Cache misses")
    sets: int = Field(default=0, description="Cache sets")
    evictions: int = Field(default=0, description="Cache evictions")
    current_size: int = Field(default=0, description="Current cache size")
    current_memory_mb: float = Field(
        default=0.0, description="Current memory usage in MB"
    )
    hit_rate: float = Field(default=0.0, description="Hit rate percentage")
    avg_response_time_ms: float = Field(
        default=0.0, description="Average response time"
    )

    def update_hit_rate(self):
        """Update hit rate calculation."""
        total_requests = self.hits + self.misses
        self.hit_rate = (
            (self.hits / total_requests * 100) if total_requests > 0 else 0.0
        )


class MemoryCache:
    """In-memory cache implementation."""

    def __init__(self, config: CacheConfig, clock: Clock | None = None):
        """Initialize memory cache.

        Args:
            config: Cache configuration
            clock: Injectable clock for time operations.  Defaults to
                ``SystemClock`` when ``None``.
        """
        self.config = config
        self._clock: Clock = clock or SystemClock()
        self.cache: dict[str, CacheEntry] = {}
        # O(1) LRU order tracking. Insertion order is recency order; the
        # least-recently-used key is always first. ``popitem(last=False)``
        # evicts in O(1) and ``move_to_end`` refreshes on access in O(1).
        self.access_order: OrderedDict[str, None] = OrderedDict()  # For LRU
        self.frequency_map: dict[str, int] = defaultdict(int)  # For LFU
        self.stats = CacheStats()
        self.current_memory_bytes = 0
        self.cleanup_task: asyncio.Task | None = None

        if config.enable_background_cleanup:
            self.cleanup_task = asyncio.create_task(self._background_cleanup())

    async def get(self, key: str) -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        start_time = self._clock.monotonic()

        if key not in self.cache:
            self.stats.misses += 1
            self.stats.update_hit_rate()
            return None

        entry = self.cache[key]

        if entry.is_expired():
            self._remove_entry_sync(key)
            self.stats.misses += 1
            self.stats.update_hit_rate()
            return None

        # Update access statistics
        entry.update_access()
        self._update_access_order(key)

        self.stats.hits += 1
        self.stats.update_hit_rate()

        response_time = (self._clock.monotonic() - start_time) * 1000
        self.stats.avg_response_time_ms = (
            self.stats.avg_response_time_ms + response_time
        ) / 2

        return entry.value

    async def set(
        self, key: str, value: Any, ttl: int | None = None, tags: set[str] | None = None
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Cache tags

        Returns:
            True if set successfully
        """
        # Serialize and compress if needed
        serialized_value = self._serialize(value)
        compressed_value = self._compress(serialized_value)

        # Calculate entry size
        entry_size = len(key) + len(compressed_value)

        # Check memory limits
        if self.config.max_memory_mb > 0:
            if (self.current_memory_bytes + entry_size) > (
                self.config.max_memory_mb * 1024 * 1024
            ):
                await self._evict_entries(entry_size)

        # Check size limits
        if len(self.cache) >= self.config.max_size:
            await self._evict_entries(1)

        now = self._clock.now()
        # Create cache entry
        entry = CacheEntry(
            key=key,
            value=compressed_value,
            created_at=now,
            last_accessed=now,
            size_bytes=entry_size,
            ttl=ttl or self.config.default_ttl,
            tags=tags or set(),
            _clock=self._clock,
        )

        # Store entry
        self.cache[key] = entry
        self._update_access_order(key)
        self.frequency_map[key] += 1
        self.current_memory_bytes += entry_size

        self.stats.sets += 1
        self.stats.current_size = len(self.cache)
        self.stats.current_memory_mb = self.current_memory_bytes / (1024 * 1024)

        return True

    async def delete(self, key: str) -> bool:
        """Delete entry from cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        return self._remove_entry_sync(key)

    async def clear(self, pattern: str | None = None, tags: builtins.set[str] | None = None):
        """Clear cache entries.

        Args:
            pattern: Key pattern to match
            tags: Tags to match
        """
        keys_to_remove = []

        for key, entry in self.cache.items():
            should_remove = True

            if pattern and pattern not in key:
                should_remove = False

            if tags and not tags.intersection(entry.tags):
                should_remove = False

            if should_remove:
                keys_to_remove.append(key)

        for key in keys_to_remove:
            self._remove_entry_sync(key)

    async def _remove_entry(self, key: str) -> bool:
        """Async compatibility shim retained for external callers.

        The removal path is synchronous (no I/O), so callers run it
        directly via :meth:`_remove_entry_sync` to avoid coroutine
        scheduling overhead; this shim preserves the old awaited API.
        """
        return self._remove_entry_sync(key)

    def _remove_entry_sync(self, key: str) -> bool:
        """Remove entry from cache.

        Args:
            key: Cache key

        Returns:
            True if removed
        """
        if key not in self.cache:
            return False

        entry = self.cache[key]
        self.current_memory_bytes -= entry.size_bytes
        del self.cache[key]

        # Update access order (O(1) removal from the OrderedDict)
        self.access_order.pop(key, None)

        # Update frequency map
        if key in self.frequency_map:
            del self.frequency_map[key]

        self.stats.current_size = len(self.cache)
        self.stats.current_memory_mb = self.current_memory_bytes / (1024 * 1024)

        return True

    def _update_access_order(self, key: str):
        """Update access order for LRU strategy."""
        if self.config.strategy == CacheStrategy.LRU:
            # ``pop`` + re-insert moves the key to the most-recent end of the
            # OrderedDict in O(1) (no linear scan of the whole LRU list).
            self.access_order.pop(key, None)
            self.access_order[key] = None

    async def _evict_entries(self, required_space: int):
        """Evict entries based on strategy.

        Args:
            required_space: Space to free in bytes
        """
        freed_space = 0
        entries_to_remove = []

        if self.config.strategy == CacheStrategy.LRU:
            # Remove least recently used
            while freed_space < required_space and self.access_order:
                # popitem(last=False) evicts the least-recently-used entry in O(1)
                key, _ = self.access_order.popitem(last=False)
                if key in self.cache:
                    entry = self.cache[key]
                    freed_space += entry.size_bytes
                    entries_to_remove.append(key)

        elif self.config.strategy == CacheStrategy.LFU:
            # Remove least frequently used
            sorted_keys = sorted(self.frequency_map.items(), key=lambda x: x[1])

            for key, _ in sorted_keys:
                if freed_space >= required_space:
                    break
                if key in self.cache:
                    entry = self.cache[key]
                    freed_space += entry.size_bytes
                    entries_to_remove.append(key)

        elif self.config.strategy == CacheStrategy.FIFO:
            # Remove oldest entries
            for key in list(self.cache.keys()):
                if freed_space >= required_space:
                    break
                if key in self.cache:
                    entry = self.cache[key]
                    freed_space += entry.size_bytes
                    entries_to_remove.append(key)

        # Remove entries
        for key in entries_to_remove:
            self._remove_entry_sync(key)
            self.stats.evictions += 1

    def _serialize(self, value: Any) -> bytes:
        """Serialize value.

        Args:
            value: Value to serialize

        Returns:
            Serialized bytes
        """
        if self.config.serialization == SerializationType.JSON:
            return json.dumps(value, default=str).encode("utf-8")
        elif self.config.serialization == SerializationType.PICKLE:
            # P0 FIX: Pickle is disabled for security — use json or msgpack
            raise ValueError("pickle serializer is disabled for security — use json or msgpack")
        elif self.config.serialization == SerializationType.MSGPACK:
            if msgpack is None:
                raise RuntimeError("msgpack is not installed")
            return msgpack.packb(value, use_bin_type=True)
        elif self.config.serialization == SerializationType.BINARY:
            if isinstance(value, bytes):
                return value
            elif isinstance(value, str):
                return value.encode("utf-8")
            else:
                return str(value).encode("utf-8")
        else:
            raise ValueError(
                f"Unsupported serialization type: {self.config.serialization!r}"
            )

    def _compress(self, data: bytes) -> bytes:
        """Compress data.

        Args:
            data: Data to compress

        Returns:
            Compressed data
        """
        if (
            self.config.compression == CompressionType.NONE
            or len(data) < self.config.compression_threshold
        ):
            return data

        if self.config.compression == CompressionType.GZIP:
            return gzip.compress(data)
        elif self.config.compression == CompressionType.ZLIB:
            return zlib.compress(data)
        elif self.config.compression == CompressionType.LZMA:
            return lzma.compress(data)
        else:
            return data

    def _decompress(self, data: bytes) -> bytes:
        """Decompress data.

        Args:
            data: Data to decompress

        Returns:
            Decompressed data
        """
        if self.config.compression == CompressionType.NONE:
            return data

        try:
            if self.config.compression == CompressionType.GZIP:
                return gzip.decompress(data)
            elif self.config.compression == CompressionType.ZLIB:
                return zlib.decompress(data)
            elif self.config.compression == CompressionType.LZMA:
                return lzma.decompress(data)
            else:
                return data
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return data

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize data.

        Args:
            data: Data to deserialize

        Returns:
            Deserialized value
        """
        if self.config.serialization == SerializationType.JSON:
            return json.loads(data.decode("utf-8"))
        elif self.config.serialization == SerializationType.PICKLE:
            # P0 FIX: Pickle is disabled for security — use json or msgpack
            raise ValueError("pickle serializer is disabled for security — use json or msgpack")
        elif self.config.serialization == SerializationType.MSGPACK:
            if msgpack is None:
                raise RuntimeError("msgpack is not installed")
            return msgpack.unpackb(data, raw=False)
        elif self.config.serialization == SerializationType.BINARY:
            return data
        else:
            raise ValueError(
                f"Unsupported serialization type: {self.config.serialization!r}"
            )

    async def get_with_deserialization(self, key: str) -> Any | None:
        """Get value with automatic deserialization.

        Args:
            key: Cache key

        Returns:
            Deserialized value or None
        """
        compressed_value = await self.get(key)
        if compressed_value is None:
            return None

        try:
            decompressed_data = self._decompress(compressed_value)
            return self._deserialize(decompressed_data)
        except Exception as e:
            logger.error(f"Deserialization failed for key {key}: {e}")
            return None

    async def set_with_serialization(
        self, key: str, value: Any, ttl: int | None = None, tags: builtins.set[str] | None = None
    ) -> bool:
        """Set value with automatic serialization.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Cache tags

        Returns:
            True if set successfully
        """
        return await self.set(key, value, ttl, tags)

    async def _background_cleanup(self):
        """Background cleanup task."""
        while True:
            try:
                await asyncio.sleep(self.config.cleanup_interval)
                await self._cleanup_expired_entries()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Background cleanup error: {e}")

    async def _cleanup_expired_entries(self):
        """Clean up expired entries."""
        expired_keys = []

        for key, entry in self.cache.items():
            if entry.is_expired():
                expired_keys.append(key)

        for key in expired_keys:
            self._remove_entry_sync(key)

        if expired_keys:
            logger.info(f"Cleaned up {len(expired_keys)} expired cache entries")

    def get_stats(self) -> CacheStats:
        """Get cache statistics.

        Returns:
            Cache statistics
        """
        return self.stats

    async def close(self):
        """Close cache and cleanup resources."""
        if self.cleanup_task:
            self.cleanup_task.cancel()
            try:
                await self.cleanup_task
            except asyncio.CancelledError:
                pass

        self.cache.clear()
        self.access_order.clear()
        self.frequency_map.clear()
        self.current_memory_bytes = 0


class RedisCache:
    """Redis-based distributed cache."""

    def __init__(
        self,
        redis_url: str,
        config: CacheConfig,
        clock: Clock | None = None,
    ):
        """Initialize Redis cache.

        Args:
            redis_url: Redis connection URL
            config: Cache configuration
            clock: Injectable clock for time operations. Defaults to
                ``SystemClock`` when ``None``.
        """
        self.redis_url = redis_url
        self.config = config
        self._clock: Clock = clock or SystemClock()
        self.redis_client: redis.Redis | None = None
        self.stats = CacheStats()

    async def connect(self):
        """Connect to Redis."""
        try:
            self.redis_client = redis.from_url(self.redis_url, decode_responses=False)
            await self.redis_client.ping()
            logger.info("Connected to Redis for caching")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def disconnect(self):
        """Disconnect from Redis."""
        if self.redis_client:
            await self.redis_client.close()
            logger.info("Disconnected from Redis")

    async def get(self, key: str) -> Any | None:
        """Get value from Redis cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.redis_client:
            return None

        start_time = self._clock.monotonic()

        try:
            data = await self.redis_client.get(key)

            if data is None:
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None

            # Deserialize and decompress
            try:
                decompressed_data = self._decompress(data)
                value = self._deserialize(decompressed_data)

                self.stats.hits += 1
                self.stats.update_hit_rate()

                response_time = (self._clock.monotonic() - start_time) * 1000
                self.stats.avg_response_time_ms = (
                    self.stats.avg_response_time_ms + response_time
                ) / 2

                return value
            except Exception as e:
                logger.error(f"Redis deserialization failed for key {key}: {e}")
                self.stats.misses += 1
                self.stats.update_hit_rate()
                return None

        except Exception as e:
            logger.error(f"Redis get error for key {key}: {e}")
            self.stats.misses += 1
            self.stats.update_hit_rate()
            return None

    async def set(
        self, key: str, value: Any, ttl: int | None = None, tags: set[str] | None = None
    ) -> bool:
        """Set value in Redis cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Cache tags

        Returns:
            True if set successfully
        """
        if not self.redis_client:
            return False

        try:
            # Serialize and compress
            serialized_value = self._serialize(value)
            compressed_value = self._compress(serialized_value)

            # Set with TTL
            redis_ttl = ttl or self.config.default_ttl

            if tags:
                # Store tags in separate hash
                await self.redis_client.hset(f"{key}:tags", *[tag for tag in tags])
                await self.redis_client.expire(f"{key}:tags", redis_ttl)

            await self.redis_client.setex(key, redis_ttl, compressed_value)

            self.stats.sets += 1

            return True

        except Exception as e:
            logger.error(f"Redis set error for key {key}: {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete entry from Redis cache.

        Args:
            key: Cache key

        Returns:
            True if deleted
        """
        if not self.redis_client:
            return False

        try:
            # Delete main entry and tags
            await self.redis_client.delete(key)
            await self.redis_client.delete(f"{key}:tags")
            return True
        except Exception as e:
            logger.error(f"Redis delete error for key {key}: {e}")
            return False

    async def clear(self, pattern: str | None = None, tags: builtins.set[str] | None = None):
        """Clear cache entries.

        Args:
            pattern: Key pattern to match
            tags: Tags to match
        """
        if not self.redis_client:
            return

        try:
            if pattern:
                # Delete by pattern
                keys = await self.redis_client.keys(pattern)
                if keys:
                    await self.redis_client.delete(*keys)

            if tags:
                # Delete by tags
                for tag in tags:
                    tag_keys = await self.redis_client.keys("*:tags")
                    for tag_key in tag_keys:
                        stored_tags = await self.redis_client.hgetall(tag_key)
                        if tag in stored_tags.values():
                            key = tag_key.replace(":tags", "")
                            await self.redis_client.delete(key)
                            await self.redis_client.delete(tag_key)
        except Exception as e:
            logger.error(f"Redis clear error: {e}")

    def _serialize(self, value: Any) -> bytes:
        """Serialize value."""
        if self.config.serialization == SerializationType.JSON:
            return json.dumps(value, default=str).encode("utf-8")
        elif self.config.serialization == SerializationType.PICKLE:
            # P0 FIX: Pickle is disabled for security — use json or msgpack
            raise ValueError("pickle serializer is disabled for security — use json or msgpack")
        elif self.config.serialization == SerializationType.MSGPACK:
            if msgpack is None:
                raise RuntimeError("msgpack is not installed")
            return msgpack.packb(value, use_bin_type=True)
        elif self.config.serialization == SerializationType.BINARY:
            if isinstance(value, bytes):
                return value
            elif isinstance(value, str):
                return value.encode("utf-8")
            else:
                return str(value).encode("utf-8")
        else:
            raise ValueError(
                f"Unsupported serialization type: {self.config.serialization!r}"
            )

    def _compress(self, data: bytes) -> bytes:
        """Compress data."""
        if (
            self.config.compression == CompressionType.NONE
            or len(data) < self.config.compression_threshold
        ):
            return data

        if self.config.compression == CompressionType.GZIP:
            return gzip.compress(data)
        elif self.config.compression == CompressionType.ZLIB:
            return zlib.compress(data)
        elif self.config.compression == CompressionType.LZMA:
            return lzma.compress(data)
        else:
            return data

    def _decompress(self, data: bytes) -> bytes:
        """Decompress data."""
        if self.config.compression == CompressionType.NONE:
            return data

        try:
            if self.config.compression == CompressionType.GZIP:
                return gzip.decompress(data)
            elif self.config.compression == CompressionType.ZLIB:
                return zlib.decompress(data)
            elif self.config.compression == CompressionType.LZMA:
                return lzma.decompress(data)
            else:
                return data
        except Exception as e:
            logger.error(f"Decompression failed: {e}")
            return data

    def _deserialize(self, data: bytes) -> Any:
        """Deserialize data."""
        if self.config.serialization == SerializationType.JSON:
            return json.loads(data.decode("utf-8"))
        elif self.config.serialization == SerializationType.PICKLE:
            # P0 FIX: Pickle is disabled for security — use json or msgpack
            raise ValueError("pickle serializer is disabled for security — use json or msgpack")
        elif self.config.serialization == SerializationType.MSGPACK:
            if msgpack is None:
                raise RuntimeError("msgpack is not installed")
            return msgpack.unpackb(data, raw=False)
        elif self.config.serialization == SerializationType.BINARY:
            return data
        else:
            raise ValueError(
                f"Unsupported serialization type: {self.config.serialization!r}"
            )

    def get_stats(self) -> CacheStats:
        """Get cache statistics."""
        return self.stats


class CacheManager:
    """Manages multiple cache instances and provides unified interface."""

    def __init__(
        self,
        memory_config: CacheConfig,
        redis_url: str | None = None,
        redis_config: CacheConfig | None = None,
    ):
        """Initialize cache manager.

        Args:
            memory_config: Memory cache configuration
            redis_url: Redis connection URL
            redis_config: Redis cache configuration
        """
        self.memory_cache = MemoryCache(memory_config)
        self.redis_cache = None

        if redis_url and redis_config:
            self.redis_cache = RedisCache(redis_url, redis_config)

        self.default_cache = self.memory_cache
        self.cache_stats = CacheStats()

    async def connect(self):
        """Connect to cache backends."""
        if self.redis_cache:
            await self.redis_cache.connect()

    async def disconnect(self):
        """Disconnect from cache backends."""
        if self.redis_cache:
            await self.redis_cache.disconnect()
        await self.memory_cache.close()

    async def get(self, key: str, cache_type: str = "auto") -> Any | None:
        """Get value from cache.

        Args:
            key: Cache key
            cache_type: Cache type ("auto", "memory", "redis")

        Returns:
            Cached value or None
        """
        if cache_type == "auto":
            # Try memory first, then Redis
            value = await self.memory_cache.get_with_deserialization(key)
            if value is not None:
                return value

            if self.redis_cache:
                value = await self.redis_cache.get(key)
                if value is not None:
                    # Cache in memory for faster access
                    await self.memory_cache.set_with_serialization(key, value)
                    return value

            return None

        elif cache_type == "memory":
            return await self.memory_cache.get_with_deserialization(key)

        elif cache_type == "redis" and self.redis_cache:
            return await self.redis_cache.get(key)

        return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: int | None = None,
        tags: set[str] | None = None,
        cache_type: str = "auto",
    ) -> bool:
        """Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds
            tags: Cache tags
            cache_type: Cache type ("auto", "memory", "redis")

        Returns:
            True if set successfully
        """
        if cache_type == "auto":
            # Set in both caches
            memory_success = await self.memory_cache.set_with_serialization(
                key, value, ttl, tags
            )

            redis_success = True
            if self.redis_cache:
                redis_success = await self.redis_cache.set(key, value, ttl, tags)

            return memory_success and redis_success

        elif cache_type == "memory":
            return await self.memory_cache.set_with_serialization(key, value, ttl, tags)

        elif cache_type == "redis" and self.redis_cache:
            return await self.redis_cache.set(key, value, ttl, tags)

        return False

    async def delete(self, key: str, cache_type: str = "auto") -> bool:
        """Delete entry from cache.

        Args:
            key: Cache key
            cache_type: Cache type ("auto", "memory", "redis")

        Returns:
            True if deleted
        """
        if cache_type == "auto":
            memory_success = await self.memory_cache.delete(key)

            redis_success = True
            if self.redis_cache:
                redis_success = await self.redis_cache.delete(key)

            return memory_success or redis_success

        elif cache_type == "memory":
            return await self.memory_cache.delete(key)

        elif cache_type == "redis" and self.redis_cache:
            return await self.redis_cache.delete(key)

        return False

    async def clear(
        self,
        pattern: str | None = None,
        tags: builtins.set[str] | None = None,
        cache_type: str = "auto",
    ):
        """Clear cache entries.

        Args:
            pattern: Key pattern to match
            tags: Tags to match
            cache_type: Cache type ("auto", "memory", "redis")
        """
        if cache_type == "auto":
            await self.memory_cache.clear(pattern, tags)
            if self.redis_cache:
                await self.redis_cache.clear(pattern, tags)

        elif cache_type == "memory":
            await self.memory_cache.clear(pattern, tags)

        elif cache_type == "redis" and self.redis_cache:
            await self.redis_cache.clear(pattern, tags)

    def get_stats(self) -> dict[str, CacheStats]:
        """Get statistics for all caches.

        Returns:
            Cache statistics
        """
        stats = {"memory": self.memory_cache.get_stats()}

        if self.redis_cache:
            stats["redis"] = self.redis_cache.get_stats()

        return stats


class PerformanceOptimizer:
    """Performance optimization utilities."""

    def __init__(self, cache_manager: CacheManager):
        """Initialize performance optimizer.

        Args:
            cache_manager: Cache manager instance
        """
        self.cache_manager = cache_manager
        self.query_cache: dict[str, Any] = {}
        self.response_cache: dict[str, Any] = {}

    def generate_cache_key(self, prefix: str, **kwargs) -> str:
        """Generate cache key from parameters.

        Args:
            prefix: Key prefix
            **kwargs: Key parameters

        Returns:
            Cache key
        """
        # Sort parameters for consistency
        sorted_params = sorted(kwargs.items())
        param_string = "&".join(f"{k}={v}" for k, v in sorted_params)

        if param_string:
            return f"{prefix}:{hashlib.md5(param_string.encode(), usedforsecurity=False).hexdigest()}"
        else:
            return prefix

    async def cached_function(
        self, key_prefix: str, ttl: int | None = None, cache_type: str = "auto"
    ):
        """Decorator for caching function results.

        Args:
            key_prefix: Cache key prefix
            ttl: Time to live in seconds
            cache_type: Cache type

        Returns:
            Decorator function
        """

        def decorator(func):
            async def wrapper(*args, **kwargs):
                # Generate cache key
                cache_key = self.generate_cache_key(
                    key_prefix, args=args, kwargs=kwargs
                )

                # Try cache
                cached_result = await self.cache_manager.get(cache_key, cache_type)
                if cached_result is not None:
                    return cached_result

                # Execute function
                result = await func(*args, **kwargs)

                # Cache result
                await self.cache_manager.set(
                    cache_key, result, ttl, cache_type=cache_type
                )

                return result

            return wrapper

        return decorator

    async def batch_get(
        self, keys: list[str], cache_type: str = "auto"
    ) -> dict[str, Any]:
        """Batch get from cache.

        Args:
            keys: List of cache keys
            cache_type: Cache type

        Returns:
            Dictionary of key-value pairs
        """
        results = {}

        for key in keys:
            value = await self.cache_manager.get(key, cache_type)
            if value is not None:
                results[key] = value

        return results

    async def batch_set(
        self,
        items: dict[str, Any],
        ttl: int | None = None,
        tags: set[str] | None = None,
        cache_type: str = "auto",
    ) -> dict[str, bool]:
        """Batch set in cache.

        Args:
            items: Dictionary of key-value pairs
            ttl: Time to live in seconds
            tags: Cache tags
            cache_type: Cache type

        Returns:
            Dictionary of key-success pairs
        """
        results = {}

        for key, value in items.items():
            success = await self.cache_manager.set(key, value, ttl, tags, cache_type)
            results[key] = success

        return results


# Global cache manager instance
_cache_manager: CacheManager | None = None
_performance_optimizer: PerformanceOptimizer | None = None


def get_cache_manager() -> CacheManager | None:
    """Get global cache manager instance.

    Returns:
        Cache manager instance
    """
    return _cache_manager


def get_performance_optimizer() -> PerformanceOptimizer | None:
    """Get global performance optimizer instance.

    Returns:
        Performance optimizer instance
    """
    return _performance_optimizer


async def initialize_caching(
    memory_config: CacheConfig,
    redis_url: str | None = None,
    redis_config: CacheConfig | None = None,
) -> tuple[CacheManager, PerformanceOptimizer]:
    """Initialize global caching system.

    Args:
        memory_config: Memory cache configuration
        redis_url: Redis connection URL
        redis_config: Redis cache configuration

    Returns:
        Cache manager and performance optimizer instances
    """
    global _cache_manager, _performance_optimizer

    _cache_manager = CacheManager(memory_config, redis_url, redis_config)
    _performance_optimizer = PerformanceOptimizer(_cache_manager)

    await _cache_manager.connect()
    logger.info("Caching system initialized")

    return _cache_manager, _performance_optimizer
