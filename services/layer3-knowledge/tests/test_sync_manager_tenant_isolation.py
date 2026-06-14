from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from src.ingestion.sync_manager import SyncManager


TENANT_A = "11111111-1111-4111-8111-111111111111"
TENANT_B = "22222222-2222-4222-8222-222222222222"


class _FakeResult:
    def __init__(self, records):
        self._records = records

    async def single(self):
        return self._records[0] if self._records else None

    def __aiter__(self):
        async def gen():
            for record in self._records:
                yield record

        return gen()


class _FakeSession:
    def __init__(self, records_by_tenant):
        self.records_by_tenant = records_by_tenant

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, query, params=None):
        tenant_id = (params or {}).get("tenant_id")
        source_id = (params or {}).get("source_id")
        records = self.records_by_tenant.get(tenant_id, [])
        if source_id:
            records = [r for r in records if r["s"]["source_id"] == source_id]
        return _FakeResult(records)


class _FakeDriver:
    def __init__(self, records_by_tenant):
        self.records_by_tenant = records_by_tenant

    def session(self, database=None):
        return _FakeSession(self.records_by_tenant)


@pytest.mark.asyncio
async def test_sync_status_is_tenant_scoped_for_same_source_id():
    records = {
        TENANT_A: [{"s": {"source_id": "shared-source", "tenant_id": TENANT_A, "status": "success", "synced_at": "2026-01-01T00:00:00Z"}}],
        TENANT_B: [{"s": {"source_id": "shared-source", "tenant_id": TENANT_B, "status": "failed", "synced_at": "2026-01-02T00:00:00Z"}}],
    }
    loader = SimpleNamespace(_get_driver=AsyncMock(return_value=_FakeDriver(records)))
    manager = SyncManager(loader=loader, settings=SimpleNamespace(neo4j_database="neo4j"))

    tenant_a = await manager.get_sync_status("shared-source", tenant_id=TENANT_A)
    tenant_b = await manager.get_sync_status("shared-source", tenant_id=TENANT_B)

    assert tenant_a["tenant_id"] == TENANT_A
    assert tenant_b["tenant_id"] == TENANT_B
    assert tenant_a["status"] != tenant_b["status"]


@pytest.mark.asyncio
async def test_list_synced_sources_is_tenant_scoped_for_same_source_id_history():
    records = {
        TENANT_A: [{"s": {"source_id": "shared-source", "tenant_id": TENANT_A, "status": "success", "synced_at": "2026-01-01T00:00:00Z"}}],
        TENANT_B: [{"s": {"source_id": "shared-source", "tenant_id": TENANT_B, "status": "success", "synced_at": "2026-01-03T00:00:00Z"}}],
    }
    loader = SimpleNamespace(_get_driver=AsyncMock(return_value=_FakeDriver(records)))
    manager = SyncManager(loader=loader, settings=SimpleNamespace(neo4j_database="neo4j"))

    sources_a = await manager.list_synced_sources(tenant_id=TENANT_A)
    sources_b = await manager.list_synced_sources(tenant_id=TENANT_B)

    assert len(sources_a) == 1 and len(sources_b) == 1
    assert sources_a[0]["tenant_id"] == TENANT_A
    assert sources_b[0]["tenant_id"] == TENANT_B


@pytest.mark.asyncio
async def test_sync_methods_require_tenant_context():
    loader = SimpleNamespace(_get_driver=AsyncMock())
    manager = SyncManager(loader=loader, settings=SimpleNamespace(neo4j_database="neo4j"))

    with pytest.raises(ValueError, match="tenant_id is required"):
        await manager.get_sync_status("source-1", tenant_id=None)
    with pytest.raises(ValueError, match="tenant_id is required"):
        await manager.list_synced_sources(tenant_id=None)
