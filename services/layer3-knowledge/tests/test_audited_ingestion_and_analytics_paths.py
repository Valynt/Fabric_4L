from __future__ import annotations

from types import SimpleNamespace

import pytest

from src.api.routes.analytics import _create_entity
from src.db.audited_mutation import AuditedGraphMutation
from src.ingestion.neo4j import Neo4jLoader, TenantValidationError
from src.ingestion.sync_manager import SyncManager

TENANT_ID = "11111111-1111-4111-8111-111111111111"


class _FakeResult:
    def __init__(self, record=None):
        self._record = record or {"loaded": 1, "deleted": 1, "entity_id": "entity-1"}

    async def single(self):
        return self._record

    def __aiter__(self):
        async def gen():
            if self._record is not None:
                yield self._record

        return gen()


class _RecordingSession:
    def __init__(self):
        self.calls: list[tuple[str, dict]] = []

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def run(self, query, params=None):
        self.calls.append((query, params or {}))
        return _FakeResult()


class _FakeDriver:
    def __init__(self, session: _RecordingSession):
        self.session_obj = session

    def session(self, database=None):
        return self.session_obj


@pytest.mark.asyncio
async def test_analytics_entity_create_emits_audit_metadata_and_requires_tenant():
    session = _RecordingSession()
    driver = _FakeDriver(session)
    operation = SimpleNamespace(
        entity_type=None, properties={"name": "Created by test"}
    )

    missing_tenant = await _create_entity(driver, operation, tenant_id=None)
    assert missing_tenant["success"] is False
    assert "tenant_id is required" in missing_tenant["error"]
    assert session.calls == []

    result = await _create_entity(driver, operation, tenant_id=TENANT_ID)

    assert result["success"] is True
    audit_calls = [call for call in session.calls if "CREATE (a:AuditEvent" in call[0]]
    assert audit_calls
    audit_params = audit_calls[-1][1]
    assert audit_params["tenant_id"] == TENANT_ID
    assert audit_params["action"] == "WRITE_NODE"
    assert audit_params["operation_source"] == "analytics._create_entity"


@pytest.mark.asyncio
async def test_sync_metadata_write_emits_audit_metadata_and_requires_tenant():
    session = _RecordingSession()
    loader = SimpleNamespace(_get_driver=lambda: None)

    async def _get_driver():
        return _FakeDriver(session)

    loader._get_driver = _get_driver
    manager = SyncManager(
        loader=loader, settings=SimpleNamespace(neo4j_database="neo4j")
    )

    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        await manager._update_sync_metadata(
            "source-1",
            "job-1",
            "hash-1",
            "success",
            tenant_id=None,
        )

    await manager._update_sync_metadata(
        "source-1",
        "job-1",
        "hash-1",
        "success",
        tenant_id=TENANT_ID,
    )

    audit_calls = [call for call in session.calls if "CREATE (a:AuditEvent" in call[0]]
    assert audit_calls
    audit_params = audit_calls[-1][1]
    assert audit_params["tenant_id"] == TENANT_ID
    assert audit_params["action"] == "WRITE_NODE"
    assert audit_params["entity_id"].startswith("SyncMetadata:")
    assert audit_params["operation_source"] == "sync_manager._update_sync_metadata"


@pytest.mark.asyncio
async def test_native_relationship_loader_uses_audited_relationship_writes_and_requires_tenant():
    session = _RecordingSession()
    loader = Neo4jLoader(
        driver=_FakeDriver(session),
        settings=SimpleNamespace(neo4j_database="neo4j", use_apoc=False),
    )
    relationships = [
        {
            "source_id": "capability-1",
            "target_id": "usecase-1",
            "predicate": "enables",
            "confidence": 0.91,
            "raw_predicate": "enables",
        }
    ]

    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        await loader._load_relationships_native(
            session,
            relationships,
            "source-doc-1",
            "job-1",
            tenant_id=None,
        )

    loaded = await loader._load_relationships_native(
        session,
        relationships,
        "source-doc-1",
        "job-1",
        tenant_id=TENANT_ID,
    )

    assert loaded == 1
    merge_calls = [
        call for call in session.calls if "MERGE (src)-[r:enables]->(tgt)" in call[0]
    ]
    assert merge_calls
    merge_params = merge_calls[-1][1]
    assert merge_params["tenant_id"] == TENANT_ID
    assert merge_params["properties"]["confidence"] == 0.91

    audit_calls = [call for call in session.calls if "CREATE (a:AuditEvent" in call[0]]
    assert audit_calls
    audit_params = audit_calls[-1][1]
    assert audit_params["tenant_id"] == TENANT_ID
    assert audit_params["action"] == "WRITE_RELATIONSHIP"
    assert audit_params["operation_source"] == "neo4j_loader._load_relationships_native"


def test_audited_graph_mutation_rejects_missing_tenant_context():
    with pytest.raises(ValueError, match="tenant_id is required"):
        AuditedGraphMutation(tenant_id="", session=object())


@pytest.mark.asyncio
async def test_sync_metadata_delete_uses_validated_write_and_explicit_audit():
    session = _RecordingSession()

    class _Loader:
        async def _get_driver(self):
            return _FakeDriver(session)

        async def delete_by_source(self, source_id, tenant_id=None):
            assert tenant_id == TENANT_ID
            return {"relationships_deleted": 0, "entities_deleted": 0}

    manager = SyncManager(
        loader=_Loader(), settings=SimpleNamespace(neo4j_database="neo4j")
    )

    with pytest.raises(TenantValidationError, match="tenant_id is required"):
        await manager.delete_source("source-1", tenant_id=None)

    result = await manager.delete_source("source-1", tenant_id=TENANT_ID)

    assert result["sync_metadata_deleted"] is True
    delete_calls = [call for call in session.calls if "DELETE s" in call[0]]
    assert delete_calls
    assert delete_calls[-1][1]["tenant_id"] == TENANT_ID

    audit_calls = [call for call in session.calls if "CREATE (a:AuditEvent" in call[0]]
    assert audit_calls
    audit_params = audit_calls[-1][1]
    assert audit_params["tenant_id"] == TENANT_ID
    assert audit_params["action"] == "DELETE_SYNC_METADATA"
    assert audit_params["operation_source"] == "sync_manager.delete_source"
