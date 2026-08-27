"""Tests for retrieval components."""

import pytest


@pytest.mark.asyncio
async def test_graphrag_result_structure():
    """Test GraphRAG result dataclass."""
    from src.retrieval.graph_rag import GraphRAGResult

    result = GraphRAGResult(
        query="test query",
        entities=[{"id": "1", "name": "Entity"}],
        relationships=[],
        context_graph={"node_count": 1},
        traversal_path=["path1"],
        confidence_score=0.8,
        sources=["source1"],
    )

    assert result.query == "test query"
    assert len(result.entities) == 1
    assert result.confidence_score == 0.8


@pytest.mark.asyncio
async def test_hybrid_search_result():
    """Test hybrid search result dataclass."""
    from src.retrieval.hybrid_search import HybridSearchResult

    result = HybridSearchResult(
        entity_id="ent-1",
        entity_type="Capability",
        name="Test Entity",
        bm25_score=0.3,
        vector_score=0.5,
        graph_score=0.2,
        combined_score=0.4,
        metadata={},
    )

    assert result.entity_type == "Capability"
    assert result.combined_score == 0.4


@pytest.mark.asyncio
async def test_vector_store_error():
    """Test vector store error handling."""
    from src.retrieval.vector_store import VectorStoreError

    with pytest.raises(VectorStoreError):
        raise VectorStoreError("Test error")
