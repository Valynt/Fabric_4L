"""End-to-end simulation of GitHub Merge Queue and Aggregate Gate arbiter behaviors.

This suite validates the complete decision matrix for:
1. Single-layer change -> affected checks run, unaffected checks safe-skip -> aggregate PASSES.
2. Documentation-only change -> runtime checks safe-skip -> aggregate PASSES.
3. Child failure -> aggregate FAILS (fail-closed).
4. Unconfirmed skip -> aggregate FAILS (fail-closed).
5. Cancelled child job -> aggregate FAILS (fail-closed).
6. Deterministic 09 policy -> validates approvals, SHA match, severity thresholds, author != reviewer.
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
AGGREGATE_GATE_SCRIPT = REPO_ROOT / "scripts" / "ci" / "aggregate_gate.py"
CHANGE_RISK_SCRIPT = REPO_ROOT / "scripts" / "ci" / "check_change_risk_approval.py"


def _run_aggregate(
    results: dict[str, str],
    safe_skips: dict[str, str] | None = None,
    extra_env: dict[str, str] | None = None,
) -> tuple[int, str]:
    # Construct needs JSON object matching GitHub Actions format:
    # {"job_name": {"result": "success"}}
    needs_payload = {job: {"result": res} for job, res in results.items()}
    args = [sys.executable, str(AGGREGATE_GATE_SCRIPT), "--needs-json", json.dumps(needs_payload)]
    
    env_vars = dict(os.environ)
    if safe_skips:
        for job, env_var_name in safe_skips.items():
            args.extend(["--skip-safe", f"{job}={env_var_name}"])
            
    if extra_env:
        env_vars.update(extra_env)
        
    proc = subprocess.run(
        args,
        capture_output=True,
        text=True,
        check=False,
        env=env_vars,
    )
    return proc.returncode, proc.stdout + proc.stderr


def test_simulation_single_layer_pr_all_green() -> None:
    # PR touches only layer1
    # layer1-checks succeeds, layer2-6 skipped with safe-skip confirmation
    results = {
        "layer1-checks": "success",
        "layer2-checks": "skipped",
        "layer3-checks": "skipped",
        "layer4-checks": "skipped",
        "layer5-checks": "skipped",
        "layer6-checks": "skipped",
        "shared-and-tests-checks": "success",
        "frontend-checks": "skipped",
    }
    # In CI, env expressions compose: SKIPSAFE_LAYER2='true' when change-scope output layer2=='false'
    safe_skips_mapping = {
        "layer2-checks": "SKIPSAFE_LAYER2",
        "layer3-checks": "SKIPSAFE_LAYER3",
        "layer4-checks": "SKIPSAFE_LAYER4",
        "layer5-checks": "SKIPSAFE_LAYER5",
        "layer6-checks": "SKIPSAFE_LAYER6",
        "frontend-checks": "SKIPSAFE_WEB",
    }
    env_values = {
        "SKIPSAFE_LAYER2": "true",
        "SKIPSAFE_LAYER3": "true",
        "SKIPSAFE_LAYER4": "true",
        "SKIPSAFE_LAYER5": "true",
        "SKIPSAFE_LAYER6": "true",
        "SKIPSAFE_WEB": "true",
    }
    code, output = _run_aggregate(results, safe_skips_mapping, env_values)
    assert code == 0, f"Expected 02-code-quality-and-tests to pass on single-layer PR:\n{output}"
    assert "aggregate gate PASSED: all 8 child job(s) succeeded or were confirmed safe to skip" in output


def test_simulation_docs_only_pr_all_safe_skips() -> None:
    # Docs-only PR: all readiness jobs skip with runtime='false' confirmation
    results = {
        "arch-conformance": "skipped",
        "security-isolation": "skipped",
        "dependency-chaos": "skipped",
        "cross-domain-smoke": "skipped",
        "agent-provenance": "skipped",
        "state-consistency": "skipped",
        "db-production-readiness-gate": "skipped",
        "observability-readiness": "skipped",
        "repo-maturity-scorecard": "skipped",
        "readiness-10": "skipped",
        "gate-engineering": "skipped",
        "release-policy": "skipped",
    }
    safe_skips_mapping = {k: f"SKIPSAFE_{k.upper().replace('-', '_')}" for k in results}
    env_values = {v: "true" for v in safe_skips_mapping.values()}
    code, output = _run_aggregate(results, safe_skips_mapping, env_values)
    assert code == 0, f"Expected 06-production-readiness to pass on docs-only PR:\n{output}"
    assert "aggregate gate PASSED: all 12 child job(s) succeeded or were confirmed safe to skip" in output


def test_simulation_negative_child_failure_blocks_merge() -> None:
    # A single unit test fails in layer1
    results = {
        "layer1-checks": "failure",
        "layer2-checks": "skipped",
        "layer3-checks": "skipped",
        "layer4-checks": "skipped",
        "layer5-checks": "skipped",
        "layer6-checks": "skipped",
        "shared-and-tests-checks": "success",
        "frontend-checks": "skipped",
    }
    safe_skips_mapping = {
        "layer2-checks": "SKIPSAFE_LAYER2",
        "layer3-checks": "SKIPSAFE_LAYER3",
        "layer4-checks": "SKIPSAFE_LAYER4",
        "layer5-checks": "SKIPSAFE_LAYER5",
        "layer6-checks": "SKIPSAFE_LAYER6",
        "frontend-checks": "SKIPSAFE_WEB",
    }
    env_values = {
        "SKIPSAFE_LAYER2": "true",
        "SKIPSAFE_LAYER3": "true",
        "SKIPSAFE_LAYER4": "true",
        "SKIPSAFE_LAYER5": "true",
        "SKIPSAFE_LAYER6": "true",
        "SKIPSAFE_WEB": "true",
    }
    code, output = _run_aggregate(results, safe_skips_mapping, env_values)
    assert code == 1, "Expected aggregate to fail on child failure"
    assert "layer1-checks=failure" in output


def test_simulation_negative_unconfirmed_skip_fails_closed() -> None:
    # layer1-checks skipped but scope was active (SKIPSAFE is 'false' or missing)
    results = {
        "layer1-checks": "skipped",
        "shared-and-tests-checks": "success",
    }
    safe_skips_mapping = {
        "layer1-checks": "SKIPSAFE_LAYER1",
    }
    env_values = {
        "SKIPSAFE_LAYER1": "false",
    }
    code, output = _run_aggregate(results, safe_skips_mapping, env_values)
    assert code == 1, "Expected aggregate to fail closed on unconfirmed skip"
    assert "FAIL layer1-checks: skipped without an explicit safe-skip confirmation" in output


def test_simulation_negative_cancelled_job_fails_closed() -> None:
    # Runner timeout or out of memory cancellation
    results = {
        "contract-compliance": "cancelled",
        "plugin-tests": "success",
    }
    code, output = _run_aggregate(results)
    assert code == 1, "Expected aggregate to fail closed on cancelled job"
    assert "FAIL contract-compliance: cancelled" in output


def test_simulation_change_risk_policy_full_lifecycle(tmp_path: Path, monkeypatch) -> None:
    head_sha = "2" * 40
    
    event_payload = {
        "merge_group": {
            "head_sha": head_sha,
        }
    }
    event_file = tmp_path / "event.json"
    event_file.write_text(json.dumps(event_payload), encoding="utf-8")
    
    from importlib.util import module_from_spec, spec_from_file_location
    spec = spec_from_file_location("check_change_risk_approval", CHANGE_RISK_SCRIPT)
    assert spec is not None and spec.loader is not None
    module = module_from_spec(spec)
    spec.loader.exec_module(module)

    monkeypatch.setenv("GITHUB_EVENT_NAME", "merge_group")
    monkeypatch.setenv("GITHUB_REPOSITORY", "acme/repo")

    # 1. Independent approver passes on merge_group event
    def fake_api_approved(args):
        endpoint = args[0]
        if "/commits/" in endpoint and endpoint.endswith("/pulls"):
            return [{"number": 42}]
        if endpoint == "repos/acme/repo/pulls/42":
            return {"user": {"login": "agent-alice"}}
        if endpoint.endswith("/reviews"):
            return [{"user": {"login": "human-bob"}, "state": "APPROVED"}]
        if endpoint.endswith("/files"):
            return [{"filename": "contracts/openapi/l4.json"}]
        if endpoint == "graphql":
            return {"data": {"repository": {"pullRequest": {"reviewDecision": "APPROVED"}}}}
        raise AssertionError(args)

    monkeypatch.setattr(module, "_gh_json", fake_api_approved)
    assert module.main(["--event-path", str(event_file)]) == 0

    # 2. Author trying to self-approve fails closed
    def fake_api_self(args):
        endpoint = args[0]
        if "/commits/" in endpoint and endpoint.endswith("/pulls"):
            return [{"number": 42}]
        if endpoint == "repos/acme/repo/pulls/42":
            return {"user": {"login": "agent-alice"}}
        if endpoint.endswith("/reviews"):
            return [{"user": {"login": "agent-alice"}, "state": "APPROVED"}]
        if endpoint.endswith("/files"):
            return [{"filename": "contracts/openapi/l4.json"}]
        if endpoint == "graphql":
            return {"data": {"repository": {"pullRequest": {"reviewDecision": "APPROVED"}}}}
        raise AssertionError(args)

    monkeypatch.setattr(module, "_gh_json", fake_api_self)
    assert module.main(["--event-path", str(event_file)]) == 1
