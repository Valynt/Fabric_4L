"""Release checks for static canary promotion gates."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml


ROLLOUT_FILES = [
    Path("k8s/gitops/rollouts/layer1-ingestion-rollout.yaml"),
    Path("k8s/gitops/rollouts/layer4-agents-rollout.yaml"),
]
HEALTH_GATES = Path("k8s/gitops/rollouts/health-gates.yaml")
FLAGGER_CANARY = Path("k8s/feature-flags/flagger-canary.yaml")


def _docs(path: Path) -> list[dict[str, Any]]:
    return [doc for doc in yaml.safe_load_all(path.read_text(encoding="utf-8")) if isinstance(doc, dict)]


def _analysis_template_names(path: Path) -> set[str]:
    return {
        str(doc.get("metadata", {}).get("name"))
        for doc in _docs(path)
        if doc.get("kind") == "AnalysisTemplate"
    }


def _analysis_steps_before_full_promotion(rollout: dict[str, Any]) -> list[dict[str, Any]]:
    steps = rollout["spec"]["strategy"]["canary"]["steps"]
    selected: list[dict[str, Any]] = []
    for step in steps:
        if step.get("setWeight") == 100:
            break
        if "analysis" in step:
            selected.append(step)
    return selected


def test_rollout_manifests_have_health_probes_and_auto_rollback() -> None:
    for path in ROLLOUT_FILES:
        rollout = next(doc for doc in _docs(path) if doc.get("kind") == "Rollout")
        canary = rollout["spec"]["strategy"]["canary"]
        assert canary["autoRollbackEnabled"] is True
        assert canary["maxUnavailable"] == 0

        containers = rollout["spec"]["template"]["spec"]["containers"]
        for container in containers:
            assert "livenessProbe" in container, f"{path} missing livenessProbe"
            assert "readinessProbe" in container, f"{path} missing readinessProbe"


def test_canary_analysis_runs_before_full_traffic_promotion() -> None:
    for path in ROLLOUT_FILES:
        rollout = next(doc for doc in _docs(path) if doc.get("kind") == "Rollout")
        analysis_steps = _analysis_steps_before_full_promotion(rollout)
        assert analysis_steps, f"{path} promotes to 100% without analysis"


def test_canary_promotion_requires_error_rate_and_latency_templates() -> None:
    expected = {
        ROLLOUT_FILES[0]: {"ingestion-success-rate", "ingestion-error-rate", "ingestion-latency"},
        ROLLOUT_FILES[1]: {"success-rate", "error-rate", "latency"},
    }
    for path, required_templates in expected.items():
        rollout = next(doc for doc in _docs(path) if doc.get("kind") == "Rollout")
        templates = _analysis_template_names(path)
        used_templates = {
            template["templateName"]
            for step in _analysis_steps_before_full_promotion(rollout)
            for template in step["analysis"].get("templates", [])
        }
        assert required_templates <= templates
        assert required_templates <= used_templates


def test_health_gate_analysis_defines_health_error_and_latency_checks() -> None:
    text = HEALTH_GATES.read_text(encoding="utf-8")
    for marker in ("environment-health", "error-rate-gate", "rollback-decision", "LATENCY", "failureLimit"):
        assert marker in text


def test_flagger_canary_keeps_pre_rollout_health_and_metric_thresholds() -> None:
    canary = next(doc for doc in _docs(FLAGGER_CANARY) if doc.get("kind") == "Canary")
    analysis = canary["spec"]["analysis"]
    metrics = {metric["name"]: metric for metric in analysis["metrics"]}
    assert analysis["threshold"] > 0
    assert analysis["maxWeight"] < 100
    assert "request-success-rate" in metrics
    assert "request-duration" in metrics
    assert metrics["request-success-rate"]["thresholdRange"]["min"] >= 99
    assert metrics["request-duration"]["thresholdRange"]["max"] <= 500
    webhook_types = {hook["type"] for hook in analysis["webhooks"]}
    assert {"pre-rollout", "rollback"} <= webhook_types
