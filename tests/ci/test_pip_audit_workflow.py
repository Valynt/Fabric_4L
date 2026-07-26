from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "pr-checks.yml"
CHECKER = ROOT / "scripts" / "ci" / "check_pip_audit_workflow.py"
AUDIT_HELPER = 'bash "${{ github.workspace }}/scripts/ci/run_pip_audit.sh"'
EXPECTED_AUDIT_JOBS = {
    "layer1-checks",
    "layer2-checks",
    "layer3-checks",
    "layer4-checks",
    "layer5-checks",
    "layer6-checks",
}


def test_layer_dependency_audits_use_the_repository_helper() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    audit_steps = {}
    for job_name, job in workflow["jobs"].items():
        for step in job.get("steps", []):
            if step.get("name") == "Dependency audit with pip-audit":
                audit_steps[job_name] = step

    assert audit_steps.keys() == EXPECTED_AUDIT_JOBS
    assert all(step.get("env", {}).get("PIP_AUDIT_VULNERABILITY_POLICY") == "any" for step in audit_steps.values())
    assert all(step.get("run") == AUDIT_HELPER for step in audit_steps.values())


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


def test_static_checker_rejects_multiline_unsupported_pip_audit_flags(tmp_path: Path) -> None:
    workflow = tmp_path / "workflow.yml"
    workflow.write_text(
        "jobs:\n"
        "  audit:\n"
        "    steps:\n"
        "      - name: Dependency audit with pip-audit\n"
        "        run: |\n"
        "          uv run pip-audit \\\n"
        "            --severity high \\\n"
        "            --exit-code 1\n",
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


def test_static_checker_reports_unreadable_workflow(tmp_path: Path) -> None:
    missing_workflow = tmp_path / "missing.yml"

    result = subprocess.run(
        [sys.executable, str(CHECKER), str(missing_workflow)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 1
    assert "unable to read workflow" in result.stderr


def test_structural_preflight_runs_the_static_checker() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    commands = [step.get("run", "") for step in workflow["jobs"]["structural-preflight"]["steps"]]

    assert "python scripts/ci/check_pip_audit_workflow.py" in commands
