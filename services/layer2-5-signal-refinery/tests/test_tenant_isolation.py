"""Tenant isolation tests for L2.5 Signal Refinery.

These are hostile tests — they verify that Tenant A cannot read, update,
or delete signals belonging to Tenant B.

All tests must pass for the service to be considered production-safe.
"""

from __future__ import annotations

import pytest

from .conftest import ACCOUNT_A, ACCOUNT_B, TENANT_A, TENANT_B, make_signal_payload


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Tenant A cannot read Tenant B signals
# ---------------------------------------------------------------------------


async def test_tenant_a_cannot_read_tenant_b_signal(client, client_b):
    """Tenant B creates a signal. Tenant A must not be able to retrieve it."""
    # Tenant B creates a signal
    payload = make_signal_payload(account_id=str(ACCOUNT_B), content="Tenant B secret signal")
    create_resp = await client_b.post("/api/v1/signals", json=payload)
    assert create_resp.status_code == 201
    signal_id = create_resp.json()["id"]

    # Tenant A tries to get it by ID — must get 404
    get_resp = await client.get(f"/api/v1/signals/{signal_id}")
    assert get_resp.status_code == 404, (
        f"Tenant A should not be able to read Tenant B signal {signal_id}"
    )


async def test_tenant_a_list_does_not_include_tenant_b_signals(client, client_b):
    """Tenant B creates signals. Tenant A's list must not include them."""
    # Tenant B creates a signal for account B
    payload_b = make_signal_payload(account_id=str(ACCOUNT_B), content="Tenant B list signal")
    await client_b.post("/api/v1/signals", json=payload_b)

    # Tenant A creates a signal for account A
    payload_a = make_signal_payload(account_id=str(ACCOUNT_A), content="Tenant A list signal")
    await client.post("/api/v1/signals", json=payload_a)

    # Tenant A lists signals for account A — must not see Tenant B's signal
    list_resp = await client.get("/api/v1/signals", params={"account_id": str(ACCOUNT_A)})
    assert list_resp.status_code == 200
    items = list_resp.json()["items"]
    contents = [s["content"] for s in items]
    assert "Tenant B list signal" not in contents


# ---------------------------------------------------------------------------
# Tenant A cannot mutate Tenant B signals
# ---------------------------------------------------------------------------


async def test_tenant_a_cannot_update_tenant_b_signal(client, client_b):
    """Tenant B creates a signal. Tenant A's PATCH must return 404."""
    payload = make_signal_payload(account_id=str(ACCOUNT_B))
    create_resp = await client_b.post("/api/v1/signals", json=payload)
    assert create_resp.status_code == 201
    signal_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/signals/{signal_id}",
        json={"lifecycle_state": "validated"},
    )
    assert patch_resp.status_code == 404, (
        f"Tenant A should not be able to update Tenant B signal {signal_id}"
    )


async def test_tenant_a_cannot_delete_tenant_b_signal(client, client_b):
    """Tenant B creates a signal. Tenant A's DELETE must return 404."""
    payload = make_signal_payload(account_id=str(ACCOUNT_B))
    create_resp = await client_b.post("/api/v1/signals", json=payload)
    assert create_resp.status_code == 201
    signal_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/signals/{signal_id}")
    assert del_resp.status_code == 404, (
        f"Tenant A should not be able to delete Tenant B signal {signal_id}"
    )

    # Verify Tenant B's signal still exists
    get_resp = await client_b.get(f"/api/v1/signals/{signal_id}")
    assert get_resp.status_code == 200


async def test_tenant_a_cannot_review_tenant_b_signal(client, client_b):
    """Tenant B creates a signal. Tenant A's review must return 404."""
    payload = make_signal_payload(account_id=str(ACCOUNT_B))
    create_resp = await client_b.post("/api/v1/signals", json=payload)
    assert create_resp.status_code == 201
    signal_id = create_resp.json()["id"]

    review_resp = await client.post(
        f"/api/v1/signals/{signal_id}/review",
        json={"status": "validated"},
    )
    assert review_resp.status_code == 404, (
        f"Tenant A should not be able to review Tenant B signal {signal_id}"
    )


async def test_tenant_a_cannot_promote_tenant_b_signal(client, client_b):
    """Tenant B creates and validates a signal. Tenant A's promote must return 404."""
    payload = make_signal_payload(account_id=str(ACCOUNT_B))
    create_resp = await client_b.post("/api/v1/signals", json=payload)
    assert create_resp.status_code == 201
    signal_id = create_resp.json()["id"]

    # Tenant B validates it
    await client_b.post(f"/api/v1/signals/{signal_id}/review", json={"status": "validated"})

    # Tenant A tries to promote it
    promote_resp = await client.post(
        f"/api/v1/signals/{signal_id}/promote",
        json={"value_path_category": "revenue_uplift"},
    )
    assert promote_resp.status_code == 404, (
        f"Tenant A should not be able to promote Tenant B signal {signal_id}"
    )


# ---------------------------------------------------------------------------
# Missing tenant context fails closed
# ---------------------------------------------------------------------------


async def test_missing_tenant_context_fails_closed(engine):
    """A request without X-Tenant-ID must be rejected."""
    from httpx import ASGITransport, AsyncClient
    from layer2_5_signal_refinery.api.main import create_app
    from layer2_5_signal_refinery import database as db_mod
    from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

    app = create_app()
    factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async def _test_db():
        async with factory() as session:
            yield session

    app.dependency_overrides[db_mod.get_db_from_context] = _test_db

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
        # No X-Tenant-ID header
    ) as c:
        resp = await c.get("/api/v1/signals", params={"account_id": "some-account"})
        assert resp.status_code in (400, 401, 422), (
            f"Expected 400/401/422 without tenant context, got {resp.status_code}"
        )


# ---------------------------------------------------------------------------
# Signal created by Tenant A has correct tenant_id
# ---------------------------------------------------------------------------


async def test_created_signal_has_correct_tenant_id(client):
    """Signals must always be stamped with the authenticated tenant_id."""
    payload = make_signal_payload()
    resp = await client.post("/api/v1/signals", json=payload)
    assert resp.status_code == 201
    assert resp.json()["tenant_id"] == str(TENANT_A)
