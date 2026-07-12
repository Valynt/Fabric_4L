"""
Contract Tests for Layer 3 Knowledge Graph API

Validates that the implementation matches the OpenAPI specification.
These tests verify endpoints exist and return expected status codes AND schema.
"""

import jsonschema
import pytest
from httpx import AsyncClient

# GraphNode schema for validation
GRAPH_NODE_SCHEMA = {
    "type": "object",
    "required": ["id"],
    "properties": {
        "id": {"type": "string"},
        "type": {"type": "string"},
        "name": {"type": "string"},
        "description": {"type": ["string", "null"]},
        "confidence_score": {"type": "number"},
    }
}

GRAPH_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["nodes", "edges"],
    "properties": {
        "nodes": {
            "type": "array",
            "items": GRAPH_NODE_SCHEMA
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "target", "type"],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                }
            }
        }
    }
}


# ============================================================================
# Entity Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_entity_traverse_endpoint_exists(client: AsyncClient):
    """Verify POST /v1/entity/traverse is implemented and returns valid response."""
    response = await client.post(
        "/v1/entity/traverse",
        json={
            "entity_id": "test-entity-123",
            "direction": "downward",
            "max_depth": 3
        }
    )
    # Should not be 404 (not found) - we accept 200, 400, or 422 as valid
    assert response.status_code != 404, "Entity traverse endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_entity_context_endpoint_exists(client: AsyncClient):
    """Verify GET /v1/entity/{entity_id}/context is implemented."""
    response = await client.get(
        "/v1/entity/test-entity-123/context",
        params={"hops": 2, "limit": 50}
    )
    # Should not be 404 - endpoint should exist
    assert response.status_code != 404, "Entity context endpoint should exist"
    # We accept 200, 400, 404 (entity not found), or 422
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


# ============================================================================
# Search Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_hybrid_search_endpoint_exists(client: AsyncClient):
    """Verify POST /v1/search/hybrid is implemented."""
    response = await client.post(
        "/v1/search/hybrid",
        json={"query": "test query", "limit": 10}
    )
    assert response.status_code != 404, "Hybrid search endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


# ============================================================================
# Value Tree Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_value_tree_get_endpoint_exists(client: AsyncClient):
    """Verify GET /v1/value-trees/{entity_id} is implemented."""
    response = await client.get("/v1/value-trees/test-entity-123")
    assert response.status_code != 404, "Value tree endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_value_tree_paths_endpoint_exists(client: AsyncClient):
    """Verify GET /v1/value-trees/{entity_id}/paths is implemented."""
    response = await client.get("/v1/value-trees/test-entity-123/paths")
    assert response.status_code != 404, "Value tree paths endpoint should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


# ============================================================================
# Formula Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_formulas_list_endpoint_exists(client: AsyncClient):
    """Verify GET /v1/formulas is implemented."""
    response = await client.get("/v1/formulas")
    assert response.status_code != 404, "Formulas list endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_formula_evaluate_endpoint_exists(client: AsyncClient):
    """Verify POST /v1/formulas/evaluate is implemented."""
    response = await client.post(
        "/v1/formulas/evaluate",
        json={"formula": "a + b", "variables": {"a": 1, "b": 2}}
    )
    assert response.status_code != 404, "Formula evaluate endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


# ============================================================================
# Analytics Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_analytics_communities_endpoint_exists(client: AsyncClient):
    """Verify POST /v1/analytics/communities is implemented."""
    response = await client.post(
        "/v1/analytics/communities",
        json={"entity_types": ["UseCase"]}
    )
    assert response.status_code != 404, "Communities endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_analytics_centrality_endpoint_exists(client: AsyncClient):
    """Verify POST /v1/analytics/centrality is implemented."""
    response = await client.post(
        "/v1/analytics/centrality",
        json={"entity_ids": ["test-1", "test-2"]}
    )
    assert response.status_code != 404, "Centrality endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


# ============================================================================
# Subgraph Endpoint (New Implementation)
# ============================================================================

SUBGRAPH_RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["nodes", "edges"],
    "properties": {
        "nodes": {
            "type": "array",
            "items": GRAPH_NODE_SCHEMA
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "target", "type"],
                "properties": {
                    "source": {"type": "string"},
                    "target": {"type": "string"},
                    "type": {"type": "string"},
                    "properties": {"type": "object"},
                }
            }
        },
        "stats": {"type": "object"},
        "depth": {"type": "integer"},
    }
}


@pytest.mark.asyncio
async def test_graph_subgraph_endpoint_exists(client: AsyncClient):
    """Verify GET /v1/graph/subgraph is implemented with query mode."""
    response = await client.get(
        "/v1/graph/subgraph",
        params={"query": "AI", "depth": 1, "limit": 50}
    )
    assert response.status_code != 404, "Subgraph endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_graph_subgraph_center_mode_exists(client: AsyncClient):
    """Verify GET /v1/graph/subgraph works with center_entity_id mode."""
    response = await client.get(
        "/v1/graph/subgraph",
        params={"center_entity_id": "test-entity-123", "depth": 2, "limit": 100}
    )
    assert response.status_code != 404, "Subgraph center mode should exist"
    assert response.status_code in [200, 400, 404, 422], \
        f"Expected 200, 400, 404, or 422, got {response.status_code}"


@pytest.mark.asyncio
async def test_graph_subgraph_returns_valid_schema(client: AsyncClient):
    """Validate subgraph endpoint returns schema-compliant response."""
    response = await client.get(
        "/v1/graph/subgraph",
        params={"query": "test", "depth": 1, "limit": 10}
    )
    if response.status_code == 200:
        data = response.json()
        jsonschema.validate(data, SUBGRAPH_RESPONSE_SCHEMA)
        # Validate coherent structure: edges reference valid nodes
        node_ids = {node["id"] for node in data["nodes"]}
        for edge in data["edges"]:
            assert edge["source"] in node_ids, f"Edge source {edge['source']} not in nodes"
            assert edge["target"] in node_ids, f"Edge target {edge['target']} not in nodes"


# ============================================================================
# GraphRAG Endpoints
# ============================================================================

@pytest.mark.asyncio
async def test_graphrag_query_endpoint_exists(client: AsyncClient):
    """Verify POST /v1/graphrag is implemented."""
    response = await client.post(
        "/v1/graphrag",
        json={"question": "What is the ROI of CRM integration?"}
    )
    assert response.status_code != 404, "GraphRAG endpoint should exist"
    assert response.status_code in [200, 400, 422], \
        f"Expected 200, 400, or 422, got {response.status_code}"


# ============================================================================
# Health Endpoint
# ============================================================================

@pytest.mark.asyncio
async def test_health_endpoint_exists(client: AsyncClient):
    """Verify GET /health is implemented."""
    response = await client.get("/health")
    assert response.status_code == 200, "Health endpoint should return 200"


# ============================================================================
# Schema Validation Tests
# ============================================================================

@pytest.mark.asyncio
async def test_graph_endpoint_returns_valid_schema(client: AsyncClient):
    """Validate graph endpoint returns schema-compliant response."""
    response = await client.get("/v1/graph/nodes?limit=5")
    assert response.status_code == 200, "Graph nodes endpoint should return 200"
    data = response.json()

    # Validate schema structure, not just status
    jsonschema.validate(data, GRAPH_RESPONSE_SCHEMA)

    # Validate business invariants
    assert all(node.get("id") for node in data["nodes"]), "All nodes must have IDs"
    assert isinstance(data["edges"], list), "Edges must be list"
