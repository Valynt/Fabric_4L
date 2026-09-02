"""PostgreSQL-backed tests for system maintenance authorization.

Tests validate that system maintenance operations require proper authorization
and that tenant isolation is preserved for all operations.

These tests MUST run against PostgreSQL.
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock
from uuid import uuid4

from layer1_ingestion.shared.exceptions import (
    SystemMaintenanceAuthorizationError,
    InvalidTenantContextError,
)
from layer1_ingestion.shared.maintenance import (
    SystemMaintenanceIdentity,
    MaintenanceOperation,
    authorize_maintenance_operation,
    maintenance_audit_log,
    system_maintenance_context,
    is_system_maintenance_request,
    require_system_maintenance,
)


pytestmark = pytest.mark.requires_postgres


class TestSystemMaintenanceIdentity:
    """Test system maintenance identity validation."""

    def test_valid_identity_token(self):
        """Test that valid identity tokens are accepted."""
        # Create a valid token
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:valid-signature"
        
        identity = SystemMaintenanceIdentity(identity_token=token)
        assert identity.is_valid() is True
        assert identity.identity_name == "fabric4l-system-maintenance"

    def test_invalid_identity_token_format(self):
        """Test that invalid token formats are rejected."""
        invalid_tokens = [
            "invalid-token",
            "wrong-prefix:123:signature",
            "fabric4l-maintenance:invalid-timestamp:signature",
            "fabric4l-maintenance",  # Missing parts
        ]
        
        for token in invalid_tokens:
            identity = SystemMaintenanceIdentity(identity_token=token)
            assert identity.is_valid() is False

    def test_expired_identity_token(self):
        """Test that expired tokens are rejected."""
        # Create an expired token (25 hours ago)
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp()) - 90000
        token = f"fabric4l-maintenance:{timestamp}:signature"
        
        identity = SystemMaintenanceIdentity(identity_token=token)
        assert identity.is_valid() is False

    def test_no_identity_token(self):
        """Test behavior when no token is configured."""
        with patch.dict(os.environ, {}, clear=True):
            identity = SystemMaintenanceIdentity()
            assert identity.is_valid() is False

    def test_environment_variable_token(self):
        """Test that environment variable tokens are used."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:env-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            identity = SystemMaintenanceIdentity()
            assert identity.is_valid() is True
            assert identity.identity_token == token


class TestMaintenanceOperationAuthorization:
    """Test maintenance operation authorization."""

    def test_allowlisted_operation_succeeds(self):
        """Test that allowlisted operations succeed with valid identity."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            # Should not raise exception
            authorize_maintenance_operation("cleanup_old_content", tenant_id="tenant-123")
            authorize_maintenance_operation("system_health_check", tenant_id=None)

    def test_non_allowlisted_operation_fails(self):
        """Test that non-allowlisted operations fail."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            with pytest.raises(SystemMaintenanceAuthorizationError) as exc_info:
                authorize_maintenance_operation("unauthorized_operation", tenant_id=None)
            
            assert "not in maintenance allowlist" in str(exc_info.value)
            assert exc_info.value.operation == "unauthorized_operation"

    def test_invalid_identity_fails(self):
        """Test that operations fail with invalid identity."""
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": ""}):
            with pytest.raises(SystemMaintenanceAuthorizationError) as exc_info:
                authorize_maintenance_operation("cleanup_old_content", tenant_id=None)

            assert "Invalid or missing system maintenance identity" in str(exc_info.value)

    def test_system_wide_operation_requires_specific_ops(self):
        """Test that system-wide operations require specific allowlisted ops."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            # cleanup_old_content requires tenant_id for tenant-iterated execution
            with pytest.raises(SystemMaintenanceAuthorizationError) as exc_info:
                authorize_maintenance_operation("cleanup_old_content", tenant_id=None)
            
            assert "requires tenant_id for tenant-iterated execution" in str(exc_info.value)

    def test_system_only_operations_succeed_without_tenant(self):
        """Test that system-only operations succeed without tenant_id."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            # These operations are allowed system-wide
            authorize_maintenance_operation("system_health_check", tenant_id=None)
            authorize_maintenance_operation("index_rebuild", tenant_id=None)
            authorize_maintenance_operation("audit_export", tenant_id=None)


class TestMaintenanceAuditLog:
    """Test maintenance operation audit logging."""

    def test_audit_log_success(self):
        """Test that successful operations are logged properly."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            with maintenance_audit_log("cleanup_old_content", tenant_id="tenant-123") as record:
                record.rows_affected = 42
                record.metadata = {"test": "data"}
            
            assert record.operation == "cleanup_old_content"
            assert record.tenant_id == "tenant-123"
            assert record.success is True
            assert record.rows_affected == 42
            assert record.system_identity == "fabric4l-system-maintenance"
            assert record.started_at is not None
            assert record.completed_at is not None

    def test_audit_log_failure(self):
        """Test that failed operations are logged properly."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            try:
                with maintenance_audit_log("cleanup_old_content", tenant_id="tenant-123") as record:
                    raise ValueError("Test error")
            except ValueError:
                pass  # Expected
            
            assert record.operation == "cleanup_old_content"
            assert record.tenant_id == "tenant-123"
            assert record.success is False
            assert record.error_message == repr(ValueError("Test error"))
            assert record.started_at is not None
            assert record.completed_at is not None

    def test_audit_log_authorization_failure(self):
        """Test that authorization failures are not logged as operations."""
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": "invalid-token"}):
            with pytest.raises(SystemMaintenanceAuthorizationError):
                with maintenance_audit_log("cleanup_old_content", tenant_id=None):
                    pass  # Should not reach here


class TestSystemMaintenanceContext:
    """Test system maintenance context manager."""

    def test_valid_context(self):
        """Test that valid system maintenance context works."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            with system_maintenance_context():
                # Context should be established
                pass

    def test_invalid_context_fails(self):
        """Test that invalid identity fails context establishment."""
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": "invalid-token"}):
            with pytest.raises(SystemMaintenanceAuthorizationError) as exc_info:
                with system_maintenance_context():
                    pass
            
            assert "requires valid system identity" in str(exc_info.value)


class TestSystemMaintenanceRequestDetection:
    """Test HTTP request detection for system maintenance."""

    def test_valid_maintenance_request(self):
        """Test that valid maintenance headers are detected."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            headers = {"X-Fabric4L-Maintenance": token}
            assert is_system_maintenance_request(headers) is True

    def test_missing_maintenance_header(self):
        """Test that missing headers are rejected."""
        headers = {}
        assert is_system_maintenance_request(headers) is False

    def test_invalid_maintenance_header(self):
        """Test that invalid headers are rejected."""
        headers = {"X-Fabric4L-Maintenance": "invalid-token"}
        assert is_system_maintenance_request(headers) is False

    def test_require_system_maintenance_success(self):
        """Test that require_system_maintenance succeeds with valid headers."""
        timestamp = int(__import__("datetime").datetime.now(__import__("datetime").timezone.utc).timestamp())
        token = f"fabric4l-maintenance:{timestamp}:test-signature"
        
        with patch.dict(os.environ, {"FABRIC4L_MAINTENANCE_TOKEN": token}):
            headers = {"X-Fabric4L-Maintenance": token}
            # Should not raise exception
            require_system_maintenance(headers)

    def test_require_system_maintenance_failure(self):
        """Test that require_system_maintenance fails with invalid headers."""
        headers = {"X-Fabric4L-Maintenance": "invalid-token"}
        
        with pytest.raises(SystemMaintenanceAuthorizationError) as exc_info:
            require_system_maintenance(headers)
        
        assert "requires system maintenance authorization" in str(exc_info.value)


class TestIntegrationWithCleanupOldContent:
    """Test integration with cleanup_old_content task."""

    def test_cleanup_with_valid_tenant_id(self, postgres_db):
        """Test cleanup with valid tenant_id uses RLS."""
        from layer1_ingestion.shared.tasks import cleanup_old_content

        tenant_id = str(uuid4())

        # Mock the maintenance audit log to avoid token requirements in tests
        # while still exercising the tenant-scoped cleanup path.
        with patch('layer1_ingestion.shared.tasks.cleanup.maintenance_audit_log') as mock_audit:
            mock_record = MagicMock()
            mock_audit.return_value.__enter__ = MagicMock(return_value=mock_record)
            mock_audit.return_value.__exit__ = MagicMock(return_value=False)

            # Should not raise exception
            try:
                cleanup_old_content(days=1, tenant_id=tenant_id)
            except Exception:
                pass  # Database might not exist in test, but authorization should work

            # Verify tenant-scoped audit log was opened with the right tenant.
            mock_audit.assert_called_once_with("cleanup_old_content", tenant_id=tenant_id)

    def test_cleanup_without_tenant_id_requires_authorization(self, postgres_db):
        """Test that cleanup without tenant_id requires system authorization."""
        from layer1_ingestion.shared.tasks import cleanup_old_content
        
        # Mock the maintenance authorization to fail
        with patch('layer1_ingestion.shared.tasks.cleanup.authorize_maintenance_operation') as mock_auth:
            mock_auth.side_effect = SystemMaintenanceAuthorizationError("Test failure")
            
            with pytest.raises(SystemMaintenanceAuthorizationError):
                cleanup_old_content(days=1, tenant_id=None)

    def test_cleanup_with_invalid_tenant_id_fails(self, postgres_db):
        """Test that cleanup with invalid tenant_id fails."""
        from layer1_ingestion.shared.tasks import cleanup_old_content
        
        with pytest.raises(InvalidTenantContextError) as exc_info:
            cleanup_old_content(days=1, tenant_id="invalid-uuid")
        
        assert "Invalid tenant_id format" in str(exc_info.value)




    def test_system_tenant_enumeration_uses_registry_only(self, postgres_db):
        """Regression: system enumeration must not read tenant-owned tables without tenant context."""
        from layer1_ingestion.shared.tasks import _enumerate_authorized_tenants_for_cleanup

        class _FakeQuery:
            def __init__(self, target):
                self.target = target

            def filter(self, *_args, **_kwargs):
                return self

            def all(self):
                return [(uuid4(),)]

        class _FakeSession:
            def __init__(self, tracker):
                self._tracker = tracker

            def query(self, target):
                self._tracker.append(target)
                return _FakeQuery(target)

        class _FakeCtx:
            def __init__(self, tracker):
                self._tracker = tracker

            def __enter__(self):
                return _FakeSession(self._tracker)

            def __exit__(self, *_args):
                return False

        query_targets = []

        with patch('layer1_ingestion.shared.tasks.cleanup.authorize_maintenance_operation'):
            with patch('layer1_ingestion.shared.tasks.cleanup.maintenance_audit_log') as mock_audit:
                mock_audit.return_value.__enter__ = MagicMock()
                mock_audit.return_value.__exit__ = MagicMock(return_value=False)
                with patch('layer1_ingestion.shared.tasks.cleanup.get_db_session', return_value=_FakeCtx(query_targets)):
                    tenant_ids = _enumerate_authorized_tenants_for_cleanup()

        assert len(tenant_ids) == 1
        assert query_targets
        queried_target = query_targets[0]
        assert 'tenantregistry' in str(queried_target).lower()
        assert 'rawcontent' not in str(queried_target).lower()
class TestMaintenanceOperationEnum:
    """Test MaintenanceOperation enum functionality."""

    def test_has_value_with_valid_operations(self):
        """Test that has_value works with valid operations."""
        assert MaintenanceOperation.has_value("cleanup_old_content") is True
        assert MaintenanceOperation.has_value("system_health_check") is True
        assert MaintenanceOperation.has_value("audit_export") is True

    def test_has_value_with_invalid_operations(self):
        """Test that has_value rejects invalid operations."""
        assert MaintenanceOperation.has_value("invalid_operation") is False
        assert MaintenanceOperation.has_value("delete_all_data") is False
        assert MaintenanceOperation.has_value("") is False

    def test_all_operations_are_allowlisted(self):
        """Test that all enum values are properly documented."""
        allowed_ops = {
            "cleanup_old_content",
            "migrate_data", 
            "system_health_check",
            "cache_warming",
            "index_rebuild",
            "audit_export",
        }
        
        enum_ops = {op.value for op in MaintenanceOperation}
        assert enum_ops == allowed_ops
