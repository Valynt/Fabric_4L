"""Contract tests for Layer 3 Graph/Entity endpoints consumed by frontend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from .schema_assertions import assert_matches_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_L3_PATH = REPO_ROOT / "contracts" / "openapi" / "layer3-knowledge.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _schema_ref(doc: dict[str, Any], name: str) -> dict[str, Any]:
    return {
        "$ref": f"#/components/schemas/{name}",
        "components": doc.get("components", {}),
    }


class TestL3GraphQueryContracts:
    """Contract tests for /v1/query/graph endpoint."""

    def test_graph_query_request_matches_openapi(self) -> None:
        """POST /v1/query/graph request payload matches OpenAPI schema."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        sample = {
            "query": "invoice automation",
            "entity_type": "Capability",
            "max_hops": 2,
            "max_results": 20,
        }
        schema = _schema_ref(l3_openapi, "GraphRAGQuery")
        assert_matches_schema(sample, schema, root=l3_openapi)

    def test_graph_query_response_matches_openapi(self) -> None:
        """POST /v1/query/graph response matches OpenAPI schema."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        sample = {
            "query": "invoice automation",
            "entities": [
                {
                    "id": "cap-1",
                    "name": "Automated Invoice Processing",
                    "entity_type": "Capability",
                    "confidence_score": 0.92,
                    "description": "Automated processing of invoices",
                    "properties": {"owner": "Finance Team"},
                }
            ],
            "relationships": [
                {
                    "source": "cap-1",
                    "target": "uc-1",
                    "type": "ENABLES",
                    "confidence": 0.88,
                    "properties": {"weight": 0.9},
                }
            ],
            "context_graph": {
                "nodes": [],
                "relationships": [],
            },
            "confidence_score": 0.9,
            "sources": ["doc-123"],
            "processing_time_ms": 18.3,
            "answer": "Automated invoice processing is enabled by OCR and workflow orchestration.",
        }
        schema = _schema_ref(l3_openapi, "GraphRAGResponse")
        assert_matches_schema(sample, schema, root=l3_openapi)


class TestL3EntityContextContracts:
    """Contract tests for /v1/entity/{id}/context endpoint."""

    def test_entity_context_response_matches_openapi(self) -> None:
        """GET /v1/entity/{id}/context response matches OpenAPI schema."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        sample = {
            "entity_id": "cap-1",
            "center": {
                "id": "cap-1",
                "name": "Automated Invoice Processing",
                "entity_type": "Capability",
                "confidence_score": 0.92,
                "description": "Automated processing of invoices",
                "properties": {"owner": "Finance Team"},
            },
            "neighbors": [
                {
                    "id": "uc-1",
                    "name": "Accounts Payable",
                    "entity_type": "UseCase",
                    "confidence_score": 0.88,
                    "description": "Managing accounts payable",
                }
            ],
            "relationships": [
                {
                    "source": "cap-1",
                    "target": "uc-1",
                    "type": "ENABLES",
                    "confidence": 0.88,
                }
            ],
            "entity_count": 2,
            "relationship_count": 1,
        }
        # EntityContextResponse must be defined for contract validation
        components = l3_openapi.get("components", {}).get("schemas", {})
        assert "EntityContextResponse" in components, (
            "Required schema 'EntityContextResponse' missing from OpenAPI spec. "
            "If this schema was intentionally removed, update the contract test."
        )
        schema = _schema_ref(l3_openapi, "EntityContextResponse")
        assert_matches_schema(sample, schema, root=l3_openapi)


class TestL3EntityTraversalContracts:
    """Contract tests for /v1/entity/traverse endpoint."""

    def test_entity_traversal_request_matches_openapi(self) -> None:
        """POST /v1/entity/traverse request payload matches OpenAPI schema."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        sample = {
            "entity_id": "cap-1",
            "direction": "up",
        }
        schema = _schema_ref(l3_openapi, "ValueTreeTraversal")
        assert_matches_schema(sample, schema, root=l3_openapi)

    def test_entity_traversal_response_matches_openapi(self) -> None:
        """POST /v1/entity/traverse response matches OpenAPI schema."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        sample = {
            "start_entity_id": "cap-1",
            "direction": "up",
            "paths": [
                {
                    "nodes": [
                        {
                            "id": "cap-1",
                            "name": "Invoice Processing",
                            "entity_type": "Capability",
                            "confidence_score": 0.92,
                        },
                        {
                            "id": "val-1",
                            "name": "Cost Reduction",
                            "entity_type": "ValueDriver",
                            "confidence_score": 0.9,
                        },
                    ],
                    "relationships": [
                        {
                            "source": "val-1",
                            "target": "cap-1",
                            "type": "DRIVES",
                            "confidence": 0.85,
                        }
                    ],
                    "value_score": 0.88,
                }
            ],
            "path_count": 1,
        }
        components = l3_openapi.get("components", {}).get("schemas", {})
        # Use namespaced schema name as generated by FastAPI
        schema_name = "layer3_knowledge__api__models__ValueTreeResponse"
        assert schema_name in components, (
            f"Required schema '{schema_name}' missing from OpenAPI spec. "
            "If this schema was intentionally removed, update the contract test."
        )
        schema = _schema_ref(l3_openapi, schema_name)
        assert_matches_schema(sample, schema, root=l3_openapi)

    def test_traversal_direction_enum_values(self) -> None:
        """Entity traversal direction enum includes expected values."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        expected_directions = {"up", "down", "both"}

        components = l3_openapi.get("components", {}).get("schemas", {})
        if "ValueTreeTraversal" in components:
            req_schema = components["ValueTreeTraversal"]
            direction_prop = req_schema.get("properties", {}).get("direction", {})
            if "enum" in direction_prop:
                schema_directions = set(direction_prop["enum"])
                missing = expected_directions - schema_directions
                assert (
                    not missing
                ), f"Traversal direction enum missing values: {missing}"


class TestL3SearchContracts:
    """Contract tests for /v1/search/hybrid endpoint."""

    def test_hybrid_search_request_matches_openapi(self) -> None:
        """POST /v1/search/hybrid request payload matches OpenAPI schema."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        sample = {
            "query": "automation",
            "search_type": "hybrid",
            "top_k": 20,
        }
        schema = _schema_ref(l3_openapi, "SearchRequest")
        assert_matches_schema(sample, schema, root=l3_openapi)

    def test_hybrid_search_response_matches_openapi(self) -> None:
        """POST /v1/search/hybrid response matches OpenAPI schema."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        sample = {
            "query": "automation",
            "results": [
                {
                    "entity_id": "cap-1",
                    "entity_type": "Capability",
                    "name": "Automated Invoice Processing",
                    "description": "Capability for automated invoice processing",
                    "bm25_score": 0.75,
                    "vector_score": 0.91,
                    "graph_score": 0.5,
                    "combined_score": 0.8,
                    "confidence": 0.92,
                    "metadata": {"source": "extraction-1"},
                }
            ],
            "total_results": 1,
            "search_type": "hybrid",
            "processing_time_ms": 22.1,
        }
        schema = _schema_ref(l3_openapi, "SearchResponse")
        assert_matches_schema(sample, schema, root=l3_openapi)

    def test_search_result_schema_completeness(self) -> None:
        """Search result contains all required fields for frontend consumption."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        required_fields = {"entity_id", "entity_type", "name", "combined_score"}

        components = l3_openapi.get("components", {}).get("schemas", {})
        if "SearchResult" in components:
            result_schema = components["SearchResult"]
            properties = set(result_schema.get("properties", {}).keys())
            missing = required_fields - properties
            assert (
                not missing
            ), f"SearchResult schema missing required fields: {missing}"


class TestL3GraphNodeContracts:
    """Contract tests for GraphNode schema used across endpoints."""

    def test_graph_node_schema_completeness(self) -> None:
        """GraphNode schema contains all required fields for frontend."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        schema_required = {"id", "name", "entity_type"}

        components = l3_openapi.get("components", {}).get("schemas", {})
        if "GraphNode" in components:
            node_schema = components["GraphNode"]
            properties = set(node_schema.get("properties", {}).keys())
            # Verify schema has its required fields
            missing = schema_required - properties
            assert not missing, f"GraphNode schema missing required fields: {missing}"

    def test_graph_node_response_sample_is_canonical_only(self) -> None:
        """GraphNode model_dump emits only canonical fields (no v2.5 aliases)."""
        from src.api.models import GraphNode

        node = GraphNode(
            id="cap-1",
            name="Automated Invoice Processing",
            entity_type="Capability",
            confidence_score=0.92,
        )
        serialized = node.model_dump()

        assert "name" in serialized
        assert serialized["name"] == "Automated Invoice Processing"
        assert "entity_type" in serialized
        assert serialized["entity_type"] == "Capability"
        assert "confidence_score" in serialized
        assert serialized["confidence_score"] == 0.92

        # v2.5 deprecation window closed: no legacy aliases in serialized output
        for legacy_key in ("label", "type", "confidence"):
            assert (
                legacy_key not in serialized
            ), f"Legacy alias '{legacy_key}' should be removed"

    def test_graph_node_rejects_legacy_alias_fields(self) -> None:
        from pydantic import ValidationError
        from src.api.models import GraphNode

        # Canonical construction remains supported after the v2.5 closure.
        GraphNode(
            id="cap-1", name="Canonical", entity_type="Capability", confidence_score=0.9
        )

        # Legacy alias fields are no longer accepted.
        with pytest.raises(ValidationError):
            GraphNode(
                id="cap-2",
                name="Canonical",
                label="LegacyMismatch",
                entity_type="Capability",
                confidence_score=0.9,
            )


class TestL3GraphRelationshipContracts:
    """Contract tests for GraphRelationship schema."""

    def test_graph_relationship_schema_completeness(self) -> None:
        """GraphRelationship schema contains all required fields."""
        l3_openapi = _load_json(OPENAPI_L3_PATH)
        required_fields = {"source", "target", "type"}

        components = l3_openapi.get("components", {}).get("schemas", {})
        if "GraphRelationship" in components:
            rel_schema = components["GraphRelationship"]
            properties = set(rel_schema.get("properties", {}).keys())
            missing = required_fields - properties
            assert (
                not missing
            ), f"GraphRelationship schema missing required fields: {missing}"

    def test_graph_relationship_response_is_canonical_only(self) -> None:
        """GraphEdge model_dump emits only the canonical 'type' field (no v2.5 alias)."""
        from src.api.models import GraphEdge

        # Create a GraphEdge instance
        edge = GraphEdge(
            source="cap-1",
            target="uc-1",
            type="ENABLES",
            weight=0.9,
        )

        serialized = edge.model_dump()

        assert (
            "type" in serialized
        ), "Canonical 'type' field should be in serialized output"
        assert serialized["type"] == "ENABLES"
        # v2.5 deprecation window closed: legacy 'relationship_type' alias removed
        assert "relationship_type" not in serialized
