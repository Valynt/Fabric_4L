from __future__ import annotations

from fastapi import Depends, FastAPI, Header, HTTPException, status
from pydantic import BaseModel, Field

from layer7_billing.storage.store import STORE

app = FastAPI(title="Layer 7 Billing Service", version="0.1.0")


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
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=f"Missing RBAC role: {role}")


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


@app.post("/v1/billing/plans")
def upsert_plan(plan: Plan, principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "billing:write")
    tenant = STORE.tenant(principal.tenant_id)
    tenant.plans[plan.plan_id] = plan.model_dump()
    tenant.entitlements[plan.plan_id] = set(plan.entitlements)
    return {"ok": True, "tenant_id": principal.tenant_id, "plan": plan}


@app.get("/v1/billing/entitlements/{plan_id}/decision")
def entitlement_decision(plan_id: str, feature: str, principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "billing:read")
    tenant = STORE.tenant(principal.tenant_id)
    allowed = feature in tenant.entitlements.get(plan_id, set())
    return {
        "tenant_id": principal.tenant_id,
        "plan_id": plan_id,
        "feature": feature,
        "allowed": allowed,
        "policy": "runtime-entitlement-api-v1",
    }


@app.post("/v1/billing/usage-events")
def ingest_usage(event: UsageEventIn, principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "billing:write")
    tenant = STORE.tenant(principal.tenant_id)
    if event.event_id in tenant.usage_events:
        return {"status": "duplicate", "event_id": event.event_id}
    audit = {
        **event.model_dump(),
        "tenant_id": principal.tenant_id,
        "actor": principal.actor,
        "ingested_at": STORE.now_iso(),
    }
    tenant.usage_events[event.event_id] = audit
    tenant.usage_aggregates[event.metric] += event.quantity
    return {"status": "accepted", "event": audit}


@app.get("/v1/billing/usage-aggregates")
def usage_aggregates(principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "billing:read")
    tenant = STORE.tenant(principal.tenant_id)
    return {"tenant_id": principal.tenant_id, "metrics": tenant.usage_aggregates}


@app.get("/v1/billing/invoices")
def list_invoices(principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "billing:read")
    tenant = STORE.tenant(principal.tenant_id)
    return {"tenant_id": principal.tenant_id, "invoices": list(tenant.invoices.values())}


@app.get("/v1/billing/payment-state")
def payment_state(principal: Principal = Depends(get_principal)) -> dict:
    require_role(principal, "billing:read")
    tenant = STORE.tenant(principal.tenant_id)
    state = tenant.payments.get("current", {"tenant_id": principal.tenant_id, "state": "pending"})
    return state
