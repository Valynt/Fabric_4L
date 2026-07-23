from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pr-checks.yml"
CHECKER = ROOT / "scripts" / "ci" / "check_pip_audit_workflow.py"
AUDIT_HELPER = "../../scripts/ci/run_pip_audit.sh"


def test_layer_dependency_audits_use_the_repository_helper() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    audit_steps = [
        step
        for job in workflow["jobs"].values()
        for step in job.get("steps", [])
        if step.get("name") == "Dependency audit with pip-audit"
    ]

    assert len(audit_steps) == 6
    assert all(step.get("env", {}).get("PIP_AUDIT_VULNERABILITY_POLICY") == "any" for step in audit_steps)
    assert all(step.get("run") == AUDIT_HELPER for step in audit_steps)


def test_static_checker_accepts_the_repository_workflow() -> None:
    result = subprocess.run(
        [sys.executable, str(CHECKER), str(WORKFLOW)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr


def test_static_checker_rejects_unsupported_pip_audit_flags(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        "jobs:\n  audit:\n    steps:\n      - run: uv run pip-audit --severity high --exit-code 1\n",
        encoding="utf-8",
    )

    result = subprocess.run(
        [sys.executable, str(CHECKER), str(workflow)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "unsupported pip-audit option" in result.stderr
    assert "--severity" in result.stderr
    assert "--exit-code" in result.stderr


def test_structural_preflight_runs_the_static_checker() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    commands = [step.get("run", "") for step in workflow["jobs"]["structural-preflight"]["steps"]]

    assert "python scripts/ci/check_pip_audit_workflow.py" in commands
