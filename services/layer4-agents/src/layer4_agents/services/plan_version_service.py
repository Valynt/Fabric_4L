from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..config.plans import build_plan_version_payload
from ..models.billing import BillingPlanVersion, BillingSubscription


class PlanVersionService:
    def __init__(self, db: AsyncSession, tenant_id: str | None = None) -> None:
        self.db = db
        # Normalize UUID-typed tenant context to str for String-typed billing
        # columns under asyncpg (see OverageService note).
        self.tenant_id = str(tenant_id) if tenant_id is not None else None

    async def get_effective_plan_version(self, plan_id: str, at_time: datetime) -> BillingPlanVersion | None:
        query = (
            select(BillingPlanVersion)
            .where(
                BillingPlanVersion.plan_id == plan_id,
                BillingPlanVersion.tenant_id.is_(None),
                BillingPlanVersion.effective_from <= at_time,
                or_(BillingPlanVersion.effective_to.is_(None), BillingPlanVersion.effective_to > at_time),
            )
            .order_by(BillingPlanVersion.effective_from.desc(), BillingPlanVersion.version.desc())
        )
        result = await self.db.execute(query)
        return result.scalars().first()

    async def ensure_bootstrap_defaults(self) -> None:
        for plan_id in ("free", "pro", "enterprise"):
            existing = await self.get_effective_plan_version(plan_id, datetime.now(UTC))
            if existing:
                continue
            payload = build_plan_version_payload(plan_id)
            self.db.add(
                BillingPlanVersion(
                    id=f"planver_{plan_id}_v1",
                    tenant_id=None,
                    plan_id=plan_id,
                    version=1,
                    effective_from=datetime(2020, 1, 1, tzinfo=UTC),
                    effective_to=None,
                    features={"ids": payload["features"]},
                    usage_limits=payload["usage_limits"],
                    config_signature=None,
                    created_by="bootstrap",
                )
            )
        await self.db.flush()

    async def get_subscription_plan_version(
        self,
        subscription: BillingSubscription | None,
        at_time: datetime,
    ) -> BillingPlanVersion | None:
        if not subscription:
            return await self.get_effective_plan_version("free", at_time)

        if subscription.plan_version_id:
            result = await self.db.execute(
                select(BillingPlanVersion).where(
                    BillingPlanVersion.id == subscription.plan_version_id,
                    BillingPlanVersion.plan_id == subscription.plan_id,
                    or_(
                        BillingPlanVersion.tenant_id.is_(None),
                        BillingPlanVersion.tenant_id == subscription.tenant_id,
                    ),
                )
            )
            pinned = result.scalar_one_or_none()
            if pinned:
                return pinned

        return await self.get_effective_plan_version(subscription.plan_id, at_time)
