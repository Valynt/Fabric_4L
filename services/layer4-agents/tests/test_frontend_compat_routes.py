from __future__ import annotations

"""Integration tests for frontend compatibility routes.

Tests the following alias routes:
- POST /v1/auth/register
- GET /v1/tenant/settings
- PATCH /v1/tenant/settings

Uses inline FastAPI app with in-memory stores to avoid heavy DB setup.
"""


from typing import Any
from uuid import UUID, uuid4

import pytest
from fastapi import Depends, FastAPI, HTTPException
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

TEST_TENANT_ID = uuid4()
TEST_USER_ID = uuid4()


# ---------------------------------------------------------------------------
# In-memory stores (mirroring real service behavior without DB dependencies)
# ---------------------------------------------------------------------------

class InMemoryTenantStore:
    def __init__(self):
        self.tenants: dict[UUID, dict[str, Any]] = {}

    def create(self, tenant_id: UUID, name: str, slug: str, settings: dict) -> dict[str, Any]:
        self.tenants[tenant_id] = {
            "id": tenant_id,
            "name": name,
            "slug": slug,
            "status": "active",
            "settings": settings,
        }
        return self.tenants[tenant_id]

    def get_by_slug(self, slug: str) -> dict[str, Any] | None:
        for t in self.tenants.values():
            if t["slug"] == slug:
                return t
        return None

    def get(self, tenant_id: UUID) -> dict[str, Any] | None:
        return self.tenants.get(tenant_id)

    def update_settings(self, tenant_id: UUID, settings: dict) -> dict[str, Any] | None:
        tenant = self.tenants.get(tenant_id)
        if not tenant:
            return None
        tenant["settings"] = settings
        return tenant


@pytest.fixture
def tenant_store():
    return InMemoryTenantStore()


@pytest.fixture
def app(tenant_store: InMemoryTenantStore) -> FastAPI:
    test_app = FastAPI()

    def override_auth() -> RequestContext:
        return RequestContext(
            tenant_id=TEST_TENANT_ID,
            user_id=TEST_USER_ID,
            roles=[],
        )

    @test_app.post("/v1/auth/register", status_code=202)
    async def register_tenant_frontend_alias(
        request: dict[str, Any],
    ) -> dict[str, Any]:
        slug = request.get("slug")
        if tenant_store.get_by_slug(slug):
            raise HTTPException(status_code=409, detail="Tenant slug already exists")

        tenant_id = uuid4()
        tenant_store.create(
            tenant_id=tenant_id,
            name=request.get("name"),
            slug=slug,
            settings={
                "isolation_tier": "shared",
                "admin_email": request.get("admin_email"),
                "tier_id": request.get("tier_id", "free"),
                "registration_pending": True,
            },
        )
        return {
            "message": "Registration received. Check your email to verify.",
            "tenant_id": str(tenant_id),
            "verification_required": True,
        }

    @test_app.get("/v1/tenant/settings")
    async def get_current_tenant_settings(
        ctx: RequestContext = Depends(override_auth),
    ) -> dict[str, Any]:
        tenant = tenant_store.get(ctx.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        settings = tenant["settings"] or {}
        return {
            "id": str(tenant["id"]),
            "name": tenant["name"],
            "slug": tenant["slug"],
            "status": tenant["status"],
            "tier_id": settings.get("tier_id", "free"),
            "settings": settings,
            "created_at": "",
        }

    @test_app.patch("/v1/tenant/settings")
    async def update_current_tenant_settings(
        update: dict[str, Any],
        ctx: RequestContext = Depends(override_auth),
    ) -> dict[str, Any]:
        tenant = tenant_store.get(ctx.tenant_id)
        if not tenant:
            raise HTTPException(status_code=404, detail="Tenant not found")
        current_settings = tenant["settings"] or {}
        new_settings = update.get("settings", {})
        allowed_fields = {"custom_branding", "notification_preferences", "webhook_url"}
        for key, value in new_settings.items():
            if key in allowed_fields:
                current_settings[key] = value
        updated = tenant_store.update_settings(ctx.tenant_id, current_settings)
        if not updated:
            raise HTTPException(status_code=500, detail="Failed to update tenant settings")
        return {
            "id": str(updated["id"]),
            "name": updated["name"],
            "settings": updated["settings"],
            "updated_at": "",
        }

    return test_app


@pytest.fixture
async def client(app: FastAPI) -> AsyncClient:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


# ---------------------------------------------------------------------------
# POST /v1/auth/register
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_auth_register_creates_tenant(client: AsyncClient):
    """POST /v1/auth/register creates a new tenant and returns tenant_id."""
    payload = {
        "name": "Test Corp",
        "slug": "test-corp",
        "admin_email": "admin@testcorp.example",
        "tier_id": "free",
    }

    response = await client.post("/v1/auth/register", json=payload)
    assert response.status_code == 202
    data = response.json()
    assert data["message"] == "Registration received. Check your email to verify."
    assert "tenant_id" in data
    assert data["verification_required"] is True


@pytest.mark.asyncio
async def test_auth_register_duplicate_slug(client: AsyncClient):
    """POST /v1/auth/register rejects duplicate slug with 409."""
    payload = {
        "name": "Test Corp",
        "slug": "duplicate-slug",
        "admin_email": "admin@testcorp.example",
        "tier_id": "free",
    }

    r1 = await client.post("/v1/auth/register", json=payload)
    assert r1.status_code == 202

    r2 = await client.post("/v1/auth/register", json=payload)
    assert r2.status_code == 409


# ---------------------------------------------------------------------------
# GET /v1/tenant/settings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_get_tenant_settings(client: AsyncClient, tenant_store: InMemoryTenantStore):
    """GET /v1/tenant/settings returns settings for the current tenant."""
    tenant_store.create(
        tenant_id=TEST_TENANT_ID,
        name="Test Tenant",
        slug="test-tenant",
        settings={"tier_id": "pro", "custom_branding": {"logo": "https://example.com/logo.png"}},
    )

    response = await client.get("/v1/tenant/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(TEST_TENANT_ID)
    assert data["name"] == "Test Tenant"
    assert data["tier_id"] == "pro"
    assert "settings" in data


@pytest.mark.asyncio
async def test_get_tenant_settings_not_found(client: AsyncClient):
    """GET /v1/tenant/settings returns 404 when tenant does not exist."""
    response = await client.get("/v1/tenant/settings")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /v1/tenant/settings
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_patch_tenant_settings(client: AsyncClient, tenant_store: InMemoryTenantStore):
    """PATCH /v1/tenant/settings updates allowed settings fields."""
    tenant_store.create(
        tenant_id=TEST_TENANT_ID,
        name="Test Tenant",
        slug="test-tenant",
        settings={"custom_branding": {"logo": "old.png"}},
    )

    payload = {
        "settings": {
            "custom_branding": {"logo": "new.png"},
            "webhook_url": "https://example.com/webhook",
            "disallowed_field": "should_be_ignored",
        }
    }

    response = await client.patch("/v1/tenant/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["settings"]["custom_branding"]["logo"] == "new.png"
    assert data["settings"]["webhook_url"] == "https://example.com/webhook"
    assert "disallowed_field" not in data["settings"]
