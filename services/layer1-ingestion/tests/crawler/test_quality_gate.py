"""Tests for QualityGate fast path validation.

Covers quality threshold evaluation, fallback decisions, and
adaptive threshold functionality.
"""

from __future__ import annotations

import pytest
import trafilatura  # noqa: F401 — mandatory dep; install via layer1-ingestion[dev]

from layer1_ingestion.crawler.httpx_crawler import FastPathResult
from layer1_ingestion.crawler.quality_gate import AdaptiveQualityGate, QualityGate, QualityThresholds


class TestQualityGateBasic:
    """Test basic quality gate functionality."""

    @pytest.fixture
    def gate(self) -> QualityGate:
        """Create a QualityGate with default thresholds."""
        return QualityGate()

    @pytest.fixture
    def good_result(self) -> FastPathResult:
        """Create a high-quality result that should pass."""
        return FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html><head><title>Good Page</title></head><body>" + "<p>Content paragraph</p>" * 100 + "</body></html>",
            title="Good Page",
            text_content="Content paragraph " * 100,
            content_hash="abc123",
            links_found=["https://example.com/other"],
            is_spa_detected=False,
            fetch_time_ms=150,
            content_type="text/html",
        )

    def test_quality_pass(self, gate: QualityGate, good_result: FastPathResult) -> None:
        """High quality result passes all checks."""
        decision = gate.evaluate(good_result)

        assert decision.passed is True
        assert all(decision.checks.values())
        assert decision.fallback_reason is None

    def test_quality_fail_short_text(self, gate: QualityGate) -> None:
        """Short text fails quality check."""
        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html><body>Short</body></html>",
            title="Page",
            text_content="Short",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)

        assert decision.passed is False
        assert decision.checks["text_length"] is False
        assert decision.fallback_reason == "text_length"

    def test_quality_fail_spa_detected(self, gate: QualityGate) -> None:
        """SPA detection fails quality check."""
        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>" + "<p>Content</p>" * 100 + "</html>",
            title="Page",
            text_content="Content " * 100,
            content_hash="hash",
            is_spa_detected=True,  # SPA detected
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)

        assert decision.passed is False
        assert decision.checks["no_spa"] is False
        assert decision.fallback_reason == "no_spa"

    def test_quality_fail_status_code(self, gate: QualityGate) -> None:
        """Non-200 status fails quality check."""
        result = FastPathResult(
            url="https://example.com/page",
            status_code=404,
            html="<html>Not found</html>",
            title="404",
            text_content="Not found " * 50,
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)

        assert decision.passed is False
        assert decision.checks["success_status"] is False

    def test_quality_fail_content_ratio(self, gate: QualityGate) -> None:
        """Low content ratio fails quality check."""
        # Lots of HTML, little text
        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>" + "<div class='wrapper'><span>" * 500 + "Text" + "</span></div>" * 500 + "</html>",
            title="Page",
            text_content="Text",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)

        assert decision.passed is False
        assert decision.checks["content_ratio"] is False

    def test_quality_fail_slow_fetch(self, gate: QualityGate) -> None:
        """Slow fetch fails quality check."""
        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>" + "<p>Content</p>" * 100 + "</html>",
            title="Page",
            text_content="Content " * 100,
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=10000,  # Very slow
        )

        decision = gate.evaluate(result)

        assert decision.passed is False
        assert decision.checks["fetch_time"] is False


class TestQualityThresholds:
    """Test configurable quality thresholds."""

    def test_custom_text_length_threshold(self) -> None:
        """Custom text length threshold."""
        thresholds = QualityThresholds(min_text_length=100)
        gate = QualityGate(thresholds)

        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html><body>Medium length content here that exceeds the one hundred character threshold easily with extra padding</body></html>",
            title="Page",
            text_content="Medium length content here that exceeds the one hundred character threshold easily with extra padding",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert decision.passed is True
        assert decision.checks["text_length"] is True

    def test_custom_content_ratio_threshold(self) -> None:
        """Custom content ratio threshold."""
        thresholds = QualityThresholds(min_content_ratio=0.01)  # More lenient
        gate = QualityGate(thresholds)

        # Moderate HTML-to-text ratio
        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>" + "<div>" * 50 + "Text content here" + "</div>" * 50 + "</html>",
            title="Page",
            text_content="Text content here",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert decision.checks["content_ratio"] is True

    def test_custom_fetch_time_threshold(self) -> None:
        """Custom fetch time threshold."""
        thresholds = QualityThresholds(max_fetch_time_ms=500)
        gate = QualityGate(thresholds)

        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html><body>Content</body></html>",
            title="Page",
            text_content="Content " * 100,
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=300,  # Under 500ms threshold
        )

        decision = gate.evaluate(result)
        assert decision.checks["fetch_time"] is True

    def test_optional_title_check(self) -> None:
        """Title check can be disabled."""
        thresholds = QualityThresholds(require_title=False)
        gate = QualityGate(thresholds)

        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html><body>Content</body></html>",
            title="",  # No title
            text_content="Content " * 100,
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert "has_title" not in decision.checks

    def test_link_count_threshold(self) -> None:
        """Link count threshold when configured."""
        thresholds = QualityThresholds(min_link_count=2)
        gate = QualityGate(thresholds)

        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html><body>Content</body></html>",
            title="Page",
            text_content="Content " * 100,
            content_hash="hash",
            links_found=["https://example.com/1"],  # Only 1 link
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert decision.checks["link_count"] is False


class TestContentTypeChecking:
    """Test content type validation."""

    def test_block_pdf_content_type(self) -> None:
        """PDF content type triggers fallback."""
        thresholds = QualityThresholds()
        gate = QualityGate(thresholds)

        result = FastPathResult(
            url="https://example.com/doc.pdf",
            status_code=200,
            html="",
            title="",
            text_content="",
            content_hash="hash",
            content_type="application/pdf",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert decision.checks["valid_content_type"] is False

    def test_allow_html_content_type(self) -> None:
        """HTML content type is valid."""
        gate = QualityGate()

        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>Content</html>",
            title="Page",
            text_content="Content",
            content_hash="hash",
            content_type="text/html; charset=utf-8",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert decision.checks["valid_content_type"] is True


class TestFallbackDecision:
    """Test should_fallback convenience method."""

    def test_should_fallback_true(self) -> None:
        """Returns True when quality fails."""
        gate = QualityGate()

        result = FastPathResult(
            url="https://example.com/page",
            status_code=404,
            html="",
            title="",
            text_content="",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        should_fallback, reason = gate.should_fallback(result)

        assert should_fallback is True
        assert reason == "success_status"

    def test_should_fallback_false(self) -> None:
        """Returns False when quality passes."""
        gate = QualityGate()

        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>" + "<p>Content</p>" * 100 + "</html>",
            title="Page",
            text_content="Content " * 100,
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        should_fallback, reason = gate.should_fallback(result)

        assert should_fallback is False
        assert reason is None


class TestDetailedMetrics:
    """Test detailed metrics generation."""

    def test_evaluate_with_details(self) -> None:
        """Get both decision and detailed metrics."""
        gate = QualityGate()

        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>" + "<p>Content</p>" * 100 + "</html>",
            title="Page",
            text_content="Content " * 100,
            content_hash="hash",
            links_found=["https://example.com/1", "https://example.com/2"],
            is_spa_detected=False,
            fetch_time_ms=150,
        )

        decision, metrics = gate.evaluate_with_details(result)

        assert decision.passed is True
        assert metrics["url"] == "https://example.com/page"
        assert metrics["text_length"] == 800  # "Content " * 100
        assert metrics["fetch_time_ms"] == 150
        assert metrics["link_count"] == 2


class TestAdaptiveQualityGate:
    """Test adaptive quality gate with domain-specific thresholds."""

    def test_domain_specific_thresholds(self) -> None:
        """Use domain-specific thresholds when available."""
        base = QualityThresholds(min_text_length=500)
        blog_adjustment = QualityThresholds(min_text_length=100)  # More lenient

        gate = AdaptiveQualityGate(
            base_thresholds=base,
            domain_adjustments={"blog.example.com": blog_adjustment},
        )

        # Medium content passes on blog subdomain (>= 100, < 500)
        blog_result = FastPathResult(
            url="https://blog.example.com/post",
            status_code=200,
            html="<html><body>This is a medium length blog post that is well over one hundred characters long with extra padding</body></html>",
            title="Post",
            text_content="This is a medium length blog post that is well over one hundred characters long with extra padding added",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(blog_result)
        assert decision.passed is True

        # Same content fails on main domain (threshold 500)
        main_result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html><body>This is a medium length blog post that is well over one hundred characters long with extra padding</body></html>",
            title="Page",
            text_content="This is a medium length blog post that is well over one hundred characters long with extra padding added",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(main_result)
        assert decision.passed is False

    def test_parent_domain_fallback(self) -> None:
        """Fall back to parent domain thresholds."""
        base = QualityThresholds(min_text_length=500)
        parent_adjustment = QualityThresholds(min_text_length=200)

        gate = AdaptiveQualityGate(
            base_thresholds=base,
            domain_adjustments={"example.com": parent_adjustment},
        )

        # Subdomain should inherit parent thresholds
        result = FastPathResult(
            url="https://sub.blog.example.com/page",
            status_code=200,
            html="<html><body>Medium content length</body></html>",
            title="Page",
            text_content="Medium content length",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        # Should use example.com threshold (200) which passes
        thresholds = gate.get_thresholds_for_url("https://sub.blog.example.com/page")
        assert thresholds.min_text_length == 200

    def test_default_thresholds_for_unknown_domain(self) -> None:
        """Use default thresholds for unknown domains."""
        base = QualityThresholds(min_text_length=500)
        gate = AdaptiveQualityGate(base_thresholds=base)

        thresholds = gate.get_thresholds_for_url("https://unknown-site.com/page")
        assert thresholds.min_text_length == 500


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_html_content_ratio(self) -> None:
        """Handle empty HTML gracefully."""
        gate = QualityGate()

        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="",
            title="",
            text_content="",
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert decision.passed is False
        assert decision.checks["content_ratio"] is False

    def test_exact_threshold_boundary(self) -> None:
        """Test at exact threshold boundary."""
        thresholds = QualityThresholds(min_text_length=500)
        gate = QualityGate(thresholds)

        # Exactly 500 characters should pass (>= threshold)
        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>" + "x" * 500 + "</html>",
            title="Page",
            text_content="x" * 500,
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert decision.checks["text_length"] is True

    def test_one_under_threshold_boundary(self) -> None:
        """Test just under threshold boundary."""
        thresholds = QualityThresholds(min_text_length=500)
        gate = QualityGate(thresholds)

        # 499 characters should fail (< threshold)
        result = FastPathResult(
            url="https://example.com/page",
            status_code=200,
            html="<html>" + "x" * 499 + "</html>",
            title="Page",
            text_content="x" * 499,
            content_hash="hash",
            is_spa_detected=False,
            fetch_time_ms=100,
        )

        decision = gate.evaluate(result)
        assert decision.checks["text_length"] is False

