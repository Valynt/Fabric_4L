from __future__ import annotations

"""SQLAlchemy model for Tenant."""


import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from sqlalchemy import JSON, DateTime, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from ...database import Base


class TenantStatus(str, Enum):
    """Tenant lifecycle status with transition validation."""

    PENDING = "pending"  # Initial state after registration
    ACTIVE = "active"    # Fully operational
    SUSPENDED = "suspended"  # Access blocked but data preserved
    DELETED = "deleted"  # Soft-deleted (purged after retention period)


# Valid status transitions
# Format: {current_status: {allowed_next_statuses}}
VALID_STATUS_TRANSITIONS = {
    TenantStatus.PENDING: {TenantStatus.ACTIVE, TenantStatus.DELETED},
    TenantStatus.ACTIVE: {TenantStatus.SUSPENDED, TenantStatus.DELETED},
    TenantStatus.SUSPENDED: {TenantStatus.ACTIVE, TenantStatus.DELETED},
    TenantStatus.DELETED: set(),  # Terminal state - no transitions allowed
}


class IsolationTier(str, Enum):
    """Tenant data isolation tiers for future-proofing (Task 4.1).

    Tiers:
    - SHARED: Shared schema with RLS (current implementation)
    - SCHEMA: Dedicated schema per tenant (future)
    - DATABASE: Dedicated database per tenant (future)
    """

    SHARED = "shared"
    SCHEMA = "schema"
    DATABASE = "database"


def validate_status_transition(current_status: str, new_status: str) -> bool:
    """Validate if a status transition is allowed.

    Args:
        current_status: Current tenant status
        new_status: Requested new status

    Returns:
        True if transition is valid, False otherwise
    """
    try:
        current = TenantStatus(current_status)
        new = TenantStatus(new_status)
    except ValueError:
        return False

    return new in VALID_STATUS_TRANSITIONS.get(current, set())


class Tenant(Base):
    """A customer organisation that owns its own isolated data partition.

    All other governance tables (User, APIKey) and all content tables
    (accounts, KG nodes, etc.) reference ``tenant_id`` pointing here.
    """

    __tablename__ = "tenants"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        comment="Internal tenant UUID",
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        comment="Display name (e.g. 'Acme Corp')",
    )

    slug: Mapped[str] = mapped_column(
        String(63),
        nullable=False,
        unique=True,
        comment="URL-safe unique identifier (lowercase kebab-case)",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default=TenantStatus.PENDING.value,
        comment="Lifecycle status: pending | active | suspended | deleted",
    )

    settings: Mapped[dict[str, Any]] = mapped_column(
        JSON,
        nullable=False,
        default=lambda: {"isolation_tier": IsolationTier.SHARED.value},
        comment="Tenant-level configuration blob (rate limits, feature flags, isolation_tier, etc.)",
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

    status_changed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Timestamp of the last status transition",
    )

    status_reason: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable reason for the last status change (e.g. 'billing overdue')",
    )

    status_changed_by: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="User ID or service name that triggered the last status change",
    )

    # Relationship to tier history (Task 4.1)
    tier_history: Mapped[list[TenantIsolationTierHistory]] = relationship(
        "TenantIsolationTierHistory",
        back_populates="tenant",
        order_by="desc(TenantIsolationTierHistory.changed_at)",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        UniqueConstraint("slug", name="uix_tenant_slug"),
        Index("ix_tenants_status", "status"),
        Index("ix_tenants_created_at", "created_at"),
    )

    def __repr__(self) -> str:
        return f"<Tenant(id={self.id}, slug={self.slug!r}, status={self.status!r})>"

    # -------------------------------------------------------------------------
    # Status lifecycle methods
    # -------------------------------------------------------------------------

    def is_active(self) -> bool:
        """Check if tenant is active and can be accessed."""
        return self.status == TenantStatus.ACTIVE.value

    def is_suspended(self) -> bool:
        """Check if tenant is suspended."""
        return self.status == TenantStatus.SUSPENDED.value

    def is_deleted(self) -> bool:
        """Check if tenant is soft-deleted."""
        return self.status == TenantStatus.DELETED.value

    def is_pending(self) -> bool:
        """Check if tenant is pending provisioning."""
        return self.status == TenantStatus.PENDING.value

    def can_transition_to(self, new_status: str) -> bool:
        """Check if transition to new_status is valid."""
        return validate_status_transition(self.status, new_status)

    def transition_to(
        self,
        new_status: str,
        *,
        reason: str | None = None,
        changed_by: str | None = None,
    ) -> None:
        """Transition to a new lifecycle status with full audit trail.

        Args:
            new_status: Target status (must be a valid ``TenantStatus`` value).
            reason: Human-readable explanation (e.g. ``'billing overdue'``).
            changed_by: User ID or service name that initiated the change.

        Raises:
            ValueError: If the transition is not allowed by the state machine.
        """
        if not self.can_transition_to(new_status):
            raise ValueError(
                f"Invalid status transition: {self.status!r} -> {new_status!r}. "
                f"Allowed targets: {[s.value for s in VALID_STATUS_TRANSITIONS.get(TenantStatus(self.status), set())]}"
            )
        now = datetime.now(UTC)
        self.status = new_status
        self.status_changed_at = now
        self.status_reason = reason
        self.status_changed_by = changed_by
        self.updated_at = now

    # Convenience wrappers -------------------------------------------------------

    def activate(self, *, reason: str | None = None, changed_by: str | None = None) -> None:
        """Activate tenant (pending -> active or suspended -> active)."""
        self.transition_to(TenantStatus.ACTIVE.value, reason=reason, changed_by=changed_by)

    def suspend(self, *, reason: str | None = None, changed_by: str | None = None) -> None:
        """Suspend tenant (active -> suspended)."""
        self.transition_to(TenantStatus.SUSPENDED.value, reason=reason, changed_by=changed_by)

    def mark_deleted(self, *, reason: str | None = None, changed_by: str | None = None) -> None:
        """Soft-delete tenant."""
        self.transition_to(TenantStatus.DELETED.value, reason=reason, changed_by=changed_by)

    # Backward compat (deprecated) -----------------------------------------------

    def transition_status(self, new_status: str) -> bool:
        """DEPRECATED: Use ``transition_to()`` which raises on invalid transitions."""
        try:
            self.transition_to(new_status)
            return True
        except ValueError:
            return False
