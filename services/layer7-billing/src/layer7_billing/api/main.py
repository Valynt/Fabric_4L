from __future__ import annotations

from datetime import datetime, timezone
from fastapi import Depends, Header
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.fastapi_framework import create_fabric_app, CallableProbe, ProbeResult

from ..database import get_db_from_context, health_probe, lifespan
from .. import repository


class Principal(BaseModel):
    tenant_id: str
    actor: str
    roles: list[str]


def get_principal(
    x_tenant_id: str = Header(...),
    x_actor: str = Header(...),
    x_roles: str = Header(default="billing:read"),
) -> Principal:
    return Principal(tenant_id=x_tenant_id, actor=x_actor, roles=[r.strip() for r in x_roles.split(",")])


def require_role(principal: Principal, role: str) -> None:
    if role not in principal.roles:
        raise AuthorizationError(message=f"Missing RBAC role: {role}")


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


@app.post("/v1/billing/plans")
async def upsert_plan(
    plan: Plan, principal: Principal = Depends(get_principal), db: AsyncSession = Depends(get_db_from_context)
) -> dict:
    require_role(principal, "billing:write")
    result = await repository.upsert_plan(
        db, principal.tenant_id, plan.plan_id, plan.name, plan.entitlements
    )
    return {"ok": True, "tenant_id": principal.tenant_id, "plan": result}


@app.get("/v1/billing/entitlements/{plan_id}/decision")
async def entitlement_decision(
    plan_id: str, feature: str, principal: Principal = Depends(get_principal), db: AsyncSession = Depends(get_db_from_context)
) -> dict:
    require_role(principal, "billing:read")
    allowed = feature in await repository.get_plan_entitlements(db, principal.tenant_id, plan_id)
    return {
        "tenant_id": principal.tenant_id,
        "plan_id": plan_id,
        "feature": feature,
        "allowed": allowed,
        "policy": "runtime-entitlement-api-v1",
    }


@app.post("/v1/billing/usage-events")
async def ingest_usage(
    event: UsageEventIn, principal: Principal = Depends(get_principal), db: AsyncSession = Depends(get_db_from_context)
) -> dict:
    require_role(principal, "billing:write")
    event_dict = event.model_dump()
    is_new = await repository.insert_usage_event(db, principal.tenant_id, event_dict)
    if not is_new:
        return {"status": "duplicate", "event_id": event.event_id}
    await repository.increment_aggregate(db, principal.tenant_id, event.metric, event.quantity)
    audit = {
        **event_dict,
        "tenant_id": principal.tenant_id,
        "actor": principal.actor,
        "ingested_at": datetime.now(timezone.utc).isoformat(),
    }
    return {"status": "accepted", "event": audit}


@app.get("/v1/billing/usage-aggregates")
async def usage_aggregates(principal: Principal = Depends(get_principal), db: AsyncSession = Depends(get_db_from_context)) -> dict:
    require_role(principal, "billing:read")
    metrics = await repository.get_usage_aggregates(db, principal.tenant_id)
    return {"tenant_id": principal.tenant_id, "metrics": metrics}


@app.get("/v1/billing/invoices")
async def list_invoices(principal: Principal = Depends(get_principal), db: AsyncSession = Depends(get_db_from_context)) -> dict:
    require_role(principal, "billing:read")
    invoices = await repository.list_invoices(db, principal.tenant_id)
    return {"tenant_id": principal.tenant_id, "invoices": invoices}


@app.get("/v1/billing/payment-state")
async def payment_state(principal: Principal = Depends(get_principal), db: AsyncSession = Depends(get_db_from_context)) -> dict:
    require_role(principal, "billing:read")
    state = await repository.get_payment_state(db, principal.tenant_id)
    return state
