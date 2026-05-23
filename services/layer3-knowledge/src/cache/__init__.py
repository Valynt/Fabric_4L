"""Cache package initialization.

Re-exports from value_fabric.shared.infrastructure.cache during migration.
"""

from value_fabric.shared.infrastructure.cache import (
    AiocacheCacheAdapter,
    CacheConfig,
    CacheKey,
    CacheManager,
    CacheParityMismatch,
    CachePort,
    CacheProviderName,
    LegacyCacheAdapter,
    RedisCache,
    RequestDeduplicator,
    ShadowCacheComparator,
    as_cache_port,
    build_cache_port,
    cache_result,
    get_cache_manager,
    get_request_deduplicator,
    initialize_cache,
)

__all__ = [
    "CacheConfig",
    "CacheKey",
    "CachePort",
    "AiocacheCacheAdapter",
    "CacheProviderName",
    "RedisCache",
    "CacheManager",
    "LegacyCacheAdapter",
    "CacheParityMismatch",
    "RequestDeduplicator",
    "as_cache_port",
    "build_cache_port",
    "ShadowCacheComparator",
    "get_cache_manager",
    "get_request_deduplicator",
    "initialize_cache",
    "cache_result",
]
