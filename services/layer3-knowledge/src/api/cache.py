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
from typing import Any

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


def get_request_deduplicator() -> Any:
    return None
