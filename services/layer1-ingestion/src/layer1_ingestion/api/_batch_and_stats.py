"""Batch operation and target statistics endpoints for Layer 1.

These endpoints are part of the canonical ``layer1_ingestion.api.main`` app.
"""

from __future__ import annotations

from enum import Enum as PyEnum
from typing import Any
from uuid import UUID, uuid4

import structlog
from fastapi import APIRouter, Depends
from fastapi import Request as _Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from value_fabric.shared.error_handling.exceptions import ValidationError

from ..shared.database import get_db_from_context_sync
from ..shared.models import (
    JobStageDetail,
    JobStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingTarget,
    TargetStatus,
    TriggeredBy,
    create_scraping_job,
)
from ..shared.tasks import process_scraping_job

logger = structlog.get_logger()

router = APIRouter()


# Lazy proxies avoid a circular import with layer1_ingestion.api.main
# because main.py includes this router and also defines these dependencies.


def _get_tenant_id(request: _Request):
    from .main import get_tenant_id

    return get_tenant_id(request)


def _get_current_user_id(request: _Request):
    from .main import get_current_user_id

    return get_current_user_id(request)


# =============================================================================
# BATCH OPERATION MODELS
# =============================================================================


class BatchOperationType(str, PyEnum):
    """Types of batch operations supported."""

    EXECUTE = "execute"
    CANCEL = "cancel"
    RETRY = "retry"


class BatchOperationRequest(BaseModel):
    """Request for batch operations on jobs and targets."""

    operation: BatchOperationType = Field(..., description="Operation to perform")
    target_ids: list[UUID] = Field(default_factory=list, description="Target IDs for execute operation")
    job_ids: list[UUID] = Field(default_factory=list, description="Job IDs for cancel/retry operations")
    options: dict[str, Any] = Field(default_factory=dict, description="Additional operation options")


class BatchOperationItemResult(BaseModel):
    """Result of a single item in a batch operation."""

    id: UUID = Field(..., description="Target or job ID")
    status: str = Field(..., description="Operation status: succeeded, failed, or skipped")
    job_id: UUID | None = Field(None, description="Resulting job ID (if applicable)")
    error: str | None = Field(None, description="Error message if failed")


class BatchOperationResponse(BaseModel):
    """Response for batch operation."""

    operation: BatchOperationType = Field(..., description="Operation performed")
    requested: int = Field(..., description="Total number of items requested")
    succeeded: int = Field(..., description="Number of successful operations")
    failed: int = Field(..., description="Number of failed operations")
    results: list[BatchOperationItemResult] = Field(..., description="Per-item results")


class TargetStatsResponse(BaseModel):
    """Aggregated statistics for scraping targets."""

    total: int
    connected: int
    disconnected: int
    error: int
    total_records: int
    average_health_score: int


# =============================================================================
# API ENDPOINTS - Target Stats
# =============================================================================


@router.get("/targets/stats", response_model=TargetStatsResponse)
async def get_target_stats(
    org_id: UUID = Depends(_get_tenant_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Get aggregated statistics for all scraping targets.

    Computes counts by derived connection status and average health score
    server-side to avoid transferring large target lists to the client.
    """
    targets = (
        db.query(
            ScrapingTarget.status,
            ScrapingTarget.last_success_at,
            ScrapingTarget.last_error_at,
            ScrapingTarget.error_count,
            ScrapingTarget.success_count,
        )
        .filter(ScrapingTarget.tenant_id == org_id)
        .all()
    )

    total = len(targets)
    connected = 0
    disconnected = 0
    error_count = 0
    health_score_sum = 0

    for t in targets:
        status = t.status
        last_success_at = t.last_success_at
        last_error_at = t.last_error_at
        target_error_count = t.error_count
        success_count = t.success_count

        # Derive connection status (mirrors frontend deriveConnectionStatus)
        if status == TargetStatus.ERROR.value:
            derived = "error"
        elif status == TargetStatus.PAUSED.value:
            derived = "disconnected"
        elif target_error_count > 0 and last_error_at and (not last_success_at or last_error_at > last_success_at):
            derived = "error"
        elif last_success_at:
            derived = "connected"
        else:
            derived = "disconnected"

        if derived == "connected":
            connected += 1
        elif derived == "disconnected":
            disconnected += 1
        else:
            error_count += 1

        # Calculate health score (mirrors frontend calculateHealthScore)
        run_total = success_count + target_error_count
        if run_total > 0:
            health_score_sum += round((success_count / run_total) * 100)

    average_health_score = round(health_score_sum / total) if total > 0 else 0

    return TargetStatsResponse(
        total=total,
        connected=connected,
        disconnected=disconnected,
        error=error_count,
        total_records=0,  # Reserved: requires per-target extracted_data aggregation
        average_health_score=average_health_score,
    )


# =============================================================================
# API ENDPOINTS - Batch Operations
# =============================================================================


@router.post("/jobs/batch", response_model=BatchOperationResponse, status_code=202)
async def batch_operation(
    request: BatchOperationRequest,
    org_id: UUID = Depends(_get_tenant_id),
    user_id: UUID = Depends(_get_current_user_id),
    db: Session = Depends(get_db_from_context_sync),
):
    """Execute batch operations on ingestion jobs and targets.

    Supports three operations:
    - execute: Trigger crawl jobs for multiple targets
    - cancel: Cancel multiple running/queued jobs
    - retry: Retry multiple failed jobs

    Returns per-item results with success/failure status.
    """
    # Validate request based on operation type
    if request.operation == BatchOperationType.EXECUTE:
        if not request.target_ids:
            raise ValidationError(message="target_ids required for execute operation")
        if request.job_ids:
            raise ValidationError(message="job_ids not allowed for execute operation")
    elif request.operation in (BatchOperationType.CANCEL, BatchOperationType.RETRY):
        if not request.job_ids:
            raise ValidationError(message="job_ids required for cancel/retry operations")
        if request.target_ids:
            raise ValidationError(message="target_ids not allowed for cancel/retry operations")

    # Enforce batch size limit
    max_batch_size = 100
    requested_count = len(request.target_ids) if request.target_ids else len(request.job_ids)
    if requested_count == 0:
        raise ValidationError(message="At least one target_id or job_id is required")
    if requested_count > max_batch_size:
        raise ValidationError(message=str(f"Batch size exceeds maximum of {max_batch_size}"))

    results = []
    succeeded = 0
    failed = 0

    if request.operation == BatchOperationType.EXECUTE:
        # Pre-fetch all targets for this batch to avoid N+1 queries
        targets = (
            db.query(ScrapingTarget)
            .filter(ScrapingTarget.id.in_(request.target_ids), ScrapingTarget.tenant_id == org_id)
            .all()
        )
        targets_by_id = {t.id: t for t in targets}

        for target_id in request.target_ids:
            try:
                # Verify target belongs to tenant
                target = targets_by_id.get(target_id)
                if not target:
                    results.append(
                        BatchOperationItemResult(
                            id=target_id,
                            status="skipped",
                            job_id=None,
                            error="Target not found or access denied",
                        )
                    )
                    failed += 1
                    continue

                if target.status != TargetStatus.ACTIVE.value:
                    results.append(
                        BatchOperationItemResult(
                            id=target_id,
                            status="skipped",
                            job_id=None,
                            error=f"Target is not active - status: {target.status}",
                        )
                    )
                    failed += 1
                    continue

                # Execute target - reuse existing execute logic
                job = create_scraping_job(
                    tenant_id=org_id,
                    target_id=target.id,
                    created_by=user_id,
                    configuration=target.extraction_config,
                    priority=request.options.get("priority", 5),
                    triggered_by=TriggeredBy.MANUAL,
                    correlation_id=f"batch:{target_id}:{uuid4()}",
                )

                db.add(job)
                db.flush()
                db.refresh(job)

                # Initialize stages
                for stage in PipelineStage:
                    stage_detail = JobStageDetail(
                        job_id=job.id,
                        tenant_id=org_id,
                        stage=stage.value,
                        status="PENDING",
                    )
                    db.add(stage_detail)

                # Queue job
                job.status = JobStatus.QUEUED.value
                process_scraping_job.delay(str(job.id), str(job.tenant_id))

                results.append(
                    BatchOperationItemResult(id=target_id, status="succeeded", job_id=job.id, error=None)
                )
                succeeded += 1

            except Exception:
                logger.error("batch_execute_failed", target_id=str(target_id), error_code="BATCH_EXECUTE_ERROR")
                results.append(
                    BatchOperationItemResult(
                        id=target_id,
                        status="failed",
                        job_id=None,
                        error="BATCH_EXECUTE_ERROR",
                    )
                )
                failed += 1

    elif request.operation == BatchOperationType.CANCEL:
        # Pre-fetch all jobs for this batch to avoid N+1 queries
        jobs = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.id.in_(request.job_ids), ScrapingJob.tenant_id == org_id)
            .all()
        )
        jobs_by_id = {j.id: j for j in jobs}

        for job_id in request.job_ids:
            try:
                # Verify job belongs to tenant
                job = jobs_by_id.get(job_id)
                if not job:
                    results.append(
                        BatchOperationItemResult(
                            id=job_id,
                            status="skipped",
                            job_id=job_id,
                            error="Job not found or access denied",
                        )
                    )
                    failed += 1
                    continue

                # Check if job can be cancelled
                terminal_states = [
                    JobStatus.COMPLETED.value,
                    JobStatus.FAILED.value,
                    JobStatus.CANCELLED.value,
                    JobStatus.PARTIAL_SUCCESS.value,
                ]
                if job.status in terminal_states:
                    results.append(
                        BatchOperationItemResult(
                            id=job_id,
                            status="skipped",
                            job_id=job_id,
                            error=f"Job is in terminal state - status: {job.status}",
                        )
                    )
                    failed += 1
                    continue

                # Cancel job
                job.status = JobStatus.CANCELLED.value
                db.flush()

                results.append(
                    BatchOperationItemResult(
                        id=job_id,
                        status="succeeded",
                        job_id=job_id,
                        error=None,
                    )
                )
                succeeded += 1

            except Exception:
                logger.error("batch_cancel_failed", job_id=str(job_id), error_code="BATCH_CANCEL_ERROR")
                results.append(
                    BatchOperationItemResult(
                        id=job_id,
                        status="failed",
                        job_id=job_id,
                        error="BATCH_CANCEL_ERROR",
                    )
                )
                failed += 1

    elif request.operation == BatchOperationType.RETRY:
        # Pre-fetch all jobs for this batch to avoid N+1 queries
        jobs = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.id.in_(request.job_ids), ScrapingJob.tenant_id == org_id)
            .all()
        )
        jobs_by_id = {j.id: j for j in jobs}

        for job_id in request.job_ids:
            try:
                # Verify job belongs to tenant
                job = jobs_by_id.get(job_id)
                if not job:
                    results.append(
                        BatchOperationItemResult(
                            id=job_id,
                            status="skipped",
                            job_id=job_id,
                            error="Job not found or access denied",
                        )
                    )
                    failed += 1
                    continue

                if job.status not in [JobStatus.FAILED.value, JobStatus.PARTIAL_SUCCESS.value]:
                    results.append(
                        BatchOperationItemResult(
                            id=job_id,
                            status="skipped",
                            job_id=job_id,
                            error=f"Only failed or partially successful jobs can be retried - status: {job.status}",
                        )
                    )
                    failed += 1
                    continue

                # Retry job - reuse existing retry logic
                correlation_id = f"retry:{job_id}:{uuid4()}"
                new_job = create_scraping_job(
                    tenant_id=org_id,
                    target_id=job.target_id,
                    created_by=user_id,
                    configuration=job.configuration,
                    priority=job.priority,
                    triggered_by=TriggeredBy.MANUAL,
                    correlation_id=correlation_id,
                )

                db.add(new_job)
                db.flush()
                db.refresh(new_job)

                # Initialize stages
                for stage in PipelineStage:
                    stage_detail = JobStageDetail(
                        job_id=new_job.id,
                        tenant_id=org_id,
                        stage=stage.value,
                        status="PENDING",
                    )
                    db.add(stage_detail)

                # Queue new job
                new_job.status = JobStatus.QUEUED.value
                process_scraping_job.delay(str(new_job.id), str(new_job.tenant_id))

                results.append(
                    BatchOperationItemResult(
                        id=job_id,
                        status="succeeded",
                        job_id=new_job.id,
                        error=None,
                    )
                )
                succeeded += 1

            except Exception:
                logger.error("batch_retry_failed", job_id=str(job_id), error_code="BATCH_RETRY_ERROR")
                results.append(
                    BatchOperationItemResult(
                        id=job_id,
                        status="failed",
                        job_id=job_id,
                        error="BATCH_RETRY_ERROR",
                    )
                )
                failed += 1

    return BatchOperationResponse(
        operation=request.operation,
        requested=requested_count,
        succeeded=succeeded,
        failed=failed,
        results=results,
    )
