"""Regression tests for PROD-P0-001: SSRF bypass in browser/fallback crawler path.

Validates that URL safety checks are enforced at:
1. crawl_url_with_routing() — routing entry point
2. _execute_browser_path() — browser path execution
3. PlaywrightCrawler.crawl_url() — crawler boundary (defense-in-depth)
"""

from __future__ import annotations

import socket
from unittest.mock import AsyncMock, MagicMock, Mock, patch

import pytest

from layer1_ingestion.compliance.url_safety import URLSafetyError


@pytest.mark.security
class TestExecuteBrowserPathSSRF:
    """_execute_browser_path must reject unsafe URLs before calling Playwright."""

    @pytest.mark.asyncio
    async def test_rejects_loopback(self, monkeypatch):
        """_execute_browser_path must block 127.0.0.1 before crawl."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 0))],
        )
        from layer1_ingestion.shared.tasks import _execute_browser_path

        with pytest.raises(URLSafetyError) as exc:
            await _execute_browser_path("http://127.0.0.1/", {})
        assert exc.value.reason_code == "IP_RANGE_BLOCKED"

    @pytest.mark.asyncio
    async def test_rejects_metadata_ip(self, monkeypatch):
        """_execute_browser_path must block 169.254.169.254 before crawl."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("169.254.169.254", 0))],
        )
        from layer1_ingestion.shared.tasks import _execute_browser_path

        with pytest.raises(URLSafetyError) as exc:
            await _execute_browser_path("http://169.254.169.254/latest/meta-data/", {})
        assert exc.value.reason_code == "IP_RANGE_BLOCKED"

    @pytest.mark.asyncio
    async def test_rejects_private_rfc1918(self, monkeypatch):
        """_execute_browser_path must block 10.0.0.1 before crawl."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("10.0.0.1", 0))],
        )
        from layer1_ingestion.shared.tasks import _execute_browser_path

        with pytest.raises(URLSafetyError) as exc:
            await _execute_browser_path("http://10.0.0.1/internal", {})
        assert exc.value.reason_code == "IP_RANGE_BLOCKED"

    @pytest.mark.asyncio
    async def test_safe_public_url_passes_with_mock(self, monkeypatch):
        """Safe public URL reaches the mocked crawler; no exception raised."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("1.1.1.1", 0))],
        )
        from layer1_ingestion.shared.tasks import _execute_browser_path

        mock_crawler = AsyncMock()
        mock_crawler.crawl_url = AsyncMock(
            return_value=Mock(
                status_code=True,
                html_content="<html></html>",
                title="Safe",
                error=None,
                final_url="https://safe.example.com/",
                blocked_resources=0,
                scroll_triggered=False,
            )
        )

        with patch(
            "layer1_ingestion.shared.tasks.crawl.PlaywrightCrawler",
            return_value=mock_crawler,
        ):
            mock_crawler.__aenter__ = AsyncMock(return_value=mock_crawler)
            mock_crawler.__aexit__ = AsyncMock(return_value=False)
            result = await _execute_browser_path("https://safe.example.com/", {})

        assert result["status_code"] is True
        mock_crawler.crawl_url.assert_awaited_once()


@pytest.mark.security
class TestPlaywrightCrawlerBoundarySSRF:
    """PlaywrightCrawler.crawl_url must reject unsafe URLs even when called directly."""

    @pytest.mark.asyncio
    async def test_rejects_loopback_when_called_directly(self, monkeypatch):
        """Direct call to crawl_url with loopback must raise URLSafetyError."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 0))],
        )
        from layer1_ingestion.crawler.playwright_crawler import PlaywrightCrawler

        crawler = PlaywrightCrawler(enable_telemetry=False)
        with pytest.raises(URLSafetyError) as exc:
            await crawler.crawl_url("http://127.0.0.1/")
        assert exc.value.reason_code == "IP_RANGE_BLOCKED"

    @pytest.mark.asyncio
    async def test_rejects_metadata_when_called_directly(self, monkeypatch):
        """Direct call to crawl_url with metadata IP must raise URLSafetyError."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("169.254.169.254", 0))],
        )
        from layer1_ingestion.crawler.playwright_crawler import PlaywrightCrawler

        crawler = PlaywrightCrawler(enable_telemetry=False)
        with pytest.raises(URLSafetyError) as exc:
            await crawler.crawl_url("http://169.254.169.254/latest/meta-data/")
        assert exc.value.reason_code == "IP_RANGE_BLOCKED"

    @pytest.mark.asyncio
    async def test_safe_url_reaches_mocked_page(self, monkeypatch):
        """Safe public URL must proceed to mocked page navigation."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("1.1.1.1", 0))],
        )
        from layer1_ingestion.crawler.playwright_crawler import PlaywrightCrawler

        crawler = PlaywrightCrawler(enable_telemetry=False)
        mock_page = AsyncMock()
        mock_page.goto = AsyncMock(return_value=Mock(status=200, headers={"content-type": "text/html"}))
        mock_page.content = AsyncMock(return_value="<html><body>OK</body></html>")
        mock_page.title = AsyncMock(return_value="OK")
        mock_page.url = "https://safe.example.com/final"

        crawler._context = MagicMock()
        crawler._context.new_page = AsyncMock(return_value=mock_page)
        crawler._semaphore = AsyncMock()
        crawler._semaphore.__aenter__ = AsyncMock(return_value=None)
        crawler._semaphore.__aexit__ = AsyncMock(return_value=False)

        result = await crawler.crawl_url("https://safe.example.com/")
        assert result.status_code == 200
        mock_page.goto.assert_awaited_once()
        assert mock_page.goto.await_args[0][0] == "https://safe.example.com/"


@pytest.mark.security
class TestCrawlUrlWithRoutingSSRF:
    """crawl_url_with_routing must reject unsafe URLs before routing decision."""

    @pytest.mark.asyncio
    async def test_rejects_loopback_before_routing(self, monkeypatch):
        """Unsafe URL must be blocked before router decides fast vs browser path."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("127.0.0.1", 0))],
        )
        from layer1_ingestion.shared.tasks import crawl_url_with_routing
        from uuid import uuid4

        job_id = str(uuid4())
        tenant_id = str(uuid4())

        # Mock DB session so we don't need a real database
        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_job = MagicMock()
        mock_job.target_id = str(uuid4())
        mock_session.query.return_value.get.return_value = mock_job
        mock_target = MagicMock()
        mock_target.extraction_config = None
        mock_session.query.return_value.get.side_effect = [mock_job, mock_target]

        with patch("layer1_ingestion.shared.tasks.crawl.get_db_session", return_value=mock_session):
            with pytest.raises(URLSafetyError) as exc:
                await crawl_url_with_routing(job_id, "http://127.0.0.1/", tenant_id)
            assert exc.value.reason_code == "IP_RANGE_BLOCKED"

    @pytest.mark.asyncio
    async def test_rejects_metadata_before_routing(self, monkeypatch):
        """Metadata IP must be blocked before router decides."""
        monkeypatch.setattr(
            socket,
            "getaddrinfo",
            lambda *args, **kwargs: [(None, None, None, None, ("169.254.169.254", 0))],
        )
        from layer1_ingestion.shared.tasks import crawl_url_with_routing
        from uuid import uuid4

        job_id = str(uuid4())
        tenant_id = str(uuid4())

        mock_session = MagicMock()
        mock_session.__enter__ = Mock(return_value=mock_session)
        mock_session.__exit__ = Mock(return_value=False)
        mock_job = MagicMock()
        mock_job.target_id = str(uuid4())
        mock_session.query.return_value.get.side_effect = [mock_job, MagicMock()]

        with patch("layer1_ingestion.shared.tasks.crawl.get_db_session", return_value=mock_session):
            with pytest.raises(URLSafetyError) as exc:
                await crawl_url_with_routing(job_id, "http://169.254.169.254/latest/meta-data/", tenant_id)
            assert exc.value.reason_code == "IP_RANGE_BLOCKED"
