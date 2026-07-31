"""Contracts for fail-closed Trivy base-versus-head comparison."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "ci" / "check_trivy_pr_delta.py"
WORKFLOW = ROOT / ".github" / "workflows" / "security-gates.yml"


def _sarif(path: Path, results: list[dict]) -> None:
    path.write_text(
        json.dumps({"version": "2.1.0", "runs": [{"results": results}]}),
        encoding="utf-8",
    )


def _finding(rule: str, path: str, line: int, message: str = "finding") -> dict:
    return {
        "ruleId": rule,
        "level": "error",
        "message": {"text": message},
        "locations": [
            {
                "physicalLocation": {
                    "artifactLocation": {"uri": path},
                    "region": {"startLine": line},
                }
            }
        ],
    }


def _run(base: Path, head: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--base", str(base), "--head", str(head)],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )


def test_existing_finding_remains_visible_without_failing_delta(tmp_path: Path) -> None:
    base = tmp_path / "base.sarif"
    head = tmp_path / "head.sarif"
    finding = _finding("CVE-1", "lock.yaml", 4)
    _sarif(base, [finding])
    _sarif(head, [finding])

    result = _run(base, head)

    assert result.returncode == 0
    assert "1 head findings" in result.stdout
    assert "0 new findings" in result.stdout


def test_new_or_changed_finding_fails_closed_without_echoing_message(tmp_path: Path) -> None:
    base = tmp_path / "base.sarif"
    head = tmp_path / "head.sarif"
    _sarif(base, [])
    _sarif(head, [_finding("CVE-2", "sdk/file.py", 9, "token=must-not-leak")])

    result = _run(base, head)

    assert result.returncode == 1
    assert "CVE-2" in result.stdout
    assert "sdk/file.py:9" in result.stdout
    assert "must-not-leak" not in result.stdout + result.stderr


def test_security_workflow_scans_live_base_and_head_then_enforces_delta() -> None:
    workflow = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    steps = workflow["jobs"]["trivy-repo-scan"]["steps"]
    names = [step.get("name") for step in steps]
    base_scan = next(step for step in steps if step.get("name") == "Scan target branch with Trivy")
    head_scan = next(step for step in steps if step.get("name") == "Scan proposed merge with Trivy")
    policy = next(step for step in steps if step.get("name") == "Enforce no-new-findings policy")

    assert base_scan["with"]["exit-code"] == "0"
    assert head_scan["with"]["exit-code"] == "0"
    assert "check_trivy_pr_delta.py" in policy["run"]
    assert names.index("Scan target branch with Trivy") < names.index(
        "Enforce no-new-findings policy"
    )
    assert names.index("Scan proposed merge with Trivy") < names.index(
        "Enforce no-new-findings policy"
    )
    assert all("continue-on-error" not in step for step in (base_scan, head_scan, policy))
