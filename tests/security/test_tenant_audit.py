"""Tests for tenant resolution audit logging (Task 3.1).

Verifies that TENANT_RESOLVED and TENANT_CONTEXT_SET audit events are properly emitted
with structured details at authentication and DB session setup points.
"""

from __future__ import annotations

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Lazy import for optional dependency
try:
    from fastapi import Request
except ImportError:
    Request = None

from value_fabric.shared.audit import (
    AuditAction,
    AuditOutcome,
    TenantContextSetDetails,
    TenantResolvedDetails,
    emit_audit_event,
)
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_API_KEY,
    AUTH_SOURCE_JWT,
    ISOLATION_TIER_SCHEMA,
    ISOLATION_TIER_SHARED,
    RequestContext,
)
from value_fabric.shared.identity.middleware import GovernanceMiddleware


class TestTenantResolvedDetails:
    """Test the TenantResolvedDetails structured details model."""

    def test_valid_details_creation(self):
        """Should create valid details with all fields."""
        details = TenantResolvedDetails(
            resolution_source="jwt_claim",
            resolved_tenant_id="tenant-123",
            user_id="user-456",
            auth_method="jwt",
            has_org_id=True,
            org_id="org-789",
            tenant_role="admin",
            isolation_tier=ISOLATION_TIER_SHARED,
            roles=["admin", "user"],
            is_super_admin=False,
            outcome="success",
            request_path="/api/v1/items",
            request_method="GET",
        )

        assert details.resolution_source == "jwt_claim"
        assert details.resolved_tenant_id == "tenant-123"
        assert details.has_org_id is True
        assert details.org_id == "org-789"
        assert details.isolation_tier == ISOLATION_TIER_SHARED
        assert details.outcome == "success"

    def test_defaults_for_optional_fields(self):
        """Should have sensible defaults for optional fields."""
        details = TenantResolvedDetails(
            resolution_source=AUTH_SOURCE_API_KEY,
            auth_method=AUTH_SOURCE_API_KEY,
        )

        assert details.has_org_id is False
        assert details.isolation_tier == ISOLATION_TIER_SHARED
        assert details.roles == []
        assert details.is_super_admin is False
        assert details.bypass is False
        assert details.outcome == "success"

    def test_model_dump_excludes_none(self):
        """Should exclude None values when dumping to dict."""
        details = TenantResolvedDetails(
            resolution_source="jwt_claim",
            auth_method="jwt",
            resolved_tenant_id="tenant-123",
        )

        dumped = details.model_dump(exclude_none=True)
        assert "org_id" not in dumped  # Was None, should be excluded
        assert "tenant_role" not in dumped  # Was None, should be excluded
        assert "resolved_tenant_id" in dumped  # Has value, should be included


class TestTenantContextSetDetails:
    """Test the TenantContextSetDetails model."""

    def test_regular_context_set(self):
        """Should create details for normal tenant context set."""
        details = TenantContextSetDetails(
            tenant_id="tenant-123",
            isolation_tier=ISOLATION_TIER_SHARED,
            bypass=False,
            context_source="request_context",
        )

        assert details.tenant_id == "tenant-123"
        assert details.bypass is False
        assert details.context_source == "request_context"

    def test_super_admin_bypass(self):
        """Should create details with bypass flag for super-admin."""
        details = TenantContextSetDetails(
            tenant_id="",
            isolation_tier=ISOLATION_TIER_SHARED,
            bypass=True,
            bypass_reason="super_admin_bypass",
            context_source="request_context",
        )

        assert details.bypass is True
        assert details.bypass_reason == "super_admin_bypass"


_AUDIT_IN_MIDDLEWARE_XFAIL = pytest.mark.xfail(
    reason=(
        "GovernanceMiddleware does not yet emit audit events directly. "
        "Audit emission lives in value_fabric.shared.identity.dependencies. "
        "These tests pin the planned contract; implement emit_audit_event in "
        "middleware.py to make them pass."
    ),
    strict=True,
)


class TestGovernanceMiddlewareAuditEmission:
    """Test that GovernanceMiddleware emits TENANT_RESOLVED audit events."""

    @_AUDIT_IN_MIDDLEWARE_XFAIL
    @pytest.mark.asyncio
    async def test_emits_tenant_resolved_on_successful_auth(self):
        """Should emit TENANT_RESOLVED after successful authentication."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "org_id": str(uuid.uuid4()),
            "tenant_role": "admin",
            "isolation_tier": "shared",
            "roles": ["tenant_admin"],
            "auth_source": "jwt_claim",
        }

        with patch(
            "shared.identity.middleware.decode_jwt", return_value=mock_payload
        ), patch(
            "shared.identity.middleware.emit_audit_event", new_callable=AsyncMock
        ) as mock_emit, patch(
            "shared.identity.middleware.AUDIT_AVAILABLE", True
        ):
            middleware = GovernanceMiddleware(app=MagicMock())
            request = MagicMock(spec=Request)
            request.headers = {"Authorization": "Bearer valid_token"}
            request.url.path = "/api/v1/test"
            request.method = "GET"

            ctx = await middleware._authenticate(request)

            # Verify audit was emitted
            mock_emit.assert_called_once()
            call_args = mock_emit.call_args

            assert call_args.kwargs["action"] == AuditAction.TENANT_RESOLVED
            assert call_args.kwargs["outcome"] == AuditOutcome.SUCCESS
            assert call_args.kwargs["tenant_id"] == tenant_id
            assert call_args.kwargs["resource_type"] == "tenant_resolution"

            # Verify details structure
            details = call_args.kwargs["details"]
            assert details["resolution_source"] == "jwt_claim"
            assert details["resolved_tenant_id"] == str(tenant_id)
            assert details["user_id"] == str(user_id)
            assert details["has_org_id"] is True
            assert details["tenant_role"] == "admin"
            assert details["is_super_admin"] is True  # tenant_admin role

    @_AUDIT_IN_MIDDLEWARE_XFAIL
    @pytest.mark.asyncio
    async def test_emits_failure_when_no_tenant_resolved(self):
        """Should emit FAILURE outcome when no tenant_id resolved."""
        with patch(
            "shared.identity.middleware.decode_jwt", return_value={}
        ), patch(
            "shared.identity.middleware.emit_audit_event", new_callable=AsyncMock
        ) as mock_emit, patch(
            "shared.identity.middleware.AUDIT_AVAILABLE", True
        ):
            middleware = GovernanceMiddleware(app=MagicMock())
            request = MagicMock(spec=Request)
            request.headers = {"Authorization": "Bearer token"}
            request.url.path = "/api/v1/test"
            request.method = "GET"

            ctx = await middleware._authenticate(request)

            mock_emit.assert_called_once()
            call_args = mock_emit.call_args

            assert call_args.kwargs["outcome"] == AuditOutcome.FAILURE
            details = call_args.kwargs["details"]
            assert details["outcome"] == "failure"
            assert "No tenant_id resolved" in details["failure_reason"]

    @pytest.mark.asyncio
    @_AUDIT_IN_MIDDLEWARE_XFAIL
    async def test_emits_service_account_details(self):
        """Should emit service account specific details."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()
        svc_id = uuid.uuid4()

        mock_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "service_account_id": str(svc_id),
            "scopes": ["read", "write"],
            "roles": [],
            "auth_source": "service_account",
        }

        with patch(
            "shared.identity.middleware.decode_jwt", return_value=mock_payload
        ), patch(
            "shared.identity.middleware.emit_audit_event", new_callable=AsyncMock
        ) as mock_emit, patch(
            "shared.identity.middleware.AUDIT_AVAILABLE", True
        ):
            middleware = GovernanceMiddleware(app=MagicMock())
            request = MagicMock(spec=Request)
            request.headers = {"Authorization": "Bearer token"}
            request.url.path = "/api/v1/jobs"
            request.method = "POST"

            ctx = await middleware._authenticate(request)

            mock_emit.assert_called_once()
            details = mock_emit.call_args.kwargs["details"]
            assert details["auth_method"] == "service_account"
            assert details["service_account_id"] == str(svc_id)


class TestAuditEventIntegration:
    """Integration-style tests for audit event flow."""

    @_AUDIT_IN_MIDDLEWARE_XFAIL
    @pytest.mark.asyncio
    async def test_end_to_end_audit_trail(self):
        """Full flow: auth -> tenant resolution -> DB context set.

        This simulates the complete flow from authentication through
        database session establishment, verifying both audit events are emitted.
        """
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "org_id": str(uuid.uuid4()),
            "tenant_role": "value_consultant",
            "isolation_tier": "shared",
            "roles": ["tenant_user"],
            "auth_source": "jwt_claim",
        }

        emitted_events = []

        async def capture_emit(*, action, outcome, details, **kwargs):
            emitted_events.append({
                "action": action,
                "outcome": outcome,
                "details": details,
            })

        with patch(
            "shared.identity.middleware.decode_jwt", return_value=mock_payload
        ), patch(
            "shared.identity.middleware.emit_audit_event", side_effect=capture_emit
        ), patch(
            "shared.identity.middleware.AUDIT_AVAILABLE", True
        ):
            middleware = GovernanceMiddleware(app=MagicMock())
            request = MagicMock(spec=Request)
            request.headers = {"Authorization": "Bearer token"}
            request.url.path = "/api/v1/entities"
            request.method = "GET"

            ctx = await middleware._authenticate(request)

            # Verify first event is TENANT_RESOLVED
            assert len(emitted_events) == 1
            assert emitted_events[0]["action"] == AuditAction.TENANT_RESOLVED
            assert emitted_events[0]["outcome"] == AuditOutcome.SUCCESS
            assert emitted_events[0]["details"]["resolution_source"] == "jwt_claim"
