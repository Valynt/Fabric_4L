"""Synchronous Redis client singleton for the API gateway.

Provides a single ``get_redis_client()`` entrypoint used by:

* ``app.routers.accounts`` for idempotency key storage
* ``app.core.security`` for token revocation deny-listing

The client is created lazily and cached for the process lifetime.  If no
``REDIS_URL`` is configured or Redis is unavailable, the helper returns
``None`` so callers can fall back to in-memory implementations.
"""

from __future__ import annotations

import logging
import os

import redis

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Process-level singleton.  Use ``_client_initialised`` so we do not keep
# retrying creation on every call once we have determined availability.
_redis_client: redis.Redis | None = None
_client_initialised: bool = False


def get_redis_client() -> redis.Redis | None:
    """Return the shared synchronous Redis client, or ``None`` if unavailable.

    The client reads ``Settings.redis_url`` first, then falls back to the
    ``REDIS_URL`` environment variable.  When Redis is not configured,
    callers must use their in-memory fallback path.
    """
    global _redis_client, _client_initialised

    if _client_initialised:
        return _redis_client

    _client_initialised = True

    settings = get_settings()
    redis_url = settings.redis_url or os.getenv("REDIS_URL")
    if not redis_url:
        return None

    try:
        _redis_client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_connect_timeout=5,
            socket_timeout=5,
        )
    except Exception as exc:
        logger.warning("Failed to create Redis client for %s: %s", redis_url, exc)
        _redis_client = None

    return _redis_client
