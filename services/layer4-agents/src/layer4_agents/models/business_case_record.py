from __future__ import annotations

"""Durable business case records."""


from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class BusinessCaseRecord(Base):
    """Persistent record linking workflow-generated business cases to accounts."""

    __tablename__ = "business_case_records"

    case_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    account_id: Mapped[UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("accounts.id", ondelete="CASCADE"),
        nullable=False,
    )
    workflow_id: Mapped[str] = mapped_column(String(100), nullable=False)
    opportunity_id: Mapped[str | None] = mapped_column(String(100), nullable=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default",
        comment="Tenant identifier for RLS isolation",
    )
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="unknown")
    document_url: Mapped[str | None] = mapped_column(String(1024), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    __table_args__ = (
        Index("ix_business_case_records_account_id", "account_id"),
        Index("ix_business_case_records_workflow_id", "workflow_id"),
        Index("ix_business_case_records_tenant_id", "tenant_id"),
        Index("ix_business_case_records_tenant_status", "tenant_id", "status"),
    )

