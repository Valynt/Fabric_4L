from __future__ import annotations

import os
from uuid import UUID

os.environ.setdefault("API_KEY_HMAC_SECRET", "test-api-key-secret")
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///:memory:")
os.environ.setdefault("JWT_SECRET", "test-jwt-secret")
os.environ.setdefault("SERVICE_AUTH_SECRET", "test-service-auth-secret")

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import notifications


TENANT_A = UUID("12345678-1234-1234-1234-123456789abc")
TENANT_B = UUID("abcdefab-1234-1234-1234-abcdefabcdef")


@pytest.fixture(autouse=True)
def clear_notification_store() -> None:
    notifications._NOTIFICATIONS_BY_TENANT.clear()


def build_app(tenant_id: UUID = TENANT_A) -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(notifications.router, prefix="/v1")
    app.dependency_overrides[notifications.require_authenticated] = lambda: RequestContext(
        tenant_id=tenant_id,
        user_id="reviewer-123",
    )
    return app


@pytest.mark.asyncio
async def test_notification_create_mark_read_and_reload_roundtrip() -> None:
    app = build_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/v1/notifications",
            json={
                "type": "review_request",
                "title": "Review requested",
                "message": "Jordan Lee requested review.",
                "account_id": "acct-1",
                "subject_type": "business_case",
                "subject_id": "case-1",
            },
        )
        assert created.status_code == 201
        notification = created.json()
        assert notification["read"] is False

        marked = await client.patch(f"/v1/notifications/{notification['id']}/read")
        assert marked.status_code == 200
        assert marked.json()["read"] is True

        listed = await client.get("/v1/notifications")
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["unread_count"] == 0
        assert listed.json()["items"][0]["id"] == notification["id"]
        assert listed.json()["items"][0]["read"] is True


@pytest.mark.asyncio
async def test_notifications_are_tenant_scoped_for_read_and_update() -> None:
    tenant_a_app = build_app(TENANT_A)
    tenant_b_app = build_app(TENANT_B)

    async with AsyncClient(transport=ASGITransport(app=tenant_a_app), base_url="http://test") as tenant_a:
        created = await tenant_a.post(
            "/v1/notifications",
            json={"type": "task_created", "title": "Task created", "message": "Tenant A task"},
        )
        assert created.status_code == 201
        notification_id = created.json()["id"]

    async with AsyncClient(transport=ASGITransport(app=tenant_b_app), base_url="http://test") as tenant_b:
        listed = await tenant_b.get("/v1/notifications")
        assert listed.status_code == 200
        assert listed.json() == {"items": [], "total": 0, "unread_count": 0}

        update = await tenant_b.patch(f"/v1/notifications/{notification_id}/read")
        assert update.status_code == 404
