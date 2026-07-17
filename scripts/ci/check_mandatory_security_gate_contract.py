#!/usr/bin/env python3
"""Fail closed when the mandatory security merge-control contract drifts."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import yaml


REPO_ROOT = Path(__file__).resolve().parents[2]
CONTRACT_PATH = REPO_ROOT / "config/ci/mandatory-security-regression-contract.json"
REQUIRED_CHECKS_PATH = REPO_ROOT / "config/ci/required-status-checks.json"
GOVERNANCE_PATH = REPO_ROOT / "docs/governance/branch-protection-required-checks.yml"
CODEOWNERS_PATH = REPO_ROOT / ".github/CODEOWNERS"
GATE_SCRIPT_PATH = REPO_ROOT / "scripts/ci/mandatory_security_regression_gate.sh"


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a JSON object")
    return payload


def _load_yaml(path: Path) -> dict[str, Any]:
    # BaseLoader prevents YAML 1.1 from treating the GitHub Actions `on` key as bool.
    payload = yaml.load(path.read_text(encoding="utf-8"), Loader=yaml.BaseLoader)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} must contain a YAML mapping")
    return payload


def _owners_by_exact_pattern() -> dict[str, list[str]]:
    owners: dict[str, list[str]] = {}
    for raw_line in CODEOWNERS_PATH.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        fields = line.split()
        if len(fields) > 1:
            owners[fields[0]] = fields[1:]
    return owners


def main() -> int:
    errors: list[str] = []
    contract = _load_json(CONTRACT_PATH)
    canonical = contract["canonical_check"]
    context = canonical["check_context"]
    workflow_path = REPO_ROOT / canonical["workflow_path"]
    workflow = _load_yaml(workflow_path)

    if workflow.get("name") != canonical["workflow_name"]:
        errors.append("canonical workflow display name drifted")

    pull_request = workflow.get("on", {}).get("pull_request")
    if not isinstance(pull_request, dict):
        errors.append("mandatory workflow must define a pull_request mapping")
    else:
        branches = pull_request.get("branches", [])
        if "main" not in branches:
            errors.append("mandatory workflow must run for pull requests to main")
        if "paths" in pull_request or "paths-ignore" in pull_request:
            errors.append("mandatory workflow must not use pull-request path filters")

    job = workflow.get("jobs", {}).get(canonical["job_id"])
    if not isinstance(job, dict):
        errors.append("canonical mandatory-security-regression job is missing")
    else:
        if job.get("name") != context:
            errors.append("mandatory job display name must exactly equal the required context")
        if "if" in job:
            errors.append("mandatory job must not have a job-level condition")
        if job.get("continue-on-error") is not None:
            errors.append("mandatory job must not use continue-on-error")
        if "strategy" in job:
            errors.append("mandatory job must not use a matrix strategy")
        if str(job.get("timeout-minutes")) != str(canonical["timeout_minutes"]):
            errors.append("mandatory job timeout drifted from the governed contract")

        run_steps = [step for step in job.get("steps", []) if isinstance(step, dict) and step.get("name") == "Run mandatory security regression gate"]
        if len(run_steps) != 1:
            errors.append("mandatory job must have exactly one gate execution step")
        else:
            step = run_steps[0]
            if step.get("run") != "bash scripts/ci/mandatory_security_regression_gate.sh":
                errors.append("mandatory gate execution command drifted")
            if str(step.get("env", {}).get("FABRIC_GATE_TEST_MODE")) != "0":
                errors.append("mandatory job must pin FABRIC_GATE_TEST_MODE=0")

    required_checks = _load_json(REQUIRED_CHECKS_PATH).get("required_status_checks")
    governance_checks = _load_yaml(GOVERNANCE_PATH).get("required_status_checks")
    if not isinstance(required_checks, list) or required_checks.count(context) != 1:
        errors.append("canonical required context must appear exactly once in required-status-checks.json")
    if governance_checks != required_checks:
        errors.append("governance required-check mirror does not match required-status-checks.json")

    policy_path = REPO_ROOT / "docs/governance/mandatory-security-regression-merge-policy.md"
    if not policy_path.exists():
        errors.append("mandatory security merge policy is missing")
    elif f"`{context}`" not in policy_path.read_text(encoding="utf-8"):
        errors.append("merge policy does not document the canonical required context")

    required_owners = _owners_by_exact_pattern()
    for path in contract["codeowners"]:
        owners = required_owners.get(path)
        if not owners or "@value-fabric/security-leads" not in owners or "@value-fabric/sre-leads" not in owners:
            errors.append(f"CODEOWNERS must require Security and SRE review for {path}")

    gate_script = GATE_SCRIPT_PATH.read_text(encoding="utf-8")
    for forbidden in ("set +e", '"PARTIAL"'):
        if forbidden in gate_script:
            errors.append(f"mandatory gate contains fail-open marker: {forbidden}")
    if '[[ "${CI:-}" == "true" && "${FABRIC_GATE_TEST_MODE}" == "1" ]]' not in gate_script:
        errors.append("mandatory gate must reject test mode in CI")

    if errors:
        for error in errors:
            print(f"::error::{error}", file=sys.stderr)
        return 1

    print(f"PASS mandatory security regression contract: {context}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
