"""Pydantic schemas for content-related API operations."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel


class SourceCorpusResponse(BaseModel):
    """SourceCorpus API response."""

    id: UUID
    tenant_id: UUID
    company_id: str | None
    company_name: str
    corpus_type: str
    source_groups: list[dict[str, Any]]
    candidate_concepts: list[str]
    provenance: list[dict[str, Any]]
    extraction_status: str
    created_at: datetime
    updated_at: datetime


class AccountIntelligencePacketResponse(BaseModel):
    """AccountIntelligencePacket API response."""

    id: UUID
    tenant_id: UUID
    account_id: str | None
    account_name: str
    packet_type: str
    company_profile: dict[str, Any]
    observed_signals: list[dict[str, Any]]
    likely_pain_areas: list[str]
    likely_stakeholders: list[str]
    source_references: list[dict[str, Any]]
    confidence_summary: dict[str, Any]
    next_recommended_events: list[str]
    created_at: datetime
    updated_at: datetime


class SourceCorpusSummary(BaseModel):
    """Summary view of a SourceCorpus for list responses.

    Omits raw provenance arrays to keep list payloads compact.
    """

    id: UUID
    company_name: str
    company_id: str | None
    corpus_type: str
    source_count: int
    extraction_status: str
    created_at: datetime


class SourceCorpusListResponse(BaseModel):
    """Paginated list of SourceCorpus summaries."""

    items: list[SourceCorpusSummary]
    total: int
    limit: int
    next_cursor: str | None


class AccountIntelligencePacketSummary(BaseModel):
    """Summary view of an AccountIntelligencePacket for list responses.

    Omits raw source_references to keep list payloads compact.
    """

    id: UUID
    account_name: str
    account_id: str | None
    packet_type: str
    observed_signal_count: int
    high_confidence_signal_count: int
    created_at: datetime


class AccountIntelligencePacketListResponse(BaseModel):
    """Paginated list of AccountIntelligencePacket summaries."""

    items: list[AccountIntelligencePacketSummary]
    total: int
    limit: int
    next_cursor: str | None


class RawContentResponse(BaseModel):
    """Raw content response."""

    id: UUID
    job_id: UUID
    url: str
    content_type: str
    content_hash: str
    content_length: int
    storage_location: str
    metadata: dict[str, Any] | None = None
    created_at: datetime


class ExtractedDataResponse(BaseModel):
    """Extracted data response."""

    id: UUID
    job_id: UUID
    source_url: str
    extraction_method: str
    schema_version: str
    data: dict[str, Any]
    confidence_score: float | None = None
    extraction_metadata: dict[str, Any] | None = None
    created_at: datetime


class ContentListResponse(BaseModel):
    """List of raw content items."""

    items: list[RawContentResponse]
    total: int
    limit: int
    next_cursor: str | None


class CrawlDecisionSummary(BaseModel):
    """Summary of a crawl decision for API responses."""

    decision_id: UUID
    job_id: UUID
    url: str
    decision: str
    reason: str | None = None
    created_at: datetime


class RouterQualityReportResponse(BaseModel):
    """Quality metrics for a job's routing decisions."""

    job_id: UUID
    total_urls: int
    successful_urls: int
    failed_urls: int
    skipped_urls: int
    average_response_time_ms: float
    fastest_url: str | None
    slowest_url: str | None


class DomainFallbackStatsResponse(BaseModel):
    """Fallback statistics for a domain."""

    domain: str
    total_attempts: int
    successful_attempts: int
    fallback_count: int
    average_response_time_ms: float
    last_attempt_at: datetime | None = None
