from __future__ import annotations

"""
SQLAlchemy models for CRM Accounts.

Phase 1: Accounts-first operational surface with embedded opportunities/contacts.
Canonical identity model ensures clean deduplication when one company appears
from both Salesforce and HubSpot.

Architecture:
- Layer 4 Postgres = system of record for operational account data
- Layer 3 KG = optional downstream graph projection (deferred to Phase 2+)
"""


import uuid
from datetime import UTC, datetime
from enum import Enum as PyEnum
from typing import Any

from sqlalchemy import (
    JSON,
    DateTime,
    Float,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from value_fabric.shared.crypto import EncryptedString

from ..database import Base

# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class SyncStatus(str, PyEnum):
    """Account sync status from CRM provider."""

    SYNCED = "synced"
    PENDING = "pending"
    FAILED = "failed"
    STALE = "stale"


class CRMProvider(str, PyEnum):
    """Supported CRM providers."""

    SALESFORCE = "salesforce"
    HUBSPOT = "hubspot"
    MANUAL = "manual"


# ---------------------------------------------------------------------------
# Embedded Data Schemas (stored as JSONB)
# ---------------------------------------------------------------------------


class EmbeddedOpportunity:
    """Schema for opportunity data embedded in account record.

    Not a separate table - stored as JSONB array in account.opportunities.
    """

    provider_opportunity_id: str
    name: str
    stage: str
    value: float | None = None
    probability: float | None = None
    close_date: str | None = None  # ISO date string
    last_synced_at: str  # ISO datetime string


class EmbeddedContact:
    """Schema for contact data embedded in account record.

    Not a separate table - stored as JSONB array in account.contacts.
    """

    provider_contact_id: str
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    is_primary: bool = False
    last_synced_at: str  # ISO datetime string


# ---------------------------------------------------------------------------
# Account Model
# ---------------------------------------------------------------------------


class Account(Base):
    """Canonical CRM account record with embedded opportunities and contacts.

    Design notes:
    - Canonical identity: internal UUID + provider + provider_record_id
    - Normalized name for deduplication across providers
    - Opportunities/contacts embedded as JSONB (Phase 1: not separate tables)
    - Raw CRM data preserved for debugging and re-sync
    """

    __tablename__ = "accounts"

    # -----------------------------------------------------------------------
    # Canonical Identity (Phase 1 guardrail for deduplication)
    # -----------------------------------------------------------------------

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, comment="Internal canonical UUID"
    )

    provider: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="Source CRM: salesforce or hubspot"
    )

    provider_record_id: Mapped[str] = mapped_column(
        String(100), nullable=False, comment="Original ID from CRM provider"
    )

    # -----------------------------------------------------------------------
    # Normalization Fields
    # -----------------------------------------------------------------------

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Company name as displayed"
    )

    normalized_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Lowercase, stripped name for deduplication matching"
    )

    domain: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Primary company domain (e.g., 'apple.com')"
    )

    # -----------------------------------------------------------------------
    # Firmographics
    # -----------------------------------------------------------------------

    industry: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Industry classification"
    )

    region: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Geographic region (state/country from CRM)"
    )

    company_size: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Employee count"
    )

    annual_revenue: Mapped[float | None] = mapped_column(
        Float, nullable=True, comment="Annual revenue in USD"
    )

    headquarters: Mapped[str | None] = mapped_column(
        EncryptedString(), nullable=True, comment="City, State or full address (encrypted at rest)"
    )

    website: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Company website URL"
    )

    # -----------------------------------------------------------------------
    # CRM Linkage
    # -----------------------------------------------------------------------

    owner_id: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="CRM owner/user ID"
    )

    owner_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Owner display name"
    )

    owner_email: Mapped[str | None] = mapped_column(
        EncryptedString(), nullable=True, comment="Owner email address (encrypted at rest)"
    )

    stage: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Account stage: prospect, qualified, opportunity, customer",
    )

    segment: Mapped[str | None] = mapped_column(
        String(100), nullable=True, comment="Account segment (type from CRM: Customer, Partner, etc.)"
    )

    employees: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Employee count (alias for company_size from CRM sync)",
    )

    # -----------------------------------------------------------------------
    # Sync Metadata
    # -----------------------------------------------------------------------

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        comment="Record creation timestamp",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
        comment="Last update timestamp",
    )

    last_synced_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last successful CRM sync timestamp"
    )

    sync_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default=SyncStatus.PENDING.value, comment="Current sync state"
    )

    # -----------------------------------------------------------------------
    # Provenance
    # -----------------------------------------------------------------------

    raw_crm_data: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True, comment="Full provider payload for debugging and re-sync"
    )

    # -----------------------------------------------------------------------
    # Multi-Tenancy
    # -----------------------------------------------------------------------

    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default",
        comment="Tenant identifier for RLS isolation",
    )

    # -----------------------------------------------------------------------
    # Embedded Related Data (Phase 1: JSONB, not separate tables)
    # -----------------------------------------------------------------------

    opportunities: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, comment="Embedded opportunities from CRM provider"
    )

    contacts: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list, comment="Embedded contacts from CRM provider"
    )

    # -----------------------------------------------------------------------
    # Enrichment Data (Data Intelligence Layer Phase 1)
    # -----------------------------------------------------------------------

    enrichment_status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="pending",
        comment="Enrichment state: pending, in_progress, enriched, failed, stale",
    )

    enriched_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True,
        comment="Last successful enrichment timestamp",
    )

    enrichment_sources: Mapped[list[str]] = mapped_column(
        JSON, nullable=False, default=list,
        comment="List of sources used for enrichment (e.g., sec_edgar, web_crawl)",
    )

    tech_stack: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
        comment="Detected technology stack: {category: [technologies]}",
    )

    executives: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Key executives: [{name, title, linkedin_url, email}]",
    )

    financials: Mapped[dict[str, Any] | None] = mapped_column(
        JSON, nullable=True,
        comment="Financial data from SEC/public sources: {revenue, growth_rate, margins, fiscal_year}",
    )

    competitive_landscape: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Known competitors: [{name, domain, overlap_areas}]",
    )

    pain_signals: Mapped[list[dict[str, Any]]] = mapped_column(
        JSON, nullable=False, default=list,
        comment="Detected pain signals: [{signal, source, confidence, detected_at}]",
    )

    # -----------------------------------------------------------------------
    # Table Configuration
    # -----------------------------------------------------------------------

    __table_args__ = (
        # Unique constraint: one record per provider+record_id combination
        UniqueConstraint("tenant_id", "provider", "provider_record_id", name="uix_account_tenant_provider_record"),
        # Indexes for common query patterns
        Index("ix_accounts_provider", "provider"),
        Index("ix_accounts_sync_status", "sync_status"),
        Index("ix_accounts_name", "name"),
        Index("ix_accounts_domain", "domain"),
        Index("ix_accounts_owner_id", "owner_id"),
        Index("ix_accounts_last_synced_at", "last_synced_at"),
        Index("ix_accounts_region", "region"),
        Index("ix_accounts_segment", "segment"),
        # Composite index for list queries: synced accounts by update time
        Index("ix_accounts_provider_sync_updated", "provider", "sync_status", "updated_at"),
        # Enrichment indexes
        Index("ix_accounts_enrichment_status", "enrichment_status"),
        Index("ix_accounts_tenant_id", "tenant_id"),
    )

    def __repr__(self) -> str:
        return f"<Account(id={self.id}, name='{self.name}', provider={self.provider})>"


# ---------------------------------------------------------------------------
# Sync Status Tracking
# ---------------------------------------------------------------------------


class AccountSyncStatus(Base):
    """Per-provider sync status and statistics.

    Tracks overall sync health per CRM provider, not per-account.
    """

    __tablename__ = "account_sync_status"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    tenant_id: Mapped[str] = mapped_column(
        String(100), nullable=False, default="default",
        comment="Tenant identifier for sync status isolation",
    )

    provider: Mapped[str] = mapped_column(
        String(20), nullable=False, comment="CRM provider: salesforce or hubspot"
    )

    last_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last sync attempt timestamp"
    )

    last_successful_sync_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True, comment="Last successful sync completion"
    )

    records_synced: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Total accounts synced in last run"
    )

    records_updated: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Accounts updated in last run"
    )

    records_failed: Mapped[int] = mapped_column(
        Integer, nullable=False, default=0, comment="Accounts failed in last run"
    )

    error_message: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Error details if sync failed"
    )

    status: Mapped[str] = mapped_column(
        String(20),
        nullable=False,
        default="idle",
        comment="Current sync state: idle, running, failed",
    )

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC)
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC)
    )

    __table_args__ = (
        UniqueConstraint("tenant_id", "provider", name="uix_sync_status_tenant_provider"),
        Index("ix_sync_status_tenant_provider", "tenant_id", "provider", "status"),
    )

    def __repr__(self) -> str:
        return f"<AccountSyncStatus(provider={self.provider}, status={self.status})>"
