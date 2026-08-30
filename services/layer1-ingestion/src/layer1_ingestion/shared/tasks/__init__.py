"""Celery task queue configuration and tasks (package bootstrap).

Spec-compliant pipeline stage tasks with multi-tenancy support.
Manages ScrapingJob lifecycle through 11 PipelineStages.
"""

import os
import time
from datetime import UTC, datetime
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID

import httpx
import structlog
from celery import Celery, chain
from celery.schedules import crontab
from celery.signals import task_failure

from ..dlq import (
    DLQ_QUEUE_NAME,
    DLQ_TASK_NAME,
    build_dlq_envelope,
    extract_failure_context,
    should_route_to_dlq,
)

try:
    from value_fabric.shared.identity.jwt import encode_service_jwt
except ImportError:
    encode_service_jwt = None  # type: ignore

from ...compliance.pii_scanner import PIIScanner as PIIScanner
from ...compliance.robots_checker import RobotsChecker
from ...compliance.url_safety import (
    URLSafetyError,
    log_url_compliance_event,
    validate_url_safety,
)
from ...compliance.url_safety import (
    enforce_rebinding_protection as enforce_rebinding_protection,
)
from ...crawler.decision_store import (
    CrawlDecisionRecord as CrawlDecisionRecord,
)
from ...crawler.decision_store import (
    CrawlDecisionRepository as CrawlDecisionRepository,
)
from ...crawler.httpx_crawler import HttpxCrawler as HttpxCrawler
from ...crawler.playwright_crawler import (
    CrawlResult as CrawlResult,
)
from ...crawler.playwright_crawler import (
    PlaywrightCrawler as PlaywrightCrawler,
)
from ...crawler.quality_gate import QualityGate as QualityGate
from ...crawler.smart_router import (
    RouteType as RouteType,
)
from ...crawler.smart_router import (
    SmartRouter as SmartRouter,
)

if TYPE_CHECKING:
    from ...crawler.httpx_crawler import FastPathResult as FastPathResult

from value_fabric.shared.audit import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome
from value_fabric.shared.error_handling import sanitize_log_error
from value_fabric.shared.redis_ha import get_celery_redis_broker_config

from ...metrics.prometheus_metrics import get_metrics
from ...skills import get_extraction_schema as get_extraction_schema
from ...skills import get_skill
from ..config import settings
from ..database import get_db_session
from ..maintenance import (
    authorize_maintenance_operation as authorize_maintenance_operation,
)
from ..maintenance import (
    maintenance_audit_log as maintenance_audit_log,
)
from ..models import (
    AccountIntelligencePacket as AccountIntelligencePacket,
)
from ..models import (
    ComplianceEventType,
    ComplianceLog,
    EventOutbox,
    JobError,
    JobStageDetail,
    JobStatus,
    OutboxStatus,
    PipelineStage,
    ScrapingJob,
    ScrapingJobType,
    ScrapingTarget,
)
from ..models import (
    ExtractedData as ExtractedData,
)
from ..models import (
    ExtractionMethod as ExtractionMethod,
)
from ..models import (
    RawContent as RawContent,
)
from ..models import (
    SourceCorpus as SourceCorpus,
)
from ..models import (
    TenantRegistry as TenantRegistry,
)
from ..otel_celery import build_celery_options, start_celery_span
from ..task_contracts import (
    _execute_browser_pathResult as _execute_browser_pathResult,
)
from ..task_contracts import (
    ai_extraction_stageResult as ai_extraction_stageResult,
)
from ..task_contracts import (
    browser_crawl_stageResult as browser_crawl_stageResult,
)
from ..task_contracts import (
    cleanup_old_contentResult as cleanup_old_contentResult,
)
from ..task_contracts import (
    compliance_check_stageResult,
    process_scraping_jobResult,
)
from ..task_contracts import (
    crawl_url_with_routingResult as crawl_url_with_routingResult,
)
from ..task_contracts import (
    notification_stageResult as notification_stageResult,
)
from ..task_contracts import (
    post_processing_stageResult as post_processing_stageResult,
)
from ..task_contracts import (
    storage_stageResult as storage_stageResult,
)
from ..task_contracts import (
    validation_stageResult as validation_stageResult,
)

# Pure, stateless helpers extracted for readability — re-exported so both
# bare-name callers in this module and consumers importing from
# ``layer1_ingestion.shared.tasks`` keep resolving identically.
from ..tasks_helpers import (
    _domain_class,
    _is_stage_already_completed,
    _run_async,
)
from ..tasks_helpers import (
    _extract_unified_crawl_result as _extract_unified_crawl_result,
)
from ..tasks_helpers import (
    _get_target_config as _get_target_config,
)
from ..tasks_helpers import (
    _validate_payload_against_schema as _validate_payload_against_schema,
)

# Maximum delivery attempts before an outbox event is dead-lettered.
MAX_DISPATCH_ATTEMPTS = 5


logger = structlog.get_logger()


async def _verify_l3_graph_population(tenant_id: str, source_version_id: str) -> int:
    """Verify L3 graph has entities from the given source version.

    Calls L3 /v1/query/entities with source_version_id filter and returns count.
    """

    from ..config import settings

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


_celery_broker_url, _celery_transport_options = get_celery_redis_broker_config(settings.redis_url)

# Initialize Celery app
celery_app = Celery(
    "layer1_ingestion",
    broker=_celery_broker_url,
    backend=_celery_broker_url,
    include=["layer1_ingestion.shared.tasks"],
)

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
# DLQ FAILURE ROUTING (P0-02 / V1-QUEUE-001)
# =============================================================================


@task_failure.connect
def route_exhausted_task_to_dlq(
    sender=None,
    task_id=None,
    exception=None,
    args=None,
    kwargs=None,
    traceback=None,
    einfo=None,
    **extra,
):
    """Republish exhausted Celery tasks to the layer1_dlq dead-letter queue.

    The Redis transport has no broker-side dead-lettering, so the final retry
    loss path is patched by a task_failure signal handler. Only failures that
    have exhausted their retry budget are routed; retryable failures continue
    to follow Celery's normal retry path.
    """
    retries = getattr(getattr(sender, "request", None), "retries", 0)
    max_retries = getattr(sender, "max_retries", None)
    if not should_route_to_dlq(retries, max_retries):
        return

    tenant_id, job_id = extract_failure_context(args, kwargs)
    envelope = build_dlq_envelope(
        task_name=getattr(sender, "name", "unknown"),
        task_id=task_id,
        tenant_id=tenant_id,
        job_id=job_id,
        error=sanitize_log_error(exception) if exception else None,
        retries=retries,
        max_retries=max_retries,
    )
    celery_app.send_task(DLQ_TASK_NAME, args=[envelope], queue=DLQ_QUEUE_NAME)


# =============================================================================
# PIPELINE ORCHESTRATION
# =============================================================================


@celery_app.task(bind=True, max_retries=3)
def process_scraping_job(self, job_id: str, tenant_id: str):
    """Main pipeline orchestrator for a ScrapingJob.

    Chains all pipeline stages together for sequential execution.

    Args:
        job_id: The job UUID
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(job_id)
    tenant_uuid = UUID(tenant_id)

    try:
        if _check_tenant_kill_switch_sync(tenant_id):
            _fail_job(job_id, tenant_id, "Tenant suspended", PipelineStage.INIT)
            return process_scraping_jobResult.model_validate(
                {
                    "success": False,
                    "job_id": str(job_id),
                    "error": "Tenant suspended",
                    "task_id": None,
                }
            ).model_dump()
    except TenantKillSwitchUnavailable as exc:
        # Unknown suspension state is not allow: retry with backoff instead of
        # processing tenant-owned work (fail-safe and recoverable, unlike the
        # previous stub which always returned "not suspended").
        raise self.retry(exc=exc, countdown=30)

    logger.info("Starting scraping job pipeline", job_id=str(job_id), tenant_id=str(tenant_uuid))

    try:
        # Set tenant context BEFORE any database queries
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            job = session.query(ScrapingJob).get(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            # Start job
            job.status = JobStatus.VALIDATING.value
            job.started_at = datetime.now(UTC)

            # Skill-aware initialization: if configuration specifies a job_type,
            # resolve the skill and copy its metadata onto the job.
            job_type = job.configuration.get("job_type", ScrapingJobType.GENERIC_SCRAPE.value)
            job.job_type = job_type
            skill = get_skill(job_type)
            if skill:
                job.skill_name = skill.skill_name
                job.output_contract = skill.output_contract
                job.downstream_events = skill.downstream_events
                logger.info(
                    "Skill-aware job initialized",
                    job_id=str(job_id),
                    job_type=job_type,
                    skill_name=skill.skill_name,
                    output_contract=skill.output_contract,
                )

            session.commit()

        # Execute pipeline chain with tenant context
        pipeline_chain = chain(
            compliance_check_stage.s(job_id, tenant_id),
            browser_crawl_stage.s(tenant_id),
            ai_extraction_stage.s(tenant_id),
            post_processing_stage.s(tenant_id),
            validation_stage.s(tenant_id),
            storage_stage.s(tenant_id),
            notification_stage.s(tenant_id),
        )

        result = pipeline_chain.apply_async(**build_celery_options())

        return process_scraping_jobResult.model_validate(
            {"success": True, "job_id": str(job_id), "task_id": result.id}
        ).model_dump()

    except Exception as exc:
        logger.error(
            "Pipeline orchestration failed",
            job_id=str(job_id),
            error_code="PIPELINE_ORCHESTRATION_ERROR",
            error=sanitize_log_error(exc),
        )
        _fail_job(job_id, tenant_id, sanitize_log_error(exc)[:200], PipelineStage.INIT)
        metrics = get_metrics()
        if metrics:
            metrics.increment_retry_event(stage="orchestration", reason="pipeline_failure")
        raise self.retry(exc=exc, countdown=60)


# =============================================================================
# PIPELINE STAGES
# =============================================================================


@celery_app.task(bind=True, max_retries=3)
def compliance_check_stage(self, job_id: UUID, tenant_id: str):
    return _run_async(_compliance_check_stage_async(self, job_id, tenant_id))


async def _compliance_check_stage_async(self, job_id: UUID, tenant_id: str):
    """Stage 1: Compliance Check (robots.txt, rate limits, domain policies).

    Args:
        job_id: The job UUID
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    tenant_uuid = UUID(tenant_id)

    try:
        if _check_tenant_kill_switch_sync(tenant_id):
            _fail_job(job_id, tenant_id, "Tenant suspended", PipelineStage.COMPLIANCE_CHECK)
            return compliance_check_stageResult.model_validate(
                {"success": False, "job_id": str(job_id), "error": "Tenant suspended"}
            ).model_dump()
    except TenantKillSwitchUnavailable as exc:
        # Unknown suspension state is not allow: retry with backoff (fail-safe).
        raise self.retry(exc=exc, countdown=30)

    stage_started_at = time.monotonic()

    logger.info("Starting compliance check stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.compliance_check",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _record_queue_latency(job, PipelineStage.COMPLIANCE_CHECK)

                if _is_stage_already_completed(session, job_id, PipelineStage.COMPLIANCE_CHECK):
                    logger.info(
                        "Compliance check already completed (idempotent retry)", job_id=str(job_id)
                    )
                    return compliance_check_stageResult.model_validate(
                        {"success": True, "job_id": str(job_id)}
                    ).model_dump()

                _update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "RUNNING")
                job.status = JobStatus.VALIDATING.value
                job.progress_stage = PipelineStage.COMPLIANCE_CHECK.value
                session.commit()

                config = job.configuration
                url = config.get("url", "")
                target = (
                    session.query(ScrapingTarget).filter(ScrapingTarget.id == job.target_id).first()
                )
                compliance_allowlist = ((target.compliance or {}) if target else {}).get(
                    "domain_allowlist"
                )

                url = await _validate_url_safety(session, job, url, compliance_allowlist)
                if url is None:
                    return compliance_check_stageResult.model_validate(
                        {
                            "success": False,
                            "error": "URL blocked by compliance policy",
                            "job_id": str(job_id),
                        }
                    ).model_dump()

                config["url"] = url
                crawl_delay = await _check_robots_txt(
                    session, job, url, config.get("compliance", {})
                )
                if crawl_delay is None:
                    return compliance_check_stageResult.model_validate(
                        {"success": False, "error": "robots.txt blocked", "job_id": str(job_id)}
                    ).model_dump()

                if crawl_delay > 0:
                    _apply_crawl_delay(session, job_id, crawl_delay)
                    raise self.retry(countdown=int(crawl_delay))

                _update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "COMPLETED")
                session.commit()

                logger.info("Compliance check completed", job_id=str(job_id))
                _record_stage_completion(stage_started_at, PipelineStage.COMPLIANCE_CHECK)
                return compliance_check_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            if "Retry" in type(exc).__name__:
                raise
            logger.error(
                "Compliance check failed",
                job_id=str(job_id),
                error_code="COMPLIANCE_CHECK_ERROR",
                error=sanitize_log_error(exc),
            )
            _handle_compliance_error(
                exc, job_id, tenant_uuid, stage_started_at, PipelineStage.COMPLIANCE_CHECK
            )
            raise self.retry(exc=exc, countdown=30)


def _record_queue_latency(job, stage):
    """Record queue latency metrics."""
    queue_latency_seconds = max(0.0, (datetime.now(UTC) - job.created_at).total_seconds())
    metrics = get_metrics()
    if metrics:
        metrics.observe_queue_latency(
            queue_latency_seconds,
            stage=stage.value,
            status=job.status,
        )


async def _validate_url_safety(session, job, url, compliance_allowlist):
    """Validate URL safety and return normalized URL or None if blocked."""
    try:
        safety_result = validate_url_safety(url, allowlist_domains=compliance_allowlist)
        log_url_compliance_event(
            session,
            tenant_id=job.tenant_id,
            job_id=job.id,
            target_id=job.target_id,
            request_url=url,
            reason_code="URL_ALLOWED",
            action="ALLOWED",
        )
        return safety_result.normalized_url
    except URLSafetyError as exc:
        log_url_compliance_event(
            session,
            tenant_id=job.tenant_id,
            job_id=job.id,
            target_id=job.target_id,
            request_url=url,
            reason_code=exc.reason_code,
            action="BLOCKED",
        )
        session.commit()
        metrics = get_metrics()
        if metrics:
            metrics.increment_url_blocked(reason="url_safety", domain_class=_domain_class(url))
        try:
            emit_audit_event(
                action=AuditAction.URL_SAFETY_BLOCKED,
                outcome=AuditOutcome.DENIED,
                tenant_id=job.tenant_id,
                resource_type="ScrapingJob",
                resource_id=str(job.id),
                details={"url": url, "reason_code": exc.reason_code},
            )
        except Exception:
            logger.exception("url_safety_blocked_audit_failed")
        _fail_job(
            job.id,
            str(job.tenant_id),
            "URL blocked by compliance policy",
            PipelineStage.COMPLIANCE_CHECK,
        )
        return None


async def _check_robots_txt(session, job, url, compliance_config):
    """Check robots.txt and return crawl_delay or None if blocked."""
    if not compliance_config.get("respect_robots_txt", True):
        return 0

    checker = RobotsChecker(
        tenant_id=str(job.tenant_id),
        strict_mode=compliance_config.get("strict_robots_compliance", False),
    )
    parsed_url = urlparse(url)
    domain = parsed_url.netloc

    allowed, reason, rules = await checker.check_url(url, job_id=str(job.id))
    crawl_delay = rules.get("crawl_delay") if rules else None

    log = ComplianceLog(
        tenant_id=job.tenant_id,
        job_id=job.id,
        target_id=job.target_id,
        event_type=ComplianceEventType.ROBOTS_TXT_CHECK.value,
        severity="INFO" if allowed else "WARNING",
        robots_txt_check={
            "url": url,
            "robots_txt_url": f"https://{domain}/robots.txt",
            "user_agent": compliance_config.get("user_agent_string", "ValueFabricBot"),
            "allowed": allowed,
            "crawl_delay": crawl_delay,
        },
        request_url=url,
        request_user_agent=compliance_config.get("user_agent_string", "ValueFabricBot"),
    )
    session.add(log)

    if not allowed:
        metrics = get_metrics()
        if metrics:
            metrics.increment_url_blocked(reason="robots_txt", domain_class=_domain_class(url))
        try:
            emit_audit_event(
                action=AuditAction.URL_ROBOTS_BLOCKED,
                outcome=AuditOutcome.DENIED,
                tenant_id=job.tenant_id,
                resource_type="ScrapingJob",
                resource_id=str(job.id),
                details={"url": url, "reason": reason},
            )
        except Exception:
            logger.exception("url_robots_blocked_audit_failed")
        _fail_job(
            job.id, str(job.tenant_id), "URL blocked by robots.txt", PipelineStage.COMPLIANCE_CHECK
        )
        return None

    return crawl_delay if crawl_delay is not None else 0


def _apply_crawl_delay(session, job_id, crawl_delay):
    """Apply crawl delay via Celery retry."""
    _update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "RUNNING")
    session.commit()
    logger.info(
        "Applying crawl delay via Celery retry", job_id=str(job_id), crawl_delay_seconds=crawl_delay
    )


def _record_stage_completion(stage_started_at, stage):
    """Record stage completion metrics."""
    metrics = get_metrics()
    if metrics:
        metrics.observe_job_stage_duration(
            time.monotonic() - stage_started_at,
            stage=stage.value,
            status="completed",
        )


def _handle_compliance_error(exc, job_id, tenant_uuid, stage_started_at, stage):
    """Handle compliance check errors."""
    try:
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as error_session:
            _update_stage(error_session, job_id, stage, "FAILED", sanitize_log_error(exc)[:200])
    except Exception as update_exc:
        logger.error(
            "Failed to update stage status",
            job_id=str(job_id),
            error_code="COMPLIANCE_CHECK_ERROR",
            error=sanitize_log_error(update_exc),
        )
    metrics = get_metrics()
    if metrics:
        metrics.increment_retry_event(stage="compliance_check", reason="stage_failure")
        metrics.observe_job_stage_duration(
            time.monotonic() - stage_started_at,
            stage=stage.value,
            status="failed",
        )
































# =============================================================================
# EVENT OUTBOX DISPATCHER
# =============================================================================


@celery_app.task(bind=True, max_retries=MAX_DISPATCH_ATTEMPTS, default_retry_delay=30)
def dispatch_outbox_event(self, event_id: str, tenant_id: str):
    """Deliver a single EventOutbox record to configured sinks.

    On success: marks the row as dispatched.
    On failure: increments attempts, records last_error, retries with backoff.
    After MAX_DISPATCH_ATTEMPTS: moves to dead_letter.

    The initial sink is a structured log. The architecture supports adding
    HTTP adapter or other delivery mechanisms without changing this task.

    Args:
        event_id: The event UUID
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    event_uuid = UUID(event_id)
    tenant_uuid = UUID(tenant_id)

    with start_celery_span(
        self,
        "l1.pipeline.dispatch_outbox",
        attributes={"event_id": str(event_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                event = session.query(EventOutbox).filter(EventOutbox.id == event_uuid).first()
            if not event:
                logger.warning("EventOutbox row not found", event_id=event_id)
                return

            # Idempotency: skip if already dispatched or dead-lettered.
            if event.status in (OutboxStatus.DISPATCHED.value, OutboxStatus.DEAD_LETTER.value):
                logger.info(
                    "EventOutbox already settled, skipping",
                    event_id=event_id,
                    status=event.status,
                )
                return

            # Deliver to configured sink.
            # Initial implementation: structured log (no-op delivery).
            # Future: HTTP adapter, internal service call, etc.
            logger.info(
                "Dispatching outbox event",
                event_id=event_id,
                event_type=event.event_type,
                aggregate_type=event.aggregate_type,
                aggregate_id=event.aggregate_id,
                tenant_id=str(event.tenant_id),
                payload=event.payload,
            )

            # Mark dispatched.
            event.status = OutboxStatus.DISPATCHED.value
            event.dispatched_at = datetime.now(UTC)
            session.commit()

            logger.info(
                "EventOutbox dispatched",
                event_id=event_id,
                event_type=event.event_type,
            )

        except Exception as exc:
            logger.error(
                "EventOutbox dispatch failed",
                event_id=event_id,
                error_code="NOTIFICATION_ERROR",
                error=sanitize_log_error(exc),
                attempt=self.request.retries + 1,
            )

            should_retry = _handle_dispatch_failure(
                event_uuid, tenant_uuid, exc, self.request.retries
            )

            if not should_retry:
                return  # Dead-lettered, do not retry

            # Retry with exponential backoff.
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="notification", reason="dispatch_failure")
            raise self.retry(exc=exc, countdown=30 * (2**self.request.retries))


def _handle_dispatch_failure(
    event_uuid: UUID, tenant_uuid: UUID, exc: Exception, current_retries: int
) -> bool:
    """Handle dispatch failure and return whether to retry.

    Returns False if event was dead-lettered (no retry), True otherwise.
    """
    try:
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            event = session.query(EventOutbox).filter(EventOutbox.id == event_uuid).first()
            if not event:
                logger.warning(
                    "EventOutbox not found for failure handling, skipping retry",
                    event_id=str(event_uuid),
                )
                return False

            event.attempts = (event.attempts or 0) + 1
            event.last_error = sanitize_log_error(exc)[:200]

            if event.attempts >= MAX_DISPATCH_ATTEMPTS:
                event.status = OutboxStatus.DEAD_LETTER.value
                event.dead_lettered_at = datetime.now(UTC)
                logger.error(
                    "EventOutbox dead-lettered after max attempts",
                    event_id=str(event_uuid),
                    event_type=event.event_type,
                    attempts=event.attempts,
                )
                _emit_dead_letter_audit(event_uuid, tenant_uuid, event)
                _record_dead_letter_metrics()
                session.commit()
                return False  # Do not retry dead-lettered events
            else:
                event.status = OutboxStatus.FAILED.value
                session.commit()
                return True
    except Exception as inner_exc:
        logger.error(
            "Failed to record outbox dispatch error",
            event_id=str(event_uuid),
            error_code="NOTIFICATION_ERROR",
            error=sanitize_log_error(inner_exc),
        )
        return True


def _emit_dead_letter_audit(event_uuid: UUID, tenant_uuid: UUID, event):
    """Emit audit event for dead-lettered outbox event."""
    try:
        emit_audit_event(
            action=AuditAction.OUTBOX_DEAD_LETTERED,
            outcome=AuditOutcome.FAILURE,
            tenant_id=tenant_uuid,
            resource_type="EventOutbox",
            resource_id=str(event_uuid),
            details={
                "event_type": event.event_type,
                "attempts": event.attempts,
                "last_error": event.last_error,
            },
        )
    except Exception:
        logger.exception("outbox_dead_lettered_audit_failed")


def _record_dead_letter_metrics():
    """Record metrics for dead-lettered events."""
    metrics = get_metrics()
    if metrics:
        metrics.increment_outbox_dead_lettered()


# =============================================================================
# CANONICAL SOURCE INGESTION PIPELINE ORCHESTRATOR
# =============================================================================


@celery_app.task(bind=True, max_retries=3)
def run_pipeline_stage(self, stage_name: str, payload: dict):
    """Execute a single stage of the canonical source ingestion pipeline.

    Loads the run, validates the current step, delegates to the stage handler,
    and advances the run transactionally.

    Args:
        stage_name: IngestionRunStatus value for the stage to execute.
        payload: Outbox event payload containing run_id, tenant_id, etc.
    """
    import uuid

    from layer1_ingestion.orchestrator.outbox_relay import run_pipeline_stage_from_payload
    from layer1_ingestion.shared.database import get_db_session

    run_id = uuid.UUID(payload["run_id"])
    tenant_uuid = uuid.UUID(payload["tenant_id"])

    try:
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            run_pipeline_stage_from_payload(session, stage_name, payload)
            session.commit()
        logger.info(
            "Pipeline stage completed",
            run_id=str(run_id),
            stage_name=stage_name,
            tenant_id=str(tenant_uuid),
        )
    except Exception as exc:
        logger.error(
            "Pipeline stage failed",
            run_id=str(run_id),
            stage_name=stage_name,
            tenant_id=str(tenant_uuid),
            error=sanitize_log_error(exc),
        )
        # Retry with exponential backoff.
        raise self.retry(exc=exc, countdown=60 * (2**self.request.retries))


@celery_app.task
def dispatch_pipeline_outbox_events(max_events: int = 100):
    """Poll and dispatch pending pipeline events from the transactional outbox.

    This task is intended to be run on a Celery beat schedule.
    """
    from layer1_ingestion.orchestrator.outbox_relay import dispatch_pending_pipeline_events
    from layer1_ingestion.shared.database import get_db_session

    # We need a tenant context to query, but the relay handles all tenants.
    # Use a system/no-tenant session for the poll; downstream handlers enforce
    # tenant context per event.
    with get_db_session(require_tenant=False) as session:
        dispatched = dispatch_pending_pipeline_events(session, max_events=max_events)
        session.commit()

    logger.info(
        "Pipeline outbox relay dispatched events",
        dispatched_count=dispatched,
    )
    return {"dispatched": dispatched}


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================


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


class TenantKillSwitchUnavailable(RuntimeError):
    """Tenant kill-switch state cannot be determined (no Redis or lookup error).

    UNKNOWN is not ALLOW: a worker must not process tenant-owned work without a
    definitive suspension answer (same tri-state doctrine as the async API).
    """


def _check_tenant_kill_switch_sync(tenant_id: str) -> bool:
    """Check whether the tenant kill-switch is active.

    Returns True when the tenant is suspended and all work must fail closed.
    Raises TenantKillSwitchUnavailable when the state cannot be determined.
    """
    from value_fabric.shared.tenant_kill_switch import TenantSuspensionStatus, get_kill_switch

    status = get_kill_switch().check_status_sync(tenant_id)
    if status == TenantSuspensionStatus.UNKNOWN:
        raise TenantKillSwitchUnavailable(
            f"Tenant kill-switch state unknown for tenant {tenant_id}"
        )
    return status == TenantSuspensionStatus.SUSPENDED


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




@celery_app.task
def execute_pipeline_stage(job_id: str, stage: str, tenant_id: str):
    """Execute a single pipeline stage (for manual/retry operations).

    SECURITY: tenant_id is required and propagated to all stage dispatches.
    """
    job_id = UUID(job_id)
    stage_enum = PipelineStage(stage)

    # Dispatch to appropriate stage task
    stage_tasks = {
        PipelineStage.COMPLIANCE_CHECK.value: compliance_check_stage,
        PipelineStage.BROWSER_LAUNCH.value: browser_crawl_stage,
        PipelineStage.NAVIGATION.value: browser_crawl_stage,
        PipelineStage.CONTENT_CAPTURE.value: browser_crawl_stage,
        PipelineStage.AI_EXTRACTION.value: ai_extraction_stage,
        PipelineStage.POST_PROCESSING.value: post_processing_stage,
        PipelineStage.VALIDATION.value: validation_stage,
        PipelineStage.STORAGE.value: storage_stage,
        PipelineStage.NOTIFICATION.value: notification_stage,
    }

    task = stage_tasks.get(stage_enum.value)
    if task:
        # SECURITY: propagate trusted tenant_id from dispatch envelope
        return task.delay(str(job_id), tenant_id)
    else:
        raise ValueError(f"Unknown stage: {stage}")


# =============================================================================
# HYBRID ROUTING (Smart Router + HTTPX Fast Path)
# =============================================================================


# ==================================================================
# RE-EXPORTS: moved submodules (kept resolvable at package level)
# ==================================================================

from .cleanup import (
    _enumerate_authorized_tenants_for_cleanup as _enumerate_authorized_tenants_for_cleanup,
)
from .cleanup import (
    cleanup_old_content as cleanup_old_content,
)
from .cleanup import (
    purge_expired_raw_content as purge_expired_raw_content,
)
from .crawl import (
    _acrawl_url_with_routing as _acrawl_url_with_routing,
)
from .crawl import (
    _browser_crawl_stage_async as _browser_crawl_stage_async,
)
from .crawl import (
    _capture_raw_content as _capture_raw_content,
)
from .crawl import (
    _crawl_browser as _crawl_browser,
)
from .crawl import (
    _execute_browser_path as _execute_browser_path,
)
from .crawl import (
    _execute_browser_routing as _execute_browser_routing,
)
from .crawl import (
    _execute_fast_path as _execute_fast_path,
)
from .crawl import (
    _execute_fast_path_routing as _execute_fast_path_routing,
)
from .crawl import (
    _execute_fast_with_fallback_routing as _execute_fast_with_fallback_routing,
)
from .crawl import (
    _execute_routing as _execute_routing,
)
from .crawl import (
    _persist_routing_decision as _persist_routing_decision,
)
from .crawl import (
    _record_stage_metrics as _record_stage_metrics,
)
from .crawl import (
    _should_fail_closed as _should_fail_closed,
)
from .crawl import (
    browser_crawl_stage as browser_crawl_stage,
)
from .crawl import (
    crawl_url_with_routing as crawl_url_with_routing,
)
from .dlq import (
    record_dead_lettered_task as record_dead_lettered_task,
)
from .extraction import (
    _ai_extraction_stage_async as _ai_extraction_stage_async,
)
from .extraction import (
    ai_extraction_stage as ai_extraction_stage,
)
from .notification import (
    notification_stage as notification_stage,
)
from .post_processing import (
    post_processing_stage as post_processing_stage,
)
from .storage import (
    storage_stage as storage_stage,
)
from .validation import (
    validation_stage as validation_stage,
)
