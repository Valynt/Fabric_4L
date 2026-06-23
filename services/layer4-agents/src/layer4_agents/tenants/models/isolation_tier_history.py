from __future__ import annotations

"""SQLAlchemy model for Tenant Isolation Tier History (Task 4.1).

Append-only audit log for isolation tier changes. Tracks who changed the tier,
when, and why - essential for governance, compliance, and incident review.
"""


import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database import Base


class TenantIsolationTierHistory(Base):
    """Audit history for tenant isolation tier changes.

    This table provides immutable, queryable history of tier changes
    for governance, compliance, and incident review purposes.

    Current tier state lives in Tenant.settings["isolation_tier"].
    This table provides the change history.
    """

    __tablename__ = "tenant_isolation_tier_history"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Internal history record UUID",
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
        comment="Reference to the tenant whose tier changed",
    )

    from_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="Previous isolation tier value",
    )

    to_tier: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        comment="New isolation tier value",
    )

    changed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="When the change occurred",
    )

    changed_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="User or service account that made the change",
    )

    reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable reason for the tier change",
    )

    change_source: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="admin",
        comment="Source of change: system | migration | admin | policy_engine | api",
    )

    request_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Request ID for correlation with audit logs",
    )

    # Relationship to tenant (optional, for convenience)
    tenant: Mapped[Tenant] = relationship("Tenant", back_populates="tier_history")

    __table_args__ = (
        Index("ix_tier_history_tenant_changed", "tenant_id", "changed_at"),
        Index("ix_tier_history_source", "change_source"),
    )

    def __repr__(self) -> str:
        return (
            f"<TenantIsolationTierHistory("
            f"tenant={self.tenant_id}, "
            f"{self.from_tier!r} -> {self.to_tier!r}, "
            f"at={self.changed_at.isoformat()}"
            f")>"
        )
