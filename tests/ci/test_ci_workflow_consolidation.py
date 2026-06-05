from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOW_DIR = REPO_ROOT / ".github" / "workflows"
PLAN = REPO_ROOT / "docs" / "operations" / "ci-workflow-consolidation.md"

CANONICAL_WORKFLOWS = {
    "pr-checks.yml",
    "security-gates.yml",
    "contract-compliance.yml",
    "launch-readiness.yml",
}

DEPRECATION_CANDIDATES = {
    "test.yml": "Legacy monolithic test workflow",
    "critical-gates.yml": "Overlaps auth coverage, tenant isolation, OpenAPI drift, and config gates",
    "prod-readiness.yml": "Older production-readiness gate",
}

ADDITIONAL_INVENTORY_CANDIDATES = {
    "chaos-smoke.yml": "Overlaps broader chaos and smoke validation",
    "codeql-analysis.yml": "Potential duplicate of `codeql.yml`",
    "deploy.yml": "Potential duplicate deployment surface",
}


def test_ci_workflow_consolidation_plan_names_canonical_owners() -> None:
    content = PLAN.read_text(encoding="utf-8")

    for workflow in CANONICAL_WORKFLOWS:
        assert workflow in content
        assert (WORKFLOW_DIR / workflow).exists(), f"Missing canonical workflow: {workflow}"


def test_ci_workflow_deprecation_candidates_are_documented_but_still_enabled() -> None:
    content = PLAN.read_text(encoding="utf-8")

    for workflow, reason in DEPRECATION_CANDIDATES.items():
        path = WORKFLOW_DIR / workflow
        assert path.exists(), f"Missing deprecation candidate workflow: {workflow}"
        assert workflow in content
        assert reason in content

        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        assert isinstance(data, dict)
        assert data.get("on") or data.get(True), f"{workflow} should remain enabled until replacement proof exists"


def test_ci_workflow_inventory_records_current_over_50_state_without_deleting_gates() -> None:
    workflow_files = sorted(
        path.name
        for path in WORKFLOW_DIR.iterdir()
        if path.suffix in {".yml", ".yaml"}
    )
    assert len(workflow_files) > 50, "S6-6 should not be marked closed until actual consolidation is complete"

    content = PLAN.read_text(encoding="utf-8")
    assert "The repository currently carries more than 50 workflow files" in content
    assert "workflow-registry.json" in content

    for workflow, reason in ADDITIONAL_INVENTORY_CANDIDATES.items():
        assert workflow in workflow_files
        assert workflow in content
        assert reason in content


def test_ci_workflow_cleanup_rules_preserve_required_gate_visibility() -> None:
    content = PLAN.read_text(encoding="utf-8")

    required_rules = [
        "Do not delete or disable a workflow",
        "Do not rename required workflow or job names",
        "Keep security and contract gates visible",
    ]
    for rule in required_rules:
        assert rule in content
