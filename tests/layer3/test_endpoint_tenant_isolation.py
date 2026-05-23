from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import pytest
from value_fabric.shared.identity import RequestContext

from value_fabric.layer3.api.dependencies_tenant import Neo4jTenantSession
from value_fabric.layer3.api.models import GraphRAGQuery, SearchRequest, SearchType
from value_fabric.layer3.api.routes import entities, query_search


class _FakeSession:
    async def run(self, query: str, params: dict):
        return SimpleNamespace(query=query, params=params)


class _FakeNeo4j:
    def __init__(self, tenant_id: str, store: dict[str, dict]):
        self.tenant_id = tenant_id
        self._store = store

    async def execute_query(self, query, params=None, **kwargs):
        params = dict(params or {})
        params.update(kwargs)
        tenant_id = self.tenant_id
        tenant_store = self._store[tenant_id]
        q = str(query)

        if "RETURN e.id as id" in q:
            return [
                {
                    "id": row["id"],
                    "name": row["name"],
                    "description": row.get("description"),
                    "entity_type": row.get("entity_type", "entity"),
                    "confidence_score": row.get("confidence_score", 1.0),
                    "created_at": row.get("created_at"),
                    "total": len(tenant_store["entities"]),
                }
                for row in tenant_store["entities"]
            ]

        if "RETURN e" in q:
            eid = params["entity_id"]
            for entity in tenant_store["entities"]:
                if entity["id"] == eid:
                    return [{"e": entity}]
            return []

        if "RETURN other.id as related_id" in q:
            return tenant_store["relationships"]

        if "RETURN source" in q:
            return [{"source": tenant_store["source"]}]

        return []


class _FakeGraphRAG:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def query(self, **kwargs):
        assert kwargs["tenant_id"] == self.tenant_id
        return {
            "query": kwargs["query_text"],
            "entities": [{"id": f"{self.tenant_id}-entity"}],
            "relationships": [{"id": f"{self.tenant_id}-rel"}],
            "context_graph": {"tenant_id": self.tenant_id},
            "confidence_score": 0.9,
            "sources": [{"id": f"{self.tenant_id}-source"}],
            "answer": f"answer-for-{self.tenant_id}",
        }


class _FakeHybridSearch:
    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id

    async def semantic_search(self, query, entity_type, top_k, tenant_id=None):
        assert tenant_id == self.tenant_id
        return [SimpleNamespace(id=f"{self.tenant_id}-vec", score=0.9, source="vector", metadata={"tenant_id": self.tenant_id})]

    async def fulltext_search(self, query, entity_type, top_k, tenant_id=None):
        assert tenant_id == self.tenant_id
        return [SimpleNamespace(id=f"{self.tenant_id}-full", score=0.8, source="fulltext", metadata={"tenant_id": self.tenant_id})]

    async def search(self, query, entity_types, top_k, weights, tenant_id=None):
        assert tenant_id == self.tenant_id
        return [SimpleNamespace(id=f"{self.tenant_id}-hybrid", score=0.95, source="hybrid", metadata={"tenant_id": self.tenant_id})]


@pytest.fixture
def tenant_store(tenant_a_id: UUID, tenant_b_id: UUID):
    return {
        str(tenant_a_id): {
            "entities": [{"id": "a-1", "name": "Tenant A Entity", "tenant_id": str(tenant_a_id), "entity_type": "company"}],
            "relationships": [{"related_id": "a-2", "related_name": "Tenant A Related", "related_type": "company", "relationship_type": "RELATED", "rel_confidence": 0.91}],
            "source": {"id": "a-source", "source_type": "doc", "extraction_method": "etl", "extracted_at": "2026-01-01T00:00:00Z", "confidence_score": 0.8},
        },
        str(tenant_b_id): {
            "entities": [{"id": "b-1", "name": "Tenant B Entity", "tenant_id": str(tenant_b_id), "entity_type": "company"}],
            "relationships": [{"related_id": "b-2", "related_name": "Tenant B Related", "related_type": "company", "relationship_type": "RELATED", "rel_confidence": 0.89}],
            "source": {"id": "b-source", "source_type": "doc", "extraction_method": "etl", "extracted_at": "2026-01-01T00:00:00Z", "confidence_score": 0.8},
        },
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("tenant_fixture,expected_prefix", [("tenant_a_id", "a-"), ("tenant_b_id", "b-")])
async def test_entity_list_and_detail_are_tenant_isolated(request, tenant_fixture, expected_prefix, tenant_store):
    tenant_id = str(request.getfixturevalue(tenant_fixture))
    neo4j = _FakeNeo4j(tenant_id=tenant_id, store=tenant_store)

    listed = await entities.list_entities(_ctx=None, neo4j=neo4j)
    assert listed.results
    assert all(entity.id.startswith(expected_prefix) for entity in listed.results)

    detail = await entities.get_entity_detail(entity_id=f"{expected_prefix}1", _ctx=None, neo4j=neo4j, app_state=None)
    assert detail.id.startswith(expected_prefix)
    assert all(rel["entity_id"].startswith(expected_prefix) for rel in detail.related_entities)


@pytest.mark.asyncio
@pytest.mark.parametrize("tenant_fixture", ["tenant_a_id", "tenant_b_id"])
async def test_graphrag_vector_and_hybrid_results_remain_tenant_scoped(request, tenant_fixture):
    tenant_id = str(request.getfixturevalue(tenant_fixture))

    ctx = RequestContext(tenant_id=tenant_id, user_id="u", roles=())
    graphrag = await query_search.graph_rag_query_impl(GraphRAGQuery(query="revenue"), _FakeGraphRAG(tenant_id), ctx=ctx)
    assert all(item["id"].startswith(tenant_id) for item in graphrag.entities)
    assert all(item["id"].startswith(tenant_id) for item in graphrag.relationships)

    vector = await query_search.hybrid_search_impl(SearchRequest(query="abc", search_type=SearchType.VECTOR), _FakeHybridSearch(tenant_id), ctx=ctx)
    hybrid = await query_search.hybrid_search_impl(SearchRequest(query="abc", search_type=SearchType.HYBRID), _FakeHybridSearch(tenant_id), ctx=ctx)

    assert all(result.id.startswith(tenant_id) for result in vector.results)
    assert all(result.id.startswith(tenant_id) for result in hybrid.results)


@pytest.mark.asyncio
async def test_raw_cypher_missing_tenant_predicate_fails_closed():
    session = Neo4jTenantSession(_FakeSession(), tenant_id="tenant-a")

    with pytest.raises(ValueError, match="tenant predicates"):
        await session.run("MATCH (e:Entity) RETURN e LIMIT 1")

    ok = await session.run("MATCH (e:Entity) WHERE e.tenant_id = $tenant_id RETURN e LIMIT 1")
    assert ok.params["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_graph_rag_query_missing_tenant_context_fails_closed():
    with pytest.raises(Exception):
        await query_search.graph_rag_query_impl(GraphRAGQuery(query="revenue"), _FakeGraphRAG("tenant-a"), ctx=None)


@pytest.mark.asyncio
async def test_hybrid_search_missing_tenant_context_fails_closed():
    with pytest.raises(Exception):
        await query_search.hybrid_search_impl(
            SearchRequest(query="abc", search_type=SearchType.HYBRID),
            _FakeHybridSearch("tenant-a"),
            ctx=None,
        )
