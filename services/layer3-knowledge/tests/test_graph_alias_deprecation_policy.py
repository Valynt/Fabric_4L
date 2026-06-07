from src.api.models import (
    GRAPH_FIELD_ALIAS_REMOVAL_VERSION,
    _include_legacy_graph_aliases,
    _serialize_entity,
    _serialize_relationship,
)


def test_legacy_aliases_present_before_removal_version() -> None:
    entity = {"id": "n1", "label": "Node", "type": "Capability", "confidence": 0.9}
    serialized = _serialize_entity(entity, api_version="v2.3")

    assert serialized["name"] == "Node"
    assert serialized["entity_type"] == "Capability"
    assert serialized["confidence_score"] == 0.9
    assert serialized["label"] == "Node"
    assert serialized["type"] == "Capability"
    assert serialized["confidence"] == 0.9


def test_legacy_aliases_removed_at_removal_version() -> None:
    entity = {"id": "n1", "label": "Node", "type": "Capability", "confidence": 0.9}
    serialized = _serialize_entity(entity, api_version=GRAPH_FIELD_ALIAS_REMOVAL_VERSION)

    assert serialized["name"] == "Node"
    assert serialized["entity_type"] == "Capability"
    assert serialized["confidence_score"] == 0.9
    assert "label" not in serialized
    assert "type" not in serialized
    assert "confidence" not in serialized


def test_relationship_alias_behavior_across_boundary() -> None:
    class _Rel(dict):
        type = "ENABLES"
        start_node = {"id": "s1"}
        end_node = {"id": "t1"}

    rel = _Rel()

    before = _serialize_relationship(rel, api_version="v2.3")
    after = _serialize_relationship(rel, api_version=GRAPH_FIELD_ALIAS_REMOVAL_VERSION)

    assert before["type"] == "ENABLES"
    assert before["relationship_type"] == "ENABLES"
    assert after["type"] == "ENABLES"
    assert "relationship_type" not in after


def test_schedule_boundary_helper() -> None:
    assert _include_legacy_graph_aliases("v2.3") is True
    assert _include_legacy_graph_aliases("v2.4") is True
    assert _include_legacy_graph_aliases("v2.5") is False
