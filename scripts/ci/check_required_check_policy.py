#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
METADATA_PATH = REPO_ROOT / "config" / "ci" / "required-status-checks.json"
GOVERNANCE_METADATA_PATH = REPO_ROOT / "docs" / "governance" / "branch-protection-required-checks.yml"
WORKFLOW_PATH = REPO_ROOT / ".github" / "workflows" / "branch-protection-validation.yml"
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"


def _load_json(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must parse to a mapping")
    return data


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"{path} must parse to a mapping")
    return data


def _load_pr_job_names() -> set[str]:
    names: set[str] = set()
    workflow_paths = sorted(WORKFLOWS_DIR.glob("*.yml")) + sorted(WORKFLOWS_DIR.glob("*.yaml"))
    for path in workflow_paths:
        text = path.read_text(encoding="utf-8")
        if not re.search(r"(?m)^\s*pull_request\s*:", text):
            continue
        names.update(re.findall(r"(?m)^  [A-Za-z0-9_-]+:\s*$\n(?:    .*\n)*?    name:\s*[\"']?([^\"'\n]+)[\"']?\s*$", text))
        names.update(re.findall(r"(?m)^  ([A-Za-z0-9_-]+):\s*$", text))
    return names


def main() -> int:
    metadata = _load_json(METADATA_PATH)
    governance_metadata = _load_yaml(GOVERNANCE_METADATA_PATH)
    checks = metadata.get("required_status_checks")
    if not isinstance(checks, list) or not checks or not all(isinstance(c, str) for c in checks):
        print("required_status_checks must be a non-empty string list", file=sys.stderr)
        return 1

    workflow_text = WORKFLOW_PATH.read_text(encoding="utf-8")
    errors: list[str] = []

    governance_checks = governance_metadata.get("required_status_checks")
    if sorted(governance_checks or []) != sorted(checks):
        errors.append(
            "governance required-check mirror does not match config/ci/required-status-checks.json"
        )

    emitted_pr_job_names = _load_pr_job_names()
    for check in checks:
        if check not in emitted_pr_job_names:
            errors.append(f"required check is not emitted by a pull_request workflow job: {check}")

    for pattern in governance_metadata.get("protected_branch_patterns", []):
        if pattern == "main" and "branches/main/protection" not in workflow_text:
            errors.append("workflow does not validate main branch")

    if governance_metadata.get("enforcement", {}).get("pull_request_merges") and "validate_branch_protection_checks.py" not in workflow_text:
        errors.append("workflow does not assert strict required status checks (PR merge up-to-date enforcement)")

    if governance_metadata.get("enforcement", {}).get("direct_pushes") and "validate_mandatory_security_gate_enforcement.py" not in workflow_text:
        errors.append("workflow does not assert required status check contexts (direct push enforcement)")

    if errors:
        for error in errors:
            print(error, file=sys.stderr)
        return 1

    print("Required check policy metadata matches branch-protection validation workflow.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
