from __future__ import annotations

from typing import Any

from sqlalchemy import select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from .models import BillingPlan, Invoice, PaymentState, UsageAggregate, UsageEvent


async def upsert_plan(
    session: AsyncSession, tenant_id: str, plan_id: str, name: str, entitlements: list[str]
) -> dict[str, Any]:
    stmt = (
        insert(BillingPlan)
        .values(plan_id=plan_id, tenant_id=tenant_id, name=name, entitlements=entitlements)
        .on_conflict_do_update(
            index_elements=["plan_id", "tenant_id"],
            set_={"name": name, "entitlements": entitlements},
        )
    )
    await session.execute(stmt)
    return {"plan_id": plan_id, "tenant_id": tenant_id, "name": name, "entitlements": entitlements}


async def get_plan_entitlements(session: AsyncSession, tenant_id: str, plan_id: str) -> list[str]:
    result = await session.execute(
        select(BillingPlan.entitlements).where(
            BillingPlan.tenant_id == tenant_id, BillingPlan.plan_id == plan_id
        )
    )
    row = result.scalar_one_or_none()
    return row or []


async def insert_usage_event(
    session: AsyncSession, tenant_id: str, event: dict[str, Any]
) -> bool:
    stmt = (
        insert(UsageEvent)
        .values(tenant_id=tenant_id, **event)
        .on_conflict_do_nothing(index_elements=["tenant_id", "event_id"])
    )
    result = await session.execute(stmt)
    return result.rowcount == 1


async def increment_aggregate(
    session: AsyncSession, tenant_id: str, metric: str, quantity: float
) -> None:
    stmt = (
        insert(UsageAggregate)
        .values(tenant_id=tenant_id, metric=metric, total_quantity=quantity)
        .on_conflict_do_update(
            index_elements=["tenant_id", "metric"],
            set_={"total_quantity": UsageAggregate.total_quantity + quantity},
        )
    )
    await session.execute(stmt)


async def get_usage_aggregates(session: AsyncSession, tenant_id: str) -> dict[str, float]:
    result = await session.execute(
        select(UsageAggregate.metric, UsageAggregate.total_quantity).where(
            UsageAggregate.tenant_id == tenant_id
        )
    )
    return {row.metric: row.total_quantity for row in result.all()}


async def list_invoices(session: AsyncSession, tenant_id: str) -> list[dict[str, Any]]:
    result = await session.execute(
        select(Invoice).where(Invoice.tenant_id == tenant_id)
    )
    rows = result.scalars().all()
    return [{"invoice_id": r.invoice_id, "payload": r.payload, "created_at": r.created_at.isoformat()} for r in rows]


async def get_payment_state(
    session: AsyncSession, tenant_id: str, state_key: str = "current"
) -> dict[str, Any]:
    result = await session.execute(
        select(PaymentState).where(
            PaymentState.tenant_id == tenant_id, PaymentState.state_key == state_key
        )
    )
    row = result.scalar_one_or_none()
    if row:
        return {"tenant_id": row.tenant_id, "state_key": row.state_key, "state": row.state, "payload": row.payload}
    return {"tenant_id": tenant_id, "state_key": state_key, "state": "pending", "payload": {}}
