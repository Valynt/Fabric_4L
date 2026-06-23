"""Tenant kill switch — real-time suspension enforcement.

Maintains a Redis-backed cache of suspended tenant IDs that all layers
(middleware, WebSocket manager, Celery workers, workflow executor) can
query to fail closed immediately when a tenant is suspended.

Design decisions:
- Redis set with TTL: entries auto-expire so a stale entry cannot block
  a tenant forever if the cleanup path fails.
- Graceful degradation: if Redis is unavailable, ``is_suspended`` returns
  ``False`` (not suspended) — this is the *safer* default because the
  middleware already performs a DB fallback check.
- Synchronous API for Celery workers; async API for FastAPI handlers.
"""

from __future__ import annotations

import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Redis key for the suspended-tenant set
SUSPENDED_TENANTS_SET = "tenant_kill_switch:suspended"
# TTL for individual entries (seconds) — auto-expire to avoid stale blocks
SUSPENDED_ENTRY_TTL_SECONDS = 300  # 5 minutes


class TenantKillSwitch:
    """Redis-backed tenant suspension kill switch.

    Usage::

        kill_switch = TenantKillSwitch(redis_client)
        await kill_switch.suspend(tenant_id)      # async
        await kill_switch.unsuspend(tenant_id)    # async
        is_suspended = await kill_switch.is_suspended(tenant_id)  # async

    For Celery (sync)::

        kill_switch = TenantKillSwitch(redis_client)
        kill_switch.suspend_sync(tenant_id)
        kill_switch.unsuspend_sync(tenant_id)
        is_suspended = kill_switch.is_suspended_sync(tenant_id)
    """

    def __init__(self, redis_client: Any | None = None) -> None:
        self._redis = redis_client

    # ------------------------------------------------------------------
    # Async API (for FastAPI / async services)
    # ------------------------------------------------------------------

    async def suspend(self, tenant_id: str) -> None:
        """Add a tenant to the suspended set with TTL."""
        if self._redis is None:
            logger.warning("Kill switch suspend skipped: no Redis client")
            return
        try:
            await self._redis.sadd(SUSPENDED_TENANTS_SET, str(tenant_id))
            await self._redis.expire(SUSPENDED_TENANTS_SET, SUSPENDED_ENTRY_TTL_SECONDS)
            logger.info("Tenant %s added to kill-switch suspended set", tenant_id)
        except Exception as exc:
            logger.warning("Kill switch suspend failed: %s", exc)

    async def unsuspend(self, tenant_id: str) -> None:
        """Remove a tenant from the suspended set."""
        if self._redis is None:
            return
        try:
            await self._redis.srem(SUSPENDED_TENANTS_SET, str(tenant_id))
            logger.info("Tenant %s removed from kill-switch suspended set", tenant_id)
        except Exception as exc:
            logger.warning("Kill switch unsuspend failed: %s", exc)

    async def is_suspended(self, tenant_id: str) -> bool:
        """Return True if the tenant is in the suspended set.

        Returns False if Redis is unavailable — the middleware DB fallback
        provides the authoritative check.
        """
        if self._redis is None:
            return False
        try:
            result = await self._redis.sismember(SUSPENDED_TENANTS_SET, str(tenant_id))
            return bool(result)
        except Exception as exc:
            logger.warning("Kill switch check failed: %s", exc)
            return False

    # ------------------------------------------------------------------
    # Sync API (for Celery workers)
    # ------------------------------------------------------------------

    def suspend_sync(self, tenant_id: str) -> None:
        """Synchronous version for Celery tasks."""
        if self._redis is None:
            logger.warning("Kill switch suspend_sync skipped: no Redis client")
            return
        try:
            self._redis.sadd(SUSPENDED_TENANTS_SET, str(tenant_id))
            self._redis.expire(SUSPENDED_TENANTS_SET, SUSPENDED_ENTRY_TTL_SECONDS)
            logger.info("Tenant %s added to kill-switch suspended set (sync)", tenant_id)
        except Exception as exc:
            logger.warning("Kill switch suspend_sync failed: %s", exc)

    def unsuspend_sync(self, tenant_id: str) -> None:
        """Synchronous version for Celery tasks."""
        if self._redis is None:
            return
        try:
            self._redis.srem(SUSPENDED_TENANTS_SET, str(tenant_id))
            logger.info("Tenant %s removed from kill-switch suspended set (sync)", tenant_id)
        except Exception as exc:
            logger.warning("Kill switch unsuspend_sync failed: %s", exc)

    def is_suspended_sync(self, tenant_id: str) -> bool:
        """Synchronous version for Celery tasks."""
        if self._redis is None:
            return False
        try:
            result = self._redis.sismember(SUSPENDED_TENANTS_SET, str(tenant_id))
            return bool(result)
        except Exception as exc:
            logger.warning("Kill switch check_sync failed: %s", exc)
            return False


# ----------------------------------------------------------------------
# Factory
# ----------------------------------------------------------------------


def get_kill_switch(redis_client: Any | None = None) -> TenantKillSwitch:
    """Return a configured TenantKillSwitch.

    If no redis_client is provided, attempts to create one from ``REDIS_URL``.
    """
    if redis_client is None:
        redis_url = os.getenv("REDIS_URL")
        if redis_url:
            try:
                from value_fabric.shared.redis_ha import create_sync_redis_client

                redis_client = create_sync_redis_client(redis_url, decode_responses=True)
            except Exception as exc:
                logger.warning("Failed to create Redis client for kill switch: %s", exc)
    return TenantKillSwitch(redis_client)
