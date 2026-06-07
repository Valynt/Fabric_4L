import pytest
from fastapi.testclient import TestClient

from src.api.main import app


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
    from metrics.prometheus_metrics import PrometheusMetrics, MetricsConfig

    metrics = PrometheusMetrics(MetricsConfig())

    # Exercise each metric so they appear in output
    metrics.observe_graph_traversal_depth(depth=5, endpoint="/test", operation="test")
    metrics.observe_graph_result_size(size=10, endpoint="/test", operation="test")
    metrics.increment_graph_slow_queries(operation="test", threshold_bucket=">1s")
    metrics.increment_tenant_isolation_violation(component="test", violation_type="test")
    metrics.increment_graph_mutation_success(operation_type="merge", route="/graph/mutate")
    metrics.increment_graph_query_failure(category="timeout", operation="run", route="tenant_query_executor")
    metrics.increment_unauthorized_traversal(category="tenant_boundary", route="tenant_query_executor", violation_type="missing_tenant_context")
    metrics.increment_index_constraint_health_failure(check_type="vector_index", component="capability_embedding_idx")

    body = metrics.get_metrics()

    required_metrics = [
        "value_fabric_graph_traversal_depth_bucket",
        "value_fabric_graph_result_size_bucket",
        "value_fabric_graph_slow_queries_total",
        "value_fabric_tenant_isolation_violations_total",
        "value_fabric_graph_mutations_total",
        "value_fabric_graph_mutation_rate",
        "value_fabric_graph_query_failures_total",
        "value_fabric_unauthorized_traversals_total",
        "value_fabric_graph_index_constraint_health_failures_total",
    ]
    for metric in required_metrics:
        assert metric in body, f"Missing required graph metric: {metric}"
