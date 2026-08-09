"""Celery task queue configuration and tasks.

Spec-compliant pipeline stage tasks with multi-tenancy support.
Manages ScrapingJob lifecycle through 11 PipelineStages.
"""

import asyncio
import os
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID

import structlog
from celery import Celery
from celery.schedules import crontab
from value_fabric.shared.redis_ha import get_celery_redis_broker_config

from ..shared.config import settings
from ..shared.database import get_db_session
from ..shared.models import (
    JobError,
    JobStageDetail,
    JobStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingTarget,
)

# Maximum delivery attempts before an outbox event is dead-lettered.
MAX_DISPATCH_ATTEMPTS = 5


def _domain_class(url: str) -> str:
    host = (urlparse(url).netloc or "").lower()
    if not host:
        return "unknown"
    if host.endswith(".gov") or host.endswith(".edu"):
        return "regulated"
    if host.endswith(".internal") or host.endswith(".local"):
        return "internal"
    return "public"


logger = structlog.get_logger()


async def _verify_l3_graph_population(tenant_id: str, source_version_id: str) -> int:
    """Verify L3 graph has entities from the given source version.

    Calls L3 /v1/query/entities with source_version_id filter and returns count.
    """
    import httpx  # noqa: F811

    from ..shared.config import settings

    l3_url = settings.layer3_api_url
    service_secret = os.getenv("SERVICE_AUTH_SECRET", "")

    headers = {
        "X-Tenant-ID": tenant_id,
        "X-Service-Auth": service_secret,
        "Content-Type": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                f"{l3_url}/v1/query/entities",
                params={"source_version_id": source_version_id, "limit": 1},
                headers=headers,
            )
            if response.status_code == 200:
                data = response.json()
                return data.get("total", 0)
    except Exception as e:
        logger.warning(
            "L3 graph verification failed",
            tenant_id=tenant_id,
            source_version_id=source_version_id,
            error=str(e),
        )
    return 0


def _run_async(coro):
    # In a Celery worker there is no running event loop, so run the coroutine
    # to completion. When called from an async test context (e.g. pytest-asyncio)
    # with a running loop, return the coroutine so the caller can await it.
    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(coro)
    return coro


_celery_broker_url, _celery_transport_options = get_celery_redis_broker_config(settings.redis_url)

# Initialize Celery app
celery_app = Celery(
    "layer1_ingestion",
    broker=_celery_broker_url,
    backend=_celery_broker_url,
    include=["layer1_ingestion.shared.tasks"],
)

_original_gen_task_name = celery_app.gen_task_name


def _compat_task_name(name: str, module: str) -> str:
    """Keep task identities stable after moving implementations."""
    if module in {
        "layer1_ingestion.shared.pipeline_tasks",
        "layer1_ingestion.shared.event_tasks",
    }:
        module = "layer1_ingestion.shared.tasks"
    return _original_gen_task_name(name, module)


celery_app.gen_task_name = _compat_task_name

# Celery configuration
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    worker_prefetch_multiplier=1,
    result_expires=3600,
    task_routes={},
    # P0-02: Dead letter queue configuration
    task_reject_on_worker_lost=True,  # Reject tasks when worker dies
    task_acks_late=True,  # Ack after task completes
    task_default_retry_delay=60,  # Default retry delay in seconds
    task_max_retries=3,  # Max retries before sending to DLQ
    task_default_rate_limit="100/m",  # Rate limit per task
    # Define dead letter queue
    task_queues={
        "default": {
            "exchange": "default",
            "routing_key": "default",
        },
        "ingestion": {
            "exchange": "ingestion",
            "routing_key": "ingestion",
        },
        "processing": {
            "exchange": "processing",
            "routing_key": "processing",
        },
        "layer1_dlq": {
            "exchange": "layer1_dlq",
            "routing_key": "layer1_dlq",
        },
    },
    task_default_queue="default",
    task_default_exchange="default",
    task_default_routing_key="default",
    broker_transport_options=_celery_transport_options,
    result_backend_transport_options=_celery_transport_options,
    # P0-03: Backpressure configuration
    worker_max_tasks_per_child=100,  # Recycle worker after 100 tasks
    worker_max_memory_per_child=500000,  # 500MB max memory per worker
    # P0-06: Graceful shutdown configuration
    worker_shutdown_timeout=30,  # 30s grace period for in-progress tasks
    worker_cancel_long_running_tasks_on_shutdown=True,
    # Data retention: purge expired raw content daily at 03:00 UTC.
    beat_schedule={
        "purge-expired-raw-content": {
            "task": "layer1_ingestion.shared.tasks.purge_expired_raw_content",
            "schedule": crontab(hour=3, minute=0),
            "options": {"queue": "default"},
        },
    },
)


# =============================================================================
# PIPELINE ORCHESTRATION
# =============================================================================


# Shared job lifecycle helpers.
def _update_stage(
    session, job_id: UUID, stage: PipelineStage, status: str, error_message: str | None = None
):
    """Update pipeline stage status."""
    stage_detail = (
        session.query(JobStageDetail)
        .filter(JobStageDetail.job_id == job_id, JobStageDetail.stage == stage.value)
        .first()
    )

    if stage_detail:
        stage_detail.status = status
        if status == "RUNNING" and not stage_detail.started_at:
            stage_detail.started_at = datetime.now(UTC)
        if status in ("COMPLETED", "FAILED"):
            stage_detail.completed_at = datetime.now(UTC)
            if stage_detail.started_at:
                stage_detail.duration_ms = int(
                    (stage_detail.completed_at - stage_detail.started_at).total_seconds() * 1000
                )
        if error_message:
            stage_detail.error_message = error_message


def _check_tenant_kill_switch_sync(tenant_id: str) -> bool:
    """Check whether the tenant kill-switch is active.

    Returns True when the tenant is suspended and all work must fail closed.
    """
    # No kill-switch implementation yet; default to not suspended.
    return False


def _fail_job(job_id: UUID, tenant_id: str, error: str, stage: PipelineStage):
    """Mark job as failed.

    Args:
        job_id: The job UUID
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
        error: Error message
        stage: Pipeline stage that failed
    """
    tenant_uuid = UUID(tenant_id)

    # Set tenant context BEFORE any database queries
    with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
        job = session.query(ScrapingJob).get(job_id)
        # Capture needed values before any commit, since SET LOCAL app.tenant_id
        # is transaction-scoped and expires objects after commit.
        job_tenant_id = job.tenant_id if job else None
        job_target_id = job.target_id if job else None

        if job:
            job.status = JobStatus.FAILED.value
            job.completed_at = datetime.now(UTC)

        # Update stage
        _update_stage(session, job_id, stage, "FAILED", error)

        # Create error record
        error_record = JobError(
            job_id=job_id,
            tenant_id=job_tenant_id,
            stage=stage.value,
            error_code="PIPELINE_ERROR",
            error_message=error,
            retryable=False,
        )
        session.add(error_record)

        # Update target error stats
        if job:
            target = session.query(ScrapingTarget).get(job_target_id)
            if target:
                try:
                    target.error_count += 1
                except TypeError:
                    target.error_count = 1
                target.last_error_at = datetime.now(UTC)

        # Single commit at the end — get_db_session context manager also commits
        # on successful exit, but an explicit commit here ensures persistence
        # before the context manager's final commit (which is a no-op if already
        # committed, and prevents stale-object issues with RLS).
        session.commit()
