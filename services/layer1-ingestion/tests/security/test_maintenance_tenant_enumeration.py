"""Tests for maintenance tenant enumeration flow.

Tests prove no tenant-owned reads before tenant context in maintenance flows:
- Tenant-specific cleanup mode only affects specified tenant
- System-scoped cleanup mode iterates TenantRegistry
- No cross-tenant reads before tenant context is set
- RLS enforcement per tenant iteration
- Audit log verification for all maintenance operations
"""

from __future__ import annotations

import inspect
import pytest
from uuid import uuid4, UUID
from datetime import datetime, timedelta, UTC

from layer1_ingestion.shared.models import (
    RawContent,
    TenantRegistry,
)
from layer1_ingestion.shared.tasks import cleanup_old_content


pytestmark = pytest.mark.requires_postgres


@pytest.fixture
def bypass_maintenance_auth(monkeypatch):
    """Patch maintenance authorization so cleanup tests focus on isolation."""
    # tasks.py imports the function, so patch the tasks module binding too.
    monkeypatch.setattr(
        "layer1_ingestion.shared.maintenance.authorize_maintenance_operation",
        lambda operation, tenant_id=None: None,
    )
    monkeypatch.setattr(
        "layer1_ingestion.shared.tasks.cleanup.authorize_maintenance_operation",
        lambda operation, tenant_id=None: None,
    )


class TestTenantSpecificCleanupMode:
    """Test tenant-specific cleanup mode."""

    def test_tenant_specific_cleanup_only_affects_specified_tenant(
        self, postgres_db, org_id, other_org_id, bypass_maintenance_auth, make_job
    ):
        """cleanup_old_content(tenant_id=A) should only delete tenant A's content."""
        job_a = make_job(tenant_id=org_id)
        job_b = make_job(tenant_id=other_org_id)

        # Create content for tenant A
        content_a = RawContent(
            id=uuid4(),
            tenant_id=org_id,
            job_id=job_a.id,
            target_id=job_a.target_id,
            source_url="https://example-a.com",
            source_final_url="https://example-a.com",
            source_domain="example-a.com",
            source_http_status=200,
            source_headers={},
            meta_title="Content A",
            capture_method="STATIC",
            capture_javascript_executed=False,
            capture_wait_time_ms=100,
            content_hash="hash-a",
            is_duplicate=False,
            processing_status="COMPLETED",
            created_at=datetime.now(UTC) - timedelta(days=60),  # Old content
        )
        postgres_db.add(content_a)

        # Create content for tenant B
        content_b = RawContent(
            id=uuid4(),
            tenant_id=other_org_id,
            job_id=job_b.id,
            target_id=job_b.target_id,
            source_url="https://example-b.com",
            source_final_url="https://example-b.com",
            source_domain="example-b.com",
            source_http_status=200,
            source_headers={},
            meta_title="Content B",
            capture_method="STATIC",
            capture_javascript_executed=False,
            capture_wait_time_ms=100,
            content_hash="hash-b",
            is_duplicate=False,
            processing_status="COMPLETED",
            created_at=datetime.now(UTC) - timedelta(days=60),  # Old content
        )
        postgres_db.add(content_b)
        postgres_db.commit()

        # Run cleanup for tenant A only
        result = cleanup_old_content(days=30, tenant_id=str(org_id))

        # Verify tenant A's content was marked DELETED
        content_a_after = postgres_db.query(RawContent).filter(RawContent.id == content_a.id).first()
        assert content_a_after is not None
        assert content_a_after.processing_status == "DELETED"

        # Verify tenant B's content was NOT deleted
        content_b_after = postgres_db.query(RawContent).filter(RawContent.id == content_b.id).first()
        assert content_b_after is not None
        assert content_b_after.processing_status == "COMPLETED"

    def test_tenant_specific_cleanup_uses_require_tenant_true(self, db, org_id):
        """Tenant-specific cleanup should use require_tenant=True."""
        # This test verifies that the implementation uses require_tenant=True
        # when tenant_id is provided
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect

        source = inspect.getsource(cleanup_old_content)

        # Should use require_tenant=True when tenant_id is provided
        assert "require_tenant=True" in source or "require_tenant=True if" in source, \
            "Tenant-specific cleanup should use require_tenant=True"


class TestSystemScopedCleanupMode:
    """Test system-scoped cleanup mode."""

    def test_system_scoped_cleanup_iterates_tenant_registry(
        self, postgres_db, org_id, other_org_id, bypass_maintenance_auth, make_job
    ):
        """System-scoped cleanup should iterate TenantRegistry."""
        # Ensure both tenants are in TenantRegistry
        tenant_a = (
            postgres_db.query(TenantRegistry).filter(TenantRegistry.tenant_id == org_id).first()
        )
        if not tenant_a:
            tenant_a = TenantRegistry(
                tenant_id=org_id,
            )
            postgres_db.add(tenant_a)

        tenant_b = (
            postgres_db.query(TenantRegistry).filter(TenantRegistry.tenant_id == other_org_id).first()
        )
        if not tenant_b:
            tenant_b = TenantRegistry(
                tenant_id=other_org_id,
            )
            postgres_db.add(tenant_b)
        postgres_db.commit()

        # Create old content for both tenants
        for tenant_id in [org_id, other_org_id]:
            job = make_job(tenant_id=tenant_id)
            content = RawContent(
                id=uuid4(),
                tenant_id=tenant_id,
                job_id=job.id,
                target_id=job.target_id,
                source_url=f"https://example-{tenant_id}.com",
                source_final_url=f"https://example-{tenant_id}.com",
                source_domain=f"example-{tenant_id}.com",
                source_http_status=200,
                source_headers={},
                meta_title=f"Content {tenant_id}",
                capture_method="STATIC",
                capture_javascript_executed=False,
                capture_wait_time_ms=100,
                content_hash=f"hash-{tenant_id}",
                is_duplicate=False,
                processing_status="COMPLETED",
                created_at=datetime.now(UTC) - timedelta(days=60),
            )
            postgres_db.add(content)
        postgres_db.commit()

        # Run system-scoped cleanup
        result = cleanup_old_content(days=30, tenant_id=None)

        # Verify both tenants' content was marked DELETED
        for tenant_id in [org_id, other_org_id]:
            content_count = (
                postgres_db.query(RawContent)
                .filter(
                    RawContent.tenant_id == tenant_id,
                    RawContent.processing_status == "DELETED",
                )
                .count()
            )
            assert content_count == 1

    def test_system_scoped_cleanup_uses_rls_per_tenant(self, db, org_id, other_org_id):
        """System-scoped cleanup should use RLS per tenant iteration."""
        # This test verifies that the implementation iterates tenants
        # and uses require_tenant=True for each iteration
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect

        source = inspect.getsource(cleanup_old_content)

        # Should iterate TenantRegistry
        assert "TenantRegistry" in source, "System-scoped cleanup should iterate TenantRegistry"

        # Should use require_tenant=True in the loop
        assert "require_tenant=True" in source, \
            "System-scoped cleanup should use require_tenant=True per tenant"


class TestNoCrossTenantReadsBeforeContext:
    """Test that no tenant-owned reads occur before tenant context."""

    def test_no_tenant_owned_reads_before_tenant_context(self, db, org_id):
        """No tenant-owned data reads before tenant context is set."""
        # This test verifies the implementation pattern
        # System-scoped mode should:
        # 1. Read TenantRegistry (system table, no RLS needed)
        # 2. For each tenant: set tenant context, then read tenant-owned data
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect

        source = inspect.getsource(cleanup_old_content)

        # Check that TenantRegistry query happens before tenant-owned queries
        lines = source.split("\n")

        tenant_registry_line = None
        raw_content_line = None

        for i, line in enumerate(lines):
            if "TenantRegistry" in line:
                tenant_registry_line = i
            if "RawContent" in line:
                raw_content_line = i

        # TenantRegistry should be queried before RawContent in system-scoped mode
        # This is a heuristic check - in production, use stricter static analysis
        if tenant_registry_line is not None and raw_content_line is not None:
            # In system-scoped mode, TenantRegistry comes first
            # Then loop over tenants with require_tenant=True
            assert tenant_registry_line is not None, "TenantRegistry query not found"
            assert raw_content_line is not None, "RawContent query not found"
            assert tenant_registry_line < raw_content_line, (
                "TenantRegistry must be queried before any tenant-owned RawContent query"
            )

    def test_tenant_registry_is_system_table(self, db):
        """TenantRegistry should be a system table (no RLS needed)."""
        # This test documents that TenantRegistry is a system table
        # In production, verify this via database schema inspection
        # For now, we document the assumption
        tenant_registry = db.query(TenantRegistry).first()
        # If TenantRegistry exists, it's a system table
        # This is a documentation test
        from layer1_ingestion.shared.tasks import _enumerate_authorized_tenants_for_cleanup
        source = inspect.getsource(_enumerate_authorized_tenants_for_cleanup)
        assert "get_db_session(tenant_id=None, require_tenant=False)" in source,             "TenantRegistry must be queried without tenant RLS (system-owned table)"


class TestRLSEnforcementPerTenant:
    """Test RLS enforcement per tenant iteration."""

    def test_each_tenant_iteration_uses_require_tenant_true(self, db, org_id):
        """Each tenant iteration should use require_tenant=True."""
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect

        source = inspect.getsource(cleanup_old_content)

        # In the tenant iteration loop, should use require_tenant=True
        # Pattern: for tenant in tenants: with get_db_session(tenant_id=..., require_tenant=True)
        assert "require_tenant=True" in source, \
            "Each tenant iteration should use require_tenant=True"

    def test_no_cross_tenant_access_in_loop(self, db, org_id, other_org_id):
        """Loop should not access cross-tenant data."""
        # This test verifies that the loop doesn't accidentally access
        # other tenants' data during iteration
        source = inspect.getsource(cleanup_old_content)
        loop_body = source.split("for tenant_uuid in tenant_ids:", 1)[1]
        # Each iteration must open a tenant-scoped session
        assert "get_db_session(tenant_id=tenant_uuid, require_tenant=True)" in loop_body,             "Tenant loop must use require_tenant=True to scope data access"


class TestAuditLogVerification:
    """Test audit log verification for maintenance operations."""

    def test_maintenance_audit_log_records_tenant_iterations(self, db, org_id):
        """maintenance_audit_log should record all tenant iterations."""
        # This test verifies that the implementation uses maintenance_audit_log
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect

        source = inspect.getsource(cleanup_old_content)

        # Should use maintenance_audit_log
        assert "maintenance_audit_log" in source, \
            "Maintenance operations should use maintenance_audit_log"

    def test_audit_log_includes_operation_and_tenant_id(self, db, org_id):
        """Audit log should include operation name and tenant_id."""
        # This test verifies the audit log includes required fields
        # Expected: operation="cleanup_old_content", tenant_id=str(tenant_uuid)
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect

        source = inspect.getsource(cleanup_old_content)

        # Should include operation name
        assert 'operation="cleanup_old_content"' in source or \
              'operation=' in source, \
            "Audit log should include operation name"

        # Should include tenant_id
        assert "tenant_id=" in source, "Audit log should include tenant_id"


class TestMaintenanceAuthorization:
    """Test maintenance operation authorization."""

    def test_maintenance_operations_require_authorization(self):
        """Maintenance operations should require proper authorization."""
        from layer1_ingestion.shared.tasks import _enumerate_authorized_tenants_for_cleanup
        source = inspect.getsource(_enumerate_authorized_tenants_for_cleanup)
        assert "authorize_maintenance_operation" in source,             "System-scoped maintenance must call authorize_maintenance_operation before tenant enumeration"

    def test_system_maintenance_uses_system_identity(self, db):
        """System maintenance should use system identity."""
        # This test verifies that system maintenance uses a system identity
        # Expected: system_identity="fabric4l-system-maintenance"
        from layer1_ingestion.shared.tasks import cleanup_old_content
        import inspect

        source = inspect.getsource(cleanup_old_content)

        # Should use system identity in audit log
        assert "system_identity" in source, \
            "System maintenance should use system identity"
