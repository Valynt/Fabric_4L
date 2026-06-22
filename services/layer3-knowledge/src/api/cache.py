"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Redis cache layer with tenant isolation.

All cache operations are tenant-scoped to prevent cross-tenant data leakage.
Cache keys follow the pattern: cache:tenant:{tenant_id}:{resource_type}:{resource_id}
"""

import logging
import os
import re
import json
from typing import Any
from uuid import UUID

import redis.asyncio as redis

try:
    from value_fabric.shared.identity.context import require_context
except ImportError:
    # Fallback for when shared package not available
    require_context = None

logger = logging.getLogger(__name__)

# Redis client singleton
_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client singleton."""
    global _redis_client
    
    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis.from_url(redis_url, decode_responses=True)
    
    return _redis_client


def _sanitize_key_component(component: str) -> str:
    """Sanitize cache key component to prevent injection attacks.
    
    Args:
        component: Raw key component (e.g., entity_id)
    
    Returns:
        Sanitized component with dangerous characters removed
    """
    # Remove path traversal attempts
    component = component.replace("../", "").replace("..\\", "")
    # Remove Redis key separators
    component = component.replace(":", "_")
    # Allow only alphanumeric, dash, underscore
    component = re.sub(r"[^a-zA-Z0-9\-_]", "_", component)
    return component


def _tenant_cache_prefix(tenant_id: UUID | str) -> str:
    try:
        normalized = str(UUID(str(tenant_id)))
    except (TypeError, ValueError) as exc:
        raise ValueError("valid tenant_id is required for cache access") from exc
    return f"cache:tenant:{normalized}"


def _cache_key(tenant_id: UUID | str, resource_type: str, resource_id: str) -> str:
    return (
        f"{_tenant_cache_prefix(tenant_id)}:"
        f"{_sanitize_key_component(resource_type)}:"
        f"{_sanitize_key_component(resource_id)}"
    )


def _sanitize_pattern_component(pattern: str) -> str:
    sentinel = "__VF_CACHE_WILDCARD__"
    value = str(pattern).replace("*", sentinel)
    value = _sanitize_key_component(value)
    return value.replace(sentinel, "*")


def _decode_json_cache_value(value: Any) -> Any:
    if value is None:
        return None
    if isinstance(value, bytes):
        value = value.decode("utf-8")
    if isinstance(value, str):
        return json.loads(value)
    return value


async def set_cached_entity(
    *,
    tenant_id: UUID | str,
    entity_id: str,
    entity_data: dict[str, Any],
    ttl_seconds: int = 300,
) -> bool:
    client = await get_redis_client()
    key = _cache_key(tenant_id, "entity", entity_id)
    return bool(await client.set(key, json.dumps(entity_data), ex=ttl_seconds))


async def get_cached_entity(
    *,
    tenant_id: UUID | str,
    entity_id: str,
) -> dict[str, Any] | None:
    client = await get_redis_client()
    value = await client.get(_cache_key(tenant_id, "entity", entity_id))
    return _decode_json_cache_value(value)


async def set_cached_query(
    *,
    tenant_id: UUID | str,
    query: str,
    results: list[dict[str, Any]],
    ttl_seconds: int = 300,
) -> bool:
    client = await get_redis_client()
    key = _cache_key(tenant_id, "query", query)
    return bool(await client.set(key, json.dumps(results), ex=ttl_seconds))


async def get_cached_query(
    *,
    tenant_id: UUID | str,
    query: str,
) -> list[dict[str, Any]] | None:
    client = await get_redis_client()
    value = await client.get(_cache_key(tenant_id, "query", query))
    return _decode_json_cache_value(value)


async def invalidate_cache_pattern(
    *,
    tenant_id: UUID | str,
    pattern: str,
) -> int:
    client = await get_redis_client()
    scoped_pattern = f"{_tenant_cache_prefix(tenant_id)}:{_sanitize_pattern_component(pattern)}"
    keys = await client.keys(scoped_pattern)
    if not keys:
        return 0
    return int(await client.delete(*keys))


async def invalidate_tenant_cache(*, tenant_id: UUID | str) -> int:
    return await invalidate_cache_pattern(tenant_id=tenant_id, pattern="*")


def get_request_deduplicator() -> Any:
    return None
