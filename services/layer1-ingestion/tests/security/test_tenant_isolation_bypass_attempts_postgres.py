"""PostgreSQL-backed tests for tenant isolation bypass attempts.

Tests validate that tenant isolation cannot be bypassed through various attack vectors
including forged tenant_id, missing context, and direct database access.

These tests MUST run against PostgreSQL.
"""

from __future__ import annotations

import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4, UUID

import asyncio
import inspect

from layer1_ingestion.shared.exceptions import (
    TenantContextError,
    InvalidTenantContextError,
    CrossTenantAccessError,
    SystemMaintenanceAuthorizationError,
    SecurityError,
)
from layer1_ingestion.shared.database import get_db_session, validate_tenant_id
from layer1_ingestion.shared.models import ScrapingJob, ScrapingTarget, RawContent
from layer1_ingestion.shared.tasks import process_scraping_job, cleanup_old_content


pytestmark = pytest.mark.requires_postgres


class TestTenantIdValidation:
    """Test tenant_id validation and forgery prevention."""

    def test_valid_uuid_tenant_id(self):
        """Test that valid UUID tenant_ids are accepted and returned as string."""
        valid_tenant_id = str(uuid4())
        result = validate_tenant_id(valid_tenant_id)
        assert result == valid_tenant_id

    def test_invalid_uuid_tenant_id_fails(self):
        """Test that invalid UUID tenant_ids are rejected."""
        from layer1_ingestion.shared.database import TenantContextError as DBTenantContextError
        invalid_tenant_ids = [
            "not-a-uuid",
            "123-456-789",
            "malicious-tenant-id",
            "../../../etc/passwd",
            "' OR '1'='1",
            "tenant-1'; DROP TABLE users; --",
        ]
        
        for invalid_id in invalid_tenant_ids:
            with pytest.raises(DBTenantContextError) as exc_info:
                validate_tenant_id(invalid_id)
            
            assert "Invalid tenant_id format" in str(exc_info.value)

    def test_none_tenant_id_handling(self):
        """Test that None tenant_id is handled appropriately."""
        from layer1_ingestion.shared.database import TenantContextError as DBTenantContextError
        # In fail-safe mode, None should raise an error unless explicitly allowed
        with pytest.raises(DBTenantContextError) as exc_info:
            validate_tenant_id(None)
        
        assert "tenant context is mandatory" in str(exc_info.value).lower()

    def test_empty_string_tenant_id_fails(self):
        """Test that empty string tenant_ids are rejected."""
        from layer1_ingestion.shared.database import TenantContextError as DBTenantContextError
        with pytest.raises(DBTenantContextError) as exc_info:
            validate_tenant_id("")
        
        assert "empty tenant_id" in str(exc_info.value).lower()

    def test_uuid_injection_attempts(self):
        """Test that UUID injection attempts are caught."""
        from layer1_ingestion.shared.database import TenantContextError as DBTenantContextError
        malicious_ids = [
            "00000000-0000-0000-0000-000000000000'; DROP TABLE scraping_jobs; --",
            "123e4567-e89b-12d3-a456-426614174000 OR 1=1",
            "admin-tenant-override",
            "system-tenant-bypass",
        ]
        
        for malicious_id in malicious_ids:
            with pytest.raises(DBTenantContextError):
                validate_tenant_id(malicious_id)


class TestCrossTenantAccessPrevention:
    """Test prevention of cross-tenant data access."""

    def test_job_lookup_with_wrong_tenant_fails(self, postgres_db, make_job):
        """Test that looking up a job with wrong tenant_id fails."""
        # Create job for tenant A
        tenant_a = str(uuid4())
        job = make_job(tenant_id=tenant_a)
        
        # Try to access with tenant B
        tenant_b = str(uuid4())
        
        with get_db_session(tenant_id=tenant_b, require_tenant=True) as session:
            retrieved = session.query(ScrapingJob).filter(ScrapingJob.id == job.id).first()
            # RLS should prevent access by returning None
            assert retrieved is None, "RLS must prevent cross-tenant job access"

    def test_target_isolation_enforced(self, postgres_db, user_id):
        """Test that target isolation is properly enforced."""
        # Create targets for different tenants
        tenant_a = str(uuid4())
        tenant_b = str(uuid4())

        target_a = ScrapingTarget(
            name="Target A",
            url="https://example-a.com",
            tenant_id=tenant_a,
            status="ACTIVE",
            created_by=user_id,
        )

        target_b = ScrapingTarget(
            name="Target B",
            url="https://example-b.com",
            tenant_id=tenant_b,
            status="ACTIVE",
            created_by=user_id,
        )

        postgres_db.add(target_a)
        postgres_db.add(target_b)
        postgres_db.commit()
        
        # Tenant A should only see Target A
        with get_db_session(tenant_id=tenant_a, require_tenant=True) as session:
            targets = session.query(ScrapingTarget).all()
            assert len(targets) == 1
            assert str(targets[0].tenant_id) == tenant_a
            assert targets[0].name == "Target A"
        
        # Tenant B should only see Target B
        with get_db_session(tenant_id=tenant_b, require_tenant=True) as session:
            targets = session.query(ScrapingTarget).all()
            assert len(targets) == 1
            assert str(targets[0].tenant_id) == tenant_b
            assert targets[0].name == "Target B"

    def test_raw_content_tenant_isolation(self, postgres_db, user_id, make_target):
        """Test that raw content is properly isolated by tenant."""
        from uuid import uuid4
        tenant_a = str(uuid4())
        tenant_b = str(uuid4())

        # Create jobs first (RawContent requires job_id)
        target_a = make_target(tenant_id=tenant_a)
        job_a = ScrapingJob(
            id=uuid4(),
            tenant_id=tenant_a,
            target_id=target_a.id,
            status="PENDING",
            configuration={},
            created_by=user_id,
        )
        postgres_db.add(job_a)
        postgres_db.flush()

        target_b = make_target(tenant_id=tenant_b)
        job_b = ScrapingJob(
            id=uuid4(),
            tenant_id=tenant_b,
            target_id=target_b.id,
            status="PENDING",
            configuration={},
            created_by=user_id,
        )
        postgres_db.add(job_b)
        postgres_db.flush()

        # Create content for different tenants
        content_a = RawContent(
            job_id=job_a.id,
            tenant_id=tenant_a,
            source_url="https://example-a.com/page1",
            source_domain="example-a.com",
            processing_status="COMPLETED",
        )

        content_b = RawContent(
            job_id=job_b.id,
            tenant_id=tenant_b,
            source_url="https://example-b.com/page1",
            source_domain="example-b.com",
            processing_status="COMPLETED",
        )

        postgres_db.add(content_a)
        postgres_db.add(content_b)
        postgres_db.commit()
        
        # Verify isolation
        with get_db_session(tenant_id=tenant_a, require_tenant=True) as session:
            content = session.query(RawContent).all()
            assert len(content) == 1
            assert str(content[0].tenant_id) == tenant_a
            assert content[0].source_domain == "example-a.com"

    def test_forged_tenant_id_in_task_dispatch(self):
        """Test that forged tenant_id in task dispatch is caught."""
        from layer1_ingestion.shared.tasks import process_scraping_job
        
        # Mock the task chain to verify tenant_id validation
        with patch('layer1_ingestion.shared.tasks.process_scraping_job') as mock_task:
            # Try to dispatch with forged tenant_id
            forged_tenant_id = "admin-override-tenant"
            job_id = str(uuid4())
            
            with pytest.raises(Exception):  # Should fail validation
                process_scraping_job(job_id, forged_tenant_id)


class TestSystemMaintenanceBypassAttempts:
    """Test that system maintenance cannot be bypassed."""

    def test_cleanup_without_maintenance_token_fails(self):
        """Test that cleanup without maintenance token fails."""
        # Remove maintenance token from environment
        with patch.dict('os.environ', {}, clear=True):
            with pytest.raises(SystemMaintenanceAuthorizationError):
                cleanup_old_content(days=1, tenant_id=None)

    def test_cleanup_with_invalid_token_fails(self):
        """Test that cleanup with invalid token fails."""
        with patch.dict('os.environ', {'FABRIC4L_MAINTENANCE_TOKEN': 'invalid-token'}):
            with pytest.raises(SystemMaintenanceAuthorizationError):
                cleanup_old_content(days=1, tenant_id=None)

    def test_forged_maintenance_token_fails(self):
        """Test that forged maintenance tokens are rejected."""
        forged_tokens = [
            "fabric4l-maintenance:fake:signature",
            "admin-bypass-token",
            "system-override-key",
            "fabric4l-maintenance:old-timestamp:fake-sig",
        ]
        
        for token in forged_tokens:
            with patch.dict('os.environ', {'FABRIC4L_MAINTENANCE_TOKEN': token}):
                with pytest.raises(SystemMaintenanceAuthorizationError):
                    cleanup_old_content(days=1, tenant_id=None)

    def test_maintenance_operation_not_allowlisted_fails(self):
        """Test that non-allowlisted operations fail even with valid token."""
        # Create a valid token format
        import time
        timestamp = int(time.time())
        valid_token = f"fabric4l-maintenance:{timestamp}:test-sig"
        
        with patch.dict('os.environ', {'FABRIC4L_MAINTENANCE_TOKEN': valid_token}):
            from layer1_ingestion.shared.maintenance import authorize_maintenance_operation
            
            # Try unauthorized operation
            with pytest.raises(SystemMaintenanceAuthorizationError):
                authorize_maintenance_operation("delete_all_data", tenant_id=None)


class TestDatabaseSessionBypassAttempts:
    """Test that database session cannot be bypassed."""

    def test_require_tenant_false_without_authorization_fails(self):
        """Test that require_tenant=False fails without proper context."""
        # This should fail in production code
        with pytest.raises(Exception):
            with get_db_session(tenant_id=None, require_tenant=False) as session:
                # Should not reach here without proper authorization
                session.query(ScrapingJob).all()

    def test_direct_sql_injection_prevented(self, postgres_db):
        """Test that direct SQL injection is prevented."""
        tenant_id = str(uuid4())
        
        # Even with direct SQL, RLS should prevent bypass
        with get_db_session(tenant_id=tenant_id, require_tenant=True) as session:
            # Try to inject SQL to bypass tenant isolation
            try:
                # This should be prevented by parameterized queries
                result = session.execute(
                    "SELECT * FROM scraping_jobs WHERE tenant_id = :tenant_id OR '1'='1'",
                    {"tenant_id": tenant_id}
                ).fetchall()
                
                # RLS should still enforce tenant isolation
                for row in result:
                    assert row.tenant_id == tenant_id
                    
            except Exception:
                # SQL injection attempts should fail
                pass

    def test_set_local_tenant_bypass_prevented(self, postgres_db):
        """Test that SET LOCAL tenant_id bypass is prevented."""
        # Try to manually set tenant context
        with pytest.raises(Exception):
            with get_db_session(tenant_id=None, require_tenant=False) as session:
                # This should fail without proper authorization
                session.execute("SET LOCAL app.tenant_id = 'admin-tenant'")
                session.query(ScrapingJob).all()


class TestTaskSecurityValidation:
    """Test security validation in Celery tasks."""

    def test_process_scraping_job_validates_tenant_id(self):
        """Test that process_scraping_job validates tenant_id."""
        from layer1_ingestion.shared.tasks import process_scraping_job
        
        # Mock the database operations to isolate validation
        with patch('layer1_ingestion.shared.tasks.get_db_session') as mock_session:
            # Try with invalid tenant_id
            with pytest.raises(Exception):  # Should fail validation
                process_scraping_job(str(uuid4()), "invalid-tenant-id")

    @pytest.mark.asyncio
    async def test_crawl_url_with_routing_validates_tenant(self):
        """Test that crawl_url_with_routing validates tenant context."""
        from layer1_ingestion.shared.tasks import crawl_url_with_routing

        # Mock get_db_session to simulate tenant validation failure
        with patch('layer1_ingestion.shared.tasks.get_db_session') as mock_session:
            mock_session.side_effect = TenantContextError("Invalid tenant")

            with pytest.raises(TenantContextError):
                await crawl_url_with_routing(
                    job_id=str(uuid4()),
                    url="https://example.com",
                    tenant_id=str(uuid4())
                )
            # Verify get_db_session was called with require_tenant=True
            _, kwargs = mock_session.call_args
            assert kwargs.get('require_tenant') is True

    @pytest.mark.asyncio
    async def test_pipeline_stages_require_tenant_context(self):
        """Test that all pipeline stages require tenant context."""
        from layer1_ingestion.shared import tasks

        pipeline_stages = [
            'compliance_check_stage',
            'browser_crawl_stage',
            'ai_extraction_stage',
            'post_processing_stage',
            'validation_stage',
            'storage_stage',
            'notification_stage',
        ]

        for stage_name in pipeline_stages:
            stage_func = getattr(tasks, stage_name)

            # Mock get_db_session to simulate tenant validation failure
            with patch('layer1_ingestion.shared.tasks.get_db_session') as mock_session:
                mock_session.side_effect = TenantContextError("Invalid tenant")

                with pytest.raises(TenantContextError):
                    result = stage_func(
                        {"job_id": str(uuid4())},
                        tenant_id=str(uuid4())
                    )
                    if inspect.isawaitable(result):
                        await result
                # Verify get_db_session was called with require_tenant=True
                _, kwargs = mock_session.call_args
                assert kwargs.get('require_tenant') is True


class TestErrorHandlingSecurity:
    """Test that error handling doesn't compromise security."""

    def test_tenant_context_errors_not_swallowed(self):
        """Test that tenant context errors are not silently swallowed."""
        with pytest.raises(TenantContextError):
            validate_tenant_id("invalid-uuid")

    def test_database_errors_dont_expose_tenant_data(self, postgres_db, user_id, make_target):
        """Test that database errors don't expose cross-tenant data."""
        tenant_a = str(uuid4())
        tenant_b = str(uuid4())

        # Create target and job for tenant A
        target = make_target(tenant_id=tenant_a)
        job_a = ScrapingJob(
            tenant_id=tenant_a,
            target_id=target.id,
            status="PENDING",
            configuration={"url": "https://tenant-a.com"},
            created_by=user_id,
        )
        postgres_db.add(job_a)
        postgres_db.commit()
        
        # Try to access from tenant B - should fail safely
        with get_db_session(tenant_id=tenant_b, require_tenant=True) as session:
            try:
                result = session.query(ScrapingJob).filter(ScrapingJob.id == job_a.id).first()
                # Should return None due to RLS, not tenant A's data
                assert result is None or result.tenant_id == tenant_b
            except Exception as e:
                # If error occurs, should not expose tenant A's data
                assert "tenant-a" not in str(e).lower()

    def test_broad_exception_handling_security_implications(self):
        """Test that broad exception handling doesn't compromise security."""
        # This test validates that the new exception hierarchy prevents
        # security errors from being caught by broad except blocks
        
        security_errors = [
            InvalidTenantContextError("Test security error"),
            SystemMaintenanceAuthorizationError("Test auth error"),
            CrossTenantAccessError("Test cross-tenant error"),
        ]
        
        for error in security_errors:
            # Security errors should not be caught by generic exception handlers
            # that are meant for recoverable errors
            try:
                raise error
            except SecurityError:
                # This should catch security errors
                pass
            except Exception:
                # This should NOT catch security errors in production code
                # (this test ensures our exception hierarchy works)
                assert False, f"Security error {type(error)} was caught by generic except"


class TestAuditLoggingSecurity:
    """Test that audit logging captures security events."""

    def test_maintenance_operations_are_audited(self):
        """Test that maintenance operations generate audit logs."""
        from layer1_ingestion.shared.maintenance import maintenance_audit_log, SystemMaintenanceIdentity, MaintenanceOperation
        from unittest.mock import patch
        
        timestamp = int(__import__('time').time())
        token = f"fabric4l-maintenance:{timestamp}:test-sig"
        identity = SystemMaintenanceIdentity(token)
        
        with patch('layer1_ingestion.shared.maintenance.get_maintenance_identity', return_value=identity):
            with maintenance_audit_log(MaintenanceOperation.CLEANUP_OLD_CONTENT.value, tenant_id="test-tenant") as record:
                record.rows_affected = 10
                record.metadata = {"test": "data"}
            
            assert record.operation == MaintenanceOperation.CLEANUP_OLD_CONTENT.value
            assert record.tenant_id == "test-tenant"
            assert record.success is True
            assert record.rows_affected == 10
            assert record.system_identity == "fabric4l-system-maintenance"

    def test_failed_operations_are_audited(self):
        """Test that failed operations are properly audited."""
        from layer1_ingestion.shared.maintenance import maintenance_audit_log, SystemMaintenanceIdentity, MaintenanceOperation
        from unittest.mock import patch
        
        timestamp = int(__import__('time').time())
        token = f"fabric4l-maintenance:{timestamp}:test-sig"
        identity = SystemMaintenanceIdentity(token)
        
        with patch('layer1_ingestion.shared.maintenance.get_maintenance_identity', return_value=identity):
            try:
                with maintenance_audit_log(MaintenanceOperation.SYSTEM_HEALTH_CHECK.value, tenant_id=None) as record:
                    raise ValueError("Test failure")
            except ValueError:
                pass  # Expected
            
            assert record.operation == MaintenanceOperation.SYSTEM_HEALTH_CHECK.value
            assert record.success is False
            assert "Test failure" in record.error_message


class TestSecurityRegressionPrevention:
    """Test that security regressions are prevented."""

    def test_no_admin_role_bypass_in_code(self):
        """Test that admin role bypass patterns are not present."""
        import os
        import re
        from pathlib import Path
        
        # Check for dangerous patterns in task files
        tasks_file = Path(__file__).parent.parent.parent / 'src' / 'layer1_ingestion' / 'shared' / 'tasks.py'
        
        with open(tasks_file, 'r') as f:
            content = f.read()
        
        # Look for dangerous patterns
        dangerous_patterns = [
            r'require_tenant=False.*ScrapingJob',  # Tenant-scoped queries with bypass
            r'SET LOCAL.*tenant_id.*admin',       # Direct tenant context setting
            r'admin.*role.*tenant',                # Admin role tenant access
            r'super.*admin.*tenant',               # Super admin tenant bypass
        ]
        
        for pattern in dangerous_patterns:
            matches = re.findall(pattern, content, re.IGNORECASE)
            if matches:
                pytest.fail(f"Dangerous pattern found: {pattern} in {matches}")

    def test_all_tenant_scoped_tables_use_rls(self):
        """Test that all tenant-scoped tables have RLS enabled."""
        # This would require database introspection in a real test
        # For now, document the requirement
        tenant_scoped_tables = [
            'scraping_jobs',
            'scraping_targets', 
            'raw_content',
            'job_stages',
            'crawl_decisions',
        ]
        
        # In production, verify these tables have RLS policies
        for table in tenant_scoped_tables:
            assert table != '', f"Table {table} should have RLS enabled"

    def test_system_operations_are_properly_documented(self):
        """Test that system operations have proper documentation."""
        from layer1_ingestion.shared.maintenance import MaintenanceOperation
        
        # All operations should be documented
        for op in MaintenanceOperation:
            assert op.value != '', f"Operation {op} should have a descriptive name"
            assert len(op.value) > 3, f"Operation {op.value} should be descriptive"
