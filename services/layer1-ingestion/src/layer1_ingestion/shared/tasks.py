"""Celery task queue configuration and tasks.

Spec-compliant pipeline stage tasks with multi-tenancy support.
Manages ScrapingJob lifecycle through 11 PipelineStages.
"""

import hashlib
import os
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
import structlog
from celery import Celery, chain
from celery.schedules import crontab
from celery.signals import task_failure

from .dlq import (
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

from ..compliance.pii_scanner import PIIScanner
from ..compliance.robots_checker import RobotsChecker
from ..compliance.url_safety import (
    URLSafetyError,
    enforce_rebinding_protection,
    log_url_compliance_event,
    validate_url_safety,
)
from ..crawler.decision_store import CrawlDecisionRecord, CrawlDecisionRepository
from ..crawler.httpx_crawler import HttpxCrawler
from ..crawler.playwright_crawler import CrawlResult, PlaywrightCrawler
from ..crawler.quality_gate import QualityGate
from ..crawler.smart_router import RouteType, SmartRouter

if TYPE_CHECKING:
    from ..crawler.httpx_crawler import FastPathResult

from value_fabric.shared.audit import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome
from value_fabric.shared.error_handling import sanitize_log_error
from value_fabric.shared.redis_ha import get_celery_redis_broker_config

from ..metrics.prometheus_metrics import get_metrics
from ..shared.config import settings
from ..shared.database import get_db_session
from ..shared.maintenance import authorize_maintenance_operation, maintenance_audit_log
from ..shared.models import (
    AccountIntelligencePacket,
    ComplianceEventType,
    ComplianceLog,
    EventOutbox,
    ExtractedData,
    ExtractionMethod,
    JobError,
    JobStageDetail,
    JobStatus,
    OutboxStatus,
    PipelineStage,
    RawContent,
    ScrapingJob,
    ScrapingJobType,
    ScrapingTarget,
    SourceCorpus,
    TenantRegistry,
)
from ..shared.otel_celery import build_celery_options, start_celery_span
from ..skills import get_extraction_schema, get_skill
from .task_contracts import (
    _execute_browser_pathResult,
    ai_extraction_stageResult,
    browser_crawl_stageResult,
    cleanup_old_contentResult,
    compliance_check_stageResult,
    crawl_url_with_routingResult,
    notification_stageResult,
    post_processing_stageResult,
    process_scraping_jobResult,
    storage_stageResult,
    validation_stageResult,
)

# Pure, stateless helpers extracted for readability — re-exported so both
# bare-name callers in this module and consumers importing from
# ``layer1_ingestion.shared.tasks`` keep resolving identically.
from .tasks_helpers import (
    _domain_class,
    _extract_unified_crawl_result,
    _get_target_config,
    _is_stage_already_completed,
    _run_async,
    _validate_payload_against_schema,
)

# Maximum delivery attempts before an outbox event is dead-lettered.
MAX_DISPATCH_ATTEMPTS = 5


logger = structlog.get_logger()


async def _verify_l3_graph_population(tenant_id: str, source_version_id: str) -> int:
    """Verify L3 graph has entities from the given source version.

    Calls L3 /v1/query/entities with source_version_id filter and returns count.
    """
    import httpx

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


@celery_app.task(bind=True, max_retries=3)
def browser_crawl_stage(self, prev_result: dict, tenant_id: str):
    return _run_async(_browser_crawl_stage_async(self, prev_result, tenant_id))


async def _browser_crawl_stage_async(self, prev_result: dict, tenant_id: str):
    """Stages 2-4: Smart crawl with routing (FAST / FAST_WITH_FALLBACK / BROWSER).

    OPTIMIZATION: Integrates SmartRouter to choose between HTTPX fast path
    and Playwright browser path. Merges launch+navigate+capture into one task,
    eliminating redundant browser launches and enabling fast path for static content.

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)
    stage_started_at = time.monotonic()

    logger.info("Starting smart crawl stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.browser_crawl",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                config = job.configuration
                url = config.get("url", "")
                browser_config = config.get("browser_config", {})
                target_config = _get_target_config(session, job)
                tenant_id_str = str(job.tenant_id) if job.tenant_id else None
                effective_mode = target_config.get("crawl_path", "browser")

                # Stage 2: Browser Launch
                _update_stage(session, job_id, PipelineStage.BROWSER_LAUNCH, "RUNNING")
                job.status = JobStatus.BROWSER_ACQUIRING.value
                job.progress_stage = PipelineStage.BROWSER_LAUNCH.value
                job.resources_browser_sessions_used += 1
                session.commit()

                # Execute routing
                crawl_result, fast_result, final_path, decision_record = await _execute_routing(
                    url, browser_config, effective_mode, job_id, tenant_id_str
                )

                # Persist routing decision
                await _persist_routing_decision(decision_record, final_path, url, tenant_id)
                _update_stage(session, job_id, PipelineStage.BROWSER_LAUNCH, "COMPLETED")
                _record_stage_metrics(stage_started_at, PipelineStage.BROWSER_LAUNCH)

                # Stage 3: Navigation
                _update_stage(session, job_id, PipelineStage.NAVIGATION, "RUNNING")
                job.status = JobStatus.NAVIGATING.value
                job.progress_stage = PipelineStage.NAVIGATION.value
                session.commit()

                if crawl_result and crawl_result.error:
                    raise Exception(crawl_result.error)

                final_url, status_code, headers, html_content, title, duration_ms = (
                    _extract_unified_crawl_result(fast_result, crawl_result, final_path)
                )

                job.configuration["navigation_result"] = {
                    "final_url": final_url,
                    "status_code": status_code,
                    "headers": headers,
                }
                _update_stage(session, job_id, PipelineStage.NAVIGATION, "COMPLETED")

                # Stage 4: Content Capture
                raw_content_id = await _capture_raw_content(
                    session,
                    job,
                    url,
                    final_url,
                    status_code,
                    headers,
                    title,
                    html_content,
                    duration_ms,
                    fast_result,
                    final_path,
                )

                _update_stage(session, job_id, PipelineStage.CONTENT_CAPTURE, "COMPLETED")
                session.commit()

                logger.info(
                    "Smart crawl completed",
                    job_id=str(job_id),
                    raw_content_id=str(raw_content_id),
                    final_path=final_path,
                    final_url=final_url,
                )
                return browser_crawl_stageResult.model_validate(
                    {
                        "success": True,
                        "job_id": str(job_id),
                        "raw_content_id": str(raw_content_id),
                    }
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Smart crawl failed",
                job_id=str(job_id),
                error_code="SMART_CRAWL_ERROR",
                error=sanitize_log_error(exc),
            )
            for stage in (
                PipelineStage.BROWSER_LAUNCH,
                PipelineStage.NAVIGATION,
                PipelineStage.CONTENT_CAPTURE,
            ):
                with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                    _update_stage(session, job_id, stage, "FAILED", sanitize_log_error(exc)[:200])
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="browser_crawl", reason="stage_failure")
                metrics.observe_job_stage_duration(
                    time.monotonic() - stage_started_at,
                    stage="crawl_path_execution",
                    status="failed",
                )
            raise self.retry(exc=exc, countdown=30)


async def _execute_routing(
    url: str, browser_config: dict, effective_mode: str, job_id: UUID, tenant_id: str
):
    """Execute routing decision and return crawl results."""
    router = SmartRouter()
    gate = QualityGate()

    route_type = RouteType(effective_mode)
    routing_decision = router.decide(url, route_type)

    decision_record = CrawlDecisionRecord(
        decision_id=str(uuid4()),
        job_id=str(job_id),
        tenant_id=tenant_id,
        url=url,
        domain=urlparse(url).netloc,
        requested_path=effective_mode,
        router_decision=routing_decision.route.value,
        router_rule=routing_decision.reason,
        quality_passed=None,
        quality_checks=None,
        fallback_reason=None,
        final_path="unknown",
        status_code=None,
        fast_duration_ms=0,
        browser_duration_ms=None,
        fetch_time_ms=0,
        bytes_transferred=0,
        spa_detected=False,
        text_length=0,
    )

    crawl_result = None
    fast_result = None
    final_path = "unknown"

    if routing_decision.route == RouteType.FAST:
        fast_result, decision_record = await _execute_fast_path_routing(
            url, fast_result, decision_record
        )
        final_path = "fast"
    elif routing_decision.route == RouteType.FAST_WITH_FALLBACK:
        crawl_result, fast_result, decision_record, final_path = (
            await _execute_fast_with_fallback_routing(
                url, browser_config, gate, fast_result, decision_record
            )
        )
    else:  # RouteType.BROWSER
        crawl_result, decision_record, final_path = await _execute_browser_routing(
            url, browser_config, decision_record
        )

    return crawl_result, fast_result, final_path, decision_record


async def _execute_fast_path_routing(url: str, fast_result, decision_record):
    """Execute fast path routing."""
    logger.info("Using FAST path (HTTPX)", url=url)
    fast_result = await _execute_fast_path(url)
    html_bytes = (fast_result.html or "").encode("utf-8")
    decision_record.final_path = "fast"
    decision_record.status_code = fast_result.status_code
    decision_record.fast_duration_ms = fast_result.fetch_time_ms
    decision_record.fetch_time_ms = fast_result.fetch_time_ms
    decision_record.bytes_transferred = len(html_bytes)
    decision_record.spa_detected = fast_result.is_spa_detected
    decision_record.text_length = len(fast_result.text_content)
    decision_record.quality_passed = fast_result.status_code == 200
    decision_record.quality_checks = {"direct_fast": True}
    return fast_result, decision_record


async def _execute_fast_with_fallback_routing(
    url: str, browser_config: dict, gate, fast_result, decision_record
):
    """Execute fast with fallback routing."""
    logger.info("Using FAST_WITH_FALLBACK path", url=url)
    fast_result = await _execute_fast_path(url)
    decision_record.fast_duration_ms = fast_result.fetch_time_ms
    decision_record.spa_detected = fast_result.is_spa_detected
    quality = gate.evaluate(fast_result)
    decision_record.quality_passed = quality.passed
    decision_record.quality_checks = quality.checks
    decision_record.fallback_reason = quality.fallback_reason

    if quality.passed:
        final_path = "fast"
        decision_record.final_path = "fast"
        decision_record.status_code = fast_result.status_code
        decision_record.fetch_time_ms = fast_result.fetch_time_ms
        decision_record.bytes_transferred = len((fast_result.html or "").encode("utf-8"))
        decision_record.text_length = len(fast_result.text_content)
        logger.info("Fast path succeeded", duration_ms=fast_result.fetch_time_ms)
        crawl_result = None
    else:
        logger.warning(
            "Fast path failed quality, escalating to browser",
            url=url,
            fallback_reason=quality.fallback_reason,
        )
        crawl_result = await _crawl_browser(url, browser_config)
        final_path = "fallback"
        decision_record.final_path = "fallback"
        decision_record.status_code = crawl_result.status_code
        decision_record.browser_duration_ms = crawl_result.duration_ms
        decision_record.fetch_time_ms = fast_result.fetch_time_ms + crawl_result.duration_ms
        decision_record.bytes_transferred = len((fast_result.html or "").encode("utf-8")) + len(
            (crawl_result.html_content or "").encode("utf-8")
        )
        decision_record.text_length = len(crawl_result.html_content or "") // 10

    return crawl_result, fast_result, decision_record, final_path


async def _execute_browser_routing(url: str, browser_config: dict, decision_record):
    """Execute browser routing."""
    logger.info("Using BROWSER path (Playwright)", url=url)
    crawl_result = await _crawl_browser(url, browser_config)
    final_path = "browser"
    decision_record.final_path = "browser"
    decision_record.status_code = crawl_result.status_code
    decision_record.browser_duration_ms = crawl_result.duration_ms
    decision_record.fetch_time_ms = crawl_result.duration_ms
    decision_record.bytes_transferred = len((crawl_result.html_content or "").encode("utf-8"))
    decision_record.text_length = len(crawl_result.html_content or "") // 10
    return crawl_result, decision_record, final_path


async def _persist_routing_decision(decision_record, final_path, url, tenant_id):
    """Persist routing decision and emit path metric."""
    decision_repo = CrawlDecisionRepository()
    await decision_repo.save(decision_record, trusted_tenant_id=tenant_id)
    metrics = get_metrics()
    if metrics:
        metrics.increment_crawl_path(path=final_path, domain_class=_domain_class(url))


def _record_stage_metrics(stage_started_at, stage):
    """Record stage duration metrics."""
    metrics = get_metrics()
    if metrics:
        metrics.observe_job_stage_duration(
            time.monotonic() - stage_started_at,
            stage=stage.value,
            status="completed",
        )


async def _capture_raw_content(
    session,
    job,
    url,
    final_url,
    status_code,
    headers,
    title,
    html_content,
    duration_ms,
    fast_result,
    final_path,
):
    """Capture raw content to database."""
    _update_stage(session, job.id, PipelineStage.CONTENT_CAPTURE, "RUNNING")
    job.status = JobStatus.EXTRACTING.value
    job.progress_stage = PipelineStage.CONTENT_CAPTURE.value
    session.commit()

    content_hash = hashlib.sha256(html_content.encode()).hexdigest()
    existing = (
        session.query(RawContent)
        .filter(
            RawContent.tenant_id == job.tenant_id,
            RawContent.content_hash == content_hash,
        )
        .first()
    )
    is_duplicate = existing is not None

    capture_method = "STATIC" if fast_result and final_path == "fast" else "DYNAMIC"
    js_executed = not (fast_result and final_path == "fast")

    raw_content = RawContent(
        job_id=job.id,
        tenant_id=job.tenant_id,
        target_id=job.target_id,
        source_url=url,
        source_final_url=final_url,
        source_domain=url.split("/")[2] if "/" in url else url,
        source_http_status=status_code,
        source_headers=headers,
        meta_title=title,
        capture_method=capture_method,
        capture_javascript_executed=js_executed,
        capture_wait_time_ms=duration_ms,
        content_hash=content_hash,
        is_duplicate=is_duplicate,
        duplicate_of_id=existing.id if existing else None,
        processing_status="PENDING",
    )
    session.add(raw_content)
    session.flush()
    job.configuration["raw_content_id"] = str(raw_content.id)
    job.results_raw_content_count += 1

    return raw_content.id


@celery_app.task(bind=True, max_retries=5)
def ai_extraction_stage(self, prev_result: dict, tenant_id: str):
    return _run_async(_ai_extraction_stage_async(self, prev_result, tenant_id))


async def _ai_extraction_stage_async(self, prev_result: dict, tenant_id: str):
    """Stage 5: AI/LLM Extraction (conditional based on config).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting AI extraction stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.ai_extraction",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                config = job.configuration
                extraction_config = config.get("extraction_config", {})
                method = extraction_config.get("method", "DETERMINISTIC")

                # Skill-aware extraction: override schema if a skill is configured
                skill_schema = get_extraction_schema(job.job_type)
                if skill_schema:
                    extraction_config = {**extraction_config, "extraction_schema": skill_schema}
                    job.configuration["extraction_config"] = extraction_config
                    logger.info(
                        "Using skill-specific extraction schema",
                        job_id=str(job_id),
                        skill_name=job.skill_name,
                    )

                if method == ExtractionMethod.DETERMINISTIC.value:
                    logger.info("Skipping AI extraction (deterministic mode)", job_id=str(job_id))
                    return ai_extraction_stageResult.model_validate(
                        {"success": True, "job_id": str(job_id), "skipped": True}
                    ).model_dump()

                _update_stage(session, job_id, PipelineStage.AI_EXTRACTION, "RUNNING")
                job.progress_stage = PipelineStage.AI_EXTRACTION.value
                session.commit()

                raw_content_id = config.get("raw_content_id")
                raw_content = (
                    session.query(RawContent).get(UUID(raw_content_id)) if raw_content_id else None
                )

                if not raw_content:
                    raise ValueError("Raw content not found for AI extraction")

                l2_url = settings.layer2_api_url
                extraction_model = extraction_config.get(
                    "model", os.getenv("EXTRACTION_MODEL", settings.openai_model)
                )
                extraction_payload = {
                    "content": raw_content.meta_title or "",
                    "content_type": "text",
                    "extraction_method": method.lower(),
                    "source_id": str(raw_content_id),
                    "source_version_id": str(raw_content_id),  # For L3 graph population tracking
                    "job_id": str(job_id),
                    "tenant_id": str(job.tenant_id),
                    "model_version": extraction_config.get("model_version", extraction_model),
                    "schema_version": extraction_config.get("schema_version", "1.0"),
                    "prompt_version": extraction_config.get(
                        "prompt_version", "entity_extraction_v1"
                    ),
                    "options": {
                        "model": extraction_model,
                        "temperature": extraction_config.get("temperature", 0.0),
                        "max_tokens": extraction_config.get("max_tokens", 4000),
                    },
                }
                # Pass skill-specific schema downstream if configured
                schema = extraction_config.get("extraction_schema")
                if schema:
                    extraction_payload["extraction_schema"] = schema

                # OPTIMIZATION: Use Celery for L2 dispatch when enabled (async queue-based processing)
                # Falls back to HTTP if Celery disabled or unavailable
                use_celery_dispatch = (
                    settings.use_celery_for_l2
                )  # Local flag to avoid race condition
                if use_celery_dispatch:
                    try:
                        # Import Celery for cross-service dispatch
                        from celery import Celery

                        # Create a Celery client pointing to L2's broker
                        l2_celery = Celery(
                            "layer2_extraction",
                            broker=settings.layer2_celery_broker_url,
                            backend=settings.layer2_celery_broker_url,
                        )

                        # Dispatch task to L2 Celery worker with extract-and-ingest
                        logger.info(
                            "Dispatching extract-and-ingest task to L2 Celery", job_id=str(job_id)
                        )
                        result = l2_celery.send_task(
                            "layer2_extraction.shared.tasks.run_extraction_task",
                            args=[
                                str(job_id),
                                job.source_url or "",
                                raw_content.meta_title or "",
                                extraction_payload,
                            ],
                            kwargs={
                                "mark_pipeline_complete": False,
                                "use_extract_and_ingest": True,
                            },
                        )

                        # Wait for result with timeout
                        extraction_result = result.get(timeout=300)
                        tokens_consumed = extraction_result.get("tokens_consumed", 0)
                        logger.info(
                            "L2 Celery extract-and-ingest completed",
                            job_id=str(job_id),
                            task_id=result.id,
                        )

                    except Exception as e:
                        logger.warning(
                            "L2 Celery dispatch failed, falling back to HTTP",
                            job_id=str(job_id),
                            error=repr(e),
                        )
                        # Fall through to HTTP fallback
                        use_celery_dispatch = False  # Disable for this run
                else:
                    logger.info("Using HTTP fallback for L2 extract-and-ingest", job_id=str(job_id))

                # HTTP fallback (extract-and-ingest endpoint for graph population)
                if not use_celery_dispatch:
                    # P1-001: Sign S2S JWT for L2 authentication
                    s2s_token = None
                    if encode_service_jwt is not None:
                        s2s_token = encode_service_jwt(
                            tenant_id=job.tenant_id,
                            sub="layer1-ingestion",
                            aud="layer2-extraction",
                        )

                    async def _call_l2():
                        request_headers = {
                            "Content-Type": "application/json",
                            "X-Tenant-ID": str(job.tenant_id),
                        }
                        if s2s_token:
                            request_headers["Authorization"] = f"Bearer {s2s_token}"
                        async with httpx.AsyncClient(timeout=60.0) as client:
                            response = await client.post(
                                f"{l2_url}/v1/extract-and-ingest",
                                json=extraction_payload,
                                headers=request_headers,
                            )
                            response.raise_for_status()
                            return response.json()

                    try:
                        extraction_result = await _call_l2()
                        tokens_consumed = extraction_result.get("tokens_consumed", 0)
                    except httpx.HTTPStatusError as e:
                        if e.response.status_code in (429, 503, 504):
                            logger.warning(
                                "L2 transient error, returning to queue via Celery retry",
                                job_id=str(job_id),
                                status=e.response.status_code,
                            )
                            raise self.retry(exc=e, countdown=15)
                        raise ValueError(
                            f"L2 extract-and-ingest failed: HTTP {e.response.status_code}: {e.response.text}"
                        )
                    except Exception as e:
                        logger.warning(
                            "L2 extract-and-ingest failed, retrying via Celery",
                            job_id=str(job_id),
                            error_code="L2_EXTRACTION_ERROR",
                        )
                        raise self.retry(exc=e, countdown=30)

                job.configuration["extraction_result"] = extraction_result

                # Verify L3 graph population from this source version
                l3_entity_count = await _verify_l3_graph_population(
                    tenant_id=str(job.tenant_id),
                    source_version_id=str(raw_content_id),
                )
                logger.info(
                    "L3 graph population verified",
                    job_id=str(job_id),
                    source_version_id=str(raw_content_id),
                    entities_in_graph=l3_entity_count,
                )

                _update_stage(session, job_id, PipelineStage.AI_EXTRACTION, "COMPLETED")
                job.resources_llm_tokens_consumed += tokens_consumed
                session.commit()

                logger.info(
                    "AI extraction completed",
                    job_id=str(job_id),
                    tokens_consumed=tokens_consumed,
                    entities_extracted=len(extraction_result.get("entities", [])),
                )
                return ai_extraction_stageResult.model_validate(
                    {
                        "success": True,
                        "job_id": str(job_id),
                        "tokens_consumed": tokens_consumed,
                        "entities_extracted": len(extraction_result.get("entities", [])),
                    }
                ).model_dump()

        except Exception as exc:
            if "Retry" in type(exc).__name__:
                raise
            logger.error(
                "AI extraction failed",
                job_id=str(job_id),
                error_code="AI_EXTRACTION_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session,
                    job_id,
                    PipelineStage.AI_EXTRACTION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="ai_extraction", reason="stage_failure")
            raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=2)
def post_processing_stage(self, prev_result: dict, tenant_id: str):
    """Stage 6: Post-processing (PII redaction, normalization).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting post-processing stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.post_processing",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _update_stage(session, job_id, PipelineStage.POST_PROCESSING, "RUNNING")
                job.status = JobStatus.TRANSFORMING.value
                job.progress_stage = PipelineStage.POST_PROCESSING.value
                session.commit()

                config = job.configuration
                compliance_config = config.get("compliance", {})
                raw_content_id = config.get("raw_content_id")

                if raw_content_id:
                    raw_content = session.query(RawContent).get(UUID(raw_content_id))

                    if raw_content and compliance_config.get("pii_redaction_enabled", True):
                        # Scan for PII
                        scanner = PIIScanner()
                        scan_result = scanner.scan(raw_content.meta_title or "")
                        scan_result.extend(scanner.scan(raw_content.meta_description or ""))

                        # Log PII detection
                        if scan_result:
                            log = ComplianceLog(
                                tenant_id=job.tenant_id,
                                job_id=job_id,
                                target_id=job.target_id,
                                event_type=ComplianceEventType.PII_DETECTED.value,
                                severity="WARNING",
                                pii_detection={
                                    "detection_method": "REGEX",
                                    "patterns_detected": [
                                        {"pattern_type": r.type, "count": 1, "locations": [r.text]}
                                        for r in scan_result
                                    ],
                                    "redaction_applied": True,
                                    "redacted_count": len(scan_result),
                                },
                                request_url=raw_content.source_url,
                                response_action_taken="REDACTED",
                            )
                            session.add(log)

                # Skill-aware post-processing: build structured intelligence outputs
                skill = get_skill(job.job_type)
                if skill:
                    raw_contents = (
                        session.query(RawContent).filter(RawContent.job_id == job_id).all()
                    )
                    extracted_data = (
                        session.query(ExtractedData).filter(ExtractedData.job_id == job_id).all()
                    )
                    skill_output = skill.build_output(job, raw_contents, extracted_data)
                    # Store in job configuration for downstream stages
                    job.configuration["skill_output"] = skill_output
                    job.configuration["output_contract"] = skill.output_contract
                    logger.info(
                        "Skill output built",
                        job_id=str(job_id),
                        skill_name=skill.skill_name,
                        output_contract=skill.output_contract,
                    )

                _update_stage(session, job_id, PipelineStage.POST_PROCESSING, "COMPLETED")
                session.commit()

                logger.info("Post-processing completed", job_id=str(job_id))
                return post_processing_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Post-processing failed",
                job_id=str(job_id),
                error_code="POST_PROCESSING_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session,
                    job_id,
                    PipelineStage.POST_PROCESSING,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="post_processing", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, max_retries=2)
def validation_stage(self, prev_result: dict, tenant_id: str):
    """Stage 7: Validation (schema, data quality).

    Validates the job's ExtractedData payload against the extraction_schema
    stored in the job configuration.  Results are written back to the
    ExtractedData record so downstream stages and the API can surface them.

    If no extraction_schema is configured the stage completes successfully
    without modifying the ExtractedData record (schema validation is opt-in).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting validation stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.validation",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _update_stage(session, job_id, PipelineStage.VALIDATION, "RUNNING")
                job.progress_stage = PipelineStage.VALIDATION.value
                session.commit()

                config = job.configuration
                extraction_config = config.get("extraction_config", {})
                schema = extraction_config.get("extraction_schema")

                if schema and isinstance(schema, dict):
                    # Locate the ExtractedData record produced by ai_extraction_stage
                    extracted = (
                        session.query(ExtractedData)
                        .filter(
                            ExtractedData.job_id == job_id,
                            ExtractedData.tenant_id == job.tenant_id,
                        )
                        .order_by(ExtractedData.provenance_extracted_at.desc())
                        .first()
                    )

                    if extracted is not None:
                        payload = extracted.data or {}
                        schema_valid, errors, required_present, required_missing = (
                            _validate_payload_against_schema(payload, schema)
                        )

                        extracted.validation_schema_valid = schema_valid
                        extracted.validation_errors = errors
                        extracted.validation_required_fields_present = required_present
                        extracted.validation_required_fields_missing = required_missing

                        if not schema_valid:
                            logger.warning(
                                "Extracted data failed schema validation",
                                job_id=str(job_id),
                                tenant_id=str(job.tenant_id),
                                error_count=len(errors),
                                required_missing=required_missing,
                            )
                        else:
                            logger.info(
                                "Extracted data passed schema validation",
                                job_id=str(job_id),
                                tenant_id=str(job.tenant_id),
                            )
                    else:
                        logger.info(
                            "No ExtractedData record found; skipping schema validation",
                            job_id=str(job_id),
                        )
                else:
                    logger.info(
                        "No extraction_schema configured; skipping schema validation",
                        job_id=str(job_id),
                    )

                _update_stage(session, job_id, PipelineStage.VALIDATION, "COMPLETED")
                session.commit()

                logger.info("Validation completed", job_id=str(job_id))
                return validation_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Validation failed",
                job_id=str(job_id),
                error_code="VALIDATION_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session,
                    job_id,
                    PipelineStage.VALIDATION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="validation", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True, max_retries=3)
def storage_stage(self, prev_result: dict, tenant_id: str):
    """Stage 8: Storage (save to database, update references).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting storage stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.storage",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _update_stage(session, job_id, PipelineStage.STORAGE, "RUNNING")
                job.status = JobStatus.STORING.value
                job.progress_stage = PipelineStage.STORAGE.value
                session.commit()

                config = job.configuration
                raw_content_id = config.get("raw_content_id")

                if raw_content_id:
                    raw_content = session.query(RawContent).get(UUID(raw_content_id))
                    if raw_content:
                        extraction_started_at = datetime.now(UTC)
                        # Create ExtractedData record
                        extracted = ExtractedData(
                            job_id=job_id,
                            tenant_id=job.tenant_id,
                            target_id=job.target_id,
                            raw_content_id=raw_content.id,
                            extraction_method=config.get("extraction_config", {}).get(
                                "method", "DETERMINISTIC"
                            ),
                            extraction_time_ms=None,
                            data={
                                "title": raw_content.meta_title,
                                "description": raw_content.meta_description,
                                "url": raw_content.source_url,
                            },
                            provenance_source_url=raw_content.source_url,
                            storage_path=raw_content.storage_html_path,
                            format="JSON",
                        )
                        extracted.extraction_time_ms = int(
                            (datetime.now(UTC) - extraction_started_at).total_seconds() * 1000
                        )
                        session.add(extracted)
                        session.flush()

                        # Update references
                        raw_content.extracted_data_id = extracted.id
                        raw_content.processing_status = "EXTRACTED"

                        job.results_extracted_record_count += 1
                        job.results_storage_bytes_used += raw_content.source_content_length or 0

                # Skill-aware storage: persist structured intelligence output
                skill_output = config.get("skill_output")
                output_contract = config.get("output_contract")
                if skill_output and output_contract:
                    if output_contract == "SourceCorpus":
                        # Idempotent: skip if a SourceCorpus already exists for this job
                        existing_corpus = (
                            session.query(SourceCorpus)
                            .filter(
                                SourceCorpus.job_id == job_id,
                                SourceCorpus.tenant_id == job.tenant_id,
                            )
                            .first()
                        )
                        if existing_corpus:
                            logger.info(
                                "SourceCorpus already exists (idempotent retry)",
                                job_id=str(job_id),
                                corpus_id=str(existing_corpus.id),
                            )
                        else:
                            corpus = SourceCorpus(
                                tenant_id=job.tenant_id,
                                company_id=skill_output.get("company_id"),
                                company_name=skill_output.get("company_name", "Unknown"),
                                corpus_type=skill_output.get(
                                    "corpus_type", "licensing_company_ontology_seed"
                                ),
                                source_groups=skill_output.get("source_groups", []),
                                candidate_concepts=skill_output.get("candidate_concepts", []),
                                provenance=skill_output.get("provenance", []),
                                extraction_status=skill_output.get(
                                    "extraction_status", "ready_for_extraction"
                                ),
                                job_id=job_id,
                            )
                            session.add(corpus)
                            session.flush()
                            logger.info(
                                "SourceCorpus stored",
                                job_id=str(job_id),
                                corpus_id=str(corpus.id),
                                company_name=corpus.company_name,
                            )
                    elif output_contract == "AccountIntelligencePacket":
                        # Idempotent: skip if a packet already exists for this job
                        existing_packet = (
                            session.query(AccountIntelligencePacket)
                            .filter(
                                AccountIntelligencePacket.job_id == job_id,
                                AccountIntelligencePacket.tenant_id == job.tenant_id,
                            )
                            .first()
                        )
                        if existing_packet:
                            logger.info(
                                "AccountIntelligencePacket already exists (idempotent retry)",
                                job_id=str(job_id),
                                packet_id=str(existing_packet.id),
                            )
                        else:
                            packet = AccountIntelligencePacket(
                                tenant_id=job.tenant_id,
                                account_id=skill_output.get("account_id"),
                                account_name=skill_output.get("account_name", "Unknown"),
                                packet_type=skill_output.get("packet_type", "prospect_research"),
                                company_profile=skill_output.get("company_profile", {}),
                                observed_signals=skill_output.get("observed_signals", []),
                                likely_pain_areas=skill_output.get("likely_pain_areas", []),
                                likely_stakeholders=skill_output.get("likely_stakeholders", []),
                                source_references=skill_output.get("source_references", []),
                                confidence_summary=skill_output.get("confidence_summary", {}),
                                next_recommended_events=skill_output.get(
                                    "next_recommended_events", []
                                ),
                                job_id=job_id,
                            )
                            session.add(packet)
                            session.flush()
                            logger.info(
                                "AccountIntelligencePacket stored",
                                job_id=str(job_id),
                                packet_id=str(packet.id),
                                account_name=packet.account_name,
                            )

                _update_stage(session, job_id, PipelineStage.STORAGE, "COMPLETED")
                session.commit()

                logger.info("Storage completed", job_id=str(job_id))
                return storage_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Storage failed",
                job_id=str(job_id),
                error_code="STORAGE_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session, job_id, PipelineStage.STORAGE, "FAILED", sanitize_log_error(exc)[:200]
                )
            metrics = get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="storage", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)


@celery_app.task(bind=True)
def notification_stage(self, prev_result: dict, tenant_id: str):
    """Stage 9: Notification (webhooks, callbacks).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting notification stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.notification",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    return notification_stageResult.model_validate(
                        {"success": False, "job_id": str(job_id), "error": "Job not found"}
                    ).model_dump()

                _update_stage(session, job_id, PipelineStage.NOTIFICATION, "RUNNING")
                job.progress_stage = PipelineStage.NOTIFICATION.value
                session.commit()

                # Complete job
                job.status = JobStatus.COMPLETED.value
                job.completed_at = datetime.now(UTC)
                job.progress_percent_complete = 100
                job.progress_stage = PipelineStage.NOTIFICATION.value

                _update_stage(session, job_id, PipelineStage.NOTIFICATION, "COMPLETED")
                session.commit()

                # Update target stats
                target = session.query(ScrapingTarget).get(job.target_id)
                if target:
                    target.success_count += 1
                    target.last_success_at = datetime.now(UTC)
                    # Calculate average execution time
                    if job.started_at and job.completed_at:
                        duration = (job.completed_at - job.started_at).total_seconds() * 1000
                        total_duration = (
                            target.average_execution_time_ms * (target.success_count - 1) + duration
                        )
                        target.average_execution_time_ms = int(
                            total_duration / target.success_count
                        )
                    session.commit()

                # Skill-aware event emission via durable transactional outbox.
                # Events are persisted in the same session as job completion so
                # they are only emitted after durable storage succeeds.
                if job.downstream_events and job.skill_name:
                    # Resolve the output record ID for the event payload.
                    output_id: str | None = None
                    if job.output_contract == "SourceCorpus":
                        corpus = (
                            session.query(SourceCorpus)
                            .filter(
                                SourceCorpus.job_id == job_id,
                                SourceCorpus.tenant_id == job.tenant_id,
                            )
                            .first()
                        )
                        output_id = str(corpus.id) if corpus else None
                    elif job.output_contract == "AccountIntelligencePacket":
                        packet = (
                            session.query(AccountIntelligencePacket)
                            .filter(
                                AccountIntelligencePacket.job_id == job_id,
                                AccountIntelligencePacket.tenant_id == job.tenant_id,
                            )
                            .first()
                        )
                        output_id = str(packet.id) if packet else None

                    emitted_at = datetime.now(UTC).isoformat()
                    outbox_ids: list[UUID] = []

                    for event_type in job.downstream_events:
                        outbox_row = EventOutbox(
                            tenant_id=job.tenant_id,
                            event_type=event_type,
                            aggregate_type=job.output_contract or "unknown",
                            aggregate_id=output_id or str(job_id),
                            payload={
                                "event_type": event_type,
                                "tenant_id": str(job.tenant_id),
                                "job_id": str(job_id),
                                "output_contract": job.output_contract,
                                "output_id": output_id,
                                "skill_name": job.skill_name,
                                "aggregate_type": job.output_contract or "unknown",
                                "aggregate_id": output_id or str(job_id),
                                "emitted_at": emitted_at,
                            },
                            status=OutboxStatus.PENDING.value,
                        )
                        session.add(outbox_row)
                        session.flush()
                        outbox_ids.append(outbox_row.id)
                        logger.info(
                            "EventOutbox row created",
                            event_id=str(outbox_row.id),
                            event_type=event_type,
                            job_id=str(job_id),
                            tenant_id=str(job.tenant_id),
                        )

                    # Commit outbox rows together with job completion.
                    session.commit()

                    # Enqueue async dispatch for each outbox row with tenant context
                    for event_id in outbox_ids:
                        dispatch_outbox_event.apply_async(
                            args=[str(event_id), str(job.tenant_id)],
                            countdown=1,
                        )

                logger.info("Job completed successfully", job_id=str(job_id))
                return notification_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id), "error": None}
                ).model_dump()

        except Exception as exc:
            logger.error(
                "Notification stage failed",
                job_id=str(job_id),
                error_code="NOTIFICATION_ERROR",
                error=sanitize_log_error(exc),
            )
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _update_stage(
                    session,
                    job_id,
                    PipelineStage.NOTIFICATION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            return notification_stageResult.model_validate(
                {"success": False, "job_id": str(job_id), "error": "Notification stage failed"}
            ).model_dump()


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


@celery_app.task(queue=DLQ_QUEUE_NAME, max_retries=0)
def record_dead_lettered_task(envelope: dict[str, Any]) -> dict[str, Any]:
    """Consume a dead-letter envelope and durably record the failure (P0-02).

    Persists a JobError with error_code TASK_DEAD_LETTERED and stage
    DEAD_LETTER when the envelope carries a tenant_id + job_id. Missing
    context is handled log-only so the DLQ consumer itself does not spin.
    """
    tenant_id = envelope.get("tenant_id")
    job_id = envelope.get("job_id")
    original_task = envelope.get("original_task", "unknown")

    try:
        metrics = get_metrics()
        if metrics:
            metrics.increment_task_dead_lettered(original_task=original_task)
    except Exception as exc:
        logger.warning("Failed to increment DLQ metric", error=sanitize_log_error(exc))

    if not tenant_id or not job_id:
        logger.warning(
            "Dead-letter envelope missing tenant_id or job_id; log-only",
            envelope=envelope,
        )
        return {"recorded": False, "reason": "missing_tenant_or_job"}

    try:
        tenant_uuid = UUID(tenant_id)
        job_uuid = UUID(job_id)
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            job = session.query(ScrapingJob).get(job_uuid)
            job_tenant_id = job.tenant_id if job else tenant_uuid
            error_record = JobError(
                job_id=job_uuid,
                tenant_id=job_tenant_id,
                stage="DEAD_LETTER",
                error_code="TASK_DEAD_LETTERED",
                error_message=envelope.get("error")
                or "Task exhausted retries and was dead-lettered",
                retryable=False,
            )
            session.add(error_record)
            session.commit()
            logger.info(
                "Dead-lettered task recorded",
                job_id=str(job_uuid),
                tenant_id=str(tenant_uuid),
                original_task=original_task,
            )
            return {"recorded": True, "job_id": job_id}
    except Exception as exc:
        logger.error(
            "Failed to record dead-lettered task",
            error=sanitize_log_error(exc),
            envelope=envelope,
        )
        raise


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


@celery_app.task(bind=True, max_retries=3)
def crawl_url_with_routing(
    self, job_id: str, url: str, tenant_id: str, target_mode: str = "browser"
):
    return _run_async(_acrawl_url_with_routing(self, job_id, url, tenant_id, target_mode))


async def _acrawl_url_with_routing(
    self, job_id: str, url: str, tenant_id: str, target_mode: str = "browser"
):
    """Crawl a single URL with Smart Router and hybrid FAST/BROWSER paths.

    Implements the hardening-pass routing logic with:
    - Smart Router per-URL decision making
    - HTTPX Fast Path for static content
    - Quality-gated fallback to browser
    - Canonical decision record persistence
    - Fail-closed behavior for ambiguous cases

    Args:
        job_id: The ScrapingJob UUID
        url: URL to crawl
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope (required)
        target_mode: Target-level mode (fast/browser/fast_fallback)

    Returns:
        dict with crawl result metadata
    """
    job_id_uuid = UUID(job_id)
    tenant_uuid = UUID(tenant_id)
    router = SmartRouter()
    gate = QualityGate()
    decision_repo = CrawlDecisionRepository()

    logger.info(
        "Starting hybrid crawl",
        job_id=job_id,
        url=url,
        target_mode=target_mode,
        tenant_id=str(tenant_uuid),
    )

    with start_celery_span(
        self,
        "l1.pipeline.crawl_url_with_routing",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id_uuid)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                target = session.query(ScrapingTarget).get(job.target_id)
                target_config = target.extraction_config or {} if target else {}

                # Use target's crawl_path if available, otherwise use parameter
                effective_mode = target_config.get("crawl_path", target_mode)

            # Parse URL for domain extraction
            parsed_url = urlparse(url)
            domain = parsed_url.netloc

            # SECURITY: Validate URL safety before any routing decision
            safety_result = validate_url_safety(url)
            enforce_rebinding_protection(safety_result.normalized_url, safety_result.resolved_ips)

            # 1. ROUTING DECISION
            route_type = RouteType(effective_mode)
            routing_decision = router.decide(url, route_type)

            # Initialize decision record
            decision_record = CrawlDecisionRecord(
                decision_id=str(uuid4()),
                job_id=job_id,
                tenant_id=tenant_id,
                url=url,
                domain=domain,
                requested_path=effective_mode,
                router_decision=routing_decision.route.value,
                router_rule=routing_decision.reason,
                quality_passed=None,
                quality_checks=None,
                fallback_reason=None,
                final_path="unknown",  # Will be updated
                status_code=None,
                fast_duration_ms=0,
                browser_duration_ms=None,
                fetch_time_ms=0,
                bytes_transferred=0,
                spa_detected=False,
                text_length=0,
            )

            # 2. EXECUTE BASED ON ROUTING DECISION
            if routing_decision.route == RouteType.FAST:
                # Direct fast path
                result = await _execute_fast_path(url)

                decision_record.final_path = "fast"
                decision_record.status_code = result.status_code
                decision_record.fast_duration_ms = result.fetch_time_ms
                decision_record.fetch_time_ms = result.fetch_time_ms
                decision_record.bytes_transferred = len(result.html.encode("utf-8"))
                decision_record.spa_detected = result.is_spa_detected
                decision_record.text_length = len(result.text_content)

                if result.status_code == 200:
                    decision_record.quality_passed = True
                    decision_record.quality_checks = {"direct_fast": True}

            elif routing_decision.route == RouteType.FAST_WITH_FALLBACK:
                # Try fast path, fallback if quality fails
                result = await _execute_fast_path(url)

                decision_record.fast_duration_ms = result.fetch_time_ms
                decision_record.spa_detected = result.is_spa_detected

                # Quality gate evaluation
                quality = gate.evaluate(result)
                decision_record.quality_passed = quality.passed
                decision_record.quality_checks = quality.checks
                decision_record.fallback_reason = quality.fallback_reason

                if quality.passed:
                    # Fast path succeeded
                    decision_record.final_path = "fast"
                    decision_record.status_code = result.status_code
                    decision_record.fetch_time_ms = result.fetch_time_ms
                    decision_record.bytes_transferred = len(result.html.encode("utf-8"))
                    decision_record.text_length = len(result.text_content)

                    logger.info(
                        "Fast path succeeded",
                        job_id=job_id,
                        url=url,
                        duration_ms=result.fetch_time_ms,
                    )
                else:
                    # FAIL-CLOSED: Fast path failed quality, escalate to browser
                    logger.warning(
                        "Fast path failed quality, escalating to browser",
                        job_id=job_id,
                        url=url,
                        fallback_reason=quality.fallback_reason,
                    )

                    browser_result = await _execute_browser_path(
                        url, routing_decision.stagehand_config
                    )

                    decision_record.final_path = "fallback"
                    decision_record.status_code = browser_result.get("status_code")
                    decision_record.browser_duration_ms = browser_result.get("duration_ms", 0)
                    decision_record.fetch_time_ms = result.fetch_time_ms + browser_result.get(
                        "duration_ms", 0
                    )
                    decision_record.bytes_transferred = len(
                        result.html.encode("utf-8")
                    ) + browser_result.get("content_length", 0)
                    decision_record.text_length = browser_result.get("text_length", 0)

            else:  # RouteType.BROWSER
                # Direct browser path
                browser_result = await _execute_browser_path(url, routing_decision.stagehand_config)

                decision_record.final_path = "browser"
                decision_record.status_code = browser_result.get("status_code")
                decision_record.browser_duration_ms = browser_result.get("duration_ms", 0)
                decision_record.fetch_time_ms = browser_result.get("duration_ms", 0)
                decision_record.bytes_transferred = browser_result.get("content_length", 0)
                decision_record.text_length = browser_result.get("text_length", 0)

            # 3. PERSIST CANONICAL DECISION
            await decision_repo.save(decision_record, trusted_tenant_id=tenant_uuid)

            logger.info(
                "Crawl completed with routing",
                job_id=job_id,
                url=url,
                final_path=decision_record.final_path,
                duration_ms=decision_record.fetch_time_ms,
            )

            return crawl_url_with_routingResult.model_validate(
                {
                    "success": True,
                    "job_id": job_id,
                    "url": url,
                    "final_path": decision_record.final_path,
                    "duration_ms": decision_record.fetch_time_ms,
                    "decision_id": decision_record.decision_id,
                }
            ).model_dump()

        except Exception as exc:
            logger.error(
                "Crawl failed",
                job_id=job_id,
                url=url,
                error_code="SMART_CRAWL_ERROR",
                error=sanitize_log_error(exc),
                exc_info=True,
            )

            # Try to save error decision if we have a decision record
            if "decision_record" in locals():
                decision_record.error_type = type(exc).__name__
                decision_record.error_message = sanitize_log_error(exc)[
                    :500
                ]  # Truncate long messages
                try:
                    await decision_repo.save(decision_record, trusted_tenant_id=tenant_uuid)
                except Exception:
                    pass  # Don't let decision save failure mask original error

            raise self.retry(exc=exc, countdown=60)


async def _execute_fast_path(url: str) -> "FastPathResult":
    """Execute HTTPX fast path crawl.

    Args:
        url: URL to fetch

    Returns:
        FastPathResult with content and metadata
    """
    result = validate_url_safety(url)
    enforce_rebinding_protection(result.normalized_url, result.resolved_ips)
    async with HttpxCrawler() as crawler:
        return await crawler.fetch(result.normalized_url)


async def _crawl_browser(url: str, browser_config: dict) -> "CrawlResult":
    """Execute Playwright browser crawl using proper CrawlerConfig.

    Args:
        url: URL to crawl
        browser_config: Browser configuration dict with headless, wait_for_selector, etc.

    Returns:
        CrawlResult with rendered HTML and metadata
    """
    from ..crawler.crawler_config import CrawlerConfig

    cfg = CrawlerConfig(headless=browser_config.get("headless", True))
    result = validate_url_safety(url)
    enforce_rebinding_protection(result.normalized_url, result.resolved_ips)
    async with PlaywrightCrawler(config=cfg) as crawler:
        return await crawler.crawl_url(
            url=result.normalized_url,
            wait_for_selector=browser_config.get("wait_for_selector"),
            wait_for_timeout=browser_config.get("wait_timeout", 30000),
            scroll_page=True,
        )


async def _execute_browser_path(url: str, config: dict | None) -> dict:
    """Execute Playwright browser path crawl.

    Args:
        url: URL to crawl
        config: Optional Stagehand/browser configuration

    Returns:
        dict with browser crawl results
    """
    start_time = time.monotonic()

    # SECURITY: Validate URL safety before browser crawl
    safety_result = validate_url_safety(url)
    enforce_rebinding_protection(safety_result.normalized_url, safety_result.resolved_ips)

    # Actual Playwright integration
    browser_config = config or {}
    wait_for_selector = browser_config.get("wait_for_selector")
    wait_timeout = browser_config.get("wait_timeout", 30000)

    from ..crawler.crawler_config import CrawlerConfig

    crawler_cfg = CrawlerConfig(headless=browser_config.get("headless", True))
    async with PlaywrightCrawler(config=crawler_cfg) as crawler:
        result = await crawler.crawl_url(
            url=safety_result.normalized_url,
            wait_for_selector=wait_for_selector,
            wait_for_timeout=wait_timeout,
            scroll_page=True,
        )

    duration_ms = int((time.monotonic() - start_time) * 1000)

    return _execute_browser_pathResult.model_validate(
        {
            "status_code": result.status_code or 200,
            "duration_ms": duration_ms,
            "content_length": len(result.html_content or ""),
            "text_length": len(result.html_content or "") // 10,  # Approximate text ratio
            "title": result.title,
            "final_url": result.final_url,
            "error": result.error,
            "config_used": config,
            "blocked_resources": result.blocked_resources,
            "scroll_triggered": result.scroll_triggered,
        }
    ).model_dump()


def _should_fail_closed(quality_result, fast_result, routing_decision) -> tuple[bool, str | None]:
    """Determine if we should fail closed to browser path.

    Fail-closed rules:
    1. Quality result is ambiguous/uncertain
    2. Fast path timing is borderline (within 90% of timeout)
    3. Content quality is indeterminate
    4. Router confidence is low

    Args:
        quality_result: QualityGate evaluation result
        fast_result: FastPathResult from HTTPX
        routing_decision: SmartRouter decision

    Returns:
        Tuple of (should_fallback, reason)
    """
    # Rule 1: Quality gate uncertain
    if quality_result.passed is None:
        return True, "quality_uncertain"

    # Rule 2: Borderline timing (within 90% of threshold)
    if fast_result.fetch_time_ms > 4500:  # 90% of 5000ms default
        return True, "timing_borderline"

    # Rule 3: Indeterminate content quality
    if not fast_result.text_content and not fast_result.is_spa_detected:
        return True, "indeterminate_quality"

    # Rule 4: Router uncertainty (default_with_fallback on ambiguous URL)
    if routing_decision.reason == "default_with_fallback" and not quality_result.passed:
        return True, "router_uncertain"

    return False, None


@celery_app.task
def _enumerate_authorized_tenants_for_cleanup() -> list[UUID]:
    """Enumerate active tenants from system-owned registry with explicit authorization."""
    authorize_maintenance_operation("cleanup_old_content", tenant_id="tenant-registry")

    correlation_id = str(uuid4())
    with maintenance_audit_log("cleanup_old_content", tenant_id="tenant-registry") as record:
        record.metadata = {
            "tenant_iteration_source": "tenant_registry",
            "source_scope": "system_owned",
            "require_tenant": False,
            "correlation_id": correlation_id,
        }
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            tenant_ids = [
                row[0]
                for row in session.query(TenantRegistry.tenant_id)
                .filter(TenantRegistry.is_active.is_(True))
                .all()
            ]
        record.rows_affected = len(tenant_ids)

    logger.info(
        "System maintenance tenant enumeration completed",
        operation="cleanup_old_content",
        tenant_iteration_source="tenant_registry",
        source_scope="system_owned",
        require_tenant=False,
        correlation_id=correlation_id,
        tenants_discovered=len(tenant_ids),
    )
    return tenant_ids


def cleanup_old_content(days: int = 30, tenant_id: str = None):
    """Clean up raw content older than specified days.

    This function implements tenant-by-tenant cleanup under RLS by default.
    System-scoped cleanup requires explicit system maintenance authorization.

    Args:
        days: Number of days to retain content
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
                   If None, requires system maintenance authorization

    Raises:
        SystemMaintenanceAuthorizationError: If system-scoped operation lacks authorization
        InvalidTenantContextError: If tenant_id is provided but invalid
    """
    from .exceptions import InvalidTenantContextError

    cutoff_date = datetime.now(UTC) - timedelta(days=days)

    # Validate tenant context if provided
    if tenant_id:
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError):
            raise InvalidTenantContextError(
                f"Invalid tenant_id format: {tenant_id}", tenant_id=tenant_id
            )

        # Tenant-scoped cleanup under RLS
        logger.info(
            "Starting tenant-scoped content cleanup",
            cutoff_date=cutoff_date.isoformat(),
            tenant_id=str(tenant_uuid),
        )

        with maintenance_audit_log("cleanup_old_content", tenant_id=str(tenant_uuid)) as record:
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                deleted_count = (
                    session.query(RawContent)
                    .filter(
                        RawContent.created_at < cutoff_date,
                        RawContent.processing_status != "DELETED",
                    )
                    .update({"processing_status": "DELETED"}, synchronize_session=False)
                )

                session.commit()
                record.rows_affected = deleted_count

                logger.info(
                    "Tenant-scoped content cleanup completed",
                    deleted_count=deleted_count,
                    cutoff_date=cutoff_date.isoformat(),
                    tenant_id=str(tenant_uuid),
                )

                return cleanup_old_contentResult.model_validate(
                    {"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat()}
                ).model_dump()

    else:
        # System-scoped: iterate tenants individually under RLS.
        # Use tenant_registry (system table, no RLS) instead of tenant-owned tables.

        # Emit metric for tenant enumeration observability
        metrics = get_metrics()
        if metrics:
            metrics.increment_maintenance_tenant_enumeration()

        # Audit log entry before TenantRegistry query
        logger.info(
            "System maintenance: beginning tenant enumeration",
            operation="cleanup_old_content",
            tenant_id=None,
            system_identity="fabric4l-system-maintenance",
            correlation_id=str(uuid4()),
        )

        tenant_ids = _enumerate_authorized_tenants_for_cleanup()

        total_deleted = 0
        failed_tenants = []
        started_at = datetime.now(UTC)

        for tenant_uuid in tenant_ids:
            try:
                with maintenance_audit_log(
                    "cleanup_old_content", tenant_id=str(tenant_uuid)
                ) as record:
                    with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                        deleted_count = (
                            session.query(RawContent)
                            .filter(
                                RawContent.created_at < cutoff_date,
                                RawContent.processing_status != "DELETED",
                            )
                            .update({"processing_status": "DELETED"}, synchronize_session=False)
                        )

                        session.commit()
                        record.rows_affected = deleted_count
                        total_deleted += deleted_count
            except Exception as e:
                failed_tenants.append(
                    (str(tenant_uuid), repr(e))  # ban-str-e-allow: internal-tracking
                )
                logger.error(
                    "Tenant cleanup failed",
                    tenant_id=str(tenant_uuid),
                    error=repr(e),
                )

        completed_at = datetime.now(UTC)

        # Aggregate summary audit event
        logger.info(
            "System maintenance audit record",
            operation="cleanup_old_content",
            tenant_id=None,
            system_identity="fabric4l-system-maintenance",
            correlation_id=str(uuid4()),
            timestamp=datetime.now(UTC).isoformat(),
            started_at=started_at.isoformat(),
            completed_at=completed_at.isoformat(),
            rows_affected=total_deleted,
            success=len(failed_tenants) == 0,
            error_message=(
                None if not failed_tenants else f"Failed tenants: {[t[0] for t in failed_tenants]}"
            ),
            metadata={
                "tenants_processed": len(tenant_ids),
                "failed_tenants": failed_tenants,
            },
        )

        logger.info(
            "System cleanup completed",
            total_deleted=total_deleted,
            tenants_processed=len(tenant_ids),
            failed_count=len(failed_tenants),
            cutoff_date=cutoff_date.isoformat(),
        )

        return cleanup_old_contentResult.model_validate(
            {
                "deleted_count": total_deleted,
                "cutoff_date": cutoff_date.isoformat(),
            }
        ).model_dump()


@celery_app.task(
    name="layer1_ingestion.shared.tasks.purge_expired_raw_content", bind=True, max_retries=2
)
def purge_expired_raw_content(self) -> dict:
    """Celery beat task: purge raw content whose per-record retention window has elapsed.

    Uses the per-record ``retention_raw_content_expiry_days`` column (default 30 days)
    to determine which rows are eligible for soft-deletion. Runs daily via the
    ``beat_schedule`` configured on ``celery_app``.

    Delegates to :func:`cleanup_old_content` for the actual deletion logic, which
    iterates over active tenants under RLS to ensure tenant isolation.
    """
    try:
        # Use the default retention window; per-record granularity can be added later.
        return cleanup_old_content(days=30, tenant_id=None)
    except Exception as exc:
        logger.error("purge_expired_raw_content failed: %s", exc)
        raise self.retry(exc=exc, countdown=3600)  # retry after 1 hour
