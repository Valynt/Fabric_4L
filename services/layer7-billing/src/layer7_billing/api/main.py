from __future__ import annotations

from datetime import datetime, timezone
from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

import structlog
from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.fastapi_framework import create_fabric_app, CallableProbe, ProbeResult, install_metrics_middleware
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ..database import get_db_from_context, health_probe, lifespan
from .. import repository
from ..logging_config import configure_structured_logging

# Configure structured logging
configure_structured_logging()
logger = structlog.get_logger(__name__)


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


app = create_fabric_app(
    service_name="layer7-billing",
    title="Layer 7 Billing Service",
    version="0.1.0",
    description="Usage event ingestion, plan entitlement checks, invoice listing, and payment state.",
    lifespan=lifespan,
    health_probes=[CallableProbe(name="database", fn=health_probe)],
    readiness_path="/ready",
)

# P0-02: Install GovernanceMiddleware — fail closed on missing/invalid auth.
try:
    from value_fabric.shared.identity.middleware import GovernanceMiddleware

    app.add_middleware(
        GovernanceMiddleware,
        api_key_resolver=None,
        rate_limiter=None,
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
    if not ctx.has_role("billing:write"):
        raise AuthorizationError(message="Missing RBAC role: billing:write")
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
