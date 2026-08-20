"""Regression coverage for heavy-workflow concurrency isolation."""

from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
HEAVY_WORKFLOWS = (
    "pr-checks.yml",
    "critical-gates.yml",
    "zero-trust-validation.yml",
    "release-evidence-bundle.yml",
    "prod-readiness.yml",
    "security-gates.yml",
)


@pytest.mark.parametrize("workflow_name", HEAVY_WORKFLOWS)
def test_heavy_workflow_concurrency_is_scoped_to_ref(workflow_name: str) -> None:
    path = REPO_ROOT / ".github" / "workflows" / workflow_name
    source = path.read_text(encoding="utf-8")
    workflow = yaml.safe_load(source)
    concurrency = workflow["concurrency"]

    assert concurrency["cancel-in-progress"] is True or concurrency["cancel-in-progress"] == "${{ github.ref != 'refs/heads/main' }}"
    assert "github.ref" in concurrency["group"]
    assert "-shared" not in concurrency["group"]
