"""Tenant lifecycle status enforcement.

Checks tenant suspension/pending/deleted states and returns blocking
responses when appropriate.
"""

from __future__ import annotations

import logging
from typing import Callable, Optional

from fastapi import Request, status
from fastapi.responses import JSONResponse

from .constants import ERR_AUTH_SERVICE_UNAVAILABLE
from .context import RequestContext
from .rate_limiter import RedisRateLimiter
from value_fabric.shared.tenant_kill_switch import (
    TenantKillSwitch,
    TenantSuspensionStatus,
)

logger = logging.getLogger(__name__)


async def enforce_tenant_status(
    ctx: RequestContext,
    tenant_status_resolver: Optional[Callable] = None,
    rate_limiter: Optional[RedisRateLimiter] = None,
    redis_client=None,
) -> Optional[JSONResponse]:
    """Return a blocking response for inactive tenant lifecycle states.

    This must be called after identity resolution and before request business
    logic. The resolver remains authoritative when available; kill-switch and
    JWT claims preserve the existing fail-closed fallback behavior.
    """
    tenant_status = None
    if tenant_status_resolver is not None:
        try:
            resolved = await tenant_status_resolver(str(ctx.tenant_id))
            if resolved is not None:
                tenant_status = resolved
        except Exception as exc:
            logger.warning(
                "tenant_status_resolver_failed",
                extra={
                    "event": "tenant_status_resolver_failed",
                    "error_code": ERR_AUTH_SERVICE_UNAVAILABLE,
                    "error": str(exc),
                    "tenant_id": str(ctx.tenant_id),
                },
            )

    if tenant_status is None and ctx.raw:
        raw_tenant_status = ctx.raw.get("tenant_status")
        if raw_tenant_status in {"suspended", "pending", "deleted"}:
            tenant_status = raw_tenant_status

    if tenant_status is None:
        # RB-4 FIX: Use check_status() (tri-state) instead of is_suspended()
        # (bool). When Redis is unavailable, check_status() returns UNKNOWN
        # which is mapped to HTTP 503 below — not a silent allow (fail-open).
        resolved_redis = (
            rate_limiter.redis_client
            if rate_limiter is not None
            else redis_client
        )
        kill_switch = TenantKillSwitch(resolved_redis)
        ks_status = await kill_switch.check_status(str(ctx.tenant_id))
        if ks_status == TenantSuspensionStatus.SUSPENDED:
            tenant_status = "suspended"
        elif ks_status == TenantSuspensionStatus.UNKNOWN:
            # Redis unavailable — fail safe with 503 rather than silently
            # allowing the request through (fail-open vulnerability).
            logger.warning(
                "tenant_kill_switch_unknown",
                extra={
                    "event": "tenant_kill_switch_unknown",
                    "tenant_id": str(ctx.tenant_id),
                },
            )
            return JSONResponse(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                content={
                    "detail": "Tenant status could not be verified. Please retry.",
                    "error": "tenant_status_unavailable",
                    "tenant_id": str(ctx.tenant_id),
                },
            )
        # ks_status == ACTIVE: confirmed not suspended, continue

    if tenant_status is None and ctx.raw:
        tenant_status = ctx.raw.get("tenant_status")

    if tenant_status == "suspended":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": "Tenant account is suspended. Please contact support.",
                "error": "tenant_suspended",
                "tenant_id": str(ctx.tenant_id),
            },
        )
    if tenant_status == "pending":
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content={
                "detail": "Tenant account is pending activation.",
                "error": "tenant_pending",
                "tenant_id": str(ctx.tenant_id),
            },
        )
    if tenant_status == "deleted":
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content={
                "detail": "Tenant not found.",
                "error": "tenant_not_found",
                "tenant_id": str(ctx.tenant_id),
            },
        )
    return None
