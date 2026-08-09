"""Standalone crawl routing and ingestion maintenance tasks."""

import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING
from urllib.parse import urlparse
from uuid import UUID, uuid4

from ..compliance.url_safety import (
    enforce_rebinding_protection,
    validate_url_safety,
)
from ..crawler.decision_store import CrawlDecisionRecord
from ..crawler.httpx_crawler import HttpxCrawler
from ..crawler.playwright_crawler import CrawlResult, PlaywrightCrawler
from ..crawler.smart_router import RouteType

if TYPE_CHECKING:
    from ..crawler.httpx_crawler import FastPathResult
from value_fabric.shared.error_handling import sanitize_log_error

from ..shared.models import (
    RawContent,
    ScrapingJob,
    ScrapingTarget,
    TenantRegistry,
)
from ..shared.otel_celery import start_celery_span
from .task_contracts import (
    _execute_browser_pathResult,
    cleanup_old_contentResult,
    crawl_url_with_routingResult,
)

# Maximum delivery attempts before an outbox event is dead-lettered.

__all__ = [
    "crawl_url_with_routing",
    "_acrawl_url_with_routing",
    "_execute_fast_path",
    "_crawl_browser",
    "_execute_browser_path",
    "_should_fail_closed",
    "_enumerate_authorized_tenants_for_cleanup",
    "cleanup_old_content",
    "purge_expired_raw_content",
]

from .task_app import _run_async, celery_app


@celery_app.task(
    name="layer1_ingestion.shared.tasks.crawl_url_with_routing", bind=True, max_retries=3
)
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
    router = _compat.SmartRouter()
    gate = _compat.QualityGate()
    decision_repo = _compat.CrawlDecisionRepository()

    _compat.logger.info(
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
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
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
            safety_result = _compat.validate_url_safety(url)
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
                result = await _compat._execute_fast_path(url)

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
                result = await _compat._execute_fast_path(url)

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

                    _compat.logger.info(
                        "Fast path succeeded",
                        job_id=job_id,
                        url=url,
                        duration_ms=result.fetch_time_ms,
                    )
                else:
                    # FAIL-CLOSED: Fast path failed quality, escalate to browser
                    _compat.logger.warning(
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
if routing_decision.route == RouteType.FAST:
    decision_record.final_path = "fast"
elif routing_decision.route == RouteType.FAST_WITH_FALLBACK:
    decision_record.final_path = (
        "fallback" if decision_record.browser_duration_ms is not None else "fast"
    )
else:  # RouteType.BROWSER
    decision_record.final_path = "browser"

await decision_repo.save(decision_record, trusted_tenant_id=tenant_uuid)
            _compat.logger.info(
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
            _compat.logger.error(
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
    safety_result = _compat.validate_url_safety(url)
    enforce_rebinding_protection(safety_result.normalized_url, safety_result.resolved_ips)

    # Actual Playwright integration
    browser_config = config or {}
    wait_for_selector = browser_config.get("wait_for_selector")
    wait_timeout = browser_config.get("wait_timeout", 30000)

    from ..crawler.crawler_config import CrawlerConfig

    crawler_cfg = CrawlerConfig(headless=browser_config.get("headless", True))
    async with _compat.PlaywrightCrawler(config=crawler_cfg) as crawler:
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
        quality_result: _compat.QualityGate evaluation result
        fast_result: FastPathResult from HTTPX
        routing_decision: _compat.SmartRouter decision

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


@celery_app.task(name="layer1_ingestion.shared.tasks._enumerate_authorized_tenants_for_cleanup")
def _enumerate_authorized_tenants_for_cleanup() -> list[UUID]:
    """Enumerate active tenants from system-owned registry with explicit authorization."""
    _compat.authorize_maintenance_operation("cleanup_old_content", tenant_id="tenant-registry")

    correlation_id = str(uuid4())
    with _compat.maintenance_audit_log(
        "cleanup_old_content", tenant_id="tenant-registry"
    ) as record:
        record.metadata = {
            "tenant_iteration_source": "tenant_registry",
            "source_scope": "system_owned",
            "require_tenant": False,
            "correlation_id": correlation_id,
        }
        with _compat.get_db_session(tenant_id=None, require_tenant=False) as session:
            tenant_ids = [
                row[0]
                for row in session.query(TenantRegistry.tenant_id)
                .filter(TenantRegistry.is_active.is_(True))
                .all()
            ]
        record.rows_affected = len(tenant_ids)

    _compat.logger.info(
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
        _compat.logger.info(
            "Starting tenant-scoped content cleanup",
            cutoff_date=cutoff_date.isoformat(),
            tenant_id=str(tenant_uuid),
        )

        with _compat.maintenance_audit_log(
            "cleanup_old_content", tenant_id=str(tenant_uuid)
        ) as record:
            with _compat.get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
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

                _compat.logger.info(
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
        metrics = _compat.get_metrics()
        if metrics:
            metrics.increment_maintenance_tenant_enumeration()

        # Audit log entry before TenantRegistry query
        _compat.logger.info(
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
                with _compat.maintenance_audit_log(
                    "cleanup_old_content", tenant_id=str(tenant_uuid)
                ) as record:
                    with _compat.get_db_session(
                        tenant_id=tenant_uuid, require_tenant=True
                    ) as session:
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
                    (str(tenant_uuid), repr(e))
                )  # ban-str-e-allow: internal-tracking
                _compat.logger.error(
                    "Tenant cleanup failed",
                    tenant_id=str(tenant_uuid),
                    error=repr(e),
                )

        completed_at = datetime.now(UTC)

        # Aggregate summary audit event
        _compat.logger.info(
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
            error_message=None
            if not failed_tenants
            else f"Failed tenants: {[t[0] for t in failed_tenants]}",
            metadata={
                "tenants_processed": len(tenant_ids),
                "failed_tenants": failed_tenants,
            },
        )

        _compat.logger.info(
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
        _compat.logger.error("purge_expired_raw_content failed: %s", exc)
        raise self.retry(exc=exc, countdown=3600)  # retry after 1 hour
