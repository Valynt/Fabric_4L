"""Target handlers for Layer 1 scraping target operations."""

from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

import sqlalchemy.exc
from fastapi import HTTPException
from sqlalchemy.orm import Session

from ...shared.exceptions import ConflictError, NotFoundError
from ...shared.models import (
    JobStatus,
    ScrapingJob,
    ScrapingTarget,
    TargetStatus,
    TriggeredBy,
    create_scraping_job,
)
from ..orchestrator.stages import _initialize_pipeline_stages
from ..shared.tasks import process_scraping_job
from ..shared.otel_celery import build_celery_options
from .schemas import ExecuteTargetRequest, ExecuteTargetResponse

logger = logging.getLogger(__name__)


async def execute_target(
    target_id: UUID,
    request: ExecuteTargetRequest,
    org_id: UUID,
    user_id: UUID,
    db: Session,
) -> ExecuteTargetResponse:
    """Execute a scraping job for a target with idempotency support."""
    target = (
        db.query(ScrapingTarget)
        .filter(ScrapingTarget.id == target_id, ScrapingTarget.tenant_id == org_id)
        .first()
    )

    if not target:
        raise NotFoundError(message="Target not found")

    if target.status != TargetStatus.ACTIVE.value:
        raise ConflictError(message=f"Target is not active (status: {target.status})")

    existing_response, placeholder = await _check_idempotency_key(
        request.idempotency_key, org_id, target_id, db
    )
    if existing_response:
        return existing_response

    configuration = _build_job_configuration(target, request.override_config)

    correlation_id = str(uuid4())
    job = create_scraping_job(
        tenant_id=org_id,
        target_id=target_id,
        created_by=user_id,
        configuration=configuration,
        priority=request.priority,
        triggered_by=TriggeredBy.API,
        correlation_id=correlation_id,
        idempotency_key=request.idempotency_key,
    )

    db.add(job)
    try:
        db.commit()
    except sqlalchemy.exc.IntegrityError:
        db.rollback()
        # Durable dedup backstop: idx_scraping_jobs_tenant_idempotency
        # (tenant_id, idempotency_key) fired — a concurrent request created the
        # job first. Redis-only dedup can lose entries on a flush; the database
        # is the authoritative idempotency boundary (V1-TENANCY-010 / S-2).
        existing_job = None
        if request.idempotency_key:
            existing_job = (
                db.query(ScrapingJob)
                .filter(
                    ScrapingJob.tenant_id == org_id,
                    ScrapingJob.idempotency_key == request.idempotency_key,
                )
                .first()
            )
        if existing_job is not None:
            logger.info(
                "Idempotency key hit at database boundary, returning existing job",
                idempotency_key=request.idempotency_key,
                job_id=str(existing_job.id),
            )
            return ExecuteTargetResponse(
                job_id=existing_job.id,
                status=existing_job.status,
                estimated_start_time=existing_job.started_at,
                queue_position=None,
                queue_position_metadata=None,
            )
        raise
    db.refresh(job)

    if request.idempotency_key:
        _update_idempotency_key(org_id, target_id, request.idempotency_key, job.id)

    try:
        _initialize_pipeline_stages(job.id, org_id, db)
        job.status = JobStatus.QUEUED.value
        db.commit()
    except sqlalchemy.exc.SQLAlchemyError as exc:
        db.rollback()
        logger.error(
            "failed_to_persist_queued_job",
            job_id=str(job.id),
            tenant_id=str(org_id),
            error=str(exc),
        )
        # The job row was already committed before stage initialization; mark it
        # failed so it is not left in an ambiguous default status.
        job.status = JobStatus.FAILED.value
        db.commit()
        # Remove the placeholder so the caller can retry; if we leave it, the
        # short TTL will still expire within 60 seconds, but explicit cleanup
        # gives a faster recovery path.
        if request.idempotency_key and placeholder:
            _delete_idempotency_key(org_id, target_id, request.idempotency_key)
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Failed to queue scraping job",
            },
        ) from exc

    process_scraping_job.apply_async(
        args=[str(job.id), str(job.tenant_id)],
        **(build_celery_options() or {}),
    )

    logger.info("Queued scraping job", job_id=str(job.id), target_id=str(target_id))

    return ExecuteTargetResponse(
        job_id=job.id,
        status=JobStatus.QUEUED.value,
        queue_position=_calculate_queue_position(db, org_id, job.created_at),
        queue_position_metadata={
            "calculation": "count_queued_jobs_created_before_or_at_current_job",
            "scope": "organization",
        },
        estimated_start_time=None,
    )


async def _check_idempotency_key(
    idempotency_key: str | None,
    org_id: UUID,
    target_id: UUID,
    db: Session,
) -> tuple[ExecuteTargetResponse | None, str | None]:
    """Check idempotency key and return existing job response if found.

    Returns a tuple of (response, placeholder). If placeholder is not None,
    the caller owns it and must either replace it with a real job_id via
    _update_idempotency_key or delete it via _delete_idempotency_key on failure.
    """
    if not idempotency_key:
        return None, None

    idempotency_key_str = f"idempotency:{org_id}:{target_id}:{idempotency_key}"
    from ..shared.database import redis_client

    if not redis_client:
        return None, None

    try:
        job_id_placeholder = f"placeholder:{uuid4()}"
        # Use a short TTL for the placeholder so an orphaned placeholder (e.g.
        # request crash before the real job_id is written) expires quickly.
        set_result = redis_client.set(
            idempotency_key_str, job_id_placeholder, nx=True, ex=60
        )
    except Exception as exc:
        logger.warning(
            "idempotency_redis_set_failed",
            idempotency_key=idempotency_key,
            error=str(exc),
        )
        return None, None

    if set_result is not None:
        from ..metrics.prometheus_metrics import get_metrics

        metrics = get_metrics()
        if metrics and metrics.config.enabled:
            metrics.increment_idempotency_key_miss()
        return None, job_id_placeholder

    for attempt in range(5):
        try:
            existing_job_id = _decode_redis_value(
                redis_client.get(idempotency_key_str)
            )
        except Exception as exc:
            logger.warning(
                "idempotency_redis_get_failed",
                idempotency_key=idempotency_key,
                error=str(exc),
            )
            break
        if not existing_job_id or not existing_job_id.startswith("placeholder:"):
            break
        await asyncio.sleep(0.05 * (2**attempt))

    try:
        existing_job_id = _decode_redis_value(redis_client.get(idempotency_key_str))
    except Exception as exc:
        logger.warning(
            "idempotency_redis_get_failed",
            idempotency_key=idempotency_key,
            error=str(exc),
        )
        existing_job_id = None

    if existing_job_id and not existing_job_id.startswith("placeholder:"):
        logger.info(
            "Idempotency key hit, returning existing job",
            idempotency_key=idempotency_key,
            job_id=existing_job_id,
        )
        existing_job = db.query(ScrapingJob).get(UUID(existing_job_id))
        if existing_job and existing_job.tenant_id == org_id:
            from ..metrics.prometheus_metrics import get_metrics

            metrics = get_metrics()
            if metrics and metrics.config.enabled:
                metrics.increment_idempotency_key_hit()
            return ExecuteTargetResponse(
                job_id=UUID(existing_job_id),
                status=existing_job.status,
                estimated_start_time=existing_job.started_at,
                queue_position=None,
                queue_position_metadata=None,
            ), None
        try:
            redis_client.delete(idempotency_key_str)
        except Exception as exc:
            logger.warning(
                "idempotency_redis_delete_failed",
                idempotency_key=idempotency_key,
                error=str(exc),
            )

    if existing_job_id and existing_job_id.startswith("placeholder:"):
        raise ConflictError(
            message="A request with this idempotency key is already in progress"
        )

    return None, None


def _delete_idempotency_key(
    org_id: UUID, target_id: UUID, idempotency_key: str
) -> None:
    """Delete an idempotency key (used on failure before a real job_id exists)."""
    idempotency_key_str = f"idempotency:{org_id}:{target_id}:{idempotency_key}"
    from ..shared.database import redis_client

    if not redis_client:
        return
    try:
        redis_client.delete(idempotency_key_str)
    except Exception as exc:
        logger.warning(
            "idempotency_redis_delete_failed",
            idempotency_key=idempotency_key,
            error=str(exc),
        )


def _update_idempotency_key(
    org_id: UUID, target_id: UUID, idempotency_key: str, job_id: UUID
) -> None:
    """Update an idempotency key with the real job id."""
    idempotency_key_str = f"idempotency:{org_id}:{target_id}:{idempotency_key}"
    from ..shared.database import redis_client

    if not redis_client:
        return
    try:
        redis_client.set(idempotency_key_str, str(job_id), ex=86400)
    except Exception as exc:
        logger.warning(
            "idempotency_redis_set_failed",
            idempotency_key=idempotency_key,
            error=str(exc),
        )


def _decode_redis_value(value: Any) -> str | None:
    """Decode a Redis value to string."""
    if value is None:
        return None
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return str(value)


def _build_job_configuration(target: ScrapingTarget, override_config: dict | None) -> dict:
    """Build job configuration from target and optional overrides."""
    configuration = {
        "url": target.url,
        "job_type": target.job_type if hasattr(target, "job_type") else "GENERIC_SCRAPE",
        "extraction_config": target.extraction_config or {},
        "compliance": target.compliance or {},
        "browser_config": (target.extraction_config or {}).get("browser_config", {}),
    }
    if override_config:
        configuration.update(override_config)
    return configuration


def _calculate_queue_position(db: Session, org_id: UUID, created_at: datetime) -> int:
    """Calculate queue position based on queued jobs created before or at current job."""
    return (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.tenant_id == org_id,
            ScrapingJob.status == JobStatus.QUEUED.value,
            ScrapingJob.created_at <= created_at,
        )
        .count()
    )
