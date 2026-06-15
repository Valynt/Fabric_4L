from __future__ import annotations

from types import SimpleNamespace
from uuid import uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from layer4_agents.api.routes import tenant_context as tenant_context_route


@pytest.fixture
def app(monkeypatch) -> FastAPI:
    test_app = FastAPI()
    register_exception_handlers(test_app)
    test_app.include_router(tenant_context_route.router, prefix="/v1")

    tenant_id = uuid4()

    async def override_auth() -> RequestContext:
        return RequestContext(
            tenant_id=tenant_id,
            user_id="user-123",
            roles=["tenant_admin"],
            permissions=frozenset({"read:tenant", "write:tenant"}),
            request_id="req-123",
            auth_source="jwt_claim",
            isolation_tier="shared",
        )

    async def override_db():
        return object()

    async def fake_get_tenant(_db, _tenant_id):
        return SimpleNamespace(
            id=tenant_id,
            name="Acme",
            slug="acme",
            status="active",
            settings={"tier_id": "pro", "region": "us"},
        )

    monkeypatch.setattr(tenant_context_route, "get_tenant", fake_get_tenant)

    test_app.dependency_overrides[require_authenticated] = override_auth
    test_app.dependency_overrides[tenant_context_route.get_db_from_context] = override_db
    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest.mark.asyncio
async def test_get_tenant_context_returns_authenticated_context(client: AsyncClient) -> None:
    response = await client.get("/v1/tenant/context")

    assert response.status_code == 200
    data = response.json()
    assert data["tenant"]["name"] == "Acme"
    assert data["tenant"]["tier_id"] == "pro"
    assert data["actor"]["user_id"] == "user-123"
    assert data["actor"]["roles"] == ["tenant_admin"]
    assert set(data["actor"]["permissions"]) == {"read:tenant", "write:tenant"}
    assert data["request"]["request_id"] == "req-123"
    assert data["request"]["auth_source"] == "jwt_claim"


@pytest.mark.asyncio
async def test_get_tenant_context_returns_404_when_tenant_missing(client: AsyncClient, app: FastAPI, monkeypatch) -> None:
    async def missing_tenant(_db, _tenant_id):
        return None

    monkeypatch.setattr(tenant_context_route, "get_tenant", missing_tenant)

    response = await client.get("/v1/tenant/context")
    assert response.status_code == 404
    assert response.json()["error"]["message"] == "Tenant not found"
