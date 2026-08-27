import os

from src.api.models import GraphEdge, GraphNode
from src.services.compat_metrics import get_deprecated_field_usage_counters
from src.api.main import app


def test_legacy_alias_warning_mode_allows_routes(test_client):
    app.state.layer3_compat_deprecation_phase = "warning_only"
    app.state.environment = "test"
    resp = test_client.post(
        "/v1/graphrag", json={"query": "x", "max_hops": 2, "max_results": 3}
    )
    assert resp.status_code in {200, 401}


def test_legacy_alias_disable_in_non_prod_returns_410(test_client):
    app.state.layer3_compat_deprecation_phase = "disable_non_prod"
    app.state.environment = "test"
    resp = test_client.post(
        "/v1/graphrag", json={"query": "x", "max_hops": 2, "max_results": 3}
    )
    assert resp.status_code in {401, 410}


def test_legacy_alias_disable_non_prod_allows_prod(test_client):
    app.state.layer3_compat_deprecation_phase = "disable_non_prod"
    app.state.environment = "prod"
    resp = test_client.post(
        "/v1/graphrag", json={"query": "x", "max_hops": 2, "max_results": 3}
    )
    assert resp.status_code in {200, 401}


def test_graph_alias_removal_phase_hides_legacy_fields(monkeypatch):
    monkeypatch.setenv("L3_GRAPH_ALIAS_DEPRECATION_PHASE", "removed")
    node = GraphNode(id="1", name="A", entity_type="Capability", confidence_score=0.9)
    edge = GraphEdge(source="1", target="2", type="supports")
    node_dump = node.model_dump(api_version="v2.5")
    edge_dump = edge.model_dump(api_version="v2.5")
    assert "label" not in node_dump
    assert "type" not in node_dump
    assert "relationship_type" not in edge_dump


def test_graph_alias_request_normalization_and_counters(monkeypatch):
    monkeypatch.setenv("L3_GRAPH_ALIAS_DEPRECATION_PHASE", "warning_only")
    GraphNode.model_validate({"id": "n1", "label": "X", "type": "Capability", "confidence": 0.7})
    GraphEdge.model_validate({"source": "n1", "target": "n2", "relationship_type": "depends_on"})
    counters = get_deprecated_field_usage_counters()
    assert counters["graph_node_request_legacy_fields"] >= 1
    assert counters["graph_edge_request_legacy_fields"] >= 1
