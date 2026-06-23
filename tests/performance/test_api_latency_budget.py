"""Static and synthetic latency-budget checks for critical APIs."""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

pytestmark = [pytest.mark.performance]

SLO_PATH = Path("docs/slo/performance-slo.v1.json")
K6_CRITICAL_PATH = Path("tests/performance/k6/l2_l3_l4_critical_paths.js")

CRITICAL_ENDPOINTS = {
    "POST /v1/extract-and-ingest": {
        "metric": "l2_extract_ingest_duration_ms",
        "error_metric": "l2_extract_ingest_error_rate",
    },
    "POST /v1/search/hybrid": {
        "metric": "l3_hybrid_search_duration_ms",
        "error_metric": "l3_hybrid_search_error_rate",
    },
    "GET /workflows/active": {
        "metric": "l4_workflows_active_duration_ms",
        "error_metric": "l4_workflows_active_error_rate",
    },
}


def _slo_targets() -> dict[str, dict]:
    data = json.loads(SLO_PATH.read_text(encoding="utf-8"))
    return {target["api"]: target for target in data["targets"]}


def _k6_thresholds() -> dict[str, str]:
    source = K6_CRITICAL_PATH.read_text(encoding="utf-8")
    return dict(re.findall(r"(\w+): \['([^']+)'\]", source))


def test_critical_endpoints_have_versioned_latency_budgets() -> None:
    targets = _slo_targets()

    assert set(CRITICAL_ENDPOINTS).issubset(targets), "critical APIs must be covered by docs/slo/performance-slo.v1.json"

    for api, expected in CRITICAL_ENDPOINTS.items():
        target = targets[api]
        assert target["metric"] == expected["metric"]
        assert target["error_metric"] == expected["error_metric"]
        assert target["objective"]["stat"] == "p95"
        assert 0 < target["objective"]["max"] <= 5_000
        assert 0 <= target["error_objective"]["max"] <= 0.05
        assert target["breach_response"]["runbook"].endswith("slo-breach-response.md")


def test_k6_thresholds_match_versioned_slo_budgets() -> None:
    targets = _slo_targets()
    thresholds = _k6_thresholds()

    for api in CRITICAL_ENDPOINTS:
        target = targets[api]
        metric = target["metric"]
        error_metric = target["error_metric"]
        assert thresholds[metric] == f"p(95)<{target['objective']['max']}"
        assert thresholds[error_metric] == f"rate<{target['error_objective']['max']}"


def test_latency_regression_policy_allows_limited_burst_not_budget_escape() -> None:
    slo = json.loads(SLO_PATH.read_text(encoding="utf-8"))
    latency_regression_pct = slo["regression_policy"]["latency_regression_pct"]
    error_regression_abs = slo["regression_policy"]["error_rate_regression_abs"]

    for target in slo["targets"]:
        p95_budget = target["objective"]["max"]
        error_budget = target["error_objective"]["max"]
        assert p95_budget * (1 + latency_regression_pct) <= p95_budget * 1.25
        assert error_budget + error_regression_abs <= 0.055
