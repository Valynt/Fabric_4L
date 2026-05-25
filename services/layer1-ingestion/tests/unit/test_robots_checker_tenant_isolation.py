"""Tenant isolation tests for RobotsChecker cache operations.

SECURITY: robots_txt_cache has tenant_id and must be scoped per tenant.
"""
from __future__ import annotations

from contextlib import contextmanager
from uuid import uuid4

import pytest
from unittest.mock import MagicMock, Mock, patch


def _make_recording_session():
    """Create a mock session that records query filter calls."""
    session = MagicMock()
    session.__enter__ = Mock(return_value=session)
    session.__exit__ = Mock(return_value=False)
    return session


class TestRobotsCheckerTenantIsolation:
    """Verify RobotsChecker respects tenant boundaries for cache read/write."""

    def test_cache_read_applies_tenant_filter(self) -> None:
        """_get_cached_robots_txt must include tenant_id in query when provided."""
        from value_fabric.layer1.compliance.robots_checker import RobotsChecker

        tenant_id = str(uuid4())
        checker = RobotsChecker(tenant_id=tenant_id)
        mock_entry = Mock()

        session = _make_recording_session()
        # Build a mock query chain that records filter calls
        query_chain = MagicMock()
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = mock_entry
        session.query.return_value = query_chain

        with patch("value_fabric.layer1.compliance.robots_checker.get_db_session", return_value=session):
            result = checker._get_cached_robots_txt("example.com")

        assert result is not None
        # Verify tenant filter was applied
        filter_calls = [call for call in query_chain.filter.call_args_list]
        assert len(filter_calls) >= 2, "Must filter by domain and tenant_id"

    def test_cache_read_without_tenant_uses_domain_only(self) -> None:
        """_get_cached_robots_txt without tenant_id must not apply tenant filter."""
        from value_fabric.layer1.compliance.robots_checker import RobotsChecker

        checker = RobotsChecker()  # No tenant_id
        mock_entry = Mock()

        session = _make_recording_session()
        query_chain = MagicMock()
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = mock_entry
        session.query.return_value = query_chain

        with patch("value_fabric.layer1.compliance.robots_checker.get_db_session", return_value=session):
            result = checker._get_cached_robots_txt("example.com")

        assert result is not None
        # Without tenant_id, only domain + expires filters should be applied
        filter_calls = [call for call in query_chain.filter.call_args_list]
        assert len(filter_calls) == 1, "Must not apply tenant filter when tenant_id is None"

    def test_cache_write_applies_tenant_filter(self) -> None:
        """_cache_robots_txt must query existing entries with tenant_id filter."""
        from value_fabric.layer1.compliance.robots_checker import RobotsChecker

        tenant_id = str(uuid4())
        checker = RobotsChecker(tenant_id=tenant_id)

        session = _make_recording_session()
        query_chain = MagicMock()
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = None  # No existing entry
        session.query.return_value = query_chain

        # Patch RobotsTxtCache constructor to avoid real DB model instantiation
        with patch("value_fabric.layer1.compliance.robots_checker.get_db_session", return_value=session):
            with patch("value_fabric.layer1.compliance.robots_checker.RobotsTxtCache") as mock_model:
                mock_model_instance = Mock()
                mock_model.return_value = mock_model_instance
                checker._cache_robots_txt(
                    domain="example.com",
                    url="https://example.com/robots.txt",
                    content="User-agent: *\nDisallow:",
                    rules={},
                    http_status=200,
                )

        # Verify tenant filter was applied to existing query
        filter_calls = [call for call in query_chain.filter.call_args_list]
        assert len(filter_calls) >= 2, "Must filter existing entries by domain and tenant_id"

    def test_cache_write_sets_tenant_id_on_new_entry(self) -> None:
        """_cache_robots_txt must set tenant_id when creating a new cache entry."""
        from value_fabric.layer1.compliance.robots_checker import RobotsChecker

        tenant_id = str(uuid4())
        checker = RobotsChecker(tenant_id=tenant_id)

        session = _make_recording_session()
        query_chain = MagicMock()
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = None
        session.query.return_value = query_chain

        with patch("value_fabric.layer1.compliance.robots_checker.get_db_session", return_value=session):
            with patch("value_fabric.layer1.compliance.robots_checker.RobotsTxtCache") as mock_model:
                mock_instance = Mock()
                mock_model.return_value = mock_instance
                checker._cache_robots_txt(
                    domain="example.com",
                    url="https://example.com/robots.txt",
                    content="User-agent: *\nDisallow:",
                    rules={},
                    http_status=200,
                )

        # Verify new entry was created with tenant_id
        assert mock_model.called, "RobotsTxtCache constructor must be called for new entry"
        _, kwargs = mock_model.call_args
        assert kwargs.get("tenant_id") is not None
        assert str(kwargs.get("tenant_id")) == tenant_id

    def test_cache_isolation_between_tenants(self) -> None:
        """Tenant B must not read Tenant A's cached robots.txt."""
        from value_fabric.layer1.compliance.robots_checker import RobotsChecker

        tenant_a = str(uuid4())
        tenant_b = str(uuid4())

        checker_a = RobotsChecker(tenant_id=tenant_a)
        checker_b = RobotsChecker(tenant_id=tenant_b)

        # Tenant A has a cached entry
        mock_entry_a = Mock()
        mock_entry_a.content = "User-agent: *\nDisallow: /private"

        session = _make_recording_session()
        query_chain = MagicMock()
        query_chain.filter.return_value = query_chain
        query_chain.first.return_value = mock_entry_a
        session.query.return_value = query_chain

        with patch("value_fabric.layer1.compliance.robots_checker.get_db_session", return_value=session):
            result_a = checker_a._get_cached_robots_txt("example.com")
            assert result_a is not None

        # For tenant B, simulate no matching entry
        query_chain_b = MagicMock()
        query_chain_b.filter.return_value = query_chain_b
        query_chain_b.first.return_value = None
        session_b = _make_recording_session()
        session_b.query.return_value = query_chain_b

        with patch("value_fabric.layer1.compliance.robots_checker.get_db_session", return_value=session_b):
            result_b = checker_b._get_cached_robots_txt("example.com")
            assert result_b is None, "Tenant B must not see Tenant A's cache"
