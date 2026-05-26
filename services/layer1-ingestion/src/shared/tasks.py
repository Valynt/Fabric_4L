"""Celery task queue configuration and tasks.

Spec-compliant pipeline stage tasks with multi-tenancy support.
Manages ScrapingJob lifecycle through 11 PipelineStages.
"""

import asyncio
import hashlib
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from urllib.parse import urlparse
from uuid import UUID, uuid4

import httpx
import structlog
from celery import Celery, chain
from jsonschema import Draft7Validator

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
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.error_handling import sanitize_log_error

from ..shared.config import settings
from ..metrics.prometheus_metrics import get_metrics
from ..shared.database import get_db_session
from sqlalchemy import text
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
from ..skills import get_extraction_schema, get_skill

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


class _execute_browser_pathResult(TypedDictModel):
    blocked_resources: Any
    config_used: Any
    content_length: Any
    duration_ms: Any
    error: Any
    final_url: Any
    scroll_triggered: Any
    status_code: bool
    text_length: Any
    title: Any

class process_scraping_jobResult(TypedDictModel):
    job_id: Any
    success: bool
    task_id: Any

class crawl_url_with_routingResult(TypedDictModel):
    decision_id: Any
    duration_ms: Any
    final_path: Any
    job_id: Any
    success: bool
    url: Any

class cleanup_old_contentResult(TypedDictModel):
    cutoff_date: Any
    deleted_count: Any

class compliance_check_stageResult(TypedDictModel):
    error: str | None = None
    job_id: Any
    success: bool

class browser_crawl_stageResult(TypedDictModel):
    job_id: Any
    raw_content_id: Any
    success: bool

class ai_extraction_stageResult(TypedDictModel):
    entities_extracted: Any | None = None
    job_id: Any
    skipped: bool
    success: bool
    tokens_consumed: Any | None = None

class post_processing_stageResult(TypedDictModel):
    job_id: Any
    success: bool

class validation_stageResult(TypedDictModel):
    job_id: Any
    success: bool

class storage_stageResult(TypedDictModel):
    job_id: Any
    success: bool

class notification_stageResult(TypedDictModel):
    error: Any
    job_id: Any
    success: bool

logger = structlog.get_logger()

# Initialize Celery app
celery_app = Celery(
    "layer1_ingestion",
    broker=settings.redis_url,
    backend=settings.redis_url,
    include=["src.shared.tasks"],
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
)


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

        result = pipeline_chain.apply_async()

        return process_scraping_jobResult.model_validate({"success": True, "job_id": str(job_id), "task_id": result.id}).model_dump()

    except Exception as exc:
        logger.error("Pipeline orchestration failed", job_id=str(job_id), error_code="PIPELINE_ORCHESTRATION_ERROR", error=sanitize_log_error(exc))
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
    """Stage 1: Compliance Check (robots.txt, rate limits, domain policies).
    
    Args:
        job_id: The job UUID
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    tenant_uuid = UUID(tenant_id)
    stage_started_at = time.monotonic()

    logger.info("Starting compliance check stage", job_id=str(job_id), tenant_id=str(tenant_uuid))

    try:
        # Set tenant context BEFORE any database queries
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            job = session.query(ScrapingJob).get(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")
            queue_latency_seconds = max(0.0, (datetime.now(UTC) - job.created_at).total_seconds())
            metrics = get_metrics()
            if metrics:
                metrics.observe_queue_latency(
                    queue_latency_seconds,
                    stage=PipelineStage.COMPLIANCE_CHECK.value,
                    status=job.status,
                )

            # Idempotent: skip if already completed (handles retry after crawl delay)
            existing_stage = (
                session.query(JobStageDetail)
                .filter(
                    JobStageDetail.job_id == job_id,
                    JobStageDetail.stage == PipelineStage.COMPLIANCE_CHECK.value,
                )
                .first()
            )
            if existing_stage and existing_stage.status == "COMPLETED":
                logger.info("Compliance check already completed (idempotent retry)", job_id=str(job_id))
                return compliance_check_stageResult.model_validate({"success": True, "job_id": str(job_id)}).model_dump()

            # Update stage status
            _update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "RUNNING")
            job.status = JobStatus.VALIDATING.value
            job.progress_stage = PipelineStage.COMPLIANCE_CHECK.value
            session.commit()

            # Get target configuration
            config = job.configuration
            url = config.get("url", "")
            target = session.query(ScrapingTarget).filter(ScrapingTarget.id == job.target_id).first()
            compliance_allowlist = ((target.compliance or {}) if target else {}).get("domain_allowlist")
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
                config["url"] = safety_result.normalized_url
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
                raise ValueError("URL blocked by compliance policy") from exc

            compliance_config = config.get("compliance", {})

            # Check robots.txt
            if compliance_config.get("respect_robots_txt", True):
                checker = RobotsChecker(
                    tenant_id=str(job.tenant_id),
                    strict_mode=compliance_config.get("strict_robots_compliance", False),
                )
                domain = url.split("/")[2] if "/" in url else url

                allowed, reason, rules = asyncio.run(checker.check_url(domain, url))
                crawl_delay = rules.get("crawl_delay") if rules else None

                # Log compliance check
                log = ComplianceLog(
                    tenant_id=job.tenant_id,
                    job_id=job_id,
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
                    _fail_job(job_id, "URL blocked by robots.txt", PipelineStage.COMPLIANCE_CHECK)
                    return compliance_check_stageResult.model_validate({"success": False, "error": "robots.txt blocked", "job_id": str(job_id)}).model_dump()

                # OPTIMIZATION: Apply crawl delay via Celery retry instead of blocking sleep.
                # This frees the worker to process other tasks during the delay.
                if crawl_delay:
                    _update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "RUNNING")
                    session.commit()
                    logger.info(
                        "Applying crawl delay via Celery retry",
                        job_id=str(job_id),
                        crawl_delay_seconds=crawl_delay,
                    )
                    raise self.retry(countdown=int(crawl_delay))

            # Complete stage
            _update_stage(session, job_id, PipelineStage.COMPLIANCE_CHECK, "COMPLETED")
            session.commit()

            logger.info("Compliance check completed", job_id=str(job_id))
            metrics = get_metrics()
            if metrics:
                metrics.observe_job_stage_duration(
                    time.monotonic() - stage_started_at,
                    stage=PipelineStage.COMPLIANCE_CHECK.value,
                    status="completed",
                )
            return compliance_check_stageResult.model_validate({"success": True, "job_id": str(job_id)}).model_dump()

    except Exception as exc:
        # Propagate Celery retry exceptions directly; don't wrap them
        if "Retry" in type(exc).__name__:
            raise
        logger.error("Compliance check failed", job_id=str(job_id), error_code="COMPLIANCE_CHECK_ERROR", error=sanitize_log_error(exc))
        try:
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as error_session:
                _update_stage(
                    error_session, job_id, PipelineStage.COMPLIANCE_CHECK, "FAILED", sanitize_log_error(exc)[:200]
                )
        except Exception as update_exc:
            logger.error("Failed to update stage status", job_id=str(job_id), error_code="COMPLIANCE_CHECK_ERROR", error=sanitize_log_error(update_exc))
        metrics = get_metrics()
        if metrics:
            metrics.increment_retry_event(stage="compliance_check", reason="stage_failure")
            metrics.observe_job_stage_duration(
                time.monotonic() - stage_started_at,
                stage=PipelineStage.COMPLIANCE_CHECK.value,
                status="failed",
            )
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(bind=True, max_retries=3)
def browser_crawl_stage(self, prev_result: dict, tenant_id: str):
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

    try:
        # Set tenant context BEFORE any database queries
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            job = session.query(ScrapingJob).get(job_id)
            if not job:
                raise ValueError(f"Job {job_id} not found")

            config = job.configuration
            url = config.get("url", "")
            browser_config = config.get("browser_config", {})
            target_config = {}
            if job.target_id:
                target = session.query(ScrapingTarget).get(job.target_id)
                if target:
                    target_config = target.extraction_config or {}

            tenant_id = str(job.tenant_id) if job.tenant_id else None
            effective_mode = target_config.get("crawl_path", "browser")

            router = SmartRouter()
            gate = QualityGate()
            decision_repo = CrawlDecisionRepository()

            # Stage 2: Browser Launch
            _update_stage(session, job_id, PipelineStage.BROWSER_LAUNCH, "RUNNING")
            job.status = JobStatus.BROWSER_ACQUIRING.value
            job.progress_stage = PipelineStage.BROWSER_LAUNCH.value
            job.resources_browser_sessions_used += 1
            session.commit()

            # Routing decision
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

            # Determine crawl path
            crawl_result = None
            fast_result = None
            final_path = "unknown"

            if routing_decision.route == RouteType.FAST:
                logger.info("Using FAST path (HTTPX)", job_id=str(job_id), url=url)
                fast_result = asyncio.run(_execute_fast_path(url))
                final_path = "fast"
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

            elif routing_decision.route == RouteType.FAST_WITH_FALLBACK:
                logger.info("Using FAST_WITH_FALLBACK path", job_id=str(job_id), url=url)
                fast_result = asyncio.run(_execute_fast_path(url))
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
                    logger.info("Fast path succeeded", job_id=str(job_id), duration_ms=fast_result.fetch_time_ms)
                else:
                    logger.warning(
                        "Fast path failed quality, escalating to browser",
                        job_id=str(job_id),
                        url=url,
                        fallback_reason=quality.fallback_reason,
                    )
                    crawl_result = asyncio.run(_crawl_browser(url, browser_config))
                    final_path = "fallback"
                    decision_record.final_path = "fallback"
                    decision_record.status_code = crawl_result.status_code
                    decision_record.browser_duration_ms = crawl_result.duration_ms
                    decision_record.fetch_time_ms = fast_result.fetch_time_ms + crawl_result.duration_ms
                    decision_record.bytes_transferred = len((fast_result.html or "").encode("utf-8")) + len((crawl_result.html_content or "").encode("utf-8"))
                    decision_record.text_length = len(crawl_result.html_content or "") // 10

            else:  # RouteType.BROWSER
                logger.info("Using BROWSER path (Playwright)", job_id=str(job_id), url=url)
                crawl_result = asyncio.run(_crawl_browser(url, browser_config))
                final_path = "browser"
                decision_record.final_path = "browser"
                decision_record.status_code = crawl_result.status_code
                decision_record.browser_duration_ms = crawl_result.duration_ms
                decision_record.fetch_time_ms = crawl_result.duration_ms
                decision_record.bytes_transferred = len((crawl_result.html_content or "").encode("utf-8"))
                decision_record.text_length = len(crawl_result.html_content or "") // 10

            # Persist routing decision and emit path metric
            asyncio.run(decision_repo.save(decision_record))
            metrics = get_metrics()
            if metrics:
                metrics.increment_crawl_path(path=final_path, domain_class=_domain_class(url))
                metrics.observe_job_stage_duration(
                    time.monotonic() - stage_started_at,
                    stage="crawl_path_execution",
                    status="completed",
                )

            _update_stage(session, job_id, PipelineStage.BROWSER_LAUNCH, "COMPLETED")

            # Stage 3: Navigation
            _update_stage(session, job_id, PipelineStage.NAVIGATION, "RUNNING")
            job.status = JobStatus.NAVIGATING.value
            job.progress_stage = PipelineStage.NAVIGATION.value
            session.commit()

            if crawl_result and crawl_result.error:
                raise Exception(crawl_result.error)

            # Extract unified result
            final_url = ""
            status_code = None
            headers = {}
            html_content = ""
            title = ""
            duration_ms = 0
            if fast_result and final_path in ("fast",):
                final_url = fast_result.url
                status_code = fast_result.status_code
                headers = fast_result.headers
                html_content = fast_result.html or ""
                title = fast_result.title
                duration_ms = fast_result.fetch_time_ms
            elif crawl_result:
                final_url = crawl_result.final_url
                status_code = crawl_result.status_code
                headers = crawl_result.headers
                html_content = crawl_result.html_content or ""
                title = crawl_result.title or ""
                duration_ms = crawl_result.duration_ms

            job.configuration["navigation_result"] = {
                "final_url": final_url,
                "status_code": status_code,
                "headers": headers,
            }
            _update_stage(session, job_id, PipelineStage.NAVIGATION, "COMPLETED")

            # Stage 4: Content Capture
            _update_stage(session, job_id, PipelineStage.CONTENT_CAPTURE, "RUNNING")
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
                job_id=job_id,
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

            _update_stage(session, job_id, PipelineStage.CONTENT_CAPTURE, "COMPLETED")
            session.commit()

            logger.info(
                "Smart crawl completed",
                job_id=str(job_id),
                raw_content_id=str(raw_content.id),
                final_path=final_path,
                final_url=final_url,
            )
            return browser_crawl_stageResult.model_validate({
                "success": True,
                "job_id": str(job_id),
                "raw_content_id": str(raw_content.id),
            }).model_dump()

    except Exception as exc:
        logger.error("Smart crawl failed", job_id=str(job_id), error_code="SMART_CRAWL_ERROR", error=sanitize_log_error(exc))
        for stage in (PipelineStage.BROWSER_LAUNCH, PipelineStage.NAVIGATION, PipelineStage.CONTENT_CAPTURE):
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


@celery_app.task(bind=True, max_retries=5)
def ai_extraction_stage(self, prev_result: dict, tenant_id: str):
    """Stage 5: AI/LLM Extraction (conditional based on config).
    
    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting AI extraction stage", job_id=str(job_id), tenant_id=str(tenant_uuid))

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
                return ai_extraction_stageResult.model_validate({"success": True, "job_id": str(job_id), "skipped": True}).model_dump()

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
            extraction_payload = {
                "content": raw_content.meta_title or "",
                "content_type": "text",
                "extraction_method": method.lower(),
                "source_id": str(raw_content_id),
                "job_id": str(job_id),
                "tenant_id": str(job.tenant_id),
                "options": {
                    "model": extraction_config.get("model", settings.openai_model),
                    "temperature": extraction_config.get("temperature", 0.0),
                    "max_tokens": extraction_config.get("max_tokens", 4000),
                },
            }
            # Pass skill-specific schema downstream if configured
            schema = extraction_config.get("extraction_schema")
            if schema:
                extraction_payload["extraction_schema"] = schema

            # OPTIMIZATION: Async L2 call with short timeout + Celery retry.
            # Previously: sync httpx.post with 120s timeout blocked the worker.
            # Now: 30s async timeout; transient failures trigger Celery retry
            # which returns the task to the queue, freeing the worker.
            async def _call_l2():
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.post(
                        f"{l2_url}/v1/extract",
                        json=extraction_payload,
                        headers={
                            "Content-Type": "application/json",
                            "X-Tenant-ID": str(job.tenant_id),
                        },
                    )
                    response.raise_for_status()
                    return response.json()

            try:
                extraction_result = asyncio.run(_call_l2())
                tokens_consumed = extraction_result.get("tokens_consumed", 0)
            except httpx.HTTPStatusError as e:
                if e.response.status_code in (429, 503, 504):
                    logger.warning(
                        "L2 transient error, returning to queue via Celery retry",
                        job_id=str(job_id),
                        status=e.response.status_code,
                    )
                    raise self.retry(exc=e, countdown=15)
                raise ValueError(f"L2 extraction failed: HTTP {e.response.status_code}: {e.response.text}")
            except Exception as e:
                logger.warning("L2 extraction failed, retrying via Celery", job_id=str(job_id), error_code="L2_EXTRACTION_ERROR")
                raise self.retry(exc=e, countdown=30)

            job.configuration["extraction_result"] = extraction_result

            _update_stage(session, job_id, PipelineStage.AI_EXTRACTION, "COMPLETED")
            job.resources_llm_tokens_consumed += tokens_consumed
            session.commit()

            logger.info(
                "AI extraction completed",
                job_id=str(job_id),
                tokens_consumed=tokens_consumed,
                entities_extracted=len(extraction_result.get("entities", [])),
            )
            return ai_extraction_stageResult.model_validate({
                "success": True,
                "job_id": str(job_id),
                "tokens_consumed": tokens_consumed,
                "entities_extracted": len(extraction_result.get("entities", [])),
            }).model_dump()

    except Exception as exc:
        if "Retry" in type(exc).__name__:
            raise
        logger.error("AI extraction failed", job_id=str(job_id), error_code="AI_EXTRACTION_ERROR", error=sanitize_log_error(exc))
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            _update_stage(session, job_id, PipelineStage.AI_EXTRACTION, "FAILED", sanitize_log_error(exc)[:200])
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
                    session.query(RawContent)
                    .filter(RawContent.job_id == job_id)
                    .all()
                )
                extracted_data = (
                    session.query(ExtractedData)
                    .filter(ExtractedData.job_id == job_id)
                    .all()
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
            return post_processing_stageResult.model_validate({"success": True, "job_id": str(job_id)}).model_dump()

    except Exception as exc:
        logger.error("Post-processing failed", job_id=str(job_id), error_code="POST_PROCESSING_ERROR", error=sanitize_log_error(exc))
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            _update_stage(session, job_id, PipelineStage.POST_PROCESSING, "FAILED", sanitize_log_error(exc)[:200])
        metrics = get_metrics()
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
            return validation_stageResult.model_validate({"success": True, "job_id": str(job_id)}).model_dump()

    except Exception as exc:
        logger.error("Validation failed", job_id=str(job_id), error_code="VALIDATION_ERROR", error=sanitize_log_error(exc))
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            _update_stage(session, job_id, PipelineStage.VALIDATION, "FAILED", sanitize_log_error(exc)[:200])
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
                        .filter(SourceCorpus.job_id == job_id, SourceCorpus.tenant_id == job.tenant_id)
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
                            corpus_type=skill_output.get("corpus_type", "licensing_company_ontology_seed"),
                            source_groups=skill_output.get("source_groups", []),
                            candidate_concepts=skill_output.get("candidate_concepts", []),
                            provenance=skill_output.get("provenance", []),
                            extraction_status=skill_output.get("extraction_status", "ready_for_extraction"),
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
                        .filter(AccountIntelligencePacket.job_id == job_id, AccountIntelligencePacket.tenant_id == job.tenant_id)
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
                            next_recommended_events=skill_output.get("next_recommended_events", []),
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
            return storage_stageResult.model_validate({"success": True, "job_id": str(job_id)}).model_dump()

    except Exception as exc:
        logger.error("Storage failed", job_id=str(job_id), error_code="STORAGE_ERROR", error=sanitize_log_error(exc))
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            _update_stage(session, job_id, PipelineStage.STORAGE, "FAILED", sanitize_log_error(exc)[:200])
        metrics = get_metrics()
        if metrics:
            metrics.increment_retry_event(stage="storage", reason="stage_failure")
        raise self.retry(exc=exc, countdown=10)


@celery_app.task
def notification_stage(prev_result: dict, tenant_id: str):
    """Stage 9: Notification (webhooks, callbacks).
    
    Args:
        prev_result: Previous stage result containing job_id
        tenant_id: Trusted tenant_id from server-controlled dispatch envelope
    """
    job_id = UUID(prev_result["job_id"])
    tenant_uuid = UUID(tenant_id)

    logger.info("Starting notification stage", job_id=str(job_id), tenant_id=str(tenant_uuid))

    try:
        # Set tenant context BEFORE any database queries
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            job = session.query(ScrapingJob).get(job_id)
            if not job:
                return

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
                    target.average_execution_time_ms = int(total_duration / target.success_count)
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
            return notification_stageResult.model_validate({"success": True, "job_id": str(job_id), "error": None}).model_dump()

    except Exception as exc:
        logger.error("Notification stage failed", job_id=str(job_id), error_code="NOTIFICATION_ERROR", error=sanitize_log_error(exc))
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            _update_stage(session, job_id, PipelineStage.NOTIFICATION, "FAILED", sanitize_log_error(exc)[:200])
        return notification_stageResult.model_validate({"success": False, "job_id": str(job_id), "error": "Notification stage failed"}).model_dump()


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

    try:
        # Set tenant context BEFORE any database queries
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            event = (
                session.query(EventOutbox)
                .filter(EventOutbox.id == event_uuid)
                .first()
            )
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

        # Record the failure on the outbox row.
        try:
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                event = (
                    session.query(EventOutbox)
                    .filter(EventOutbox.id == event_uuid)
                    .first()
                )
                if event:
                    event.attempts = (event.attempts or 0) + 1
                    event.last_error = sanitize_log_error(exc)[:200]

                    if event.attempts >= MAX_DISPATCH_ATTEMPTS:
                        event.status = OutboxStatus.DEAD_LETTER.value
                        event.dead_lettered_at = datetime.now(UTC)
                        logger.error(
                            "EventOutbox dead-lettered after max attempts",
                            event_id=event_id,
                            event_type=event.event_type,
                            attempts=event.attempts,
                        )
                        metrics = get_metrics()
                        if metrics:
                            metrics.increment_outbox_dead_lettered()
                        session.commit()
                        return  # Do not retry dead-lettered events.
                    else:
                        event.status = OutboxStatus.FAILED.value
                        session.commit()
        except Exception as inner_exc:
            logger.error(
                "Failed to record outbox dispatch error",
                event_id=event_id,
                error_code="NOTIFICATION_ERROR",
                error=sanitize_log_error(inner_exc),
            )

        # Retry with exponential backoff.
        metrics = get_metrics()
        if metrics:
            metrics.increment_retry_event(stage="notification", reason="dispatch_failure")
        raise self.retry(exc=exc, countdown=30 * (2 ** self.request.retries))


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
        if job:
            job.status = JobStatus.FAILED.value
            job.completed_at = datetime.now(UTC)
            session.commit()

        # Update stage
        _update_stage(session, job_id, stage, "FAILED", error)

        # Create error record
        error_record = JobError(
            job_id=job_id,
            tenant_id=job.tenant_id if job else None,
            stage=stage.value,
            error_code="PIPELINE_ERROR",
            error_message=error,
            retryable=False,
        )
        session.add(error_record)
        session.commit()

        # Update target error stats
        if job:
            target = session.query(ScrapingTarget).get(job.target_id)
            if target:
                try:
                    target.error_count += 1
                except TypeError:
                    target.error_count = 1
                target.last_error_at = datetime.now(UTC)
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


@celery_app.task(bind=True, max_retries=3)
def crawl_url_with_routing(self, job_id: str, url: str, tenant_id: str, target_mode: str = "browser"):
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
            result = asyncio.run(_execute_fast_path(url))

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
            result = asyncio.run(_execute_fast_path(url))

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

                browser_result = asyncio.run(_execute_browser_path(url, routing_decision.stagehand_config))

                decision_record.final_path = "fallback"
                decision_record.status_code = browser_result.get("status_code")
                decision_record.browser_duration_ms = browser_result.get("duration_ms", 0)
                decision_record.fetch_time_ms = result.fetch_time_ms + browser_result.get(
                    "duration_ms", 0
                )
                decision_record.bytes_transferred = len(result.html.encode("utf-8")) + browser_result.get(
                    "content_length", 0
                )
                decision_record.text_length = browser_result.get("text_length", 0)

        else:  # RouteType.BROWSER
            # Direct browser path
            browser_result = asyncio.run(_execute_browser_path(url, routing_decision.stagehand_config))

            decision_record.final_path = "browser"
            decision_record.status_code = browser_result.get("status_code")
            decision_record.browser_duration_ms = browser_result.get("duration_ms", 0)
            decision_record.fetch_time_ms = browser_result.get("duration_ms", 0)
            decision_record.bytes_transferred = browser_result.get("content_length", 0)
            decision_record.text_length = browser_result.get("text_length", 0)

        # 3. PERSIST CANONICAL DECISION
        asyncio.run(decision_repo.save(decision_record))

        logger.info(
            "Crawl completed with routing",
            job_id=job_id,
            url=url,
            final_path=decision_record.final_path,
            duration_ms=decision_record.fetch_time_ms,
        )

        return crawl_url_with_routingResult.model_validate({
            "success": True,
            "job_id": job_id,
            "url": url,
            "final_path": decision_record.final_path,
            "duration_ms": decision_record.fetch_time_ms,
            "decision_id": decision_record.decision_id,
        }).model_dump()


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
            decision_record.error_message = sanitize_log_error(exc)[:500]  # Truncate long messages
            try:
                asyncio.run(decision_repo.save(decision_record))
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

    # Actual Playwright integration
    browser_config = config or {}
    wait_for_selector = browser_config.get("wait_for_selector")
    wait_timeout = browser_config.get("wait_timeout", 30000)

    from ..crawler.crawler_config import CrawlerConfig
    crawler_cfg = CrawlerConfig(headless=browser_config.get("headless", True))
    async with PlaywrightCrawler(config=crawler_cfg) as crawler:
        result = await crawler.crawl_url(
            url=url,
            wait_for_selector=wait_for_selector,
            wait_for_timeout=wait_timeout,
            scroll_page=True,
        )

    duration_ms = int((time.monotonic() - start_time) * 1000)

    return _execute_browser_pathResult.model_validate({
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
    }).model_dump()


def _should_fail_closed(
    quality_result, fast_result, routing_decision
) -> tuple[bool, str | None]:
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
    from .maintenance import maintenance_audit_log
    
    cutoff_date = datetime.now(UTC) - timedelta(days=days)
    
    # Validate tenant context if provided
    if tenant_id:
        try:
            tenant_uuid = UUID(tenant_id)
        except (ValueError, TypeError) as e:
            raise InvalidTenantContextError(
                f"Invalid tenant_id format: {tenant_id}",
                tenant_id=tenant_id
            )
        
        # Tenant-scoped cleanup under RLS
        logger.info("Starting tenant-scoped content cleanup", 
                   cutoff_date=cutoff_date.isoformat(), 
                   tenant_id=str(tenant_uuid))
        
        with maintenance_audit_log("cleanup_old_content", tenant_id=str(tenant_uuid)) as record:
            with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
                deleted_count = (
                    session.query(RawContent)
                    .filter(RawContent.created_at < cutoff_date, RawContent.processing_status != "DELETED")
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

                return cleanup_old_contentResult.model_validate({"deleted_count": deleted_count, "cutoff_date": cutoff_date.isoformat()}).model_dump()
    
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
        
        tenant_ids = []
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            tenant_ids = [
                row[0] for row in
                session.query(TenantRegistry.tenant_id)
                .filter(TenantRegistry.is_active == True)
                .all()
            ]

        total_deleted = 0
        failed_tenants = []
        started_at = datetime.now(UTC)

        for tenant_uuid in tenant_ids:
            try:
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
                        total_deleted += deleted_count
            except Exception as e:
                failed_tenants.append((str(tenant_uuid), str(e)))
                logger.error(
                    "Tenant cleanup failed",
                    tenant_id=str(tenant_uuid),
                    error=str(e),
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
            error_message=None if not failed_tenants else f"Failed tenants: {[t[0] for t in failed_tenants]}",
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

        return cleanup_old_contentResult.model_validate({
            "deleted_count": total_deleted,
            "cutoff_date": cutoff_date.isoformat(),
        }).model_dump()
