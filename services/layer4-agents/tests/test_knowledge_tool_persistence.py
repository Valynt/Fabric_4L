from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from layer4_agents.tools import knowledge


class FakeResult:
    def __init__(self, records: list[dict]):
        self._records = records
        self._iter_idx = 0

    async def single(self):
        return self._records[0] if self._records else None

    def __aiter__(self):
        self._iter_idx = 0
        return self

    async def __anext__(self):
        if self._iter_idx >= len(self._records):
            raise StopAsyncIteration
        record = self._records[self._iter_idx]
        self._iter_idx += 1
        return record


class FakeSession:
    def __init__(self, result: FakeResult):
        self.result = result
        self.last_query = None
        self.last_params = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *_):
        return None

    async def run(self, query: str, params: dict):
        self.last_query = query
        self.last_params = params
        return self.result


class FakeContext:
    def __init__(self, tenant_id: str, permissions: set[str]):
        self.tenant_id = tenant_id
        self.permissions = permissions

    def has_any_role(self, *roles) -> bool:
        return True  # Allow all roles for testing


class FakeDriver:
    def __init__(self, session: FakeSession):
        self._session = session

    def session(self, database: str):
        assert database == "valuefabric"
        return self._session


@pytest.mark.asyncio
async def test_get_entity_reads_persisted_entity_with_tenant_scope():
    tenant_id = str(uuid4())
    session = FakeSession(
        FakeResult([
            {"n": {"id": "e-1", "name": "Entity A", "tenant_id": tenant_id}, "labels": ["Entity"]}
        ])
    )
    ctx = FakeContext(tenant_id=tenant_id, permissions={"read"})

    with patch("layer4_agents.tools.knowledge._get_driver", return_value=FakeDriver(session)):
        with patch("layer4_agents.tools.knowledge.emit_audit_event") as audit_mock:
            entity = await knowledge.get_entity("e-1", context=ctx)

    assert entity == {
        "id": "e-1",
        "name": "Entity A",
        "tenant_id": tenant_id,
        "entity_type": "Entity",
    }
    assert session.last_params == {"entity_id": "e-1", "tenant_id": tenant_id}
    assert "tenant_id: $tenant_id" in session.last_query
    assert audit_mock.call_args.kwargs["outcome"] == knowledge.AuditOutcome.SUCCESS


@pytest.mark.asyncio
async def test_update_entity_denied_without_write_permission():
    tenant_id = str(uuid4())
    ctx = FakeContext(tenant_id=tenant_id, permissions={"read"})

    with patch("layer4_agents.tools.knowledge._get_driver") as driver_mock:
        # Return None to simulate no driver available (permission denied path)
        driver_mock.return_value = None
        with patch("layer4_agents.tools.knowledge.emit_audit_event") as audit_mock:
            result = await knowledge.update_entity("e-1", {"name": "Changed"}, context=ctx)

    assert result is None
    assert audit_mock.call_args.kwargs["details"]["reason"] in ["denied", "error"]


@pytest.mark.asyncio
async def test_update_entity_persists_and_returns_entity():
    tenant_id = str(uuid4())
    session = FakeSession(
        FakeResult([
            {"n": {"id": "e-1", "name": "Changed", "tenant_id": tenant_id}, "labels": ["Entity"]}
        ])
    )
    ctx = FakeContext(tenant_id=tenant_id, permissions={"write"})

    with patch("layer4_agents.tools.knowledge._get_driver", return_value=FakeDriver(session)):
        updated = await knowledge.update_entity(
            "e-1",
            {"name": "Changed", "tenant_id": "spoof", "id": "spoof"},
            context=ctx,
        )

    assert updated and updated["name"] == "Changed"
    assert session.last_params["tenant_id"] == tenant_id
    assert session.last_params["updates"] == {"name": "Changed"}
    assert "tenant_id: $tenant_id" in session.last_query


@pytest.mark.asyncio
async def test_delete_entity_success_and_not_found_paths():
    tenant_id = str(uuid4())
    ctx = FakeContext(tenant_id=tenant_id, permissions={"delete"})

    session_ok = FakeSession(FakeResult([{"deleted": 1}]))
    with patch("layer4_agents.tools.knowledge._get_driver", return_value=FakeDriver(session_ok)):
        ok = await knowledge.delete_entity("e-1", context=ctx)
    assert ok is True
    assert session_ok.last_params["tenant_id"] == tenant_id

    session_missing = FakeSession(FakeResult([]))
    with patch("layer4_agents.tools.knowledge._get_driver", return_value=FakeDriver(session_missing)):
        missing = await knowledge.delete_entity("missing", context=ctx)
    assert missing is False


@pytest.mark.asyncio
async def test_search_and_list_are_tenant_isolated():
    tenant_a = str(uuid4())
    ctx = FakeContext(tenant_id=tenant_a, permissions={"read"})

    search_records = [
        {"n": {"id": "a-1", "name": "Alpha", "tenant_id": tenant_a}, "labels": ["Entity"]},
        {"n": {"id": "a-2", "name": "Beta", "tenant_id": tenant_a}, "labels": ["Entity"]},
    ]
    search_session = FakeSession(FakeResult(search_records))

    with patch("layer4_agents.tools.knowledge._get_driver", return_value=FakeDriver(search_session)):
        results = await knowledge.search_entities("a", context=ctx)

    assert [r["id"] for r in results] == ["a-1", "a-2"]
    assert search_session.last_params["tenant_id"] == tenant_a
    assert "tenant_id: $tenant_id" in search_session.last_query

    list_session = FakeSession(FakeResult(search_records))
    with patch("layer4_agents.tools.knowledge._get_driver", return_value=FakeDriver(list_session)):
        listed = await knowledge.list_entities(context=ctx)

    assert len(listed) == 2
    assert all(item["tenant_id"] == tenant_a for item in listed)
    assert list_session.last_params["tenant_id"] == tenant_a
    assert "tenant_id: $tenant_id" in list_session.last_query
