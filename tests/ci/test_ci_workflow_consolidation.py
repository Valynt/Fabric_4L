from __future__ import annotations

import json
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
REGISTRY = WORKFLOW_DIR / "workflow-registry.json"
PLAN = REPO_ROOT / "docs" / "operations" / "ci-workflow-consolidation.md"

CANONICAL_WORKFLOWS = {
    "pr-checks.yml",
    "security-gates.yml",
    "contract-compliance.yml",
    "prod-readiness.yml",
    "codeql.yml",
    "chaos-testing.yml",
    "dr-drill.yml",
    "k8s-readiness.yml",
    "repo-hygiene.yml",
    "supply-chain.yml",
    "performance-load-tests.yml",
}

RETIRED_WORKFLOWS = {
    "audit-snapshot.yml",
    "chaos-engineering.yml",
    "chaos-smoke.yml",
    "ci-failure-backlog.yml",
    "cleanup-branches.yml",
    "codeql-analysis.yml",
    "compliance-evidence-integrity.yml",
    "game-day-evidence.yml",
    "integration-tests.yml",
    "k8s-validation.yml",
    "launch-readiness.yml",
    "layer6-dashboard-metric-drift.yml",
    "live-workflow-validation.yml",
    "package-manager-policy.yml",
    "package-sign.yml",
    "performance-baseline.yml",
    "pr-performance-gate.yml",
    "preflight.yml",
    "production-readiness-check.yml",
    "refresh-testing-kpis.yml",
    "regenerate-sdk.yml",
    "restore-verification.yml",
    "secret-guardrails.yml",
    "security-validation.yml",
    "smoke-gate.yml",
    "stale.yml",
    "test-mandatory.yml",
    "test.yml",
    "verify-gate.yml",
    "workflow-readme-sync-check.yml",
}

CONSOLIDATION_PROOF_CANDIDATES = {
    "codeql-analysis.yml": {
        "canonical": ["codeql.yml"],
        "status": "retired-recorded",
        "risk": "needs branch-protection update",
        "required_phrase": "both CodeQL workflows were blocking",
    },
    "chaos-smoke.yml": {
        "canonical": ["chaos-testing.yml"],
        "status": "retired-recorded",
        "risk": "needs branch-protection update",
        "required_phrase": "PR-triggered and blocking",
    },
    "deploy.yml": {
        "canonical": ["build-deploy.yml", "environment-promotion.yml"],
        "status": "present-blocked",
        "risk": "not safe",
        "required_phrase": "workflow-call deployment behavior",
    },
}


def _workflow_files() -> set[str]:
    return {
        path.name
        for path in WORKFLOW_DIR.iterdir()
        if path.suffix in {".yml", ".yaml"}
    }


def _registry_workflows() -> set[str]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {Path(workflow["path"]).name for workflow in data["workflows"]}


def _registry_workflow_map() -> dict[str, dict]:
    data = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {
        Path(workflow["path"]).name: workflow
        for workflow in data["workflows"]
    }


def _workflow_data(workflow: str) -> dict:
    data = yaml.safe_load((WORKFLOW_DIR / workflow).read_text(encoding="utf-8"))
    assert isinstance(data, dict), f"{workflow} should parse as a workflow mapping"
    return data


def _workflow_triggers(workflow: str) -> set[str]:
    triggers = _workflow_data(workflow).get("on", _workflow_data(workflow).get(True, {}))
    if isinstance(triggers, str):
        return {triggers}
    if isinstance(triggers, list):
        return {str(trigger) for trigger in triggers}
    if isinstance(triggers, dict):
        return {str(trigger) for trigger in triggers}
    return set()


def _workflow_jobs(workflow: str) -> set[str]:
    jobs = _workflow_data(workflow).get("jobs", {})
    assert isinstance(jobs, dict), f"{workflow} should define jobs"
    return set(jobs)


def test_ci_workflow_consolidation_plan_names_canonical_owners() -> None:
    content = PLAN.read_text(encoding="utf-8")

    for workflow in CANONICAL_WORKFLOWS:
        assert workflow in content
        assert (WORKFLOW_DIR / workflow).exists(), f"Missing canonical workflow: {workflow}"


def test_ci_workflow_retired_candidates_are_documented_and_removed() -> None:
    content = PLAN.read_text(encoding="utf-8")
    workflow_files = _workflow_files()
    registry_workflows = _registry_workflows()

    for workflow in RETIRED_WORKFLOWS:
        assert workflow not in workflow_files, f"Retired workflow still exists: {workflow}"
        assert workflow not in registry_workflows, f"Retired workflow still registered: {workflow}"
        assert workflow in content


def test_ci_workflow_inventory_stays_within_s6_6_limit() -> None:
    workflow_files = _workflow_files()
    assert len(workflow_files) <= 55

    content = PLAN.read_text(encoding="utf-8")
    assert "at most 55 workflow YAML files" in content
    assert "workflow-registry.json" in content


def test_ci_workflow_cleanup_rules_preserve_required_gate_visibility() -> None:
    content = PLAN.read_text(encoding="utf-8")

    required_rules = [
        "Keep branch-protected check names aligned",
        "Add future workflow behavior as a job/profile",
        "Run `python scripts/ci/verify_workflow_registry.py`",
    ]
    for rule in required_rules:
        assert rule in content


def test_ci_workflow_consolidation_proof_records_deletion_risk() -> None:
    content = PLAN.read_text(encoding="utf-8")
    registry = _registry_workflow_map()
    workflow_files = _workflow_files()

    for workflow, proof in CONSOLIDATION_PROOF_CANDIDATES.items():
        assert workflow in content
        assert proof["status"] in content
        assert proof["risk"] in content
        assert proof["required_phrase"] in content

        for canonical in proof["canonical"]:
            assert canonical in content
            assert canonical in workflow_files

        if workflow not in workflow_files:
            assert proof["status"] == "retired-recorded"
            assert workflow not in registry
            continue

        assert proof["status"] == "present-blocked"
        assert workflow in registry
        duplicate = registry[workflow]
        canonical_entries = [registry[canonical] for canonical in proof["canonical"]]

        duplicate_triggers = _workflow_triggers(workflow)
        canonical_triggers = set().union(
            *(_workflow_triggers(canonical) for canonical in proof["canonical"])
        )
        duplicate_jobs = _workflow_jobs(workflow)
        canonical_jobs = set().union(
            *(_workflow_jobs(canonical) for canonical in proof["canonical"])
        )
        duplicate_secrets = set(duplicate.get("required_secrets", []))
        canonical_secrets = set().union(
            *(set(canonical.get("required_secrets", [])) for canonical in canonical_entries)
        )
        duplicate_artifacts = set(duplicate.get("produced_artifacts", []))
        canonical_artifacts = set().union(
            *(set(canonical.get("produced_artifacts", [])) for canonical in canonical_entries)
        )

        for trigger in duplicate_triggers - canonical_triggers:
            assert trigger in content
        for job in duplicate_jobs - canonical_jobs:
            assert job in content
        for secret in duplicate_secrets - canonical_secrets:
            assert secret in content
        for artifact in duplicate_artifacts - canonical_artifacts:
            assert artifact in content
