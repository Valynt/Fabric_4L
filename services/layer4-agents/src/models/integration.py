from __future__ import annotations

"""
SQLAlchemy models for CRM Integration configurations.

Stores encrypted credentials and sync configuration for Salesforce and HubSpot.
Credentials are encrypted at rest using AES-256 via the encryption service.
"""


import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    Boolean,
    DateTime,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from ..database import Base
from ..models.account import CRMProvider


class IntegrationStatus(str, PyEnum):
    """Integration connection and sync status."""

    IDLE = "idle"
    RUNNING = "running"
    FAILED = "failed"
    PENDING = "pending"
    DEGRADED = "degraded"  # Token expired but refreshable, or partial sync failure


class Integration(Base):
    """CRM Integration configuration with encrypted credentials.

    Security:
        - Credentials are encrypted at rest (AES-256)
        - Encryption key ID stored separately for key rotation
        - Credentials never returned in API responses
        - Audit logging for all CRUD operations
    """

    __tablename__ = "integrations"

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uq_integration_tenant_provider"),
    )

    # Primary key
    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )

    # Tenant isolation (required for multi-tenancy)
    tenant_id: Mapped[str] = mapped_column(String(255), nullable=False, index=True)

    # Provider type
    provider: Mapped[CRMProvider] = mapped_column(
        String(50), nullable=False
    )

    # Enablement flag
    enabled: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    # Encrypted credentials (AES-256 encrypted)
    # Structure: {"api_key": "...", "api_secret": "...", "instance_url": "..."}
    credentials_encrypted: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )

    # OAuth refresh token (encrypted separately for rotation/audit)
    refresh_token_encrypted: Mapped[bytes | None] = mapped_column(
        LargeBinary, nullable=True
    )

    # Encryption key reference for credential rotation
    encryption_key_id: Mapped[str] = mapped_column(String(255), nullable=False)

    # Salesforce-specific metadata
    salesforce_org_id: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Configuration
    instance_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    sync_interval_minutes: Mapped[int] = mapped_column(
        Integer, nullable=False, default=60
    )
    sync_batch_size: Mapped[int] = mapped_column(
        Integer, nullable=False, default=100
    )

    # Sync status (denormalized for quick reads)
    last_sync_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    records_synced: Mapped[int] = mapped_column(Integer, default=0)
    records_updated: Mapped[int] = mapped_column(Integer, default=0)
    records_failed: Mapped[int] = mapped_column(Integer, default=0)
    sync_status: Mapped[IntegrationStatus] = mapped_column(
        String(50), default=IntegrationStatus.IDLE, nullable=False
    )
    last_error_message: Mapped[str | None] = mapped_column(String(1000), nullable=True)

    # Metadata
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(UTC), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        nullable=False,
    )
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    updated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    def to_dict(self, include_credentials: bool = False) -> dict[str, Any]:
        """Convert to dictionary for API responses.

        Args:
            include_credentials: If True, include decrypted credentials (internal use only)

        Returns:
            Dictionary representation, credentials excluded by default
        """
        # Handle both enum instances and string values from SQLAlchemy
        provider_val = self.provider.value if hasattr(self.provider, 'value') else self.provider
        status_val = self.sync_status.value if hasattr(self.sync_status, 'value') else self.sync_status

        result = {
            "id": str(self.id),
            "tenant_id": self.tenant_id,
            "provider": provider_val,
            "enabled": self.enabled,
            "instance_url": self.instance_url,
            "sync_interval_minutes": self.sync_interval_minutes,
            "sync_batch_size": self.sync_batch_size,
            "last_sync_at": self.last_sync_at.isoformat() if self.last_sync_at else None,
            "last_successful_sync_at": self.last_successful_sync_at.isoformat()
            if self.last_successful_sync_at
            else None,
            "records_synced": self.records_synced,
            "records_updated": self.records_updated,
            "records_failed": self.records_failed,
            "status": status_val,
            "last_error_message": self.last_error_message,
            "has_refresh_token": bool(self.refresh_token_encrypted),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

        if include_credentials:
            # Only for internal service use, never API responses
            result["_credentials_encrypted"] = "<encrypted>"

        return result
