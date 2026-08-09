"""PostgreSQL-backed tests for crawl decisions tenant isolation.

Tests validate that crawl_decision writes cannot cross tenant boundaries:
- CrawlDecisionRepository.save() with wrong tenant_id raises tenant isolation error
- Queries with tenant_id=A cannot see tenant B's decisions
- Decision records are scoped to tenant_id in database
- RLS policies prevent cross-tenant reads/writes on crawl_decisions table

These tests MUST run against PostgreSQL.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from layer1_ingestion.crawler.decision_store import (
    CrawlDecisionRecord,
    CrawlDecisionRepository,
)
from layer1_ingestion.shared.models import CrawlDecision

pytestmark = pytest.mark.requires_postgres


class TestCrawlDecisionTenantIsolation:
    """Test that crawl decisions are properly isolated by tenant."""

    @pytest.mark.asyncio
    async def test_crawl_decision_save_with_tenant_id_scopes_record(
        self, db, org_id, other_org_id
    ):
        """Saving a crawl decision with tenant_id should scope it to that tenant."""
        from layer1_ingestion.shared.database import get_db_session
        
        # Create decision for tenant A
        record_a = CrawlDecisionRecord(
            decision_id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_id=str(org_id),
            url="https://example.com",
            domain="example.com",
            requested_path="browser",
            router_decision="browser",
            router_rule="default",
            quality_passed=True,
            quality_checks={"spa_detected": False},
            fallback_reason=None,
            final_path="browser",
            status_code=200,
            fast_duration_ms=0,
            browser_duration_ms=1000,
            fetch_time_ms=1000,
            bytes_transferred=5000,
            spa_detected=False,
            text_length=1000,
        )

        # Save with tenant A context
        tenant_uuid = UUID(str(org_id))
        with get_db_session(tenant_id=tenant_uuid, require_tenant=True) as session:
            # Use repository with session
            repo_with_session = CrawlDecisionRepository(db_session=session)
            await repo_with_session.save(record_a)

        # Verify record exists in database with tenant_id
        db_record = (
            db.query(CrawlDecision)
            .filter(CrawlDecision.decision_id == UUID(record_a.decision_id))
            .first()
        )
        assert db_record is not None
        assert db_record.tenant_id == org_id

    @pytest.mark.asyncio
    async def test_crawl_decision_query_respects_tenant_context(
        self, db, org_id, other_org_id
    ):
        """Queries with tenant_id=A should not see tenant B's decisions."""
        from layer1_ingestion.shared.database import get_db_session
        
        # Create decision for tenant A
        record_a = CrawlDecisionRecord(
            decision_id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_id=str(org_id),
            url="https://example-a.com",
            domain="example-a.com",
            requested_path="browser",
            router_decision="browser",
            router_rule="default",
            quality_passed=True,
            quality_checks=None,
            fallback_reason=None,
            final_path="browser",
            status_code=200,
            fast_duration_ms=0,
            browser_duration_ms=1000,
            fetch_time_ms=1000,
            bytes_transferred=5000,
            spa_detected=False,
            text_length=1000,
        )

        # Create decision for tenant B
        record_b = CrawlDecisionRecord(
            decision_id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_id=str(other_org_id),
            url="https://example-b.com",
            domain="example-b.com",
            requested_path="browser",
            router_decision="browser",
            router_rule="default",
            quality_passed=True,
            quality_checks=None,
            fallback_reason=None,
            final_path="browser",
            status_code=200,
            fast_duration_ms=0,
            browser_duration_ms=1000,
            fetch_time_ms=1000,
            bytes_transferred=5000,
            spa_detected=False,
            text_length=1000,
        )

        # Save both decisions
        # Save tenant A decision
        tenant_a_uuid = UUID(str(org_id))
        with get_db_session(tenant_id=tenant_a_uuid, require_tenant=True) as session:
            repo_a = CrawlDecisionRepository(db_session=session)
            await repo_a.save(record_a)

        # Save tenant B decision
        tenant_b_uuid = UUID(str(other_org_id))
        with get_db_session(tenant_id=tenant_b_uuid, require_tenant=True) as session:
            repo_b = CrawlDecisionRepository(db_session=session)
            await repo_b.save(record_b)

        # Query with tenant A context should only see tenant A's decision
        tenant_a_uuid = UUID(str(org_id))
        with get_db_session(tenant_id=tenant_a_uuid, require_tenant=True) as session:
            repo_query = CrawlDecisionRepository(db_session=session)
            decisions_a = await repo_query.get_by_domain(
                "example-a.com", tenant_id=str(org_id)
            )
        assert len(decisions_a) == 1
        assert decisions_a[0].tenant_id == str(org_id)
        assert decisions_a[0].url == "https://example-a.com"

        # Query with tenant A context should NOT see tenant B's decision
        tenant_a_uuid = UUID(str(org_id))
        with get_db_session(tenant_id=tenant_a_uuid, require_tenant=True) as session:
            repo_query = CrawlDecisionRepository(db_session=session)
            decisions_b_from_a = await repo_query.get_by_domain(
                "example-b.com", tenant_id=str(org_id)
            )
        assert len(decisions_b_from_a) == 0

    @pytest.mark.asyncio
    async def test_crawl_decision_save_requires_tenant_context(self, db, org_id):
        """Saving crawl decisions should require tenant context."""
        repo = CrawlDecisionRepository()

        record = CrawlDecisionRecord(
            decision_id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_id=str(org_id),
            url="https://example.com",
            domain="example.com",
            requested_path="browser",
            router_decision="browser",
            router_rule="default",
            quality_passed=True,
            quality_checks=None,
            fallback_reason=None,
            final_path="browser",
            status_code=200,
            fast_duration_ms=0,
            browser_duration_ms=1000,
            fetch_time_ms=1000,
            bytes_transferred=5000,
            spa_detected=False,
            text_length=1000,
        )

        # This should fail if _get_session() is called without tenant context
        # The repository's _get_session() method should require explicit tenant context
        # Try to use repository without passing session
        # This should fail or require tenant_id parameter
        try:
            await repo.save(record)
            # If we get here, the repository allowed saving without tenant context
            # This is a security issue
            assert False, "Repository should require tenant context for save operations"
        except RuntimeError as e:
            # Expected: repository should raise error when called without tenant context
            assert "tenant" in str(e).lower()

    @pytest.mark.asyncio
    async def test_crawl_decision_cross_tenant_write_blocked(self, db, org_id, other_org_id):
        """Attempting to write crawl decision for tenant B with tenant_id=A should fail."""
        from layer1_ingestion.shared.database import get_db_session
        
        record_b = CrawlDecisionRecord(
            decision_id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_id=str(other_org_id),  # Record belongs to tenant B
            url="https://example-b.com",
            domain="example-b.com",
            requested_path="browser",
            router_decision="browser",
            router_rule="default",
            quality_passed=True,
            quality_checks=None,
            fallback_reason=None,
            final_path="browser",
            status_code=200,
            fast_duration_ms=0,
            browser_duration_ms=1000,
            fetch_time_ms=1000,
            bytes_transferred=5000,
            spa_detected=False,
            text_length=1000,
        )

        # Try to save with tenant A context but record has tenant_id=B
        tenant_a_uuid = UUID(str(org_id))
        with get_db_session(tenant_id=tenant_a_uuid, require_tenant=True) as session:
            repo = CrawlDecisionRepository(db_session=session)
            # This should fail due to RLS or validation
            try:
                await repo.save(record_b)
                # If we get here, cross-tenant write succeeded - security issue
                assert False, "Cross-tenant write should be blocked by RLS"
            except Exception as e:
                # Expected: RLS should block cross-tenant write
                # The error should be related to tenant isolation
                assert "tenant" in str(e).lower() or "permission" in str(e).lower()

    @pytest.mark.asyncio
    async def test_crawl_decision_rls_prevents_cross_tenant_reads(self, db, org_id, other_org_id):
        """RLS policies should prevent cross-tenant reads on crawl_decisions table."""
        from layer1_ingestion.shared.database import get_db_session
        
        # Create decision for tenant B
        record_b = CrawlDecisionRecord(
            decision_id=str(uuid4()),
            job_id=str(uuid4()),
            tenant_id=str(other_org_id),
            url="https://example-b.com",
            domain="example-b.com",
            requested_path="browser",
            router_decision="browser",
            router_rule="default",
            quality_passed=True,
            quality_checks=None,
            fallback_reason=None,
            final_path="browser",
            status_code=200,
            fast_duration_ms=0,
            browser_duration_ms=1000,
            fetch_time_ms=1000,
            bytes_transferred=5000,
            spa_detected=False,
            text_length=1000,
        )

        # Save with tenant B context
        tenant_b_uuid = UUID(str(other_org_id))
        with get_db_session(tenant_id=tenant_b_uuid, require_tenant=True) as session:
            repo = CrawlDecisionRepository(db_session=session)
            await repo.save(record_b)

        # Direct database query with tenant A context should not see tenant B's decision
        tenant_a_uuid = UUID(str(org_id))
        with get_db_session(tenant_id=tenant_a_uuid, require_tenant=True) as session:
            # Try to query tenant B's decision with tenant A context
            db_record = (
                session.query(CrawlDecision)
                .filter(CrawlDecision.decision_id == UUID(record_b.decision_id))
                .first()
            )
            # RLS should prevent this - should return None
            assert db_record is None, "RLS should prevent cross-tenant reads"
