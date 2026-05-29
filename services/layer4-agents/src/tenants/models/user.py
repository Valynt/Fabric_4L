from __future__ import annotations

"""SQLAlchemy model for User.

User passwords are hashed with bcrypt (appropriate for human credentials,
unlike API keys which use HMAC-SHA256 for throughput reasons).
"""


import uuid
from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey, Index, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, validates
from value_fabric.shared.crypto import EncryptedString, blind_index

from ...database import Base


class User(Base):
    """A human user belonging to exactly one tenant."""

    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )

    tenant_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("tenants.id", ondelete="CASCADE"),
        nullable=False,
        comment="Owning tenant",
    )

    email: Mapped[str] = mapped_column(
        EncryptedString(),
        nullable=False,
        comment="Email address (encrypted at rest, unique per tenant)",
    )

    email_hash: Mapped[str | None] = mapped_column(
        String(64),
        nullable=True,
        index=True,
        comment="Blind index (HMAC-SHA256) for exact-match email lookups",
    )

    # bcrypt hash — never store raw passwords
    hashed_password: Mapped[str | None] = mapped_column(
        String(72),
        nullable=True,
        comment="bcrypt hash of the user's password (null until user activates invite)",
    )

    display_name: Mapped[str | None] = mapped_column(
        String(200),
        nullable=True,
    )

    role: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
        default="analyst",
        comment="Canonical role from shared.identity.permissions.Role",
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="invited",
        comment="Lifecycle: invited | active | deactivated",
    )

    last_login_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    invited_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        comment="User who sent the invite",
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

    __table_args__ = (
        # Email uniqueness is scoped to tenant via blind index
        UniqueConstraint("tenant_id", "email_hash", name="uix_user_tenant_email"),
        Index("ix_users_tenant_id", "tenant_id"),
        Index("ix_users_email_hash", "email_hash"),
        Index("ix_users_status", "status"),
        Index("ix_users_tenant_status", "tenant_id", "status"),
    )

    @validates("email")
    def _sync_email_hash(self, _key: str, email: str | None) -> str | None:
        """Keep the blind index in sync with the plaintext email."""
        self.email_hash = blind_index(email)
        return email

    def __repr__(self) -> str:
        return f"<User(id={self.id}, email={self.email!r}, role={self.role!r})>"
