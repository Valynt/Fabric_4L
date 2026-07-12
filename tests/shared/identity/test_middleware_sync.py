"""Tests for synchronous identity middleware contract behavior."""

from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi import HTTPException
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_API_KEY,
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
)
from value_fabric.shared.identity.middleware_sync import (
    GovernanceMiddlewareSync,
    SyncRequestContext,
    get_request_context_sync,
)


def _make_request(governance_context: RequestContext | None = None):
    state = SimpleNamespace()
    if governance_context is not None:
        state.governance_context = governance_context
    return SimpleNamespace(state=state)


class TestSyncRequestContext:
    def test_service_auth_context_has_none_user_id(self):
        tenant_id = UUID("12345678-1234-5678-1234-567812345678")
        ctx = SyncRequestContext(tenant_id=tenant_id, user_id=None, roles=["system"], auth_source=AUTH_SOURCE_SERVICE_ACCOUNT)
        assert ctx.user_id is None
        assert ctx.tenant_id == tenant_id
        assert ctx.auth_source == AUTH_SOURCE_SERVICE_ACCOUNT


class TestGovernanceMiddlewareSync:
    def test_service_auth_creates_valid_context(self, monkeypatch):
        monkeypatch.setenv("SERVICE_AUTH_SECRET", "test-secret")
        middleware = GovernanceMiddlewareSync(None)
        ctx = middleware._resolve_identity_sync(
            x_tenant_header="12345678-1234-5678-1234-567812345678",
            x_service_auth="test-secret",
        )
        assert ctx is not None
        assert ctx.user_id is None
        assert ctx.auth_source == AUTH_SOURCE_SERVICE_ACCOUNT
        assert "system" in ctx.roles

    def test_forged_x_organization_id_ignored_when_governance_context_present(self):
        """JWT claims take precedence over forged headers — forged X-Organization-ID is ignored."""
        tenant_id = str(uuid4())
        forged_org = str(uuid4())
        req = _make_request(
            RequestContext(
                tenant_id=tenant_id,
                user_id=str(uuid4()),
                roles=["tenant_admin"],
                permissions=frozenset(),
                source="jwt_claim",
                auth_source="jwt_claim",
                request_id="req-123",
            )
        )

        ctx = get_request_context_sync(req, x_organization_id=forged_org)
        # Authenticated context wins; forged header is silently ignored
        assert str(ctx.tenant_id) == tenant_id
        assert ctx.request_id == "req-123"

    def test_matching_x_organization_id_allowed_with_authenticated_context(self):
        tenant_id = str(uuid4())
        req = _make_request(
            RequestContext(tenant_id=tenant_id, roles=["tenant_admin"], source="jwt_claim", auth_source="jwt_claim", request_id="req-abc")
        )
        ctx = get_request_context_sync(req, x_organization_id=tenant_id)
        assert str(ctx.tenant_id) == tenant_id
        assert ctx.request_id == "req-abc"

    def test_api_key_context_carries_audit_fields(self):
        middleware = GovernanceMiddlewareSync(None, api_key_resolver=lambda _: {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "key_id": "key-123",
            "role": "tenant_admin",
            "request_id": "req-key-1",
        })
        ctx = middleware._resolve_identity_sync(api_key_header="vf_abc")
        assert ctx is not None
        assert ctx.auth_source == AUTH_SOURCE_API_KEY
        assert ctx.request_id == "req-key-1"
        assert ctx.user_id is not None
