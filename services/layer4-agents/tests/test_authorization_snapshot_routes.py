from __future__ import annotations

from datetime import UTC, datetime, timedelta
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from value_fabric.shared.identity.context import RequestContext

from layer4_agents.api.app_factory import create_app
from layer4_agents.api.routes.authorization_snapshot import get_authorization_snapshot


def test_authorization_snapshot_route_is_registered() -> None:
    app = create_app()

    assert any(route.path == "/v1/authz/snapshot" for route in app.routes)


@pytest.mark.asyncio
async def test_authenticated_tenant_receives_verified_authorization_snapshot(monkeypatch) -> None:
    tenant = SimpleNamespace(id="tenant-id", slug="acme")

    async def fake_get_tenant(_db, _tenant_id):
        return tenant

    monkeypatch.setattr(
        "layer4_agents.api.routes.authorization_snapshot.get_tenant", fake_get_tenant
    )
    expires_at = datetime.now(UTC) + timedelta(minutes=5)
    context = RequestContext(
        tenant_id="tenant-id",
        user_id="user-id",
        roles=["org:value_engineer"],
        permissions=frozenset({"account:read"}),
        tenant_role="org:value_engineer",
        raw={
            "exp": expires_at.timestamp(),
            "entitlements": ["feature.a"],
            "account_ids": ["account-1"],
        },
    )

    response = await get_authorization_snapshot(
        tenant_slug="acme", db=object(), ctx=context
    )

    assert response.snapshot.tenant_id == "tenant-id"
    assert response.snapshot.tenant_slug == "acme"
    assert response.snapshot.role == "org:value_engineer"
    assert response.snapshot.permissions == ["account:read"]
    assert response.snapshot.entitlements == ["feature.a"]
    assert response.snapshot.account_ids == ["account-1"]
    assert response.snapshot.tenant_member is True
    assert response.snapshot.expires_at == expires_at


@pytest.mark.asyncio
async def test_snapshot_rejects_slug_outside_authenticated_tenant(monkeypatch) -> None:
    async def fake_get_tenant(_db, _tenant_id):
        return SimpleNamespace(id="tenant-id", slug="acme")

    monkeypatch.setattr(
        "layer4_agents.api.routes.authorization_snapshot.get_tenant", fake_get_tenant
    )
    context = RequestContext(
        tenant_id="tenant-id",
        user_id="user-id",
        roles=["org:member"],
        raw={"exp": (datetime.now(UTC) + timedelta(minutes=5)).timestamp()},
    )

    with pytest.raises(HTTPException) as exc_info:
        await get_authorization_snapshot(
            tenant_slug="other", db=object(), ctx=context
        )

    assert exc_info.value.status_code == 403
