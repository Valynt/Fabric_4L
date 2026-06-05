from __future__ import annotations

"""Execution logging for crawler path decisions and performance metrics.

Provides structured logging for cost attribution, fallback analysis,
and performance monitoring without full cost tracking implementation.
"""


import json
import os
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from urllib.parse import urlparse

import structlog
from value_fabric.shared.models.typed_dict import TypedDictModel

from .httpx_crawler import FastPathResult
from .smart_router import QualityDecision, RoutingDecision


class ExecutionLogger_get_stats_for_jobResult(TypedDictModel):
    avg_time_ms: Any | None = None
    fallback_rate: Any | None = None
    job_id: Any
    path_breakdown: dict[str, Any] | None = None
    total_bytes: Any | None = None
    total_time_ms: Any | None = None
    urls_processed: int

logger = structlog.get_logger()


class ExecutionPath(str, Enum):
    """Execution path taken for a URL."""

    FAST = "fast"  # HTTPX only
    BROWSER = "browser"  # Playwright only
    FALLBACK = "fallback"  # HTTPX â†’ Browser


@dataclass
class ExecutionLogEntry:
    """Single execution log entry for a URL fetch.

    Captures all data needed for cost attribution and performance analysis.
    """

    # Identifiers
    timestamp: str
    job_id: str | None
    url: str
    domain: str

    # Routing decision
    target_mode: str  # fast, browser, fast_fallback
    initial_route: str  # fast, browser
    final_path: str  # fast, browser, fallback
    routing_reason: str

    # Quality gate (for fast path attempts)
    quality_passed: bool | None
    quality_checks: dict[str, bool] | None
    fallback_reason: str | None

    # Performance metrics
    fetch_time_ms: int
    total_time_ms: int  # Including any fallback
    bytes_transferred: int

    # Browser metrics (if applicable)
    browser_sessions_used: int = 0
    browser_steps: int = 0

    # Result metadata
    status_code: int | None = None
    content_hash: str | None = None
    text_length: int = 0
    link_count: int = 0
    spa_detected: bool = False

    # Error tracking
    error_type: str | None = None
    error_message: str | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def to_json(self) -> str:
        """Serialize to JSON string."""
        return json.dumps(self.to_dict(), default=str)


class ExecutionLogger:
    """Logger for crawler execution events.

    Provides structured logging for:
    - Path decisions (FAST vs BROWSER vs FALLBACK)
    - Quality gate outcomes
    - Performance metrics (timing, bytes)
    - Error tracking

    Does NOT implement cost attribution (deferred), but logs all
data needed to calculate it later.

    Example:
        logger = ExecutionLogger()

        # Log successful fast path
        logger.log_fast_path(
            job_id="uuid",
            url="https://example.com",
            result=fast_result,
            routing_decision=routing_decision,
        )

        # Log fallback
        logger.log_fallback(
            job_id="uuid",
            url="https://example.com",
            fast_result=fast_result,
            quality_decision=quality_decision,
        )
    """

    def __init__(self) -> None:
        """Initialize execution logger."""
        self.logger = logger.bind(component="ExecutionLogger")

    def log_fast_path(
        self,
        job_id: str | None,
        url: str,
        result: FastPathResult,
        routing_decision: RoutingDecision,
        target_mode: str,
    ) -> ExecutionLogEntry:
        """Log a successful fast path execution.

        Args:
            job_id: Optional job identifier
            url: URL that was fetched
            result: FastPathResult from HTTPX crawler
            routing_decision: The routing decision that led to fast path
            target_mode: Target-level mode (fast/browser/fast_fallback)

        Returns:
            ExecutionLogEntry that was logged
        """

        entry = ExecutionLogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            job_id=job_id,
            url=url,
            domain=urlparse(url).netloc,
            target_mode=target_mode,
            initial_route=routing_decision.route.value,
            final_path=ExecutionPath.FAST.value,
            routing_reason=routing_decision.reason,
            quality_passed=None,  # Not applicable for direct fast path
            quality_checks=None,
            fallback_reason=None,
            fetch_time_ms=result.fetch_time_ms,
            total_time_ms=result.fetch_time_ms,
            bytes_transferred=len(result.html.encode("utf-8", errors="replace")),
            browser_sessions_used=0,
            browser_steps=0,
            status_code=result.status_code,
            content_hash=result.content_hash,
            text_length=len(result.text_content),
            link_count=len(result.links_found),
            spa_detected=result.is_spa_detected,
        )

        self._write_log(entry, "fast_path_success")
        return entry

    def log_fallback(
        self,
        job_id: str | None,
        url: str,
        fast_result: FastPathResult,
        quality_decision: QualityDecision,
        routing_decision: RoutingDecision,
        target_mode: str,
    ) -> ExecutionLogEntry:
        """Log a fast path â†’ browser fallback execution.

        Args:
            job_id: Optional job identifier
            url: URL that required fallback
            fast_result: The failed FastPathResult
            quality_decision: QualityDecision explaining why fallback occurred
            routing_decision: The routing decision that led to fast path attempt
            target_mode: Target-level mode

        Returns:
            ExecutionLogEntry that was logged
        """

        entry = ExecutionLogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            job_id=job_id,
            url=url,
            domain=urlparse(url).netloc,
            target_mode=target_mode,
            initial_route=routing_decision.route.value,
            final_path=ExecutionPath.FALLBACK.value,
            routing_reason=routing_decision.reason,
            quality_passed=quality_decision.passed,
            quality_checks=quality_decision.checks,
            fallback_reason=quality_decision.fallback_reason,
            fetch_time_ms=fast_result.fetch_time_ms,
            total_time_ms=fast_result.fetch_time_ms,  # Will be updated after browser
            bytes_transferred=len(fast_result.html.encode("utf-8", errors="replace")),
            browser_sessions_used=1,  # Starting browser session
            browser_steps=0,  # Will be updated after browser completes
            status_code=fast_result.status_code,
            content_hash=fast_result.content_hash,
            text_length=len(fast_result.text_content),
            link_count=len(fast_result.links_found),
            spa_detected=fast_result.is_spa_detected,
        )

        self._write_log(entry, "fast_path_fallback")
        return entry

    def log_browser_path(
        self,
        job_id: str | None,
        url: str,
        routing_decision: RoutingDecision,
        target_mode: str,
        browser_duration_ms: int,
        browser_steps: int = 0,
        status_code: int | None = None,
    ) -> ExecutionLogEntry:
        """Log a direct browser path execution.

        Args:
            job_id: Optional job identifier
            url: URL that was fetched
            routing_decision: The routing decision that led to browser
            target_mode: Target-level mode
            browser_duration_ms: Total browser execution time
            browser_steps: Number of browser actions taken
            status_code: HTTP status if available

        Returns:
            ExecutionLogEntry that was logged
        """

        entry = ExecutionLogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            job_id=job_id,
            url=url,
            domain=urlparse(url).netloc,
            target_mode=target_mode,
            initial_route=routing_decision.route.value,
            final_path=ExecutionPath.BROWSER.value,
            routing_reason=routing_decision.reason,
            quality_passed=None,  # Not applicable
            quality_checks=None,
            fallback_reason=None,
            fetch_time_ms=0,  # No fast path
            total_time_ms=browser_duration_ms,
            bytes_transferred=0,  # Unknown without result
            browser_sessions_used=1,
            browser_steps=browser_steps,
            status_code=status_code,
            content_hash=None,
            text_length=0,  # Unknown without result
            link_count=0,
            spa_detected=False,  # Not applicable
        )

        self._write_log(entry, "browser_path")
        return entry

    def log_error(
        self,
        job_id: str | None,
        url: str,
        error_type: str,
        error_message: str,
        routing_decision: RoutingDecision | None = None,
        target_mode: str = "unknown",
    ) -> ExecutionLogEntry:
        """Log an execution error.

        Args:
            job_id: Optional job identifier
            url: URL that failed
            error_type: Type of error (timeout, network_error, etc.)
            error_message: Human-readable error message
            routing_decision: Optional routing decision that led to error
            target_mode: Target-level mode

        Returns:
            ExecutionLogEntry that was logged
        """

        entry = ExecutionLogEntry(
            timestamp=datetime.now(UTC).isoformat(),
            job_id=job_id,
            url=url,
            domain=urlparse(url).netloc,
            target_mode=target_mode,
            initial_route=routing_decision.route.value if routing_decision else "unknown",
            final_path="error",
            routing_reason=routing_decision.reason if routing_decision else "error",
            quality_passed=None,
            quality_checks=None,
            fallback_reason=error_type,
            fetch_time_ms=0,
            total_time_ms=0,
            bytes_transferred=0,
            browser_sessions_used=0,
            browser_steps=0,
            status_code=None,
            content_hash=None,
            text_length=0,
            link_count=0,
            spa_detected=False,
            error_type=error_type,
            error_message=error_message,
        )

        self._write_log(entry, "execution_error")
        return entry

    def update_fallback_entry(
        self,
        entry: ExecutionLogEntry,
        browser_duration_ms: int,
        final_bytes: int,
        final_text_length: int,
        browser_steps: int = 0,
    ) -> ExecutionLogEntry:
        """Update a fallback entry after browser completion.

        Args:
            entry: The original fallback ExecutionLogEntry
            browser_duration_ms: Time spent in browser
            final_bytes: Final bytes transferred
            final_text_length: Final text content length
            browser_steps: Number of browser actions

        Returns:
            Updated ExecutionLogEntry
        """
        entry.total_time_ms = entry.fetch_time_ms + browser_duration_ms
        entry.bytes_transferred = entry.bytes_transferred + final_bytes
        entry.text_length = final_text_length
        entry.browser_steps = browser_steps

        self._write_log(entry, "fallback_complete")
        return entry

    def _write_log(self, entry: ExecutionLogEntry, event_type: str) -> None:
        """Write log entry to structured logger.

        Args:
            entry: ExecutionLogEntry to log
            event_type: Type of event (fast_path_success, fallback, etc.)
        """
        log_data = entry.to_dict()

        # Add event type to log
        log_data["event_type"] = event_type

        # Log at appropriate level
        if entry.error_type:
            self.logger.error(
                f"execution_{event_type}",
                **log_data,
            )
        elif entry.final_path == ExecutionPath.FALLBACK.value:
            self.logger.warning(
                f"execution_{event_type}",
                **log_data,
            )
        else:
            self.logger.info(
                f"execution_{event_type}",
                **log_data,
            )

    def get_stats_for_job(self, job_id: str, entries: list[ExecutionLogEntry]) -> dict[str, Any]:
        """Calculate aggregate statistics for a job.

        Args:
            job_id: Job identifier
            entries: List of execution log entries for the job

        Returns:
            Dictionary with aggregate statistics
        """
        job_entries = [e for e in entries if e.job_id == job_id]

        if not job_entries:
            return ExecutionLogger_get_stats_for_jobResult.model_validate({"job_id": job_id, "urls_processed": 0})

        fast_count = sum(1 for e in job_entries if e.final_path == ExecutionPath.FAST.value)
        browser_count = sum(1 for e in job_entries if e.final_path == ExecutionPath.BROWSER.value)
        fallback_count = sum(1 for e in job_entries if e.final_path == ExecutionPath.FALLBACK.value)

        total_time = sum(e.total_time_ms for e in job_entries)
        total_bytes = sum(e.bytes_transferred for e in job_entries)

        return ExecutionLogger_get_stats_for_jobResult.model_validate({
            "job_id": job_id,
            "urls_processed": len(job_entries),
            "path_breakdown": {
                "fast": fast_count,
                "browser": browser_count,
                "fallback": fallback_count,
            },
            "fallback_rate": fallback_count / len(job_entries) if job_entries else 0,
            "total_time_ms": total_time,
            "total_bytes": total_bytes,
            "avg_time_ms": total_time / len(job_entries) if job_entries else 0,
        })


class NoOpExecutionLogger(ExecutionLogger):
    """No-op logger for testing or when logging is disabled.

    WARNING: This is an intentional null object for testing/dev use only.
    Never bind to this implementation in production.
    """

    def __init__(self) -> None:
        if os.getenv("ENVIRONMENT", "").strip().lower() == "production":
            raise RuntimeError("NoOpExecutionLogger must not be used in production")
        super().__init__()

    def _write_log(self, entry: ExecutionLogEntry, event_type: str) -> None:
        """Do nothing - log entry is intentionally discarded for test scenarios."""
        pass
