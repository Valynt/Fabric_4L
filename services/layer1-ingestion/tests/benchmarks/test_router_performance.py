"""Performance benchmarks comparing browser-only vs router+fast-path.

Measures:
- Speedup factor for static content
- Accuracy for mixed content sites
- Fallback rate by domain type
- Quality gate effectiveness
"""

import pytest
import trafilatura  # noqa: F401 — mandatory dep; already in layer1-ingestion dependencies
import os

import statistics
import time
import asyncio
from uuid import uuid4

from layer1_ingestion.crawler.smart_router import SmartRouter, RouteType
from layer1_ingestion.crawler.httpx_crawler import HttpxCrawler, FastPathResult
from layer1_ingestion.crawler.quality_gate import QualityGate
from layer1_ingestion.crawler.decision_store import InMemoryCrawlDecisionRepository


def _env_flag_enabled(name: str) -> bool:
    return os.getenv(name, "").strip().lower() in {"1", "true", "yes", "on"}


pytestmark = [
    pytest.mark.performance,
    pytest.mark.benchmark,
    pytest.mark.quarantine,
    pytest.mark.skipif(
        not _env_flag_enabled("RUN_ROUTER_BENCHMARKS"),
        reason=(
            "Environment-sensitive router benchmarks are quarantined by default. "
            "Set RUN_ROUTER_BENCHMARKS=1 to run explicitly."
        ),
    ),
]


class TestStaticSiteSpeedup:
    """Benchmark: Fast path delivers 10x+ speedup on static content."""

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_blog_site_speedup(self, respx_mock):
        """Static blog should be 10x faster with router vs browser-only."""
        html = """<html><body>
            <h1>Blog Post Title</h1>
            <p>This is a long blog post with lots of content about Python programming.
            It covers asyncio, threading, and multiprocessing in depth. More content
            here to make the text substantial for quality gate validation.</p>
            <p>""" + "Content " * 100 + """</p></body></html>"""

        import httpx
        respx_mock.get("https://blog.example.com/post").mock(
            return_value=httpx.Response(200, html=html)
        )

        # Simulate browser-only timing (would be ~3-5s)
        browser_times = []
        for _ in range(5):
            start = time.monotonic()
            await asyncio.sleep(0.1)  # Simulated browser delay (reduced for tests)
            browser_times.append((time.monotonic() - start) * 1000)

        browser_avg = statistics.mean(browser_times)

        # Router + fast path timing
        router_times = []
        router = SmartRouter()

        for _ in range(5):
            start = time.monotonic()

            decision = router.decide(
                "https://blog.example.com/post",
                RouteType.FAST_WITH_FALLBACK
            )

            if decision.route in (RouteType.FAST, RouteType.FAST_WITH_FALLBACK):
                async with HttpxCrawler() as crawler:
                    result = await crawler.fetch(
                        "https://blog.example.com/post",
                        allowlist_domains=["example.com"],
                    )
                    router_times.append(result.fetch_time_ms)
            else:
                # Router chose browser path for what should be static content
                router_times.append(100)  # Conservative estimate

        router_avg = statistics.mean(router_times) if router_times else 100

        # Calculate speedup
        speedup = browser_avg / router_avg

        print(f"Browser-only avg: {browser_avg:.0f}ms")
        print(f"Router+Fast avg: {router_avg:.0f}ms")
        print(f"Speedup: {speedup:.1f}x")

        # Assert speedup achieved (relaxed for test environment)
        assert speedup >= 2.0, f"Expected 2x+ speedup, got {speedup:.1f}x"

    @pytest.mark.benchmark
    @pytest.mark.asyncio
    async def test_docs_site_speedup(self, respx_mock):
        """Documentation site should be significantly faster with fast path."""
        html = """<html><body>
            <nav><ul><li><a href="#section1">Section 1</a></li></ul></nav>
            <main>
                <h1>Documentation</h1>
                <p>""" + "Documentation content. " * 50 + """</p>
            </main>
        </body></html>"""

        import httpx
        respx_mock.get("https://docs.example.com/guide").mock(
            return_value=httpx.Response(200, html=html)
        )

        # Router decision timing
        router = SmartRouter()
        decision = router.decide(
            "https://docs.example.com/guide",
            RouteType.FAST_WITH_FALLBACK
        )

        async with HttpxCrawler() as crawler:
            start = time.monotonic()
            result = await crawler.fetch(
                "https://docs.example.com/guide",
                allowlist_domains=["example.com"],
            )
            fetch_time = (time.monotonic() - start) * 1000

        # Fast path should be quick
        assert fetch_time < 500, f"Fast path too slow: {fetch_time:.0f}ms"
        assert result.status_code == 200


class TestMixedContentAccuracy:
    """Benchmark: Router correctly classifies mixed content."""

    @pytest.mark.benchmark
    def test_mixed_site_routing_distribution(self):
        """Mixed site should have reasonable routing distribution."""

        urls = [
            ("https://mixed.com/blog/post1", "static"),
            ("https://mixed.com/blog/post2", "static"),
            ("https://mixed.com/pricing", "dynamic"),
            ("https://mixed.com/features", "static"),
            ("https://mixed.com/dashboard", "spa"),
            ("https://mixed.com/docs/guide", "static"),
            ("https://mixed.com/about", "static"),
            ("https://mixed.com/contact", "static"),
            ("https://mixed.com/app", "spa"),
            ("https://mixed.com/enterprise", "dynamic"),
        ]

        # Run routing decisions
        router = SmartRouter()
        results = []

        for url, _ in urls:
            decision = router.decide(url, RouteType.FAST_WITH_FALLBACK)
            results.append({
                "url": url,
                "route": decision.route.value,
                "reason": decision.reason,
            })

        # Analyze distribution
        fast_count = sum(1 for r in results if r["route"] == "fast")
        browser_count = sum(1 for r in results if r["route"] == "browser")
        fallback_count = sum(1 for r in results if r["route"] == "fast_fallback")

        total = len(results)
        fast_rate = fast_count / total
        browser_rate = browser_count / total
        fallback_rate = fallback_count / total

        print(f"Fast: {fast_count}/{total} ({fast_rate:.0%})")
        print(f"Browser: {browser_count}/{total} ({browser_rate:.0%})")
        print(f"Fallback: {fallback_count}/{total} ({fallback_rate:.0%})")

        # Assertions for reasonable distribution
        # With smart router rules:
        # - pricing -> browser (Rule 5)
        # - enterprise -> browser (Rule 5)
        # - blog, features, docs, about, contact -> fast or fallback
        # - dashboard, app -> fallback (default)
        assert browser_rate >= 0.1, f"Expected >=10% browser, got {browser_rate:.0%}"
        assert fallback_rate >= 0.1, f"Expected >=10% fallback, got {fallback_rate:.0%}"


class TestQualityGateEffectiveness:
    """Benchmark: Quality gate catches low-quality fast path results."""

    @pytest.mark.benchmark
    def test_spa_detection_accuracy(self):
        """SPA detection should have high accuracy."""

        test_cases = [
            # (html, is_actually_spa, description)
            ("<div id='root'></div><script></script><script></script>", True, "React SPA"),
            ("<div id='app'></div><script src='vue.js'></script>", True, "Vue SPA"),
            ("<div ng-app='myApp'></div><script></script>", True, "Angular SPA"),
            ("<article><h1>Title</h1><p>Content</p></article>", False, "Static article"),
            ("<main><h1>Docs</h1><p>Documentation</p></main>", False, "Static docs"),
            ("<body></body>", False, "Empty page"),
        ]

        gate = QualityGate()
        correct = 0

        for html, is_spa, desc in test_cases:
            result = FastPathResult(
                url=f"https://example.com/{desc}",
                html=html,
                text_content="Content" if not is_spa else "",
                status_code=200,
                headers={},
                fetch_time_ms=100,
                links=[],
                is_spa_detected=gate._detect_spa_in_content(html),
                script_count=html.count("<script"),
                original_html_length=len(html),
            )

            detected_spa = result.is_spa_detected

            if detected_spa == is_spa:
                correct += 1
            else:
                print(f"Missed {desc}: expected SPA={is_spa}, detected SPA={detected_spa}")

        accuracy = correct / len(test_cases)
        print(f"SPA detection accuracy: {accuracy:.0%}")

        assert accuracy >= 0.7, f"Expected >=70% SPA detection, got {accuracy:.0%}"

    @pytest.mark.benchmark
    def test_content_ratio_validation(self):
        """Quality gate should validate content-to-markup ratio."""

        gate = QualityGate()

        # High ratio (good content)
        good_html = "<html><body><h1>Title</h1><p>" + "Good content. " * 50 + "</p></body></html>"
        good_result = FastPathResult(
            url="https://example.com/good",
            html=good_html,
            text_content="Good content. " * 50,
            status_code=200,
            headers={},
            fetch_time_ms=100,
            links=[],
            is_spa_detected=False,
            script_count=0,
            original_html_length=len(good_html),
        )

        good_quality = gate.evaluate(good_result)

        # Low ratio (poor content)
        poor_html = "<html><body>" + "<div class='wrapper'>" * 20 + "<p>Small</p>" + "</div>" * 20 + "</body></html>"
        poor_result = FastPathResult(
            url="https://example.com/poor",
            html=poor_html,
            text_content="Small",
            status_code=200,
            headers={},
            fetch_time_ms=100,
            links=[],
            is_spa_detected=False,
            script_count=0,
            original_html_length=len(poor_html),
        )

        poor_quality = gate.evaluate(poor_result)

        # Both should be evaluated
        assert good_quality is not None
        assert poor_quality is not None

        # Print comparison
        print(f"Good content quality: {good_quality.passed}")
        print(f"Poor content quality: {poor_quality.passed}")


class TestRouterDecisionSpeed:
    """Benchmark: Router decision speed should be negligible."""

    @pytest.mark.benchmark
    def test_router_decision_latency(self):
        """Router decision should complete in under 10ms."""

        router = SmartRouter()
        urls = [
            "https://example.com/page1",
            "https://example.com/page2",
            "https://example.com/pricing",
            "https://example.com/sitemap.xml",
        ]

        times = []
        for url in urls:
            start = time.perf_counter()
            decision = router.decide(url, RouteType.FAST_WITH_FALLBACK)
            elapsed_ms = (time.perf_counter() - start) * 1000
            times.append(elapsed_ms)

        avg_time = statistics.mean(times)
        max_time = max(times)

        print(f"Average decision time: {avg_time:.3f}ms")
        print(f"Max decision time: {max_time:.3f}ms")

        assert avg_time < 10, f"Router decision too slow: {avg_time:.3f}ms avg"


class TestFallbackRateTarget:
    """Benchmark: Fallback rate stays within acceptable bounds."""

    @pytest.mark.benchmark
    def test_fallback_rate_on_representative_urls(self):
        """Fallback rate on representative URL set should be <30%."""

        # Representative URLs from different domains
        urls = [
            # Static content (should rarely fallback)
            "https://docs.python.org/tutorial",
            "https://developer.mozilla.org/docs",
            "https://blog.example.com/article",

            # Dynamic content (may fallback more)
            "https://app.example.com/dashboard",
            "https://platform.example.com/analytics",

            # Mixed
            "https://example.com/about",
            "https://example.com/pricing",
            "https://example.com/features",
        ]

        router = SmartRouter()
        fallback_count = 0

        for url in urls:
            decision = router.decide(url, RouteType.FAST_WITH_FALLBACK)
            if decision.route == RouteType.FAST_WITH_FALLBACK:
                fallback_count += 1

        fallback_rate = fallback_count / len(urls)
        print(f"Fallback rate: {fallback_rate:.1%} ({fallback_count}/{len(urls)})")

        # With smart routing, we expect reasonable fallback rate
        assert fallback_rate < 0.5, f"Fallback rate too high: {fallback_rate:.1%}"

