cat << 'INNER_EOF' > tests/ci/test_pip_audit_workflow.py
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
    "layer7-checks",
    "billing-checks",
    "api-checks",
}

def test_all_expected_layers_have_pip_audit_steps():
    with open(WORKFLOW, encoding="utf-8") as f:
        workflow = yaml.safe_load(f)

    jobs = workflow.get("jobs", {})
    for job_name in EXPECTED_AUDIT_JOBS:
        assert job_name in jobs, f"Missing expected CI job: {job_name}"
        steps = jobs[job_name].get("steps", [])
        has_audit_step = any(step.get("run") == AUDIT_HELPER for step in steps)
        assert (
            has_audit_step
        ), f"Job {job_name} missing the pip-audit step. Add: `run: {AUDIT_HELPER}`"


def test_checker_script_can_run():
    res = subprocess.run([sys.executable, str(CHECKER)], capture_output=True)
    assert res.returncode == 0, f"checker script failed: {res.stderr.decode()}"
INNER_EOF
