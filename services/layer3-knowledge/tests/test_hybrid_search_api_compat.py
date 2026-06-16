"""Regression tests for HybridSearch API compatibility."""

from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.config import Settings
from src.retrieval.hybrid_search import HybridSearch
from src.retrieval.vector_store import Neo4jVectorStore


class _FakeArray:
    def __init__(self, values: list[float]) -> None:
        self._values = values

    def tolist(self) -> list[float]:
        return self._values


class _FakeEmbeddingModel:
    def __init__(self, dim: int = 384) -> None:
        self._dim = dim

    def encode(self, text: str, normalize_embeddings: bool = True, batch_size: int | None = None) -> _FakeArray:
        return _FakeArray([0.1] * self._dim)


class _FakeRecord:
    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getitem__(self, key: str) -> Any:
        return self._data[key]

    def keys(self) -> list[str]:
        return list(self._data.keys())

    def values(self) -> list[Any]:
        return list(self._data.values())

    def items(self) -> list[tuple[str, Any]]:
        return list(self._data.items())


class _FakeResult:
    def __init__(self, records: list[_FakeRecord]) -> None:
        self._records = records

    def __aiter__(self) -> "_FakeResult":
        self._iter = iter(self._records)
        return self

    async def __anext__(self) -> _FakeRecord:
        try:
            return next(self._iter)
        except StopIteration:
            raise StopAsyncIteration

    async def single(self) -> _FakeRecord | None:
        return self._records[0] if self._records else None


class _AsyncContextManagerMock:
    def __init__(self, enter_value: Any) -> None:
        self._enter_value = enter_value

    async def __aenter__(self) -> Any:
        return self._enter_value

    async def __aexit__(self, *args: Any) -> None:
        pass


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
async def test_hybrid_search_vector_and_graph_paths_no_validation_errors(monkeypatch: pytest.MonkeyPatch) -> None:
    """Vector and graph search code paths execute without tenant-validation or result-consumption errors.

    Regression coverage for:
      - Neo4jVectorStore returning/consuming records inside the session.
      - HybridSearch._graph_search using run_validated_query with multi-clause allowlist
        and modern CALL () { ... } subquery syntax.
    """
    settings = Settings(neo4j_password="test_password", embedding_dimension=384)
    tenant = "tenant-test"

    vector_record = _FakeRecord({
        "entity_id": "cap-1",
        "entity_type": "Capability",
        "score": 0.92,
        "name": "AI Ops",
        "description": "AI-driven operations",
        "confidence": 0.95,
    })
    graph_record = _FakeRecord({
        "id": "cap-1",
        "entity_type": "Capability",
        "name": "AI Ops",
        "score": 0.85,
    })
    bm25_record = _FakeRecord({
        "id": "cap-1",
        "entity_type": "Capability",
        "name": "AI Ops",
        "description": "AI-driven operations",
        "score": 0.78,
    })

    call_count = 0

    async def fake_run(query: str, params: dict[str, Any]) -> _FakeResult:
        nonlocal call_count
        call_count += 1
        if "db.index.vector.queryNodes" in query:
            return _FakeResult([vector_record])
        if "CALL () {" in query:
            return _FakeResult([graph_record])
        if "db.index.fulltext.queryNodes" in query:
            return _FakeResult([bm25_record])
        return _FakeResult([])

    fake_session = AsyncMock()
    fake_session.run = fake_run
    fake_driver = AsyncMock()
    fake_driver.session = MagicMock(return_value=_AsyncContextManagerMock(fake_session))

    vector_store = Neo4jVectorStore(driver=fake_driver, settings=settings)
    monkeypatch.setattr(vector_store, "_get_embedding_model", lambda: _FakeEmbeddingModel(dim=384))

    hybrid = HybridSearch(driver=fake_driver, vector_store=vector_store, settings=settings)
    results = await hybrid.search("ai ops", ["Capability"], top_k=5, tenant_id=tenant)

    assert len(results) == 1
    assert results[0].entity_id == "cap-1"
    assert results[0].entity_type == "Capability"
    assert results[0].vector_score > 0
    assert results[0].graph_score > 0
    assert results[0].bm25_score > 0
    assert results[0].combined_score > 0
    # Ensure all three search components were exercised.
    assert call_count >= 3
