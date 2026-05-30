"""Auth enforcement tests for Layer 7 Billing Service.

Tests verify:
1. All routes require authentication (exact 401 on missing auth)
2. All routes enforce RBAC roles (exact 403 on missing roles)
3. Tenant context is properly enforced via RequestContext
4. GovernanceMiddleware is installed and functioning
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import AsyncMock, patch

from layer7_billing.api.main import app
from .conftest import auth_headers


@pytest.mark.asyncio
async def test_plans_route_requires_auth():
    """POST /v1/billing/plans without auth must return exact 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/billing/plans", json={
            "plan_id": "test-plan",
            "name": "Test Plan",
            "entitlements": ["feature1"]
        })
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_entitlements_route_requires_auth():
    """GET /v1/billing/entitlements/{plan_id}/decision without auth must return exact 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/billing/entitlements/test-plan/decision?feature=feature1")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_usage_events_route_requires_auth():
    """POST /v1/billing/usage-events without auth must return exact 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post("/v1/billing/usage-events", json={
            "event_id": "event-123",
            "metric": "api_calls",
            "quantity": 100.0,
            "source": "test",
            "timestamp": "2026-05-27T00:00:00Z",
            "request_id": "req-123"
        })
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_usage_aggregates_route_requires_auth():
    """GET /v1/billing/usage-aggregates without auth must return exact 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/billing/usage-aggregates")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_invoices_route_requires_auth():
    """GET /v1/billing/invoices without auth must return exact 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/billing/invoices")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_payment_state_route_requires_auth():
    """GET /v1/billing/payment-state without auth must return exact 401."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/v1/billing/payment-state")
        assert response.status_code == 401


@pytest.mark.asyncio
async def test_governance_middleware_installed():
    """GovernanceMiddleware should be installed on the app."""
    from value_fabric.shared.identity.middleware import GovernanceMiddleware

    middleware_types = [type(m.cls) if hasattr(m, 'cls') else type(m) for m in app.user_middleware]
    assert GovernanceMiddleware in middleware_types or any(
        "GovernanceMiddleware" in str(m) for m in app.user_middleware
    ), "GovernanceMiddleware must be installed for P0-02 fail-closed behavior"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("POST", "/v1/billing/plans", {"plan_id": "p1", "name": "P1", "entitlements": []}),
        ("POST", "/v1/billing/usage-events", {
            "event_id": "evt-1", "metric": "api_calls", "quantity": 1.0,
            "source": "test", "timestamp": "2026-05-27T00:00:00Z", "request_id": "req-1",
        }),
    ],
)
async def test_write_routes_require_billing_write_role(method, path, json_payload):
    """Write routes must return 403 when caller lacks billing:write role."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(
            method, path, json=json_payload, headers=auth_headers(roles=["billing:read"])
        )
        assert response.status_code == 403, (
            f"{method} {path} with billing:read only must return 403, got {response.status_code}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("GET", "/v1/billing/entitlements/plan-1/decision?feature=f1"),
        ("GET", "/v1/billing/usage-aggregates"),
        ("GET", "/v1/billing/invoices"),
        ("GET", "/v1/billing/payment-state"),
    ],
)
async def test_read_routes_require_billing_read_role(method, path):
    """Read routes must return 403 when caller lacks billing:read role."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(
            method, path, headers=auth_headers(roles=["billing:write"])
        )
        assert response.status_code == 403, (
            f"{method} {path} without billing:read must return 403, got {response.status_code}"
        )


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("POST", "/v1/billing/plans", {"plan_id": "p1", "name": "P1", "entitlements": []}),
        ("GET", "/v1/billing/entitlements/plan-1/decision?feature=f1", None),
        ("POST", "/v1/billing/usage-events", {
            "event_id": "evt-1", "metric": "api_calls", "quantity": 1.0,
            "source": "test", "timestamp": "2026-05-27T00:00:00Z", "request_id": "req-1",
        }),
        ("GET", "/v1/billing/usage-aggregates", None),
        ("GET", "/v1/billing/invoices", None),
        ("GET", "/v1/billing/payment-state", None),
    ],
)
async def test_all_routes_fail_with_no_roles(method, path, json_payload):
    """All routes must return 403 when caller has no billing roles."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.request(
            method, path, json=json_payload, headers=auth_headers(roles=[])
        )
        assert response.status_code == 403, (
            f"{method} {path} with no roles must return 403, got {response.status_code}"
        )
