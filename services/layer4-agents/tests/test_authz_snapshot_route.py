from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api import routers
from layer4_agents.api.routes import authz


def _context(**overrides: object) -> RequestContext:
    raw = {
        "exp": (datetime.now(UTC) + timedelta(minutes=5)).timestamp(),
        "entitlements": ["reports", "reports", ""],
        "account_ids": ["account-b", "account-a", "account-a"],
    }
    raw.update(overrides.pop("raw", {}))
    return RequestContext(
        tenant_id=overrides.pop("tenant_id", "tenant-1"),
        user_id="user-1",
        roles=overrides.pop("roles", ["custom:operator"]),
        permissions=overrides.pop("permissions", ["signals:read", "account:read"]),
        raw=raw,
        **overrides,
    )


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch):
    app = FastAPI()
    app.include_router(authz.router, prefix="/v1")
    current = {"ctx": _context()}

    async def get_ctx():
        return current["ctx"]

    async def get_db():
        yield object()

    async def get_tenant(_db, tenant_id):
        return SimpleNamespace(id=tenant_id, slug="tenant-a")

    app.dependency_overrides[authz.require_authenticated] = get_ctx
    app.dependency_overrides[authz.get_db_from_context] = get_db
    monkeypatch.setattr(authz, "get_tenant", get_tenant)
    return TestClient(app), current


def test_snapshot_returns_only_authoritative_context_grants(client):
    http, _ = client
    response = http.get("/v1/authz/snapshot", params={"tenant_slug": "tenant-a"})
    assert response.status_code == 200
    assert response.json() == {
        "tenantId": "tenant-1",
        "tenantSlug": "tenant-a",
        "role": "custom:operator",
        "expiresAt": response.json()["expiresAt"],
        "permissions": ["account:read", "signals:read"],
        "entitlements": ["reports"],
        "tenantMember": True,
        "accountIds": ["account-a", "account-b"],
    }


def test_snapshot_rejects_cross_tenant_selector(client):
    http, _ = client
    assert http.get("/v1/authz/snapshot?tenant_slug=tenant-b").status_code == 403


@pytest.mark.parametrize(
    "ctx",
    [
        _context(tenant_id=None),
        _context(raw={"exp": "not-a-date"}),
        _context(raw={"exp": (datetime.now(UTC) - timedelta(seconds=1)).timestamp()}),
    ],
)
def test_snapshot_rejects_incomplete_or_expired_context(client, ctx):
    http, current = client
    current["ctx"] = ctx
    response = http.get("/v1/authz/snapshot")
    assert response.status_code == 401
    assert "permissions" not in response.json()


def test_layer4_registers_snapshot_and_openapi_schema():
    app = FastAPI()
    routers.register_routers(app)
    operation = app.openapi()["paths"]["/v1/authz/snapshot"]["get"]
    schema = operation["responses"]["200"]["content"]["application/json"]["schema"]
    assert schema["$ref"].endswith("/AuthorizationSnapshot")
