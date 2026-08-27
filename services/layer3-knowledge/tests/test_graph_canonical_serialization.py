from src.api.models import GraphEdge, GraphNode


def test_graph_node_serialization_is_canonical() -> None:
    node = GraphNode(
        id="n1", name="Node", entity_type="Capability", confidence_score=0.9
    )
    payload = node.model_dump()

    # Canonical fields only — legacy aliases have been removed in v2.5.
    assert payload["name"] == "Node"
    assert payload["entity_type"] == "Capability"
    assert payload["confidence_score"] == 0.9
    assert "label" not in payload
    assert "type" not in payload
    assert "confidence" not in payload


def test_graph_node_accepts_canonical_fields_only() -> None:
    node = GraphNode.model_validate(
        {
            "id": "n2",
            "name": "Node",
            "entity_type": "Capability",
            "confidence_score": 0.7,
        }
    )
    assert node.name == "Node"
    assert node.entity_type == "Capability"
    assert node.confidence_score == 0.7


def test_graph_edge_serialization_is_canonical() -> None:
    edge = GraphEdge(source="n1", target="n2", type="RELATES_TO")
    payload = edge.model_dump()

    assert payload["type"] == "RELATES_TO"
    assert "relationship_type" not in payload
