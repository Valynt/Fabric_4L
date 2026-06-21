"""Layer 3 response helpers shared by root and service-local pytest setup."""

from typing import Any
from unittest.mock import AsyncMock


def create_mock_graphrag_response() -> AsyncMock:
    """Create a mock GraphRAG response matching the Layer 3 helper."""
    mock = AsyncMock()
    mock.query.return_value = {
        "entities": [{"id": "test_entity", "type": "Capability", "name": "Test"}],
        "relationships": [{"source": "test", "target": "entity", "type": "has"}],
        "context_graph": {"nodes": 1, "edges": 0},
        "confidence_score": 0.8,
        "sources": ["test_entity"],
        "processing_time_ms": 100.0,
    }
    return mock


def create_mock_search_response() -> AsyncMock:
    """Create a mock search response matching the Layer 3 helper."""
    mock = AsyncMock()
    mock.search.return_value = {
        "results": [
            {
                "entity_id": "test_entity",
                "entity_type": "Capability",
                "name": "Test Capability",
                "bm25_score": 0.7,
                "vector_score": 0.8,
                "graph_score": 0.6,
                "combined_score": 0.7,
                "metadata": {},
                "confidence": 0.75,
            }
        ],
        "total_results": 1,
        "search_type": "hybrid",
        "processing_time_ms": 50.0,
    }
    return mock


class TestUtils:
    """Layer 3 response-shape assertions used by legacy bare imports."""

    @staticmethod
    def assert_valid_health_response(response_data: dict[str, Any]) -> None:
        assert "status" in response_data
        assert "version" in response_data
        assert "timestamp" in response_data
        assert "uptime_seconds" in response_data
        assert "dependencies" in response_data
        assert "metrics" in response_data
        assert "neo4j" in response_data
        assert "schema_status" in response_data
        assert response_data["status"] in ["healthy", "unhealthy", "degraded"]
        assert isinstance(response_data["uptime_seconds"], (int, float))
        assert response_data["uptime_seconds"] >= 0

    @staticmethod
    def assert_valid_search_response(response_data: dict[str, Any]) -> None:
        assert "query" in response_data
        assert "results" in response_data
        assert "total_results" in response_data
        assert "search_type" in response_data
        assert isinstance(response_data["results"], list)
        assert isinstance(response_data["total_results"], int)
        assert response_data["total_results"] >= 0
        if response_data["results"]:
            result = response_data["results"][0]
            assert "entity_id" in result
            assert "entity_type" in result
            assert "name" in result
            assert "combined_score" in result
            assert "confidence" in result

    @staticmethod
    def assert_valid_graphrag_response(response_data: dict[str, Any]) -> None:
        assert "query" in response_data
        assert "entities" in response_data
        assert "relationships" in response_data
        assert "context_graph" in response_data
        assert "confidence_score" in response_data
        assert "sources" in response_data
        assert isinstance(response_data["entities"], list)
        assert isinstance(response_data["relationships"], list)
        assert isinstance(response_data["sources"], list)
        assert isinstance(response_data["confidence_score"], (int, float))
        assert 0 <= response_data["confidence_score"] <= 1

    @staticmethod
    def assert_valid_ingestion_response(response_data: dict[str, Any]) -> None:
        assert "status" in response_data
        assert "source_id" in response_data
        assert "entities_loaded" in response_data
        assert "relationships_loaded" in response_data
        assert "triples_processed" in response_data
        assert response_data["status"] in ["success", "partial", "failed"]
        assert isinstance(response_data["entities_loaded"], int)
        assert isinstance(response_data["relationships_loaded"], int)
        assert isinstance(response_data["triples_processed"], int)
        assert all(
            count >= 0
            for count in [
                response_data["entities_loaded"],
                response_data["relationships_loaded"],
                response_data["triples_processed"],
            ]
        )
