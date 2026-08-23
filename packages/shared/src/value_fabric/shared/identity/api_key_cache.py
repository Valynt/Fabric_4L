"""
API key validation cache with tenant isolation.

API key validation results are cached per tenant to prevent key reuse between tenants.
Uses HMAC-SHA256 for secure key fingerprinting (not raw key storage).
"""

import hashlib
import hmac
import logging
import os
from uuid import UUID

import redis.asyncio as redis
from value_fabric.shared.security.config import is_production_like_environment

logger = logging.getLogger(__name__)

# SECURITY: Secret key for HMAC-SHA256 key fingerprinting
# Must be set in production to prevent key hash collisions
_CACHE_KEY_VERSION = "v2"
_CACHE_KEY_NAMESPACE = "apikey"
_API_KEY_FINGERPRINT_SECRET = "API_KEY_FINGERPRINT_SECRET"


def _get_cache_secret() -> str:
    secret = os.getenv(_API_KEY_FINGERPRINT_SECRET, "")
    if not secret:
        if is_production_like_environment():
            raise RuntimeError(
                "API_KEY_FINGERPRINT_SECRET environment variable is required in "
                "production-like environments. Generate a 32+ byte random secret."
            )
        return "dev-insecure-api-key-fingerprint-secret"
    return secret


# Redis client singleton
_redis_client: redis.Redis | None = None


async def get_redis_client() -> redis.Redis:
    """Get or create Redis client singleton."""
    global _redis_client

    if _redis_client is None:
        redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
        _redis_client = redis.from_url(redis_url, decode_responses=True)

    return _redis_client


def _build_api_key_cache_key(api_key: str, tenant_id: UUID) -> str:
    """Build tenant-scoped API key cache key.

    Uses HMAC-SHA256 for cryptographically secure key fingerprinting.
    This prevents:
    - Process-randomized hash collisions (Python hash() is not stable across runs)
    - Timing attacks on key comparison
    - Information leakage via hash values

    Args:
        api_key: API key string
        tenant_id: Tenant UUID

    Returns:
        Tenant-scoped cache key with HMAC-SHA256 fingerprint
    """
    # SECURITY: Use HMAC-SHA256 for stable, secure key fingerprinting
    key_hash = hmac.new(
        _get_cache_secret().encode("utf-8"), api_key.encode("utf-8"), hashlib.sha256
    ).hexdigest()[
        :32
    ]  # First 32 chars (128 bits) sufficient for cache keys
    return f"{_CACHE_KEY_NAMESPACE}:{_CACHE_KEY_VERSION}:tenant:{tenant_id}:hash:{key_hash}"


async def validate_api_key(
    api_key: str, tenant_id: UUID, is_valid: bool | None = None
) -> bool | None:
    """Validate API key with tenant-scoped caching.

    If is_valid is provided, caches the validation result.
    If is_valid is None, checks cache for existing validation.

    Args:
        api_key: API key to validate
        tenant_id: Tenant UUID
        is_valid: Validation result to cache, or None to check cache

    Returns:
        Cached validation result, or None if not cached
    """
    try:
        client = await get_redis_client()
        key = _build_api_key_cache_key(api_key, tenant_id)

        if is_valid is not None:
            # Cache validation result
            await client.set(key, "1" if is_valid else "0", ex=300)  # 5 min TTL
            return is_valid
        else:
            # Check cache
            cached = await client.get(key)
            if cached is not None:
                return cached == "1"
            return None
    except Exception as e:
        logger.warning(f"API key cache operation failed: {e}")
        return None if is_valid is None else is_valid
