from __future__ import annotations

from contextlib import asynccontextmanager
from types import SimpleNamespace
from uuid import UUID

import pytest
from value_fabric.shared.identity.context import RequestContext

import layer4_agents.feature_flags.service as module
from layer4_agents.feature_flags.service import FeatureFlagService

TENANT = UUID("550e8400-e29b-41d4-a716-446655440000")
USER = UUID("5f7ed580-763c-4adb-9b4d-4c79e5152548")


class Result:
    def __init__(self, *, scalar=None, scalars=()):
        self.value = scalar
        self.values = list(scalars)

    def scalar_one_or_none(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class DB:
    def __init__(self, results=()):
        self.results = list(results)
        self.queries = []
        self.added = []
        self.deleted = []
        self.flushes = 0

    async def execute(self, query):
        self.queries.append(query)
        return self.results.pop(0)

    def add(self, value):
        self.added.append(value)

    async def delete(self, value):
        self.deleted.append(value)

    async def flush(self):
        self.flushes += 1


class Background:
    def __init__(self):
        self.calls = []

    def add_task(self, *args):
        self.calls.append(args)


@pytest.mark.asyncio
async def test_list_and_get_flags_scope_tenant_and_platform() -> None:
    flags = [object()]
    tenant_flag = object()
    db = DB([Result(scalars=flags), Result(scalars=[]), Result(scalar=tenant_flag)])
    assert await FeatureFlagService.list_flags(db, TENANT, limit=3, offset=2) == flags
    assert await FeatureFlagService.list_flags(db, None) == []
    assert await FeatureFlagService.get_flag(db, "flag", TENANT) is tenant_flag
    rendered = [str(query) for query in db.queries]
    assert "tenant_id =" in rendered[0]
    assert "tenant_id IS NULL" in rendered[1]
    assert "flag_key" in rendered[2] and "tenant_id" in rendered[2]


@pytest.mark.asyncio
async def test_upsert_updates_existing_and_emits_audit(monkeypatch) -> None:
    existing = SimpleNamespace(
        enabled=False,
        rollout_percentage=0,
        description="old",
        metadata_={"old": True},
        updated_by=None,
    )
    db = DB([Result(scalar=existing)])
    events = []
    event = object()
    monkeypatch.setattr(
        module, "emit_audit_event", lambda *args, **kwargs: events.append((args, kwargs)) or event
    )
    monkeypatch.setattr(module.AuditEmitter, "write_to_db", object())
    background = Background()
    ctx = RequestContext(tenant_id=TENANT, user_id=str(USER), api_key_id="key")
    result = await FeatureFlagService.upsert_flag(
        db,
        "flag",
        TENANT,
        True,
        75,
        "new",
        {"team": "platform"},
        USER,
        background,
        ctx,
    )
    assert result is existing
    assert existing.enabled and existing.rollout_percentage == 75
    assert existing.description == "new" and existing.metadata_ == {"team": "platform"}
    assert existing.updated_by == USER and db.flushes == 1 and db.added == []
    assert events[0][1]["user_id"] == str(USER) and events[0][1]["api_key_id"] == "key"
    assert background.calls and background.calls[0][1] is event


@pytest.mark.asyncio
async def test_upsert_creates_flag_and_preserves_existing_optional_fields(monkeypatch) -> None:
    monkeypatch.setattr(module, "emit_audit_event", lambda *_args, **_kwargs: object())
    db = DB([Result(scalar=None)])
    created = await FeatureFlagService.upsert_flag(db, "flag", None, False, 10, None, None, None)
    assert created in db.added and created.flag_key == "flag"
    assert created.metadata_ == {} and db.flushes == 1

    existing = SimpleNamespace(
        enabled=True,
        rollout_percentage=50,
        description="keep",
        metadata_={"keep": True},
        updated_by=USER,
    )
    db = DB([Result(scalar=existing)])
    await FeatureFlagService.upsert_flag(db, "flag", TENANT, False, 0, None, None, None)
    assert existing.description == "keep" and existing.metadata_ == {"keep": True}


@pytest.mark.asyncio
async def test_delete_missing_and_existing_with_audit(monkeypatch) -> None:
    flag = object()
    db = DB([Result(scalar=None), Result(scalar=flag)])
    monkeypatch.setattr(module, "emit_audit_event", lambda *_args, **_kwargs: object())
    assert not await FeatureFlagService.delete_flag(db, "missing", TENANT)
    assert await FeatureFlagService.delete_flag(db, "flag", TENANT)
    assert db.deleted == [flag] and db.flushes == 1


@pytest.mark.asyncio
async def test_evaluate_and_lookup_contracts(monkeypatch) -> None:
    calls = []

    async def enabled(*args):
        calls.append(args)
        return True

    monkeypatch.setattr(module, "is_enabled", enabled)
    assert await FeatureFlagService.evaluate_flag("flag", TENANT, "user")
    assert calls == [("flag", TENANT, "user")]

    flag = SimpleNamespace(enabled=True, rollout_percentage=25)
    db = DB([Result(scalar=flag), Result(scalar=None)])
    found = await FeatureFlagService.lookup_flag(db, "flag", TENANT)
    assert found.enabled is True and found.rollout_percentage == 25
    assert await FeatureFlagService.lookup_flag(db, "missing", TENANT) is None


@pytest.mark.asyncio
async def test_registered_lookup_prefers_tenant_then_platform(monkeypatch) -> None:
    tenant_db = DB([Result(scalar=SimpleNamespace(enabled=True, rollout_percentage=80))])
    platform_db = DB([Result(scalar=SimpleNamespace(enabled=False, rollout_percentage=0))])
    clears = []

    @asynccontextmanager
    async def tenant_session(_context):
        yield tenant_db

    class FactoryContext:
        async def __aenter__(self):
            return platform_db

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr("layer4_agents.database.db_session_for_context", tenant_session)
    monkeypatch.setattr(
        "layer4_agents.database.get_session_factory", lambda: lambda: FactoryContext()
    )
    monkeypatch.setattr(
        "layer4_agents.database._clear_local_tenant_context",
        lambda db: clears.append(db) or _completed(),
    )
    found = await module._lookup_flag("flag", TENANT)
    assert found.enabled is True and found.rollout_percentage == 80
    assert platform_db.queries == []

    tenant_db.results = [Result(scalar=None)]
    found = await module._lookup_flag("flag", TENANT)
    assert found.enabled is False and clears == [platform_db]

    platform_db.results = [Result(scalar=None)]
    assert await module._lookup_flag("missing", None) is None


async def _completed():
    return None


def test_init_registers_lookup_callback(monkeypatch) -> None:
    callbacks = []
    monkeypatch.setattr(module, "register_feature_flag_lookup", callbacks.append)
    module.init_feature_flag_lookup()
    assert callbacks == [module._lookup_flag]
