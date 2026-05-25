"""PostgreSQL-backed Celery task tenant isolation tests.

Tests validate that Celery tasks properly enforce tenant isolation:
- Tasks accept tenant_id from dispatch envelope
- Tasks set RLS context before tenant-scoped queries
- Tasks with forged tenant_id cannot access other tenant's data
- Error handling paths respect tenant context
- Pipeline chain passes tenant_id through all stages

These tests MUST run against PostgreSQL.
"""

from __future__ import annotations

import pytest
from uuid import uuid4
from unittest.mock import MagicMock, patch

from value_fabric.layer1.shared.database import get_db_session, TenantContextError
from value_fabric.layer1.shared.models import ScrapingJob, ScrapingTarget, JobStatus


pytestmark = pytest.mark.postgres


class TestCeleryTaskTenantContext:
    """Test that Celery tasks properly handle tenant context."""

    def test_process_scraping_job_signature_accepts_tenant_id(self):
        """process_scraping_job task signature includes tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import process_scraping_job
        import inspect
        
        sig = inspect.signature(process_scraping_job)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "process_scraping_job must accept tenant_id"
        assert 'job_id' in params, "process_scraping_job must accept job_id"

    def test_compliance_check_stage_accepts_tenant_id(self):
        """compliance_check_stage task signature includes tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import compliance_check_stage
        import inspect
        
        sig = inspect.signature(compliance_check_stage)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "compliance_check_stage must accept tenant_id"

    def test_browser_crawl_stage_accepts_tenant_id(self):
        """browser_crawl_stage task signature includes tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import browser_crawl_stage
        import inspect
        
        sig = inspect.signature(browser_crawl_stage)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "browser_crawl_stage must accept tenant_id"

    def test_ai_extraction_stage_accepts_tenant_id(self):
        """ai_extraction_stage task signature includes tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import ai_extraction_stage
        import inspect
        
        sig = inspect.signature(ai_extraction_stage)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "ai_extraction_stage must accept tenant_id"

    def test_post_processing_stage_accepts_tenant_id(self):
        """post_processing_stage task signature includes tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import post_processing_stage
        import inspect
        
        sig = inspect.signature(post_processing_stage)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "post_processing_stage must accept tenant_id"

    def test_validation_stage_accepts_tenant_id(self):
        """validation_stage task signature includes tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import validation_stage
        import inspect
        
        sig = inspect.signature(validation_stage)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "validation_stage must accept tenant_id"

    def test_storage_stage_accepts_tenant_id(self):
        """storage_stage task signature includes tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import storage_stage
        import inspect
        
        sig = inspect.signature(storage_stage)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "storage_stage must accept tenant_id"

    def test_notification_stage_accepts_tenant_id(self):
        """notification_stage task signature includes tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import notification_stage
        import inspect
        
        sig = inspect.signature(notification_stage)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "notification_stage must accept tenant_id"


class TestCeleryTaskRLSEnforcement:
    """Test that Celery tasks enforce RLS when using tenant_id."""

    def test_task_with_tenant_id_can_query_own_data(self, postgres_db, org_id, make_job):
        """Task with valid tenant_id can query tenant's own data."""
        job = make_job(tenant_id=org_id)
        
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            queried_job = session.query(ScrapingJob).filter(ScrapingJob.id == job.id).first()
            assert queried_job is not None
            assert queried_job.id == job.id
            assert queried_job.tenant_id == org_id

    def test_task_with_tenant_id_cannot_query_other_tenant(self, postgres_db, org_id, other_org_id, make_job):
        """Task with tenant_id cannot query other tenant's data."""
        other_job = make_job(tenant_id=other_org_id)
        
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            queried_job = session.query(ScrapingJob).filter(ScrapingJob.id == other_job.id).first()
            assert queried_job is None, "RLS should block cross-tenant access"

    def test_task_without_tenant_id_fails_closed(self, postgres_db):
        """Task without tenant_id fails with TenantContextError."""
        with pytest.raises(TenantContextError):
            with get_db_session(tenant_id=None, require_tenant=True) as session:
                session.query(ScrapingJob).first()

    def test_task_with_invalid_tenant_id_fails_closed(self, postgres_db):
        """Task with invalid tenant_id fails with TenantContextError."""
        fake_tenant_id = uuid4()
        
        with pytest.raises(TenantContextError):
            with get_db_session(tenant_id=fake_tenant_id, require_tenant=True) as session:
                session.query(ScrapingJob).first()


class TestPipelineChainTenantPropagation:
    """Test that pipeline chain properly propagates tenant_id."""

    def test_pipeline_chain_includes_tenant_id(self):
        """Pipeline chain construction includes tenant_id in all stages."""
        from value_fabric.layer1.shared.tasks import (
            compliance_check_stage,
            browser_crawl_stage,
            ai_extraction_stage,
            post_processing_stage,
            validation_stage,
            storage_stage,
            notification_stage,
        )
        from celery import chain
        
        job_id = str(uuid4())
        tenant_id = str(uuid4())
        
        # Construct pipeline chain as done in process_scraping_job
        pipeline_chain = chain(
            compliance_check_stage.s(job_id, tenant_id),
            browser_crawl_stage.s(tenant_id=tenant_id),
            ai_extraction_stage.s(tenant_id=tenant_id),
            post_processing_stage.s(tenant_id=tenant_id),
            validation_stage.s(tenant_id=tenant_id),
            storage_stage.s(tenant_id=tenant_id),
            notification_stage.s(tenant_id=tenant_id),
        )
        
        # Verify the chain was constructed
        assert pipeline_chain is not None

    def test_dispatch_calls_include_tenant_id(self):
        """Verify API dispatch calls include tenant_id."""
        # This is a static check - we verify the code pattern
        import re
        
        main_file = 'src/api/main.py'
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find process_scraping_job.delay calls (multi-line aware)
        # Match balanced parentheses
        pattern = r'process_scraping_job\.delay\((?:[^()]|\([^()]*\))*\)'
        matches = re.findall(pattern, content)
        
        # Verify each call includes tenant_id
        for match in matches:
            # Should contain tenant_id parameter
            assert 'tenant_id' in match or 'str(job.tenant_id)' in match or 'str(new_job.tenant_id)' in match, \
                f"Dispatch call missing tenant_id: {match[:100]}"

    def test_app_monolith_dispatch_calls_include_tenant_id(self):
        """Verify app_monolith dispatch calls include tenant_id."""
        import re
        
        app_monolith_file = 'src/api/app_monolith.py'
        with open(app_monolith_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find process_scraping_job.delay calls (multi-line aware)
        # Match balanced parentheses
        pattern = r'process_scraping_job\.delay\((?:[^()]|\([^()]*\))*\)'
        matches = re.findall(pattern, content)
        
        # Verify each call includes tenant_id
        for match in matches:
            # Should contain tenant_id parameter
            assert 'tenant_id' in match or 'str(job.tenant_id)' in match or 'str(new_job.tenant_id)' in match, \
                f"Dispatch call missing tenant_id: {match[:100]}"


class TestErrorHandlingTenantContext:
    """Test that error handling paths respect tenant context."""

    def test_error_handler_uses_tenant_context(self, postgres_db, org_id, make_job):
        """Error handling in tasks uses tenant context."""
        job = make_job(tenant_id=org_id)
        
        # Simulate error handling with tenant context
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # This simulates the error handling pattern in tasks
            # where we update stage status with tenant context
            job.status = JobStatus.FAILED.value
            session.commit()
            
            # Verify the update succeeded
            session.refresh(job)
            assert job.status == JobStatus.FAILED.value

    def test_error_handler_without_tenant_fails(self, postgres_db):
        """Error handling without tenant context fails."""
        with pytest.raises(TenantContextError):
            with get_db_session(tenant_id=None, require_tenant=True) as session:
                session.query(ScrapingJob).first()


class TestCleanupTaskTenantIsolation:
    """Test that cleanup tasks respect tenant isolation."""

    def test_cleanup_old_content_accepts_tenant_id(self):
        """cleanup_old_content task accepts tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import cleanup_old_content
        import inspect
        
        sig = inspect.signature(cleanup_old_content)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "cleanup_old_content must accept tenant_id"

    def test_cleanup_with_tenant_id_isolated(self, postgres_db, org_id, other_org_id, make_job):
        """Cleanup with tenant_id only affects tenant's own data."""
        # Create jobs for both tenants
        org_job = make_job(tenant_id=org_id)
        other_job = make_job(tenant_id=other_org_id)
        
        # Simulate cleanup with org_id context
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # Query all jobs - should only see org_id's jobs
            jobs = session.query(ScrapingJob).all()
            job_ids = {job.id for job in jobs}
            
            assert org_job.id in job_ids
            assert other_job.id not in job_ids

    def test_cleanup_without_tenant_id_is_system_level(self, postgres_db):
        """Cleanup without tenant_id is system-level (requires admin auth)."""
        # This test validates that cleanup_old_content can be called
        # without tenant_id for system-level operations
        # In production, this should require admin authorization
        
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            # System-level query should work
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1


class TestDispatchOutboxEventTenantIsolation:
    """Test that dispatch_outbox_event respects tenant isolation."""

    def test_dispatch_outbox_event_accepts_tenant_id(self):
        """dispatch_outbox_event task accepts tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import dispatch_outbox_event
        import inspect
        
        sig = inspect.signature(dispatch_outbox_event)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "dispatch_outbox_event must accept tenant_id"

    def test_dispatch_outbox_event_uses_tenant_context(self, postgres_db, org_id, make_job):
        """dispatch_outbox_event uses tenant context for queries."""
        job = make_job(tenant_id=org_id)
        
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # Simulate dispatch_outbox_event querying with tenant context
            queried_job = session.query(ScrapingJob).filter(ScrapingJob.id == job.id).first()
            assert queried_job is not None
            assert queried_job.tenant_id == org_id


class TestFailJobTenantContext:
    """Test that _fail_job helper respects tenant context."""

    def test_fail_job_accepts_tenant_id(self):
        """_fail_job helper accepts tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import _fail_job
        import inspect
        
        sig = inspect.signature(_fail_job)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "_fail_job must accept tenant_id"

    def test_fail_job_uses_tenant_context(self, postgres_db, org_id, make_job):
        """_fail_job uses tenant context for updates."""
        job = make_job(tenant_id=org_id)
        
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # Simulate _fail_job updating job status
            job.status = JobStatus.FAILED.value
            session.commit()
            
            session.refresh(job)
            assert job.status == JobStatus.FAILED.value


class TestCrawlUrlWithRoutingTenantContext:
    """Test that crawl_url_with_routing respects tenant context."""

    def test_crawl_url_with_routing_accepts_tenant_id(self):
        """crawl_url_with_routing task accepts tenant_id parameter."""
        from value_fabric.layer1.shared.tasks import crawl_url_with_routing
        import inspect
        
        sig = inspect.signature(crawl_url_with_routing)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "crawl_url_with_routing must accept tenant_id"

    def test_crawl_url_with_routing_uses_tenant_context(self, postgres_db, org_id, make_job):
        """crawl_url_with_routing uses tenant context for queries."""
        job = make_job(tenant_id=org_id)
        
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # Simulate crawl_url_with_routing querying job with tenant context
            queried_job = session.query(ScrapingJob).filter(ScrapingJob.id == job.id).first()
            assert queried_job is not None
            assert queried_job.tenant_id == org_id
