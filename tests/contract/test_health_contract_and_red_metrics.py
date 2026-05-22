from __future__ import annotations

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / "contracts/jsonschema/system-route-health.json"

HEALTH_FILES = [
    "services/layer2-extraction/src/layer2_extraction/api/main.py",
    "services/layer3-knowledge/src/api/routes/system.py",
    "services/layer4-agents/src/api/core_routes.py",
]

METRICS_FILES = [
    "services/layer1-ingestion/src/metrics/prometheus_metrics.py",
    "services/layer4-agents/src/metrics/prometheus_metrics.py",
    "services/layer5-ground-truth/src/metrics/prometheus_metrics.py",
    "services/layer6-benchmarks/src/metrics/prometheus_metrics.py",
]


def test_health_schema_requires_dependency_status_and_failure_reason() -> None:
    schema = json.loads(SCHEMA_PATH.read_text(encoding="utf-8"))
    assert "dependencies" in schema["required"]
    dep_item = schema["properties"]["dependencies"]["items"]
    assert dep_item["required"] == ["name", "status", "failure_reason"]


def test_service_health_implementations_emit_failure_reason_contract_field() -> None:
    for rel_path in HEALTH_FILES:
        source = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "failure_reason" in source, f"Expected failure_reason in {rel_path}"


def test_red_metric_exports_include_tenant_label_where_required() -> None:
    for rel_path in METRICS_FILES:
        source = (REPO_ROOT / rel_path).read_text(encoding="utf-8")
        assert "tenant_id" in source, f"Expected tenant_id label plumbing in {rel_path}"
