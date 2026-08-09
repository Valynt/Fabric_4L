"""Scraping pipeline orchestration and stage tasks."""

import hashlib
import os
import time
from datetime import UTC, datetime
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
from jsonschema import Draft7Validator

try:
    from value_fabric.shared.identity.jwt import encode_service_jwt
except ImportError:
    encode_service_jwt = None  # type: ignore

from value_fabric.shared.audit import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome
from value_fabric.shared.error_handling import sanitize_log_error

from ..compliance.pii_scanner import PIIScanner
from ..compliance.url_safety import (
    URLSafetyError,
    log_url_compliance_event,
)
from ..crawler.decision_store import CrawlDecisionRecord
from ..crawler.smart_router import RouteType
from ..shared.models import (
    AccountIntelligencePacket,
    ComplianceEventType,
    ComplianceLog,
    ExtractedData,
    ExtractionMethod,
    JobError,
    JobStageDetail,
    JobStatus,
    PipelineStage,
    RawContent,
    ScrapingJob,
    ScrapingJobType,
    ScrapingTarget,
    SourceCorpus,
)
from ..shared.otel_celery import build_celery_options, start_celery_span
from ..skills import get_extraction_schema
from .task_contracts import (
    ai_extraction_stageResult,
    browser_crawl_stageResult,
    compliance_check_stageResult,
    post_processing_stageResult,
    process_scraping_jobResult,
    storage_stageResult,
    validation_stageResult,
)

__all__ = [
    "process_scraping_job",
    "compliance_check_stage",
    "_compliance_check_stage_async",
    "_record_queue_latency",
    "_is_stage_already_completed",
    "_validate_url_safety",
    "_check_robots_txt",
    "_apply_crawl_delay",
    "_record_stage_completion",
    "_handle_compliance_error",
    "browser_crawl_stage",
    "_browser_crawl_stage_async",
    "_get_target_config",
    "_execute_routing",
    "_execute_fast_path_routing",
    "_execute_fast_with_fallback_routing",
    "_execute_browser_routing",
    "_persist_routing_decision",
    "_record_stage_metrics",
    "_extract_unified_crawl_result",
    "_capture_raw_content",
    "ai_extraction_stage",
    "_ai_extraction_stage_async",
    "post_processing_stage",
    "_validate_payload_against_schema",
    "validation_stage",
    "storage_stage",
    "_update_stage",
    "_check_tenant_kill_switch_sync",
    "_fail_job",
    "execute_pipeline_stage",
]

from . import tasks as _compat

_domain_class = _compat._domain_class
_run_async = _compat._run_async
_verify_l3_graph_population = _compat._verify_l3_graph_population
celery_app = _compat.celery_app


@celery_app.task(
    name="layer1_ingestion.shared.tasks.process_scraping_job", bind=True, max_retries=3
)
def process_scraping_job(self, job_id: str, tenant_id: str):
    """Main pipeline orchestrator for a ScrapingJob.

    Chains all pipeline stages together for sequential execution.

    Args:
        job_id: The job UUID
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(job_id)
    tenant_uuid = UUID(tenant_id)

    if _compat._check_tenant_kill_switch_sync(tenant_id):
        _compat._fail_job(job_id, tenant_id, "Tenant suspended", PipelineStage.INIT)
        return process_scraping_jobResult.model_validate(
            {"success": False, "job_id": str(job_id), "error": "Tenant suspended", "task_id": None}
        ).model_dump()

    _compat.logger.info(
        "Starting scraping job pipeline", job_id=str(job_id), tenant_id=str(tenant_uuid)
    )

    try:
        # Set tenant context BEFORE any database queries
        with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
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
            skill = _compat.get_skill(job_type)
            if skill:
                job.skill_name = skill.skill_name
                job.output_contract = skill.output_contract
                job.downstream_events = skill.downstream_events
                _compat.logger.info(
                    "Skill-aware job initialized",
                    job_id=str(job_id),
                    job_type=job_type,
                    skill_name=skill.skill_name,
                    output_contract=skill.output_contract,
                )

            session.commit()

        # Resolve the delivery task lazily to keep task modules acyclic.
        from .delivery_tasks import notification_stage

        # Execute pipeline _compat.chain with tenant context
        pipeline_chain = _compat.chain(
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
        _compat.logger.error(
            "Pipeline orchestration failed",
            job_id=str(job_id),
            error_code="PIPELINE_ORCHESTRATION_ERROR",
            error=sanitize_log_error(exc),
        )
        _compat._fail_job(job_id, tenant_id, sanitize_log_error(exc)[:200], PipelineStage.INIT)
        metrics = _compat.get_metrics()
        if metrics:
            metrics.increment_retry_event(stage="orchestration", reason="pipeline_failure")
        raise self.retry(exc=exc, countdown=60)


# =============================================================================
# PIPELINE STAGES
# =============================================================================


@celery_app.task(
    name="layer1_ingestion.shared.tasks.compliance_check_stage", bind=True, max_retries=3
)
def compliance_check_stage(self, job_id: UUID, tenant_id: str):
    return _run_async(_compat._compliance_check_stage_async(self, job_id, tenant_id))


async def _compliance_check_stage_async(self, job_id: UUID, tenant_id: str):
    """Stage 1: Compliance Check (robots.txt, rate limits, domain policies).

    Args:
        job_id: The job UUID
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    tenant_uuid = UUID(tenant_id)

    if _compat._check_tenant_kill_switch_sync(tenant_id):
        _compat._fail_job(job_id, tenant_id, "Tenant suspended", PipelineStage.COMPLIANCE_CHECK)
        return compliance_check_stageResult.model_validate(
            {"success": False, "job_id": str(job_id), "error": "Tenant suspended"}
        ).model_dump()

    stage_started_at = time.monotonic()

    _compat.logger.info(
        "Starting compliance check stage", job_id=str(job_id), tenant_id=str(tenant_uuid)
    )
    with start_celery_span(
        self,
        "l1.pipeline.compliance_check",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _record_queue_latency(job, PipelineStage.COMPLIANCE_CHECK)

                if _is_stage_already_completed(session, job_id, PipelineStage.COMPLIANCE_CHECK):
                    _compat.logger.info(
                        "Compliance check already completed (idempotent retry)", job_id=str(job_id)
                    )
                    return compliance_check_stageResult.model_validate(
                        {"success": True, "job_id": str(job_id)}
                    ).model_dump()

                _compat._update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "RUNNING")
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

                _compat._update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "COMPLETED")
                session.commit()

                _compat.logger.info("Compliance check completed", job_id=str(job_id))
                _record_stage_completion(stage_started_at, PipelineStage.COMPLIANCE_CHECK)
                return compliance_check_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            if "Retry" in type(exc).__name__:
                raise
            _compat.logger.error(
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
    metrics = _compat.get_metrics()
    if metrics:
        metrics.observe_queue_latency(
            queue_latency_seconds,
            stage=stage.value,
            status=job.status,
        )


def _is_stage_already_completed(session, job_id, stage):
    """Check if stage is already completed (idempotency)."""
    existing_stage = (
        session.query(JobStageDetail)
        .filter(
            JobStageDetail.job_id == job_id,
            JobStageDetail.stage == stage.value,
        )
        .first()
    )
    return existing_stage and existing_stage.status == "COMPLETED"


async def _validate_url_safety(session, job, url, compliance_allowlist):
    """Validate URL safety and return normalized URL or None if blocked."""
    try:
        safety_result = _compat.validate_url_safety(url, allowlist_domains=compliance_allowlist)
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
        metrics = _compat.get_metrics()
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
            _compat.logger.exception("url_safety_blocked_audit_failed")
        _compat._fail_job(
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

    checker = _compat.RobotsChecker(
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
        metrics = _compat.get_metrics()
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
            _compat.logger.exception("url_robots_blocked_audit_failed")
        _compat._fail_job(
            job.id, str(job.tenant_id), "URL blocked by robots.txt", PipelineStage.COMPLIANCE_CHECK
        )
        return None

    return crawl_delay if crawl_delay is not None else 0


def _apply_crawl_delay(session, job_id, crawl_delay):
    """Apply crawl delay via Celery retry."""
    _compat._update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "RUNNING")
    session.commit()
    _compat.logger.info(
        "Applying crawl delay via Celery retry", job_id=str(job_id), crawl_delay_seconds=crawl_delay
    )


def _record_stage_completion(stage_started_at, stage):
    """Record stage completion metrics."""
    metrics = _compat.get_metrics()
    if metrics:
        metrics.observe_job_stage_duration(
            time.monotonic() - stage_started_at,
            stage=stage.value,
            status="completed",
        )


def _handle_compliance_error(exc, job_id, tenant_uuid, stage_started_at, stage):
    """Handle compliance check errors."""
    try:
        with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as error_session:
            _compat._update_stage(
                error_session, job_id, stage, "FAILED", sanitize_log_error(exc)[:200]
            )
    except Exception as update_exc:
        _compat.logger.error(
            "Failed to update stage status",
            job_id=str(job_id),
            error_code="COMPLIANCE_CHECK_ERROR",
            error=sanitize_log_error(update_exc),
        )
    metrics = _compat.get_metrics()
    if metrics:
        metrics.increment_retry_event(stage="compliance_check", reason="stage_failure")
        metrics.observe_job_stage_duration(
            time.monotonic() - stage_started_at,
            stage=stage.value,
            status="failed",
        )


@celery_app.task(name="layer1_ingestion.shared.tasks.browser_crawl_stage", bind=True, max_retries=3)
def browser_crawl_stage(self, prev_result: dict, tenant_id: str):
    return _run_async(_compat._browser_crawl_stage_async(self, prev_result, tenant_id))


async def _browser_crawl_stage_async(self, prev_result: dict, tenant_id: str):
    """Stages 2-4: Smart crawl with routing (FAST / FAST_WITH_FALLBACK / BROWSER).

    OPTIMIZATION: Integrates _compat.SmartRouter to choose between HTTPX fast path
    and Playwright browser path. Merges launch+navigate+capture into one task,
    eliminating redundant browser launches and enabling fast path for static content.

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)
    stage_started_at = time.monotonic()

    _compat.logger.info(
        "Starting smart crawl stage", job_id=str(job_id), tenant_id=str(tenant_uuid)
    )
    with start_celery_span(
        self,
        "l1.pipeline.browser_crawl",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
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
                _compat._update_stage(session, job_id, PipelineStage.BROWSER_LAUNCH, "RUNNING")
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
                _compat._update_stage(session, job_id, PipelineStage.BROWSER_LAUNCH, "COMPLETED")
                _record_stage_metrics(stage_started_at, PipelineStage.BROWSER_LAUNCH)

                # Stage 3: Navigation
                _compat._update_stage(session, job_id, PipelineStage.NAVIGATION, "RUNNING")
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
                _compat._update_stage(session, job_id, PipelineStage.NAVIGATION, "COMPLETED")

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

                _compat._update_stage(session, job_id, PipelineStage.CONTENT_CAPTURE, "COMPLETED")
                session.commit()

                _compat.logger.info(
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
            _compat.logger.error(
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
                with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                    _compat._update_stage(
                        session, job_id, stage, "FAILED", sanitize_log_error(exc)[:200]
                    )
            metrics = _compat.get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="browser_crawl", reason="stage_failure")
                metrics.observe_job_stage_duration(
                    time.monotonic() - stage_started_at,
                    stage="crawl_path_execution",
                    status="failed",
                )
            raise self.retry(exc=exc, countdown=30)


def _get_target_config(session, job) -> dict:
    """Get target configuration from job."""
    target_config = {}
    if job.target_id:
        target = session.query(ScrapingTarget).get(job.target_id)
        if target:
            target_config = target.extraction_config or {}
    return target_config


async def _execute_routing(
    url: str, browser_config: dict, effective_mode: str, job_id: UUID, tenant_id: str
):
    """Execute routing decision and return crawl results."""
    router = _compat.SmartRouter()
    gate = _compat.QualityGate()

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

    if routing_decision.route == RouteType.FAST:
        fast_result, decision_record = await _execute_fast_path_routing(
            url, fast_result, decision_record
        )
        final_path = "fast"
    elif routing_decision.route == RouteType.FAST_WITH_FALLBACK:
        (
            crawl_result,
            fast_result,
            decision_record,
            final_path,
        ) = await _execute_fast_with_fallback_routing(
            url, browser_config, gate, fast_result, decision_record
        )
    else:  # RouteType.BROWSER
        crawl_result, decision_record, final_path = await _execute_browser_routing(
            url, browser_config, decision_record
        )

    return crawl_result, fast_result, final_path, decision_record


async def _execute_fast_path_routing(url: str, fast_result, decision_record):
    """Execute fast path routing."""
    _compat.logger.info("Using FAST path (HTTPX)", url=url)
    fast_result = await _compat._execute_fast_path(url)
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
    _compat.logger.info("Using FAST_WITH_FALLBACK path", url=url)
    fast_result = await _compat._execute_fast_path(url)
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
        _compat.logger.info("Fast path succeeded", duration_ms=fast_result.fetch_time_ms)
        crawl_result = None
    else:
        _compat.logger.warning(
            "Fast path failed quality, escalating to browser",
            url=url,
            fallback_reason=quality.fallback_reason,
        )
        crawl_result = await _compat._crawl_browser(url, browser_config)
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

    _compat.logger.info("Using BROWSER path (Playwright)", url=url)
    crawl_result = await _compat._crawl_browser(url, browser_config)
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
    decision_repo = _compat.CrawlDecisionRepository()
    await decision_repo.save(decision_record, trusted_tenant_id=tenant_id)
    metrics = _compat.get_metrics()
    if metrics:
        metrics.increment_crawl_path(path=final_path, domain_class=_domain_class(url))


def _record_stage_metrics(stage_started_at, stage):
    """Record stage duration metrics."""
    metrics = _compat.get_metrics()
    if metrics:
        metrics.observe_job_stage_duration(
            time.monotonic() - stage_started_at,
            stage=stage.value,
            status="completed",
        )


def _extract_unified_crawl_result(fast_result, crawl_result, final_path):
    """Extract unified crawl result from fast or browser path."""
    if fast_result and final_path in ("fast",):
        return (
            fast_result.url,
            fast_result.status_code,
            fast_result.headers,
            fast_result.html or "",
            fast_result.title,
            fast_result.fetch_time_ms,
        )
    elif crawl_result:
        return (
            crawl_result.final_url,
            crawl_result.status_code,
            crawl_result.headers,
            crawl_result.html_content or "",
            crawl_result.title or "",
            crawl_result.duration_ms,
        )
    return "", None, {}, "", "", 0


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
    _compat._update_stage(session, job.id, PipelineStage.CONTENT_CAPTURE, "RUNNING")
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


@celery_app.task(name="layer1_ingestion.shared.tasks.ai_extraction_stage", bind=True, max_retries=5)
def ai_extraction_stage(self, prev_result: dict, tenant_id: str):
    return _run_async(_compat._ai_extraction_stage_async(self, prev_result, tenant_id))


async def _ai_extraction_stage_async(self, prev_result: dict, tenant_id: str):
    """Stage 5: AI/LLM Extraction (conditional based on config).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    _compat.logger.info(
        "Starting AI extraction stage", job_id=str(job_id), tenant_id=str(tenant_uuid)
    )
    with start_celery_span(
        self,
        "l1.pipeline.ai_extraction",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
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
                    _compat.logger.info(
                        "Using skill-specific extraction schema",
                        job_id=str(job_id),
                        skill_name=job.skill_name,
                    )

                if method == ExtractionMethod.DETERMINISTIC.value:
                    _compat.logger.info(
                        "Skipping AI extraction (deterministic mode)", job_id=str(job_id)
                    )
                    return ai_extraction_stageResult.model_validate(
                        {"success": True, "job_id": str(job_id), "skipped": True}
                    ).model_dump()

                _compat._update_stage(session, job_id, PipelineStage.AI_EXTRACTION, "RUNNING")
                job.progress_stage = PipelineStage.AI_EXTRACTION.value
                session.commit()

                raw_content_id = config.get("raw_content_id")
                raw_content = (
                    session.query(RawContent).get(UUID(raw_content_id)) if raw_content_id else None
                )

                if not raw_content:
                    raise ValueError("Raw content not found for AI extraction")

                l2_url = _compat.settings.layer2_api_url
                extraction_model = extraction_config.get(
                    "model", os.getenv("EXTRACTION_MODEL", _compat.settings.openai_model)
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
                    _compat.settings.use_celery_for_l2
                )  # Local flag to avoid race condition
                if use_celery_dispatch:
                    try:
                        # Import Celery for cross-service dispatch
                        from celery import Celery

                        # Create a Celery client pointing to L2's broker
                        l2_celery = Celery(
                            "layer2_extraction",
                            broker=_compat.settings.layer2_celery_broker_url,
                            backend=_compat.settings.layer2_celery_broker_url,
                        )

                        # Dispatch task to L2 Celery worker with extract-and-ingest
                        _compat.logger.info(
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

                        _compat.logger.info(
                            "L2 Celery extract-and-ingest completed",
                            job_id=str(job_id),
                            task_id=result.id,
                        )

                    except Exception as e:
                        _compat.logger.warning(
                            "L2 Celery dispatch failed, falling back to HTTP",
                            job_id=str(job_id),
                            error=repr(e),
                        )
                        # Fall through to HTTP fallback
                        use_celery_dispatch = False  # Disable for this run
                else:
                    _compat.logger.info(
                        "Using HTTP fallback for L2 extract-and-ingest", job_id=str(job_id)
                    )

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
                            _compat.logger.warning(
                                "L2 transient error, returning to queue via Celery retry",
                                job_id=str(job_id),
                                status=e.response.status_code,
                            )
                            raise self.retry(exc=e, countdown=15)
                        raise ValueError(
                            f"L2 extract-and-ingest failed: HTTP {e.response.status_code}: {e.response.text}"
                        )
                    except Exception as e:
                        _compat.logger.warning(
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
                _compat.logger.info(
                    "L3 graph population verified",
                    job_id=str(job_id),
                    source_version_id=str(raw_content_id),
                    entities_in_graph=l3_entity_count,
                )

                _compat._update_stage(session, job_id, PipelineStage.AI_EXTRACTION, "COMPLETED")
                job.resources_llm_tokens_consumed += tokens_consumed
                session.commit()

                _compat.logger.info(
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
            _compat.logger.error(
                "AI extraction failed",
                job_id=str(job_id),
                error_code="AI_EXTRACTION_ERROR",
                error=sanitize_log_error(exc),
            )
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _compat._update_stage(
                    session,
                    job_id,
                    PipelineStage.AI_EXTRACTION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = _compat.get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="ai_extraction", reason="stage_failure")
            raise self.retry(exc=exc, countdown=30)


@celery_app.task(
    name="layer1_ingestion.shared.tasks.post_processing_stage", bind=True, max_retries=2
)
def post_processing_stage(self, prev_result: dict, tenant_id: str):
    """Stage 6: Post-processing (PII redaction, normalization).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    _compat.logger.info(
        "Starting post-processing stage", job_id=str(job_id), tenant_id=str(tenant_uuid)
    )
    with start_celery_span(
        self,
        "l1.pipeline.post_processing",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _compat._update_stage(session, job_id, PipelineStage.POST_PROCESSING, "RUNNING")
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
                skill = _compat.get_skill(job.job_type)
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
                    _compat.logger.info(
                        "Skill output built",
                        job_id=str(job_id),
                        skill_name=skill.skill_name,
                        output_contract=skill.output_contract,
                    )

                _compat._update_stage(session, job_id, PipelineStage.POST_PROCESSING, "COMPLETED")
                session.commit()

                _compat.logger.info("Post-processing completed", job_id=str(job_id))
                return post_processing_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            _compat.logger.error(
                "Post-processing failed",
                job_id=str(job_id),
                error_code="POST_PROCESSING_ERROR",
                error=sanitize_log_error(exc),
            )
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _compat._update_stage(
                    session,
                    job_id,
                    PipelineStage.POST_PROCESSING,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = _compat.get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="post_processing", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)


def _validate_payload_against_schema(
    data: dict,
    schema: dict,
) -> tuple[bool, list[dict], list[str], list[str]]:
    """Validate *data* against a JSON Schema *schema*.

    Returns:
        (schema_valid, errors, required_present, required_missing)

    *errors* is a list of dicts with keys ``path``, ``message``, ``validator``
    so callers can persist them directly into ``ExtractedData.validation_errors``.
    """
    validator = Draft7Validator(schema)
    raw_errors = sorted(validator.iter_errors(data), key=lambda e: list(e.absolute_path))

    errors = [
        {
            "path": ".".join(str(p) for p in err.absolute_path) or "$",
            "message": err.message,
            "validator": err.validator,
        }
        for err in raw_errors
    ]

    # Determine which required fields are present / missing
    required_fields: list[str] = schema.get("required", [])
    required_present = [f for f in required_fields if f in data]
    required_missing = [f for f in required_fields if f not in data]

    return len(errors) == 0, errors, required_present, required_missing


@celery_app.task(name="layer1_ingestion.shared.tasks.validation_stage", bind=True, max_retries=2)
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

    _compat.logger.info("Starting validation stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.validation",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _compat._update_stage(session, job_id, PipelineStage.VALIDATION, "RUNNING")
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
                            _compat.logger.warning(
                                "Extracted data failed schema validation",
                                job_id=str(job_id),
                                tenant_id=str(job.tenant_id),
                                error_count=len(errors),
                                required_missing=required_missing,
                            )
                        else:
                            _compat.logger.info(
                                "Extracted data passed schema validation",
                                job_id=str(job_id),
                                tenant_id=str(job.tenant_id),
                            )
                    else:
                        _compat.logger.info(
                            "No ExtractedData record found; skipping schema validation",
                            job_id=str(job_id),
                        )
                else:
                    _compat.logger.info(
                        "No extraction_schema configured; skipping schema validation",
                        job_id=str(job_id),
                    )

                _compat._update_stage(session, job_id, PipelineStage.VALIDATION, "COMPLETED")
                session.commit()

                _compat.logger.info("Validation completed", job_id=str(job_id))
                return validation_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            _compat.logger.error(
                "Validation failed",
                job_id=str(job_id),
                error_code="VALIDATION_ERROR",
                error=sanitize_log_error(exc),
            )
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _compat._update_stage(
                    session,
                    job_id,
                    PipelineStage.VALIDATION,
                    "FAILED",
                    sanitize_log_error(exc)[:200],
                )
            metrics = _compat.get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="validation", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)


@celery_app.task(name="layer1_ingestion.shared.tasks.storage_stage", bind=True, max_retries=3)
def storage_stage(self, prev_result: dict, tenant_id: str):
    """Stage 8: Storage (save to database, update references).

    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    _compat.logger.info("Starting storage stage", job_id=str(job_id), tenant_id=str(tenant_uuid))
    with start_celery_span(
        self,
        "l1.pipeline.storage",
        attributes={"job_id": str(job_id), "tenant_id": str(tenant_uuid)},
    ):
        try:
            # Set tenant context BEFORE any database queries
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                job = session.query(ScrapingJob).get(job_id)
                if not job:
                    raise ValueError(f"Job {job_id} not found")

                _compat._update_stage(session, job_id, PipelineStage.STORAGE, "RUNNING")
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
                            _compat.logger.info(
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
                            _compat.logger.info(
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
                            _compat.logger.info(
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
                            _compat.logger.info(
                                "AccountIntelligencePacket stored",
                                job_id=str(job_id),
                                packet_id=str(packet.id),
                                account_name=packet.account_name,
                            )

                _compat._update_stage(session, job_id, PipelineStage.STORAGE, "COMPLETED")
                session.commit()

                _compat.logger.info("Storage completed", job_id=str(job_id))
                return storage_stageResult.model_validate(
                    {"success": True, "job_id": str(job_id)}
                ).model_dump()

        except Exception as exc:
            _compat.logger.error(
                "Storage failed",
                job_id=str(job_id),
                error_code="STORAGE_ERROR",
                error=sanitize_log_error(exc),
            )
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                _compat._update_stage(
                    session, job_id, PipelineStage.STORAGE, "FAILED", sanitize_log_error(exc)[:200]
                )
            metrics = _compat.get_metrics()
            if metrics:
                metrics.increment_retry_event(stage="storage", reason="stage_failure")
            raise self.retry(exc=exc, countdown=10)


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
    with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
        job = session.query(ScrapingJob).get(job_id)
        # Capture needed values before any commit, since SET LOCAL app.tenant_id
        # is transaction-scoped and expires objects after commit.
        job_tenant_id = job.tenant_id if job else None
        job_target_id = job.target_id if job else None

        if job:
            job.status = JobStatus.FAILED.value
            job.completed_at = datetime.now(UTC)

        # Update stage
        _compat._update_stage(session, job_id, stage, "FAILED", error)

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

        # Single commit at the end — _compat.get_db_session context manager also commits
        # on successful exit, but an explicit commit here ensures persistence
        # before the context manager's final commit (which is a no-op if already
        # committed, and prevents stale-object issues with RLS).
        session.commit()


@celery_app.task(name="layer1_ingestion.shared.tasks.execute_pipeline_stage")
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
        PipelineStage.NOTIFICATION.value: _compat.notification_stage,
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
