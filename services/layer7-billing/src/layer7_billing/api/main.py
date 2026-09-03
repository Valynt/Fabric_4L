from __future__ import annotations

from datetime import datetime, timezone
import json
import os
import time
from typing import Any

from fastapi import Depends, Header, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ServiceUnavailableError,
)
from value_fabric.shared.fastapi_framework import (
    CallableProbe,
    ProbeResult,
    create_fabric_app,
    install_metrics_middleware,
    register_health_endpoint,
)
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.rate_limiter import RedisRateLimiter

from ..database import get_db_from_context, health_probe, lifespan
from .. import repository
from ..logging_config import configure_structured_logging
from ..webhook_security import (
    DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS,
    verify_stripe_webhook_signature,
)
from .routes.billing import router as billing_router
from .routes.billing_overages import router as billing_overages_router
from .routes.billing_usage import router as billing_usage_router
from .routes.billing_webhooks import router as billing_webhooks_router

# Configure structured logging
configure_structured_logging()
logger = structlog.get_logger(__name__)


_STRIPE_WEBHOOK_REPLAY_CACHE: dict[str, int] = {}


def _stripe_webhook_secret() -> str | None:
    return os.getenv("STRIPE_WEBHOOK_SECRET")


def _stripe_webhook_tolerance_seconds() -> int:
    raw_tolerance = os.getenv(
        "STRIPE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS",
        str(DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS),
    )
    try:
        return int(raw_tolerance)
    except ValueError:
        return DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS


def _reject_replayed_stripe_event(
    event_id: str, timestamp: int, *, now: int | None = None
) -> None:
    current_time = int(time.time()) if now is None else now
    tolerance_seconds = _stripe_webhook_tolerance_seconds()
    expired_before = current_time - tolerance_seconds
    for cached_event_id, cached_timestamp in list(_STRIPE_WEBHOOK_REPLAY_CACHE.items()):
        if cached_timestamp < expired_before:
            del _STRIPE_WEBHOOK_REPLAY_CACHE[cached_event_id]

    if event_id in _STRIPE_WEBHOOK_REPLAY_CACHE:
        raise ValueError("Duplicate Stripe webhook event")
    _STRIPE_WEBHOOK_REPLAY_CACHE[event_id] = timestamp

# SEC-P001: Stripe webhook rate limit — prevent endpoint abuse.
# Uses a separate in-memory sliding window for webhooks since these
# are unauthenticated requests that must not hit tenant-scoped Redis keys.
_STRIPE_WEBHOOK_RATE_LIMIT_MAX: int = int(os.getenv("STRIPE_WEBHOOK_RATE_LIMIT_PER_MINUTE", "100"))
_stripe_webhook_hit_log: dict[str, float] = {}

def _check_stripe_webhook_rate_limit(source_ip: str) -> None:
    """Fail closed if the Stripe webhook endpoint exceeds its rate limit.

    Uses a per-source-IP sliding window with automatic eviction of stale
    entries.  Raises ServiceUnavailableError (which maps to HTTP 429) when
    the limit is exceeded.
    """
    now = time.time()
    window = 60.0  # 1 minute sliding window
    cutoff = now - window
    # Evict stale entries
    for key, ts in list(_stripe_webhook_hit_log.items()):
        if ts < cutoff:
            del _stripe_webhook_hit_log[key]
    window_key = f"stripe_webhook:{source_ip}"
    count = sum(1 for k, ts in _stripe_webhook_hit_log.items() if k.startswith(window_key) and ts >= cutoff)
    if count >= _STRIPE_WEBHOOK_RATE_LIMIT_MAX:
        raise ServiceUnavailableError(message="Stripe webhook rate limit exceeded. Retry after 60 seconds.")
    _stripe_webhook_hit_log[f"{window_key}:{now}"] = now


class Plan(BaseModel):
    plan_id: str
    name: str
    entitlements: list[str] = Field(default_factory=list)


class UsageEventIn(BaseModel):
    event_id: str
    metric: str
    quantity: float
    source: str
    timestamp: str
    request_id: str

# SEC-P001: Per-tenant usage event ingestion rate limit.
# Enforces a tenant-scoped limit on /v1/billing/usage-events to prevent
# a single tenant from flooding the billing pipeline.
_USAGE_EVENT_RATE_LIMIT_MAX: int = int(os.getenv("USAGE_EVENT_RATE_LIMIT_PER_MINUTE", "1000"))
_tenant_usage_event_log: dict[str, list[float]] = {}

def _check_usage_event_rate_limit(tenant_id: str) -> None:
    """Fail closed if tenant exceeds usage event ingestion rate limit."""
    now = time.time()
    window = 60.0
    cutoff = now - window
    window_list = _tenant_usage_event_log.setdefault(tenant_id, [])
    # Evict stale entries
    window_list[:] = [ts for ts in window_list if ts >= cutoff]
    count = len(window_list)
    if count >= _USAGE_EVENT_RATE_LIMIT_MAX:
        raise ServiceUnavailableError(
            message=f"Usage event rate limit exceeded for tenant {tenant_id}. Retry after 60 seconds."
        )
    window_list.append(now)


app = create_fabric_app(
    service_name="layer7-billing",
    title="Layer 7 Billing Service",
    version="0.1.0",
    description="Usage event ingestion, plan entitlement checks, invoice listing, and payment state.",
    lifespan=lifespan,
    health_probes=[CallableProbe(name="database", fn=health_probe)],
    readiness_path="/ready",
    audit_worker_db_factory=get_db_from_context,
    enforce_tenant_context=True,
    telemetry_service_name="layer7-billing",
    instrument_telemetry=True,
)
register_health_endpoint(app, service_name="layer7-billing", include_in_schema=False)

# P0-02: Install GovernanceMiddleware — fail closed on missing/invalid auth.
try:
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    from ..database import redis_client_async

    # SEC-P001: Initialize RedisRateLimiter for per-tenant rate limiting.
    _redis_rate_limiter: RedisRateLimiter | None = None
    try:
        if redis_client_async is not None:
            _redis_rate_limiter = RedisRateLimiter(redis_client_async)
    except Exception as _rl_err:
        logger.error(
            "CRITICAL: RedisRateLimiter init failed",
            component="layer7-billing",
            error=str(_rl_err),
        )
        raise RuntimeError("RedisRateLimiter is required for Layer 7 billing rate limiting.") from _rl_err

    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=None,
        rate_limiter=_redis_rate_limiter,
    )
    logger.info("GovernanceMiddleware installed", component="layer7-billing")
except ImportError:
    logger.error("CRITICAL: GovernanceMiddleware not importable.")
    raise RuntimeError("GovernanceMiddleware is required for Layer 7 billing.")

# Install metrics middleware if available
try:
    from prometheus_client import Counter, Histogram, Registry
    from value_fabric.shared.fastapi_framework.metrics import MetricsMiddleware

    metrics_registry = Registry()
    metrics = MetricsMiddleware(metrics_registry)
    install_metrics_middleware(app, metrics=metrics, middleware_factory=lambda m: m)
    logger.info("Metrics middleware installed", component="layer7-billing")
except ImportError:
    logger.warning("Metrics middleware not available - prometheus_client not installed", component="layer7-billing")


@app.post("/v1/billing/plans")
async def upsert_plan(
    plan: Plan,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict:
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")
    result = await repository.upsert_plan(
        db, str(ctx.tenant_id), plan.plan_id, plan.name, plan.entitlements
    )
    logger.info("Billing plan upserted", tenant_id=str(ctx.tenant_id), plan_id=plan.plan_id, operation="plan_upsert", route="/v1/billing/plans")
    return {"ok": True, "tenant_id": str(ctx.tenant_id), "plan": result}


@app.get("/v1/billing/entitlements/{plan_id}/decision")
async def entitlement_decision(
    plan_id: str,
    feature: str,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict:
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")
    allowed = feature in await repository.get_plan_entitlements(db, str(ctx.tenant_id), plan_id)
    logger.info("Entitlement decision", tenant_id=str(ctx.tenant_id), plan_id=plan_id, feature=feature, allowed=allowed, operation="entitlement_decision", route="/v1/billing/entitlements")
    return {
        "tenant_id": str(ctx.tenant_id),
        "plan_id": plan_id,
        "feature": feature,
        "allowed": allowed,
        "policy": "runtime-entitlement-api-v1",
    }


@app.post("/v1/billing/usage-events")
async def ingest_usage(
    event: UsageEventIn,
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict:
    # SEC-P001: Enforce per-tenant usage event rate limit before authz check
    # to fail fast under load.  Authz still runs after for defense in depth.
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")

    # SEC-P001: Tenant-scoped rate limit on usage event ingestion.
    if ctx.tenant_id:
        _check_usage_event_rate_limit(str(ctx.tenant_id))

    event_dict = event.model_dump()
    is_new = await repository.insert_usage_event(db, str(ctx.tenant_id), event_dict)
    if not is_new:
        logger.info("Usage event duplicate", tenant_id=str(ctx.tenant_id), event_id=event.event_id, operation="usage_event_ingest", route="/v1/billing/usage-events", status="duplicate")
        return {"status": "duplicate", "event_id": event.event_id}
    await repository.increment_aggregate(db, str(ctx.tenant_id), event.metric, event.quantity)
    audit = {
        **event_dict,
        "tenant_id": str(ctx.tenant_id),
        "actor": str(ctx.user_id) if ctx.user_id else "system",
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    logger.info("Usage event ingested", tenant_id=str(ctx.tenant_id), event_id=event.event_id, metric=event.metric, quantity=event.quantity, operation="usage_event_ingest", route="/v1/billing/usage-events", status="accepted")
    return {"status": "accepted", "event": audit}


@app.get("/v1/billing/usage-aggregates")
async def usage_aggregates(
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict:
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")
    metrics = await repository.get_usage_aggregates(db, str(ctx.tenant_id))
    logger.info("Usage aggregates retrieved", tenant_id=str(ctx.tenant_id), metric_count=len(metrics), operation="usage_aggregates", route="/v1/billing/usage-aggregates")
    return {"tenant_id": str(ctx.tenant_id), "metrics": metrics}


@app.get("/v1/billing/invoices")
async def list_invoices(
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict:
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")
    invoices = await repository.list_invoices(db, str(ctx.tenant_id))
    logger.info("Invoices listed", tenant_id=str(ctx.tenant_id), invoice_count=len(invoices), operation="list_invoices", route="/v1/billing/invoices")
    return {"tenant_id": str(ctx.tenant_id), "invoices": invoices}


@app.get("/v1/billing/payment-state")
async def payment_state(
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
) -> dict:
    if not ctx.has_role("billing:read"):
        raise AuthorizationError(message="Missing RBAC role: billing:read")
    state = await repository.get_payment_state(db, str(ctx.tenant_id))
    logger.info("Payment state retrieved", tenant_id=str(ctx.tenant_id), state_key=state.get("state_key"), operation="payment_state", route="/v1/billing/payment-state")
    return state


@app.post("/v1/billing/webhook")  # type: ignore[misc]
async def stripe_webhook(
    request: Request,
    stripe_signature: str | None = Header(default=None, alias="Stripe-Signature"),
) -> dict[str, Any]:
    """Receive Stripe billing webhooks after HMAC signature verification.

    Stripe webhooks are authenticated by ``Stripe-Signature`` rather than a
    tenant header or user JWT. The raw request body is verified before JSON is
    parsed, and event IDs are cached within the timestamp tolerance window to
    reject immediate replay attempts.
    """

    body = await request.body()
    tolerance_seconds = _stripe_webhook_tolerance_seconds()
    try:
        # SEC-P001: Enforce webhook-specific rate limit before signature verification
        # to prevent CPU-intensive verification from being DOS'd.
        source_ip = request.client.host if request.client else "unknown"
        _check_stripe_webhook_rate_limit(source_ip)
        signature = verify_stripe_webhook_signature(
            body,
            stripe_signature,
            _stripe_webhook_secret(),
            tolerance_seconds=tolerance_seconds,
        )
        event = json.loads(body)
        event_id = event.get("id") if isinstance(event, dict) else None
        event_type = event.get("type") if isinstance(event, dict) else None
        if not isinstance(event_id, str) or not event_id.strip():
            raise ValueError("Stripe webhook event id is required")
        _reject_replayed_stripe_event(event_id, signature.timestamp)
    except json.JSONDecodeError as exc:
        logger.warning(
            "Stripe webhook JSON decoding rejected",
            operation="stripe_webhook",
            route="/v1/billing/webhook",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook payload",
        ) from exc
    except ValueError as exc:
        logger.warning(
            "Stripe webhook validation rejected",
            reason=str(exc),  # ban-str-e-allow: structured-log
            operation="stripe_webhook",
            route="/v1/billing/webhook",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook payload",
        ) from exc

    logger.info(
        "Stripe webhook accepted",
        event_id=event_id,
        event_type=event_type,
        operation="stripe_webhook",
        route="/v1/billing/webhook",
    )
    return {"received": True, "event_id": event_id}


# S3-1: Phase 1 billing route extraction — mount extracted L4 billing routers
# under the canonical /v1/billing prefix.  These replace the L4-local
# billing routes which now forward via HTTP client stubs.
app.include_router(billing_router, prefix="/v1")
app.include_router(billing_overages_router, prefix="/v1/billing")
app.include_router(billing_usage_router, prefix="/v1/billing")
app.include_router(billing_webhooks_router, prefix="/v1/billing")
