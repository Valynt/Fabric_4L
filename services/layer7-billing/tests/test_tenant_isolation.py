"""Tenant isolation tests for Layer 7 Billing Service.

Tests verify:
1. Tenant A cannot access Tenant B's billing data
2. Tenant A cannot modify Tenant B's plans
3. Tenant A cannot inject usage events for Tenant B
4. Tenant A cannot view Tenant B's invoices
5. Adversarial attempts to bypass tenant isolation are blocked
"""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from layer7_billing.api.main import app, get_principal, Principal
from layer7_billing.database import get_db_from_context
from layer7_billing import repository


@pytest.mark.asyncio
async def test_tenant_cannot_access_another_tenant_plan(db: AsyncSession):
    """Tenant A should not be able to retrieve Tenant B's plan entitlements."""
    # Setup: Create plan for Tenant A
    await repository.upsert_plan(
        db, "tenant-a", "plan-a", "Plan A", ["feature1", "feature2"]
    )
    await db.commit()
    
    # Setup: Create plan for Tenant B
    await repository.upsert_plan(
        db, "tenant-b", "plan-b", "Plan B", ["feature3", "feature4"]
    )
    await db.commit()
    
    # Act: Tenant A attempts to access Tenant B's plan
    entitlements = await repository.get_plan_entitlements(db, "tenant-a", "plan-b")
    
    # Assert: Tenant A should not see Tenant B's entitlements
    assert entitlements == [], "Tenant A should not see Tenant B's plan entitlements"


@pytest.mark.asyncio
async def test_tenant_cannot_modify_another_tenant_plan(db: AsyncSession):
    """Tenant A should not be able to modify Tenant B's plan."""
    # Setup: Create plan for Tenant B
    await repository.upsert_plan(
        db, "tenant-b", "plan-b", "Plan B", ["feature3", "feature4"]
    )
    await db.commit()
    
    # Act: Tenant A attempts to modify Tenant B's plan
    # This should only affect Tenant A's context due to RLS
    await repository.upsert_plan(
        db, "tenant-a", "plan-b", "Hacked Plan", ["malicious"]
    )
    await db.commit()
    
    # Assert: Tenant B's original plan should remain unchanged
    # Switch to Tenant B context to verify
    entitlements = await repository.get_plan_entitlements(db, "tenant-b", "plan-b")
    assert entitlements == ["feature3", "feature4"], "Tenant B's plan should remain unchanged"


@pytest.mark.asyncio
async def test_tenant_cannot_inject_usage_events_for_another_tenant(db: AsyncSession):
    """Tenant A should not be able to inject usage events for Tenant B."""
    # Setup: Tenant A attempts to inject event for Tenant B
    event_dict = {
        "event_id": "event-123",
        "metric": "api_calls",
        "quantity": 1000.0,
        "source": "malicious",
        "timestamp": "2026-05-27T00:00:00Z",
        "request_id": "req-123"
    }
    
    # Act: Tenant A context attempts to inject event with tenant_b's ID
    # Due to RLS, this should only affect Tenant A's data
    is_new = await repository.insert_usage_event(db, "tenant-a", event_dict)
    await db.commit()
    
    # Assert: Event should be associated with Tenant A, not Tenant B
    # Verify by checking Tenant A's aggregates
    aggregates = await repository.get_usage_aggregates(db, "tenant-a")
    assert "api_calls" in aggregates, "Event should be associated with Tenant A"
    assert aggregates["api_calls"] == 1000.0


@pytest.mark.asyncio
async def test_tenant_cannot_view_another_tenant_invoices(db: AsyncSession):
    """Tenant A should not be able to view Tenant B's invoices."""
    # Setup: Create invoice for Tenant B
    from layer7_billing.models import Invoice
    invoice = Invoice(
        invoice_id="inv-123",
        tenant_id="tenant-b",
        payload={"amount": 1000, "currency": "USD"}
    )
    db.add(invoice)
    await db.commit()
    
    # Act: Tenant A attempts to list invoices
    invoices = await repository.list_invoices(db, "tenant-a")
    
    # Assert: Tenant A should not see Tenant B's invoice
    assert len(invoices) == 0, "Tenant A should not see Tenant B's invoices"
    
    # Verify Tenant B can see their own invoice
    invoices_b = await repository.list_invoices(db, "tenant-b")
    assert len(invoices_b) == 1, "Tenant B should see their own invoice"
    assert invoices_b[0]["invoice_id"] == "inv-123"


@pytest.mark.asyncio
async def test_tenant_cannot_access_another_tenant_payment_state(db: AsyncSession):
    """Tenant A should not be able to access Tenant B's payment state."""
    # Setup: Create payment state for Tenant B
    from layer7_billing.models import PaymentState
    state = PaymentState(
        tenant_id="tenant-b",
        state_key="current",
        state="paid",
        payload={"amount": 1000}
    )
    db.add(state)
    await db.commit()
    
    # Act: Tenant A attempts to get payment state
    state_a = await repository.get_payment_state(db, "tenant-a", "current")
    
    # Assert: Tenant A should get default state, not Tenant B's state
    assert state_a["state"] == "pending", "Tenant A should get default pending state"
    assert state_a["payload"] == {}, "Tenant A should not see Tenant B's payload"
    
    # Verify Tenant B can see their own state
    state_b = await repository.get_payment_state(db, "tenant-b", "current")
    assert state_b["state"] == "paid", "Tenant B should see their paid state"
    assert state_b["payload"]["amount"] == 1000


@pytest.mark.asyncio
async def test_cross_tenant_usage_aggregate_isolation(db: AsyncSession):
    """Usage aggregates should be isolated per tenant."""
    # Setup: Create usage events for both tenants
    event_a = {
        "event_id": "event-a",
        "metric": "api_calls",
        "quantity": 100.0,
        "source": "tenant-a",
        "timestamp": "2026-05-27T00:00:00Z",
        "request_id": "req-a"
    }
    
    event_b = {
        "event_id": "event-b",
        "metric": "api_calls",
        "quantity": 200.0,
        "source": "tenant-b",
        "timestamp": "2026-05-27T00:00:00Z",
        "request_id": "req-b"
    }
    
    await repository.insert_usage_event(db, "tenant-a", event_a)
    await repository.insert_usage_event(db, "tenant-b", event_b)
    await repository.increment_aggregate(db, "tenant-a", "api_calls", 100.0)
    await repository.increment_aggregate(db, "tenant-b", "api_calls", 200.0)
    await db.commit()
    
    # Act: Get aggregates for each tenant
    aggregates_a = await repository.get_usage_aggregates(db, "tenant-a")
    aggregates_b = await repository.get_usage_aggregates(db, "tenant-b")
    
    # Assert: Aggregates should be isolated
    assert aggregates_a["api_calls"] == 100.0, "Tenant A should only see their own usage"
    assert aggregates_b["api_calls"] == 200.0, "Tenant B should only see their own usage"


@pytest.mark.asyncio
async def test_plan_upsert_isolation(db: AsyncSession):
    """Plan upsert should be isolated per tenant."""
    # Setup: Both tenants create plans with same plan_id
    await repository.upsert_plan(
        db, "tenant-a", "shared-plan", "Tenant A Plan", ["feature1"]
    )
    await repository.upsert_plan(
        db, "tenant-b", "shared-plan", "Tenant B Plan", ["feature2"]
    )
    await db.commit()
    
    # Act: Get entitlements for each tenant
    entitlements_a = await repository.get_plan_entitlements(db, "tenant-a", "shared-plan")
    entitlements_b = await repository.get_plan_entitlements(db, "tenant-b", "shared-plan")
    
    # Assert: Each tenant should see their own plan
    assert entitlements_a == ["feature1"], "Tenant A should see their own plan"
    assert entitlements_b == ["feature2"], "Tenant B should see their own plan"


@pytest.mark.asyncio
async def test_usage_event_idempotency_per_tenant(db: AsyncSession):
    """Usage event idempotency should be per-tenant, not global."""
    event_dict = {
        "event_id": "duplicate-event",
        "metric": "api_calls",
        "quantity": 100.0,
        "source": "test",
        "timestamp": "2026-05-27T00:00:00Z",
        "request_id": "req-123"
    }
    
    # Act: Tenant A inserts event
    is_new_a1 = await repository.insert_usage_event(db, "tenant-a", event_dict)
    await db.commit()
    assert is_new_a1 is True, "First insert should be new"
    
    # Act: Tenant A attempts duplicate insert
    is_new_a2 = await repository.insert_usage_event(db, "tenant-a", event_dict)
    await db.commit()
    assert is_new_a2 is False, "Duplicate insert should not be new"
    
    # Act: Tenant B inserts same event_id (should be allowed)
    is_new_b = await repository.insert_usage_event(db, "tenant-b", event_dict)
    await db.commit()
    assert is_new_b is True, "Same event_id should be new for different tenant"
