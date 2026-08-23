from __future__ import annotations

"""Smart Router for hybrid HTTPX/Browser ingestion path selection.

Provides per-URL routing decisions based on deterministic rules with
SPA detection and quality-gated fallback support.
"""


import re
from dataclasses import dataclass
from enum import Enum
from typing import Any
from urllib.parse import urlparse

from value_fabric.shared.models.typed_dict import TypedDictModel

# Precompiled regexes (compiled once at import instead of per-call).
_TAG_RE = re.compile(r"<[^>]+>")
_EMPTY_ROOT_RE = re.compile(
    r'<div\s+id=["\']root["\']\s*>\s*</div>', re.IGNORECASE
)


class SmartRouter__default_browser_configResult(TypedDictModel):
    scroll_percent: int
    timeout: int
    wait_for: str


class RouteType(str, Enum):
    """Available ingestion paths."""

    FAST = "fast"  # HTTPX static fetch
    BROWSER = "browser"  # Playwright browser automation
    FAST_WITH_FALLBACK = "fast_fallback"  # Try fast, fall back to browser


@dataclass(frozen=True)
class RoutingDecision:
    """Result of a routing decision for a URL."""

    url: str
    route: RouteType
    reason: str
    priority: int = 5  # 1-10, higher = scrape first
    stagehand_config: dict[str, Any] | None = None


@dataclass(frozen=True)
class QualityDecision:
    """Result of quality gate evaluation."""

    passed: bool
    checks: dict[str, bool]
    fallback_reason: str | None = None


class SmartRouter:
    """Cascading rule engine for FAST vs BROWSER path selection.

    Implements 7 deterministic rules for per-URL routing decisions:
    1. Target-level override (FAST or BROWSER mode)
    2. Static assets (always FAST)
    3. URL patterns indicating dynamic content
    4. SPA shell detection
    5. Previous crawl path consistency
    6. Query params/fragments (BROWSER)
    7. Default with fallback option
    """

    # Patterns that strongly indicate dynamic content
    DYNAMIC_PATTERNS = (
        "/solutions/",
        "/platform/",
        "/pricing",
        "/trust",
        "/customer-stories",
        "/resource-center",
        "/about",
        "/partner-ecosystem",
        "/integrations",
        "/products/",
        "/features/",
    )

    # Static asset extensions (always fast). Tuple so `str.endswith` uses the
    # C-level fast path instead of a Python-side scan.
    STATIC_EXTENSIONS = (
        ".css",
        ".js",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".svg",
        ".ico",
        ".pdf",
        ".zip",
    )

    STATIC_PATH_PATTERNS = (
        "/wp-content/",
        "/assets/",
        "/static/",
        "/uploads/",
    )

    # URL patterns that need browser navigation
    NAVIGATION_PATTERNS = ("#", "?", "/search", "/filter")

    # SPA detection markers (lightweight heuristic); frozenset for O(1) scans
    SPA_MARKERS = frozenset(
        {
            '<div id="root"></div>',
            '<div id="app"></div>',
            '<div id="__next"></div>',
            "data-reactroot",
            "ng-version=",
            'data-server-rendered="false"',
            "window.__INITIAL_STATE__",
        }
    )

    # Sitemap/robots patterns (always fast)
    SITEMAP_PATTERNS = ("/sitemap.xml", "/robots.txt", "/sitemap_index.xml")

    def __init__(
        self,
        spa_indicator_threshold: int = 2,
        min_text_length: int = 500,
        min_content_ratio: float = 0.02,
    ):
        """Initialize SmartRouter with configurable thresholds.

        Args:
            spa_indicator_threshold: Number of SPA markers to trigger SPA detection
            min_text_length: Minimum text length for quality gate
            min_content_ratio: Minimum ratio of text to HTML for quality gate
        """
        self.spa_threshold = spa_indicator_threshold
        self.min_text_length = min_text_length
        self.min_content_ratio = min_content_ratio

    def decide(
        self,
        url: str,
        target_mode: RouteType = RouteType.FAST_WITH_FALLBACK,
        previous_route: RouteType | None = None,
    ) -> RoutingDecision:
        """Make routing decision using cascading rules.

        Args:
            url: The URL to route
            target_mode: The target-level default mode
            previous_route: Previous crawl route for this URL (if any)

        Returns:
            RoutingDecision with selected path and reason
        """
        parsed = urlparse(url)
        path = parsed.path.lower()

        # Rule 1: Target-level override
        if target_mode == RouteType.FAST:
            return RoutingDecision(
                url=url,
                route=RouteType.FAST,
                reason="target_override_fast",
                priority=5,
            )

        if target_mode == RouteType.BROWSER:
            return RoutingDecision(
                url=url,
                route=RouteType.BROWSER,
                reason="target_override_browser",
                priority=5,
                stagehand_config=self._default_browser_config(),
            )

        # Rule 2: Static file extensions -> FAST
        if any(path.endswith(ext) for ext in self.STATIC_EXTENSIONS):
            return RoutingDecision(
                url=url,
                route=RouteType.FAST,
                reason="static_asset",
                priority=1,
            )

        # Rule 2b: Static asset directories -> FAST
        if any(pattern in path for pattern in self.STATIC_PATH_PATTERNS):
            return RoutingDecision(
                url=url,
                route=RouteType.FAST,
                reason="static_asset",
                priority=1,
            )

        # Rule 3: Sitemap / robots.txt -> FAST
        if path in self.SITEMAP_PATTERNS:
            return RoutingDecision(
                url=url,
                route=RouteType.FAST,
                reason="robots" if path == "/robots.txt" else "sitemap",
                priority=10,
            )

        # Rule 4: Previous crawl used browser -> same path (consistency)
        if previous_route == RouteType.BROWSER:
            return RoutingDecision(
                url=url,
                route=RouteType.BROWSER,
                reason="previous_crawl_browser",
                priority=5,
                stagehand_config=self._default_browser_config(),
            )

        # Rule 5: Known dynamic pages -> BROWSER
        if any(pattern in path for pattern in self.DYNAMIC_PATTERNS):
            page_type = self._infer_page_type(path)
            return RoutingDecision(
                url=url,
                route=RouteType.BROWSER,
                reason=f"known_dynamic_page:{page_type}",
                priority=self._priority_for_page_type(page_type),
                stagehand_config=self._browser_config_for(page_type),
            )

        # Rule 6: URLs with fragments or query params -> BROWSER
        if any(pattern in url for pattern in self.NAVIGATION_PATTERNS):
            return RoutingDecision(
                url=url,
                route=RouteType.BROWSER,
                reason="navigation_or_search",
                priority=4,
                stagehand_config=self._default_browser_config(),
            )

        # Rule 7: Default -> FAST with browser fallback option
        return RoutingDecision(
            url=url,
            route=RouteType.FAST_WITH_FALLBACK,
            reason="default_with_fallback",
            priority=3,
            stagehand_config=self._default_browser_config(),
        )

    def detect_spa(self, html: str) -> bool:
        """Detect if HTML appears to be a JS-rendered SPA shell.

        Uses lightweight heuristics (not perfect, but fast):
        - High script tag density (>5 scripts)
        - Low content-to-HTML ratio
        - Presence of common SPA markers

        Args:
            html: Raw HTML content

        Returns:
            True if SPA shell detected, False otherwise
        """
        if not html:
            return False

        html_lower = html.lower()

        # Indicator 1: High script density
        script_count = html_lower.count("<script")
        high_script_density = script_count > 5

        # Indicator 2: Low content ratio (rough heuristic)
        # Strip tags and check text length
        text_content = _TAG_RE.sub("", html)
        content_ratio = len(text_content) / max(len(html), 1)
        low_content = content_ratio < self.min_content_ratio

        # Indicator 3: SPA markers present
        markers_found = sum(
            1 for marker in self.SPA_MARKERS if marker.lower() in html_lower
        )
        has_spa_markers = markers_found >= 1

        # Indicator 4: Empty root containers
        has_empty_root = bool(_EMPTY_ROOT_RE.search(html))

        indicators = [
            high_script_density,
            low_content,
            has_spa_markers,
            has_empty_root,
        ]

        return sum(indicators) >= self.spa_threshold

    def evaluate_quality(
        self,
        text_content: str,
        html_content: str,
        status_code: int,
        spa_detected: bool,
    ) -> QualityDecision:
        """Evaluate if fast path result meets quality threshold.

        Args:
            text_content: Extracted text content
            html_content: Raw HTML content
            status_code: HTTP status code
            spa_detected: Whether SPA was detected in HTML

        Returns:
            QualityDecision with pass/fail and specific check results
        """
        checks = {
            "text_length": len(text_content) >= self.min_text_length,
            "content_ratio": len(text_content) / max(len(html_content), 1)
            >= self.min_content_ratio,
            "no_spa": not spa_detected,
            "success_status": status_code == 200,
        }

        passed = all(checks.values())
        fallback_reason = None

        if not passed:
            # Find first failing check for reporting
            fallback_reason = next((k for k, v in checks.items() if not v), None)

        return QualityDecision(
            passed=passed,
            checks=checks,
            fallback_reason=fallback_reason,
        )

    def _infer_page_type(self, path: str) -> str:
        """Infer page type from URL path for priority/config selection."""
        if "/platform/" in path or "/products/" in path or "/ai-" in path:
            return "PRODUCT"
        elif "/solutions/" in path:
            if any(
                r in path
                for r in ["marketing", "sales-", "enablement", "learning"]
            ):
                return "ROLE_SOLUTION"
            return "INDUSTRY_SOLUTION"
        elif "/customer-stories" in path or "/case-stud" in path:
            return "CUSTOMER_STORY"
        elif "/pricing" in path:
            return "PRICING"
        elif "/trust" in path or "/security" in path:
            return "TRUST"
        elif "/integrations" in path:
            return "INTEGRATIONS"
        elif "/partner" in path:
            return "PARTNERS"
        elif "/about" in path or "/company" in path:
            return "COMPANY_ABOUT"
        elif "/resource" in path or "/blog" in path or "/news" in path:
            return "RESOURCE_CENTER"
        return "UNKNOWN"

    def _priority_for_page_type(self, page_type: str) -> int:
        """Higher priority = scrape first (dependencies first)."""
        priorities = {
            "PRODUCT": 10,  # Core entities
            "HOMEPAGE": 9,  # Company identity
            "PRICING": 8,  # Commercial model
            "TRUST": 8,  # Compliance
            "CUSTOMER_STORY": 7,  # Proof points
            "ROLE_SOLUTION": 6,  # Personas
            "INDUSTRY_SOLUTION": 6,  # Industries
            "INTEGRATIONS": 5,  # Ecosystem
            "PARTNERS": 4,  # Supporting
            "COMPANY_ABOUT": 4,  # Identity
            "RESOURCE_CENTER": 3,  # Lower priority
            "UNKNOWN": 2,
        }
        return priorities.get(page_type, 3)

    def _browser_config_for(self, page_type: str) -> dict[str, Any]:
        """Browser-specific configuration per page type."""
        configs = {
            "PRODUCT": {
                "scroll_percent": 100,
                "wait_for": "networkidle",
                "extract_schema": "product",
                "timeout": 60000,
                "observe_first": True,
            },
            "CUSTOMER_STORY": {
                "scroll_percent": 100,
                "wait_for": "networkidle",
                "extract_schema": "customer_story",
                "timeout": 45000,
            },
            "PRICING": {
                "scroll_percent": 80,
                "wait_for": "networkidle",
                "extract_schema": "pricing",
                "timeout": 30000,
            },
            "TRUST": {
                "scroll_percent": 100,
                "wait_for": "networkidle",
                "extract_schema": "trust",
                "timeout": 45000,
            },
            "HOMEPAGE": {
                "scroll_percent": 100,
                "wait_for": "networkidle",
                "extract_schema": "homepage",
                "timeout": 45000,
            },
        }
        return configs.get(
            page_type,
            {
                "scroll_percent": 50,
                "wait_for": "domcontentloaded",
                "timeout": 30000,
            },
        )

    def _default_browser_config(self) -> dict[str, Any]:
        """Default browser configuration."""
        return SmartRouter__default_browser_configResult.model_validate({
            "scroll_percent": 50,
            "wait_for": "domcontentloaded",
            "timeout": 30000,
        })


