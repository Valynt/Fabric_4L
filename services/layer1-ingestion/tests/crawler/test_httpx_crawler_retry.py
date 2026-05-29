"""Tests for HttpxCrawler retry logic.

Covers:
- Retry on retriable HTTP status codes (429, 5xx)
- Retry on transient network errors (TimeoutException, NetworkError)
- Retry-After header is respected
- max_retries=0 disables retries
- retry_count field populated on FastPathResult
- get_stats() exposes total_retries
- Non-retriable errors (4xx) do not trigger retry
- Exponential backoff with jitter (_compute_backoff)
- Success on a later attempt is reported with correct retry_count
"""

from __future__ import annotations

from unittest.mock import MagicMock

import httpx
import pytest
import respx
from httpx import Response
from layer1_ingestion.crawler.httpx_crawler import (
    FastPathResult,
    HttpxCrawler,
    HttpxCrawlerConfig,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _no_sleep_config(max_retries: int = 3) -> HttpxCrawlerConfig:
    """Config with zero backoff so tests don't actually sleep."""
    return HttpxCrawlerConfig(
        max_retries=max_retries,
        retry_backoff_base=0.0,
        retry_backoff_max=0.0,
        retry_jitter=False,
        retry_on_status_codes=[429, 500, 502, 503, 504],
    )


# ---------------------------------------------------------------------------
# Retry on 5xx status codes
# ---------------------------------------------------------------------------

class TestRetryOn5xx:
    """Crawler retries on retriable 5xx responses."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_503_succeeds_eventually(self) -> None:
        """After two 503 responses the third attempt returns 200."""
        route = respx.get("https://example.com/page")
        route.side_effect = [
            Response(503, text="Service Unavailable"),
            Response(503, text="Service Unavailable"),
            Response(200, text="<html><head><title>OK</title></head><body><p>content here</p></body></html>"),
        ]

        async with HttpxCrawler(_no_sleep_config(max_retries=3)) as crawler:
            result = await crawler.fetch("https://example.com/page")

        assert result.status_code == 200
        assert result.retry_count == 2
        assert crawler._total_retries == 2

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_500_exhausts_all_attempts(self) -> None:
        """All attempts fail with 500; final result is an error result."""
        route = respx.get("https://example.com/page")
        route.side_effect = [
            Response(500, text="Internal Server Error"),
            Response(500, text="Internal Server Error"),
            Response(500, text="Internal Server Error"),
            Response(500, text="Internal Server Error"),
        ]

        async with HttpxCrawler(_no_sleep_config(max_retries=3)) as crawler:
            result = await crawler.fetch("https://example.com/page")

        assert result.status_code == 500
        assert result.content_type == "http_error"
        # 3 retries attempted before final failure
        assert result.retry_count == 3
        assert crawler._total_retries == 3

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_502_and_503(self) -> None:
        """Both 502 and 503 are retriable status codes."""
        for status in [502, 503]:
            route = respx.get(f"https://example.com/{status}")
            route.side_effect = [
                Response(status, text="error"),
                Response(200, text="<html><body><p>ok content here</p></body></html>"),
            ]

        async with HttpxCrawler(_no_sleep_config(max_retries=2)) as crawler:
            for status in [502, 503]:
                result = await crawler.fetch(f"https://example.com/{status}")
                assert result.status_code == 200
                assert result.retry_count == 1

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_retry_on_404(self) -> None:
        """404 is not a retriable status code; fetch returns immediately."""
        respx.get("https://example.com/missing").mock(return_value=Response(404, text="Not Found"))

        config = _no_sleep_config(max_retries=3)
        async with HttpxCrawler(config) as crawler:
            result = await crawler.fetch("https://example.com/missing")

        assert result.status_code == 404
        assert result.retry_count == 0
        assert crawler._total_retries == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_retry_on_403(self) -> None:
        """403 Forbidden is not a retriable status code."""
        respx.get("https://example.com/forbidden").mock(return_value=Response(403, text="Forbidden"))

        config = _no_sleep_config(max_retries=3)
        async with HttpxCrawler(config) as crawler:
            result = await crawler.fetch("https://example.com/forbidden")

        assert result.status_code == 403
        assert result.retry_count == 0


# ---------------------------------------------------------------------------
# Retry on 429 with Retry-After header
# ---------------------------------------------------------------------------

class TestRetryOn429:
    """Crawler retries on 429 responses and respects Retry-After."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_retry_on_429_succeeds(self) -> None:
        """429 triggers retry; second attempt returns 200."""
        route = respx.get("https://example.com/api")
        route.side_effect = [
            Response(429, text="Too Many Requests"),
            Response(200, text="<html><body><p>Success content</p></body></html>"),
        ]

        async with HttpxCrawler(_no_sleep_config(max_retries=2)) as crawler:
            result = await crawler.fetch("https://example.com/api")

        assert result.status_code == 200
        assert result.retry_count == 1

    @pytest.mark.asyncio
    async def test_retry_after_header_used_as_backoff(self) -> None:
        """_compute_backoff returns Retry-After value when header is present."""
        crawler = HttpxCrawler(_no_sleep_config())

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.headers = httpx.Headers({"retry-after": "42"})

        delay = crawler._compute_backoff(attempt=0, response=mock_response)
        assert delay == 42.0

    @pytest.mark.asyncio
    async def test_retry_after_header_invalid_falls_back(self) -> None:
        """Non-numeric Retry-After header falls back to exponential backoff."""
        config = HttpxCrawlerConfig(
            max_retries=3,
            retry_backoff_base=1.0,
            retry_backoff_max=60.0,
            retry_jitter=False,
        )
        crawler = HttpxCrawler(config)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.headers = httpx.Headers({"retry-after": "not-a-number"})

        delay = crawler._compute_backoff(attempt=1, response=mock_response)
        # With jitter=False and attempt=1: 1.0 * 2^1 = 2.0
        assert delay == 2.0


# ---------------------------------------------------------------------------
# Retry on transient network errors
# ---------------------------------------------------------------------------

class TestRetryOnNetworkErrors:
    """Crawler retries on transient network-level failures."""

    @pytest.mark.asyncio
    async def test_retry_on_timeout(self) -> None:
        """TimeoutException triggers retry; subsequent success is returned."""
        call_count = 0

        async def _mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count < 3:
                raise httpx.TimeoutException("Timed out", request=MagicMock())
            return Response(200, text="<html><body><p>finally worked</p></body></html>")

        config = _no_sleep_config(max_retries=3)
        async with HttpxCrawler(config) as crawler:
            crawler._client.get = _mock_get
            result = await crawler.fetch("https://example.com/slow")

        assert result.status_code == 200
        assert result.retry_count == 2
        assert crawler._total_retries == 2

    @pytest.mark.asyncio
    async def test_retry_timeout_exhausted(self) -> None:
        """All attempts timeout; final result has status 504."""
        async def _always_timeout(url, **kwargs):
            raise httpx.TimeoutException("Timed out", request=MagicMock())

        config = _no_sleep_config(max_retries=2)
        async with HttpxCrawler(config) as crawler:
            crawler._client.get = _always_timeout
            result = await crawler.fetch("https://example.com/slow")

        assert result.status_code == 504
        assert result.content_type == "timeout"
        assert result.retry_count == 2

    @pytest.mark.asyncio
    async def test_retry_on_network_error(self) -> None:
        """NetworkError triggers retry; subsequent success is returned."""
        call_count = 0

        async def _mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("Connection refused", request=MagicMock())
            return Response(200, text="<html><body><p>recovered content here</p></body></html>")

        config = _no_sleep_config(max_retries=2)
        async with HttpxCrawler(config) as crawler:
            crawler._client.get = _mock_get
            result = await crawler.fetch("https://example.com/page")

        assert result.status_code == 200
        assert result.retry_count == 1

    @pytest.mark.asyncio
    async def test_non_retriable_exception_no_retry(self) -> None:
        """Unexpected exceptions (e.g. ValueError) do not trigger retry."""
        call_count = 0

        async def _mock_get(url, **kwargs):
            nonlocal call_count
            call_count += 1
            raise ValueError("Unexpected error")

        config = _no_sleep_config(max_retries=3)
        async with HttpxCrawler(config) as crawler:
            crawler._client.get = _mock_get
            result = await crawler.fetch("https://example.com/page")

        # Only called once — no retry for non-network exceptions
        assert call_count == 1
        assert result.status_code == 0
        assert "ValueError" in result.content_type
        assert result.retry_count == 0


# ---------------------------------------------------------------------------
# max_retries=0 disables retries entirely
# ---------------------------------------------------------------------------

class TestRetryDisabled:
    """When max_retries=0, no retries are attempted."""

    @respx.mock
    @pytest.mark.asyncio
    async def test_no_retry_when_max_retries_zero(self) -> None:
        """max_retries=0 means a single attempt only — no retry on 503."""
        respx.get("https://example.com/page").mock(return_value=Response(503, text="Service Unavailable"))

        config = _no_sleep_config(max_retries=0)
        async with HttpxCrawler(config) as crawler:
            result = await crawler.fetch("https://example.com/page")

        assert result.status_code == 503
        assert result.retry_count == 0
        assert crawler._total_retries == 0


# ---------------------------------------------------------------------------
# Compute backoff formula
# ---------------------------------------------------------------------------

class TestComputeBackoff:
    """Tests for the _compute_backoff method."""

    def test_exponential_growth_without_jitter(self) -> None:
        """Backoff doubles with each attempt when jitter is disabled."""
        config = HttpxCrawlerConfig(
            retry_backoff_base=1.0,
            retry_backoff_max=60.0,
            retry_jitter=False,
        )
        crawler = HttpxCrawler(config)

        assert crawler._compute_backoff(0) == 1.0  # 1.0 * 2^0
        assert crawler._compute_backoff(1) == 2.0  # 1.0 * 2^1
        assert crawler._compute_backoff(2) == 4.0  # 1.0 * 2^2
        assert crawler._compute_backoff(3) == 8.0  # 1.0 * 2^3

    def test_backoff_capped_at_max(self) -> None:
        """Backoff never exceeds retry_backoff_max."""
        config = HttpxCrawlerConfig(
            retry_backoff_base=1.0,
            retry_backoff_max=5.0,
            retry_jitter=False,
        )
        crawler = HttpxCrawler(config)

        assert crawler._compute_backoff(10) == 5.0

    def test_jitter_adds_randomness(self) -> None:
        """With jitter enabled, two calls for the same attempt differ."""
        config = HttpxCrawlerConfig(
            retry_backoff_base=10.0,
            retry_backoff_max=60.0,
            retry_jitter=True,
        )
        crawler = HttpxCrawler(config)

        results = {crawler._compute_backoff(2) for _ in range(20)}
        # With jitter we expect multiple distinct values across 20 calls
        assert len(results) > 1

    def test_no_retry_after_header_falls_through(self) -> None:
        """No retry-after header means exponential backoff is used."""
        config = HttpxCrawlerConfig(
            retry_backoff_base=2.0,
            retry_backoff_max=60.0,
            retry_jitter=False,
        )
        crawler = HttpxCrawler(config)

        mock_response = MagicMock(spec=httpx.Response)
        mock_response.headers = httpx.Headers({})  # No retry-after header

        delay = crawler._compute_backoff(attempt=1, response=mock_response)
        assert delay == 4.0  # 2.0 * 2^1


# ---------------------------------------------------------------------------
# get_stats() exposes total_retries
# ---------------------------------------------------------------------------

class TestGetStats:
    """get_stats() includes retry configuration and cumulative retry counts."""

    def test_stats_include_retry_config(self) -> None:
        config = HttpxCrawlerConfig(max_retries=5)
        crawler = HttpxCrawler(config)

        stats = crawler.get_stats()
        assert stats["config"]["max_retries"] == 5
        assert "total_retries" in stats
        assert stats["total_retries"] == 0

    @respx.mock
    @pytest.mark.asyncio
    async def test_total_retries_accumulates_across_fetches(self) -> None:
        """total_retries sums up retries from all fetch calls."""
        route = respx.get("https://example.com/page")
        route.side_effect = [
            Response(503),
            Response(200, text="<html><body><p>content</p></body></html>"),
            Response(503),
            Response(503),
            Response(200, text="<html><body><p>content</p></body></html>"),
        ]

        async with HttpxCrawler(_no_sleep_config(max_retries=3)) as crawler:
            await crawler.fetch("https://example.com/page")  # 1 retry
            await crawler.fetch("https://example.com/page")  # 2 retries

        stats = crawler.get_stats()
        assert stats["total_retries"] == 3  # 1 + 2


# ---------------------------------------------------------------------------
# retry_count on FastPathResult
# ---------------------------------------------------------------------------

class TestFastPathResultRetryCount:
    """retry_count field on FastPathResult defaults to zero."""

    def test_default_retry_count_is_zero(self) -> None:
        result = FastPathResult(
            url="https://example.com",
            status_code=200,
            html="<html></html>",
            title="Title",
            text_content="Content",
            content_hash="abc123",
        )
        assert result.retry_count == 0

    def test_retry_count_can_be_set(self) -> None:
        result = FastPathResult(
            url="https://example.com",
            status_code=200,
            html="<html></html>",
            title="Title",
            text_content="Content",
            content_hash="abc123",
            retry_count=2,
        )
        assert result.retry_count == 2
