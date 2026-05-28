from __future__ import annotations

"""Durable CRM sync job model."""


import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from .account import CRMProvider


class CRMSyncJobStatus(str, PyEnum):
    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    CANCELLED = "cancelled"


class CRMSyncJob(Base):
    """Durable CRM sync execution record."""

    __tablename__ = "crm_sync_jobs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    provider: Mapped[CRMProvider] = mapped_column(String(50), nullable=False, index=True)
    status: Mapped[CRMSyncJobStatus] = mapped_column(
        String(50), nullable=False, default=CRMSyncJobStatus.QUEUED, index=True
    )
    requested_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    queued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    records_synced: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    error_summary: Mapped[str | None] = mapped_column(String(1000), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )

    def to_dict(self) -> dict[str, Any]:
        provider_val = self.provider.value if hasattr(self.provider, "value") else self.provider
        status_val = self.status.value if hasattr(self.status, "value") else self.status
        return {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "provider": provider_val,
            "status": status_val,
            "requested_by": self.requested_by,
            "queued_at": self.queued_at.isoformat() if self.queued_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "finished_at": self.finished_at.isoformat() if self.finished_at else None,
            "records_synced": self.records_synced,
            "records_updated": self.records_updated,
            "records_failed": self.records_failed,
            "error_summary": self.error_summary,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }
