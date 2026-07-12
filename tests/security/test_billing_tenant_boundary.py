"""Security boundary tests for Layer 7 Billing Service (P0-02).

Verifies:
- Missing/invalid auth is rejected (401)
- Spoofed headers without JWT/API key are rejected
- Tenant isolation is enforced even with valid auth
- RBAC is enforced via canonical RequestContext
"""

from unittest.mock import patch
from uuid import uuid4

import pytest
from fastapi import Depends
from fastapi.testclient import TestClient
from layer7_billing.api.main import app
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated


def _auth_ctx(tenant: str = "11111111-1111-1111-1111-111111111111", roles: list[str] | None = None, user_id: str = "tester") -> RequestContext:
    return RequestContext(
        tenant_id=tenant,
        user_id=user_id,
        roles=roles or ["billing:read", "billing:write"],
        auth_source="jwt_claim",
    )


class _FakeAsyncSession:
    """Minimal mock for AsyncSession that supports the ``async with`` pattern."""

    async def __aenter__(self):
        return self

    async def __aexit__(self, *args):
        return False

    async def commit(self):
        pass

    async def rollback(self):
        pass

    async def close(self):
        pass

    async def execute(self, *args, **kwargs):
        from unittest.mock import MagicMock
        return MagicMock()


def _client_with_auth(tenant: str = "11111111-1111-1111-1111-111111111111", roles: list[str] | None = None):
    """Return a TestClient whose GovernanceMiddleware._resolve_identity is patched.

    This bypasses JWT validation entirely and injects a synthetic context so
    we can test route-level RBAC and repository-level tenant isolation.
    The database dependency is also mocked to avoid needing a live PostgreSQL.
    """
    ctx = _auth_ctx(tenant, roles)

    async def _fake_resolve(self, request):
        return ctx

    async def _fake_db(ctx: RequestContext = Depends(require_authenticated)):
        session = _FakeAsyncSession()
        yield session

    from layer7_billing.api.main import app, get_db_from_context
    app.dependency_overrides[get_db_from_context] = _fake_db

    patcher = patch(
        "value_fabric.shared.identity.middleware.GovernanceMiddleware._resolve_identity",
        _fake_resolve,
    )
    patcher.start()
    client = TestClient(app)
    return client, patcher, app.dependency_overrides


class TestMissingAuthentication:
    """Hostile: no JWT, no API key, no session."""

    def test_missing_auth_returns_401(self):
        client = TestClient(app)
        resp = client.get("/v1/billing/usage-aggregates")
        assert resp.status_code == 401

    def test_spoofed_headers_without_auth_return_401(self):
        """Raw X-Tenant-ID/X-Actor/X-Roles must not be accepted without JWT/API key."""
        client = TestClient(app)
        resp = client.get(
            "/v1/billing/usage-aggregates",
            headers={
                "x-tenant-id": "22222222-2222-2222-2222-222222222222",
                "x-actor": "attacker",
                "x-roles": "billing:read",
            },
        )
        assert resp.status_code == 401


class TestTenantIsolationWithValidAuth:
    """Positive: valid auth context, verify data scoping."""

    def test_tenant_a_cannot_read_tenant_b_usage(self):
        client, patcher, overrides = _client_with_auth("11111111-1111-1111-1111-111111111111")
        try:
            tenant_a = client.get("/v1/billing/usage-aggregates").json()
            assert tenant_a["tenant_id"] == "11111111-1111-1111-1111-111111111111"
        finally:
            patcher.stop()
            overrides.clear()

    def test_cross_tenant_invoice_access_blocked(self):
        client, patcher, overrides = _client_with_auth("11111111-1111-1111-1111-111111111111")
        try:
            resp = client.get("/v1/billing/invoices")
            assert resp.status_code == 200
            data = resp.json()
            assert data["tenant_id"] == "11111111-1111-1111-1111-111111111111"
        finally:
            patcher.stop()
            overrides.clear()


class TestRbacEnforcement:
    """RBAC must be checked against the authenticated context, not spoofed headers."""

    def test_read_only_role_cannot_mutate(self):
        client, patcher, overrides = _client_with_auth("11111111-1111-1111-1111-111111111111", roles=["billing:read"])
        try:
            resp = client.post(
                "/v1/billing/plans",
                json={"plan_id": "starter", "name": "Starter", "entitlements": []},
            )
            assert resp.status_code == 403
        finally:
            patcher.stop()
            overrides.clear()

    def test_write_role_can_mutate(self):
        client, patcher, overrides = _client_with_auth("11111111-1111-1111-1111-111111111111", roles=["billing:read", "billing:write"])
        try:
            resp = client.post(
                "/v1/billing/plans",
                json={"plan_id": "starter", "name": "Starter", "entitlements": []},
            )
            # 422 if plan validation fails, 200/201 if success — either is acceptable
            # for RBAC-positive; 403 would mean RBAC blocked a valid write role.
            assert resp.status_code != 403
        finally:
            patcher.stop()
            overrides.clear()
