"""Scraping job route handlers."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import Depends, HTTPException, Query
from sqlalchemy import func
from sqlalchemy.orm import Session
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
)
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..crawler.decision_store import CrawlDecisionRepository
from ..shared.database import get_db_from_context_sync
from ..shared.models import (
    CrawlDecision,
    ExtractedData,
    JobError,
    JobStageDetail,
    JobStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingTarget,
    TriggeredBy,
    create_scraping_job,
)
from .dependencies import get_current_user_id, get_tenant_id
from .schemas.content_schemas import (
    DomainFallbackStatsResponse,
    RouterQualityReportResponse,
)
from .schemas.job_schemas import (
    JobErrorResponse,
    JobListResponse,
    JobProgressDetail,
    JobProgressResponse,
    JobResultsDetail,
    JobStageDetailResponse,
    JobSummary,
    ResourceUsageDetail,
    RetryJobRequest,
    ScrapingJobDetail,
)

logger = structlog.get_logger()


class cancel_jobResult(TypedDictModel):
    job_id: str
    status: str


class get_job_resultsResult(TypedDictModel):
    data: list[dict[str, Any]]
    format: str
    job_id: str
    limit: int
    page: int
    total_records: int


class retry_jobResult(TypedDictModel):
    new_job_id: str
    original_job_id: str
    status: str


def _build_task_unavailable_detail() -> dict[str, str]:
    return {
        "code": "SERVICE_UNAVAILABLE",
        "message": (
            "Background processing is temporarily unavailable. "
            "Please retry shortly or contact support if the issue persists."
        ),
    }


class _UnavailableTask:
    """Fail closed when task infrastructure is unavailable."""

    def __init__(self, task_name: str, import_error: ImportError) -> None:
        self.task_name = task_name
        self.import_error = import_error

    def apply_async(self, *args: Any, **kwargs: Any) -> None:
        logger.error(
            "background_task_unavailable",
            task_name=self.task_name,
            error_type=type(self.import_error).__name__,
            error=str(self.import_error),
            exc_info=self.import_error,
        )
        raise HTTPException(status_code=503, detail=_build_task_unavailable_detail())


try:
    from ..shared.otel_celery import build_celery_options
    from ..shared.tasks import process_scraping_job
except ImportError as exc:
    build_celery_options = None  # type: ignore[assignment]
    process_scraping_job = _UnavailableTask("process_scraping_job", exc)


async def get_job_router_report(
    job_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get routing quality report for a specific job."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message="Job not found")

    repo = CrawlDecisionRepository(db)
    report = await repo.get_router_quality_report(str(job_id), tenant_id=str(org_id))

    return RouterQualityReportResponse(
        job_id=UUID(report.job_id),
        total_urls=report.total_urls,
        fast_path_count=report.fast_path_count,
        browser_path_count=report.browser_path_count,
        fallback_count=report.fallback_count,
        fallback_rate=report.fallback_rate,
        quality_gate_accuracy=report.quality_gate_accuracy,
        top_router_rules=report.top_router_rules,
        avg_fetch_time_ms=report.avg_fetch_time_ms,
        slowest_url=report.slowest_url,
        fastest_url=report.fastest_url,
    )


async def get_domain_fallback_stats(
    domain: str,
    days: int = Query(default=7, ge=1, le=30),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get fallback statistics for a specific domain."""
    has_access = (
        db.query(CrawlDecision)
        .filter(CrawlDecision.domain == domain, CrawlDecision.tenant_id == org_id)
        .first()
    )

    if not has_access:
        has_target = (
            db.query(ScrapingTarget)
            .filter(
                ScrapingTarget.tenant_id == org_id,
                ScrapingTarget.url.ilike(f"%{domain}%"),
            )
            .first()
        )

        if not has_target:
            raise AuthorizationError(message="No access to this domain")

    since = datetime.now(UTC) - timedelta(days=days)
    repo = CrawlDecisionRepository(db)
    stats = await repo.get_fallback_stats(domain, tenant_id=str(org_id), since=since)

    return DomainFallbackStatsResponse(
        domain=stats.domain,
        total_decisions=stats.total_decisions,
        fast_count=stats.fast_count,
        browser_count=stats.browser_count,
        fallback_count=stats.fallback_count,
        fallback_rate=stats.fallback_rate,
        top_fallback_reasons=stats.top_fallback_reasons,
        avg_fast_duration_ms=stats.avg_fast_duration_ms,
        avg_browser_duration_ms=stats.avg_browser_duration_ms,
    )


async def list_jobs(
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    target_id: UUID | None = Query(None),
    status: list[JobStatus] | None = Query(None),
    triggered_by: str | None = Query(None),
    date_from: datetime | None = Query(None),
    date_to: datetime | None = Query(None),
    priority_min: int | None = Query(None, ge=1, le=10),
    priority_max: int | None = Query(None, ge=1, le=10),
    has_errors: bool | None = Query(None),
    sort_by: str = Query(
        default="created_at", pattern="^(created_at|started_at|completed_at|priority)$"
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """List all scraping jobs with filtering and pagination."""
    query = db.query(ScrapingJob).filter(ScrapingJob.tenant_id == org_id)

    if target_id:
        query = query.filter(ScrapingJob.target_id == target_id)

    if status:
        status_values = [s.value for s in status]
        query = query.filter(ScrapingJob.status.in_(status_values))

    if triggered_by:
        query = query.filter(ScrapingJob.triggered_by == triggered_by)

    if date_from:
        query = query.filter(ScrapingJob.created_at >= date_from)

    if date_to:
        query = query.filter(ScrapingJob.created_at <= date_to)

    if priority_min is not None:
        query = query.filter(ScrapingJob.priority >= priority_min)

    if priority_max is not None:
        query = query.filter(ScrapingJob.priority <= priority_max)

    if has_errors is not None:
        if has_errors:
            query = query.filter(ScrapingJob.errors.any())
        else:
            query = query.filter(~ScrapingJob.errors.any())

    total = query.count()
    total_pages = (total + limit - 1) // limit

    status_counts = (
        db.query(ScrapingJob.status, func.count(ScrapingJob.id))
        .filter(ScrapingJob.tenant_id == org_id)
        .group_by(ScrapingJob.status)
        .all()
    )

    by_status = {status: count for status, count in status_counts}

    sort_column = getattr(ScrapingJob, sort_by)
    if sort_order == "desc":
        sort_column = sort_column.desc()
    query = query.order_by(sort_column)

    offset = (page - 1) * limit
    jobs = query.offset(offset).limit(limit).all()

    return JobListResponse(
        data=[
            JobSummary(
                id=j.id,
                target_id=j.target_id,
                status=j.status,
                priority=j.priority,
                progress_percent_complete=j.progress_percent_complete,
                created_at=j.created_at,
                started_at=j.started_at,
                completed_at=j.completed_at,
            )
            for j in jobs
        ],
        aggregation={
            "by_status": by_status,
            "total_execution_time_ms": sum(j.resources_compute_time_ms for j in jobs),
            "total_records_extracted": sum(
                j.results_extracted_record_count for j in jobs
            ),
        },
        pagination={
            "page": page,
            "limit": limit,
            "total": total,
            "total_pages": total_pages,
        },
    )


async def get_job(
    job_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get detailed job information including execution stages."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message="Job not found")

    stages = (
        db.query(JobStageDetail)
        .filter(JobStageDetail.job_id == job_id)
        .order_by(JobStageDetail.created_at)
        .all()
    )

    errors = (
        db.query(JobError)
        .filter(JobError.job_id == job_id)
        .order_by(JobError.occurred_at.desc())
        .all()
    )

    return ScrapingJobDetail(
        id=job.id,
        tenant_id=job.tenant_id,
        target_id=job.target_id,
        configuration=job.configuration,
        status=job.status,
        priority=job.priority,
        scheduled_at=job.scheduled_at,
        started_at=job.started_at,
        completed_at=job.completed_at,
        estimated_duration_ms=job.estimated_duration_ms,
        progress=JobProgressDetail(
            total_pages=job.progress_total_pages,
            processed_pages=job.progress_processed_pages,
            failed_pages=job.progress_failed_pages,
            current_url=job.progress_current_url,
            current_stage=job.progress_stage,
            percent_complete=job.progress_percent_complete,
        ),
        results=JobResultsDetail(
            raw_content_count=job.results_raw_content_count,
            extracted_record_count=job.results_extracted_record_count,
            storage_bytes_used=job.results_storage_bytes_used,
            output_location=job.results_output_location,
        ),
        resources=ResourceUsageDetail(
            browser_sessions_used=job.resources_browser_sessions_used,
            proxy_requests_made=job.resources_proxy_requests_made,
            llm_tokens_consumed=job.resources_llm_tokens_consumed,
            compute_time_ms=job.resources_compute_time_ms,
        ),
        triggered_by=job.triggered_by,
        correlation_id=job.correlation_id,
        created_at=job.created_at,
        created_by=job.created_by,
        stages=[
            JobStageDetailResponse(
                stage=s.stage,
                status=s.status,
                started_at=s.started_at,
                completed_at=s.completed_at,
                duration_ms=s.duration_ms,
                error_message=s.error_message,
            )
            for s in stages
        ],
        errors=[
            JobErrorResponse(
                id=e.id,
                stage=e.stage,
                error_code=e.error_code,
                error_message=e.error_message,
                url=e.url,
                retryable=e.retryable,
                retry_count=e.retry_count,
                occurred_at=e.occurred_at,
                resolved_at=e.resolved_at,
            )
            for e in errors
        ],
    )


async def cancel_job(
    job_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Cancel a running or queued job."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message="Job not found")

    terminal_states = [
        JobStatus.COMPLETED.value,
        JobStatus.FAILED.value,
        JobStatus.CANCELLED.value,
        JobStatus.PARTIAL_SUCCESS.value,
    ]

    if job.status in terminal_states:
        raise ConflictError(message=f"Job already in terminal state: {job.status}")

    job.status = JobStatus.CANCELLED.value
    job.completed_at = datetime.now(UTC)

    logger.info("Cancelled scraping job", job_id=str(job_id))

    return cancel_jobResult.model_validate(
        {"status": "CANCELLED", "job_id": str(job_id)}
    )


async def get_job_progress(
    job_id: UUID,
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get real-time job progress."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message="Job not found")

    return JobProgressResponse(
        job_id=job.id,
        status=job.status,
        progress=JobProgressDetail(
            total_pages=job.progress_total_pages,
            processed_pages=job.progress_processed_pages,
            failed_pages=job.progress_failed_pages,
            current_url=job.progress_current_url,
            current_stage=job.progress_stage,
            percent_complete=job.progress_percent_complete,
        ),
        last_update=datetime.now(UTC),
    )


async def get_job_results(
    job_id: UUID,
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
    org_id: UUID = Depends(get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get extracted data results for a job."""
    job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not job:
        raise NotFoundError(message="Job not found")

    query = db.query(ExtractedData).filter(
        ExtractedData.job_id == job_id, ExtractedData.tenant_id == org_id
    )

    total = query.count()
    offset = (page - 1) * limit
    data = query.offset(offset).limit(limit).all()

    return get_job_resultsResult.model_validate(
        {
            "job_id": str(job_id),
            "format": "json",
            "total_records": total,
            "data": [
                {
                    "id": str(d.id),
                    "raw_content_id": str(d.raw_content_id),
                    "extraction_method": d.extraction_method,
                    "confidence": (
                        float(d.extraction_confidence_score)
                        if d.extraction_confidence_score
                        else None
                    ),
                    "data": d.data,
                    "created_at": d.created_at.isoformat(),
                }
                for d in data
            ],
            "page": page,
            "limit": limit,
        }
    )


async def retry_job(
    job_id: UUID,
    request: RetryJobRequest,
    org_id: UUID = Depends(get_tenant_id),
    user_id: UUID = Depends(get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Retry a failed or partially successful job."""
    original_job = (
        db.query(ScrapingJob)
        .filter(ScrapingJob.id == job_id, ScrapingJob.tenant_id == org_id)
        .first()
    )

    if not original_job:
        raise NotFoundError(message="Job not found")

    if original_job.status not in [
        JobStatus.FAILED.value,
        JobStatus.PARTIAL_SUCCESS.value,
    ]:
        raise ConflictError(
            message="Only failed or partially successful jobs can be retried"
        )

    correlation_id = f"retry:{job_id}:{uuid4()}"
    new_job = create_scraping_job(
        tenant_id=org_id,
        target_id=original_job.target_id,
        created_by=user_id,
        configuration=original_job.configuration,
        priority=original_job.priority,
        triggered_by=TriggeredBy.MANUAL,
        correlation_id=correlation_id,
    )

    db.add(new_job)
    db.commit()
    db.refresh(new_job)

    for stage in PipelineStage:
        stage_detail = JobStageDetail(
            job_id=new_job.id, tenant_id=org_id, stage=stage.value, status="PENDING"
        )
        db.add(stage_detail)

    new_job.status = JobStatus.QUEUED.value
    db.commit()

    process_scraping_job.apply_async(
        args=[str(new_job.id), str(new_job.tenant_id)],
        **(build_celery_options() or {}),
    )

    logger.info(
        "Created retry job", original_job_id=str(job_id), new_job_id=str(new_job.id)
    )

    return retry_jobResult.model_validate(
        {
            "original_job_id": str(job_id),
            "new_job_id": str(new_job.id),
            "status": JobStatus.QUEUED.value,
        }
    )
