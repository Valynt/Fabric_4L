"""Tests verifying GitHub Merge Queue (merge_group) contract and aggregate check invariants.

Invariants verified:
1. Every workflow hosting required checks or aggregates triggers on merge_group.
2. Required/aggregate workflows do not use top-level paths filters that cause checks to disappear.
3. Every aggregate job uses `if: always()` and resolves all `needs:` to real jobs in the same workflow.
4. change-scope action supports both pull_request and merge_group event triggers.
"""
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

REPO_ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS_DIR = REPO_ROOT / ".github" / "workflows"
CHANGE_SCOPE_ACTION = REPO_ROOT / ".github" / "actions" / "change-scope" / "action.yml"
REQUIRED_CHECKS_CONFIG = REPO_ROOT / "config" / "ci" / "required-status-checks.json"
BRANCH_PROTECTION_CONFIG = REPO_ROOT / "docs" / "governance" / "branch-protection-required-checks.yml"

REQUIRED_WORKFLOWS = [
    "pr-checks.yml",
    "security-gates.yml",
    "contract-compliance.yml",
    "prod-readiness.yml",
    "supply-chain-integrity.yml",
    "release-evidence-bundle.yml",
    "critical-gates.yml",
]

AGGREGATE_CHECKS_MAP = {
    "pr-checks.yml": [
        "01-repository-integrity",
        "02-code-quality-and-tests",
        "05-tenant-isolation-and-behavior",
        "09-change-risk-and-approval",
    ],
    "contract-compliance.yml": [
        "03-contract-compliance",
    ],
    "security-gates.yml": [
        "04-security-gates",
    ],
    "prod-readiness.yml": [
        "06-production-readiness",
    ],
    "supply-chain-integrity.yml": [
        "07-supply-chain-integrity",
    ],
    "release-evidence-bundle.yml": [
        "08-release-evidence",
    ],
}


def _load_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def test_required_workflows_trigger_on_merge_group() -> None:
    for wf_filename in REQUIRED_WORKFLOWS:
        wf_path = WORKFLOWS_DIR / wf_filename
        assert wf_path.exists(), f"Workflow file {wf_filename} does not exist"
        data = _load_yaml(wf_path)
        triggers = data.get("on", data.get(True, {}))
        assert "merge_group" in triggers, (
            f"Workflow {wf_filename} is required for merge queue but lacks 'merge_group' trigger in 'on:'"
        )


def test_no_top_level_paths_filter_on_required_merge_group_workflows() -> None:
    for wf_filename in REQUIRED_WORKFLOWS:
        wf_path = WORKFLOWS_DIR / wf_filename
        data = _load_yaml(wf_path)
        triggers = data.get("on", data.get(True, {}))
        mg = triggers.get("merge_group")
        if isinstance(mg, dict):
            assert "paths" not in mg and "paths-ignore" not in mg, (
                f"Workflow {wf_filename} has path filtering on merge_group; required checks must not disappear"
            )


def test_change_scope_action_supports_merge_group() -> None:
    data = _load_yaml(CHANGE_SCOPE_ACTION)
    steps = data.get("runs", {}).get("steps", [])
    filter_step = next((s for s in steps if s.get("id") == "filter"), None)
    assert filter_step is not None, "filter step missing in change-scope action"
    
    if_expr = filter_step.get("if", "")
    assert "merge_group" in if_expr, f"change-scope filter step does not trigger on merge_group: {if_expr}"
    
    with_clause = filter_step.get("with", {})
    assert "base_sha" in with_clause, "change-scope filter step missing base_sha parameter"
    assert "head_sha" in with_clause, "change-scope filter step missing head_sha parameter"
    assert "merge_group.base_sha" in with_clause["base_sha"], "base_sha does not resolve merge_group.base_sha"
    assert "merge_group.head_sha" in with_clause["head_sha"], "head_sha does not resolve merge_group.head_sha"


def test_all_aggregates_defined_with_valid_needs() -> None:
    for wf_filename, expected_aggregates in AGGREGATE_CHECKS_MAP.items():
        wf_path = WORKFLOWS_DIR / wf_filename
        data = _load_yaml(wf_path)
        jobs = data.get("jobs", {})
        
        for agg_name in expected_aggregates:
            agg_job_key = f"aggregate-{agg_name}"
            assert agg_job_key in jobs, f"Job {agg_job_key} missing in {wf_filename}"
            job_def = jobs[agg_job_key]
            
            assert job_def.get("name") == agg_name, f"Job display name mismatch for {agg_job_key}"
            
            needs = job_def.get("needs", [])
            if isinstance(needs, str):
                needs = [needs]
            if needs:
                assert job_def.get("if") == "always()", f"Fan-in aggregate job {agg_job_key} must have if: always()"
                for child in needs:
                    assert child in jobs, (
                        f"Aggregate {agg_job_key} in {wf_filename} needs '{child}' which is not in {wf_filename}"
                    )
            else:
                assert agg_name == "09-change-risk-and-approval", (
                    f"Aggregate {agg_job_key} has no needs: but is not 09 policy gate"
                )
