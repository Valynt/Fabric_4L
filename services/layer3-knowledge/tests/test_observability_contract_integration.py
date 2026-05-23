import pytest
from fastapi.testclient import TestClient

from value_fabric.layer3.api.main import app


@pytest.mark.unit
def test_standard_observability_probes_and_correlation_header() -> None:
    client = TestClient(app)

    for path in ("/health", "/ready", "/metrics"):
        response = client.get(path)
        assert response.status_code in {200, 401, 503}

    trace_id = "trace-l3-123"
    health = client.get("/health", headers={"X-Trace-ID": trace_id})
    assert health.headers.get("X-Request-ID") == trace_id
    assert health.headers.get("X-Correlation-ID") == trace_id
    assert health.headers.get("X-Trace-ID") == trace_id


@pytest.mark.unit
def test_graph_specific_metrics_present_in_prometheus_output() -> None:
    """Assert that the four graph-specific SLO metrics are registered and emitted."""
    client = TestClient(app)
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text

    required_metrics = [
        "value_fabric_graph_traversal_depth_bucket",
        "value_fabric_graph_result_size_bucket",
        "value_fabric_graph_slow_queries_total",
        "value_fabric_tenant_isolation_violations_total",
    ]
    for metric in required_metrics:
        assert metric in body, f"Missing required graph metric: {metric}"
