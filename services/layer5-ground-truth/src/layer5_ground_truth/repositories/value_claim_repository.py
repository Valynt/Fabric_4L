"""Tenant-scoped ValueClaim repository."""
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from layer5_ground_truth.models.value_evidence_graph import ValueClaim


class ValueClaimRepository:
    def __init__(self, db: AsyncSession) -> None:
        self._db = db

    async def create(self, claim: ValueClaim) -> ValueClaim:
        self._db.add(claim)
        await self._db.flush()
        await self._db.refresh(claim)
        return claim

    async def get_by_id(self, tenant_id: UUID, claim_id: UUID) -> ValueClaim | None:
        result = await self._db.execute(
            select(ValueClaim).where(
                ValueClaim.tenant_id == tenant_id,
                ValueClaim.id == claim_id,
            )
        )
        return result.scalar_one_or_none()

    async def list_by_account(
        self,
        tenant_id: UUID,
        account_id: UUID,
        status: str | None = None,
    ) -> list[ValueClaim]:
        stmt = select(ValueClaim).where(
            ValueClaim.tenant_id == tenant_id,
            ValueClaim.account_id == account_id,
        )
        if status:
            stmt = stmt.where(ValueClaim.status == status)
        result = await self._db.execute(stmt)
        return list(result.scalars().all())

    async def update_status(
        self,
        tenant_id: UUID,
        claim_id: UUID,
        status: str,
    ) -> ValueClaim | None:
        claim = await self.get_by_id(tenant_id, claim_id)
        if claim is None:
            return None
        claim.status = status
        await self._db.flush()
        await self._db.refresh(claim)
        return claim
