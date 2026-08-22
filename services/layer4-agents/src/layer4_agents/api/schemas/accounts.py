from __future__ import annotations

"""
Pydantic schemas for Accounts API.

Request/response models for the accounts surface.
"""


from datetime import datetime
from decimal import Decimal
from enum import Enum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from ...models.account import CRMProvider, SyncStatus

# ============================================================================
# Embedded Data Schemas
# ============================================================================


class OpportunitySchema(BaseModel):
    """Opportunity data embedded in account detail response."""

    provider_opportunity_id: str
    name: str
    stage: str
    value: Decimal | None = None
    probability: float | None = None
    close_date: str | None = None
    last_synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ContactSchema(BaseModel):
    """Contact data embedded in account detail response."""

    provider_contact_id: str
    name: str
    title: str | None = None
    email: str | None = None
    phone: str | None = None
    is_primary: bool = False
    last_synced_at: datetime

    model_config = ConfigDict(from_attributes=True)


class ActivityItemSchema(BaseModel):
    """Activity timeline item from fetch_interaction_history tool."""

    id: str
    type: str  # call, email, meeting, task
    date: str
    subject: str | None = None
    duration_minutes: int | None = None
    notes: str | None = None
    outcome: str | None = None

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# List/Search Response Schemas
# ============================================================================


class AccountListItemSchema(BaseModel):
    """Account item in list response."""

    id: UUID
    provider: CRMProvider
    name: str
    domain: str | None = None
    industry: str | None = None
    region: str | None = None
    company_size: int | None = None
    owner_name: str | None = None
    stage: str | None = None
    segment: str | None = None
    sync_status: SyncStatus
    last_synced_at: datetime | None = None
    updated_at: datetime

    # Source attribution
    provider_badge: str = Field(..., description="Display badge: 'Salesforce' or 'HubSpot'")

    model_config = ConfigDict(from_attributes=True)


class AccountListResponse(BaseModel):
    """Paginated account list response."""

    items: list[AccountListItemSchema]
    total: int
    page: int
    page_size: int
    has_more: bool


class AccountSearchRequest(BaseModel):
    """Account search request body."""

    query: str | None = Field(None, description="Search across name, domain, owner")
    provider: CRMProvider | None = None
    stage: str | None = None
    industry: str | None = None
    region: str | None = None
    segment: str | None = None
    owner_id: str | None = None
    sync_status: SyncStatus | None = None

    # Pagination
    page: int = Field(1, ge=1)
    page_size: int = Field(20, ge=1, le=100)

    # Sorting
    sort_by: str = Field("updated_at", pattern="^(name|updated_at|company_size|last_synced_at)$")
    sort_order: str = Field("desc", pattern="^(asc|desc)$")


class CreateAccountRequest(BaseModel):
    """Account creation request.

    Supports both CRM-imported accounts (provider=salesforce|hubspot)
    and manually created accounts (provider=manual).
    For manual accounts, provider_record_id is auto-generated if omitted.
    """

    id: UUID | None = Field(
        None, description="Optional deterministic account UUID for validation seeding"
    )
    provider: CRMProvider
    provider_record_id: str | None = Field(
        None,
        min_length=1,
        max_length=100,
        description="Original CRM record ID. Auto-generated for manual accounts.",
    )
    name: str = Field(..., min_length=1, max_length=255)
    domain: str | None = Field(None, max_length=255)
    industry: str | None = Field(None, max_length=100)
    region: str | None = Field(None, max_length=100)
    company_size: int | None = Field(None, ge=0)
    annual_revenue: float | None = Field(None, ge=0, description="Annual revenue in USD")
    headquarters: str | None = Field(None, max_length=255)
    website: str | None = Field(None, max_length=255)
    owner_id: str | None = Field(None, max_length=100)
    owner_name: str | None = Field(None, max_length=255)
    owner_email: str | None = Field(None, max_length=255)
    stage: str | None = Field(None, max_length=50)
    segment: str | None = Field(None, max_length=100)


# ============================================================================
# Detail Response Schema
# ============================================================================


class AccountDetailSchema(BaseModel):
    """Full account detail response."""

    # Canonical identity
    id: UUID
    provider: CRMProvider
    provider_record_id: str

    # Firmographics
    name: str
    domain: str | None = None
    industry: str | None = None
    region: str | None = None
    company_size: int | None = None
    annual_revenue: float | None = None
    headquarters: str | None = None
    website: str | None = None

    # CRM linkage
    owner_id: str | None = None
    owner_name: str | None = None
    owner_email: str | None = None
    stage: str | None = None
    segment: str | None = None

    # Sync metadata
    created_at: datetime
    updated_at: datetime
    last_synced_at: datetime | None = None
    sync_status: SyncStatus

    # Source attribution
    source_attribution: str = Field(
        ..., description="Human-readable sync info: 'Synced from Salesforce 2 hours ago'"
    )
    provider_badge: str = Field(..., description="Display badge: 'Salesforce' or 'HubSpot'")

    # Embedded related data (Phase 1: subordinate sections)
    opportunities: list[OpportunitySchema] = []
    contacts: list[ContactSchema] = []

    model_config = ConfigDict(from_attributes=True)


# ============================================================================
# Activity Response Schema
# ============================================================================


class AccountActivityResponse(BaseModel):
    """Account activity timeline response."""

    account_id: UUID
    interactions: list[ActivityItemSchema]
    total_count: int
    summary: str | None = None


# ============================================================================
# Sync Request/Response Schemas
# ============================================================================


class SyncAccountsRequest(BaseModel):
    """Manual sync trigger request."""

    provider: CRMProvider | None = Field(
        None, description="Specific provider to sync, or null for all"
    )
    account_ids: list[str] | None = Field(
        None, description="Specific account IDs to sync, or null for all"
    )
    force_refresh: bool = Field(False, description="Force re-sync even if data is fresh")


class SyncAccountsResponse(BaseModel):
    """Sync trigger response."""

    sync_id: str = Field(..., description="Unique sync job identifier")
    status: str = Field(..., description="Sync status: queued, running, completed, failed")
    provider: CRMProvider | None = None
    message: str


class SyncStatusSchema(BaseModel):
    """Per-provider sync status."""

    provider: CRMProvider
    status: str  # idle, running, failed
    last_sync_at: datetime | None = None
    last_successful_sync_at: datetime | None = None
    records_synced: int
    records_updated: int
    records_failed: int
    error_message: str | None = None

    model_config = ConfigDict(from_attributes=True)


class SyncStatusListResponse(BaseModel):
    """All providers sync status response."""

    providers: list[SyncStatusSchema]
    overall_status: str  # healthy, degraded, unhealthy


# ============================================================================
# Filter Options Schema
# ============================================================================


class AccountFilterOptionsResponse(BaseModel):
    """Available filter options for account list."""

    industries: list[str]
    stages: list[str]
    regions: list[str]
    segments: list[str]
    providers: list[CRMProvider]
    owners: list[dict[str, Any]]


# ============================================================================
# Journey Timeline Schemas (Pillar 2)
# ============================================================================


class JourneyStageStatus(str, Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    BLOCKED = "blocked"
    FAILED = "failed"


class JourneyTimelineStage(BaseModel):
    id: str
    label: str  # Signal, Hypothesis, Value drivers, ROI calculation, Evidence validation, Narrative, Export or CRM sync
    stage_key: str  # signal, hypothesis, value_drivers, roi_calculation, evidence_validation, narrative, export_crm_sync
    status: JourneyStageStatus = JourneyStageStatus.NOT_STARTED
    updated_at: datetime | None = None
    actor: str | None = None
    source_artifact_id: str | None = None
    target_artifact_id: str | None = None
    evidence_links: list[str] = Field(default_factory=list)
    truth_object_ids: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    degradation_reason: str | None = None
    deep_link: str | None = None


class AccountJourneyTimelineResponse(BaseModel):
    tenant_id: str
    account_id: str
    journey_id: str
    stages: list[JourneyTimelineStage]
    current_stage_key: str
    updated_at: datetime

    providers: list[CRMProvider]
    owners: list[dict[str, str]]  # [{"id": "...", "name": "..."}]
