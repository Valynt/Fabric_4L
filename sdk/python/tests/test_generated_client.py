"""Tests for generated OpenAPI-based clients."""

from __future__ import annotations

import pytest
import respx
from httpx import Response

from valuefabric.generated import L3Client, L4Client
from valuefabric.generated.l3 import SearchRequest, SearchResponse, SearchType


class TestL3Client:
    """Tests for L3 Knowledge Graph generated client."""

    @respx.mock
    def test_health_check(self):
        """Test L3 health endpoint."""
        route = respx.get("http://localhost:8001/health").mock(
            return_value=Response(200, json={"status": "healthy"})
        )

        client = L3Client()
        result = client.health()

        assert result["status"] == "healthy"
        assert route.called

    @respx.mock
    def test_search(self):
        """Test L3 search endpoint."""
        mock_response = {
            "query": "test query",
            "results": [
                {
                    "entity_id": "entity-1",
                    "entity_type": "Capability",
                    "name": "Test Entity",
                    "bm25_score": 0.9,
                    "vector_score": 0.85,
                    "graph_score": 0.8,
                    "combined_score": 0.87,
                    "confidence": 0.92,
                }
            ],
            "total_results": 1,
            "search_type": "hybrid",
            "processing_time_ms": 150,
        }
        route = respx.post("http://localhost:8001/v1/search/hybrid").mock(
            return_value=Response(200, json=mock_response)
        )

        client = L3Client()
        request = SearchRequest(query="test query", top_k=10)
        result = client.search(request)

        assert result.query == "test query"
        assert result.total_results == 1
        assert len(result.results) == 1
        assert result.results[0].entity_id == "entity-1"
        assert route.called

    @respx.mock
    @pytest.mark.asyncio
    async def test_async_search(self):
        """Test async L3 search endpoint."""
        mock_response = {
            "query": "async test",
            "results": [],
            "total_results": 0,
            "search_type": "hybrid",
            "processing_time_ms": 50,
        }
        route = respx.post("http://localhost:8001/v1/search/hybrid").mock(
            return_value=Response(200, json=mock_response)
        )

        client = L3Client()
        request = SearchRequest(query="async test")
        result = await client.asearch(request)

        assert result.query == "async test"
        assert result.total_results == 0
        assert route.called


class TestL4Client:
    """Tests for L4 Agents generated client."""

    @respx.mock
    def test_health_check(self):
        """Test L4 health endpoint."""
        route = respx.get("http://localhost:8000/health").mock(
            return_value=Response(200, json={"status": "ok"})
        )

        client = L4Client()
        result = client.health()

        assert result["status"] == "ok"
        assert route.called

    def test_client_auth_with_api_key(self):
        """Test L4 client with API key auth."""
        client = L4Client(api_key="test-key-123")
        assert client._sync_client.headers["X-API-Key"] == "test-key-123"

    def test_client_auth_with_jwt(self):
        """Test L4 client with JWT token auth."""
        client = L4Client(jwt_token="jwt-token-456")
        assert client._sync_client.headers["Authorization"] == "Bearer jwt-token-456"

    def test_client_default_headers(self):
        """Test L4 client has default headers."""
        client = L4Client()
        assert client._sync_client.headers["Accept"] == "application/json"
        assert client._sync_client.headers["Content-Type"] == "application/json"


class TestGeneratedModels:
    """Tests for generated Pydantic models."""

    def test_search_request_serialization(self):
        """Test SearchRequest serializes correctly."""
        from valuefabric.generated.l3 import SearchRequest, SearchType

        request = SearchRequest(
            query="test query",
            top_k=5,
            search_type=SearchType.hybrid,
        )

        data = request.model_dump(mode="json", exclude_none=True)
        assert data["query"] == "test query"
        assert data["top_k"] == 5
        assert data["search_type"] == "hybrid"

    def test_search_response_deserialization(self):
        """Test SearchResponse deserializes correctly."""
        from valuefabric.generated.l3 import SearchResponse, SearchType

        data = {
            "query": "test",
            "results": [],
            "total_results": 0,
            "search_type": "hybrid",
            "processing_time_ms": 100,
        }

        response = SearchResponse.model_validate(data)
        assert response.query == "test"
        assert response.total_results == 0
        assert response.search_type == SearchType.hybrid

    def test_entity_type_enum(self):
        """Test EntityType enum values."""
        from valuefabric.generated.l3 import EntityType

        assert EntityType.Capability.value == "Capability"
        assert EntityType.UseCase.value == "UseCase"
        assert EntityType.Persona.value == "Persona"
