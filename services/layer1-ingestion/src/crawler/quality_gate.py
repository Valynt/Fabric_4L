from __future__ import annotations

"""Quality gate for validating fast path extraction results.

Evaluates HTTPX fetch results to determine if content meets quality
thresholds or requires fallback to browser path.
"""


from dataclasses import dataclass, field
from typing import Any

import structlog

from .httpx_crawler import FastPathResult
from .smart_router import QualityDecision

logger = structlog.get_logger()


@dataclass
class QualityThresholds:
    """Configurable quality thresholds for fast path validation."""

    min_text_length: int = 500
    """Minimum characters of extracted text."""

    min_content_ratio: float = 0.02
    """Minimum ratio of text chars to HTML chars."""

    max_fetch_time_ms: int = 5000
    """Maximum acceptable fetch time (indicates slow/dynamic page)."""

    require_title: bool = True
    """Require page title extraction."""

    min_link_count: int = 0
    """Minimum links found (for crawling scenarios)."""

    blocked_content_types: list[str] = field(default_factory=lambda: [
        "application/pdf",
        "application/zip",
        "application/octet-stream",
    ])
    """Content types that indicate non-HTML response."""


class QualityGate:
    """Validates fast path results against quality thresholds.

    Evaluates extraction quality and decides whether to accept
    the HTTPX result or escalate to browser fallback.

    Example:
        gate = QualityGate()
        result = await httpx_crawler.fetch(url)
        decision = gate.evaluate(result)

        if decision.passed:
            print("Fast path succeeded")
        else:
            print(f"Fallback needed: {decision.fallback_reason}")
    """

    def __init__(self, thresholds: QualityThresholds | None = None) -> None:
        """Initialize quality gate with thresholds.

        Args:
            thresholds: Quality thresholds. Uses defaults if not provided.
        """
        self.thresholds = thresholds or QualityThresholds()
        self.logger = logger.bind(component="QualityGate")

    def evaluate(self, result: FastPathResult) -> QualityDecision:
        """Evaluate a fast path result against quality thresholds.

        Args:
            result: The FastPathResult from HTTPX crawler

        Returns:
            QualityDecision with pass/fail status and specific check results
        """
        checks = {
            "success_status": self._check_status_code(result),
            "text_length": self._check_text_length(result),
            "content_ratio": self._check_content_ratio(result),
            "no_spa": self._check_no_spa(result),
            "fetch_time": self._check_fetch_time(result),
            "valid_content_type": self._check_content_type(result),
        }

        # Title check is optional based on config
        if self.thresholds.require_title:
            checks["has_title"] = self._check_title(result)

        # Link count check if configured
        if self.thresholds.min_link_count > 0:
            checks["link_count"] = self._check_link_count(result)

        passed = all(checks.values())

        # Find first failing check for reporting
        fallback_reason = None
        if not passed:
            fallback_reason = next(
                (k for k, v in checks.items() if not v),
                "unknown"
            )
            self.logger.debug(
                "Quality check failed",
                url=result.url,
                reason=fallback_reason,
                checks=checks,
            )

        return QualityDecision(
            passed=passed,
            checks=checks,
            fallback_reason=fallback_reason,
        )

    def evaluate_with_details(
        self,
        result: FastPathResult,
    ) -> tuple[QualityDecision, dict[str, Any]]:
        """Evaluate with detailed metrics for logging.

        Args:
            result: The FastPathResult from HTTPX crawler

        Returns:
            Tuple of (QualityDecision, detailed_metrics_dict)
        """
        decision = self.evaluate(result)

        metrics = {
            "url": result.url,
            "passed": decision.passed,
            "fallback_reason": decision.fallback_reason,
            "text_length": len(result.text_content),
            "text_threshold": self.thresholds.min_text_length,
            "content_ratio": len(result.text_content) / max(result.original_html_length or len(result.html), 1),
            "ratio_threshold": self.thresholds.min_content_ratio,
            "fetch_time_ms": result.fetch_time_ms,
            "time_threshold_ms": self.thresholds.max_fetch_time_ms,
            "spa_detected": result.is_spa_detected,
            "status_code": result.status_code,
            "title_present": bool(result.title),
            "link_count": len(result.links_found),
        }

        return decision, metrics

    def _check_status_code(self, result: FastPathResult) -> bool:
        """Check if HTTP status indicates success."""
        return result.status_code == 200

    def _check_text_length(self, result: FastPathResult) -> bool:
        """Check if extracted text meets minimum length."""
        return len(result.text_content) >= self.thresholds.min_text_length

    def _check_content_ratio(self, result: FastPathResult) -> bool:
        """Check if text-to-HTML ratio is sufficient."""
        # P1 Fix: Use original_html_length to avoid inflated ratio from truncation
        html_length = result.original_html_length if result.original_html_length > 0 else len(result.html)
        if not html_length:
            return False
        ratio = len(result.text_content) / html_length
        return ratio >= self.thresholds.min_content_ratio

    def _check_no_spa(self, result: FastPathResult) -> bool:
        """Check if page is not detected as SPA shell."""
        return not result.is_spa_detected

    def _check_fetch_time(self, result: FastPathResult) -> bool:
        """Check if fetch completed within acceptable time."""
        return result.fetch_time_ms <= self.thresholds.max_fetch_time_ms

    def _check_content_type(self, result: FastPathResult) -> bool:
        """Check if content type is valid HTML (not PDF/binary)."""
        content_type = result.content_type.lower()
        for blocked in self.thresholds.blocked_content_types:
            if blocked in content_type:
                return False
        return True

    def _check_title(self, result: FastPathResult) -> bool:
        """Check if page title was extracted."""
        return bool(result.title and result.title.strip())

    def _check_link_count(self, result: FastPathResult) -> bool:
        """Check if minimum links were found."""
        return len(result.links_found) >= self.thresholds.min_link_count

    def should_fallback(self, result: FastPathResult) -> tuple[bool, str | None]:
        """Quick check for fallback decision.

        Args:
            result: The FastPathResult to evaluate

        Returns:
            Tuple of (should_fallback, reason)
        """
        decision = self.evaluate(result)
        return (not decision.passed), decision.fallback_reason


class AdaptiveQualityGate(QualityGate):
    """Quality gate with adaptive thresholds based on domain patterns.

    Adjusts thresholds dynamically based on observed site characteristics.
    Useful for handling sites with varying content structures.
    """

    def __init__(
        self,
        base_thresholds: QualityThresholds | None = None,
        domain_adjustments: dict[str, QualityThresholds] | None = None,
    ) -> None:
        """Initialize adaptive gate with domain-specific overrides.

        Args:
            base_thresholds: Default thresholds
            domain_adjustments: Map of domain -> custom thresholds
        """
        super().__init__(base_thresholds)
        self.domain_adjustments = domain_adjustments or {}

    def get_thresholds_for_url(self, url: str) -> QualityThresholds:
        """Get appropriate thresholds for a URL based on domain."""
        from urllib.parse import urlparse

        domain = urlparse(url).netloc.lower()

        # Check for exact domain match
        if domain in self.domain_adjustments:
            return self.domain_adjustments[domain]

        # Check for parent domain match (e.g., blog.example.com matches example.com)
        parts = domain.split(".")
        for i in range(1, len(parts)):
            parent = ".".join(parts[i:])
            if parent in self.domain_adjustments:
                return self.domain_adjustments[parent]

        return self.thresholds

    def evaluate(self, result: FastPathResult) -> QualityDecision:
        """Evaluate using domain-specific thresholds."""
        # Temporarily swap thresholds for this evaluation
        original_thresholds = self.thresholds
        self.thresholds = self.get_thresholds_for_url(result.url)

        try:
            return super().evaluate(result)
        finally:
            self.thresholds = original_thresholds
