"""
Tests for super-admin privileged access audit functionality (Task 2).

Verifies that all super-admin bypass operations emit CROSS_TENANT_ACCESS
audit events with comprehensive details for compliance monitoring.
"""

import pytest

pytestmark = [pytest.mark.security, pytest.mark.tenant_boundary]
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

from fastapi import HTTPException, Request

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_privileged_access
from value_fabric.shared.audit.models import AuditAction, AuditOutcome, PrivilegedAccessDetails


@pytest.fixture
def super_admin_context():
    """Create a super admin request context."""
    return RequestContext(
        tenant_id=uuid4(),
        user_id=uuid4(),
        roles=["super_admin"],
        permissions=["all"],
        request_id="test-request-123",
    )


@pytest.fixture
def regular_user_context():
    """Create a regular user request context."""
    return RequestContext(
        tenant_id=uuid4(),
        user_id=uuid4(),
        roles=["user"],
        permissions=["read"],
        request_id="test-request-456",
    )


@pytest.fixture
def mock_request():
    """Create a mock FastAPI request."""
    request = MagicMock(spec=Request)
    request.headers = {}
    request.url.path = "/api/v1/admin/cross-tenant-data"
    request.client.host = "192.168.1.100"
    return request


class TestRequirePrivilegedAccess:
    """Tests for require_privileged_access dependency."""
    
    @pytest.mark.asyncio
    async def test_blocks_non_super_admin(self, mock_request, regular_user_context):
        """Verify non-super-admin users are blocked."""
        dependency = require_privileged_access()
        
        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, context=regular_user_context)
        
        assert exc_info.value.status_code == 403
        assert "super admin role" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_requires_reason_header(self, mock_request, super_admin_context):
        """Verify X-Privileged-Reason header is required."""
        dependency = require_privileged_access()
        
        with pytest.raises(HTTPException) as exc_info:
            await dependency(request=mock_request, context=super_admin_context)
        
        assert exc_info.value.status_code == 400
        assert "X-Privileged-Reason" in exc_info.value.detail
    
    @pytest.mark.asyncio
    async def test_accepts_valid_privileged_access(self, mock_request, super_admin_context):
        """Verify valid super-admin access with reason is allowed."""
        mock_request.headers["X-Privileged-Reason"] = "Emergency data recovery"
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock):
            result = await dependency(request=mock_request, context=super_admin_context)
        
        assert result == super_admin_context
    
    @pytest.mark.asyncio
    async def test_emits_cross_tenant_access_audit_event(self, mock_request, super_admin_context):
        """Verify CROSS_TENANT_ACCESS audit event is emitted."""
        mock_request.headers["X-Privileged-Reason"] = "Customer support ticket #12345"
        mock_request.headers["X-Approval-Ticket"] = "JIRA-SEC-9876"
        super_admin_context.accessed_tenant_ids = {"tenant-a", "tenant-b"}
        
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            await dependency(request=mock_request, context=super_admin_context)
            
            # Verify audit event was emitted
            assert mock_emit.called
            call_kwargs = mock_emit.call_args.kwargs
            
            assert call_kwargs["action"] == AuditAction.CROSS_TENANT_ACCESS
            assert call_kwargs["actor_id"] == super_admin_context.user_id
            assert call_kwargs["actor_type"] == "super_admin"
            assert call_kwargs["resource_type"] == "privileged_session"
    
    @pytest.mark.asyncio
    async def test_audit_details_include_accessed_tenants(self, mock_request, super_admin_context):
        """Verify audit details include list of accessed tenant IDs."""
        mock_request.headers["X-Privileged-Reason"] = "Data migration"
        super_admin_context.accessed_tenant_ids = {"tenant-a", "tenant-b", "tenant-c"}
        
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            await dependency(request=mock_request, context=super_admin_context)
            
            details = mock_emit.call_args.kwargs["details"]
            assert "accessed_tenant_ids" in details
            assert set(details["accessed_tenant_ids"]) == {"tenant-a", "tenant-b", "tenant-c"}
    
    @pytest.mark.asyncio
    async def test_audit_details_include_reason(self, mock_request, super_admin_context):
        """Verify audit details include the access reason."""
        reason = "Emergency incident response for customer outage"
        mock_request.headers["X-Privileged-Reason"] = reason
        
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            await dependency(request=mock_request, context=super_admin_context)
            
            details = mock_emit.call_args.kwargs["details"]
            assert details["reason"] == reason
    
    @pytest.mark.asyncio
    async def test_audit_details_include_approval_ticket(self, mock_request, super_admin_context):
        """Verify audit details include optional approval ticket."""
        mock_request.headers["X-Privileged-Reason"] = "Approved access"
        mock_request.headers["X-Approval-Ticket"] = "JIRA-SEC-12345"
        
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            await dependency(request=mock_request, context=super_admin_context)
            
            details = mock_emit.call_args.kwargs["details"]
            assert details["approval_ticket"] == "JIRA-SEC-12345"
    
    @pytest.mark.asyncio
    async def test_tracks_session_duration(self, mock_request, super_admin_context):
        """Verify session duration is tracked."""
        import time
        
        mock_request.headers["X-Privileged-Reason"] = "Testing"
        super_admin_context.privileged_session_start = time.time() - 45  # 45 seconds ago
        
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            await dependency(request=mock_request, context=super_admin_context)
            
            details = mock_emit.call_args.kwargs["details"]
            assert details["session_duration_seconds"] >= 45
            assert details["session_duration_seconds"] < 50  # Allow some tolerance
    
    @pytest.mark.asyncio
    async def test_initializes_session_start_on_first_access(self, mock_request, super_admin_context):
        """Verify privileged_session_start is initialized on first access."""
        mock_request.headers["X-Privileged-Reason"] = "First access"
        assert super_admin_context.privileged_session_start is None
        
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock):
            await dependency(request=mock_request, context=super_admin_context)
        
        assert super_admin_context.privileged_session_start is not None
    
    @pytest.mark.asyncio
    async def test_does_not_block_on_audit_failure(self, mock_request, super_admin_context):
        """Verify request proceeds even if audit event emission fails."""
        mock_request.headers["X-Privileged-Reason"] = "Testing audit failure"
        
        dependency = require_privileged_access(require_audit_emission=False)
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            mock_emit.side_effect = Exception("Audit system down")
            
            # Should not raise exception when audit emission is not required
            result = await dependency(request=mock_request, context=super_admin_context)
            assert result == super_admin_context
    
    @pytest.mark.asyncio
    async def test_custom_reason_header_name(self, mock_request, super_admin_context):
        """Verify custom reason header name can be specified."""
        mock_request.headers["X-Admin-Justification"] = "Custom header test"
        
        dependency = require_privileged_access(privilege_reason_header="X-Admin-Justification")
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock):
            result = await dependency(request=mock_request, context=super_admin_context)
        
        assert result == super_admin_context
    
    @pytest.mark.asyncio
    async def test_audit_disabled_allows_access_without_reason(self, mock_request, super_admin_context):
        """Verify audit can be disabled for internal services."""
        # No reason header provided
        dependency = require_privileged_access(require_audit_log=False)
        
        # Should succeed without requiring reason header
        result = await dependency(request=mock_request, context=super_admin_context)
        assert result == super_admin_context


class TestPrivilegedAccessDetails:
    """Tests for PrivilegedAccessDetails model."""
    
    def test_creates_with_required_fields(self):
        """Verify model can be created with required fields."""
        details = PrivilegedAccessDetails(
            reason="Emergency access",
        )
        
        assert details.reason == "Emergency access"
        assert details.accessed_tenant_ids == []
        assert details.resource_types == []
        assert details.session_duration_seconds == 0
    
    def test_creates_with_all_fields(self):
        """Verify model can be created with all fields."""
        details = PrivilegedAccessDetails(
            accessed_tenant_ids=["tenant-a", "tenant-b"],
            resource_types=["Entity", "Relationship"],
            session_duration_seconds=120,
            reason="Approved data migration",
            approval_ticket="JIRA-OPS-5678",
            query_count=15,
            data_exported=True,
        )
        
        assert len(details.accessed_tenant_ids) == 2
        assert details.session_duration_seconds == 120
        assert details.approval_ticket == "JIRA-OPS-5678"
        assert details.query_count == 15
        assert details.data_exported is True
    
    def test_serializes_to_dict(self):
        """Verify model can be serialized to dict for audit storage."""
        details = PrivilegedAccessDetails(
            accessed_tenant_ids=["tenant-a"],
            reason="Testing",
            query_count=5,
        )
        
        data = details.model_dump()
        
        assert isinstance(data, dict)
        assert data["accessed_tenant_ids"] == ["tenant-a"]
        assert data["reason"] == "Testing"
        assert data["query_count"] == 5


class TestCrossTenantAccessScenarios:
    """Integration tests for cross-tenant access scenarios."""
    
    @pytest.mark.asyncio
    async def test_multiple_tenant_access_tracked(self, mock_request, super_admin_context):
        """Verify accessing multiple tenants is tracked in audit."""
        mock_request.headers["X-Privileged-Reason"] = "Multi-tenant investigation"
        
        # Simulate accessing multiple tenants
        super_admin_context.accessed_tenant_ids.add("tenant-a")
        super_admin_context.accessed_tenant_ids.add("tenant-b")
        super_admin_context.accessed_tenant_ids.add("tenant-c")
        
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            await dependency(request=mock_request, context=super_admin_context)
            
            details = mock_emit.call_args.kwargs["details"]
            assert len(details["accessed_tenant_ids"]) == 3
            assert details["query_count"] == 3
    
    @pytest.mark.asyncio
    async def test_zero_tenant_access_allowed(self, mock_request, super_admin_context):
        """Verify super-admin can access without crossing tenant boundaries."""
        mock_request.headers["X-Privileged-Reason"] = "System maintenance"
        
        # No tenants accessed yet
        assert len(super_admin_context.accessed_tenant_ids) == 0
        
        dependency = require_privileged_access()
        
        with patch("shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            await dependency(request=mock_request, context=super_admin_context)
            
            details = mock_emit.call_args.kwargs["details"]
            assert details["accessed_tenant_ids"] == []
            assert details["query_count"] == 0


class TestAdminConsoleEndpoint:
    """Contract tests for the cross-tenant admin console endpoint (SAAS-002)."""

    @pytest.fixture
    def admin_console_app(self, super_admin_context):
        """Minimal FastAPI app with the admin console router and injected context."""
        from fastapi import FastAPI
        from starlette.middleware.base import BaseHTTPMiddleware

        class _InjectContextMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, context=None):
                super().__init__(app)
                self.context = context

            async def dispatch(self, request, call_next):
                request.state.governance_context = self.context
                return await call_next(request)

        app = FastAPI()
        app.add_middleware(_InjectContextMiddleware, context=super_admin_context)

        # Import and register the router
        from layer4_agents.tenants.api.routes.admin_console import (
            router as admin_console_router,
        )
        from layer4_agents.database import get_db_from_context

        # Mock DB dependency — return empty results for read-only aggregation
        async def _mock_get_db():
            mock_session = AsyncMock()
            # First execute: set_config
            # Second execute: COUNT(*)
            count_result = MagicMock()
            count_result.scalar_one_or_none.return_value = 0
            # Third execute: overview query
            overview_result = MagicMock()
            overview_result.fetchall.return_value = []
            mock_session.execute.side_effect = [
                None,  # set_config
                count_result,
                overview_result,
            ]
            yield mock_session

        app.dependency_overrides[get_db_from_context] = _mock_get_db
        app.include_router(admin_console_router, prefix="/v1/admin")

        return app

    @pytest.fixture
    def admin_console_client(self, admin_console_app):
        """TestClient for the admin console app."""
        from fastapi.testclient import TestClient
        return TestClient(admin_console_app)

    def test_tenant_overview_emits_cross_tenant_access_audit(
        self, admin_console_client
    ):
        """Verify GET /v1/admin/tenant-overview emits CROSS_TENANT_ACCESS."""
        with patch(
            "shared.identity.dependencies.emit_audit_event", new_callable=AsyncMock
        ) as mock_emit:
            response = admin_console_client.get(
                "/v1/admin/tenant-overview",
                headers={"X-Privileged-Reason": "Platform audit review"},
            )
            assert response.status_code == 200, (
                f"Expected 200, got {response.status_code}: {response.text}"
            )

            # Verify CROSS_TENANT_ACCESS audit was emitted
            cross_tenant_calls = [
                call
                for call in mock_emit.call_args_list
                if call.kwargs.get("action") == AuditAction.CROSS_TENANT_ACCESS
            ]
            assert len(cross_tenant_calls) >= 1, (
                "Expected at least one CROSS_TENANT_ACCESS audit event"
            )

            call_kwargs = cross_tenant_calls[0].kwargs
            assert call_kwargs["actor_type"] == "super_admin"
            assert call_kwargs["resource_type"] == "privileged_session"
            assert call_kwargs["outcome"] == AuditOutcome.SUCCESS
            assert "details" in call_kwargs
            assert call_kwargs["details"]["reason"] == "Platform audit review"

    def test_tenant_overview_requires_privileged_reason_header(
        self, admin_console_app, super_admin_context
    ):
        """Verify the endpoint rejects requests without X-Privileged-Reason."""
        from fastapi.testclient import TestClient

        # Use a fresh app without the injected context so we can test the
        # dependency in isolation via a simple route.
        from fastapi import FastAPI
        from starlette.middleware.base import BaseHTTPMiddleware

        class _InjectContextMiddleware(BaseHTTPMiddleware):
            def __init__(self, app, context=None):
                super().__init__(app)
                self.context = context

            async def dispatch(self, request, call_next):
                request.state.governance_context = self.context
                return await call_next(request)

        app = FastAPI()
        app.add_middleware(_InjectContextMiddleware, context=super_admin_context)

        from layer4_agents.tenants.api.routes.admin_console import (
            router as admin_console_router,
        )
        from layer4_agents.database import get_db_from_context

        async def _mock_get_db():
            mock_session = AsyncMock()
            yield mock_session

        app.dependency_overrides[get_db_from_context] = _mock_get_db
        app.include_router(admin_console_router, prefix="/v1/admin")

        client = TestClient(app)
        response = client.get("/v1/admin/tenant-overview")
        assert response.status_code == 400
        assert "X-Privileged-Reason" in response.text
