"""Auth boundary tests for L2.5 Signal Refinery.

These are hostile negative tests — they verify that unauthenticated,
unauthorized, and malformed-auth requests are rejected at the boundary.

Every protected route must fail safely when auth is missing or invalid.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from .conftest import ACCOUNT_A, TENANT_A, make_signal_payload

pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# Fixtures: unauthorized clients
# ---------------------------------------------------------------------------


@pytest_asyncio.fixture
async def no_auth_client(connection):
    """HTTP client with NO auth context injected.

    Simulates a request that bypasses GovernanceMiddleware.
    """
    from layer2_5_signal_refinery.api.main import create_app
    from layer2_5_signal_refinery import database as db_mod

    app = create_app()

    async def _test_db():
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
            await session.flush()
        finally:
            await session.close()

    app.dependency_overrides[db_mod.get_db_from_context] = _test_db
    # NOTE: deliberately do NOT inject request-context middleware

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


@pytest_asyncio.fixture
async def empty_auth_client(connection):
    """HTTP client with empty/invalid auth context."""
    from layer2_5_signal_refinery.api.main import create_app
    from layer2_5_signal_refinery import database as db_mod
    from value_fabric.shared.identity.context import RequestContext, set_request_context

    app = create_app()

    async def _test_db():
        session = AsyncSession(bind=connection, expire_on_commit=False)
        try:
            yield session
            await session.flush()
        finally:
            await session.close()

    app.dependency_overrides[db_mod.get_db_from_context] = _test_db

    @app.middleware("http")
    async def _inject_empty_context(request, call_next):
        # Empty tenant_id should fail closed
        set_request_context(
            RequestContext(
                tenant_id="",
                user_id="",
                roles=[],
                auth_source="",
            )
        )
        try:
            return await call_next(request)
        finally:
            set_request_context(None)

    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test",
    ) as c:
        yield c


# ---------------------------------------------------------------------------
# Unauthenticated access to protected routes
# ---------------------------------------------------------------------------


async def test_no_auth_create_signal_returns_401(no_auth_client):
    """POST /signals without auth must return 401."""
    payload = make_signal_payload()
    response = await no_auth_client.post("/api/v1/signals", json=payload)
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated create, got {response.status_code}"
    )


async def test_no_auth_list_signals_returns_401(no_auth_client):
    """GET /signals without auth must return 401."""
    response = await no_auth_client.get(
        "/api/v1/signals", params={"account_id": str(ACCOUNT_A)}
    )
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated list, got {response.status_code}"
    )


async def test_no_auth_get_signal_returns_401(no_auth_client):
    """GET /signals/{id} without auth must return 401."""
    response = await no_auth_client.get(
        "/api/v1/signals/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated get, got {response.status_code}"
    )


async def test_no_auth_patch_signal_returns_401(no_auth_client):
    """PATCH /signals/{id} without auth must return 401."""
    response = await no_auth_client.patch(
        "/api/v1/signals/00000000-0000-0000-0000-000000000000",
        json={"lifecycle_state": "validated"},
    )
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated patch, got {response.status_code}"
    )


async def test_no_auth_delete_signal_returns_401(no_auth_client):
    """DELETE /signals/{id} without auth must return 401."""
    response = await no_auth_client.delete(
        "/api/v1/signals/00000000-0000-0000-0000-000000000000"
    )
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated delete, got {response.status_code}"
    )


async def test_no_auth_review_signal_returns_401(no_auth_client):
    """POST /signals/{id}/review without auth must return 401."""
    response = await no_auth_client.post(
        "/api/v1/signals/00000000-0000-0000-0000-000000000000/review",
        json={"status": "validated"},
    )
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated review, got {response.status_code}"
    )


async def test_no_auth_promote_signal_returns_401(no_auth_client):
    """POST /signals/{id}/promote without auth must return 401."""
    response = await no_auth_client.post(
        "/api/v1/signals/00000000-0000-0000-0000-000000000000/promote",
        json={"value_path_category": "revenue_uplift"},
    )
    assert response.status_code == 401, (
        f"Expected 401 for unauthenticated promote, got {response.status_code}"
    )


# ---------------------------------------------------------------------------
# Empty/invalid auth context fails closed
# ---------------------------------------------------------------------------


async def test_empty_auth_context_fails_closed(empty_auth_client):
    """Empty tenant_id in auth context must fail closed (401)."""
    payload = make_signal_payload()
    response = await empty_auth_client.post("/api/v1/signals", json=payload)
    assert response.status_code in (401, 403), (
        f"Expected 401/403 for empty auth context, got {response.status_code}"
    )


