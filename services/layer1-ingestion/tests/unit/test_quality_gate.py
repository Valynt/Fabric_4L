"""
Tests for QualityGate and AdaptiveQualityGate.

Covers:
- evaluate(): all checks pass / individual check failures
- evaluate_with_details(): metrics shape
- should_fallback(): convenience wrapper
- AdaptiveQualityGate: domain-specific threshold override
- Configurable thresholds (QualityThresholds)
"""

import pytest

from layer1_ingestion.crawler.httpx_crawler import FastPathResult
from layer1_ingestion.crawler.quality_gate import (
    AdaptiveQualityGate,
    QualityGate,
    QualityThresholds,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_result(
    url: str = "https://example.com/page",
    status_code: int = 200,
    html: str = "x" * 2000,
    title: str = "Example Page",
    text_content: str = "a" * 1000,
    content_hash: str = "abc123",
    links_found: list[str] | None = None,
    is_spa_detected: bool = False,
    fetch_time_ms: int = 1000,
    content_type: str = "text/html; charset=utf-8",
    original_html_length: int = 0,
) -> FastPathResult:
    """Factory for FastPathResult test fixtures."""
    return FastPathResult(
        url=url,
        status_code=status_code,
        html=html,
        title=title,
        text_content=text_content,
        content_hash=content_hash,
        links_found=links_found or [],
        is_spa_detected=is_spa_detected,
        fetch_time_ms=fetch_time_ms,
        content_type=content_type,
        original_html_length=original_html_length or len(html),
    )


@pytest.fixture
def gate() -> QualityGate:
    """Default QualityGate with standard thresholds."""
    return QualityGate()


@pytest.fixture
def passing_result() -> FastPathResult:
    """A FastPathResult that meets all default quality thresholds."""
    html = "x" * 2000
    text = "a" * 1000
    return _make_result(html=html, text_content=text, original_html_length=len(html))


# ---------------------------------------------------------------------------
# QualityGate.evaluate
# ---------------------------------------------------------------------------

class TestQualityGateEvaluate:
    """Tests for QualityGate.evaluate."""

    def test_all_checks_pass(self, gate, passing_result):
        """All quality checks pass for a well-formed result."""
        decision = gate.evaluate(passing_result)
        assert decision.passed is True
        assert decision.fallback_reason is None
        assert all(decision.checks.values())

    def test_fail_non_200_status(self, gate):
        """HTTP 404 causes success_status check to fail."""
        result = _make_result(status_code=404)
        decision = gate.evaluate(result)
        assert decision.passed is False
        assert "success_status" in decision.checks
        assert decision.checks["success_status"] is False

    def test_fail_short_text(self, gate):
        """Text shorter than min_text_length causes text_length check to fail."""
        result = _make_result(text_content="too short", html="x" * 2000, original_html_length=2000)
        decision = gate.evaluate(result)
        assert decision.passed is False
        assert decision.checks["text_length"] is False

    def test_fail_low_content_ratio(self, gate):
        """Very long HTML with little text causes content_ratio check to fail."""
        html = "x" * 100_000
        text = "a" * 100  # tiny ratio
        result = _make_result(html=html, text_content=text, original_html_length=len(html))
        decision = gate.evaluate(result)
        assert decision.passed is False
        assert decision.checks["content_ratio"] is False

    def test_fail_spa_detected(self, gate):
        """SPA-detected result fails no_spa check."""
        result = _make_result(is_spa_detected=True)
        decision = gate.evaluate(result)
        assert decision.passed is False
        assert decision.checks["no_spa"] is False

    def test_fail_slow_fetch(self, gate):
        """Fetch time exceeding max_fetch_time_ms fails fetch_time check."""
        result = _make_result(fetch_time_ms=99_000)
        decision = gate.evaluate(result)
        assert decision.passed is False
        assert decision.checks["fetch_time"] is False

    def test_fail_blocked_content_type(self, gate):
        """PDF content type fails valid_content_type check."""
        result = _make_result(content_type="application/pdf")
        decision = gate.evaluate(result)
        assert decision.passed is False
        assert decision.checks["valid_content_type"] is False

    def test_fail_missing_title_when_required(self):
        """Missing title fails has_title check when require_title=True."""
        gate = QualityGate(QualityThresholds(require_title=True))
        result = _make_result(title="")
        decision = gate.evaluate(result)
        assert decision.passed is False
        assert decision.checks.get("has_title") is False

    def test_title_check_skipped_when_not_required(self):
        """has_title check is absent from checks when require_title=False."""
        gate = QualityGate(QualityThresholds(require_title=False))
        result = _make_result(title="")  # no title but not required
        decision = gate.evaluate(result)
        assert "has_title" not in decision.checks

    def test_link_count_check_skipped_when_zero_threshold(self, gate):
        """link_count check is absent when min_link_count=0 (default)."""
        result = _make_result(links_found=[])
        decision = gate.evaluate(result)
        assert "link_count" not in decision.checks

    def test_link_count_check_added_when_threshold_set(self):
        """link_count check is present when min_link_count > 0."""
        gate = QualityGate(QualityThresholds(min_link_count=5))
        result = _make_result(links_found=["http://a.com"])
        decision = gate.evaluate(result)
        assert "link_count" in decision.checks
        assert decision.checks["link_count"] is False

    def test_link_count_passes_when_sufficient(self):
        """link_count check passes when enough links found."""
        gate = QualityGate(QualityThresholds(min_link_count=2))
        result = _make_result(links_found=["http://a.com", "http://b.com", "http://c.com"])
        decision = gate.evaluate(result)
        assert decision.checks["link_count"] is True

    def test_fallback_reason_is_first_failing_check(self, gate):
        """fallback_reason names the first failing check key."""
        result = _make_result(status_code=500)
        decision = gate.evaluate(result)
        assert decision.fallback_reason is not None
        assert isinstance(decision.fallback_reason, str)


# ---------------------------------------------------------------------------
# QualityGate.evaluate_with_details
# ---------------------------------------------------------------------------

class TestEvaluateWithDetails:
    """Tests for evaluate_with_details."""

    def test_returns_decision_and_metrics(self, gate, passing_result):
        """evaluate_with_details returns a (decision, metrics) tuple."""
        decision, metrics = gate.evaluate_with_details(passing_result)
        assert decision.passed is True
        assert "url" in metrics
        assert "text_length" in metrics
        assert "content_ratio" in metrics
        assert "fetch_time_ms" in metrics

    def test_metrics_url_matches_result(self, gate, passing_result):
        _, metrics = gate.evaluate_with_details(passing_result)
        assert metrics["url"] == passing_result.url

    def test_metrics_spa_detected_field(self, gate):
        result = _make_result(is_spa_detected=True)
        _, metrics = gate.evaluate_with_details(result)
        assert metrics["spa_detected"] is True


# ---------------------------------------------------------------------------
# QualityGate.should_fallback
# ---------------------------------------------------------------------------

class TestShouldFallback:
    """Tests for the should_fallback convenience method."""

    def test_no_fallback_for_passing_result(self, gate, passing_result):
        should, reason = gate.should_fallback(passing_result)
        assert should is False
        assert reason is None

    def test_fallback_for_failing_result(self, gate):
        result = _make_result(status_code=503)
        should, reason = gate.should_fallback(result)
        assert should is True
        assert reason is not None


# ---------------------------------------------------------------------------
# QualityGate content_ratio edge case (original_html_length = 0)
# ---------------------------------------------------------------------------

class TestContentRatioEdgeCase:
    """Edge cases for _check_content_ratio."""

    def test_zero_original_html_length_falls_back_to_html_field(self, gate):
        """When original_html_length == 0, falls back to len(html)."""
        html = "x" * 5000
        text = "a" * 500
        result = _make_result(html=html, text_content=text, original_html_length=0)
        decision = gate.evaluate(result)
        # ratio = 500/5000 = 0.1 > default 0.02, so should pass
        assert decision.checks["content_ratio"] is True

    def test_zero_html_content_fails_ratio(self, gate):
        """Empty HTML causes content_ratio to fail."""
        result = _make_result(html="", text_content="a" * 600, original_html_length=0)
        decision = gate.evaluate(result)
        assert decision.checks["content_ratio"] is False


# ---------------------------------------------------------------------------
# AdaptiveQualityGate
# ---------------------------------------------------------------------------

class TestAdaptiveQualityGate:
    """Tests for AdaptiveQualityGate domain-specific threshold overrides."""

    def test_exact_domain_override_applied(self):
        """Domain-specific thresholds override base for matching domain."""
        strict = QualityThresholds(min_text_length=10_000)
        adaptive = AdaptiveQualityGate(
            base_thresholds=QualityThresholds(min_text_length=500),
            domain_adjustments={"strict.example.com": strict},
        )
        result = _make_result(
            url="https://strict.example.com/page",
            text_content="a" * 600,  # passes base (500) but fails strict (10000)
            html="x" * 5000,
            original_html_length=5000,
        )
        decision = adaptive.evaluate(result)
        assert decision.checks["text_length"] is False

    def test_base_thresholds_used_for_unknown_domain(self):
        """Unknown domain uses base thresholds."""
        adaptive = AdaptiveQualityGate(
            base_thresholds=QualityThresholds(min_text_length=100),
            domain_adjustments={},
        )
        result = _make_result(
            url="https://other.example.com/",
            text_content="a" * 200,
            html="x" * 2000,
            original_html_length=2000,
        )
        decision = adaptive.evaluate(result)
        assert decision.checks["text_length"] is True

    def test_parent_domain_match(self):
        """blog.example.com matches example.com domain adjustment."""
        lenient = QualityThresholds(min_text_length=10)
        adaptive = AdaptiveQualityGate(
            base_thresholds=QualityThresholds(min_text_length=5000),
            domain_adjustments={"example.com": lenient},
        )
        result = _make_result(
            url="https://blog.example.com/article",
            text_content="a" * 50,  # fails base (5000) but passes lenient (10)
            html="x" * 2000,
            original_html_length=2000,
        )
        decision = adaptive.evaluate(result)
        assert decision.checks["text_length"] is True

    def test_original_thresholds_restored_after_evaluate(self):
        """Base thresholds are unchanged after domain-specific evaluate call."""
        base = QualityThresholds(min_text_length=500)
        adaptive = AdaptiveQualityGate(
            base_thresholds=base,
            domain_adjustments={"special.com": QualityThresholds(min_text_length=1)},
        )
        result = _make_result(url="https://special.com/")
        adaptive.evaluate(result)
        # Thresholds should be restored to base
        assert adaptive.thresholds.min_text_length == 500

    def test_get_thresholds_returns_exact_match(self):
        """get_thresholds_for_url returns domain-specific override."""
        override = QualityThresholds(min_text_length=9999)
        adaptive = AdaptiveQualityGate(
            domain_adjustments={"target.com": override},
        )
        thresholds = adaptive.get_thresholds_for_url("https://target.com/page")
        assert thresholds.min_text_length == 9999

    def test_get_thresholds_returns_base_for_unknown(self):
        """get_thresholds_for_url falls back to base for unknown domain."""
        base = QualityThresholds(min_text_length=42)
        adaptive = AdaptiveQualityGate(base_thresholds=base, domain_adjustments={})
        thresholds = adaptive.get_thresholds_for_url("https://unknown.example.org/")
        assert thresholds.min_text_length == 42
