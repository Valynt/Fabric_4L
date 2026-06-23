from __future__ import annotations

"""SQLAlchemy ORM model for FeatureFlag."""


import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import JSON, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base


class FeatureFlag(Base):
    """A tenant-scoped or platform-wide feature flag."""

    __tablename__ = "feature_flags"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=True,
        comment="Owning tenant (NULL for platform-wide flags)",
    )

    flag_key: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Feature flag identifier",
    )

    enabled: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
    )

    rollout_percentage: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="Percentage of users that should see the feature (0-100)",
    )

    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    metadata_: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSON,
        nullable=False,
        default=dict,
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    updated_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "flag_key", name="uix_feature_flag_tenant_key"),
        Index("ix_feature_flags_tenant_id", "tenant_id"),
        Index("ix_feature_flags_flag_key", "flag_key"),
    )

    def __repr__(self) -> str:
        return f"<FeatureFlag(id={self.id}, key={self.flag_key!r}, enabled={self.enabled})>"
