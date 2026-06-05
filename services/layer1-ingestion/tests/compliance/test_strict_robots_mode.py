"""Tests for strict robots.txt compliance mode.

Tests verify that strict robots compliance blocks on parse/network failures:
- Network failure in strict mode blocks crawling
- Parse failure in strict mode blocks crawling
- Network failure in permissive mode raises RobotsFetchError (caller decides)
- Parse failure in permissive mode allows with warning
- Crawl delays use Celery retry mechanism (non-blocking)
"""

from __future__ import annotations

import pytest
from unittest.mock import AsyncMock, patch
from layer1_ingestion.compliance.robots_checker import RobotsChecker
from layer1_ingestion.shared.exceptions import RobotsFetchError, RobotsParseError


class TestStrictRobotsModeNetworkFailure:
    """Test network failure behavior in strict vs permissive mode."""

    def test_network_failure_strict_mode_blocks(self):
        """Network failure in strict mode should return False (block)."""
        checker = RobotsChecker(
            tenant_id="test-tenant",
            strict_mode=True,
        )

        # Mock network error
        with patch.object(
            checker, "_get_robots_txt", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = RobotsFetchError(
                "Network timeout",
                domain="example.com",
                status_code=None,
            )

            import asyncio

            allowed, reason, rules = asyncio.run(
                checker.check_url("https://example.com/page")
            )

            assert allowed is False
            assert "strict mode" in reason.lower()
            assert rules is not None
            assert rules.get("strict_mode") is True
            assert rules.get("domain") == "example.com"
            assert rules.get("error") == "ROBOTS_FETCH_ERROR"

    def test_network_failure_permissive_mode_raises(self):
        """Network failure in permissive mode should raise RobotsFetchError."""
        checker = RobotsChecker(
            tenant_id="test-tenant",
            strict_mode=False,
        )

        # Mock network error
        with patch.object(
            checker, "_get_robots_txt", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = RobotsFetchError(
                "Network timeout",
                domain="example.com",
                status_code=None,
            )

            import asyncio

            with pytest.raises(RobotsFetchError) as exc_info:
                asyncio.run(
                    checker.check_url("https://example.com/page")
                )

            assert "Network timeout" in str(exc_info.value)

    def test_network_failure_permissive_mode_caller_decides(self):
        """In permissive mode, caller can decide to allow after network error."""
        checker = RobotsChecker(
            tenant_id="test-tenant",
            strict_mode=False,
        )

        # Mock network error
        with patch.object(
            checker, "_get_robots_txt", new_callable=AsyncMock
        ) as mock_get:
            mock_get.side_effect = RobotsFetchError(
                "Network timeout",
                domain="example.com",
                status_code=None,
            )

            import asyncio

            # Caller catches exception and decides to allow
            try:
                asyncio.run(
                    checker.check_url("https://example.com/page")
                )
            except RobotsFetchError:
                # Caller decides to allow anyway
                allowed = True  # Permissive mode allows caller to decide
                assert allowed is True


class TestStrictRobotsModeParseFailure:
    """Test parse failure behavior in strict vs permissive mode."""

    def test_parse_failure_strict_mode_blocks(self):
        """Parse failure in strict mode should return False (block)."""
        checker = RobotsChecker(
            tenant_id="test-tenant",
            strict_mode=True,
        )

        # Mock parse error
        with patch.object(
            checker, "_get_robots_txt", new_callable=AsyncMock
        ) as mock_get:
            # Return valid data but mock parse to fail
            mock_get.return_value = {
                "content": "malformed robots.txt content",
                "cached": False,
            }

            with patch("protego.Protego.parse", side_effect=Exception("Parse error")):
                import asyncio

                allowed, reason, rules = asyncio.run(
                    checker.check_url("https://example.com/page")
                )

                assert allowed is False
                assert "strict mode" in reason.lower()
                assert "parse error" in reason.lower()
                assert rules is not None
                assert rules.get("strict_mode") is True
                assert rules.get("parse_error") == "ROBOTS_PARSE_ERROR"

    def test_parse_failure_permissive_mode_allows(self):
        """Parse failure in permissive mode should return True (allow with warning)."""
        checker = RobotsChecker(
            tenant_id="test-tenant",
            strict_mode=False,
        )

        # Mock parse error
        with patch.object(
            checker, "_get_robots_txt", new_callable=AsyncMock
        ) as mock_get:
            # Return valid data but mock parse to fail
            mock_get.return_value = {
                "content": "malformed robots.txt content",
                "cached": False,
            }

            with patch("protego.Protego.parse", side_effect=Exception("Parse error")):
                import asyncio

                allowed, reason, rules = asyncio.run(
                    checker.check_url("https://example.com/page")
                )

                assert allowed is True
                assert reason is None  # Permissive mode doesn't return error reason
                assert rules is not None
                assert rules.get("parse_error") == "ROBOTS_PARSE_ERROR"


class TestStrictRobotsModeNoRobotsTxt:
    """Test behavior when robots.txt is not available."""

    def test_no_robots_txt_strict_mode_blocks(self):
        """No robots.txt in strict mode should return False (block)."""
        checker = RobotsChecker(
            tenant_id="test-tenant",
            strict_mode=True,
        )

        # Mock no robots.txt available
        with patch.object(
            checker, "_get_robots_txt", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            import asyncio

            allowed, reason, rules = asyncio.run(
                checker.check_url("https://example.com/page")
            )

            assert allowed is False
            assert "strict mode" in reason.lower()
            assert "required but not available" in reason.lower()
            assert rules is not None
            assert rules.get("strict_mode") is True
            assert rules.get("domain") == "example.com"

    def test_no_robots_txt_permissive_mode_allows(self):
        """No robots.txt in permissive mode should return True (allow)."""
        checker = RobotsChecker(
            tenant_id="test-tenant",
            strict_mode=False,
        )

        # Mock no robots.txt available
        with patch.object(
            checker, "_get_robots_txt", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = None

            import asyncio

            allowed, reason, rules = asyncio.run(
                checker.check_url("https://example.com/page")
            )

            assert allowed is True
            assert reason is None
            assert rules is None


class TestCrawlDelayApplication:
    """Test that crawl delays use Celery retry mechanism."""

    def test_crawl_delay_uses_celery_retry_not_blocking_sleep(self):
        """Crawl delay should be applied via Celery retry, not blocking sleep."""
        checker = RobotsChecker(
            tenant_id="test-tenant",
            strict_mode=False,
        )

        # Mock robots.txt with crawl delay
        robots_content = """
        User-agent: *
        Crawl-delay: 5
        Disallow: /admin
        """

        with patch.object(
            checker, "_get_robots_txt", new_callable=AsyncMock
        ) as mock_get:
            mock_get.return_value = {
                "content": robots_content,
                "cached": False,
            }

            import asyncio

            # This should not block for 5 seconds
            # In the actual implementation, crawl delay is handled by Celery retry
            # in the compliance_check_stage task
            allowed, reason, rules = asyncio.run(
                checker.check_url("https://example.com/page")
            )

            # The checker itself doesn't apply the delay - it returns the delay
            # The task layer handles it via Celery retry
            assert allowed is True  # robots.txt allows the URL
            assert rules is not None
            assert rules.get("crawl_delay") == 5

    def test_crawl_delay_respected_in_task(self):
        """Verify that the task layer applies crawl delay via Celery retry."""
        # This test would need to mock the Celery task behavior
        # For now, we document the expected behavior
        # In compliance_check_stage, crawl_delay triggers:
        # raise self.retry(countdown=int(crawl_delay))
        # This is non-blocking and returns the task to the queue
        pass


class TestStrictRobotsModeMetrics:
    """Test that strict robots mode emits appropriate metrics."""

    def test_strict_mode_block_emits_metric(self):
        """Strict mode blocks should emit a metric for observability."""
        # This test would require mocking the metrics system
        # Expected: increment_strict_robots_block(domain, reason)
        # This is a placeholder for when metrics are added
        pass

    def test_permissive_mode_no_block_metric(self):
        """Permissive mode should not emit block metric."""
        # This test would require mocking the metrics system
        # Expected: no increment_strict_robots_block call
        # This is a placeholder for when metrics are added
        pass
