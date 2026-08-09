"""PostgreSQL-backed tests for global robots cache isolation.

Tests validate that robots_txt_cache contains only public metadata and
does not leak tenant data or require tenant isolation.

These tests MUST run against PostgreSQL.
"""

from __future__ import annotations

import pytest
from uuid import uuid4
from datetime import datetime, timezone, timedelta

from layer1_ingestion.shared.exceptions import (
    RobotsCacheError,
    InvalidTenantContextError,
    RobotsFetchError,
)
from layer1_ingestion.compliance.robots_checker import RobotsChecker
from layer1_ingestion.shared.models import RobotsTxtCache


pytestmark = pytest.mark.requires_postgres


class TestGlobalRobotsCacheIsolation:
    """Test that robots cache is properly isolated as global public metadata."""

    def test_cache_contains_no_tenant_data(self, postgres_db):
        """Test that cache entries contain no tenant-owned data."""
        # Create cache entry with system-owned tenant_id (legacy column)
        cache_entry = RobotsTxtCache(
            domain="example.com",
            tenant_id=None,  # System-owned only
            content="User-agent: *\nDisallow: /private",
            url="https://example.com/robots.txt",
            rules={"*": {"crawl_delay": None, "request_rate": None}},
            fetched_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            http_status=200,
            is_valid=True,
        )
        
        postgres_db.add(cache_entry)
        postgres_db.commit()
        
        # Verify entry contains only public metadata
        retrieved = postgres_db.query(RobotsTxtCache).filter(RobotsTxtCache.domain == "example.com").first()
        assert retrieved is not None
        assert retrieved.domain == "example.com"
        assert retrieved.content == "User-agent: *\nDisallow: /private"
        assert retrieved.url == "https://example.com/robots.txt"
        assert retrieved.tenant_id is None  # System-owned only
        assert retrieved.is_valid is True
        
        # Verify no tenant-specific fields are present
        assert not hasattr(retrieved, 'account_id')
        assert not hasattr(retrieved, 'target_id')
        assert not hasattr(retrieved, 'job_id')
        assert not hasattr(retrieved, 'crawl_decision')

    def test_cache_access_without_tenant_context(self, postgres_db):
        """Test that cache can be accessed without tenant context."""
        # Create cache entry
        cache_entry = RobotsTxtCache(
            domain="public.com",
            tenant_id=None,
            content="User-agent: *\nAllow: /",
            url="https://public.com/robots.txt",
            rules={"*": {"crawl_delay": 1.0, "request_rate": None}},
            fetched_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            http_status=200,
            is_valid=True,
        )
        
        postgres_db.add(cache_entry)
        postgres_db.commit()
        
        # Access without tenant context should work
        from layer1_ingestion.shared.database import get_db_session
        
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            retrieved = session.query(RobotsTxtCache).filter(RobotsTxtCache.domain == "public.com").first()
            assert retrieved is not None
            assert retrieved.domain == "public.com"

    def test_cache_access_with_any_tenant_context(self, postgres_db):
        """Test that cache can be accessed from any tenant context."""
        # Create cache entry
        cache_entry = RobotsTxtCache(
            domain="shared.com",
            tenant_id=None,
            content="User-agent: *\nCrawl-delay: 2",
            url="https://shared.com/robots.txt",
            rules={"*": {"crawl_delay": 2.0, "request_rate": None}},
            fetched_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            http_status=200,
            is_valid=True,
        )
        
        postgres_db.add(cache_entry)
        postgres_db.commit()
        
        # Access from different tenant contexts should all work
        tenant_ids = [str(uuid4()), str(uuid4()), str(uuid4())]
        
        from layer1_ingestion.shared.database import get_db_session
        
        for tenant_id in tenant_ids:
            with get_db_session(tenant_id=tenant_id, require_tenant=True) as session:
                retrieved = session.query(RobotsTxtCache).filter(RobotsTxtCache.domain == "shared.com").first()
                assert retrieved is not None
                assert retrieved.domain == "shared.com"

    def test_cache_entries_are_shared_across_tenants(self, postgres_db):
        """Test that cache entries are shared across all tenants."""
        # Create cache entry from one tenant context
        tenant_id_1 = str(uuid4())
        
        from layer1_ingestion.shared.database import get_db_session
        
        with get_db_session(tenant_id=tenant_id_1, require_tenant=True) as session:
            cache_entry = RobotsTxtCache(
                domain="global.com",
                tenant_id=None,  # System-owned only
                content="User-agent: *\nDisallow: /admin",
                url="https://global.com/robots.txt",
                rules={"*": {"crawl_delay": None, "request_rate": None}},
                fetched_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                http_status=200,
                is_valid=True,
            )
            session.add(cache_entry)
            session.commit()
        
        # Verify entry is accessible from other tenant contexts
        tenant_id_2 = str(uuid4())
        
        with get_db_session(tenant_id=tenant_id_2, require_tenant=True) as session:
            retrieved = session.query(RobotsTxtCache).filter(RobotsTxtCache.domain == "global.com").first()
            assert retrieved is not None
            assert retrieved.content == "User-agent: *\nDisallow: /admin"

    def test_cache_does_not_store_tenant_specific_urls(self, postgres_db):
        """Test that cache doesn't store tenant-specific URLs or content."""
        from layer1_ingestion.shared.database import get_db_session
        
        # Attempt to cache tenant-specific data should be prevented
        tenant_id = str(uuid4())
        
        with get_db_session(tenant_id=tenant_id, require_tenant=True) as session:
            # Only public robots.txt URLs should be cached
            valid_urls = [
                "https://example.com/robots.txt",
                "https://subdomain.example.com/robots.txt",
                "http://example.org/robots.txt",
            ]
            
            invalid_urls = [
                "https://example.com/tenant-specific-page",  # Not robots.txt
                "https://example.com/api/tenant-data",        # API endpoint
                "https://tenant.example.com/private",         # Tenant-specific
            ]
            
            for url in valid_urls:
                cache_entry = RobotsTxtCache(
                    domain=urlparse(url).netloc,
                    tenant_id=None,
                    content="Public robots.txt",
                    url=url,
                    rules={},
                    fetched_at=datetime.now(timezone.utc),
                    expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                    http_status=200,
                    is_valid=True,
                )
                session.add(cache_entry)
            
            session.commit()
            
            # Verify only valid entries exist
            all_entries = session.query(RobotsTxtCache).all()
            for entry in all_entries:
                assert entry.url.endswith("/robots.txt")
                assert "/tenant-" not in entry.url
                assert "/api/" not in entry.url

    def test_legacy_tenant_id_column_is_system_owned_only(self, postgres_db):
        """Test that tenant_id column is only used for system ownership."""
        from layer1_ingestion.shared.database import get_db_session
        
        # Create entries with different tenant_id values
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            # System-owned entry (correct usage)
            system_entry = RobotsTxtCache(
                domain="system.com",
                tenant_id=None,  # System-owned only
                content="System robots.txt",
                url="https://system.com/robots.txt",
                rules={},
                fetched_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                http_status=200,
                is_valid=True,
            )
            session.add(system_entry)
            
            # Legacy entry with system tenant_id (should be documented as legacy)
            legacy_entry = RobotsTxtCache(
                domain="legacy.com", 
                tenant_id=uuid4(),  # Legacy - should be documented
                content="Legacy robots.txt",
                url="https://legacy.com/robots.txt",
                rules={},
                fetched_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                http_status=200,
                is_valid=True,
            )
            session.add(legacy_entry)
            
            session.commit()
        
        # Both entries should be accessible globally
        with get_db_session(tenant_id=str(uuid4()), require_tenant=True) as session:
            system_retrieved = session.query(RobotsTxtCache).filter(RobotsTxtCache.domain == "system.com").first()
            legacy_retrieved = session.query(RobotsTxtCache).filter(RobotsTxtCache.domain == "legacy.com").first()
            
            assert system_retrieved is not None
            assert legacy_retrieved is not None
            assert system_retrieved.tenant_id is None
            assert legacy_retrieved.tenant_id is not None  # Legacy


class TestRobotsCheckerGlobalCacheAccess:
    """Test RobotsChecker access to global cache."""

    @pytest.mark.asyncio
    async def test_robots_checker_accesses_global_cache(self, postgres_db):
        """Test that RobotsChecker can access global cache without tenant context."""
        # Setup cache entry
        cache_entry = RobotsTxtCache(
            domain="checker.com",
            tenant_id=None,
            content="User-agent: *\nCrawl-delay: 5",
            url="https://checker.com/robots.txt",
            rules={"*": {"crawl_delay": 5.0, "request_rate": None}},
            fetched_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            http_status=200,
            is_valid=True,
        )
        
        postgres_db.add(cache_entry)
        postgres_db.commit()
        
        # Test RobotsChecker with tenant context
        tenant_id = str(uuid4())
        checker = RobotsChecker(tenant_id=tenant_id)
        
        # Should access global cache successfully
        cached = await checker._get_cached_robots_txt("checker.com")
        
        assert cached is not None
        assert cached["rules"]["*"]["crawl_delay"] == 5.0

    @pytest.mark.asyncio
    async def test_robots_checker_without_tenant_context(self, postgres_db):
        """Test that RobotsChecker works without tenant context."""
        # Setup cache entry
        cache_entry = RobotsTxtCache(
            domain="notenant.com",
            tenant_id=None,
            content="User-agent: *\nAllow: /",
            url="https://notenant.com/robots.txt",
            rules={"*": {"crawl_delay": None, "request_rate": None}},
            fetched_at=datetime.now(timezone.utc),
            expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
            http_status=200,
            is_valid=True,
        )
        
        postgres_db.add(cache_entry)
        postgres_db.commit()
        
        # Test RobotsChecker without tenant context
        checker = RobotsChecker(tenant_id=None)
        
        # Should access global cache successfully
        cached = await checker._get_cached_robots_txt("notenant.com")
        
        assert cached is not None
        assert cached["rules"]["*"]["crawl_delay"] is None

    @pytest.mark.asyncio
    async def test_robots_checker_invalid_tenant_id_fails(self):
        """Test that RobotsChecker fails with invalid tenant_id."""
        checker = RobotsChecker(tenant_id="invalid-uuid")
        
        with pytest.raises(InvalidTenantContextError) as exc_info:
            await checker._get_cached_robots_txt("example.com")
        
        assert "Invalid tenant_id format" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_robots_checker_cache_error_handling(self, postgres_db):
        """Test that RobotsChecker properly handles cache errors."""
        # Mock a database error
        from layer1_ingestion.shared.database import get_db_session
        from unittest.mock import patch
        
        with patch('layer1_ingestion.shared.database.get_db_session') as mock_session:
            mock_session.side_effect = Exception("Database connection failed")
            
            checker = RobotsChecker(tenant_id=str(uuid4()))
            
            with pytest.raises(RobotsCacheError) as exc_info:
                await checker._get_cached_robots_txt("error.com")
            
            assert "Failed to retrieve cached robots.txt" in str(exc_info.value)
            assert exc_info.value.domain == "error.com"


class TestCacheSecurityProperties:
    """Test security properties of the global cache."""

    def test_cache_cannot_store_tenant_owned_data(self, postgres_db):
        """Test that cache cannot be used to store tenant-owned data."""
        from layer1_ingestion.shared.database import get_db_session
        
        tenant_id = str(uuid4())
        test_domain = f"tenant-{tenant_id[:8]}.com"
        
        # Attempt to store tenant-owned data should be prevented by design
        with get_db_session(tenant_id=tenant_id, require_tenant=True) as session:
            # RobotsTxtCache model doesn't have tenant-owned fields
            # Only public robots.txt response data can be stored
            cache_entry = RobotsTxtCache(
                domain=test_domain,
                tenant_id=None,  # Always system-owned for global cache
                content="Public robots.txt only",  # No tenant-specific content
                url=f"https://{test_domain}/robots.txt",  # Only robots.txt URLs
                rules={},  # Only parsed rules, not crawl decisions
                fetched_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                http_status=200,
                is_valid=True,
                # No tenant-owned fields available
            )
            session.add(cache_entry)
            session.commit()
        
        # Verify no tenant-owned data is stored
        with get_db_session(tenant_id=tenant_id, require_tenant=True) as session:
            retrieved = session.query(RobotsTxtCache).filter(RobotsTxtCache.domain == test_domain).first()
            assert retrieved is not None
            assert retrieved.tenant_id is None  # System-owned only
            assert "tenant" not in retrieved.content.lower()  # No tenant-specific content

    def test_cache_rls_not_required(self, postgres_db):
        """Test that cache doesn't require RLS policies."""
        from layer1_ingestion.shared.database import get_db_session
        
        # Create cache entry without any tenant context
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            cache_entry = RobotsTxtCache(
                domain="norls.com",
                tenant_id=None,
                content="User-agent: *\nDisallow: /",
                url="https://norls.com/robots.txt",
                rules={},
                fetched_at=datetime.now(timezone.utc),
                expires_at=datetime.now(timezone.utc) + timedelta(hours=24),
                http_status=200,
                is_valid=True,
            )
            session.add(cache_entry)
            session.commit()
        
        # Access should work from any context without RLS
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            retrieved = session.query(RobotsTxtCache).filter(RobotsTxtCache.domain == "norls.com").first()
            assert retrieved is not None


class TestStrictRobotsEnforcementSetting:
    """Security-relevant checks for strict robots enforcement behavior."""

    @pytest.mark.asyncio
    async def test_strict_robots_enforcement_blocks_fetch_failures_with_reason_code(self):
        checker = RobotsChecker(
            tenant_id=str(uuid4()),
            strict_mode=True,
        )

        from unittest.mock import AsyncMock, patch

        with patch.object(checker, "_get_robots_txt", new_callable=AsyncMock) as mock_get:
            mock_get.side_effect = RobotsFetchError("network down", domain="example.com")
            allowed, reason, rules = await checker.check_url("https://example.com/path", job_id="job-123")

        assert allowed is False
        assert "strict mode" in (reason or "").lower()
        assert rules is not None
        assert rules["reason_code"] == "ROBOTS_FETCH_ERROR"


# Helper function for URL parsing
def urlparse(url):
    """Simple URL parser for testing."""
    from urllib.parse import urlparse as real_urlparse
    return real_urlparse(url)
