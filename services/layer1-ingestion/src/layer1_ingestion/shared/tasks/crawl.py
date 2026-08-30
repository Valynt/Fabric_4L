"""Browser/HTTPX crawl routing tasks.

Submodule of ``layer1_ingestion.shared.tasks`` (split from the former megafile).
"""

import hashlib
import time
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID, uuid4

from value_fabric.shared.error_handling import sanitize_log_error

from ...compliance.url_safety import (
    enforce_rebinding_protection,
    validate_url_safety,
)
from ...crawler.decision_store import CrawlDecisionRecord, CrawlDecisionRepository
from ...crawler.httpx_crawler import HttpxCrawler
from ...crawler.playwright_crawler import CrawlResult, PlaywrightCrawler
from ...crawler.quality_gate import QualityGate
from ...crawler.smart_router import RouteType, SmartRouter
from ...metrics.prometheus_metrics import get_metrics
from ..database import get_db_session
from ..models import (
    JobStatus,
    PipelineStage,
    RawContent,
    ScrapingJob,
    ScrapingTarget,
)
from ..otel_celery import start_celery_span
from ..task_contracts import (
    _execute_browser_pathResult,
    browser_crawl_stageResult,
    crawl_url_with_routingResult,
)
from ..tasks import (
    _update_stage,
)
from .tasks_bootstrap import celery_app, logger
from ..tasks_helpers import (
    _domain_class,
    _extract_unified_crawl_result,
    _get_target_config,
    _run_async,
)

if TYPE_CHECKING:
    from ...crawler.httpx_crawler import FastPathResult


@celery_app.task(name="layer1_ingestion.shared.tasks.browser_crawl_stage", bind=True, max_retries=3)
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


@celery_app.task(name="layer1_ingestion.shared.tasks.crawl_url_with_routing", bind=True, max_retries=3)
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
    from ...crawler.crawler_config import CrawlerConfig

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

    from ...crawler.crawler_config import CrawlerConfig

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
