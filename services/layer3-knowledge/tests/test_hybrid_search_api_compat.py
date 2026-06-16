"""Regression tests for HybridSearch API compatibility."""

import pytest

from src.config import Settings
from src.retrieval.hybrid_search import HybridSearch


@pytest.mark.asyncio
async def test_search_positional_weights_remain_compatible() -> None:
    """search(query, entity_types, top_k, weights) must remain valid."""
    settings = Settings(neo4j_password="test_password")
    engine = HybridSearch(settings=settings)

    requested_limits: list[int] = []

    async def fake_bm25(query, entity_types, top_k, tenant_id=None):
        assert tenant_id == "tenant-test"
        requested_limits.append(top_k)
        return []

    async def fake_vector(query, entity_types, top_k, tenant_id=None):
        requested_limits.append(top_k)
        return []

    async def fake_graph(query, entity_types, top_k, tenant_id=None):
        requested_limits.append(top_k)
        return []

    def fake_merge(_bm25, _vector, _graph, normalized_weights):
        assert normalized_weights["bm25"] == pytest.approx(0.25)
        assert normalized_weights["vector"] == pytest.approx(0.25)
        assert normalized_weights["graph"] == pytest.approx(0.5)
        return ["r1", "r2", "r3", "r4"]

    engine._bm25_search = fake_bm25
    engine._vector_search = fake_vector
    engine._graph_search = fake_graph
    engine._merge_results = fake_merge

    result = await engine.search(
        "predictive maintenance",
        ["Capability"],
        3,
        {"bm25": 1.0, "vector": 1.0, "graph": 2.0},
        tenant_id="tenant-test",
    )

    assert requested_limits == [6, 6, 6]
    assert result == ["r1", "r2", "r3"]


@pytest.mark.asyncio
async def test_search_limit_alias_overrides_top_k() -> None:
    """limit should override top_k while preserving search behavior."""
    settings = Settings(neo4j_password="test_password")
    engine = HybridSearch(settings=settings)

    requested_limits: list[int] = []

    async def fake_search_component(query, entity_types, top_k, tenant_id=None):
        requested_limits.append(top_k)
        return []

    def fake_merge(_bm25, _vector, _graph, _weights):
        return ["r1", "r2", "r3"]

    engine._bm25_search = fake_search_component
    engine._vector_search = fake_search_component
    engine._graph_search = fake_search_component
    engine._merge_results = fake_merge

    result = await engine.search(
        query="predictive maintenance",
        top_k=5,
        limit=2,
        tenant_id="tenant-test",
    )

    assert requested_limits == [4, 4, 4]
    assert result == ["r1", "r2"]


@pytest.mark.asyncio
async def test_graph_search_marks_internal_fulltext_query_with_narrow_allowlist() -> None:
    """Hybrid graph search should keep tenant scope and reviewed query metadata."""
    settings = Settings(neo4j_password="test_password")
    engine = HybridSearch(settings=settings)
    captured = []

    class _Result:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise StopAsyncIteration

    class _Session:
        async def __aenter__(self):
            return self

        async def __aexit__(self, exc_type, exc, tb):
            return False

    class _Driver:
        def session(self, **_kwargs):
            return _Session()

    async def fake_get_driver():
        return _Driver()

    async def fake_run_scoped(_session, scoped):
        captured.append(scoped)
        return _Result()

    engine._get_driver = fake_get_driver
    engine._run_scoped = fake_run_scoped

    await engine._graph_search(
        query="se hours",
        entity_types=["ValueDriver"],
        top_k=3,
        tenant_id="tenant-a",
    )

    assert len(captured) == 1
    scoped = captured[0]
    assert scoped.operation == "hybrid_search.graph"
    assert scoped.allowlist_key == "hybrid_search.graph_fulltext_tenant_scoped"
    assert scoped.tenant_id == "tenant-a"
    assert "node.tenant_id = $_tenant_id" in scoped.cypher

