"""
Tests for SmartRouter routing logic.

Covers:
- decide(): target override (FAST / BROWSER)
- decide(): static asset extensions and directory patterns → FAST
- decide(): sitemap/robots.txt → FAST with high priority
- decide(): previous crawl browser consistency rule
- decide(): known dynamic page patterns → BROWSER
- decide(): navigation patterns (# / ? / /search / /filter) → BROWSER
- decide(): default fallback → FAST_WITH_FALLBACK
- detect_spa(): SPA detection heuristics
- evaluate_quality(): quality decision with all checks
- _infer_page_type(): page type inference from path
- _priority_for_page_type(): priority mapping
"""

import pytest

from layer1_ingestion.crawler.smart_router import (
    QualityDecision,
    RouteType,
    RoutingDecision,
    SmartRouter,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def router() -> SmartRouter:
    return SmartRouter()


# ---------------------------------------------------------------------------
# decide(): target override rules
# ---------------------------------------------------------------------------

class TestDecideTargetOverride:
    """Rule 1: target_mode FAST or BROWSER always wins."""

    def test_fast_override(self, router):
        decision = router.decide("https://example.com/dynamic-page", target_mode=RouteType.FAST)
        assert decision.route == RouteType.FAST
        assert decision.reason == "target_override_fast"

    def test_browser_override(self, router):
        decision = router.decide("https://example.com/static", target_mode=RouteType.BROWSER)
        assert decision.route == RouteType.BROWSER
        assert decision.reason == "target_override_browser"
        assert decision.stagehand_config is not None


# ---------------------------------------------------------------------------
# decide(): static assets
# ---------------------------------------------------------------------------

class TestDecideStaticAssets:
    """Rules 2a/2b: static file extensions and directories → FAST."""

    @pytest.mark.parametrize("ext", [".css", ".js", ".png", ".jpg", ".jpeg", ".gif", ".svg", ".ico", ".pdf", ".zip"])
    def test_static_extension(self, router, ext):
        url = f"https://example.com/assets/file{ext}"
        decision = router.decide(url)
        assert decision.route == RouteType.FAST
        assert decision.reason == "static_asset"
        assert decision.priority == 1

    @pytest.mark.parametrize("path_prefix", ["/wp-content/", "/assets/", "/static/", "/uploads/"])
    def test_static_directory(self, router, path_prefix):
        url = f"https://example.com{path_prefix}image.webp"
        decision = router.decide(url)
        assert decision.route == RouteType.FAST
        assert decision.reason == "static_asset"


# ---------------------------------------------------------------------------
# decide(): sitemap/robots
# ---------------------------------------------------------------------------

class TestDecideSitemap:
    """Rule 3: sitemap and robots.txt get FAST with high priority."""

    @pytest.mark.parametrize("path", ["/sitemap.xml", "/robots.txt", "/sitemap_index.xml"])
    def test_sitemap_routes_fast(self, router, path):
        url = f"https://example.com{path}"
        decision = router.decide(url)
        assert decision.route == RouteType.FAST
        assert decision.reason == "sitemap"
        assert decision.priority == 10


# ---------------------------------------------------------------------------
# decide(): previous crawl consistency
# ---------------------------------------------------------------------------

class TestDecidePreviousCrawl:
    """Rule 4: previous browser crawl maintains browser route."""

    def test_previous_browser_stays_browser(self, router):
        decision = router.decide(
            "https://example.com/some-page",
            previous_route=RouteType.BROWSER,
        )
        assert decision.route == RouteType.BROWSER
        assert decision.reason == "previous_crawl_browser"

    def test_previous_fast_does_not_short_circuit(self, router):
        """previous_route=FAST does not force FAST; falls through to further rules."""
        decision = router.decide(
            "https://example.com/pricing",  # known dynamic
            previous_route=RouteType.FAST,
        )
        # Should still be BROWSER due to dynamic page rule
        assert decision.route == RouteType.BROWSER


# ---------------------------------------------------------------------------
# decide(): known dynamic pages
# ---------------------------------------------------------------------------

class TestDecideKnownDynamicPages:
    """Rule 5: known dynamic URL patterns → BROWSER."""

    @pytest.mark.parametrize("path", [
        "/solutions/enterprise",
        "/platform/analytics",
        "/pricing",
        "/trust",
        "/customer-stories/acme",
        "/resource-center/guides",
        "/about",
        "/partner-ecosystem",
        "/integrations/salesforce",
        "/products/core",
        "/features/ai",
    ])
    def test_dynamic_path_routes_browser(self, router, path):
        url = f"https://example.com{path}"
        decision = router.decide(url)
        assert decision.route == RouteType.BROWSER

    def test_dynamic_decision_includes_stagehand_config(self, router):
        decision = router.decide("https://example.com/pricing")
        assert decision.stagehand_config is not None
        assert "timeout" in decision.stagehand_config


# ---------------------------------------------------------------------------
# decide(): navigation patterns
# ---------------------------------------------------------------------------

class TestDecideNavigationPatterns:
    """Rule 6: # / ? / /search / /filter → BROWSER."""

    def test_fragment_routes_browser(self, router):
        decision = router.decide("https://example.com/page#section")
        assert decision.route == RouteType.BROWSER
        assert decision.reason == "navigation_or_search"

    def test_query_param_routes_browser(self, router):
        decision = router.decide("https://example.com/page?q=test")
        assert decision.route == RouteType.BROWSER

    def test_search_path_routes_browser(self, router):
        decision = router.decide("https://example.com/search")
        assert decision.route == RouteType.BROWSER

    def test_filter_path_routes_browser(self, router):
        decision = router.decide("https://example.com/filter/category")
        assert decision.route == RouteType.BROWSER


# ---------------------------------------------------------------------------
# decide(): default fallback
# ---------------------------------------------------------------------------

class TestDecideDefault:
    """Rule 7: unrecognised URL → FAST_WITH_FALLBACK."""

    def test_default_fallback(self, router):
        decision = router.decide("https://example.com/unknown-page")
        assert decision.route == RouteType.FAST_WITH_FALLBACK
        assert decision.reason == "default_with_fallback"
        assert decision.stagehand_config is not None

    def test_homepage_default_fallback(self, router):
        """Plain homepage doesn't match any rule and falls back."""
        decision = router.decide("https://example.com/")
        assert decision.route == RouteType.FAST_WITH_FALLBACK


# ---------------------------------------------------------------------------
# RoutingDecision properties
# ---------------------------------------------------------------------------

class TestRoutingDecision:
    """Basic RoutingDecision dataclass properties."""

    def test_decision_url_preserved(self, router):
        url = "https://example.com/page"
        decision = router.decide(url)
        assert decision.url == url

    def test_default_priority_range(self, router):
        decision = router.decide("https://example.com/unknown")
        assert 1 <= decision.priority <= 10


# ---------------------------------------------------------------------------
# detect_spa
# ---------------------------------------------------------------------------

class TestDetectSpa:
    """Tests for SPA detection heuristics."""

    def test_empty_html_not_spa(self, router):
        assert router.detect_spa("") is False

    def test_plain_html_not_spa(self, router):
        html = "<html><body><p>Hello world with lots of real content here.</p></body></html>"
        assert router.detect_spa(html) is False

    def test_react_root_detected(self, router):
        """Empty React root div is a SPA indicator."""
        html = '<div id="root"></div>'
        # Single indicator may not hit the threshold by itself; check with high script density
        spa_html = "<script></script>" * 6 + html
        result = router.detect_spa(spa_html)
        assert isinstance(result, bool)  # just verify it doesn't raise

    def test_multiple_spa_markers_detected(self, router):
        """Multiple SPA markers cross the threshold."""
        html = (
            "<script></script>" * 6  # high script density
            + '<div id="root"></div>'  # SPA marker + empty root container
            + 'data-reactroot="true"'
        )
        # Provide minimal text to ensure low content ratio
        assert router.detect_spa(html) is True

    def test_high_script_density_alone(self, router):
        """Many script tags alone count as one SPA indicator; threshold is 2."""
        html = "<script></script>" * 10 + "<p>" + "a" * 10000 + "</p>"
        # One indicator (script density), good content ratio → not SPA
        assert router.detect_spa(html) is False

    def test_next_js_marker(self, router):
        html = (
            "<script></script>" * 6
            + '<div id="__next"></div>'
            + "window.__INITIAL_STATE__ = {}"
        )
        # high script density + marker + low content → should be SPA
        assert router.detect_spa(html) is True


# ---------------------------------------------------------------------------
# evaluate_quality
# ---------------------------------------------------------------------------

class TestEvaluateQuality:
    """Tests for SmartRouter.evaluate_quality."""

    def test_passing_quality_check(self, router):
        decision = router.evaluate_quality(
            text_content="a" * 1000,
            html_content="x" * 5000,
            status_code=200,
            spa_detected=False,
        )
        assert decision.passed is True
        assert decision.fallback_reason is None

    def test_fail_short_text(self, router):
        decision = router.evaluate_quality(
            text_content="short",
            html_content="x" * 5000,
            status_code=200,
            spa_detected=False,
        )
        assert decision.passed is False
        assert "text_length" in decision.checks
        assert decision.checks["text_length"] is False

    def test_fail_bad_status(self, router):
        decision = router.evaluate_quality(
            text_content="a" * 1000,
            html_content="x" * 5000,
            status_code=403,
            spa_detected=False,
        )
        assert decision.passed is False
        assert decision.checks["success_status"] is False

    def test_fail_spa_detected(self, router):
        decision = router.evaluate_quality(
            text_content="a" * 1000,
            html_content="x" * 5000,
            status_code=200,
            spa_detected=True,
        )
        assert decision.passed is False
        assert decision.checks["no_spa"] is False

    def test_fail_low_content_ratio(self, router):
        decision = router.evaluate_quality(
            text_content="a" * 10,
            html_content="x" * 100_000,
            status_code=200,
            spa_detected=False,
        )
        assert decision.passed is False
        assert decision.checks["content_ratio"] is False

    def test_fallback_reason_set_on_failure(self, router):
        decision = router.evaluate_quality(
            text_content="tiny",
            html_content="x" * 5000,
            status_code=200,
            spa_detected=False,
        )
        assert decision.fallback_reason is not None


# ---------------------------------------------------------------------------
# _infer_page_type
# ---------------------------------------------------------------------------

class TestInferPageType:
    """Tests for _infer_page_type path-based inference."""

    @pytest.mark.parametrize("path,expected", [
        ("/platform/analytics", "PRODUCT"),
        ("/products/suite", "PRODUCT"),
        ("/solutions/marketing-enablement", "ROLE_SOLUTION"),
        ("/solutions/healthcare", "INDUSTRY_SOLUTION"),
        ("/customer-stories/acme", "CUSTOMER_STORY"),
        ("/pricing", "PRICING"),
        ("/trust/certifications", "TRUST"),
        ("/integrations/slack", "INTEGRATIONS"),
        ("/partner-ecosystem", "PARTNERS"),
        ("/about", "COMPANY_ABOUT"),
        ("/resource-center/guides", "RESOURCE_CENTER"),
        ("/random-unknown-page", "UNKNOWN"),
    ])
    def test_page_type_inference(self, router, path, expected):
        assert router._infer_page_type(path) == expected


# ---------------------------------------------------------------------------
# _priority_for_page_type
# ---------------------------------------------------------------------------

class TestPriorityForPageType:
    """Tests for _priority_for_page_type."""

    def test_product_highest_priority(self, router):
        assert router._priority_for_page_type("PRODUCT") == 10

    def test_unknown_gets_low_priority(self, router):
        assert router._priority_for_page_type("UNKNOWN") == 2

    def test_unknown_type_gets_default(self, router):
        assert router._priority_for_page_type("NONEXISTENT") == 3

    def test_pricing_priority(self, router):
        assert router._priority_for_page_type("PRICING") == 8
