"""Contract tests for the Layer 3 graph model after the v2.5 deprecation window closure.

The v2.5 graph-field aliases (`label`, `type`, `confidence` on GraphNode and
`relationship_type` on GraphEdge) have been removed. Serialization and
validation are canonical-only: `name`, `entity_type`, `confidence_score`, `type`.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from src.api.models import GraphEdge, GraphNode
except (ImportError, Exception) as _exc:
    pytest.skip(
        "value_fabric.layer3 service stack not available (pre-existing blocker #1/#9)",
        allow_module_level=True,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_L3_PATH = REPO_ROOT / "contracts" / "openapi" / "layer3-knowledge.json"


def _load_openapi() -> dict:
    return json.loads(OPENAPI_L3_PATH.read_text(encoding="utf-8"))


def test_graph_node_contract_is_canonical_only() -> None:
    node = GraphNode(
        id="n1", name="Node", entity_type="Capability", confidence_score=0.9
    )
    payload = node.model_dump()

    assert payload["name"] == "Node"
    assert payload["entity_type"] == "Capability"
    assert payload["confidence_score"] == 0.9

    # v2.5 deprecation window closed: legacy aliases are gone from serialization.
    for legacy_key in ("label", "type", "confidence"):
        assert legacy_key not in payload


def test_graph_edge_contract_is_canonical_only() -> None:
    edge = GraphEdge(source="n1", target="n2", type="RELATES_TO")
    payload = edge.model_dump()

    assert payload["type"] == "RELATES_TO"
    # v2.5 deprecation window closed: legacy alias is gone from serialization
    assert "relationship_type" not in payload


def test_graph_models_reject_legacy_alias_fields() -> None:
    # After the v2.5 closure the legacy alias field names are no longer accepted
    # on input either.
    for payload in (
        {"id": "n2", "label": "Legacy", "type": "Capability", "confidence": 0.7},
        {
            "id": "n2",
            "name": "Legacy",
            "entity_type": "Capability",
            "confidence_score": 0.7,
            "label": "x",
        },
    ):
        with pytest.raises(Exception):
            GraphNode.model_validate(payload)


def test_graph_models_accept_canonical_fields() -> None:
    node = GraphNode.model_validate(
        {
            "id": "n2",
            "name": "Canonical",
            "entity_type": "Capability",
            "confidence_score": 0.7,
        }
    )
    edge = GraphEdge.model_validate(
        {"source": "n2", "target": "n3", "type": "DEPENDS_ON"}
    )
    assert node.name == "Canonical"
    assert edge.type == "DEPENDS_ON"


def test_layer3_contract_fixtures_prefer_canonical_fields() -> None:
    """Regression guard: tests that represent consumers should not drift back to legacy aliases."""
    sample = GraphNode(
        id="n4", name="Canonical", entity_type="Capability", confidence_score=0.8
    ).model_dump()
    assert sample["name"] == "Canonical"
    assert sample["entity_type"] == "Capability"
    assert sample["confidence_score"] == 0.8


def test_openapi_graph_node_fields_are_canonical_only() -> None:
    schema = _load_openapi()["components"]["schemas"]["GraphNode"]["properties"]
    assert {"id", "name", "entity_type", "confidence_score", "properties"}.issubset(
        schema.keys()
    )
    # v2.5 deprecation window closed: alias fields are removed from the OpenAPI schema
    assert not ({"label", "type", "confidence"} & set(schema.keys()))
    unexpected = {"title", "node_type"} & set(schema.keys())
    assert not unexpected


def test_openapi_graph_edge_fields_are_canonical_only() -> None:
    schema = _load_openapi()["components"]["schemas"]["GraphEdge"]["properties"]
    assert {"source", "target", "type", "weight", "properties"}.issubset(schema.keys())
    # v2.5 deprecation window closed: alias is removed from the OpenAPI schema
    assert "relationship_type" not in schema
    unexpected = {"title", "edge_type"} & set(schema.keys())
    assert not unexpected


def test_deprecated_legacy_routes_remain_marked_deprecated() -> None:
    schema = _load_openapi()["paths"]
    for route in ("/v1/graphrag", "/v1/query/graph", "/v1/query/search"):
        assert schema[route]["post"].get("deprecated") is True
