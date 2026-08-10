"""Fail-closed deterministic seed boundary for backend-integrated validation."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Literal, cast
from urllib.parse import urlparse
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException
from pydantic import BaseModel, Field, field_validator
from sqlalchemy.orm import Session

from ..shared.config import is_production_like_environment, settings
from ..shared.database import get_db_from_context_sync
from ..shared.models import (
    JobStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingTarget,
    TargetStatus,
    TargetType,
    TriggeredBy,
    create_scraping_job,
    create_scraping_target,
)
from .dependencies import get_current_user_id, get_current_user_roles, get_tenant_id

router = APIRouter()
_SEED_REASON = "validation-seed"
_SEED_CORRELATION_ID = "e2e-validation-seed"


class ValidationJobSeedRequest(BaseModel):
    """A deterministic completed ingestion job used only by validation stacks."""

    domain: str = Field(min_length=1, max_length=253)
    url: str = Field(min_length=1, max_length=2048)
    status: Literal["COMPLETED"] = "COMPLETED"

    @field_validator("domain")
    @classmethod
    def normalize_domain(cls, value: str) -> str:
        return value.strip().lower().rstrip(".")

    @field_validator("url")
    @classmethod
    def require_matching_https_url(cls, value: str, info) -> str:
        normalized = value.strip()
        parsed = urlparse(normalized)
        domain = str(info.data.get("domain", ""))
        if parsed.scheme != "https" or not parsed.hostname or parsed.hostname.lower() != domain:
            raise ValueError("url must be an HTTPS URL for domain")
        return normalized


class ValidationJobSeedResponse(BaseModel):
    seeded: bool
    target_id: UUID
    job_id: UUID
    domain: str
    status: str
    progress_percent_complete: int


def authorize_validation_seed(
    *,
    environment: str,
    privileged_reason: str | None,
    roles: list[str],
) -> None:
    """Allow only an explicit super-admin validation action outside production."""

    if (
        is_production_like_environment(environment)
        or privileged_reason != _SEED_REASON
        or "super_admin" not in roles
    ):
        raise HTTPException(status_code=403, detail="Validation seed endpoint is disabled")


def seed_validation_job(
    *,
    request: ValidationJobSeedRequest,
    privileged_reason: str | None,
    org_id: UUID,
    user_id: UUID,
    roles: list[str],
    db: Session,
    environment: str,
) -> ValidationJobSeedResponse:
    """Idempotently persist one tenant-scoped completed target/job fixture."""

    authorize_validation_seed(
        environment=environment,
        privileged_reason=privileged_reason,
        roles=roles,
    )

    target = (
        db.query(ScrapingTarget)
        .filter(
            ScrapingTarget.tenant_id == org_id,
            ScrapingTarget.url == request.url,
        )
        .first()
    )
    if target is None:
        target = create_scraping_target(
            tenant_id=org_id,
            name=f"Validation target: {request.domain}",
            url=request.url,
            target_type=TargetType.SINGLE_PAGE,
            created_by=user_id,
            extraction_config={"method": "DETERMINISTIC"},
            compliance={"domain_allowlist": [request.domain]},
            tags=["e2e-validation"],
        )
        db.add(target)
        db.flush()
    setattr(target, "status", TargetStatus.ACTIVE.value)
    setattr(target, "last_success_at", datetime.now(UTC))
    setattr(target, "success_count", max(cast(int | None, target.success_count) or 0, 1))
    target_id = cast(UUID, target.id)

    job = (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.tenant_id == org_id,
            ScrapingJob.target_id == target_id,
            ScrapingJob.correlation_id == _SEED_CORRELATION_ID,
        )
        .first()
    )
    if job is None:
        job = create_scraping_job(
            tenant_id=org_id,
            target_id=target_id,
            created_by=user_id,
            configuration={"url": request.url, "domain": request.domain},
            triggered_by=TriggeredBy.API,
            correlation_id=_SEED_CORRELATION_ID,
        )
        db.add(job)

    now = datetime.now(UTC)
    setattr(job, "status", JobStatus.COMPLETED.value)
    setattr(job, "started_at", now)
    setattr(job, "completed_at", now)
    setattr(job, "progress_stage", PipelineStage.NOTIFICATION.value)
    setattr(job, "progress_total_pages", 1)
    setattr(job, "progress_processed_pages", 1)
    setattr(job, "progress_failed_pages", 0)
    setattr(job, "progress_current_url", request.url)
    setattr(job, "progress_percent_complete", 100)
    db.commit()
    db.refresh(target)
    db.refresh(job)

    return ValidationJobSeedResponse(
        seeded=True,
        target_id=target_id,
        job_id=cast(UUID, job.id),
        domain=request.domain,
        status=cast(str, job.status),
        progress_percent_complete=cast(int, job.progress_percent_complete),
    )


@router.post(
    "/validation/seed/job",
    response_model=ValidationJobSeedResponse,
    include_in_schema=False,
)
def seed_validation_job_route(
    request: ValidationJobSeedRequest,
    privileged_reason: str | None = Header(default=None, alias="X-Privileged-Reason"),
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    roles: list[str] = Depends(get_current_user_roles),
    db: Session = Depends(get_db_from_context_sync),
) -> ValidationJobSeedResponse:
    return seed_validation_job(
        request=request,
        privileged_reason=privileged_reason,
        org_id=org_id,
        user_id=user_id,
        roles=roles,
        db=db,
        environment=settings.environment,
    )
