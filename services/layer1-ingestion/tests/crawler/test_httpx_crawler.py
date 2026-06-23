"""Tests for HttpxCrawler fast path implementation.

Covers HTTP fetching, SPA detection, content extraction, error handling,
and batch operations.
"""

from __future__ import annotations

import asyncio

import httpx
import pytest
import respx
from httpx import Response

from layer1_ingestion.compliance.url_safety import URLSafetyError
from layer1_ingestion.crawler.httpx_crawler import (
    FastPathResult,
    HttpxCrawler,
    HttpxCrawlerConfig,
)


class TestHttpxCrawlerBasic:
    """Test basic HTTPX crawler functionality."""

    @pytest.fixture
    def crawler(self) -> HttpxCrawler:
        """Create an unstarted crawler (for config tests)."""
        return HttpxCrawler()

    @pytest.fixture
    async def started_crawler(self) -> HttpxCrawler:
        """Create and start a crawler (for fetch tests)."""
        crawler = HttpxCrawler()
        await crawler.start()
        yield crawler
        await crawler.stop()

    def test_default_config(self, crawler: HttpxCrawler) -> None:
        """Crawler has sensible default configuration."""
        assert crawler.config.timeout_seconds == 15
        assert crawler.config.max_connections == 50
        assert crawler.config.max_concurrent_requests == 20
        assert "ValueFabric-FastPath" in crawler.config.user_agent

    def test_custom_config(self) -> None:
        """Crawler accepts custom configuration."""
        config = HttpxCrawlerConfig(
            timeout_seconds=30,
            max_connections=100,
            user_agent="CustomBot/1.0",
        )
        crawler = HttpxCrawler(config)
        assert crawler.config.timeout_seconds == 30
        assert crawler.config.max_connections == 100
        assert crawler.config.user_agent == "CustomBot/1.0"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_success(self, started_crawler: HttpxCrawler) -> None:
        """Successfully fetch a page."""
        route = respx.get("https://example.com/page").mock(
            return_value=Response(
                200,
                html="<html><head><title>Test Page</title></head><body><h1>Hello</h1><p>Content here</p></body></html>",
                headers={"content-type": "text/html"},
            )
        )

        result = await started_crawler.fetch("https://example.com/page")

        assert result.status_code == 200
        assert result.title == "Test Page"
        assert "Hello" in result.text_content
        assert result.fetch_time_ms >= 0
        assert result.content_hash
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_not_found(self, started_crawler: HttpxCrawler) -> None:
        """Handle 404 response gracefully."""
        route = respx.get("https://example.com/not-found").mock(
            return_value=Response(404, text="Not found")
        )

        result = await started_crawler.fetch("https://example.com/not-found")

        assert result.status_code == 404
        assert result.text_content == ""
        assert result.content_type == "http_error"

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_redirect_followed(self, started_crawler: HttpxCrawler) -> None:
        """Follow redirects automatically."""
        respx.get("https://example.com/old").mock(
            return_value=Response(301, headers={"location": "https://example.com/new"})
        )
        respx.get("https://example.com/new").mock(
            return_value=Response(200, html="<html><title>New Page</title></html>")
        )

        result = await started_crawler.fetch("https://example.com/old")

        assert result.status_code == 200
        assert result.title == "New Page"

    @pytest.mark.asyncio
    async def test_fetch_requires_start(self) -> None:
        """Fetch fails if crawler not started."""
        crawler = HttpxCrawler()
        with pytest.raises(RuntimeError, match="not started"):
            await crawler.fetch("https://example.com/page")


class TestSPADetection:
    """Test SPA shell detection heuristics."""

    @pytest.fixture
    def crawler(self) -> HttpxCrawler:
        return HttpxCrawler()

    def test_detect_empty_root(self, crawler: HttpxCrawler) -> None:
        """Detect SPA with empty root div."""
        html = """
        <html>
            <head><script src="app.js"></script></head>
            <body><div id="root"></div></body>
        </html>
        """
        assert crawler._detect_spa_shell(html) is True

    def test_detect_high_script_density(self, crawler: HttpxCrawler) -> None:
        """Detect SPA with many script tags."""
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
            <body><div id="app"></div></body>
        </html>
        """
        assert crawler._detect_spa_shell(html) is True

    def test_detect_react_marker(self, crawler: HttpxCrawler) -> None:
        """Detect SPA with React marker."""
        html = """
        <html data-reactroot="">
            <head>
                <script src="1.js"></script>
                <script src="2.js"></script>
                <script src="3.js"></script>
                <script src="4.js"></script>
                <script src="5.js"></script>
            </head>
            <body><div id="root"></div></body>
        </html>
        """
        assert crawler._detect_spa_shell(html) is True

    def test_detect_low_content_ratio(self, crawler: HttpxCrawler) -> None:
        """Detect SPA with low content ratio."""
        # Lots of markup, very little text, plus empty root div
        html = "<html><body><div id='root'></div>" + "<div class='wrapper'><span>" * 500 + "Short" + "</span></div>" * 500 + "</body></html>"
        assert crawler._detect_spa_shell(html) is True

    def test_not_detect_static_page(self, crawler: HttpxCrawler) -> None:
        """Static page is not detected as SPA."""
        html = """
        <html>
            <head><title>Static Page</title></head>
            <body>
                <h1>Full Article Title</h1>
                <p>This is a paragraph with substantial content. It contains enough
                text to represent a real article or blog post that would be rendered
                server-side and served as static HTML to the browser.</p>
                <p>Additional paragraphs provide more content and demonstrate that
                this is indeed a fully rendered page, not a JavaScript shell waiting
                to be populated by client-side rendering.</p>
                <script src="analytics.js"></script>
            </body>
        </html>
        """
        assert crawler._detect_spa_shell(html) is False

    def test_not_detect_empty_html(self, crawler: HttpxCrawler) -> None:
        """Empty HTML is not a SPA."""
        assert crawler._detect_spa_shell("") is False

    def test_not_detect_server_rendered_react(self, crawler: HttpxCrawler) -> None:
        """Server-rendered React (Next.js) is not detected as SPA shell."""
        html = """
        <html>
            <head><title>SSR Page</title></head>
            <body>
                <div id="__next">
                    <h1>Server Rendered Content</h1>
                    <p>Lots of server-rendered content here...</p>
                    <p>More paragraphs with substantial text...</p>
                    <p>Even more content to keep ratio high...</p>
                </div>
            </body>
        </html>
        """
        # Should not detect because content ratio is high
        assert crawler._detect_spa_shell(html) is False


class TestLinkExtraction:
    """Test link extraction from HTML."""

    @pytest.fixture
    def crawler(self) -> HttpxCrawler:
        return HttpxCrawler()

    def test_extract_absolute_links(self, crawler: HttpxCrawler) -> None:
        """Extract absolute URLs."""
        html = """
        <html>
            <body>
                <a href="https://example.com/page1">Page 1</a>
                <a href="https://example.com/page2">Page 2</a>
            </body>
        </html>
        """
        links = crawler._extract_links(html, "https://example.com")
        assert len(links) == 2
        assert "https://example.com/page1" in links
        assert "https://example.com/page2" in links

    def test_extract_relative_links(self, crawler: HttpxCrawler) -> None:
        """Resolve relative URLs to absolute."""
        html = """
        <html>
            <body>
                <a href="/about">About</a>
                <a href="contact">Contact</a>
            </body>
        </html>
        """
        links = crawler._extract_links(html, "https://example.com")
        assert "https://example.com/about" in links
        assert "https://example.com/contact" in links

    def test_skip_javascript_links(self, crawler: HttpxCrawler) -> None:
        """Skip javascript: and anchor-only links."""
        html = """
        <html>
            <body>
                <a href="javascript:void(0)">Click</a>
                <a href="#section">Section</a>
                <a href="https://example.com/page">Page</a>
            </body>
        </html>
        """
        links = crawler._extract_links(html, "https://example.com")
        assert len(links) == 1
        assert "https://example.com/page" in links

    def test_skip_mailto_tel(self, crawler: HttpxCrawler) -> None:
        """Skip mailto: and tel: links."""
        html = """
        <html>
            <body>
                <a href="mailto:test@example.com">Email</a>
                <a href="tel:+1234567890">Call</a>
                <a href="/contact">Contact Page</a>
            </body>
        </html>
        """
        links = crawler._extract_links(html, "https://example.com")
        assert len(links) == 1
        assert "https://example.com/contact" in links

    def test_deduplicate_links(self, crawler: HttpxCrawler) -> None:
        """Remove duplicate links while preserving order."""
        html = """
        <html>
            <body>
                <a href="/page">Page</a>
                <a href="/page">Duplicate</a>
                <a href="/other">Other</a>
            </body>
        </html>
        """
        links = crawler._extract_links(html, "https://example.com")
        assert len(links) == 2
        assert links[0] == "https://example.com/page"
        assert links[1] == "https://example.com/other"


class TestBatchOperations:
    """Test batch URL fetching."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_fetch_batch_concurrent(self) -> None:
        """Fetch multiple URLs concurrently."""
        respx.get("https://example.com/page1").mock(
            return_value=Response(200, html="<title>Page 1</title>")
        )
        respx.get("https://example.com/page2").mock(
            return_value=Response(200, html="<title>Page 2</title>")
        )
        respx.get("https://example.com/page3").mock(
            return_value=Response(200, html="<title>Page 3</title>")
        )

        async with HttpxCrawler() as crawler:
            results = await crawler.fetch_batch(
                [
                    "https://example.com/page1",
                    "https://example.com/page2",
                    "https://example.com/page3",
                ]
            )

        assert len(results) == 3
        assert all(r.status_code == 200 for r in results)
        assert results[0].title == "Page 1"
        assert results[1].title == "Page 2"
        assert results[2].title == "Page 3"


class TestErrorHandling:
    """Test error cases and edge conditions."""

    @pytest.fixture
    async def started_crawler(self) -> HttpxCrawler:
        crawler = HttpxCrawler()
        await crawler.start()
        yield crawler
        await crawler.stop()

    @pytest.mark.asyncio
    async def test_timeout_handling(self) -> None:
        """Handle request timeout."""

        class TimeoutClient:
            async def get(self, *_args, **_kwargs):
                raise httpx.TimeoutException("Request timed out")

            async def aclose(self):
                pass

        config = HttpxCrawlerConfig(timeout_seconds=1)
        crawler = HttpxCrawler(config)
        await crawler.start()
        crawler._client = TimeoutClient()

        result = await crawler.fetch("https://example.com/slow")
        await crawler.stop()

        assert result.status_code == 504
        assert result.content_type == "timeout"

    @respx.mock
    @pytest.mark.asyncio
    async def test_server_error(self, started_crawler: HttpxCrawler) -> None:
        """Handle 500 server error."""
        respx.get("https://example.com/error").mock(return_value=Response(500, text="Error"))

        result = await started_crawler.fetch("https://example.com/error")

        assert result.status_code == 500
        assert result.text_content == ""

    @respx.mock
    @pytest.mark.asyncio
    async def test_empty_response(self, started_crawler: HttpxCrawler) -> None:
        """Handle empty HTML response."""
        respx.get("https://example.com/empty").mock(return_value=Response(200, html=""))

        result = await started_crawler.fetch("https://example.com/empty")

        assert result.status_code == 200
        assert result.html == ""
        assert result.text_content == ""
        assert not result.is_spa_detected


class TestSSRFProtection:
    """Test SSRF network boundary enforcement."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        [
            "http://127.0.0.1/admin",
            "http://10.0.0.1/",
            "http://172.16.0.1/",
            "http://192.168.1.10/",
            "http://169.254.169.254/latest/meta-data/",
            "http://[::1]/",
            "ftp://example.com/file",
            "http://localhost:8000/",
        ],
    )
    async def test_fetch_rejects_private_targets(self, url: str) -> None:
        crawler = HttpxCrawler()
        await crawler.start()
        crawler._semaphore = asyncio.Semaphore(1)

        result = await crawler.fetch(url)
        await crawler.stop()

        assert result.status_code == 400
        assert result.content_type == "ssrf_blocked"

    @pytest.mark.asyncio
    async def test_fetch_blocks_private_ip(self) -> None:
        crawler = HttpxCrawler()
        await crawler.start()
        crawler._semaphore = asyncio.Semaphore(1)

        result = await crawler.fetch("http://169.254.169.254/latest/meta-data/")
        await crawler.stop()

        assert result.status_code == 400
        assert result.content_type == "ssrf_blocked"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "url",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://169.254.170.2/v2/metadata",
            "http://100.100.100.200/latest/meta-data/",
            "http://192.0.0.254/opc/v1/instance/",
            "http://[fd00:ec2::254]/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "http://metadata.internal/secret",
            "https://service.metadata/secret",
        ],
    )
    async def test_fetch_blocks_cloud_metadata_endpoints_before_network(
        self,
        url: str,
    ) -> None:
        class FailingClient:
            async def get(self, *_args, **_kwargs):
                raise AssertionError("SSRF validation must run before outbound fetch")

            async def aclose(self):
                pass

        crawler = HttpxCrawler()
        await crawler.start()
        crawler._client = FailingClient()
        crawler._semaphore = asyncio.Semaphore(1)

        result = await crawler.fetch(url)
        await crawler.stop()

        assert result.status_code == 400
        assert result.content_type == "ssrf_blocked"

    @pytest.mark.asyncio
    async def test_redirect_to_private_ip_is_blocked(self) -> None:
        class FakeClient:
            async def get(self, *_args, **_kwargs):
                return Response(302, headers={"location": "http://127.0.0.1/admin"})

            async def aclose(self):
                pass

        crawler = HttpxCrawler()
        await crawler.start()
        crawler._client = FakeClient()
        crawler._semaphore = asyncio.Semaphore(1)

        result = await crawler.fetch("https://example.com/redirect")
        await crawler.stop()

        assert result.status_code == 400
        assert result.content_type == "ssrf_blocked"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        "location",
        [
            "http://169.254.169.254/latest/meta-data/",
            "http://metadata.google.internal/computeMetadata/v1/",
            "https://service.metadata/secret",
        ],
    )
    async def test_redirect_to_cloud_metadata_endpoint_is_blocked(
        self,
        location: str,
    ) -> None:
        class FakeClient:
            async def get(self, *_args, **_kwargs):
                return Response(302, headers={"location": location})

            async def aclose(self):
                pass

        crawler = HttpxCrawler()
        await crawler.start()
        crawler._client = FakeClient()
        crawler._semaphore = asyncio.Semaphore(1)

        result = await crawler.fetch("https://example.com/redirect")
        await crawler.stop()

        assert result.status_code == 400
        assert result.content_type == "ssrf_blocked"


class TestFastPathResult:
    """Test FastPathResult data structure."""

    def test_result_creation(self) -> None:
        """Create result with all fields."""
        result = FastPathResult(
            url="https://example.com",
            status_code=200,
            html="<html></html>",
            title="Title",
            text_content="Content",
            content_hash="abc123",
            links_found=["https://example.com/page"],
            is_spa_detected=False,
            fetch_time_ms=150,
        )

        assert result.url == "https://example.com"
        assert result.status_code == 200
        assert result.fetch_time_ms == 150

    def test_result_defaults(self) -> None:
        """Result has sensible defaults."""
        result = FastPathResult(
            url="https://example.com",
            status_code=200,
            html="<html></html>",
            title="Title",
            text_content="Content",
            content_hash="abc123",
        )

        assert result.links_found == []
        assert result.is_spa_detected is False
        assert result.fetch_time_ms == 0

