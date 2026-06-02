"""Tests for SmartRouter per-URL routing decisions.

Covers all 7 routing rules plus SPA detection and quality gate evaluation.
"""

from __future__ import annotations

import pytest

from layer1_ingestion.crawler.smart_router import (
    QualityDecision,
    RouteType,
    RoutingDecision,
    SmartRouter,
)


class TestRoutingRules:
    """Test the 7 cascading routing rules."""

    @pytest.fixture
    def router(self) -> SmartRouter:
        """Create a SmartRouter with default settings."""
        return SmartRouter()

    def test_decide_is_sync_function(self, router: SmartRouter) -> None:
        """P0 Regression: Verify decide() is synchronous (not async)."""
        import inspect

        assert not inspect.iscoroutinefunction(router.decide)
        # Should return immediately without event loop
        result = router.decide("https://example.com/page.html")
        assert isinstance(result, RoutingDecision)
        assert result.route == RouteType.FAST_WITH_FALLBACK

    @pytest.mark.parametrize("path,expected_route", [
        ("/wp-content/uploads/image.jpg", RouteType.FAST),  # Directory pattern
        ("/assets/js/app.js", RouteType.FAST),              # Directory pattern
        ("/static/css/style.css", RouteType.FAST),          # Directory pattern
        ("/page.html", RouteType.FAST_WITH_FALLBACK),       # File extension not in static list
        ("/app.js", RouteType.FAST),                        # JS extension is in static list
        ("/api/dynamic", RouteType.FAST_WITH_FALLBACK),    # Neither
    ])
    def test_static_pattern_matching(self, router: SmartRouter, path: str, expected_route: RouteType) -> None:
        """P1 Regression: Verify static asset patterns correctly route to FAST path."""
        decision = router.decide(f"https://example.com{path}")
        assert decision.route == expected_route, f"{path} should route to {expected_route}"

    def test_rule1_target_override_fast(self, router: SmartRouter) -> None:
        """Rule 1: Target mode FAST always routes to fast path."""
        decision = router.decide(
            "https://example.com/solutions/platform",
            target_mode=RouteType.FAST,
        )
        assert decision.route == RouteType.FAST
        assert decision.reason == "target_override_fast"

    def test_rule1_target_override_browser(self, router: SmartRouter) -> None:
        """Rule 1: Target mode BROWSER always routes to browser."""
        decision = router.decide(
            "https://example.com/sitemap.xml",
            target_mode=RouteType.BROWSER,
        )
        assert decision.route == RouteType.BROWSER
        assert decision.reason == "target_override_browser"
        assert decision.stagehand_config is not None

    def test_rule2_static_assets_css(self, router: SmartRouter) -> None:
        """Rule 2: CSS files always use fast path."""
        decision = router.decide(
            "https://example.com/assets/style.css",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.FAST
        assert decision.reason == "static_asset"
        assert decision.priority == 1  # Low priority for static assets

    def test_rule2_static_assets_js(self, router: SmartRouter) -> None:
        """Rule 2: JS files always use fast path."""
        decision = router.decide(
            "https://example.com/static/app.js",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.FAST

    def test_rule2_static_assets_wp_content(self, router: SmartRouter) -> None:
        """Rule 2: WordPress uploads use fast path."""
        decision = router.decide(
            "https://example.com/wp-content/uploads/image.png",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.FAST

    def test_rule3_sitemap_xml(self, router: SmartRouter) -> None:
        """Rule 3: Sitemap.xml uses fast path with high priority."""
        decision = router.decide(
            "https://example.com/sitemap.xml",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.FAST
        assert decision.reason == "sitemap"
        assert decision.priority == 10  # High priority

    def test_rule3_robots_txt(self, router: SmartRouter) -> None:
        """Rule 3: Robots.txt uses fast path."""
        decision = router.decide(
            "https://example.com/robots.txt",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.FAST

    def test_rule4_previous_crawl_browser(self, router: SmartRouter) -> None:
        """Rule 4: Previous browser crawl maintains consistency."""
        decision = router.decide(
            "https://example.com/page",
            target_mode=RouteType.FAST_WITH_FALLBACK,
            previous_route=RouteType.BROWSER,
        )
        assert decision.route == RouteType.BROWSER
        assert decision.reason == "previous_crawl_browser"

    def test_rule5_dynamic_platform(self, router: SmartRouter) -> None:
        """Rule 5: Platform pages route to browser."""
        decision = router.decide(
            "https://example.com/platform/ai-engine",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.BROWSER
        assert "known_dynamic_page" in decision.reason
        assert decision.stagehand_config is not None

    def test_rule5_dynamic_pricing(self, router: SmartRouter) -> None:
        """Rule 5: Pricing pages route to browser."""
        decision = router.decide(
            "https://example.com/pricing",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.BROWSER
        assert decision.priority == 8  # High priority

    def test_rule5_dynamic_solutions(self, router: SmartRouter) -> None:
        """Rule 5: Solutions pages route to browser."""
        decision = router.decide(
            "https://example.com/solutions/marketing",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.BROWSER

    def test_rule6_navigation_fragment(self, router: SmartRouter) -> None:
        """Rule 6: URLs with fragments route to browser."""
        decision = router.decide(
            "https://example.com/page#section",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.BROWSER
        assert decision.reason == "navigation_or_search"

    def test_rule6_navigation_query(self, router: SmartRouter) -> None:
        """Rule 6: URLs with query params route to browser."""
        decision = router.decide(
            "https://example.com/search?q=test",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.BROWSER

    def test_rule7_default_fallback(self, router: SmartRouter) -> None:
        """Rule 7: Default is FAST_WITH_FALLBACK."""
        decision = router.decide(
            "https://example.com/some-page",
            target_mode=RouteType.FAST_WITH_FALLBACK,
        )
        assert decision.route == RouteType.FAST_WITH_FALLBACK
        assert decision.reason == "default_with_fallback"
        assert decision.priority == 3  # Lower priority


class TestSPADetection:
    """Test SPA shell detection heuristics."""

    @pytest.fixture
    def router(self) -> SmartRouter:
        """Create a SmartRouter with default settings (threshold=2)."""
        return SmartRouter(spa_indicator_threshold=2)

    def test_detect_spa_empty_root(self, router: SmartRouter) -> None:
        """Detect SPA with empty root div."""
        html = '<html><body><div id="root"></div></body></html>'
        assert router.detect_spa(html) is True

    def test_detect_spa_react_marker(self, router: SmartRouter) -> None:
        """Detect SPA with root div marker."""
        html = '<html><body><div id="root"></div></body></html>'
        assert router.detect_spa(html) is True

    def test_detect_spa_high_script_density(self, router: SmartRouter) -> None:
        """Detect SPA with high script density plus empty root div."""
        html = """
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
        """
        assert router.detect_spa(html) is True

    def test_detect_spa_low_content_ratio(self, router: SmartRouter) -> None:
        """Detect SPA with low content-to-HTML ratio plus empty root div."""
        # HTML with lots of markup, little text
        html = "<html><body><div id=\"root\"></div>" + "<div><span>" * 100 + "Some text" + "</span></div>" * 100 + "</body></html>"
        assert router.detect_spa(html) is True

    def test_detect_not_spa_static_page(self, router: SmartRouter) -> None:
        """Static page is not detected as SPA."""
        html = """
        <html>
            <body>
                <h1>Full Page Title</h1>
                <p>Lots of content here. This is a paragraph with meaningful text.
                It continues with more information about the topic at hand.</p>
                <script src="app.js"></script>
            </body>
        </html>
        """
        assert router.detect_spa(html) is False

    def test_detect_not_spa_empty_html(self, router: SmartRouter) -> None:
        """Empty HTML is not detected as SPA."""
        assert router.detect_spa("") is False

    def test_detect_spa_multiple_indicators(self, router: SmartRouter) -> None:
        """SPA with multiple indicators triggers detection."""
        html = """
        <html>
            <head>
                <script src="1.js"></script>
                <script src="2.js"></script>
                <script src="3.js"></script>
                <script src="4.js"></script>
                <script src="5.js"></script>
                <script src="6.js"></script>
                <script src="7.js"></script>
            </head>
            <body>
                <div id="app"></div>
            </body>
        </html>
        """
        assert router.detect_spa(html) is True


class TestQualityGate:
    """Test quality gate evaluation for fast path results."""

    @pytest.fixture
    def router(self) -> SmartRouter:
        """Create a SmartRouter with default quality thresholds."""
        return SmartRouter(min_text_length=500, min_content_ratio=0.02)

    def test_quality_pass(self, router: SmartRouter) -> None:
        """Quality passes with good content."""
        html = "<html>" + "<p>Content paragraph</p>" * 100 + "</html>"
        text = "Content paragraph " * 100

        result = router.evaluate_quality(text, html, 200, spa_detected=False)

        assert result.passed is True
        assert all(result.checks.values())
        assert result.fallback_reason is None

    def test_quality_fail_short_text(self, router: SmartRouter) -> None:
        """Quality fails with short text."""
        result = router.evaluate_quality(
            "Short text", "<html>Short text</html>", 200, spa_detected=False
        )

        assert result.passed is False
        assert result.checks["text_length"] is False
        assert result.fallback_reason == "text_length"

    def test_quality_fail_spa_detected(self, router: SmartRouter) -> None:
        """Quality fails when SPA detected."""
        html = "<html>" + "<p>Content</p>" * 100 + "</html>"
        text = "Content " * 100

        result = router.evaluate_quality(text, html, 200, spa_detected=True)

        assert result.passed is False
        assert result.checks["no_spa"] is False
        assert result.fallback_reason == "no_spa"

    def test_quality_fail_status_code(self, router: SmartRouter) -> None:
        """Quality fails with non-200 status."""
        html = "<html>" + "<p>Content</p>" * 100 + "</html>"
        text = "Content " * 100

        result = router.evaluate_quality(text, html, 404, spa_detected=False)

        assert result.passed is False
        assert result.checks["success_status"] is False

    def test_quality_fail_low_ratio(self, router: SmartRouter) -> None:
        """Quality fails with low content ratio."""
        # Lots of HTML, little text
        html = "<html>" + "<div class='wrapper'><span>" * 200 + "Text" + "</span></div>" * 200 + "</html>"
        text = "Text"

        result = router.evaluate_quality(text, html, 200, spa_detected=False)

        assert result.passed is False
        assert result.checks["content_ratio"] is False


class TestPageTypeInference:
    """Test page type detection from URL patterns."""

    @pytest.fixture
    def router(self) -> SmartRouter:
        return SmartRouter()

    def test_infer_product(self, router: SmartRouter) -> None:
        """Detect product pages."""
        assert router._infer_page_type("/platform/ai-engine") == "PRODUCT"
        assert router._infer_page_type("/products/sales-suite") == "PRODUCT"

    def test_infer_pricing(self, router: SmartRouter) -> None:
        """Detect pricing pages."""
        assert router._infer_page_type("/pricing") == "PRICING"

    def test_infer_customer_story(self, router: SmartRouter) -> None:
        """Detect customer story pages."""
        assert router._infer_page_type("/customer-stories/acme") == "CUSTOMER_STORY"

    def test_infer_resource_center(self, router: SmartRouter) -> None:
        """Detect resource center pages."""
        assert router._infer_page_type("/blog/post-1") == "RESOURCE_CENTER"
        assert router._infer_page_type("/resources/guides") == "RESOURCE_CENTER"

    def test_infer_unknown(self, router: SmartRouter) -> None:
        """Default to unknown for unrecognized paths."""
        assert router._infer_page_type("/random-page") == "UNKNOWN"


class TestPriorityAssignment:
    """Test priority levels for different page types."""

    @pytest.fixture
    def router(self) -> SmartRouter:
        return SmartRouter()

    def test_priority_product_highest(self, router: SmartRouter) -> None:
        """Product pages get highest priority."""
        assert router._priority_for_page_type("PRODUCT") == 10

    def test_priority_homepage_high(self, router: SmartRouter) -> None:
        """Homepage gets high priority."""
        assert router._priority_for_page_type("HOMEPAGE") == 9

    def test_priority_pricing_trust_high(self, router: SmartRouter) -> None:
        """Pricing and trust get high priority."""
        assert router._priority_for_page_type("PRICING") == 8
        assert router._priority_for_page_type("TRUST") == 8

    def test_priority_resource_low(self, router: SmartRouter) -> None:
        """Resource center gets lower priority."""
        assert router._priority_for_page_type("RESOURCE_CENTER") == 3

    def test_priority_unknown_default(self, router: SmartRouter) -> None:
        """Unknown pages get default priority."""
        assert router._priority_for_page_type("UNKNOWN") == 2
        assert router._priority_for_page_type("RANDOM_TYPE") == 3


class TestBrowserConfig:
    """Test browser configuration generation."""

    @pytest.fixture
    def router(self) -> SmartRouter:
        return SmartRouter()

    def test_config_product_includes_observe(self, router: SmartRouter) -> None:
        """Product config includes observe_first flag."""
        config = router._browser_config_for("PRODUCT")
        assert config["observe_first"] is True
        assert config["timeout"] == 60000

    def test_config_pricing_shorter_timeout(self, router: SmartRouter) -> None:
        """Pricing uses shorter timeout."""
        config = router._browser_config_for("PRICING")
        assert config["timeout"] == 30000
        assert config["scroll_percent"] == 80

    def test_config_unknown_uses_defaults(self, router: SmartRouter) -> None:
        """Unknown page type gets default config."""
        config = router._browser_config_for("UNKNOWN")
        assert config["timeout"] == 30000
        assert config["scroll_percent"] == 50

    def test_default_config_structure(self, router: SmartRouter) -> None:
        """Default config has required fields."""
        config = router._default_browser_config()
        assert "scroll_percent" in config
        assert "wait_for" in config
        assert "timeout" in config

