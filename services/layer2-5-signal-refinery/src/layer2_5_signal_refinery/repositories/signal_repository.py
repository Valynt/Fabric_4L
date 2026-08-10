from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..models.db_models import ValueSignalRow

"""Signal repository — tenant-scoped PostgreSQL persistence for ValueSignals.

All methods require an explicit tenant_id derived from authenticated context.
No method accepts tenant_id from request body.
"""

logger = logging.getLogger(__name__)


def _row_to_dict(row: ValueSignalRow) -> dict[str, Any]:
    """Convert an ORM row to a plain dict suitable for Pydantic parsing."""
    return {
        "id": str(row.id),
        "tenant_id": str(row.tenant_id),
        "account_id": str(row.account_id),
        "type": row.type,
        "content": row.content,
        "confidence": row.confidence,
        "trust_score": row.trust_score,
        "lifecycle_state": row.lifecycle_state,
        "evidence": row.evidence or [],
        "provenance": row.provenance or {},
        "source_refs": row.source_refs or [],
        "opportunity_id": str(row.opportunity_id) if row.opportunity_id else None,
        "value_driver_id": str(row.value_driver_id) if row.value_driver_id else None,
        "stakeholder_id": str(row.stakeholder_id) if row.stakeholder_id else None,
        "persona": row.persona,
        "industry": row.industry,
        "impact_area": row.impact_area,
        "estimated_value": row.estimated_value,
        "currency": row.currency,
        "time_horizon": row.time_horizon,
        "validation_notes": row.validation_notes,
        "reviewer_id": str(row.reviewer_id) if row.reviewer_id else None,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "supersedes_signal_id": str(row.supersedes_signal_id) if row.supersedes_signal_id else None,
        "related_signal_ids": [str(x) for x in row.related_signal_ids] if row.related_signal_ids else None,
        "created_at": row.created_at.isoformat(),
        "updated_at": row.updated_at.isoformat(),
        "reviewed_at": row.reviewed_at.isoformat() if row.reviewed_at else None,
    }


class SignalRepository:
    """Tenant-scoped repository for ValueSignal persistence.

    All queries filter by tenant_id. The session must already have
    SET LOCAL app.tenant_id applied (done by get_db_from_context).
    """

    def __init__(self, db: AsyncSession, tenant_id: str) -> None:
        self._db = db
        self._tenant_id = tenant_id

    # ------------------------------------------------------------------
    # Read
    # ------------------------------------------------------------------

    async def get(self, signal_id: str) -> dict[str, Any] | None:
        """Fetch a single signal by ID, scoped to tenant."""
        result = await self._db.execute(
            select(ValueSignalRow).where(
                and_(
                    ValueSignalRow.id == signal_id,
                    ValueSignalRow.tenant_id == self._tenant_id,
                    ValueSignalRow.deleted_at.is_(None),
                )
            )
        )
        row = result.scalar_one_or_none()
        return _row_to_dict(row) if row else None

    async def list(
        self,
        account_id: str,
        *,
        types: list[str] | None = None,
        lifecycle_states: list[str] | None = None,
        min_confidence: float | None = None,
        min_trust_score: float | None = None,
        impact_area: str | None = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[list[dict[str, Any]], int]:
        """List signals for an account, scoped to tenant. Returns (items, total)."""
        base_filter = and_(
            ValueSignalRow.tenant_id == self._tenant_id,
            ValueSignalRow.account_id == account_id,
            ValueSignalRow.deleted_at.is_(None),
        )

        filters = [base_filter]
        if types:
            filters.append(ValueSignalRow.type.in_(types))
        if lifecycle_states:
            filters.append(ValueSignalRow.lifecycle_state.in_(lifecycle_states))
        if min_confidence is not None:
            filters.append(ValueSignalRow.confidence >= min_confidence)
        if min_trust_score is not None:
            filters.append(ValueSignalRow.trust_score >= min_trust_score)
        if impact_area:
            filters.append(ValueSignalRow.impact_area == impact_area)

        combined = and_(*filters)

        count_result = await self._db.execute(
            select(func.count()).select_from(ValueSignalRow).where(combined)
        )
        total = count_result.scalar_one()

        result = await self._db.execute(
            select(ValueSignalRow)
            .where(combined)
            .order_by(ValueSignalRow.created_at.desc())
            .limit(limit)
            .offset(offset)
        )
        rows = result.scalars().all()
        return [_row_to_dict(r) for r in rows], total

    # ------------------------------------------------------------------
    # Write
    # ------------------------------------------------------------------

    async def create(self, data: dict[str, Any]) -> dict[str, Any]:
        """Insert a new ValueSignal row. tenant_id is always from self._tenant_id."""
        now = datetime.now(UTC)
        row = ValueSignalRow(
            id=data.get("id") or str(uuid.uuid4()),
            tenant_id=self._tenant_id,
            account_id=str(data["account_id"]),
            type=data["type"],
            content=data["content"],
            confidence=data["confidence"],
            trust_score=data.get("trust_score", 0.0),
            lifecycle_state=data.get("lifecycle_state", "draft"),
            evidence=data.get("evidence", []),
            provenance=data["provenance"],
            source_refs=data.get("source_refs", []),
            opportunity_id=str(data["opportunity_id"]) if data.get("opportunity_id") else None,
            value_driver_id=str(data["value_driver_id"]) if data.get("value_driver_id") else None,
            stakeholder_id=str(data["stakeholder_id"]) if data.get("stakeholder_id") else None,
            persona=data.get("persona"),
            industry=data.get("industry"),
            impact_area=data.get("impact_area"),
            estimated_value=data.get("estimated_value"),
            currency=data.get("currency"),
            time_horizon=data.get("time_horizon"),
            created_at=now,
            updated_at=now,
        )
        self._db.add(row)
        await self._db.flush()
        await self._db.refresh(row)
        return _row_to_dict(row)

    # Columns that exist on ValueSignalRow and are safe to update
    _UPDATABLE_COLUMNS = frozenset({
        "lifecycle_state", "validation_notes", "reviewer_id", "impact_area",
        "estimated_value", "currency", "time_horizon", "value_driver_id",
        "expires_at", "supersedes_signal_id", "related_signal_ids",
        "opportunity_id", "stakeholder_id", "persona", "industry",
        "reviewed_at", "updated_at",
    })

    async def update(self, signal_id: str, updates: dict[str, Any]) -> dict[str, Any] | None:
        """Partial update of a signal. Returns updated dict or None if not found.

        Only columns present in _UPDATABLE_COLUMNS are applied — unknown keys
        are silently dropped to prevent SQLAlchemy compile errors.
        """
        safe = {k: v for k, v in updates.items() if k in self._UPDATABLE_COLUMNS}
        safe["updated_at"] = datetime.now(UTC)
        await self._db.execute(
            update(ValueSignalRow)
            .where(
                and_(
                    ValueSignalRow.id == signal_id,
                    ValueSignalRow.tenant_id == self._tenant_id,
                    ValueSignalRow.deleted_at.is_(None),
                )
            )
            .values(**safe)
        )
        return await self.get(signal_id)

    async def soft_delete(self, signal_id: str) -> bool:
        """Soft-delete by setting deleted_at. Returns True if found and deleted."""
        result = await self._db.execute(
            update(ValueSignalRow)
            .where(
                and_(
                    ValueSignalRow.id == signal_id,
                    ValueSignalRow.tenant_id == self._tenant_id,
                    ValueSignalRow.deleted_at.is_(None),
                )
            )
            .values(
                deleted_at=datetime.now(UTC),
                lifecycle_state="rejected",
                updated_at=datetime.now(UTC),
            )
        )
        return result.rowcount > 0
