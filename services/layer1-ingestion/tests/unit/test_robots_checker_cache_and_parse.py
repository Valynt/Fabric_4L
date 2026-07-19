from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from layer1_ingestion.compliance.robots_checker import RobotsChecker
from layer1_ingestion.shared.exceptions import InvalidTenantContextError, RobotsParseError


def test_parse_robots_txt_returns_common_agent_rules() -> None:
    checker = RobotsChecker(tenant_id="00000000-0000-0000-0000-000000000001")

    rules = checker._parse_robots_txt("""
        User-agent: *
        Crawl-delay: 7
        Disallow: /private
        """)

    assert rules["*"]["crawl_delay"] == 7.0
    assert set(rules) == {"*", "ValueFabricBot", "ValueFabricBot/1.0", "Googlebot"}


def test_parse_robots_txt_wraps_parser_failures_without_attribute_error() -> None:
    checker = RobotsChecker(tenant_id="00000000-0000-0000-0000-000000000001")

    with patch(
        "layer1_ingestion.compliance.robots_checker.Protego.parse", side_effect=Exception("boom")
    ):
        with pytest.raises(RobotsParseError) as exc_info:
            checker._parse_robots_txt("User-agent: *\nDisallow: /private")

    assert "Failed to parse robots.txt content" in str(exc_info.value)


def test_get_cached_robots_txt_rejects_invalid_tenant_before_database_access() -> None:
    checker = RobotsChecker(tenant_id="not-a-uuid")

    with patch("layer1_ingestion.compliance.robots_checker.get_db_session") as mock_session:
        with pytest.raises(InvalidTenantContextError):
            checker._get_cached_robots_txt("example.com")

    mock_session.assert_not_called()


def test_cache_robots_txt_rejects_invalid_tenant_before_database_access() -> None:
    checker = RobotsChecker(tenant_id="not-a-uuid")

    with patch("layer1_ingestion.compliance.robots_checker.get_db_session") as mock_session:
        with pytest.raises(InvalidTenantContextError):
            checker._cache_robots_txt(
                domain="example.com",
                url="https://example.com/robots.txt",
                content="User-agent: *",
                rules={},
                http_status=200,
            )

    mock_session.assert_not_called()


def test_get_cached_robots_txt_returns_global_public_cache_entry() -> None:
    checker = RobotsChecker(tenant_id="00000000-0000-0000-0000-000000000001")
    cache_entry = MagicMock()
    cache_entry.content = "User-agent: *"
    cache_entry.rules = {"*": {"crawl_delay": None}}
    cache_entry.fetched_at = "fetched"
    cache_entry.expires_at = "expires"

    query = MagicMock()
    query.filter.return_value = query
    query.first.return_value = cache_entry
    session = MagicMock()
    session.query.return_value = query
    context = MagicMock()
    context.__enter__.return_value = session
    context.__exit__.return_value = None

    with patch(
        "layer1_ingestion.compliance.robots_checker.get_db_session", return_value=context
    ) as mock_session:
        cached = checker._get_cached_robots_txt("example.com")

    mock_session.assert_called_once()
    assert mock_session.call_args.kwargs["require_tenant"] is False
    assert dict(cached) == {
        "content": "User-agent: *",
        "rules": {"*": {"crawl_delay": None}},
        "fetched_at": "fetched",
        "expires_at": "expires",
    }
