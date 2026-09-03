"""Cross-tenant hostile tests for Layer 7 Billing Service.

Validates that a tenant cannot read or mutate another tenant's billing data.
Per the tenant-isolation checklist:
  - Tenant A cannot read Tenant B data
  - Tenant A cannot mutate Tenant B data
  - Missing tenant context fails closed
"""

from __future__ import annotations

from unittest.mock import AsyncMock

import pytest
from httpx import AsyncClient

from layer7_billing.api.main import app

from .conftest import auth_headers


@pytest.fixture
def mock_repo_hostile(monkeypatch):
    """Mock repository that simulates tenant-scoped data."""
    mock = AsyncMock()

    async def simulated_upsert_plan(session, tenant_id, plan_id, name, entitlements):
        return {"plan_id": plan_id, "tenant_id": tenant_id}

    async def simulated_get_plan_entitlements(session, tenant_id, plan_id):
        if tenant_id == "victim-tenant" and plan_id == "victim-plan":
            return ["premium_feature"]
        return []

    async def simulated_insert_usage_event(session, tenant_id, event):
        return True

    async def simulated_increment_aggregate(session, tenant_id, metric, quantity):
        return None

    async def simulated_get_usage_aggregates(session, tenant_id):
        if tenant_id == "victim-tenant":
            return {"api_calls": 9999.0}
        return {}

    async def simulated_list_invoices(session, tenant_id):
        if tenant_id == "victim-tenant":
            return [{"invoice_id": "inv-1", "payload": {"amount": 1000}, "created_at": "2026-05-01T00:00:00Z"}]
        return []

    async def simulated_get_payment_state(session, tenant_id, state_key="current"):
        if tenant_id == "victim-tenant":
            return {"tenant_id": tenant_id, "state_key": state_key, "state": "paid", "payload": {"balance": 5000}}
        return {"tenant_id": tenant_id, "state_key": state_key, "state": "pending", "payload": {}}

    mock.upsert_plan = AsyncMock(side_effect=simulated_upsert_plan)
    mock.get_plan_entitlements = AsyncMock(side_effect=simulated_get_plan_entitlements)
    mock.insert_usage_event = AsyncMock(side_effect=simulated_insert_usage_event)
    mock.increment_aggregate = AsyncMock(side_effect=simulated_increment_aggregate)
    mock.get_usage_aggregates = AsyncMock(side_effect=simulated_get_usage_aggregates)
    mock.list_invoices = AsyncMock(side_effect=simulated_list_invoices)
    mock.get_payment_state = AsyncMock(side_effect=simulated_get_payment_state)

    monkeypatch.setattr("layer7_billing.api.main.repository", mock)
    return mock


@pytest.mark.asyncio
async def test_hostile_cannot_read_victim_plan_entitlements(
    mock_repo_hostile: AsyncMock, isolated_client: AsyncClient
):
    """Hostile tenant must not see victim's plan entitlements."""
    response = await isolated_client.get(
        "/v1/billing/entitlements/victim-plan/decision?feature=premium_feature",
        headers=auth_headers(tenant_id="tenant-hostile"),
    )
    # Hostile gets empty entitlements → feature not allowed, but 200 is fine
    # because the repository correctly filters by tenant
    assert response.status_code == 200
    data = response.json()
    assert data["allowed"] is False
    mock_repo_hostile.get_plan_entitlements.assert_called_once()
    args, _ = mock_repo_hostile.get_plan_entitlements.call_args
    assert args[1] == "tenant-hostile"


@pytest.mark.asyncio
async def test_hostile_cannot_read_victim_usage_aggregates(
    mock_repo_hostile: AsyncMock, isolated_client: AsyncClient
):
    """Hostile tenant must not see victim's usage aggregates."""
    response = await isolated_client.get(
        "/v1/billing/usage-aggregates",
        headers=auth_headers(tenant_id="tenant-hostile"),
    )
    assert response.status_code == 200
    data = response.json()
    # Hostile should see empty aggregates, not victim's 9999.0
    assert data["metrics"] == {}
    mock_repo_hostile.get_usage_aggregates.assert_called_once()
    args, _ = mock_repo_hostile.get_usage_aggregates.call_args
    assert args[1] == "tenant-hostile"


@pytest.mark.asyncio
async def test_hostile_cannot_read_victim_invoices(
    mock_repo_hostile: AsyncMock, isolated_client: AsyncClient
):
    """Hostile tenant must not list victim's invoices."""
    response = await isolated_client.get(
        "/v1/billing/invoices",
        headers=auth_headers(tenant_id="tenant-hostile"),
    )
    assert response.status_code == 200
    data = response.json()
    assert data["invoices"] == []
    mock_repo_hostile.list_invoices.assert_called_once()
    args, _ = mock_repo_hostile.list_invoices.call_args
    assert args[1] == "tenant-hostile"


@pytest.mark.asyncio
async def test_hostile_cannot_read_victim_payment_state(
    mock_repo_hostile: AsyncMock, isolated_client: AsyncClient
):
    """Hostile tenant must not see victim's payment state."""
    response = await isolated_client.get(
        "/v1/billing/payment-state",
        headers=auth_headers(tenant_id="tenant-hostile"),
    )
    assert response.status_code == 200
    data = response.json()
    # Should see pending state, not victim's paid state
    assert data["state"] == "pending"
    assert data["payload"] == {}
    mock_repo_hostile.get_payment_state.assert_called_once()
    args, _ = mock_repo_hostile.get_payment_state.call_args
    assert args[1] == "tenant-hostile"


@pytest.mark.asyncio
async def test_hostile_cannot_mutate_victim_plan(
    mock_repo_hostile: AsyncMock, isolated_client: AsyncClient
):
    """Hostile tenant upserting a plan must only affect their own tenant."""
    response = await isolated_client.post(
        "/v1/billing/plans",
        json={"plan_id": "victim-plan", "name": "Hacked Plan", "entitlements": ["stolen"]},
        headers=auth_headers(tenant_id="tenant-hostile"),
    )
    assert response.status_code == 200
    mock_repo_hostile.upsert_plan.assert_called_once()
    args, _ = mock_repo_hostile.upsert_plan.call_args
    assert args[1] == "tenant-hostile"
    # Composite key (plan_id, tenant_id) ensures victim's plan is safe


@pytest.mark.asyncio
async def test_hostile_cannot_inject_victim_usage_event(
    mock_repo_hostile: AsyncMock, isolated_client: AsyncClient
):
    """Hostile tenant injecting usage events must only affect their own tenant."""
    response = await isolated_client.post(
        "/v1/billing/usage-events",
        json={
            "event_id": "evt-1",
            "metric": "api_calls",
            "quantity": 1000.0,
            "source": "malicious",
            "timestamp": "2026-05-27T00:00:00Z",
            "request_id": "req-1",
        },
        headers=auth_headers(tenant_id="tenant-hostile"),
    )
    assert response.status_code == 200
    mock_repo_hostile.insert_usage_event.assert_called_once()
    args, _ = mock_repo_hostile.insert_usage_event.call_args
    assert args[1] == "tenant-hostile"
    mock_repo_hostile.increment_aggregate.assert_called_once()
    args, _ = mock_repo_hostile.increment_aggregate.call_args
    assert args[1] == "tenant-hostile"
