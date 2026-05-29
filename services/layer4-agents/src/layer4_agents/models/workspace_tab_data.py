from __future__ import annotations

"""Workspace tab persistence model.

Stores JSON-blob tab data per case, enabling workspace tabs to persist
and retrieve state without requiring a full AI generation pipeline.
"""


from datetime import UTC, datetime

from sqlalchemy import DateTime, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class WorkspaceTabData(Base):
    """Persistent storage for workspace tab data."""

    __tablename__ = "workspace_tab_data"

    case_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    tab_key: Mapped[str] = mapped_column(String(50), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default",
        comment="Tenant identifier for RLS isolation",
    )
    data: Mapped[dict | list | None] = mapped_column(
        JSONB, nullable=True, default=dict,
        comment="Opaque JSON blob storing tab-specific data",
    )
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
        Index("ix_workspace_tab_data_case_id", "case_id"),
        Index("ix_workspace_tab_data_tenant_id", "tenant_id"),
    )
