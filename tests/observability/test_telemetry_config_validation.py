"""Tests proving Prometheus/Grafana config parses and metric labels are safe.

These tests are static checks — they do not require a running Prometheus or
Grafana instance.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]

PROMETHEUS_YML = REPO_ROOT / "monitoring" / "prometheus" / "prometheus.yml"
BLACKBOX_TARGETS = REPO_ROOT / "monitoring" / "prometheus" / "blackbox-targets.yml"
LAYER6_METRICS_JSON = REPO_ROOT / "contracts" / "observability" / "layer6-metrics.json"

# Services that must have a scrape target in prometheus.yml.
EXPECTED_SCRAPE_JOBS = {
    "prometheus",
    "layer1-ingestion",
    "layer2-extraction",
    "layer3-knowledge",
    "layer4-agents",
    "layer5-ground-truth",
    "layer6-benchmarks",
    "blackbox-health",
    "blackbox-metrics",
}

# Metric name substrings that must exist across the platform source files.
# We check for substrings because the prefix is a variable (e.g. f"{prefix}...").
EXPECTED_METRIC_SUBSTRINGS = [
    "http_requests_total",
    "http_request_duration_seconds",
    "auth_failures_total",
    "errors_total",
]

# Full metric names that must appear in the Layer 6 JSON contract.
EXPECTED_L6_METRIC_NAMES = {
    "layer6_requests_total",
    "layer6_request_duration_seconds",
    "layer6_dataset_comparisons_total",
    "layer6_health_status",
    "layer6_errors_total",
    "layer6_auth_failures_total",
}

# VF-prefixed metric names that must appear in Layer 2 sources.
EXPECTED_VF_METRIC_NAMES = {
    "vf_extraction_outcomes_total",
    "vf_auth_failures_total",
}

# High-cardinality or sensitive labels that must NOT appear in .labels() calls.
FORBIDDEN_LABEL_TOKENS = (
    "tenant_id",
    "user_id",
    "email",
    "secret",
    "password",
    "document",
    "prompt",
)


def _extract_label_keys(source: str) -> list[tuple[str, str]]:
    """Extract (metric_name, label_key) pairs from .labels(...) calls."""
    results: list[tuple[str, str]] = []
    label_call = re.compile(
        r'self\._metrics\["(\w+)"\]\.labels\(([^)]*)\)',
        re.DOTALL,
    )
    for match in label_call.finditer(source):
        metric_name = match.group(1)
        kwargs_body = match.group(2)
        for kwarg in re.finditer(r'(\w+)\s*=', kwargs_body):
            results.append((metric_name, kwarg.group(1)))
    return results


def _load_prometheus_yml() -> dict:
    return yaml.safe_load(PROMETHEUS_YML.read_text(encoding="utf-8"))


def _load_blackbox_targets() -> dict:
    return yaml.safe_load(BLACKBOX_TARGETS.read_text(encoding="utf-8"))


def _load_layer6_metrics_json() -> dict:
    return json.loads(LAYER6_METRICS_JSON.read_text(encoding="utf-8"))


def test_prometheus_yml_parses() -> None:
    data = _load_prometheus_yml()
    assert "scrape_configs" in data
    assert isinstance(data["scrape_configs"], list)


def test_blackbox_targets_parse() -> None:
    data = _load_blackbox_targets()
    assert "scrape_configs" in data


def test_layer6_metrics_json_parses() -> None:
    data = _load_layer6_metrics_json()
    assert "metrics" in data
    assert len(data["metrics"]) > 0


def test_all_services_have_scrape_targets() -> None:
    data = _load_prometheus_yml()
    job_names = {job.get("job_name") for job in data["scrape_configs"]}
    missing = EXPECTED_SCRAPE_JOBS - job_names
    assert not missing, f"Missing scrape jobs: {missing}"


def test_blackbox_targets_have_required_relabel_configs() -> None:
    data = _load_blackbox_targets()
    for job in data["scrape_configs"]:
        assert "relabel_configs" in job, f"Job {job.get('job_name')} missing relabel_configs"
        replacements = {
            r.get("replacement") for r in job["relabel_configs"] if "replacement" in r
        }
        assert "blackbox-exporter:9115" in replacements


def test_layer6_metrics_json_has_required_metrics() -> None:
    data = _load_layer6_metrics_json()
    names = {m["name"] for m in data["metrics"]}
    missing = EXPECTED_L6_METRIC_NAMES - names
    assert not missing, f"Layer 6 metrics contract missing: {missing}"


def test_layer6_metrics_json_labels_are_bounded() -> None:
    """Every metric in the JSON contract must declare max_cardinality for every label."""
    data = _load_layer6_metrics_json()
    for metric in data["metrics"]:
        labels = set(metric["labels"])
        cardinality = metric.get("max_cardinality", {})
        missing = labels - set(cardinality.keys())
        assert not missing, (
            f"Metric {metric['name']} missing cardinality bounds for: {missing}"
        )


def test_no_forbidden_labels_in_metrics_sources() -> None:
    """Assert no .labels() call emits raw tenant_id / user_id / email / secret."""
    metrics_sources = [
        REPO_ROOT / "services" / "layer1-ingestion" / "src" / "metrics" / "prometheus_metrics.py",
        REPO_ROOT / "services" / "layer2-extraction" / "src" / "layer2_extraction" / "metrics" / "prometheus_metrics.py",
        REPO_ROOT / "services" / "layer5-ground-truth" / "src" / "metrics" / "prometheus_metrics.py",
        REPO_ROOT / "services" / "layer6-benchmarks" / "src" / "layer6_benchmarks" / "metrics" / "prometheus_metrics.py",
    ]
    for path in metrics_sources:
        if not path.exists():
            continue
        source = path.read_text(encoding="utf-8")
        for metric_name, label_key in _extract_label_keys(source):
            assert label_key not in FORBIDDEN_LABEL_TOKENS, (
                f"{path}: metric {metric_name} emits forbidden label '{label_key}'"
            )


def test_no_raw_tenant_id_in_prometheus_yml_scrape_labels() -> None:
    """Assert prometheus.yml does not set tenant_id as a label in scrape configs."""
    data = _load_prometheus_yml()
    for job in data["scrape_configs"]:
        static_configs = job.get("static_configs", [])
        for cfg in static_configs:
            labels = cfg.get("labels", {})
            assert "tenant_id" not in labels, (
                f"Job {job.get('job_name')} sets raw tenant_id label"
            )


def test_expected_metric_substrings_are_defined_in_sources() -> None:
    """Assert each expected metric substring appears in at least one source file."""
    metrics_sources = [
        REPO_ROOT / "services" / "layer1-ingestion" / "src" / "metrics" / "prometheus_metrics.py",
        REPO_ROOT / "services" / "layer2-extraction" / "src" / "layer2_extraction" / "metrics" / "prometheus_metrics.py",
        REPO_ROOT / "services" / "layer5-ground-truth" / "src" / "metrics" / "prometheus_metrics.py",
        REPO_ROOT / "services" / "layer6-benchmarks" / "src" / "layer6_benchmarks" / "metrics" / "prometheus_metrics.py",
    ]
    all_source = "\n".join(
        p.read_text(encoding="utf-8") if p.exists() else "" for p in metrics_sources
    )
    missing = [s for s in EXPECTED_METRIC_SUBSTRINGS if s not in all_source]
    assert not missing, f"Expected metric substrings not found in any source: {missing}"


def test_expected_vf_metric_names_in_layer2() -> None:
    """Assert VF-prefixed metric names appear in Layer 2 sources."""
    path = REPO_ROOT / "services" / "layer2-extraction" / "src" / "layer2_extraction" / "metrics" / "prometheus_metrics.py"
    if not path.exists():
        return
    source = path.read_text(encoding="utf-8")
    missing = {s for s in EXPECTED_VF_METRIC_NAMES if s not in source}
    assert not missing, f"Layer 2 missing VF metric names: {missing}"


def test_expected_l6_metric_names_in_contract() -> None:
    """Assert Layer 6 metric names appear in the JSON contract."""
    data = _load_layer6_metrics_json()
    names = {m["name"] for m in data["metrics"]}
    missing = EXPECTED_L6_METRIC_NAMES - names
    assert not missing, f"Layer 6 JSON contract missing metric names: {missing}"


def test_prometheus_yml_has_blackbox_alertmanager() -> None:
    data = _load_prometheus_yml()
    alerting = data.get("alerting", {})
    managers = alerting.get("alertmanagers", [])
    assert managers, "No alertmanager targets configured"
