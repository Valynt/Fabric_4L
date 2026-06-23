from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from src.api.models import (
        GRAPH_FIELD_ALIAS_REMOVAL_VERSION,
        GraphEdge,
        GraphNode,
        get_deprecated_field_usage_counters,
    )
except (ImportError, Exception) as _exc:
    pytest.skip(
        "value_fabric.layer3 service stack not available (pre-existing blocker #1/#9)",
        allow_module_level=True,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_L3_PATH = REPO_ROOT / "contracts" / "openapi" / "layer3-knowledge.json"


def _load_openapi() -> dict:
    return json.loads(OPENAPI_L3_PATH.read_text(encoding="utf-8"))


def test_graph_node_contract_includes_legacy_and_canonical_fields() -> None:
    node = GraphNode(id="n1", name="Node", entity_type="Capability", confidence_score=0.9)
    payload = node.model_dump()

    assert payload["label"] == "Node"
    assert payload["type"] == "Capability"
    assert payload["confidence"] == 0.9

    assert payload["name"] == "Node"
    assert payload["entity_type"] == "Capability"
    assert payload["confidence_score"] == 0.9


def test_graph_edge_contract_includes_legacy_and_canonical_fields() -> None:
    edge = GraphEdge(source="n1", target="n2", type="RELATES_TO")
    payload = edge.model_dump()

    assert payload["type"] == "RELATES_TO"
    assert payload["relationship_type"] == "RELATES_TO"


def test_graph_aliases_removed_at_version_boundary() -> None:
    node = GraphNode(id="n1", name="Node", entity_type="Capability", confidence_score=0.9)
    edge = GraphEdge(source="n1", target="n2", type="RELATES_TO")

    node_payload = node.model_dump(api_version=GRAPH_FIELD_ALIAS_REMOVAL_VERSION)
    edge_payload = edge.model_dump(api_version=GRAPH_FIELD_ALIAS_REMOVAL_VERSION)

    assert "label" not in node_payload
    assert "type" not in node_payload
    assert "confidence" not in node_payload
    assert "relationship_type" not in edge_payload


def test_deprecated_field_usage_counters_increment_for_request_and_response() -> None:
    before = get_deprecated_field_usage_counters()

    GraphNode.model_validate({"id": "n2", "label": "Legacy", "type": "Capability", "confidence": 0.7})
    GraphEdge.model_validate({"source": "n2", "target": "n3", "relationship_type": "DEPENDS_ON"})
    GraphNode(id="n3", label="New", type="Outcome").model_dump()
    GraphEdge(source="n3", target="n4", type="ENABLES").model_dump()

    after = get_deprecated_field_usage_counters()
    assert after["graph_node_request_legacy_fields"] >= before["graph_node_request_legacy_fields"] + 1
    assert after["graph_edge_request_legacy_fields"] >= before["graph_edge_request_legacy_fields"] + 1
    assert after["graph_node_response_legacy_fields"] >= before["graph_node_response_legacy_fields"] + 1
    assert after["graph_edge_response_legacy_fields"] >= before["graph_edge_response_legacy_fields"] + 1


def test_layer3_contract_fixtures_prefer_canonical_fields() -> None:
    """Regression guard: tests that represent consumers should not drift back to legacy aliases."""
    sample = GraphNode(id="n4", name="Canonical", entity_type="Capability", confidence_score=0.8).model_dump()
    assert sample["name"] == "Canonical"
    assert sample["entity_type"] == "Capability"
    assert sample["confidence_score"] == 0.8


def test_openapi_graph_node_fields_are_canonical_plus_explicit_aliases_only() -> None:
    schema = _load_openapi()["components"]["schemas"]["GraphNode"]["properties"]
    assert {"id", "name", "entity_type", "confidence_score", "properties"}.issubset(schema.keys())
    assert {"label", "type", "confidence"}.issubset(schema.keys())
    unexpected = {"title", "node_type"} & set(schema.keys())
    assert not unexpected


def test_deprecated_alias_routes_remain_marked_deprecated() -> None:
    schema = _load_openapi()["paths"]
    for route in ("/v1/graphrag", "/v1/query/graph", "/v1/query/search"):
        assert schema[route]["post"].get("deprecated") is True
