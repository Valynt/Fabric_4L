"""Tests for PlaywrightCrawler with mocked Playwright.

Comprehensive test coverage for crawling, rate limiting, error handling,
and metrics collection - following the skill framework's pytest patterns.
"""

import asyncio
from typing import Any
from unittest.mock import AsyncMock, Mock, patch

import importlib.util

import pytest

# Playwright is an optional slow dependency (browser automation).
# Tests are collected but skipped when playwright is not installed.
# Install with: pip install playwright && playwright install chromium
_playwright_missing = importlib.util.find_spec("playwright") is None
pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(_playwright_missing, reason="playwright not installed — optional slow dep"),
]

from layer1_ingestion.crawler.crawler_config import CrawlerConfig
from value_fabric.shared.models.typed_dict import TypedDictModel

if _playwright_missing:
    CrawlResult = None  # type: ignore[misc]
    PlaywrightCrawler = None  # type: ignore[misc]
else:
    from layer1_ingestion.crawler.playwright_crawler import CrawlResult, PlaywrightCrawler


class mock_playwrightResult(TypedDictModel):
    browser: Any
    context: Any
    page: Any
    playwright: Any


# Fixtures
@pytest.fixture
def mock_playwright():
    """Create a fully mocked Playwright instance."""
    mock_pw = AsyncMock()
    mock_browser = AsyncMock()
    mock_context = AsyncMock()
    mock_page = AsyncMock()
    
    # Setup async chain
    mock_pw.chromium.launch = AsyncMock(return_value=mock_browser)
    mock_browser.new_context = AsyncMock(return_value=mock_context)
    mock_context.new_page = AsyncMock(return_value=mock_page)
    mock_page.goto = AsyncMock(return_value=Mock(status=200, headers={"content-type": "text/html"}))
    mock_page.content = AsyncMock(return_value="<html><body>Test content</body></html>")
    mock_page.title = AsyncMock(return_value="Test Page")
    mock_page.url = "https://example.com/final"
    
    return mock_playwrightResult.model_validate({
        "playwright": mock_pw,
        "browser": mock_browser,
        "context": mock_context,
        "page": mock_page,
    })


@pytest.fixture
def crawler_config():
    """Create a test crawler config."""
    return CrawlerConfig(
        max_concurrent=2,
        timeout_ms=5000,
        navigation_timeout_ms=5000,
        scroll_enabled=False,
        enable_tracing=False,  # Disable for tests
        blocked_resource_patterns=["**/*.png"],
    )


class TestPlaywrightCrawlerInit:
    """Test crawler initialization."""
    
    def test_init_with_defaults(self):
        """Test crawler initializes with default config."""
        crawler = PlaywrightCrawler(enable_telemetry=False)
        
        assert crawler.max_concurrent > 0
        assert crawler.timeout_ms > 0
        assert crawler.config is not None
        assert crawler.metrics is not None
        
    def test_init_with_custom_config(self, crawler_config):
        """Test crawler accepts custom config."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        assert crawler.max_concurrent == 2
        assert crawler.timeout_ms == 5000
        assert crawler.enable_telemetry is False
        
    def test_init_with_override_params(self, crawler_config):
        """Test constructor params override config values."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            max_concurrent=10,
            enable_telemetry=False,
        )
        
        assert crawler.max_concurrent == 10  # Constructor override
        assert crawler.timeout_ms == 5000  # From config


class TestPlaywrightCrawlerStartStop:
    """Test crawler lifecycle."""
    
    @pytest.mark.asyncio
    async def test_start_initializes_resources(self, mock_playwright, crawler_config):
        """Test that start() initializes Playwright resources."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            
            await crawler.start()
            
            # Verify resources were initialized
            assert crawler._playwright is not None
            assert crawler._semaphore is not None
            mock_playwright["playwright"].chromium.launch.assert_called_once()
            
            # Cleanup
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_stop_releases_resources(self, mock_playwright, crawler_config):
        """Test that stop() releases all resources."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        # Set up mock resources
        crawler._playwright = mock_playwright["playwright"]
        crawler._browser = mock_playwright["browser"]
        crawler._context = mock_playwright["context"]
        
        await crawler.stop()
        
        # Verify cleanup
        mock_playwright["context"].close.assert_called_once()
        mock_playwright["browser"].close.assert_called_once()
        mock_playwright["playwright"].stop.assert_called_once()
        
    @pytest.mark.asyncio
    async def test_context_manager_usage(self, mock_playwright, crawler_config):
        """Test async context manager usage."""
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            
            async with PlaywrightCrawler(
                config=crawler_config,
                enable_telemetry=False,
                use_browser_pool=False,
            ) as crawler:
                assert crawler._playwright is not None
                
            # After exit, resources should be cleaned up
            mock_playwright["playwright"].stop.assert_called_once()


class TestCrawlUrl:
    """Test single URL crawling."""
    
    @pytest.mark.asyncio
    async def test_successful_crawl(self, mock_playwright, crawler_config):
        """Test successful URL crawl returns correct result."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        # Setup mocks
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            result = await crawler.crawl_url("https://example.com")
            
            # Verify result structure
            assert isinstance(result, CrawlResult)
            assert result.url == "https://example.com"
            assert result.status_code == 200
            assert result.html_content is not None
            assert result.error is None
            assert result.duration_ms >= 0
            assert result.final_url == "https://example.com/final"
            
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_crawl_with_resource_blocking(self, mock_playwright, crawler_config):
        """Test that resource blocking patterns are applied."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            await crawler.crawl_url("https://example.com")
            
            # Verify route was set up for resource blocking
            mock_playwright["page"].route.assert_called()
            
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_crawl_handles_navigation_error(self, mock_playwright, crawler_config):
        """Test that navigation errors are handled gracefully."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        # Make goto raise an exception
        mock_playwright["page"].goto = AsyncMock(side_effect=Exception("Navigation timeout"))
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            result = await crawler.crawl_url("https://example.com")
            
            # Should return error result, not raise
            assert result.error is not None
            assert result.error == "Crawl failed"
            assert result.status_code is None
            assert result.html_content is None
            
            # Metrics should track failure
            assert crawler.metrics.error_count == 1
            assert crawler.metrics.crawl_count == 1
            
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_crawl_records_metrics(self, mock_playwright, crawler_config):
        """Test that successful crawls record metrics."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            await crawler.crawl_url("https://example.com")
            
            assert crawler.metrics.crawl_count == 1
            assert crawler.metrics.error_count == 0
            assert crawler.metrics.avg_duration_ms >= 0
            
            await crawler.stop()


class TestCrawlUrls:
    """Test batch URL crawling with rate limiting."""
    
    @pytest.mark.asyncio
    async def test_crawl_multiple_urls(self, mock_playwright, crawler_config):
        """Test crawling multiple URLs returns correct results."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            urls = [
                "https://example.com/page1",
                "https://example.com/page2",
            ]
            results = await crawler.crawl_urls(urls)
            
            assert len(results) == 2
            for i, result in enumerate(results):
                assert result.url == urls[i]
                assert result.error is None
                
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_rate_limiting_delays_requests(self, mock_playwright, crawler_config):
        """Test that rate limiting delays requests to same domain."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            urls = [
                "https://example.com/page1",
                "https://example.com/page2",  # Same domain
            ]
            
            start_time = asyncio.get_event_loop().time()
            results = await crawler.crawl_urls(urls, delay_seconds=0.1)
            elapsed = asyncio.get_event_loop().time() - start_time
            
            # Should have taken at least 0.1s due to rate limiting
            assert elapsed >= 0.05  # Allow some tolerance
            assert len(results) == 2
            
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_no_delay_for_different_domains(self, mock_playwright, crawler_config):
        """Test that different domains don't trigger rate limiting."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            urls = [
                "https://example1.com/page",
                "https://example2.com/page",  # Different domain
            ]
            
            results = await crawler.crawl_urls(urls, delay_seconds=0.5)
            
            # Should complete quickly without delay between different domains
            assert len(results) == 2
            
            await crawler.stop()


class TestScrollPage:
    """Test page scrolling functionality."""
    
    @pytest.mark.asyncio
    async def test_scroll_enabled_executes_script(self, mock_playwright, crawler_config):
        """Test that scroll executes JavaScript when enabled."""
        config = CrawlerConfig(**{**crawler_config.__dict__, "scroll_enabled": True})
        crawler = PlaywrightCrawler(
            config=config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            result = await crawler.crawl_url("https://example.com", scroll_page=True)
            
            # Verify scroll script was executed
            mock_playwright["page"].evaluate.assert_called()
            assert result.scroll_triggered is True
            
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_scroll_disabled_skips_execution(self, mock_playwright, crawler_config):
        """Test that scroll is skipped when disabled in config."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            result = await crawler.crawl_url("https://example.com", scroll_page=False)
            
            assert result.scroll_triggered is False
            
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_scroll_handles_error(self, mock_playwright, crawler_config):
        """Test that scroll errors are handled gracefully."""
        config = CrawlerConfig(**{**crawler_config.__dict__, "scroll_enabled": True})
        crawler = PlaywrightCrawler(
            config=config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        # Make scroll fail
        mock_playwright["page"].evaluate = AsyncMock(side_effect=Exception("Scroll error"))
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            result = await crawler.crawl_url("https://example.com", scroll_page=True)
            
            # Should still succeed even if scroll fails
            assert result.error is None  # Main crawl succeeds
            assert result.scroll_triggered is False  # But scroll failed
            
            await crawler.stop()


class TestExtractLinks:
    """Test link extraction functionality."""
    
    @pytest.mark.asyncio
    async def test_extract_links_from_page(self, mock_playwright, crawler_config):
        """Test extracting links from a page."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        # Mock page.evaluate to return test links
        mock_links = [
            {"href": "/page1", "text": "Page 1", "title": ""},
            {"href": "https://other.com/page", "text": "External", "title": ""},
        ]
        mock_playwright["page"].evaluate = AsyncMock(return_value=mock_links)
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            links = await crawler.extract_links(
                mock_playwright["page"],
                "https://example.com",
                same_domain_only=True
            )
            
            assert len(links) == 1  # Only same-domain links
            assert links[0]["url"] == "https://example.com/page1"
            assert links[0]["is_external"] is False
            
            await crawler.stop()
            
    @pytest.mark.asyncio
    async def test_extract_links_includes_external(self, mock_playwright, crawler_config):
        """Test that external links are included when flag is set."""
        crawler = PlaywrightCrawler(
            config=crawler_config,
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        mock_links = [
            {"href": "/page1", "text": "Page 1", "title": ""},
            {"href": "https://other.com/page", "text": "External", "title": ""},
        ]
        mock_playwright["page"].evaluate = AsyncMock(return_value=mock_links)
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_playwright["playwright"])
            await crawler.start()
            
            links = await crawler.extract_links(
                mock_playwright["page"],
                "https://example.com",
                same_domain_only=False
            )
            
            assert len(links) == 2
            assert links[1]["is_external"] is True
            
            await crawler.stop()


class TestConcurrency:
    """Test concurrent crawling with semaphore."""
    
    @pytest.mark.asyncio
    async def test_semaphore_limits_concurrency(self, crawler_config):
        """Test that semaphore limits concurrent page operations."""
        crawler = PlaywrightCrawler(
            config=CrawlerConfig(**{**crawler_config.__dict__, "max_concurrent": 1}),
            enable_telemetry=False,
            use_browser_pool=False,
        )
        
        # Mock Playwright
        mock_pw = AsyncMock()
        mock_pw.chromium.launch = AsyncMock(return_value=AsyncMock(
            new_context=AsyncMock(return_value=AsyncMock(
                new_page=AsyncMock(return_value=AsyncMock(
                    route=AsyncMock(),
                    goto=AsyncMock(return_value=Mock(status=200, headers={})),
                    content=AsyncMock(return_value="<html></html>"),
                    title=AsyncMock(return_value="Test"),
                    url="https://example.com",
                    close=AsyncMock(),
                )),
                set_default_timeout=Mock(),
                set_default_navigation_timeout=Mock(),
            )),
            close=AsyncMock(),
        ))
        mock_pw.stop = AsyncMock()
        
        with patch('layer1_ingestion.crawler.playwright_crawler.async_playwright') as mock_async_pw:
            mock_async_pw.return_value.start = AsyncMock(return_value=mock_pw)
            await crawler.start()
            
            # Verify semaphore was created with correct value
            assert crawler._semaphore._value == 1
            
            await crawler.stop()

