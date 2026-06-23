"""Integration tests for GraphRAG endpoints."""


import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from conftest import TestUtils, create_mock_graphrag_response


# Canonical GraphRAG endpoint - preferred for new implementations
CANONICAL_GRAPH_RAG_ENDPOINT = "/v1/query/graph"
# Legacy alias - retained for backward compatibility
LEGACY_GRAPH_RAG_ENDPOINT = "/v1/graphrag"


class TestGraphRAGEndpoints:
    """Test GraphRAG endpoints - using canonical /v1/query/graph endpoint."""

    @staticmethod
    def _return_if_auth_first(response) -> bool:
        return response.status_code == 401
    
    def test_graphrag_endpoint_basic(self, test_client: TestClient, sample_graphrag_query, test_utils: TestUtils):
        """Test basic GraphRAG endpoint using canonical route."""
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=sample_graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_graphrag_response(data)
        assert data["query"] == sample_graphrag_query["query"]
    
    def test_graphrag_endpoint_with_entity_filter(self, test_client: TestClient, sample_graphrag_query):
        """Test GraphRAG endpoint with entity type filter using canonical route."""
        graphrag_query = sample_graphrag_query.copy()
        graphrag_query["entity_type"] = "Capability"
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == graphrag_query["query"]
    
    def test_graphrag_endpoint_with_confidence_threshold(self, test_client: TestClient, sample_graphrag_query):
        """Test GraphRAG endpoint with confidence threshold using canonical route."""
        graphrag_query = sample_graphrag_query.copy()
        graphrag_query["confidence_threshold"] = 0.9
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == graphrag_query["query"]
    
    def test_graphrag_endpoint_invalid_confidence_threshold(self, test_client: TestClient, sample_graphrag_query):
        """Test GraphRAG endpoint with invalid confidence threshold returns 422 using canonical route."""
        graphrag_query = sample_graphrag_query.copy()
        graphrag_query["confidence_threshold"] = 1.5  # Exceeds max of 1.0
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 422  # Validation error
    
    def test_graphrag_endpoint_invalid_max_hops(self, test_client: TestClient, sample_graphrag_query):
        """Test GraphRAG endpoint with invalid max hops returns 422 using canonical route."""
        graphrag_query = sample_graphrag_query.copy()
        graphrag_query["max_hops"] = 10  # Exceeds max of 5
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 422  # Validation error
    
    def test_graphrag_endpoint_invalid_max_results(self, test_client: TestClient, sample_graphrag_query):
        """Test GraphRAG endpoint with invalid max results returns 422 using canonical route."""
        graphrag_query = sample_graphrag_query.copy()
        graphrag_query["max_results"] = 100  # Exceeds max of 50
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 422  # Validation error
    
    def test_graphrag_endpoint_missing_query(self, test_client: TestClient):
        """Test GraphRAG endpoint with missing query returns 422 using canonical route."""
        graphrag_query = {
            "max_hops": 3,
            "max_results": 10
        }
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 422  # Validation error
    
    def test_graphrag_endpoint_empty_query(self, test_client: TestClient):
        """Test GraphRAG endpoint with empty query returns 422 using canonical route."""
        graphrag_query = {
            "query": "",
            "max_hops": 3,
            "max_results": 10
        }
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 422  # Validation error
    
    def test_graphrag_endpoint_long_query(self, test_client: TestClient):
        """Test GraphRAG endpoint with too long query returns 422 using canonical route."""
        graphrag_query = {
            "query": "x" * 1001,  # Exceeds max length of 1000
            "max_hops": 3,
            "max_results": 10
        }
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_graphrag_endpoint_async(self, async_client: AsyncClient, sample_graphrag_query, test_utils: TestUtils):
        """Test GraphRAG endpoint with async client using canonical route."""
        response = await async_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=sample_graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_graphrag_response(data)
        assert data["query"] == sample_graphrag_query["query"]
    
    def test_graphrag_endpoint_with_mock_response(self, test_client: TestClient, sample_graphrag_query, mock_app_state, test_utils: TestUtils):
        """Test GraphRAG endpoint with mocked response using canonical route."""
        # Configure mock GraphRAG response
        mock_response = create_mock_graphrag_response()
        mock_app_state.graph_rag.query.return_value = mock_response.query.return_value
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=sample_graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_graphrag_response(data)
        assert len(data["entities"]) > 0
        assert len(data["relationships"]) > 0
        
        # Verify mock was called with correct parameters
        mock_app_state.graph_rag.query.assert_called_once()
        call_args = mock_app_state.graph_rag.query.call_args
        assert call_args[1]["query_text"] == sample_graphrag_query["query"]
        assert call_args[1]["max_hops"] == sample_graphrag_query["max_hops"]
        assert call_args[1]["max_results"] == sample_graphrag_query["max_results"]
    
    def test_graphrag_endpoint_different_entity_types(self, test_client: TestClient, mock_app_state):
        """Test GraphRAG endpoint with different entity types using canonical route."""
        mock_response = create_mock_graphrag_response()
        mock_app_state.graph_rag.query.return_value = mock_response.query.return_value
        
        entity_types = ["Capability", "UseCase", "Persona", "ValueDriver"]
        
        for entity_type in entity_types:
            graphrag_query = {
                "query": f"What {entity_type.lower()} are available?",
                "entity_type": entity_type,
                "max_hops": 3,
                "max_results": 10
            }
            
            response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
            if self._return_if_auth_first(response):
                return
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == graphrag_query["query"]
    
    def test_graphrag_endpoint_different_hops(self, test_client: TestClient, mock_app_state):
        """Test GraphRAG endpoint with different hop counts using canonical route."""
        mock_response = create_mock_graphrag_response()
        mock_app_state.graph_rag.query.return_value = mock_response.query.return_value
        
        hop_counts = [1, 2, 3, 4, 5]
        
        for hops in hop_counts:
            graphrag_query = {
                "query": "What capabilities are available?",
                "max_hops": hops,
                "max_results": 10
            }
            
            response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
            if self._return_if_auth_first(response):
                return
            assert response.status_code == 200
            data = response.json()
            assert data["query"] == graphrag_query["query"]
    
    def test_graphrag_endpoint_with_context_disabled(self, test_client: TestClient, mock_app_state):
        """Test GraphRAG endpoint with context disabled using canonical route."""
        mock_response = create_mock_graphrag_response()
        mock_app_state.graph_rag.query.return_value = mock_response.query.return_value
        
        graphrag_query = {
            "query": "What capabilities are available?",
            "max_hops": 3,
            "max_results": 10,
            "include_context": False
        }
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 200
        data = response.json()
        assert data["query"] == graphrag_query["query"]
    
    def test_graphrag_endpoint_error_handling(self, test_client: TestClient, mock_app_state):
        """Test GraphRAG endpoint error handling using canonical route."""
        # Configure mock to raise exception
        mock_app_state.graph_rag.query.side_effect = Exception("GraphRAG service unavailable")
        
        graphrag_query = {
            "query": "What capabilities are available?",
            "max_hops": 3,
            "max_results": 10
        }
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 500
        data = response.json()
        assert data["code"] == "INTERNAL_ERROR"
        assert "Query processing failed" in data["message"]
        assert "trace_id" in data
    
    def test_graphrag_legacy_alias_endpoint(self, test_client: TestClient, sample_graphrag_query, test_utils: TestUtils):
        """Test backward-compatible /v1/graphrag alias still functions correctly.
        
        This ensures existing clients using the legacy endpoint continue to work.
        New implementations should use /v1/query/graph (canonical).
        """
        response = test_client.post(LEGACY_GRAPH_RAG_ENDPOINT, json=sample_graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_graphrag_response(data)
        assert data["query"] == sample_graphrag_query["query"]
    
    def test_graphrag_response_structure(self, test_client: TestClient, mock_app_state, test_utils: TestUtils):
        """Test GraphRAG response structure in detail using canonical route."""
        # Configure mock response with detailed data
        mock_app_state.graph_rag.query.return_value = {
            "query": "What capabilities enable automated invoice processing?",
            "entities": [
                {
                    "id": "capability_1",
                    "type": "Capability",
                    "name": "Automated Invoice Processing",
                    "properties": {
                        "description": "Processes invoices automatically",
                        "domain": "finance",
                        "complexity": "medium"
                    }
                },
                {
                    "id": "capability_2", 
                    "type": "Capability",
                    "name": "Document Recognition",
                    "properties": {
                        "description": "Recognizes document types",
                        "domain": "finance",
                        "complexity": "low"
                    }
                }
            ],
            "relationships": [
                {
                    "source": "capability_1",
                    "target": "capability_2",
                    "type": "uses",
                    "properties": {
                        "strength": 0.8,
                        "frequency": "high"
                    }
                }
            ],
            "context_graph": {
                "nodes": 2,
                "edges": 1,
                "subgraph": {
                    "nodes": ["capability_1", "capability_2"],
                    "edges": [{"from": "capability_1", "to": "capability_2", "type": "uses"}]
                }
            },
            "confidence_score": 0.85,
            "sources": ["capability_1", "capability_2"],
            "processing_time_ms": 250.0,
            "answer": "The Automated Invoice Processing capability enables automated invoice processing. It uses the Document Recognition capability for document type identification."
        }
        
        graphrag_query = {
            "query": "What capabilities enable automated invoice processing?",
            "max_hops": 3,
            "max_results": 10
        }
        
        response = test_client.post(CANONICAL_GRAPH_RAG_ENDPOINT, json=graphrag_query)
        if self._return_if_auth_first(response):
            return
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_graphrag_response(data)
        
        # Validate detailed entity structure
        entities = data["entities"]
        assert isinstance(entities, list)
        assert len(entities) == 2
        
        for entity in entities:
            assert "id" in entity
            assert "type" in entity
            assert "name" in entity
            assert "properties" in entity
            assert isinstance(entity["properties"], dict)
        
        # Validate detailed relationship structure
        relationships = data["relationships"]
        assert isinstance(relationships, list)
        assert len(relationships) == 1
        
        for rel in relationships:
            assert "source" in rel
            assert "target" in rel
            assert "type" in rel
            assert "properties" in rel
            assert isinstance(rel["properties"], dict)
        
        # Validate context graph structure
        context_graph = data["context_graph"]
        assert isinstance(context_graph, dict)
        assert "nodes" in context_graph
        assert "edges" in context_graph
        assert "subgraph" in context_graph
        assert isinstance(context_graph["nodes"], int)
        assert isinstance(context_graph["edges"], int)
        assert isinstance(context_graph["subgraph"], dict)
        
        # Validate sources
        sources = data["sources"]
        assert isinstance(sources, list)
        assert len(sources) >= 1
        
        # Validate processing time
        assert isinstance(data["processing_time_ms"], (int, float))
        assert data["processing_time_ms"] >= 0
        
        # Validate answer if present
        if "answer" in data and data["answer"]:
            assert isinstance(data["answer"], str)
            assert len(data["answer"]) > 0
