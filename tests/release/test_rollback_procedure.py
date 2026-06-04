"""Release checks for rollback procedure documentation and CI fail-closed behavior."""

from __future__ import annotations

from pathlib import Path

import yaml


ROLLBACK_RUNBOOK = Path("docs/runbooks/deployment/rollback-production-release.md")
FAILED_DEPLOYMENT_RUNBOOK = Path("docs/runbooks/deployment/failed-deployment.md")
PROMOTION_WORKFLOW = Path(".github/workflows/environment-promotion.yml")
POLICY_FILE = Path(".fabric/prod-gates.policy.yaml")


def test_rollback_runbook_documents_decision_and_validation_controls() -> None:
    text = ROLLBACK_RUNBOOK.read_text(encoding="utf-8").lower()
    for marker in (
        "freeze new deploys",
        "last known-good",
        "database owner",
        "traffic",
        "feature flags",
        "error rate",
        "p95 latency",
        "tenant-isolation",
        "evidence to preserve",
    ):
        assert marker in text, f"Rollback runbook missing {marker!r}"


def test_failed_deployment_runbook_blocks_promotion_and_preserves_evidence() -> None:
    text = FAILED_DEPLOYMENT_RUNBOOK.read_text(encoding="utf-8").lower()
    for marker in (
        "stop automatic promotion",
        "freeze unrelated production changes",
        "preserve ci logs",
        "canary",
        "rollback",
        "full required release validation",
    ):
        assert marker in text, f"Failed deployment runbook missing {marker!r}"


def test_environment_promotion_workflow_blocks_failed_deployments_and_triggers_rollback() -> None:
    workflow = yaml.safe_load(PROMOTION_WORKFLOW.read_text(encoding="utf-8"))
    jobs = workflow["jobs"]
    assert jobs["validate-build"]["if"] == (
        "github.event.workflow_run.conclusion == 'success' || github.event_name == 'workflow_dispatch'"
    )
    assert "rollback-on-failure" in jobs
    assert jobs["rollback-on-failure"]["if"] == "failure()"

    validate_build_text = str(jobs["validate-build"])
    assert "promotion blocked" in validate_build_text.lower()
    assert "exit 1" in validate_build_text


def test_release_policy_includes_blocking_rollback_readiness_gate() -> None:
    policy = yaml.safe_load(POLICY_FILE.read_text(encoding="utf-8"))
    gate = policy["gate-definitions"]["rollback-readiness"]
    assert gate["target"] == "gate-rollback-readiness"
    assert gate["class"] == "blocking"
    assert gate["required"] is True
    assert "rollback-readiness" in policy["profiles"]["tier1-beta-readiness"]["gates"]
