from __future__ import annotations

"""Business case persistence service."""


from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from ..models.business_case_record import BusinessCaseRecord


class BusinessCaseService:
    """Service for durable business case records."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def upsert_case_record(
        self,
        *,
        case_id: str,
        workflow_id: str,
        account_id: UUID,
        opportunity_id: str | None,
        status: str,
        document_url: str | None,
        tenant_id: str,
    ) -> BusinessCaseRecord:
        """Create or update a case record keyed by case_id."""
        existing = await self.db.get(BusinessCaseRecord, case_id)
        if existing:
            existing.workflow_id = workflow_id
            existing.account_id = account_id
            existing.opportunity_id = opportunity_id
            existing.status = status
            existing.document_url = document_url
            existing.tenant_id = tenant_id
            record = existing
        else:
            record = BusinessCaseRecord(
                case_id=case_id,
                workflow_id=workflow_id,
                account_id=account_id,
                opportunity_id=opportunity_id,
                status=status,
                document_url=document_url,
                tenant_id=tenant_id,
            )
            self.db.add(record)

        await self.db.commit()
        await self.db.refresh(record)
        return record

