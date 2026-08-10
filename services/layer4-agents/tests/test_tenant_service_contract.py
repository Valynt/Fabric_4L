from __future__ import annotations

from datetime import UTC, datetime
from types import SimpleNamespace
from uuid import UUID

import pytest
from fastapi import HTTPException
from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ConflictError,
    TenantIsolationError,
    ValidationError,
)
from value_fabric.shared.identity.models import TenantStatus, UserStatus
from value_fabric.shared.identity.permissions import Role

import layer4_agents.tenants.service as module
from layer4_agents.tenants.models.tenant import IsolationTier

TENANT = UUID("550e8400-e29b-41d4-a716-446655440000")
USER = UUID("5f7ed580-763c-4adb-9b4d-4c79e5152548")


class Result:
    def __init__(self, value=None, values=(), scalar=None):
        self.value = value
        self.values = list(values)
        self.scalar_value = scalar

    def scalar_one_or_none(self):
        return self.value

    def scalar(self):
        return self.scalar_value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class DB:
    def __init__(self, results=()):
        self.results = list(results)
        self.added = []
        self.flushes = 0

    async def execute(self, _query):
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def flush(self):
        self.flushes += 1
        now = datetime.now(UTC)
        for value in self.added:
            if getattr(value, "created_at", None) is None:
                value.created_at = now
            if getattr(value, "updated_at", None) is None:
                value.updated_at = now


def tenant(**values):
    defaults = {
        "id": TENANT,
        "name": "Tenant",
        "slug": "tenant",
        "status": TenantStatus.ACTIVE.value,
        "settings": {},
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def user(**values):
    defaults = {
        "id": USER,
        "tenant_id": TENANT,
        "email": "user@example.test",
        "display_name": "User",
        "role": Role.ANALYST.value,
        "status": UserStatus.ACTIVE.value,
        "last_login_at": None,
        "invited_by": None,
        "created_at": datetime.now(UTC),
        "updated_at": datetime.now(UTC),
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


def api_key(**values):
    defaults = {
        "key_id": "vf_key",
        "tenant_id": TENANT,
        "user_id": USER,
        "name": "Key",
        "prefix": "vf_test",
        "role": Role.ANALYST.value,
        "permissions": [],
        "enabled": True,
        "revoked_at": None,
        "created_at": datetime.now(UTC),
        "expires_at": None,
        "last_used_at": None,
        "rate_limit_per_minute": 10,
        "metadata_": {},
        "is_revoked": lambda: False,
        "is_active": lambda: True,
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_tenant_crud_and_counts(monkeypatch) -> None:
    db = DB()
    request = SimpleNamespace(name="New", slug="new", settings={"tier_id": "free"})
    created = await module.create_tenant(db, request)
    assert created.name == "New" and db.added[0].slug == "new"

    row = tenant(settings={"existing": 1})
    db.results = [Result(row), Result(None), Result("active"), Result(row), Result(None)]
    assert (await module.get_tenant(db, TENANT)).id == TENANT
    assert await module.get_tenant(db, TENANT) is None
    assert await module.get_tenant_status(db, TENANT) == "active"
    assert (await module.get_tenant_by_slug(db, "tenant")).slug == "tenant"
    assert await module.get_tenant_by_slug(db, "missing") is None

    db.results = [Result(row), Result(None)]
    updated = await module.update_tenant_settings(
        db, TENANT, name="Changed", settings_update={"new": 2}
    )
    assert updated.name == "Changed" and updated.settings == {"existing": 1, "new": 2}
    assert await module.update_tenant_settings(db, TENANT) is None

    db.results = [Result(scalar=3), Result(scalar=None), Result(value={"limit": 1}), Result(None)]
    assert await module.count_users(db, TENANT) == 3
    assert await module.count_api_keys(db, TENANT) == 0
    assert await module.get_tenant_settings(db, TENANT) == {"limit": 1}
    assert await module.get_tenant_settings(db, TENANT) == {}

    db.results = [Result(values=[row])]
    assert [item.id for item in await module.list_tenants(db, status="active", limit=1)] == [TENANT]

    request = SimpleNamespace(name="Renamed", status=TenantStatus.SUSPENDED, settings={"x": 1})
    db.results = [Result(row), Result(None)]
    assert (await module.update_tenant(db, TENANT, request)).status == "suspended"
    assert await module.update_tenant(db, TENANT, request) is None

    monkeypatch.setattr(module, "get_tenant", lambda *_args: _value(None))
    assert await module.get_tier_api_key_limit(db, TENANT) is None


@pytest.mark.asyncio
async def test_tenant_status_delete_and_isolation_history(monkeypatch) -> None:
    transitions = []
    row = tenant()
    row.transition_to = lambda *args, **kwargs: transitions.append((args, kwargs))
    db = DB([Result(None), Result(row), Result(row), Result(None)])
    assert not await module.update_tenant_status(db, TENANT, "suspended")
    assert await module.update_tenant_status(db, TENANT, "suspended", reason="policy")
    assert await module.delete_tenant(db, TENANT)
    assert not await module.delete_tenant(db, TENANT, reason="closed", changed_by="admin")
    assert transitions[-1][0] == ("deleted",)

    with pytest.raises(ValueError, match="change_source"):
        await module.log_isolation_tier_change(db, TENANT, "shared", "schema", change_source="bad")
    with pytest.raises(ValueError, match="from_tier"):
        await module.log_isolation_tier_change(db, TENANT, "bad", "schema")
    with pytest.raises(ValueError, match="to_tier"):
        await module.log_isolation_tier_change(db, TENANT, "shared", "bad")
    history = await module.log_isolation_tier_change(
        db, TENANT, "shared", "schema", changed_by=USER, reason="scale"
    )
    assert history in db.added and history.change_source == "admin"

    with pytest.raises(ValueError, match="Invalid isolation tier"):
        await module.update_tenant_isolation_tier(db, TENANT, "bad")
    db.results = [Result(None)]
    assert await module.update_tenant_isolation_tier(db, TENANT, "schema") is None
    row = tenant(settings={"isolation_tier": IsolationTier.SHARED.value})
    db.results = [Result(row)]
    changed = await module.update_tenant_isolation_tier(
        db, TENANT, IsolationTier.SCHEMA.value, changed_by=USER
    )
    assert changed.settings["isolation_tier"] == "schema"


@pytest.mark.asyncio
async def test_user_invitation_security_and_crud(monkeypatch) -> None:
    request = SimpleNamespace(email="new@example.test", display_name="New", role=Role.ANALYST)
    db = DB()
    monkeypatch.setattr(module, "can_grant_role", lambda *_args: False)
    with pytest.raises(AuthorizationError):
        await module.invite_user(db, TENANT, request, inviter_roles=[Role.ANALYST.value])

    monkeypatch.setattr(module, "can_grant_role", lambda *_args: True)
    db.results = [Result(user())]
    with pytest.raises(ConflictError):
        await module.invite_user(db, TENANT, request)

    invitation = SimpleNamespace(generate_token=lambda *_args: "token")
    db.results = [Result(None)]
    invited, token = await module.invite_user(db, TENANT, request, invitation_service=invitation)
    assert invited.status == "invited" and token == "token"

    invalid_invitation = SimpleNamespace(verify_token=lambda _token: _value(None))
    accept = SimpleNamespace(token="token", password="Password123!", display_name=None)
    with pytest.raises(HTTPException) as exc:
        await module.accept_invitation(db, accept, invalid_invitation)
    assert exc.value.status_code == 401

    token_data = SimpleNamespace(user_id=USER, tenant_id=TENANT)
    invitation = SimpleNamespace(
        verify_token=lambda _token: _value(token_data), consume_token=lambda _token: _value(None)
    )
    db.results = [Result(None)]
    with pytest.raises(HTTPException):
        await module.accept_invitation(db, accept, invitation)
    db.results = [Result(user(status="active"))]
    with pytest.raises(HTTPException):
        await module.accept_invitation(db, accept, invitation)

    invited_row = user(status="invited")
    db.results = [Result(invited_row)]
    monkeypatch.setattr(module, "hash_password", lambda _password: "hashed")
    activated = await module.accept_invitation(db, accept, invitation)
    assert activated.status == "active" and invited_row.hashed_password == "hashed"

    db.results = [Result(user()), Result(None), Result(values=[user()])]
    assert (await module.get_user(db, TENANT, USER)).id == USER
    assert await module.get_user(db, TENANT, USER) is None
    assert len(await module.list_users(db, TENANT)) == 1
    row = user()
    update = SimpleNamespace(
        display_name="Changed", role=Role.TENANT_ADMIN, status=UserStatus.DEACTIVATED
    )
    db.results = [Result(row), Result(None), Result(row), Result(None)]
    assert (await module.update_user(db, TENANT, USER, update)).role == Role.TENANT_ADMIN.value
    assert await module.update_user(db, TENANT, USER, update) is None
    assert await module.deactivate_user(db, TENANT, USER)
    assert not await module.deactivate_user(db, TENANT, USER)


@pytest.mark.asyncio
async def test_api_key_isolation_listing_revocation_and_lookup(monkeypatch) -> None:
    request = SimpleNamespace(role=Role.ANALYST)
    db = DB()
    monkeypatch.setattr(module, "can_grant_role", lambda *_args: False)
    with pytest.raises(AuthorizationError):
        await module.create_api_key(db, TENANT, request, creator_role=Role.ANALYST)
    monkeypatch.setattr(module, "can_grant_role", lambda *_args: True)
    db.results = [Result(None)]
    with pytest.raises(TenantIsolationError):
        await module.create_api_key(db, TENANT, request, user_id=USER)

    key = api_key()
    db.results = [Result(values=[key]), Result(values=[key])]
    assert len(await module.list_api_keys(db, TENANT)) == 1
    assert len(await module.list_api_keys(db, TENANT, active_only=False)) == 1

    revoked = api_key(is_revoked=lambda: True)
    active = api_key()
    db.results = [Result(None), Result(revoked), Result(active)]
    assert not await module.revoke_api_key(db, TENANT, "missing")
    assert await module.revoke_api_key(db, TENANT, "revoked")
    assert await module.revoke_api_key(db, TENANT, "active") and not active.enabled

    db.results = [Result(None), Result(api_key(is_active=lambda: False)), Result(key)]
    assert await module.lookup_api_key_by_hash(db, "key") is None
    assert await module.lookup_api_key_by_hash(db, "key") is None
    result = await module.lookup_api_key_by_hash(db, "key")
    assert result.key_id == "vf_key" and result.tenant_id == str(TENANT)


@pytest.mark.asyncio
async def test_accept_invitation_rejects_bad_password(monkeypatch) -> None:
    token_data = SimpleNamespace(user_id=USER, tenant_id=TENANT)
    invitation = SimpleNamespace(verify_token=lambda _token: _value(token_data))
    db = DB([Result(user(status="invited"))])
    monkeypatch.setattr(module, "hash_password", lambda _password: _raise(ValueError("weak")))
    with pytest.raises(ValidationError, match="requirements"):
        await module.accept_invitation(
            db,
            SimpleNamespace(token="token", password="weak", display_name=None),
            invitation,
        )


async def _value(value):
    return value


def _raise(error):
    raise error
