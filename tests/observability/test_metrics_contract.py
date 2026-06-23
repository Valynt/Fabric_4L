from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

METRICS_SOURCES = {
    "api": REPO_ROOT / "services/api/app/core/metrics.py",
    "layer1": REPO_ROOT / "services/layer1-ingestion/src/metrics/prometheus_metrics.py",
    "layer2": REPO_ROOT / "services/layer2-extraction/src/layer2_extraction/metrics/prometheus_metrics.py",
    "layer3": REPO_ROOT / "services/layer3-knowledge/src/metrics/prometheus_metrics.py",
    "layer4": REPO_ROOT / "services/layer4-agents/src/layer4_agents/metrics/prometheus_metrics.py",
    "layer5": REPO_ROOT / "services/layer5-ground-truth/src/metrics/prometheus_metrics.py",
    "layer6": REPO_ROOT / "services/layer6-benchmarks/src/layer6_benchmarks/metrics/prometheus_metrics.py",
}


def test_maintained_services_have_success_failure_latency_metric_paths() -> None:
    for service, path in METRICS_SOURCES.items():
        source = path.read_text(encoding="utf-8")
        assert "Counter(" in source or "_record_counter" in source, f"{service} must expose counter metrics"
        assert "Histogram(" in source or "_observe_histogram" in source, f"{service} must expose latency histogram metrics"
        assert "duration" in source or "latency" in source, f"{service} must record latency"
        assert "status" in source or "outcome" in source, f"{service} must label success/failure outcomes"
        assert (
            "error" in source
            or "failure" in source
            or "5xx" in source
            or "status_class" in source
        ), f"{service} must record failures"


def test_retry_or_operation_metrics_exist_for_critical_flows() -> None:
    required_tokens = {
        "api": ("REQUESTS_TOTAL", "ERRORS_TOTAL", "REQUEST_LATENCY_SECONDS"),
        "layer1": ("retry_events_total", "queue_latency_seconds", "errors_total"),
        "layer2": ("record_retry", "record_extraction_outcome", "record_model_latency"),
        "layer3": ("database_operations_total", "graph_query_failures_total", "search_query_duration"),
        "layer4": ("workflow_executions_total", "repeated_workflow_failures_total", "workflow_duration"),
        "layer5": ("validations_total", "validation_transition_failures_total", "validation_latency_seconds"),
        "layer6": ("dataset_comparisons_total", "request_duration", "status_class"),
    }
    for service, tokens in required_tokens.items():
        source = METRICS_SOURCES[service].read_text(encoding="utf-8")
        for token in tokens:
            assert token in source, f"{service} metrics contract missing {token}"


def test_high_cardinality_metric_labels_are_bounded() -> None:
    bounded_sources = {
        "api": "_route_path",
        "layer1": "endpoint",
        "layer3": "_normalize_path",
        "layer4": "tenant_tier",
        "layer5": "PathNormalizer",
        "layer6": "PathNormalizer",
    }
    for service, token in bounded_sources.items():
        source = METRICS_SOURCES[service].read_text(encoding="utf-8")
        assert token in source, f"{service} metrics must bound path or tenant label cardinality"


def test_layer6_metrics_are_backed_by_json_contract() -> None:
    source = METRICS_SOURCES["layer6"].read_text(encoding="utf-8")
    assert "metric_spec_map" in source
    assert (REPO_ROOT / "contracts/observability/layer6-metrics.json").exists()
