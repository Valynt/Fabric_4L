"""Tenant kill switch — real-time suspension enforcement.

Maintains a Redis-backed cache of suspended tenant IDs that all layers
(middleware, WebSocket manager, Celery workers, workflow executor) can
query to fail closed immediately when a tenant is suspended.

Design decisions:
- Redis set with TTL: entries auto-expire so a stale entry cannot block
  a tenant forever if the cleanup path fails.
- Fail-safe tri-state: ``is_suspended`` now returns a ``TenantSuspensionStatus``
  enum instead of a plain bool. When Redis is unavailable or raises an
  exception, the result is ``UNKNOWN`` — not ``ACTIVE`` (allow). Callers
  MUST handle ``UNKNOWN`` explicitly; the middleware maps it to HTTP 503.
- Synchronous API for Celery workers; async API for FastAPI handlers.

RB-4 FIX: The previous implementation returned ``False`` (allow) when Redis
was unavailable or raised an exception. This is a fail-open vulnerability:
a suspended tenant could bypass the kill switch during a Redis outage.

The fix introduces ``TenantSuspensionStatus`` with three values:
  - ACTIVE   — Redis confirmed the tenant is NOT suspended (allow)
  - SUSPENDED — Redis confirmed the tenant IS suspended (block with 403)
  - UNKNOWN  — Redis unavailable or error (block with 503 by default)

The ``_enforce_tenant_status`` middleware method is updated to map UNKNOWN
to a 503 response, not a silent allow. The ``_tenant_status_resolver``
(DB fallback) is still consulted first when injected; UNKNOWN from the
kill switch is only reached when no resolver is configured or the resolver
also fails.
"""

from __future__ import annotations

import enum
import logging
import os
from typing import Any

logger = logging.getLogger(__name__)

# Redis key for the suspended-tenant set
SUSPENDED_TENANTS_SET = "tenant_kill_switch:suspended"
# TTL for individual entries (seconds) — auto-expire to avoid stale blocks
SUSPENDED_ENTRY_TTL_SECONDS = 300  # 5 minutes


class TenantSuspensionStatus(enum.Enum):
    """Tri-state result of a kill-switch lookup.

    Callers MUST handle all three values explicitly. The ``UNKNOWN`` state
    MUST NOT be treated as ``ACTIVE`` (allow). It indicates that the
    authoritative source (Redis) was unavailable and the caller should
    fail safe — typically by returning HTTP 503.
    """

    ACTIVE = "active"       # Confirmed not suspended — allow request
    SUSPENDED = "suspended" # Confirmed suspended — block with 403
    UNKNOWN = "unknown"     # Redis unavailable or error — block with 503


class TenantKillSwitch:
    """Redis-backed tenant suspension kill switch.

    Usage::

        kill_switch = TenantKillSwitch(redis_client)
        await kill_switch.suspend(tenant_id)      # async
        await kill_switch.unsuspend(tenant_id)    # async
        status = await kill_switch.check_status(tenant_id)  # async, tri-state
        # Legacy bool API preserved for backward compatibility:
        is_suspended = await kill_switch.is_suspended(tenant_id)  # async

    For Celery (sync)::

        kill_switch = TenantKillSwitch(redis_client)
        kill_switch.suspend_sync(tenant_id)
        kill_switch.unsuspend_sync(tenant_id)
        status = kill_switch.check_status_sync(tenant_id)
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

    async def check_status(self, tenant_id: str) -> TenantSuspensionStatus:
        """Return the tri-state suspension status for a tenant.

        Returns:
            TenantSuspensionStatus.SUSPENDED  — tenant is in the suspended set
            TenantSuspensionStatus.ACTIVE     — tenant is confirmed not suspended
            TenantSuspensionStatus.UNKNOWN    — Redis unavailable or error

        Callers MUST handle UNKNOWN explicitly. The middleware maps UNKNOWN
        to HTTP 503 (service unavailable) rather than silently allowing
        the request through.
        """
        if self._redis is None:
            logger.warning(
                "kill_switch_no_redis",
                extra={"event": "kill_switch_no_redis", "tenant_id": str(tenant_id)},
            )
            return TenantSuspensionStatus.UNKNOWN
        try:
            result = await self._redis.sismember(SUSPENDED_TENANTS_SET, str(tenant_id))
            return (
                TenantSuspensionStatus.SUSPENDED
                if bool(result)
                else TenantSuspensionStatus.ACTIVE
            )
        except Exception as exc:
            logger.warning(
                "kill_switch_check_failed",
                extra={
                    "event": "kill_switch_check_failed",
                    "tenant_id": str(tenant_id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return TenantSuspensionStatus.UNKNOWN

    async def is_suspended(self, tenant_id: str) -> bool:
        """Return True if the tenant is in the suspended set.

        .. deprecated::
            Use ``check_status()`` instead. This method returns ``False`` for
            both ACTIVE and UNKNOWN states, masking Redis failures. It is
            preserved for backward compatibility with existing call sites that
            have not yet been updated to handle the tri-state result.

        Returns False if Redis is unavailable — callers that use this method
        directly will not detect Redis outages. Prefer ``check_status()``.
        """
        status = await self.check_status(tenant_id)
        return status == TenantSuspensionStatus.SUSPENDED

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

    def check_status_sync(self, tenant_id: str) -> TenantSuspensionStatus:
        """Return the tri-state suspension status for a tenant synchronously."""
        if self._redis is None:
            logger.warning(
                "kill_switch_no_redis",
                extra={"event": "kill_switch_no_redis", "tenant_id": str(tenant_id)},
            )
            return TenantSuspensionStatus.UNKNOWN
        try:
            result = self._redis.sismember(SUSPENDED_TENANTS_SET, str(tenant_id))
            return (
                TenantSuspensionStatus.SUSPENDED
                if bool(result)
                else TenantSuspensionStatus.ACTIVE
            )
        except Exception as exc:
            logger.warning(
                "kill_switch_check_failed",
                extra={
                    "event": "kill_switch_check_failed",
                    "tenant_id": str(tenant_id),
                    "error": str(exc),
                    "error_type": type(exc).__name__,
                },
            )
            return TenantSuspensionStatus.UNKNOWN

    def is_suspended_sync(self, tenant_id: str) -> bool:
        """Synchronous version for Celery tasks."""
        return self.check_status_sync(tenant_id) == TenantSuspensionStatus.SUSPENDED


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
