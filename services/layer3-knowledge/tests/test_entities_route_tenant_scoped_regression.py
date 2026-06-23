from unittest.mock import MagicMock

import pytest

from src.api.models import EntityFilterRequest
from src.api.routes.entities import (
    get_entity_context_route,
    list_entities,
    query_entities,
)


class _Neo4jCapture:
    def __init__(self):
        self.tenant_id = "tenant-a"
        self.calls = []

    async def execute_query(self, query, params=None, **kwargs):
        self.calls.append((query, params or {}, kwargs))
        return [
            {
                "total": 2,
                "id": "e1",
                "name": "Test Entity",
                "description": "",
                "entity_type": "Capability",
                "confidence_score": 0.8,
                "created_at": "2024-01-01",
            }
        ]


@pytest.mark.asyncio
async def test_list_entities_combined_filters_keep_tenant_predicate():
    neo4j = _Neo4jCapture()

    await list_entities(
        search_text="edge",
        entity_types=["Capability", "UseCase"],
        confidence_min=0.7,
        limit=10,
        offset=0,
        sort_by="name",
        sort_order="asc",
        _ctx=MagicMock(),
        neo4j=neo4j,
    )

    scoped_query, params, _ = neo4j.calls[0]
    assert "MATCH (e:Entity)" in scoped_query.cypher
    assert "e.tenant_id = $_tenant_id" in scoped_query.cypher
    assert "e.entity_type IN $entity_types" in scoped_query.cypher
    assert "e.confidence_score >= $confidence_min" in scoped_query.cypher
    assert "search_text" in params


@pytest.mark.asyncio
async def test_query_entities_filter_combinations_keep_tenant_predicate():
    neo4j = _Neo4jCapture()

    await query_entities(
        request=EntityFilterRequest(
            entity_types=["Capability"],
            min_confidence=0.2,
            max_confidence=0.8,
            limit=5,
            offset=0,
        ),
        _ctx=MagicMock(),
        neo4j=neo4j,
    )

    count_query, count_params, _ = neo4j.calls[0]
    list_query, list_params, _ = neo4j.calls[1]
    assert "e.tenant_id = $_tenant_id" in count_query.cypher
    assert "e.tenant_id = $_tenant_id" in list_query.cypher
    assert count_params["entity_types"] == ["Capability"]
    assert list_params["confidence_max"] == 0.8


class _Neo4jContextCapture:
    def __init__(self, records=None):
        self.tenant_id = "tenant-a"
        self.calls = []
        self.records = records or []

    async def execute_query(self, query, params=None, **kwargs):
        self.calls.append((query, params or {}, kwargs))
        return self.records


def _make_relationship(start_id: str, end_id: str, rel_type: str = "ENABLES"):
    return {
        "start_node": {"id": start_id},
        "end_node": {"id": end_id},
        "type": rel_type,
        "confidence": 0.85,
    }


@pytest.mark.asyncio
async def test_get_entity_context_uses_tenant_scoped_cypher_and_entity_labels():
    neo4j = _Neo4jContextCapture(records=[{
        "center": {"id": "e1", "name": "Center", "entity_type": "Capability", "confidence_score": 0.9},
        "neighbors": [],
        "all_rels": [],
    }])

    response = await get_entity_context_route(
        entity_id="e1",
        hops=2,
        min_confidence=0.5,
        _ctx=MagicMock(),
        neo4j=neo4j,
    )

    assert response.entity_id == "e1"
    scoped_query, params, _ = neo4j.calls[0]
    cypher = scoped_query.cypher
    assert "(center:Entity)" in cypher
    assert "(connected:Entity)" in cypher
    assert "center.id = $entity_id" in cypher
    assert "node.tenant_id = $_tenant_id" in cypher
    assert "node.confidence_score >= $min_confidence" in cypher
    assert "[*1..2]" in cypher
    assert params["entity_id"] == "e1"
    assert params["min_confidence"] == 0.5


@pytest.mark.asyncio
async def test_get_entity_context_hop_allowlist():
    for hops, expected in [(1, "[*1..1]"), (2, "[*1..2]"), (3, "[*1..3]")]:
        neo4j = _Neo4jContextCapture(records=[{
            "center": {"id": "e1", "name": "Center", "entity_type": "Capability", "confidence_score": 0.9},
            "neighbors": [],
            "all_rels": [],
        }])
        await get_entity_context_route(
            entity_id="e1",
            hops=hops,
            min_confidence=0.0,
            _ctx=MagicMock(),
            neo4j=neo4j,
        )
        assert expected in neo4j.calls[0][0].cypher


@pytest.mark.asyncio
async def test_get_entity_context_relationship_types_are_parameterized():
    neo4j = _Neo4jContextCapture(records=[{
        "center": {"id": "e1", "name": "Center", "entity_type": "Capability", "confidence_score": 0.9},
        "neighbors": [],
        "all_rels": [],
    }])

    await get_entity_context_route(
        entity_id="e1",
        hops=2,
        relationship_types=["ENABLES", "DEPENDS_ON"],
        _ctx=MagicMock(),
        neo4j=neo4j,
    )

    scoped_query, params, _ = neo4j.calls[0]
    assert "type(r) IN $relationship_types" in scoped_query.cypher
    assert params["relationship_types"] == ["ENABLES", "DEPENDS_ON"]


@pytest.mark.asyncio
async def test_get_entity_context_returns_neighbors_and_relationships():
    center = {"id": "e1", "name": "Center", "entity_type": "Capability", "confidence_score": 0.9}
    neighbor = {"id": "e2", "name": "Neighbor", "entity_type": "Product", "confidence_score": 0.8}
    neo4j = _Neo4jContextCapture(records=[{
        "center": center,
        "neighbors": [neighbor],
        "all_rels": [[_make_relationship("e1", "e2", "ENABLES")]],
    }])

    response = await get_entity_context_route(
        entity_id="e1",
        hops=2,
        _ctx=MagicMock(),
        neo4j=neo4j,
    )

    assert response.center["id"] == "e1"
    assert len(response.neighbors) == 1
    assert response.neighbors[0]["id"] == "e2"
    assert response.entity_count == 2
    assert response.relationship_count == 1
    assert response.pagination is not None
    assert response.pagination["returned_count"] == 1


@pytest.mark.asyncio
async def test_get_entity_context_not_found_when_no_records():
    neo4j = _Neo4jContextCapture(records=[])
    from value_fabric.shared.error_handling.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await get_entity_context_route(
            entity_id="missing",
            hops=2,
            _ctx=MagicMock(),
            neo4j=neo4j,
        )


@pytest.mark.asyncio
async def test_get_entity_context_not_found_when_center_missing():
    neo4j = _Neo4jContextCapture(records=[{"center": None, "neighbors": [], "all_rels": []}])
    from value_fabric.shared.error_handling.exceptions import NotFoundError

    with pytest.raises(NotFoundError):
        await get_entity_context_route(
            entity_id="missing",
            hops=2,
            _ctx=MagicMock(),
            neo4j=neo4j,
        )
