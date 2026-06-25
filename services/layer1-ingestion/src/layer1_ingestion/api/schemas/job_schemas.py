"""Pydantic schemas for job-related API operations."""
from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, field_validator


class JobSummary(BaseModel):
    """Summary of a scraping job."""

    id: UUID
    target_id: UUID
    status: str
    priority: int
    progress_percent_complete: int
    created_at: datetime
    started_at: datetime | None = None
    completed_at: datetime | None = None


class JobStageDetailResponse(BaseModel):
    """Pipeline stage detail."""

    stage: str
    status: str
    started_at: datetime | None = None
    completed_at: datetime | None = None
    duration_ms: int | None = None
    error_message: str | None = None


class JobErrorResponse(BaseModel):
    """Job error detail."""

    id: UUID
    stage: str
    error_code: str
    error_message: str
    url: str | None = None
    retryable: bool
    retry_count: int
    occurred_at: datetime
    resolved_at: datetime | None = None


class ResourceUsageDetail(BaseModel):
    """Resource usage metrics."""

    browser_sessions_used: int
    proxy_requests_made: int
    llm_tokens_consumed: int
    compute_time_ms: int


class JobResultsDetail(BaseModel):
    """Job results summary."""

    raw_content_count: int
    extracted_record_count: int
    storage_bytes_used: int
    output_location: str | None = None


class JobProgressDetail(BaseModel):
    """Job progress information."""

    total_pages: int | None = None
    processed_pages: int
    failed_pages: int
    current_url: str | None = None
    current_stage: str
    percent_complete: int


class ScrapingJobDetail(BaseModel):
    """Detailed job response."""

    id: UUID
    tenant_id: UUID
    target_id: UUID
    configuration: dict[str, Any]
    status: str
    priority: int
    scheduled_at: datetime | None = None
    started_at: datetime | None = None
    completed_at: datetime | None = None
    estimated_duration_ms: int | None = None
    progress: JobProgressDetail
    results: JobResultsDetail
    resources: ResourceUsageDetail
    triggered_by: str
    correlation_id: str | None = None
    created_at: datetime
    created_by: UUID
    stages: list[JobStageDetailResponse]
    errors: list[JobErrorResponse]


class JobListResponse(BaseModel):
    """List of jobs response."""

    data: list[JobSummary]
    aggregation: dict[str, Any]
    pagination: dict[str, Any]


class RetryJobRequest(BaseModel):
    """Request to retry a job."""

    retry_strategy: str = "FULL"
    from_stage: str | None = None
    max_retries: int = 3

    @field_validator("retry_strategy")
    @classmethod
    def validate_retry_strategy(cls, v: str) -> str:
        allowed = {"FULL", "PARTIAL", "FROM_STAGE"}
        if v not in allowed:
            raise ValueError(
                f"retry_strategy must be one of {sorted(allowed)}, got '{v}'"
            )
        return v


class CreateLicensingCompanyIntakeRequest(BaseModel):
    """Request to create a licensing company ontology intake job."""

    target_id: UUID
    company_name: str
    company_id: str | None = None
    priority: int = 5
    override_config: dict[str, Any] | None = None


class CreateProspectResearchRequest(BaseModel):
    """Request to create a prospect research job."""

    target_id: UUID
    account_name: str
    account_id: str | None = None
    priority: int = 5
    override_config: dict[str, Any] | None = None


class SkillJobResponse(BaseModel):
    """Response for skill-aware job creation."""

    job_id: UUID
    status: str
    job_type: str
    skill_name: str
    queue_position: int
    queue_position_metadata: dict[str, str]
    estimated_start_time: datetime | None = None


class JobProgressResponse(BaseModel):
    """Real-time job progress."""

    job_id: UUID
    status: str
    progress: JobProgressDetail
    last_update: datetime
