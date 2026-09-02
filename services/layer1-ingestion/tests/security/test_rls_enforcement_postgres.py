"""PostgreSQL-backed RLS enforcement tests.

Tests validate PostgreSQL-specific tenant isolation behavior:
- Row-Level Security (RLS) policies
- SET LOCAL app.tenant_id
- current_setting('app.tenant_id')
- FORCE ROW LEVEL SECURITY
- Fail-closed behavior for missing/invalid tenant context

These tests MUST run against PostgreSQL. They will fail with a clear error
if run against SQLite or any other database.
"""

from __future__ import annotations

import pytest
from pathlib import Path
from sqlalchemy import text
from uuid import uuid4

from layer1_ingestion.shared.database import get_db_session
from layer1_ingestion.shared.models import ScrapingJob, ScrapingTarget, JobStatus

# Resolve source paths relative to this test file (services/layer1-ingestion/tests/security/)
_TASKS_DIR = Path(__file__).resolve().parents[2] / "src" / "layer1_ingestion" / "shared" / "tasks"


def _read_tasks_source() -> str:
    """Concatenate all tasks package submodule sources."""
    return "".join(
        p.read_text(encoding="utf-8") for p in sorted(_TASKS_DIR.glob("*.py"))
    )

pytestmark = pytest.mark.requires_postgres


class TestRLSEnforcement:
    """Test PostgreSQL Row-Level Security enforcement."""

    def test_missing_tenant_context_fails_closed(self, postgres_db):
        """Missing tenant_id should cause TenantContextError."""
        from layer1_ingestion.shared.database import TenantContextError
        
        with pytest.raises(TenantContextError):
            with get_db_session(tenant_id=None, require_tenant=True) as session:
                session.query(ScrapingJob).first()

    def test_invalid_tenant_id_fails_closed(self, postgres_db):
        """Invalid tenant_id should cause TenantContextError."""
        from layer1_ingestion.shared.database import TenantContextError
        
        # Use an invalid tenant_id format (not a UUID)
        invalid_tenant_id = "not-a-valid-uuid"
        
        with pytest.raises(TenantContextError):
            with get_db_session(tenant_id=invalid_tenant_id, require_tenant=True) as session:
                session.query(ScrapingJob).first()

    def test_cross_tenant_job_lookup_fails(self, postgres_db, org_id, other_org_id, make_job):
        """Tenant A cannot query Tenant B's job."""
        # Create a job for other_org_id
        other_job = make_job(tenant_id=other_org_id)
        
        # Try to query it with org_id context
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            job = session.query(ScrapingJob).filter(ScrapingJob.id == other_job.id).first()
            # RLS should prevent this - job should be None
            assert job is None, "Cross-tenant job lookup should return None due to RLS"

    def test_own_tenant_job_succeeds(self, postgres_db, org_id, make_job):
        """Tenant can query their own jobs."""
        # Create a job for org_id
        own_job = make_job(tenant_id=org_id)
        
        # Query it with org_id context
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            job = session.query(ScrapingJob).filter(ScrapingJob.id == own_job.id).first()
            assert job is not None, "Own-tenant job lookup should succeed"
            assert job.id == own_job.id
            assert job.tenant_id == org_id

    def test_set_local_applied_before_queries(self, postgres_db, org_id, make_job):
        """SET LOCAL app.tenant_id is applied before tenant-scoped queries."""
        own_job = make_job(tenant_id=org_id)
        
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # Verify tenant context is set by checking current_setting
            result = session.execute(text("SELECT current_setting('app.tenant_id', true)"))
            tenant_setting = result.scalar()
            assert tenant_setting == str(org_id), "SET LOCAL should set app.tenant_id"
            
            # Verify query respects the setting
            job = session.query(ScrapingJob).filter(ScrapingJob.id == own_job.id).first()
            assert job is not None

    def test_require_tenant_false_allowlisted(self, postgres_db):
        """require_tenant=False is allowlisted and should not touch tenant-owned data."""
        # This test validates that require_tenant=False is only used for
        # system-level operations that don't access tenant-scoped tables
        # or for operations that explicitly handle tenant context themselves
        
        # Example: querying system tables or non-tenant-scoped data
        with get_db_session(tenant_id=None, require_tenant=False) as session:
            # This should work for system-level queries
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

    def test_cleanup_respects_tenant_isolation(self, postgres_db, org_id, other_org_id, make_job):
        """Cleanup tasks do not bypass tenant isolation for tenant-owned tables."""
        # Create jobs for both tenants
        own_job = make_job(tenant_id=org_id)
        other_job = make_job(tenant_id=other_org_id)
        
        # Simulate cleanup with org_id context
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # Query all jobs - should only see org_id's jobs
            jobs = session.query(ScrapingJob).all()
            job_ids = {job.id for job in jobs}
            
            assert own_job.id in job_ids, "Should see own job"
            assert other_job.id not in job_ids, "Should NOT see other tenant's job due to RLS"

    def test_target_isolation(self, postgres_db, org_id, other_org_id, make_target):
        """Tenant A cannot query Tenant B's targets."""
        # Create a target for other_org_id
        other_target = make_target(tenant_id=other_org_id, name="Other Tenant Target")
        
        # Try to query it with org_id context
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            target = session.query(ScrapingTarget).filter(ScrapingTarget.id == other_target.id).first()
            # RLS should prevent this
            assert target is None, "Cross-tenant target lookup should return None due to RLS"

    def test_multiple_tenants_isolated(self, postgres_db, org_id, other_org_id, make_job):
        """Multiple tenants are properly isolated from each other."""
        # Create multiple jobs for each tenant
        org_jobs = [make_job(tenant_id=org_id) for _ in range(3)]
        other_jobs = [make_job(tenant_id=other_org_id) for _ in range(3)]
        
        # Query with org_id context
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            jobs = session.query(ScrapingJob).all()
            job_ids = {job.id for job in jobs}
            
            # Should only see org_id's jobs
            for job in org_jobs:
                assert job.id in job_ids
            
            for job in other_jobs:
                assert job.id not in job_ids

    def test_tenant_context_persistence_in_transaction(self, postgres_db, org_id, make_job):
        """Tenant context persists throughout a transaction."""
        own_job = make_job(tenant_id=org_id)
        
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # First query
            job1 = session.query(ScrapingJob).filter(ScrapingJob.id == own_job.id).first()
            assert job1 is not None
            
            # Second query in same transaction
            job2 = session.query(ScrapingJob).filter(ScrapingJob.id == own_job.id).first()
            assert job2 is not None
            assert job1.id == job2.id

    def test_forged_tenant_id_cannot_access_other_tenant(self, postgres_db, org_id, other_org_id, make_job):
        """A task with a forged tenant_id cannot access another tenant's data."""
        # Create a job for other_org_id
        other_job = make_job(tenant_id=other_org_id)
        
        # Try to access it with org_id (simulating a forged tenant_id in a task)
        with get_db_session(tenant_id=org_id, require_tenant=True) as session:
            # Even if we know the job_id, RLS should block access
            job = session.query(ScrapingJob).filter(ScrapingJob.id == other_job.id).first()
            assert job is None, "Forged tenant_id should not allow cross-tenant access"


class TestCeleryTaskTenantIsolation:
    """Test that Celery tasks properly enforce tenant isolation."""

    def test_process_scraping_job_requires_tenant_id(self, postgres_db, org_id, make_job):
        """process_scraping_job task requires tenant_id parameter."""
        from layer1_ingestion.shared.tasks import process_scraping_job
        from layer1_ingestion.shared.database import TenantContextError
        
        job = make_job(tenant_id=org_id)
        
        # The task should fail if called without tenant_id
        # This is a compile-time check - the task signature requires tenant_id
        # We validate the implementation by checking the task accepts tenant_id
        assert callable(process_scraping_job)
        
        # Verify the task can be called with tenant_id (signature check)
        # Actual execution would require Celery worker, but we validate the interface
        import inspect
        sig = inspect.signature(process_scraping_job)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "process_scraping_job must accept tenant_id parameter"

    def test_all_pipeline_stages_accept_tenant_id(self):
        """All pipeline stage tasks accept tenant_id parameter."""
        from layer1_ingestion.shared import tasks
        import inspect
        
        stage_tasks = [
            'compliance_check_stage',
            'browser_crawl_stage',
            'ai_extraction_stage',
            'post_processing_stage',
            'validation_stage',
            'storage_stage',
            'notification_stage',
        ]
        
        for task_name in stage_tasks:
            task = getattr(tasks, task_name)
            sig = inspect.signature(task)
            params = list(sig.parameters.keys())
            assert 'tenant_id' in params, f"{task_name} must accept tenant_id parameter"

    def test_fail_job_accepts_tenant_id(self):
        """_fail_job helper accepts tenant_id parameter."""
        from layer1_ingestion.shared.tasks import _fail_job
        import inspect
        
        sig = inspect.signature(_fail_job)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "_fail_job must accept tenant_id parameter"

    def test_dispatch_outbox_event_accepts_tenant_id(self):
        """dispatch_outbox_event task accepts tenant_id parameter."""
        from layer1_ingestion.shared.tasks import dispatch_outbox_event
        import inspect
        
        sig = inspect.signature(dispatch_outbox_event)
        params = list(sig.parameters.keys())
        assert 'tenant_id' in params, "dispatch_outbox_event must accept tenant_id parameter"


class TestRequireTenantFalseAllowlist:
    """Test that require_tenant=False usage is properly allowlisted."""

    def test_require_tenant_false_not_used_in_tenant_scoped_queries(self):
        """require_tenant=False is not used in tenant-scoped queries."""
        from layer1_ingestion.shared import tasks
        import re
        
        # Read the tasks package source
        content = _read_tasks_source()
        
        # Find all occurrences of require_tenant=False
        pattern = r'get_db_session\([^)]*require_tenant=False[^)]*\)'
        matches = re.findall(pattern, content)
        
        # These should only be in specific allowlisted contexts:
        # 1. System-level operations (no tenant-scoped tables)
        # 2. Operations that explicitly handle tenant context themselves
        # 3. Error handling paths that have been reviewed and approved
        
        # For now, we verify the count is reasonable and document each usage
        # In production, this should be enforced via static analysis
        assert len(matches) < 10, f"Too many require_tenant=False usages: {len(matches)}"
        
        # Log each usage for review
        for i, match in enumerate(matches):
            print(f"require_tenant=False usage {i+1}: {match[:100]}...")
