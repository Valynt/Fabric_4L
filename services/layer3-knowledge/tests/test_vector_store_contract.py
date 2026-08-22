"""Contract and isolation tests for Neo4jVectorStore."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.retrieval.vector_store import (
    Neo4jVectorStore,
    VectorStoreError,
    VECTOR_ENTITY_TYPES,
)


@pytest.mark.unit
def test_clean_entity_metadata_removes_tenant_ids_and_non_primitives():
    """Verify tenant_id, tenantId, and complex objects are stripped from metadata."""
    meta = {
        "tenant_id": "tenant-override",
        "tenantId": "tenant-camel",
        "name": "Predictive Maintenance",
        "confidence": 0.95,
        "count": 10,
        "is_active": True,
        "nested_dict": {"foo": "bar"},
        "tags": ["a", "b"],
    }
    cleaned = Neo4jVectorStore._clean_entity_metadata(meta)
    assert cleaned == {
        "name": "Predictive Maintenance",
        "confidence": 0.95,
        "count": 10,
        "is_active": True,
    }


@pytest.mark.unit
def test_format_search_record():
    """Verify search record format produces expected (id, score, meta) tuple."""
    record = {
        "entity_id": "cap-123",
        "score": 0.88,
        "entity_type": "Capability",
        "name": "Smart Inventory",
        "description": "Real-time tracking",
        "confidence": 0.9,
    }
    formatted = Neo4jVectorStore._format_search_record(record)
    assert formatted == (
        "cap-123",
        0.88,
        {
            "entity_type": "Capability",
            "name": "Smart Inventory",
            "description": "Real-time tracking",
            "confidence": 0.9,
        },
    )


@pytest.mark.unit
def test_resolve_tenant_id_fail_closed():
    """Verify vector store operations fail closed when tenant_id is missing."""
    store = Neo4jVectorStore()
    with pytest.raises(ValueError, match="tenant_id is required"):
        store._resolve_tenant_id(None)


@pytest.mark.asyncio
async def test_search_tenant_isolation_scoping():
    """Verify search builds tenant-scoped Cypher queries for each entity type."""
    store = Neo4jVectorStore()
    store._embed = MagicMock(return_value=[0.1] * 384)
    
    mock_records = [
        {
            "entity_id": "cap-1",
            "entity_type": "Capability",
            "score": 0.95,
            "name": "Cap 1",
            "description": "Desc 1",
            "confidence": 1.0,
        }
    ]
    store._run_scoped_list = AsyncMock(return_value=mock_records)

    results = await store.search(
        query_text="inventory management",
        entity_type="Capability",
        top_k=5,
        tenant_id="tenant-secure-123",
    )

    assert len(results) == 1
    assert results[0][0] == "cap-1"
    assert results[0][1] == 0.95
    assert results[0][2]["entity_type"] == "Capability"

    # Verify scoped query was passed to executor with tenant id
    store._run_scoped_list.assert_awaited_once()
    scoped = store._run_scoped_list.call_args[0][0]
    assert scoped.tenant_id == "tenant-secure-123"
    assert "WHERE node.tenant_id = $_tenant_id" in scoped.cypher


@pytest.mark.asyncio
async def test_delete_entity_requires_tenant():
    """Verify delete_entity fails closed when tenant_id is missing or empty."""
    store = Neo4jVectorStore()
    with pytest.raises(ValueError, match="tenant_id is required"):
        await store.delete_entity("ent-1", tenant_id="")


@pytest.mark.asyncio
async def test_upsert_entity_invalid_type_raises():
    """Verify upserting an entity with unsupported type raises VectorStoreError."""
    store = Neo4jVectorStore()
    with pytest.raises(VectorStoreError, match="Unknown entity type"):
        await store.upsert_entity(
            entity_id="x",
            entity_type="InvalidType",
            text="hello",
            tenant_id="tenant-123",
        )
