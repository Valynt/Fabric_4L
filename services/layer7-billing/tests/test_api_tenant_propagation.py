"""API tenant propagation tests for Layer 7 Billing Service.

Validates that every route extracts tenant_id from the authenticated
RequestContext and propagates it strictly down to the repository layer.

Per the tenant-isolation checklist:
  - Repository/service methods receive tenant_id from trusted request context
  - Missing tenant context fails closed (401)
"""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from layer7_billing.api.main import app

from .conftest import auth_headers


@pytest.fixture
def mock_repo(monkeypatch):
    """Mock repository for asserting call arguments."""
    mock = AsyncMock()
    mock.upsert_plan = AsyncMock(return_value={"plan_id": "p1", "tenant_id": "t1"})
    mock.get_plan_entitlements = AsyncMock(return_value=["feature1"])
    mock.insert_usage_event = AsyncMock(return_value=True)
    mock.increment_aggregate = AsyncMock(return_value=None)
    mock.get_usage_aggregates = AsyncMock(return_value={"api_calls": 100.0})
    mock.list_invoices = AsyncMock(return_value=[])
    mock.get_payment_state = AsyncMock(return_value={"state_key": "current", "state": "paid"})
    monkeypatch.setattr("layer7_billing.api.main.repository", mock)
    return mock


@pytest.mark.asyncio
async def test_upsert_plan_propagates_tenant(mock_repo: AsyncMock, isolated_client: AsyncClient):
    """POST /v1/billing/plans must pass context tenant_id to repository."""
    hostile_tenant = "tenant-hostile-xyz"
    response = await isolated_client.post(
        "/v1/billing/plans",
        json={"plan_id": "plan-abc", "name": "Test Plan", "entitlements": ["f1"]},
        headers=auth_headers(tenant_id=hostile_tenant),
    )
    assert response.status_code == 200
    mock_repo.upsert_plan.assert_called_once()
    args, _ = mock_repo.upsert_plan.call_args
    assert args[1] == hostile_tenant


@pytest.mark.asyncio
async def test_entitlement_decision_propagates_tenant(mock_repo: AsyncMock, isolated_client: AsyncClient):
    """GET /v1/billing/entitlements/{plan_id}/decision must pass context tenant_id."""
    hostile_tenant = "tenant-hostile-abc"
    response = await isolated_client.get(
        "/v1/billing/entitlements/plan-abc/decision?feature=feature1",
        headers=auth_headers(tenant_id=hostile_tenant),
    )
    assert response.status_code == 200
    mock_repo.get_plan_entitlements.assert_called_once()
    args, _ = mock_repo.get_plan_entitlements.call_args
    assert args[1] == hostile_tenant


@pytest.mark.asyncio
async def test_ingest_usage_propagates_tenant(mock_repo: AsyncMock, isolated_client: AsyncClient):
    """POST /v1/billing/usage-events must pass context tenant_id to repository."""
    hostile_tenant = "tenant-hostile-usage"
    response = await isolated_client.post(
        "/v1/billing/usage-events",
        json={
            "event_id": "evt-1",
            "metric": "api_calls",
            "quantity": 100.0,
            "source": "test",
            "timestamp": "2026-05-27T00:00:00Z",
            "request_id": "req-1",
        },
        headers=auth_headers(tenant_id=hostile_tenant),
    )
    assert response.status_code == 200
    mock_repo.insert_usage_event.assert_called_once()
    args, _ = mock_repo.insert_usage_event.call_args
    assert args[1] == hostile_tenant
    mock_repo.increment_aggregate.assert_called_once()
    args, _ = mock_repo.increment_aggregate.call_args
    assert args[1] == hostile_tenant


@pytest.mark.asyncio
async def test_usage_aggregates_propagates_tenant(mock_repo: AsyncMock, isolated_client: AsyncClient):
    """GET /v1/billing/usage-aggregates must pass context tenant_id."""
    hostile_tenant = "tenant-hostile-aggr"
    response = await isolated_client.get(
        "/v1/billing/usage-aggregates",
        headers=auth_headers(tenant_id=hostile_tenant),
    )
    assert response.status_code == 200
    mock_repo.get_usage_aggregates.assert_called_once()
    args, _ = mock_repo.get_usage_aggregates.call_args
    assert args[1] == hostile_tenant


@pytest.mark.asyncio
async def test_list_invoices_propagates_tenant(mock_repo: AsyncMock, isolated_client: AsyncClient):
    """GET /v1/billing/invoices must pass context tenant_id."""
    hostile_tenant = "tenant-hostile-inv"
    response = await isolated_client.get(
        "/v1/billing/invoices",
        headers=auth_headers(tenant_id=hostile_tenant),
    )
    assert response.status_code == 200
    mock_repo.list_invoices.assert_called_once()
    args, _ = mock_repo.list_invoices.call_args
    assert args[1] == hostile_tenant


@pytest.mark.asyncio
async def test_payment_state_propagates_tenant(mock_repo: AsyncMock, isolated_client: AsyncClient):
    """GET /v1/billing/payment-state must pass context tenant_id."""
    hostile_tenant = "tenant-hostile-pay"
    response = await isolated_client.get(
        "/v1/billing/payment-state",
        headers=auth_headers(tenant_id=hostile_tenant),
    )
    assert response.status_code == 200
    mock_repo.get_payment_state.assert_called_once()
    args, _ = mock_repo.get_payment_state.call_args
    assert args[1] == hostile_tenant


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("method", "path", "json_payload"),
    [
        ("POST", "/v1/billing/plans", {"plan_id": "p1", "name": "P1", "entitlements": []}),
        ("GET", "/v1/billing/entitlements/p1/decision?feature=f1", None),
        (
            "POST",
            "/v1/billing/usage-events",
            {
                "event_id": "evt-1",
                "metric": "api_calls",
                "quantity": 1.0,
                "source": "test",
                "timestamp": "2026-05-27T00:00:00Z",
                "request_id": "req-1",
            },
        ),
        ("GET", "/v1/billing/usage-aggregates", None),
        ("GET", "/v1/billing/invoices", None),
        ("GET", "/v1/billing/payment-state", None),
    ],
)
async def test_endpoints_fail_closed_without_tenant_context(
    mock_repo: AsyncMock,
    isolated_client: AsyncClient,
    method: str,
    path: str,
    json_payload: dict | None,
):
    """Missing tenant context must fail closed before repository is reached."""
    response = await isolated_client.request(method, path, json=json_payload)

    assert response.status_code == 401
    mock_repo.upsert_plan.assert_not_called()
    mock_repo.get_plan_entitlements.assert_not_called()
    mock_repo.insert_usage_event.assert_not_called()
