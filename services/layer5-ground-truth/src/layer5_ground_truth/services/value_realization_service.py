"""
Value Realization Ledger Service.

Business logic for Value Realization Entry CRUD, update tracking, and audit trail.
"""

import logging
import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import and_, select
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.value_realization_ledger import (
    ValueRealizationEntry,
    ValueRealizationUpdate,
)

logger = logging.getLogger(__name__)


class ValueEntryNotFoundError(Exception):
    """Raised when a value entry is not found."""
    pass


class ValueRealizationService:
    """Service for Value Realization Ledger operations."""

    async def create_value_entry(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        entry_type: str,
        entry_name: str,
        current_value: float,
        description: str | None = None,
        value_unit: str | None = None,
        value_currency: str | None = None,
        formula_id: uuid.UUID | None = None,
        formula_version: str | None = None,
        benchmark_id: uuid.UUID | None = None,
        benchmark_version: str | None = None,
        assumption_ids: list[uuid.UUID] | None = None,
        opportunity_id: uuid.UUID | None = None,
        account_id: uuid.UUID | None = None,
        business_case_id: uuid.UUID | None = None,
        created_by: str = "system",
    ) -> ValueRealizationEntry:
        """
        Create a new value realization entry.

        Args:
            db: Database session
            tenant_id: Tenant ID
            entry_type: Type of entry
            entry_name: Entry name
            current_value: Current value
            description: Optional description
            value_unit: Optional value unit
            value_currency: Optional currency code
            formula_id: Optional formula ID
            formula_version: Optional formula version
            benchmark_id: Optional benchmark ID
            benchmark_version: Optional benchmark version
            assumption_ids: Optional assumption IDs
            opportunity_id: Optional opportunity ID
            account_id: Optional account ID
            business_case_id: Optional business case ID
            created_by: User creating the entry

        Returns:
            Created ValueRealizationEntry
        """
        entry = ValueRealizationEntry(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            entry_type=entry_type,
            entry_name=entry_name,
            description=description,
            current_value=current_value,
            value_unit=value_unit,
            value_currency=value_currency,
            formula_id=formula_id,
            formula_version=formula_version,
            benchmark_id=benchmark_id,
            benchmark_version=benchmark_version,
            assumption_ids=assumption_ids,
            opportunity_id=opportunity_id,
            account_id=account_id,
            business_case_id=business_case_id,
            is_active=True,
            created_by=created_by,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        db.add(entry)
        await db.flush()

        logger.info(
            "Created value entry %s (entry_name: %s, tenant: %s)",
            entry.id,
            entry_name,
            tenant_id,
        )

        return entry

    async def get_value_entry(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        entry_id: uuid.UUID,
    ) -> ValueRealizationEntry:
        """
        Get a value entry by ID with tenant scoping.

        Args:
            db: Database session
            tenant_id: Tenant ID
            entry_id: Entry ID

        Returns:
            ValueRealizationEntry

        Raises:
            ValueEntryNotFoundError: If entry not found
        """
        result = await db.execute(
            select(ValueRealizationEntry).where(
                and_(
                    ValueRealizationEntry.id == entry_id,
                    ValueRealizationEntry.tenant_id == tenant_id,
                )
            )
        )
        entry = result.scalar_one_or_none()

        if entry is None:
            raise ValueEntryNotFoundError(f"Value entry {entry_id} not found")

        return entry

    async def list_value_entries(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        entry_type: str | None = None,
        opportunity_id: uuid.UUID | None = None,
        account_id: uuid.UUID | None = None,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ValueRealizationEntry], int]:
        """
        List value entries with pagination and filtering.

        Args:
            db: Database session
            tenant_id: Tenant ID
            entry_type: Optional filter by entry type
            opportunity_id: Optional filter by opportunity
            account_id: Optional filter by account
            page: Page number
            page_size: Page size

        Returns:
            Tuple of (entries, total count)
        """
        query = select(ValueRealizationEntry).where(
            ValueRealizationEntry.tenant_id == tenant_id
        )

        if entry_type:
            query = query.where(ValueRealizationEntry.entry_type == entry_type)

        if opportunity_id:
            query = query.where(ValueRealizationEntry.opportunity_id == opportunity_id)

        if account_id:
            query = query.where(ValueRealizationEntry.account_id == account_id)

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(ValueRealizationEntry.created_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        entries = result.scalars().all()

        return list(entries), total

    async def add_value_update(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        entry_id: uuid.UUID,
        new_value: float,
        update_reason: str,
        update_notes: str | None = None,
        formula_id_at_update: uuid.UUID | None = None,
        formula_version_at_update: str | None = None,
        benchmark_id_at_update: uuid.UUID | None = None,
        benchmark_version_at_update: str | None = None,
        assumption_ids_at_update: list[uuid.UUID] | None = None,
        calculation_metadata: dict[str, Any] | None = None,
        updated_by: str = "system",
    ) -> ValueRealizationEntry:
        """
        Add an update to a value realization entry.

        Args:
            db: Database session
            tenant_id: Tenant ID
            entry_id: Entry ID
            new_value: New value after update
            update_reason: Reason for update
            update_notes: Optional notes
            formula_id_at_update: Formula ID at time of update
            formula_version_at_update: Formula version at time of update
            benchmark_id_at_update: Benchmark ID at time of update
            benchmark_version_at_update: Benchmark version at time of update
            assumption_ids_at_update: Assumption IDs at time of update
            calculation_metadata: Optional calculation metadata
            updated_by: User performing update

        Returns:
            Updated ValueRealizationEntry

        Raises:
            ValueEntryNotFoundError: If entry not found
        """
        entry = await self.get_value_entry(db, tenant_id, entry_id)

        old_value = Decimal(str(entry.current_value))
        new_value_decimal = Decimal(str(new_value))
        value_change = new_value_decimal - old_value
        value_change_percent = (
            (value_change / old_value * Decimal("100")) if old_value != 0 else Decimal("0")
        )

        # Create ValueRealizationUpdate record
        update = ValueRealizationUpdate(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            entry_id=entry_id,
            previous_value=old_value,
            new_value=new_value_decimal,
            value_change=value_change,
            value_change_percent=value_change_percent,
            update_reason=update_reason,
            update_notes=update_notes,
            formula_id_at_update=formula_id_at_update,
            formula_version_at_update=formula_version_at_update,
            benchmark_id_at_update=benchmark_id_at_update,
            benchmark_version_at_update=benchmark_version_at_update,
            assumption_ids_at_update=assumption_ids_at_update,
            calculation_metadata=calculation_metadata,
            updated_by=updated_by,
            updated_at=datetime.now(UTC),
        )
        db.add(update)
        await db.flush()

        # Update entry current value
        entry.current_value = new_value_decimal
        entry.updated_at = datetime.now(UTC)

        await db.flush()

        logger.info(
            "Added value update for entry %s (old: %s, new: %s, change: %s%%, tenant: %s)",
            entry_id,
            old_value,
            new_value,
            value_change_percent,
            tenant_id,
        )

        return entry

    async def get_value_updates(
        self,
        db: AsyncSession,
        tenant_id: uuid.UUID,
        entry_id: uuid.UUID,
        page: int = 1,
        page_size: int = 50,
    ) -> tuple[list[ValueRealizationUpdate], int]:
        """
        Get update history for a value entry.

        Args:
            db: Database session
            tenant_id: Tenant ID
            entry_id: Entry ID
            page: Page number
            page_size: Page size

        Returns:
            Tuple of (updates, total count)
        """
        query = select(ValueRealizationUpdate).where(
            and_(
                ValueRealizationUpdate.tenant_id == tenant_id,
                ValueRealizationUpdate.entry_id == entry_id,
            )
        )

        # Get total count
        from sqlalchemy import func

        count_query = select(func.count()).select_from(query.subquery())
        total_result = await db.execute(count_query)
        total = total_result.scalar()

        # Apply pagination
        query = query.order_by(ValueRealizationUpdate.updated_at.desc())
        query = query.offset((page - 1) * page_size).limit(page_size)

        result = await db.execute(query)
        updates = result.scalars().all()

        return list(updates), total
