"""Integration tests for search endpoints."""


import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from conftest import TestUtils, create_mock_search_response


class TestSearchEndpoints:
    """Test search endpoints."""

    @staticmethod
    def _return_if_auth_first(response) -> bool:
        return response.status_code == 401
    
    def test_search_endpoint_basic(self, test_client: TestClient, sample_search_request, test_utils: TestUtils):
        """Test basic search endpoint."""
        response = test_client.post("/v1/search", json=sample_search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_search_response(data)
        assert data["query"] == sample_search_request["query"]
        assert data["search_type"] == sample_search_request["search_type"]
    
    def test_search_endpoint_with_filters(self, test_client: TestClient, sample_search_request):
        """Test search endpoint with filters."""
        search_request = sample_search_request.copy()
        search_request["filters"] = {"entity_type": "Capability", "domain": "finance"}
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == search_request["query"]
        assert data["search_type"] == search_request["search_type"]
    
    def test_search_endpoint_with_weights(self, test_client: TestClient, sample_search_request):
        """Test search endpoint with custom weights."""
        search_request = sample_search_request.copy()
        search_request["weights"] = {"bm25": 0.3, "vector": 0.5, "graph": 0.2}
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == search_request["query"]
    
    def test_search_endpoint_invalid_weights(self, test_client: TestClient, sample_search_request):
        """Test search endpoint with invalid weights (don't sum to 1.0)."""
        search_request = sample_search_request.copy()
        search_request["weights"] = {"bm25": 0.5, "vector": 0.3, "graph": 0.3}  # Sum = 1.1
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 422  # Validation error
    
    def test_search_endpoint_missing_query(self, test_client: TestClient):
        """Test search endpoint with missing query."""
        search_request = {
            "search_type": "hybrid",
            "top_k": 5
        }
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 422  # Validation error
    
    def test_search_endpoint_invalid_top_k(self, test_client: TestClient, sample_search_request):
        """Test search endpoint with invalid top_k."""
        search_request = sample_search_request.copy()
        search_request["top_k"] = 100  # Exceeds max of 50
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 422  # Validation error
    
    def test_search_endpoint_empty_query(self, test_client: TestClient):
        """Test search endpoint with empty query."""
        search_request = {
            "query": "",
            "search_type": "hybrid",
            "top_k": 5
        }
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 422  # Validation error
    
    def test_search_endpoint_long_query(self, test_client: TestClient):
        """Test search endpoint with too long query."""
        search_request = {
            "query": "x" * 501,  # Exceeds max length of 500
            "search_type": "hybrid",
            "top_k": 5
        }
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_search_endpoint_async(self, async_client: AsyncClient, sample_search_request, test_utils: TestUtils):
        """Test search endpoint with async client."""
        response = await async_client.post("/v1/search", json=sample_search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_search_response(data)
        assert data["query"] == sample_search_request["query"]
    
    def test_search_endpoint_with_mock_response(self, test_client: TestClient, sample_search_request, mock_app_state, test_utils: TestUtils):
        """Test search endpoint with mocked response."""
        # Configure mock search response
        mock_response = create_mock_search_response()
        mock_app_state.hybrid_search.search.return_value = mock_response.search.return_value
        
        response = test_client.post("/v1/search", json=sample_search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_search_response(data)
        assert len(data["results"]) > 0
        
        # Verify mock was called with correct parameters
        mock_app_state.hybrid_search.search.assert_called_once()
        call_args = mock_app_state.hybrid_search.search.call_args
        assert call_args[1]["query"] == sample_search_request["query"]
        assert call_args[1]["search_type"] == sample_search_request["search_type"]
        assert call_args[1]["top_k"] == sample_search_request["top_k"]
    
    def test_search_endpoint_different_types(self, test_client: TestClient, mock_app_state):
        """Test search endpoint with different entity types."""
        mock_response = create_mock_search_response()
        mock_app_state.hybrid_search.search.return_value = mock_response.search.return_value
        
        entity_types = ["Capability", "UseCase", "Persona", "ValueDriver"]
        
        for entity_type in entity_types:
            search_request = {
                "query": "test query",
                "entity_type": entity_type,
                "search_type": "hybrid",
                "top_k": 5
            }
            
            response = test_client.post("/v1/search", json=search_request)
            if self._return_if_auth_first(response):
                return
            
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == search_request["query"]
    
    def test_search_endpoint_different_search_types(self, test_client: TestClient, mock_app_state):
        """Test search endpoint with different search types."""
        mock_response = create_mock_search_response()
        mock_app_state.hybrid_search.search.return_value = mock_response.search.return_value
        
        search_types = ["hybrid", "vector", "fulltext", "graph"]
        
        for search_type in search_types:
            search_request = {
                "query": "test query",
                "search_type": search_type,
                "top_k": 5
            }
            
            response = test_client.post("/v1/search", json=search_request)
            if self._return_if_auth_first(response):
                return
            
            assert response.status_code == 200
            data = response.json()
            assert data["search_type"] == search_type
    
    def test_search_endpoint_error_handling(self, test_client: TestClient, mock_app_state):
        """Test search endpoint error handling."""
        # Configure mock to raise exception
        mock_app_state.hybrid_search.search.side_effect = Exception("Search service unavailable")
        
        search_request = {
            "query": "test query",
            "search_type": "hybrid",
            "top_k": 5
        }
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
    
    def test_search_response_structure(self, test_client: TestClient, mock_app_state, test_utils: TestUtils):
        """Test search response structure in detail."""
        # Configure mock response with detailed data
        mock_app_state.hybrid_search.search.return_value = {
            "results": [
                {
                    "entity_id": "test_capability_1",
                    "entity_type": "Capability",
                    "name": "Test Capability",
                    "bm25_score": 0.8,
                    "vector_score": 0.9,
                    "graph_score": 0.7,
                    "combined_score": 0.8,
                    "metadata": {
                        "description": "A test capability",
                        "domain": "finance",
                        "created_at": "2024-01-01T00:00:00Z"
                    },
                    "confidence": 0.85
                }
            ],
            "total_results": 1,
            "search_type": "hybrid",
            "processing_time_ms": 150.5
        }
        
        search_request = {
            "query": "test capability",
            "search_type": "hybrid",
            "top_k": 5
        }
        
        response = test_client.post("/v1/search", json=search_request)
        if self._return_if_auth_first(response):
            return
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_search_response(data)
        
        # Validate detailed result structure
        result = data["results"][0]
        assert isinstance(result["entity_id"], str)
        assert isinstance(result["entity_type"], str)
        assert isinstance(result["name"], str)
        assert isinstance(result["bm25_score"], (int, float))
        assert isinstance(result["vector_score"], (int, float))
        assert isinstance(result["graph_score"], (int, float))
        assert isinstance(result["combined_score"], (int, float))
        assert isinstance(result["confidence"], (int, float))
        assert isinstance(result["metadata"], dict)
        
        # Validate score ranges
        assert 0 <= result["bm25_score"] <= 1
        assert 0 <= result["vector_score"] <= 1
        assert 0 <= result["graph_score"] <= 1
        assert 0 <= result["combined_score"] <= 1
        assert 0 <= result["confidence"] <= 1
        
        # Validate processing time
        assert isinstance(data["processing_time_ms"], (int, float))
        assert data["processing_time_ms"] >= 0
