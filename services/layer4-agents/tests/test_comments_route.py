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
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.routes import comments


TENANT_A = UUID("12345678-1234-1234-1234-123456789abc")
TENANT_B = UUID("abcdefab-1234-1234-1234-abcdefabcdef")


@pytest.fixture(autouse=True)
def clear_comment_store() -> None:
    comments._COMMENTS_BY_TENANT.clear()


def build_app(tenant_id: UUID = TENANT_A) -> FastAPI:
    app = FastAPI()
    app.include_router(comments.router, prefix="/v1")
    app.dependency_overrides[comments.require_authenticated] = lambda: RequestContext(
        tenant_id=tenant_id,
        user_id="reviewer-123",
    )
    return app


@pytest.mark.asyncio
async def test_comment_create_and_reload_roundtrip() -> None:
    app = build_app()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        created = await client.post(
            "/v1/comments",
            json={
                "account_id": "acct-1",
                "subject_type": "business_case",
                "subject_id": "case-1",
                "body": "Please verify the CFO assumption lineage.",
            },
        )
        assert created.status_code == 201
        comment = created.json()
        assert comment["author"] == "reviewer-123"

        listed = await client.get(
            "/v1/comments",
            params={"subject_type": "business_case", "subject_id": "case-1", "account_id": "acct-1"},
        )
        assert listed.status_code == 200
        assert listed.json()["total"] == 1
        assert listed.json()["items"][0]["id"] == comment["id"]
        assert listed.json()["items"][0]["body"] == "Please verify the CFO assumption lineage."


@pytest.mark.asyncio
async def test_comments_are_tenant_scoped() -> None:
    tenant_a_app = build_app(TENANT_A)
    tenant_b_app = build_app(TENANT_B)

    async with AsyncClient(transport=ASGITransport(app=tenant_a_app), base_url="http://test") as tenant_a:
        created = await tenant_a.post(
            "/v1/comments",
            json={"subject_type": "signal", "subject_id": "sig-1", "body": "Tenant A comment"},
        )
        assert created.status_code == 201

    async with AsyncClient(transport=ASGITransport(app=tenant_b_app), base_url="http://test") as tenant_b:
        listed = await tenant_b.get("/v1/comments")
        assert listed.status_code == 200
        assert listed.json() == {"items": [], "total": 0}
