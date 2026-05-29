from __future__ import annotations

"""Test configuration and fixtures for Value Fabric Layer 3 API."""


import json
import os
import sys
from collections.abc import AsyncGenerator, Iterator
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock

# Stub optional heavy deps before any imports that transitively require them
try:
    import redis.asyncio  # noqa: F401
except ImportError:
    _redis_mock = MagicMock()
    sys.modules["redis"] = _redis_mock
    sys.modules["redis.asyncio"] = _redis_mock.asyncio

try:
    import psutil  # noqa: F401
except ImportError:
    sys.modules["psutil"] = MagicMock()

_LAYER3_SRC = Path(__file__).resolve().parents[1] / "src"
if str(_LAYER3_SRC) not in sys.path:
    sys.path.insert(0, str(_LAYER3_SRC))
os.environ["PYTHONPATH"] = str(_LAYER3_SRC) + os.pathsep + os.environ.get("PYTHONPATH", "")

_TEST_ENV_DEFAULTS = {
    "ENVIRONMENT": "test",
    "APP_ENV": "test",
    "TESTING": "true",
    "ALLOW_LEGACY_TEST_TENANT_IDS": "true",
    # P0-008: Dev auth bypass flags removed — no longer needed
    "WORKERS": "1",
    "WEB_CONCURRENCY": "1",
    "OTEL_SDK_DISABLED": "true",
    "OTEL_TRACES_EXPORTER": "none",
    "OTEL_METRICS_EXPORTER": "none",
    "OTEL_LOGS_EXPORTER": "none",
}
for _key, _value in _TEST_ENV_DEFAULTS.items():
    os.environ.setdefault(_key, _value)

import pytest
import pytest_asyncio
from fastapi.testclient import TestClient
from httpx import ASGITransport, AsyncClient

from value_fabric.layer3.api.dependencies import AppState
from value_fabric.layer3.config import Settings, get_settings
from value_fabric.shared.models.typed_dict import TypedDictModel


class sample_search_requestResult(TypedDictModel):
    entity_type: str
    query: str
    search_type: str
    top_k: int

class sample_graphrag_queryResult(TypedDictModel):
    confidence_threshold: float
    max_hops: int
    max_results: int
    query: str

class sample_search_resultsResult(TypedDictModel):
    processing_time_ms: float
    query: str
    results: list[Any]
    search_type: str
    total_results: int

class sample_graphrag_responseResult(TypedDictModel):
    answer: str
    confidence_score: float
    context_graph: dict[str, Any]
    entities: list[Any]
    processing_time_ms: float
    query: str
    relationships: list[Any]
    sources: list[Any]

class sample_ingestion_requestResult(TypedDictModel):
    content_hash: str
    extraction_job_id: str
    rdf_data: str
    source_id: str

class sample_ingestion_responseResult(TypedDictModel):
    duration_seconds: float
    entities_loaded: int
    relationships_loaded: int
    source_id: str
    status: str
    triples_processed: int
    warnings: list[Any]


class TestSettings(Settings):
    """Test settings with safe defaults."""
    
    def __init__(self, **kwargs):
        # Override with test-safe defaults
        test_defaults = {
            "neo4j_uri": "bolt://localhost:7687",
            "neo4j_user": "neo4j",
            "neo4j_password": "test_password",
            "neo4j_database": "test_neo4j",
            "pinecone_api_key": None,
            "api_host": "127.0.0.1",
            "api_port": 8003,
            "log_level": "DEBUG",
            "cache_enabled": False,  # Disable cache for tests
            "metrics_enabled": False,  # Disable metrics for tests
            "rate_limit_enabled": False,  # Disable rate limiting for tests
        }
        test_defaults.update(kwargs)
        super().__init__(**test_defaults)


@pytest.fixture
def test_settings() -> TestSettings:
    """Get test settings."""
    return TestSettings()


@pytest.fixture
def mock_app_state() -> AppState:
    """Create mock application state."""
    state = AppState()
    
    # Mock Neo4j driver
    state.neo4j_driver = AsyncMock()
    state.neo4j_driver.verify_connectivity.return_value = None
    state.neo4j_driver.close.return_value = None
    
    # Mock schema initializer
    state.schema_initializer = AsyncMock()
    state.schema_initializer.health_check.return_value = {
        "status": "healthy",
        "database": "test_neo4j",
        "uri": "bolt://localhost:7687"
    }
    state.schema_initializer.verify_schema.return_value = {
        "constraints": {"expected": 5, "found": 5, "missing": []},
        "indexes": {"expected": 8, "found": 8, "missing": []},
        "valid": True
    }
    state.schema_initializer.get_statistics.return_value = {
        "nodes": {"Capability": 10, "UseCase": 15},
        "relationships": {"enables": 20, "requires": 25},
        "total_nodes": 25,
        "total_relationships": 45
    }
    
    # Mock analytics components
    state.graph_rag = AsyncMock()
    state.graph_rag.query.return_value = create_mock_graphrag_response().query.return_value
    state.hybrid_search = AsyncMock()
    state.centrality_analyzer = AsyncMock()
    state.community_detector = AsyncMock()
    state.similarity_analyzer = AsyncMock()
    state.sync_manager = AsyncMock()
    
    return state


@pytest.fixture
def test_client(
    test_settings: TestSettings,
    mock_app_state: AppState,
) -> Iterator[TestClient]:
    """Create test client with mocked dependencies."""
    from value_fabric.layer3.api.main import app

    # Override settings
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    # Override app state dependencies
    from value_fabric.layer3.api.dependencies import (
        get_app_state,
        get_centrality_analyzer,
        get_community_detector,
        get_graph_rag,
        get_hybrid_search,
        get_schema_initializer,
        get_similarity_analyzer,
        get_sync_manager,
    )
    
    app.dependency_overrides[get_app_state] = lambda: mock_app_state
    app.dependency_overrides[get_schema_initializer] = lambda: mock_app_state.schema_initializer
    app.dependency_overrides[get_graph_rag] = lambda: mock_app_state.graph_rag
    app.dependency_overrides[get_hybrid_search] = lambda: mock_app_state.hybrid_search
    app.dependency_overrides[get_centrality_analyzer] = lambda: mock_app_state.centrality_analyzer
    app.dependency_overrides[get_community_detector] = lambda: mock_app_state.community_detector
    app.dependency_overrides[get_similarity_analyzer] = lambda: mock_app_state.similarity_analyzer
    app.dependency_overrides[get_sync_manager] = lambda: mock_app_state.sync_manager
    
    with TestClient(app) as client:
        yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def async_client(test_settings: TestSettings, mock_app_state: AppState) -> AsyncGenerator[AsyncClient, None]:
    """Create async test client with mocked dependencies."""
    from value_fabric.layer3.api.main import app

    # Override settings
    app.dependency_overrides[get_settings] = lambda: test_settings
    
    # Override app state dependencies
    from value_fabric.layer3.api.dependencies import (
        get_app_state,
        get_centrality_analyzer,
        get_community_detector,
        get_graph_rag,
        get_hybrid_search,
        get_schema_initializer,
        get_similarity_analyzer,
        get_sync_manager,
    )
    
    app.dependency_overrides[get_app_state] = lambda: mock_app_state
    app.dependency_overrides[get_schema_initializer] = lambda: mock_app_state.schema_initializer
    app.dependency_overrides[get_graph_rag] = lambda: mock_app_state.graph_rag
    app.dependency_overrides[get_hybrid_search] = lambda: mock_app_state.hybrid_search
    app.dependency_overrides[get_centrality_analyzer] = lambda: mock_app_state.centrality_analyzer
    app.dependency_overrides[get_community_detector] = lambda: mock_app_state.community_detector
    app.dependency_overrides[get_similarity_analyzer] = lambda: mock_app_state.similarity_analyzer
    app.dependency_overrides[get_sync_manager] = lambda: mock_app_state.sync_manager
    
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        yield client
    
    # Clean up overrides
    app.dependency_overrides.clear()


# Sample data fixtures
@pytest.fixture
def sample_rdf_data() -> str:
    """Sample RDF data for testing."""
    return """
    @prefix ex: <http://example.com/> .
    @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
    
    ex:capability1 rdf:type ex:Capability ;
        ex:name "Automated Invoice Processing" ;
        ex:description "Capability to automatically process invoices" .
    
    ex:usecase1 rdf:type ex:UseCase ;
        ex:name "Invoice Management" ;
        ex:enables ex:capability1 .
    """


@pytest.fixture
def sample_search_request() -> dict[str, Any]:
    """Sample search request for testing."""
    return {
        "query": "automated invoice processing",
        "search_type": "hybrid",
        "top_k": 5,
        "entity_type": "Capability"
    }


@pytest.fixture
def sample_graphrag_query() -> dict[str, Any]:
    """Sample GraphRAG query for testing."""
    return {
        "query": "What capabilities enable automated invoice processing?",
        "max_hops": 3,
        "max_results": 10,
        "confidence_threshold": 0.7
    }


@pytest.fixture
def sample_search_results() -> dict[str, Any]:
    """Sample search results for testing."""
    return sample_search_resultsResult.model_validate({
        "query": "automated invoice processing",
        "results": [
            {
                "entity_id": "capability1",
                "entity_type": "Capability",
                "name": "Automated Invoice Processing",
                "bm25_score": 0.8,
                "vector_score": 0.9,
                "graph_score": 0.7,
                "combined_score": 0.8,
                "metadata": {"description": "Automated invoice processing capability"},
                "confidence": 0.85
            }
        ],
        "total_results": 1,
        "search_type": "hybrid",
        "processing_time_ms": 150.5
    })


@pytest.fixture
def sample_graphrag_response() -> dict[str, Any]:
    """Sample GraphRAG response for testing."""
    return sample_graphrag_responseResult.model_validate({
        "query": "What capabilities enable automated invoice processing?",
        "entities": [
            {
                "id": "capability1",
                "type": "Capability",
                "name": "Automated Invoice Processing",
                "properties": {"description": "Processes invoices automatically"}
            }
        ],
        "relationships": [
            {
                "source": "usecase1",
                "target": "capability1",
                "type": "enables"
            }
        ],
        "context_graph": {
            "nodes": 2,
            "edges": 1,
            "subgraph": "graph_data_here"
        },
        "confidence_score": 0.85,
        "sources": ["capability1", "usecase1"],
        "processing_time_ms": 250.0,
        "answer": "The Automated Invoice Processing capability enables automated invoice processing."
    })


@pytest.fixture
def sample_ingestion_request() -> dict[str, Any]:
    """Sample ingestion request for testing."""
    return {
        "rdf_data": """
            @prefix ex: <http://example.com/> .
            @prefix rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#> .
            
            ex:test_capability rdf:type ex:Capability ;
                ex:name "Test Capability" .
        """,
        "source_id": "test_doc_123",
        "extraction_job_id": "test_job_456",
        "content_hash": "abc123def456789",
        "tenant_id": "tenant-test-123",
    }


@pytest.fixture
def sample_ingestion_response() -> dict[str, Any]:
    """Sample ingestion response for testing."""
    return sample_ingestion_responseResult.model_validate({
        "status": "success",
        "source_id": "test_doc_123",
        "entities_loaded": 5,
        "relationships_loaded": 8,
        "triples_processed": 13,
        "duration_seconds": 2.5,
        "warnings": []
    })


# Mock response helpers
def create_mock_response(data: dict[str, Any], status_code: int = 200) -> MagicMock:
    """Create a mock HTTP response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = data
    response.text = json.dumps(data)
    response.headers = {"content-type": "application/json"}
    return response


def create_mock_graphrag_response() -> AsyncMock:
    """Create a mock GraphRAG response."""
    mock = AsyncMock()
    mock.query.return_value = {
        "entities": [{"id": "test_entity", "type": "Capability", "name": "Test"}],
        "relationships": [{"source": "test", "target": "entity", "type": "has"}],
        "context_graph": {"nodes": 1, "edges": 0},
        "confidence_score": 0.8,
        "sources": ["test_entity"],
        "processing_time_ms": 100.0
    }
    return mock


def create_mock_search_response() -> AsyncMock:
    """Create a mock search response."""
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
                "confidence": 0.75
            }
        ],
        "total_results": 1,
        "search_type": "hybrid",
        "processing_time_ms": 50.0
    }
    return mock


# Test utilities
class TestUtils:
    """Utility functions for testing."""
    
    @staticmethod
    def assert_valid_health_response(response_data: dict[str, Any]) -> None:
        """Assert health response has required fields."""
        assert "status" in response_data
        assert "version" in response_data
        assert "timestamp" in response_data
        assert "uptime_seconds" in response_data
        assert "dependencies" in response_data
        assert "metrics" in response_data
        assert "neo4j" in response_data
        assert "schema_status" in response_data
        
        # Validate status values
        assert response_data["status"] in ["healthy", "unhealthy", "degraded"]
        assert isinstance(response_data["uptime_seconds"], (int, float))
        assert response_data["uptime_seconds"] >= 0
    
    @staticmethod
    def assert_valid_search_response(response_data: dict[str, Any]) -> None:
        """Assert search response has required fields."""
        assert "query" in response_data
        assert "results" in response_data
        assert "total_results" in response_data
        assert "search_type" in response_data
        
        assert isinstance(response_data["results"], list)
        assert isinstance(response_data["total_results"], int)
        assert response_data["total_results"] >= 0
        
        # Validate result structure if present
        if response_data["results"]:
            result = response_data["results"][0]
            assert "entity_id" in result
            assert "entity_type" in result
            assert "name" in result
            assert "combined_score" in result
            assert "confidence" in result
    
    @staticmethod
    def assert_valid_graphrag_response(response_data: dict[str, Any]) -> None:
        """Assert GraphRAG response has required fields."""
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
        """Assert ingestion response has required fields."""
        assert "status" in response_data
        assert "source_id" in response_data
        assert "entities_loaded" in response_data
        assert "relationships_loaded" in response_data
        assert "triples_processed" in response_data
        
        assert response_data["status"] in ["success", "partial", "failed"]
        assert isinstance(response_data["entities_loaded"], int)
        assert isinstance(response_data["relationships_loaded"], int)
        assert isinstance(response_data["triples_processed"], int)
        assert all(count >= 0 for count in [
            response_data["entities_loaded"],
            response_data["relationships_loaded"], 
            response_data["triples_processed"]
        ])


@pytest.fixture
def test_utils():
    """Provide test utilities."""
    return TestUtils

