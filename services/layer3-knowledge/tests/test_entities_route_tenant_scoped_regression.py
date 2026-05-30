from unittest.mock import MagicMock

import pytest

from api.routes.entities import list_entities, query_entities
from api.models import EntityFilterRequest


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
