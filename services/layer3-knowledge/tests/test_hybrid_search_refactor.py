"""Characterization and tenant boundary tests for HybridSearch refactor."""

from unittest.mock import AsyncMock, MagicMock
import pytest

from src.retrieval.hybrid_search import HybridSearch


@pytest.mark.unit
def test_normalize_vector_item_tuple():
    """Verify tuple format from vector store is correctly adapted to dictionary."""
    meta = {
        "entity_type": "Capability",
        "name": "Predictive Maintenance",
        "description": "AI maintenance system",
        "tenant_id": "tenant-alpha",
    }
    raw_tuple = ("cap-123", 0.95, meta)
    res = HybridSearch._normalize_vector_item(raw_tuple)
    assert res["id"] == "cap-123"
    assert res["entity_id"] == "cap-123"
    assert res["score"] == 0.95
    assert res["entity_type"] == "Capability"
    assert res["name"] == "Predictive Maintenance"
    assert res["description"] == "AI maintenance system"
    assert res["metadata"] == meta


@pytest.mark.unit
def test_normalize_vector_item_dict():
    """Verify legacy dictionary format is properly normalized."""
    raw_dict = {
        "entity_id": "cap-456",
        "score": 0.82,
        "entity_type": "UseCase",
        "name": "Supply Chain",
    }
    res = HybridSearch._normalize_vector_item(raw_dict)
    assert res["id"] == "cap-456"
    assert res["score"] == 0.82


@pytest.mark.unit
def test_merge_results_deterministic_normalization():
    """Verify deterministic normalization and weighting of multimodal signals."""
    searcher = HybridSearch()
    weights = {"bm25": 0.2, "vector": 0.5, "graph": 0.3}

    bm25_results = [
        {"id": "node-1", "score": 10.0, "name": "Node 1", "entity_type": "Capability"},
        {"id": "node-2", "score": 5.0, "name": "Node 2", "entity_type": "Capability"},
    ]
    vector_results = [
        {"id": "node-1", "score": 0.8, "name": "Node 1", "entity_type": "Capability"},
        {"id": "node-3", "score": 0.4, "name": "Node 3", "entity_type": "UseCase"},
    ]
    graph_results = [
        {"id": "node-2", "score": 2.0, "name": "Node 2", "entity_type": "Capability"},
    ]

    merged = searcher._merge_results(bm25_results, vector_results, graph_results, weights)

    assert len(merged) == 3
    # node-1 bm25 norm: 10/10 = 1.0 -> 0.2*1.0 = 0.2; vector norm: 0.8/0.8 = 1.0 -> 0.5*1.0 = 0.5; graph: 0 -> total = 0.7
    # node-2 bm25 norm: 5/10 = 0.5 -> 0.2*0.5 = 0.1; vector: 0; graph norm: 2.0/2.0 = 1.0 -> 0.3*1.0 = 0.3 -> total = 0.4
    # node-3 bm25: 0; vector norm: 0.4/0.8 = 0.5 -> 0.5*0.5 = 0.25; graph: 0 -> total = 0.25
    ids = [item.entity_id for item in merged]
    assert ids == ["node-1", "node-2", "node-3"]
    assert pytest.approx(merged[0].combined_score, 0.001) == 0.70
    assert pytest.approx(merged[1].combined_score, 0.001) == 0.40
    assert pytest.approx(merged[2].combined_score, 0.001) == 0.25


@pytest.mark.unit
def test_tenant_builder_resolution():
    """Verify tenant isolation resolution during search calls."""
    searcher = HybridSearch()

    builder = searcher._tenant_builder("override-tenant")
    assert builder.tenant_id == "override-tenant"

    # Fails closed if no context and no tenant_id provided
    with pytest.raises(ValueError, match="tenant_id is required"):
        searcher._tenant_builder(None)


@pytest.mark.asyncio
async def test_execute_bm25_for_type_handles_exceptions():
    """Verify _execute_bm25_for_type catches errors and returns empty list safely."""
    searcher = HybridSearch()
    mock_session = MagicMock()
    mock_builder = searcher._tenant_builder("test-tenant")
    searcher._run_scoped = AsyncMock(side_effect=RuntimeError("Neo4j down"))

    res = await searcher._execute_bm25_for_type(
        session=mock_session,
        builder=mock_builder,
        escaped_query="test",
        etype="Capability",
        top_k=5,
    )
    assert res == []


@pytest.mark.asyncio
async def test_execute_graph_for_type_handles_exceptions():
    """Verify _execute_graph_for_type catches errors and returns empty list safely."""
    searcher = HybridSearch()
    mock_session = MagicMock()
    mock_builder = searcher._tenant_builder("test-tenant")
    searcher._run_scoped = AsyncMock(side_effect=RuntimeError("Graph traversal error"))

    res = await searcher._execute_graph_for_type(
        session=mock_session,
        builder=mock_builder,
        escaped_query="test",
        etype="Capability",
        top_k=5,
    )
    assert res == []

