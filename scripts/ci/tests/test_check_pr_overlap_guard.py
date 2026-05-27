from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

SCRIPT = Path("scripts/ci/check_pr_overlap_guard.py")


def run_case(tmp_path: Path, *, body: str, changed: str, fixture: dict, threshold: float = 0.3):
    event = {"pull_request": {"body": body}}
    event_path = tmp_path / "event.json"
    event_path.write_text(json.dumps(event), encoding="utf-8")
    fixture_path = tmp_path / "fixture.json"
    fixture_path.write_text(json.dumps(fixture), encoding="utf-8")
    env = os.environ.copy()
    env.update({
        "GITHUB_EVENT_PATH": str(event_path),
        "CHANGED_FILES": changed,
        "GITHUB_TOKEN": "x",
        "GITHUB_REPOSITORY": "acme/repo",
        "PR_OVERLAP_FIXTURE": str(fixture_path),
    })
    return subprocess.run([sys.executable, str(SCRIPT), "--threshold", str(threshold)], capture_output=True, text=True, check=False, env=env)


def test_allowlisted_changes_pass(tmp_path: Path):
    result = run_case(tmp_path, body="", changed="Makefile", fixture={"merged_prs": []})
    assert result.returncode == 0


def test_threshold_requires_reason_section(tmp_path: Path):
    fixture = {"merged_prs": [{"number": 1, "merged_at": "2026-01-01"}], "pr_files": {"1": ["services/api/main.py"]}}
    result = run_case(tmp_path, body="## Summary\nX", changed="services/api/main.py", fixture=fixture)
    assert result.returncode == 1
    assert "Why overlap is expected" in result.stdout


def test_runtime_shared_path_uses_strict_reason_length(tmp_path: Path):
    fixture = {"merged_prs": [{"number": 2, "merged_at": "2026-01-01"}], "pr_files": {"2": ["packages/shared/src/value_fabric/shared/foo.py"]}}
    result = run_case(
        tmp_path,
        body="## Why overlap is expected\nshort",
        changed="packages/shared/src/value_fabric/shared/foo.py",
        fixture=fixture,
    )
    assert result.returncode == 1
    assert "strict runtime shared-module overlap" in result.stdout
