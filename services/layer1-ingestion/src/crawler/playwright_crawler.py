"""Playwright-based web crawler implementation.

This module provides async web crawling capabilities using Playwright
to render JavaScript-heavy pages and extract clean content.

Features:
- OpenTelemetry tracing for observability
- External configuration via CrawlerConfig
- Structured metrics collection
- Concurrent crawling with rate limiting
"""

import asyncio
import contextlib
import random
import time
from dataclasses import dataclass
from typing import Any
from urllib.parse import urljoin, urlparse

import structlog
from playwright.async_api import Browser, BrowserContext, Page, async_playwright

from ..compliance.url_safety import validate_url_safety
from .browser_pool import BrowserPool, get_browser_pool
from .crawler_config import CrawlerConfig, load_config
from .telemetry import (
    CrawlMetrics,
    get_tracer,
    init_telemetry,
    start_batch_span,
    start_crawl_span,
)

logger = structlog.get_logger()


@dataclass
class CrawlResult:
    """Result of crawling a single URL."""

    url: str
    status_code: int | None
    html_content: str | None
    title: str | None
    error: str | None
    duration_ms: int
    headers: dict[str, str]
    final_url: str  # In case of redirects
    blocked_resources: int = 0  # Number of resources blocked during crawl
    scroll_triggered: bool = False  # Whether lazy loading was triggered


class PlaywrightCrawler:
    """Async web crawler using Playwright with observability."""

    def __init__(
        self,
        max_concurrent: int | None = None,
        timeout_ms: int | None = None,
        navigation_timeout_ms: int | None = None,
        user_agent: str | None = None,
        config: CrawlerConfig | None = None,
        enable_telemetry: bool = True,
        use_browser_pool: bool = True,  # P1-01: Enable browser pool by default
    ):
        # Load config from file if not provided
        self.config = config or load_config()

        # Allow constructor parameters to override config
        self.max_concurrent = max_concurrent or self.config.max_concurrent
        self.timeout_ms = timeout_ms or self.config.timeout_ms
        self.navigation_timeout_ms = navigation_timeout_ms or self.config.navigation_timeout_ms
        self.user_agent = user_agent or self.config.user_agent
        self.enable_telemetry = enable_telemetry and self.config.enable_tracing
        self.use_browser_pool = use_browser_pool

        # Initialize telemetry if enabled
        if self.enable_telemetry:
            init_telemetry(
                service_name=self.config.trace_attributes.get("service.name", "layer1-crawler"),
                service_version=self.config.trace_attributes.get("service.version", "1.0.0"),
                attributes=self.config.trace_attributes,
            )

        # Metrics collector
        self.metrics = CrawlMetrics()

        self._playwright = None
        self._browser: Browser | None = None
        self._context: BrowserContext | None = None
        self._semaphore: asyncio.Semaphore | None = None
        
        # P1-01: Browser pool for instance reuse
        self._browser_pool: BrowserPool | None = None

    async def __aenter__(self):
        """Async context manager entry."""
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.stop()

    async def start(self):
        """Initialize Playwright browser with tracing."""
        tracer = get_tracer() if self.enable_telemetry else None

        with tracer.start_as_current_span("crawler.start") if tracer else contextlib.nullcontext():
            logger.info(
                "Starting Playwright crawler",
                max_concurrent=self.max_concurrent,
                timeout_ms=self.timeout_ms,
                telemetry_enabled=self.enable_telemetry,
                use_browser_pool=self.use_browser_pool,
            )

            # P1-01: Use browser pool if enabled
            if self.use_browser_pool:
                self._browser_pool = get_browser_pool()
                await self._browser_pool.initialize()
                logger.info("Browser pool initialized", stats=self._browser_pool.get_stats())
            else:
                # Legacy mode: create single browser instance
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=self.config.headless,
                    args=self.config.browser_args,
                )
                self._context = await self._browser.new_context(
                    user_agent=self.user_agent,
                    viewport=self.config.viewport,
                    java_script_enabled=True,
                    bypass_csp=True,
                )
                self._context.set_default_timeout(self.timeout_ms)
                self._context.set_default_navigation_timeout(self.navigation_timeout_ms)

            # Semaphore for concurrency control
            self._semaphore = asyncio.Semaphore(self.max_concurrent)

            logger.info("Playwright crawler started successfully")

    async def stop(self):
        """Close Playwright browser with metrics export."""
        tracer = get_tracer() if self.enable_telemetry else None

        with (
            tracer.start_as_current_span("crawler.stop")
            if tracer
            else contextlib.nullcontext() as span
        ):
            # Log final metrics
            if self.metrics.crawl_count > 0:
                metrics_data = self.metrics.to_dict()
                logger.info(
                    "Crawler session summary",
                    **metrics_data,
                )
                if span:
                    for key, value in metrics_data.items():
                        span.set_attribute(key, value)

            logger.info("Stopping Playwright crawler")

            # P1-01: Cleanup browser pool if used
            if self._browser_pool:
                await self._browser_pool.cleanup()
                logger.info("Browser pool cleaned up", stats=self._browser_pool.get_stats())
            else:
                # Legacy mode cleanup
                if self._context:
                    await self._context.close()

                if self._browser:
                    await self._browser.close()

                if self._playwright:
                    await self._playwright.stop()

            logger.info("Playwright crawler stopped successfully")

    async def crawl_url(
        self,
        url: str,
        wait_for_selector: str | None = None,
        wait_for_timeout: int = 2000,
        scroll_page: bool = True,
    ) -> CrawlResult:
        """Crawl a single URL and return the result with tracing.

        Args:
            url: URL to crawl
            wait_for_selector: Optional CSS selector to wait for
            wait_for_timeout: Time to wait after page load (ms)
            scroll_page: Whether to scroll to bottom to trigger lazy loading

        Returns:
            CrawlResult with HTML content and metadata
        """
        # SECURITY: Defense-in-depth URL safety validation at crawler boundary
        validate_url_safety(url)

        start_time = time.time()
        blocked_resources = 0
        scroll_triggered = False

        with (
            start_crawl_span(url, "crawl_url")
            if self.enable_telemetry
            else contextlib.nullcontext() as span
        ):
            async with self._semaphore:
                page: Page | None = None
                browser_instance = None

                try:
                    # P1-01: Use browser pool if enabled
                    if self._browser_pool:
                        browser_instance, page = await self._browser_pool.get_page()
                    else:
                        # Legacy mode: create page from single context
                        page = await self._context.new_page()

                    # Block unnecessary resources with counting
                    async def block_route(route):
                        nonlocal blocked_resources
                        blocked_resources += 1
                        await route.abort()

                    for pattern in self.config.blocked_resource_patterns:
                        await page.route(pattern, block_route)

                    # Navigate to URL
                    nav_start = time.time()
                    response = await page.goto(
                        url, wait_until="networkidle", timeout=self.navigation_timeout_ms
                    )
                    nav_duration_ms = int((time.time() - nav_start) * 1000)

                    if span:
                        span.set_attribute("crawl.navigation_ms", nav_duration_ms)
                        if response:
                            span.set_attribute("crawl.status_code", response.status)

                    # Wait for specific element if requested
                    if wait_for_selector:
                        try:
                            await page.wait_for_selector(
                                wait_for_selector, timeout=wait_for_timeout
                            )
                        except Exception:
                            logger.warning(
                                "Wait selector timeout",
                                url=url,
                                selector=wait_for_selector,
                                error_code="SELECTOR_TIMEOUT",
                            )
                            if span:
                                span.set_attribute("crawl.selector_timeout", True)
                    else:
                        # Default wait for dynamic content
                        await asyncio.sleep(wait_for_timeout / 1000)

                    # Scroll to trigger lazy loading
                    if scroll_page and self.config.scroll_enabled:
                        scroll_success = await self._scroll_page(page)
                        scroll_triggered = scroll_success
                        if span:
                            span.set_attribute("crawl.scroll_triggered", scroll_success)

                    # Get page content
                    html_content = await page.content()
                    title = await page.title()

                    # Get final URL (after redirects)
                    final_url = page.url

                    duration_ms = int((time.time() - start_time) * 1000)

                    # Record metrics
                    self.metrics.record_crawl(
                        duration_ms=duration_ms,
                        success=True,
                        blocked_resources=blocked_resources,
                        scroll_triggered=scroll_triggered,
                    )

                    if span:
                        span.set_attribute("crawl.duration_ms", duration_ms)
                        span.set_attribute("crawl.blocked_resources", blocked_resources)
                        span.set_attribute("crawl.final_url", final_url)

                    return CrawlResult(
                        url=url,
                        status_code=response.status if response else None,
                        html_content=html_content,
                        title=title,
                        error=None,
                        duration_ms=duration_ms,
                        headers=dict(response.headers) if response else {},
                        final_url=final_url,
                        blocked_resources=blocked_resources,
                        scroll_triggered=scroll_triggered,
                    )

                except Exception:
                    duration_ms = int((time.time() - start_time) * 1000)

                    # Record failure metrics
                    self.metrics.record_crawl(
                        duration_ms=duration_ms,
                        success=False,
                        blocked_resources=blocked_resources,
                        scroll_triggered=scroll_triggered,
                    )

                    logger.error(
                        "Crawl failed",
                        url=url,
                        error_code="CRAWL_ERROR",
                        duration_ms=duration_ms,
                        exc_info=True,
                    )

                    if span:
                        span.set_attribute("crawl.duration_ms", duration_ms)
                        span.set_attribute("crawl.error_code", "CRAWL_ERROR")

                    return CrawlResult(
                        url=url,
                        status_code=None,
                        html_content=None,
                        title=None,
                        error="Crawl failed",
                        duration_ms=duration_ms,
                        headers={},
                        final_url=url,
                        blocked_resources=blocked_resources,
                        scroll_triggered=scroll_triggered,
                    )

                finally:
                    # P1-01: Release page and browser instance back to pool
                    if page:
                        if self._browser_pool and browser_instance:
                            await self._browser_pool.release_page(browser_instance, page)
                        else:
                            await page.close()

    async def crawl_urls(self, urls: list[str], delay_seconds: float | None = None) -> list[CrawlResult]:
        """Crawl multiple URLs with rate limiting and batch tracing.

        Args:
            urls: List of URLs to crawl
            delay_seconds: Delay between requests to same domain

        Returns:
            List of CrawlResult objects
        """
        delay = delay_seconds or self.config.per_domain_delay_seconds

        with (
            start_batch_span(len(urls), "crawl_urls")
            if self.enable_telemetry
            else contextlib.nullcontext() as span
        ):
            results = []
            last_request_time: dict[str, float] = {}
            success_count = 0

            for i, url in enumerate(urls):
                domain = urlparse(url).netloc

                # Rate limiting with telemetry
                if delay and domain in last_request_time:
                    elapsed = time.time() - last_request_time[domain]
                    if elapsed < delay:
                        wait_time = delay - elapsed
                        # Add jitter
                        jitter = wait_time * (self.config.jitter_percent / 100)
                        wait_time += random.uniform(-jitter, jitter)

                        logger.debug(
                            "Rate limiting delay",
                            domain=domain,
                            wait_seconds=wait_time,
                            url_index=i,
                        )
                        if span:
                            span.set_attribute(f"crawl.url_{i}.rate_limited", True)
                            span.set_attribute(f"crawl.url_{i}.wait_ms", int(wait_time * 1000))

                        await asyncio.sleep(max(0, wait_time))

                # Crawl the URL
                result = await self.crawl_url(url)
                results.append(result)

                if result.error is None:
                    success_count += 1

                last_request_time[domain] = time.time()

            # Record batch metrics
            if span:
                span.set_attribute("crawl.success_count", success_count)
                span.set_attribute("crawl.error_count", len(urls) - success_count)
                span.set_attribute("crawl.success_rate", success_count / len(urls) if urls else 0)

            logger.info(
                "Batch crawl completed",
                total_urls=len(urls),
                success_count=success_count,
                error_count=len(urls) - success_count,
            )

            return results

    async def _scroll_page(self, page: Page) -> bool:
        """Scroll page to trigger lazy loading with config-driven parameters.

        Args:
            page: Playwright page object

        Returns:
            True if scroll succeeded, False otherwise
        """
        try:
            scroll_script = f"""
                async () => {{
                    await new Promise((resolve) => {{
                        let totalHeight = 0;
                        const distance = {self.config.scroll_distance};
                        const timer = setInterval(() => {{
                            const scrollHeight = document.body.scrollHeight;
                            window.scrollBy(0, distance);
                            totalHeight += distance;
                            
                            if (totalHeight >= scrollHeight) {{
                                clearInterval(timer);
                                resolve();
                            }}
                        }}, {self.config.scroll_interval_ms});
                    }});
                }}
            """
            await page.evaluate(scroll_script)
            # Delay after scrolling from config
            await asyncio.sleep(self.config.scroll_delay_after_ms / 1000)
            return True
        except Exception:
            logger.warning("Page scroll failed", error_code="SCROLL_ERROR")
            return False

    async def extract_links(
        self, page: Page, base_url: str, same_domain_only: bool = True
    ) -> list[dict[str, Any]]:
        """Extract all links from a page.

        Args:
            page: Playwright page object
            base_url: Base URL for resolving relative links
            same_domain_only: Only return links from same domain

        Returns:
            List of link dictionaries with url, text, and is_external
        """
        base_domain = urlparse(base_url).netloc

        links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                .map(a => ({
                    href: a.href,
                    text: a.textContent.trim(),
                    title: a.title
                }))
                .filter(a => a.href && !a.href.startsWith('javascript:') && !a.href.startsWith('#'))
        """)

        result = []
        for link in links:
            absolute_url = urljoin(base_url, link["href"])
            parsed = urlparse(absolute_url)

            # Skip non-HTTP(S) protocols
            if parsed.scheme not in ("http", "https"):
                continue

            is_external = parsed.netloc != base_domain

            if same_domain_only and is_external:
                continue

            result.append(
                {
                    "url": absolute_url,
                    "text": link["text"][:200],  # Limit text length
                    "title": link.get("title", "")[:200],
                    "is_external": is_external,
                }
            )

        return result
