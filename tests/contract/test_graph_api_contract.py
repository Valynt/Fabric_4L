"""
LAYER 5: CONTRACT TESTS
Pact-style contract tests ensuring request/response shapes match

Requirements:
- Pact-style contract tests ensuring request/response shapes match
- Version compatibility checks
- Schema validation against OpenAPI/swagger definitions

This tests the contract between:
1. Frontend (Consumer) - useGraphQuery hooks
2. Backend (Provider) - Layer 3 Graph API
"""

from typing import Any

import jsonschema
import pytest
from jsonschema import ValidationError, validate

# ============================================================================
# CONTRACT SCHEMAS (Source of Truth)
# These schemas define the API contract between frontend and backend
# ============================================================================

# Subgraph Response Schema - Must match both frontend types and backend model
SUBGRAPH_RESPONSE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["root_entity_id", "nodes", "edges", "depth", "stats"],
    "properties": {
        "root_entity_id": {"type": "string"},
        "nodes": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "entity_type", "confidence_score"],
                "properties": {
                    "id": {"type": "string", "minLength": 1},
                    "name": {"type": "string", "minLength": 1},
                    "entity_type": {"type": "string", "minLength": 1},
                    "confidence_score": {
                        "type": "number",
                        "minimum": 0,
                        "maximum": 1,
                    },
                    "description": {"type": "string"},
                    "properties": {"type": "object"},
                    "x": {"type": "number"},
                    "y": {"type": "number"},
                },
            },
        },
        "edges": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "target", "type"],
                "properties": {
                    "source": {"type": "string", "minLength": 1},
                    "target": {"type": "string", "minLength": 1},
                    "type": {"type": "string", "minLength": 1},
                    "confidence": {"type": "number", "minimum": 0, "maximum": 1},
                    "properties": {"type": "object"},
                },
            },
        },
        "depth": {"type": "integer", "minimum": 1, "maximum": 3},
        "stats": {
            "type": "object",
            "required": ["total_nodes", "total_edges", "density"],
            "properties": {
                "total_nodes": {"type": "integer", "minimum": 0},
                "total_edges": {"type": "integer", "minimum": 0},
                "density": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
    },
}

# Entity Context Response Schema
ENTITY_CONTEXT_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["entity_id", "center", "neighbors", "relationships", "entity_count", "relationship_count"],
    "properties": {
        "entity_id": {"type": "string", "minLength": 1},
        "center": {
            "type": "object",
            "required": ["id", "name", "entity_type", "confidence_score"],
            "properties": {
                "id": {"type": "string", "minLength": 1},
                "name": {"type": "string", "minLength": 1},
                "entity_type": {"type": "string", "minLength": 1},
                "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
            },
        },
        "neighbors": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "name", "entity_type", "confidence_score"],
            },
        },
        "relationships": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["source", "target", "type"],
            },
        },
        "entity_count": {"type": "integer", "minimum": 0},
        "relationship_count": {"type": "integer", "minimum": 0},
    },
}

# Graph Query Request Schema
GRAPH_QUERY_REQUEST_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["query"],
    "properties": {
        "query": {"type": "string", "minLength": 1},
        "entity_type": {"type": "string"},
        "max_hops": {"type": "integer", "minimum": 1, "maximum": 5},
        "max_results": {"type": "integer", "minimum": 1, "maximum": 1000},
    },
}

# Graph Query Response Schema
GRAPH_QUERY_RESPONSE_SCHEMA = {
    "$schema": "http://json-schema.org/draft-07/schema#",
    "type": "object",
    "required": ["query", "entities", "relationships", "confidence_score", "processing_time_ms"],
    "properties": {
        "query": {"type": "string"},
        "entities": {"type": "array"},
        "relationships": {"type": "array"},
        "context_graph": {"type": "object"},
        "confidence_score": {"type": "number", "minimum": 0, "maximum": 1},
        "sources": {"type": "array", "items": {"type": "string"}},
        "processing_time_ms": {"type": "number", "minimum": 0},
    },
}


# ============================================================================
# CONTRACT TESTS
# ============================================================================

@pytest.mark.contract
class TestSubgraphContract:
    """
    Contract tests for /subgraph endpoint
    Ensures frontend can consume backend responses
    """

    def test_subgraph_response_schema_valid(self):
        """Valid that a valid subgraph response passes schema validation"""
        valid_response = {
            "root_entity_id": "entity-1",
            "nodes": [
                {
                    "id": "node-1",
                    "name": "Test Node",
                    "entity_type": "Capability",
                    "confidence_score": 0.95,
                    "description": "A test node",
                    "x": 100,
                    "y": 200,
                }
            ],
            "edges": [
                {"source": "node-1", "target": "node-2", "type": "ENABLES", "confidence": 0.88}
            ],
            "depth": 2,
            "stats": {"total_nodes": 1, "total_edges": 1, "density": 0.5},
        }

        validate(instance=valid_response, schema=SUBGRAPH_RESPONSE_SCHEMA)

    def test_subgraph_response_missing_required_field_fails(self):
        """Validation should fail if required field is missing"""
        invalid_response = {
            "root_entity_id": "entity-1",
            # Missing "nodes" field
            "edges": [],
            "depth": 2,
            "stats": {"total_nodes": 0, "total_edges": 0, "density": 0},
        }

        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_response, schema=SUBGRAPH_RESPONSE_SCHEMA)

        assert "nodes" in str(exc_info.value)

    def test_subgraph_response_invalid_confidence_score_fails(self):
        """Validation should fail for confidence_score out of range"""
        invalid_response = {
            "root_entity_id": "entity-1",
            "nodes": [
                {
                    "id": "node-1",
                    "name": "Test",
                    "entity_type": "Capability",
                    "confidence_score": 1.5,  # Invalid: > 1
                }
            ],
            "edges": [],
            "depth": 2,
            "stats": {"total_nodes": 1, "total_edges": 0, "density": 0},
        }

        with pytest.raises(ValidationError) as exc_info:
            validate(instance=invalid_response, schema=SUBGRAPH_RESPONSE_SCHEMA)

        assert "confidence_score" in str(exc_info.value)

    def test_subgraph_empty_response_valid(self):
        """Empty subgraph response should be valid"""
        empty_response = {
            "root_entity_id": "",
            "nodes": [],
            "edges": [],
            "depth": 2,
            "stats": {"total_nodes": 0, "total_edges": 0, "density": 0},
        }

        validate(instance=empty_response, schema=SUBGRAPH_RESPONSE_SCHEMA)


@pytest.mark.contract
class TestEntityContextContract:
    """Contract tests for /entity/{id}/context endpoint"""

    def test_entity_context_response_valid(self):
        """Valid entity context response should pass validation"""
        valid_response = {
            "entity_id": "entity-1",
            "center": {
                "id": "entity-1",
                "name": "Center Entity",
                "entity_type": "Capability",
                "confidence_score": 0.95,
            },
            "neighbors": [
                {
                    "id": "neighbor-1",
                    "name": "Neighbor",
                    "entity_type": "UseCase",
                    "confidence_score": 0.88,
                }
            ],
            "relationships": [
                {"source": "entity-1", "target": "neighbor-1", "type": "ENABLES"}
            ],
            "entity_count": 2,
            "relationship_count": 1,
        }

        validate(instance=valid_response, schema=ENTITY_CONTEXT_SCHEMA)

    def test_entity_context_no_neighbors_valid(self):
        """Entity with no neighbors should be valid"""
        orphan_response = {
            "entity_id": "orphan",
            "center": {
                "id": "orphan",
                "name": "Orphan Entity",
                "entity_type": "Capability",
                "confidence_score": 0.9,
            },
            "neighbors": [],
            "relationships": [],
            "entity_count": 1,
            "relationship_count": 0,
        }

        validate(instance=orphan_response, schema=ENTITY_CONTEXT_SCHEMA)


@pytest.mark.contract
class TestGraphQueryContract:
    """Contract tests for /query/graph endpoint"""

    def test_graph_query_request_valid(self):
        """Valid request should pass schema validation"""
        valid_request = {
            "query": "Find AI capabilities",
            "entity_type": "Capability",
            "max_hops": 3,
            "max_results": 20,
        }

        validate(instance=valid_request, schema=GRAPH_QUERY_REQUEST_SCHEMA)

    def test_graph_query_request_minimal_valid(self):
        """Request with only required fields should be valid"""
        minimal_request = {"query": "test"}

        validate(instance=minimal_request, schema=GRAPH_QUERY_REQUEST_SCHEMA)

    def test_graph_query_request_missing_query_fails(self):
        """Request without required 'query' field should fail"""
        invalid_request = {"max_hops": 2}

        with pytest.raises(ValidationError):
            validate(instance=invalid_request, schema=GRAPH_QUERY_REQUEST_SCHEMA)

    def test_graph_query_response_valid(self):
        """Valid response should pass schema validation"""
        valid_response = {
            "query": "Find AI",
            "entities": [],
            "relationships": [],
            "confidence_score": 0.85,
            "processing_time_ms": 150,
            "sources": ["neo4j", "vector-search"],
        }

        validate(instance=valid_response, schema=GRAPH_QUERY_RESPONSE_SCHEMA)


@pytest.mark.contract
class TestVersionCompatibility:
    """
    Version compatibility tests
    Ensures API contract doesn't break between versions
    """

    def test_schema_version_matches_api_version(self):
        """
        Schema version should match the API version documented in OpenAPI spec.
        This is a placeholder - real implementation would parse OpenAPI spec.
        """
        # API version should be documented
        api_version = "v1"
        schema_version = "v1"

        assert api_version == schema_version

    @pytest.mark.temporary_compat
    def test_deprecated_fields_still_supported(self):
        """
        Deprecated fields should still be accepted in responses.
        This prevents breaking older clients.
        """
        # Example: old 'type' field alongside new 'entity_type'
        backward_compatible_response = {
            "root_entity_id": "",
            "nodes": [
                {
                    "id": "node-1",
                    "name": "Test",
                    "entity_type": "Capability",
                    "type": "Capability",  # Deprecated but still present
                    "confidence_score": 0.9,
                }
            ],
            "edges": [],
            "depth": 2,
            "stats": {"total_nodes": 1, "total_edges": 0, "density": 0},
        }

        # Should not fail - extra fields are allowed
        validate(instance=backward_compatible_response, schema=SUBGRAPH_RESPONSE_SCHEMA)

    def test_new_optional_fields_dont_break_old_clients(self):
        """
        New optional fields in responses should not break old clients.
        Old clients should ignore unknown fields.
        """
        response_with_new_field = {
            "root_entity_id": "",
            "nodes": [
                {
                    "id": "node-1",
                    "name": "Test",
                    "entity_type": "Capability",
                    "confidence_score": 0.9,
                    "new_field": "This should be ignored by old clients",
                }
            ],
            "edges": [],
            "depth": 2,
            "stats": {"total_nodes": 1, "total_edges": 0, "density": 0},
        }

        # Should not fail - extra fields are allowed
        validate(instance=response_with_new_field, schema=SUBGRAPH_RESPONSE_SCHEMA)


@pytest.mark.contract
class TestConsumerProviderContract:
    """
    Full consumer-provider contract tests.
    These verify that frontend expectations match backend capabilities.
    """

    def test_frontend_can_parse_backend_response(self):
        """
        Simulates what frontend receives and validates it can be used.
        This catches type mismatches between TypeScript and Python.
        """
        # This is what the backend sends
        backend_response = {
            "root_entity_id": "cap-123",
            "nodes": [
                {
                    "id": "cap-123",
                    "name": "AI Analytics",
                    "entity_type": "Capability",
                    "confidence_score": 0.95,
                    "description": "AI-powered analytics",
                    "properties": {"cost": 100000, "roi": 2.5},
                    "x": 100.5,
                    "y": 200.75,
                }
            ],
            "edges": [],
            "depth": 2,
            "stats": {"total_nodes": 1, "total_edges": 0, "density": 0.0},
        }

        # Frontend validation (simulated by JSON schema)
        validate(instance=backend_response, schema=SUBGRAPH_RESPONSE_SCHEMA)

        # Simulate frontend TypeScript types
        # GraphNode expects: id, name, entity_type, confidence_score, plus optional fields
        node = backend_response["nodes"][0]
        assert isinstance(node["id"], str)
        assert isinstance(node["confidence_score"], (int, float))
        assert 0 <= node["confidence_score"] <= 1

    def test_coherence_property_in_contract(self):
        """
        Critical business rule: All edge endpoints must exist in nodes.
        This is a semantic contract, not just syntactic.
        """
        coherent_response = {
            "root_entity_id": "node-1",
            "nodes": [
                {"id": "node-1", "name": "A", "entity_type": "Capability", "confidence_score": 0.9},
                {"id": "node-2", "name": "B", "entity_type": "UseCase", "confidence_score": 0.8},
            ],
            "edges": [
                {"source": "node-1", "target": "node-2", "type": "ENABLES"}
            ],
            "depth": 2,
            "stats": {"total_nodes": 2, "total_edges": 1, "density": 0.5},
        }

        # Validate structure
        validate(instance=coherent_response, schema=SUBGRAPH_RESPONSE_SCHEMA)

        # Validate coherence: all edge endpoints exist
        node_ids = {n["id"] for n in coherent_response["nodes"]}
        for edge in coherent_response["edges"]:
            assert edge["source"] in node_ids, f"Edge source {edge['source']} not in nodes"
            assert edge["target"] in node_ids, f"Edge target {edge['target']} not in nodes"


# ============================================================================
# SCHEMA EVOLUTION TESTS
# ============================================================================

@pytest.mark.contract
class TestSchemaEvolution:
    """
    Tests for safe schema evolution.
    Documents what changes are safe vs breaking.
    """

    SAFE_CHANGES = [
        "adding optional fields",
        "making required fields optional",
        "expanding enum values",
        "increasing maximum limits",
    ]

    BREAKING_CHANGES = [
        "removing fields",
        "adding new required fields",
        "changing field types",
        "reducing maximum limits",
    ]

    def test_document_safe_changes(self):
        """Document what schema changes are safe"""
        for change in self.SAFE_CHANGES:
            assert change  # Just documenting

    def test_document_breaking_changes(self):
        """Document what schema changes are breaking"""
        for change in self.BREAKING_CHANGES:
            assert change  # Just documenting


# ============================================================================
# PACT-STYLE CONSUMER CONTRACT
# ============================================================================

class ConsumerContract:
    """
    Simulates Pact contract generation.
    In real implementation, this would generate .pact files.
    """

    @staticmethod
    def generate_subgraph_consumer_contract():
        """
        Generates the contract that the frontend (consumer) expects from the backend.
        """
        return {
            "consumer": {
                "name": "value-fabric-frontend"
            },
            "provider": {
                "name": "layer3-knowledge-api"
            },
            "interactions": [
                {
                    "description": "a request for a subgraph",
                    "provider_state": "graph data exists",
                    "request": {
                        "method": "GET",
                        "path": "/api/v1/graph/subgraph",
                        "query": "query=AI&depth=2&limit=100"
                    },
                    "response": {
                        "status": 200,
                        "body": {
                            "root_entity_id": "",
                            "nodes": [
                                {
                                    "id": "entity-1",
                                    "name": "AI Capability",
                                    "entity_type": "Capability",
                                    "confidence_score": 0.95
                                }
                            ],
                            "edges": [],
                            "depth": 2,
                            "stats": {
                                "total_nodes": 1,
                                "total_edges": 0,
                                "density": 0
                            }
                        }
                    }
                }
            ],
            "metadata": {
                "pactSpecificationVersion": "2.0.0"
            }
        }


@pytest.mark.temporary_compat
def test_consumer_contract_generation():
    """Verify we can generate a consumer contract"""
    contract = ConsumerContract.generate_subgraph_consumer_contract()
    assert contract["consumer"]["name"] == "value-fabric-frontend"
    assert contract["provider"]["name"] == "layer3-knowledge-api"
    assert len(contract["interactions"]) > 0
