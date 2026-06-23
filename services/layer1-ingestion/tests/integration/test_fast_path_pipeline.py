"""Integration tests for HTTPX Fast Path + Smart Router pipeline.

End-to-end tests validating the full hybrid routing architecture
from target configuration through execution to result validation.
"""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from layer1_ingestion.crawler.execution_logger import ExecutionLogger, ExecutionPath
from layer1_ingestion.crawler.httpx_crawler import HttpxCrawler
from layer1_ingestion.crawler.quality_gate import QualityGate
from layer1_ingestion.crawler.smart_router import RouteType, SmartRouter
from layer1_ingestion.shared.models import CrawlPath


class TestTargetLevelModes:
    """Test target-level crawl mode configuration."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fast_mode_uses_httpx_only(self) -> None:
        """FAST mode always uses HTTPX, even for dynamic-looking URLs."""
        # Setup
        respx.get("https://example.com/platform/product").mock(
            return_value=Response(
                200,
                html="<html><title>Product</title><body>Content</body></html>",
            )
        )

        router = SmartRouter()
        async with HttpxCrawler() as crawler:
            decision = router.decide(
                "https://example.com/platform/product",
                target_mode=RouteType.FAST,
            )
            assert decision.route == RouteType.FAST

            result = await crawler.fetch("https://example.com/platform/product")
            assert result.status_code == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_browser_mode_skips_fast_path(self) -> None:
        """BROWSER mode skips HTTPX entirely."""
        router = SmartRouter()

        decision = router.decide(
            "https://example.com/sitemap.xml",  # Would normally be fast
            target_mode=RouteType.BROWSER,
        )

        assert decision.route == RouteType.BROWSER
        assert decision.stagehand_config is not None

    @respx.mock
    @pytest.mark.asyncio
    async def test_fallback_mode_with_quality_pass(self) -> None:
        """FALLBACK mode uses HTTPX when quality passes."""
        # Good static content
        respx.get("https://example.com/article").mock(
            return_value=Response(
                200,
                html="<html><head><title>Article</title></head><body>" +
                     "<p>Paragraph " * 100 + "</p></body></html>",
            )
        )

        router = SmartRouter()
        gate = QualityGate()
        async with HttpxCrawler() as crawler:
            decision = router.decide(
                "https://example.com/article",
                target_mode=RouteType.FAST_WITH_FALLBACK,
            )
            assert decision.route == RouteType.FAST_WITH_FALLBACK

            result = await crawler.fetch("https://example.com/article")
            quality = gate.evaluate(result)

            assert quality.passed is True


class TestPerURLSmartRouting:
    """Test per-URL Smart Router decisions."""

    @pytest.mark.asyncio
    async def test_static_assets_route_fast(self) -> None:
        """Static assets (.css, .js) route to fast path."""
        router = SmartRouter()

        for ext in [".css", ".js", ".png"]:
            decision = router.decide(
                f"https://example.com/assets/file{ext}",
                target_mode=RouteType.FAST_WITH_FALLBACK,
            )
            assert decision.route == RouteType.FAST, f"{ext} should route to FAST"
            assert decision.reason == "static_asset"

    @pytest.mark.asyncio
    async def test_sitemap_routes_fast_high_priority(self) -> None:
        """Sitemap.xml routes to fast with high priority."""
        router = SmartRouter()

        decision = router.decide(
            "https://example.com/sitemap.xml",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )

        assert decision.route == RouteType.FAST
        assert decision.reason == "sitemap"
        assert decision.priority == 10

    @pytest.mark.asyncio
    async def test_dynamic_pages_route_browser(self) -> None:
        """Dynamic page patterns route to browser."""
        router = SmartRouter()

        dynamic_urls = [
            "https://example.com/platform/product",
            "https://example.com/pricing",
            "https://example.com/solutions/marketing",
            "https://example.com/customer-stories/acme",
        ]

        for url in dynamic_urls:
            decision = router.decide(
                url,
                target_mode=RouteType.FAST_WITH_FALLBACK,
            )
            assert decision.route == RouteType.BROWSER, f"{url} should route to BROWSER"
            assert "known_dynamic_page" in decision.reason

    @pytest.mark.asyncio
    async def test_navigation_urls_route_browser(self) -> None:
        """URLs with fragments/query params route to browser."""
        router = SmartRouter()

        decision = router.decide(
            "https://example.com/page#section",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.BROWSER

        decision = router.decide(
            "https://example.com/search?q=test",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.BROWSER

    @pytest.mark.asyncio
    async def test_previous_crawl_consistency(self) -> None:
        """Previous browser crawl maintains consistency."""
        router = SmartRouter()

        decision = router.decide(
            "https://example.com/page",
            target_mode=RouteType.FAST_WITH_FALLBACK,
            previous_route=RouteType.BROWSER,
        )

        assert decision.route == RouteType.BROWSER
        assert decision.reason == "previous_crawl_browser"


class TestSPADetection:
    """Test SPA detection triggering fallback."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_spa_detected_triggers_fallback(self) -> None:
        """SPA detection in HTTPX result triggers fallback."""
        # SPA shell response
        respx.get("https://example.com/app").mock(
            return_value=Response(
                200,
                html="""
                <html>
                    <head>
                        <script src="1.js"></script>
                        <script src="2.js"></script>
                        <script src="3.js"></script>
                        <script src="4.js"></script>
                        <script src="5.js"></script>
                        <script src="6.js"></script>
                    </head>
                    <body><div id="root"></div></body>
                </html>
                """,
            )
        )

        router = SmartRouter()
        gate = QualityGate()
        async with HttpxCrawler() as crawler:
            decision = router.decide(
                "https://example.com/app",
                target_mode=RouteType.FAST_WITH_FALLBACK,
            )
            assert decision.route == RouteType.FAST_WITH_FALLBACK

            result = await crawler.fetch("https://example.com/app")
            assert result.is_spa_detected is True

            quality = gate.evaluate(result)
            assert quality.passed is False
            assert quality.fallback_reason == "no_spa"

    @respx.mock
    @pytest.mark.asyncio
    async def test_non_spa_passes_quality(self) -> None:
        """Non-SPA content passes quality check."""
        respx.get("https://example.com/page").mock(
            return_value=Response(
                200,
                html="<html><head><title>Page</title></head><body>" +
                     "<h1>Title</h1><p>Content paragraph</p>" * 50 +
                     "</body></html>",
            )
        )

        router = SmartRouter()
        gate = QualityGate()
        async with HttpxCrawler() as crawler:
            result = await crawler.fetch("https://example.com/page")
            assert result.is_spa_detected is False

            quality = gate.evaluate(result)
            assert quality.passed is True


class TestQualityGating:
    """Test quality gate evaluation in pipeline."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_short_content_fails_quality(self) -> None:
        """Short content fails quality and triggers fallback."""
        respx.get("https://example.com/empty").mock(
            return_value=Response(200, html="<html><body>Short</body></html>")
        )

        gate = QualityGate()
        async with HttpxCrawler() as crawler:
            result = await crawler.fetch("https://example.com/empty")
            quality = gate.evaluate(result)

            assert quality.passed is False
            assert quality.fallback_reason == "text_length"

    @respx.mock
    @pytest.mark.asyncio
    async def test_low_content_ratio_fails_quality(self) -> None:
        """Low text-to-HTML ratio fails quality."""
        # Lots of HTML markup, little content
        respx.get("https://example.com/heavy").mock(
            return_value=Response(
                200,
                html="<html>" + "<div class='wrapper'><span>" * 200 +
                     "Some text" +
                     "</span></div>" * 200 + "</html>",
            )
        )

        gate = QualityGate()
        async with HttpxCrawler() as crawler:
            result = await crawler.fetch("https://example.com/heavy")
            quality = gate.evaluate(result)

            assert quality.passed is False
            assert quality.checks["content_ratio"] is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_error_status_fails_quality(self) -> None:
        """Non-200 status fails quality."""
        respx.get("https://example.com/error").mock(
            return_value=Response(500, text="Server Error")
        )

        gate = QualityGate()
        async with HttpxCrawler() as crawler:
            result = await crawler.fetch("https://example.com/error")
            quality = gate.evaluate(result)

            assert quality.passed is False
            assert quality.checks["success_status"] is False


class TestExecutionLogging:
    """Test execution logging captures correct data."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_fast_path_success(self) -> None:
        """Log fast path execution correctly."""
        respx.get("https://example.com/page").mock(
            return_value=Response(
                200,
                html="<html><head><title>Page</title></head><body>" +
                     "<p>Content</p>" * 100 + "</body></html>",
            )
        )

        logger = ExecutionLogger()
        router = SmartRouter()
        async with HttpxCrawler() as crawler:
            decision = router.decide(
                "https://example.com/page",
                target_mode=RouteType.FAST,
            )
            result = await crawler.fetch("https://example.com/page")

            entry = logger.log_fast_path(
                job_id="test-job-123",
                url="https://example.com/page",
                result=result,
                routing_decision=decision,
                target_mode="fast",
            )

            assert entry.job_id == "test-job-123"
            assert entry.final_path == ExecutionPath.FAST.value
            assert entry.domain == "example.com"
            assert entry.status_code == 200
            assert entry.spa_detected is False

    @respx.mock
    @pytest.mark.asyncio
    async def test_log_fallback(self) -> None:
        """Log fallback execution correctly."""
        respx.get("https://example.com/spa").mock(
            return_value=Response(
                200,
                html="""
                <html>
                    <head>
                        <script src="1.js"></script>
                        <script src="2.js"></script>
                        <script src="3.js"></script>
                        <script src="4.js"></script>
                        <script src="5.js"></script>
                        <script src="6.js"></script>
                    </head>
                    <body><div id="app"></div></body>
                </html>
                """,
            )
        )

        logger = ExecutionLogger()
        router = SmartRouter()
        gate = QualityGate()
        async with HttpxCrawler() as crawler:
            decision = router.decide(
                "https://example.com/spa",
                target_mode=RouteType.FAST_WITH_FALLBACK,
            )
            result = await crawler.fetch("https://example.com/spa")
            quality = gate.evaluate(result)

            entry = logger.log_fallback(
                job_id="test-job-123",
                url="https://example.com/spa",
                fast_result=result,
                quality_decision=quality,
                routing_decision=decision,
                target_mode="fast_fallback",
            )

            assert entry.final_path == ExecutionPath.FALLBACK.value
            assert entry.quality_passed is False
            assert entry.fallback_reason == "no_spa"
            assert entry.spa_detected is True


class TestEndToEndPipeline:
    """Test complete end-to-end pipeline scenarios."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_mixed_content_target(self) -> None:
        """Handle target with mix of static and dynamic pages."""
        # Setup: some pages static, some dynamic
        respx.get("https://example.com/").mock(
            return_value=Response(
                200,
                html="<html><head><title>Home</title></head><body>" +
                     "<p>Home page content</p>" * 50 + "</body></html>",
            )
        )
        respx.get("https://example.com/sitemap.xml").mock(
            return_value=Response(
                200,
                content=b"<xml></xml>",
                headers={"content-type": "application/xml"},
            )
        )

        router = SmartRouter()
        gate = QualityGate()
        logger = ExecutionLogger()
        async with HttpxCrawler() as crawler:
            urls = [
                "https://example.com/",  # Default → FAST
                "https://example.com/sitemap.xml",  # Sitemap → FAST
            ]

            results = []
            for url in urls:
                decision = router.decide(url, target_mode=RouteType.FAST_WITH_FALLBACK)
                result = await crawler.fetch(url)
                quality = gate.evaluate(result)

                if quality.passed:
                    entry = logger.log_fast_path(
                        job_id="mixed-test",
                        url=url,
                        result=result,
                        routing_decision=decision,
                        target_mode="fast_fallback",
                    )
                else:
                    entry = logger.log_fallback(
                        job_id="mixed-test",
                        url=url,
                        fast_result=result,
                        quality_decision=quality,
                        routing_decision=decision,
                        target_mode="fast_fallback",
                    )

                results.append({
                    "url": url,
                    "route": decision.route.value,
                    "quality_passed": quality.passed,
                    "final_path": entry.final_path,
                })

            # Verify routing decisions
            assert results[0]["route"] in ["fast", "fast_fallback"]
            assert results[0]["quality_passed"] is True
            assert results[1]["route"] == "fast"

    @pytest.mark.asyncio
    async def test_backward_compatibility_browser_default(self) -> None:
        """Existing BROWSER targets work unchanged."""
        router = SmartRouter()

        # When no mode specified or BROWSER explicitly set
        decision = router.decide(
            "https://example.com/page",
            target_mode=RouteType.BROWSER,
        )

        assert decision.route == RouteType.BROWSER
        assert decision.stagehand_config is not None


class TestPerformanceCharacteristics:
    """Test performance characteristics of fast path."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fast_path_fetch_time_under_500ms(self) -> None:
        """Fast path completes in under 500ms."""
        respx.get("https://example.com/fast").mock(
            return_value=Response(
                200,
                html="<html><head><title>Fast</title></head><body>Content</body></html>",
            )
        )

        async with HttpxCrawler() as crawler:
            result = await crawler.fetch("https://example.com/fast")

            # Should complete in well under 500ms (locally mocked)
            assert result.fetch_time_ms < 500
            assert result.status_code == 200

    @respx.mock
    @pytest.mark.asyncio
    async def test_concurrent_fetch_performance(self) -> None:
        """Multiple URLs fetched concurrently."""
        for i in range(10):
            respx.get(f"https://example.com/page{i}").mock(
                return_value=Response(200, html=f"<html>Page {i}</html>")
            )

        async with HttpxCrawler() as crawler:
            urls = [f"https://example.com/page{i}" for i in range(10)]
            import time

            start = time.monotonic()
            results = await crawler.fetch_batch(urls)
            elapsed_ms = (time.monotonic() - start) * 1000

            # All 10 should complete in reasonable time (concurrent)
            assert len(results) == 10
            assert elapsed_ms < 2000  # Should be much faster than sequential

    def test_execution_logger_handles_invalid_utf8(self) -> None:
        """P1 Regression: ExecutionLogger handles binary/invalid UTF-8 content."""
        from unittest.mock import MagicMock
        from layer1_ingestion.crawler.execution_logger import ExecutionLogger

        logger = ExecutionLogger()

        # Create result with invalid UTF-8 sequences (e.g., binary content)
        result = MagicMock()
        result.html = b"\xff\xfe<script>".decode("latin-1")  # Invalid UTF-8 bytes
        result.text_content = "test"
        result.status_code = 200
        result.fetch_time_ms = 100
        result.content_hash = "abc123"
        result.links_found = []
        result.is_spa_detected = False

        routing_decision = MagicMock()
        routing_decision.route.value = "fast"
        routing_decision.reason = "static_asset"

        # Should not raise UnicodeEncodeError
        entry = logger.log_fast_path(
            job_id="test-job",
            url="https://example.com",
            result=result,
            routing_decision=routing_decision,
            target_mode="fast"
        )
        assert entry is not None
        assert entry.bytes_transferred > 0

    def test_content_ratio_uses_original_html_length(self) -> None:
        """P1 Regression: Content ratio uses original HTML length, not truncated."""
        from unittest.mock import MagicMock
        from layer1_ingestion.crawler.quality_gate import QualityGate, QualityThresholds

        # Use a high threshold that would fail if using truncated length
        thresholds = QualityThresholds(min_content_ratio=0.5)
        gate = QualityGate(thresholds)

        # Create result with truncated HTML but large original
        result = MagicMock()
        result.text_content = "A" * 1000  # 1000 chars of text
        result.html = "A" * 1000          # Truncated to 1000 (ratio would be 1.0)
        result.original_html_length = 50000  # Originally 50000 (actual ratio 0.02)
        result.status_code = 200
        result.is_spa_detected = False
        result.fetch_time_ms = 100
        result.title = "Test"

        # Evaluate quality
        decision = gate.evaluate(result)

        # Should FAIL because actual ratio 0.02 < threshold 0.5
        # If code incorrectly used truncated length (ratio 1.0), it would PASS
        assert not decision.passed, "Quality gate should fail with low content ratio"
        assert decision.checks["content_ratio"] is False, "content_ratio check should fail"

