from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.retrieval.vector_store import Neo4jVectorStore


class _FakeResult:
    async def single(self):
        return {"entity_id": "entity-1", "upserted": True}


def _settings_stub() -> SimpleNamespace:
    return SimpleNamespace(
        neo4j_database="neo4j",
        neo4j_uri="bolt://localhost:7687",
        neo4j_auth=("neo4j", "test"),
        neo4j_max_pool_size=1,
    )


@pytest.mark.asyncio
async def test_upsert_entity_uses_explicit_tenant_and_strips_forged_metadata(monkeypatch):
    store = Neo4jVectorStore(driver=object(), settings=_settings_stub())
    captured = {}

    async def _fake_run_scoped(scoped):
        captured["scoped"] = scoped
        return _FakeResult()

    monkeypatch.setattr(store, "_run_scoped", _fake_run_scoped)
    monkeypatch.setattr(store, "_embed", lambda _: [0.1, 0.2])

    await store.upsert_entity(
        entity_id="entity-1",
        entity_type="Capability",
        text="Tenant-safe embedding",
        metadata={"tenant_id": "tenant-b", "tenantId": "tenant-b", "name": "x"},
        tenant_id="tenant-a",
    )

    scoped = captured["scoped"]
    assert scoped.tenant_id == "tenant-a"
    assert scoped.params["_tenant_id"] == "tenant-a"
    assert "tenant_id" not in scoped.params["metadata"]
    assert "tenantId" not in scoped.params["metadata"]


@pytest.mark.asyncio
async def test_upsert_entity_rejects_missing_explicit_tenant(monkeypatch):
    store = Neo4jVectorStore(driver=object(), settings=_settings_stub())
    monkeypatch.setattr(store, "_embed", lambda _: [0.1, 0.2])

    with pytest.raises(ValueError, match="tenant_id is required"):
        await store.upsert_entity(
            entity_id="entity-1",
            entity_type="Capability",
            text="Tenant-safe embedding",
            metadata={"tenant_id": "tenant-b"},
            tenant_id="",
        )


@pytest.mark.asyncio
async def test_hostile_metadata_override_cannot_cross_tenant(monkeypatch):
    store = Neo4jVectorStore(driver=object(), settings=_settings_stub())
    captured = {}

    async def _fake_run_scoped(scoped):
        captured["scoped"] = scoped
        return _FakeResult()

    monkeypatch.setattr(store, "_run_scoped", _fake_run_scoped)
    monkeypatch.setattr(store, "_embed_batch", lambda _: [[0.1, 0.2]])

    await store.upsert_batch(
        entities=[{"id": "entity-1", "text": "x", "tenant_id": "tenant-b", "name": "bad override"}],
        entity_type="Capability",
        tenant_id="tenant-a",
    )

    scoped = captured["scoped"]
    assert scoped.tenant_id == "tenant-a"
    assert scoped.params["_tenant_id"] == "tenant-a"
    assert "tenant_id" not in scoped.params["records"][0]["metadata"]
