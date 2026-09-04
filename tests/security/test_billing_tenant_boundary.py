"""Security boundary tests for the canonical L4 Billing runtime (P0-02).

Layer 7 (``layer7-billing``) has been removed; ``layer4-agents`` is the single
canonical billing implementation. These tests exercise the L4 billing router
mounted at ``/v1/billing`` and verify:

- Missing/invalid auth is rejected (401)
- Spoofed headers without JWT/API key are rejected
- Tenant isolation is enforced even with valid auth
- Auth-context enforcement (auth_source validity, tenant-context requirement)
  is applied through the canonical RequestContext / GovernanceMiddleware
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.middleware import GovernanceMiddleware

from layer4_agents.api.routes import billing as billing_route


def _auth_ctx(
    tenant: str | None = "11111111-1111-1111-1111-111111111111",
    roles: list[str] | None = None,
    user_id: str = "tester",
    auth_source: str = "jwt_claim",
) -> RequestContext:
    return RequestContext(
        tenant_id=tenant,
        user_id=user_id,
        roles=roles or ["billing:read", "billing:write"],
        auth_source=auth_source,
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


def _make_app() -> FastAPI:
    """Build a minimal FastAPI app that mounts only the canonical L4 billing router.

    The GovernanceMiddleware runs real identity resolution (and the
    ``require_authenticated`` dependency reads the resolved context from
    ``request.state.governance_context``), so the 401/403 failures are produced
    by the same machinery used in production.
    """
    app = FastAPI()
    register_exception_handlers(app)
    app.add_middleware(GovernanceMiddleware)
    app.include_router(billing_route.router, prefix="/v1")
    return app


@pytest.fixture
def app() -> FastAPI:
    return _make_app()


def _client_with_auth(ctx: RequestContext):
    """Return a TestClient whose GovernanceMiddleware is seeded with ``ctx``.

    This bypasses JWT validation entirely and injects a synthetic context so
    we can test route-level tenant scoping. The database dependency is mocked
    to avoid needing a live PostgreSQL, and the billing services are patched
    by the individual tests.
    """
    app = _make_app()

    async def _fake_resolve(self, request):
        return ctx

    async def _fake_db():
        session = _FakeAsyncSession()
        yield session

    app.dependency_overrides[billing_route.get_route_db] = _fake_db

    patcher = patch(
        "value_fabric.shared.identity.middleware.GovernanceMiddleware._resolve_identity",
        _fake_resolve,
    )
    patcher.start()
    client = TestClient(app)
    return client, patcher, app.dependency_overrides


def _usage_service_capture():
    """Return a UsageService stub that records every tenant it is constructed for."""
    captured: list[str | None] = []

    class _CapturingUsageService:
        def __init__(self, db, *, tenant_id):
            self.db = db
            self.tenant_id = tenant_id
            captured.append(tenant_id)

        async def get_usage_summary(self, **kwargs):
            return {"total_quantity": 12, "unit": "seats"}

        async def sync_to_stripe(self, **kwargs):
            return {"synced": 1, "failed": 0}

    return _CapturingUsageService, captured


class TestMissingAuthentication:
    """Hostile: no JWT, no API key, no session."""

    def test_missing_auth_returns_401(self, app):
        resp = TestClient(app).get("/v1/billing/invoices")
        assert resp.status_code == 401

    def test_spoofed_headers_without_auth_return_401(self, app):
        """Raw X-Tenant-ID/X-Actor/X-Roles must not be accepted without JWT/API key."""
        resp = TestClient(app).get(
            "/v1/billing/invoices",
            headers={
                "x-tenant-id": "22222222-2222-2222-2222-222222222222",
                "x-actor": "attacker",
                "x-roles": "billing:read",
            },
        )
        assert resp.status_code == 401


class TestTenantIsolationWithValidAuth:
    """Positive: valid auth context, verify data scoping to the authenticated tenant."""

    def test_authenticated_usage_queries_scoped_to_tenant(self):
        client, patcher, overrides = _client_with_auth(_auth_ctx())
        capturing, captured = _usage_service_capture()
        patcher_usage = patch.object(billing_route, "UsageService", capturing)
        patcher_usage.start()
        try:
            resp = client.get(
                "/v1/billing/usage/cus_x/summary",
                params={"metric_name": "seats"},
            )
            assert resp.status_code == 200
            assert resp.json()["customer_id"] == "cus_x"
            assert captured == ["11111111-1111-1111-1111-111111111111"]
        finally:
            patcher.stop()
            patcher_usage.stop()
            overrides.clear()

    def test_authenticated_invoice_list_scoped_to_tenant(self):
        client, patcher, overrides = _client_with_auth(_auth_ctx())
        captured: list[str | None] = []

        class _CapturingInvoiceService:
            def __init__(self, db, *, tenant_id):
                self.db = db
                self.tenant_id = tenant_id
                captured.append(tenant_id)

            async def list_invoices(self, **kwargs):
                return []

        patcher_svc = patch.object(billing_route, "InvoiceService", _CapturingInvoiceService)
        patcher_svc.start()
        try:
            resp = client.get("/v1/billing/invoices")
            assert resp.status_code == 200
            data = resp.json()
            assert data["invoices"] == []
            assert "pagination" in data
            assert captured == ["11111111-1111-1111-1111-111111111111"]
        finally:
            patcher.stop()
            patcher_svc.stop()
            overrides.clear()

    def test_cross_tenant_invoice_access_blocked(self):
        """Hostile: an authenticated tenant must not read another tenant's invoice.

        InvoiceService is constructed with the authenticated tenant only, and a
        tenant-scoped lookup returns no invoice for a foreign-owned invoice id,
        so the route responds 404 and never leaks tenant B data.
        """
        tenant_a = "11111111-1111-1111-1111-111111111111"
        tenant_b = "22222222-2222-4222-8222-222222222222"
        client, patcher, overrides = _client_with_auth(_auth_ctx(tenant_a))
        captured: list[str | None] = []
        # Mirror of the tenant_scope column: invoice ids map to their owning
        # tenant, so lookups outside the caller's tenant find nothing.
        invoice_owners = {"in_tenant_b": tenant_b}

        class _TenantScopedInvoiceService:
            def __init__(self, db, *, tenant_id):
                self.db = db
                self.tenant_id = tenant_id
                captured.append(tenant_id)

            async def get_invoice(self, invoice_id, **kwargs):
                if invoice_owners.get(invoice_id) == self.tenant_id:
                    return object()
                return None

        patcher_svc = patch.object(
            billing_route, "InvoiceService", _TenantScopedInvoiceService
        )
        patcher_svc.start()
        try:
            resp = client.get("/v1/billing/invoices/in_tenant_b")
            assert resp.status_code == 404
            assert captured == [tenant_a]
            assert tenant_b not in captured
        finally:
            patcher.stop()
            patcher_svc.stop()
            overrides.clear()

    def test_different_authenticated_tenants_are_kept_distinct(self):
        capturing, captured = _usage_service_capture()
        patcher_usage = patch.object(billing_route, "UsageService", capturing)
        patcher_usage.start()
        try:
            client_a, patcher_a, overrides_a = _client_with_auth(
                _auth_ctx("11111111-1111-1111-1111-111111111111")
            )
            try:
                client_a.get(
                    "/v1/billing/usage/cus_x/summary",
                    params={"metric_name": "seats"},
                )
            finally:
                patcher_a.stop()
                overrides_a.clear()

            client_b, patcher_b, overrides_b = _client_with_auth(
                _auth_ctx("22222222-2222-4222-8222-222222222222")
            )
            try:
                client_b.get(
                    "/v1/billing/usage/cus_x/summary",
                    params={"metric_name": "seats"},
                )
            finally:
                patcher_b.stop()
                overrides_b.clear()

            # Each request was scoped to its own authenticated tenant; tenant B
            # never observed data as (or for) tenant A.
            assert captured == [
                "11111111-1111-1111-1111-111111111111",
                "22222222-2222-4222-8222-222222222222",
            ]
        finally:
            patcher_usage.stop()


class TestAuthContextEnforcement:
    """Hostile/edge auth contexts must be rejected by the canonical middleware."""

    def test_invalid_auth_source_rejected(self):
        client, patcher, overrides = _client_with_auth(
            _auth_ctx(auth_source="unknown")
        )
        try:
            resp = client.get("/v1/billing/invoices")
            assert resp.status_code == 401
        finally:
            patcher.stop()
            overrides.clear()

    def test_missing_tenant_context_rejected(self):
        client, patcher, overrides = _client_with_auth(_auth_ctx(tenant=None))
        try:
            resp = client.get("/v1/billing/invoices")
            assert resp.status_code == 403
        finally:
            patcher.stop()
            overrides.clear()

    def test_valid_write_context_can_mutate(self):
        """A valid authenticated context may write; scoping is to its tenant."""
        client, patcher, overrides = _client_with_auth(_auth_ctx())
        capturing, captured = _usage_service_capture()
        patcher_usage = patch.object(billing_route, "UsageService", capturing)
        patcher_usage.start()
        try:
            resp = client.post("/v1/billing/usage/cus_x/sync")
            assert resp.status_code == 200
            assert resp.json()["synced"] == 1
            assert captured == ["11111111-1111-1111-1111-111111111111"]
        finally:
            patcher.stop()
            patcher_usage.stop()
            overrides.clear()
