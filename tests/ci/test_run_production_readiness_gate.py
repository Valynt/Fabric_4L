from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "run_production_readiness_gate.py"
PR_CHECKS_WORKFLOW = REPO_ROOT / ".github" / "workflows" / "pr-checks.yml"


def load_runner_module():
    spec = importlib.util.spec_from_file_location("run_production_readiness_gate", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_gate_writes_expected_artifacts_for_each_suite(tmp_path, monkeypatch):
    runner = load_runner_module()
    calls = []

    def fake_run(command, cwd, env, check):
        calls.append((command, cwd, env, check))

        class Result:
            returncode = 0

        return Result()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.run_gate(("security", "billing"), tmp_path)

    assert result == 0
    assert [call[0][5] for call in calls] == ["tests/security/", "tests/billing/"]
    for suite in ("security", "billing"):
        summary = (tmp_path / suite / "summary.md").read_text(encoding="utf-8")
        assert f"# Production readiness: {suite}" in summary
        assert f"- Suite: tests/{suite}/" in summary
        assert f"- JUnit artifact: {tmp_path.as_posix()}/{suite}/junit.xml" in summary
        assert "- Status: passed" in summary
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["overall_status"] == "passed"
    assert manifest["blocks_release_on_failure"] is True
    assert manifest["required_regression_domains"] == [
        "architecture",
        "contracts",
        "operational-behavior",
        "security",
        "tenant-isolation",
    ]
    assert {entry["suite"]: entry["status"] for entry in manifest["suites"]} == {
        "security": "passed",
        "billing": "passed",
    }
    assert "security" in manifest["covered_regression_domains"]
    assert "contracts" in manifest["covered_regression_domains"]


def test_gate_stops_on_first_failed_suite(tmp_path, monkeypatch):
    runner = load_runner_module()
    calls = []

    def fake_run(command, cwd, env, check):
        calls.append(command)

        class Result:
            returncode = 1 if command[5] == "tests/reliability/" else 0

        return Result()

    monkeypatch.setattr(runner.subprocess, "run", fake_run)

    result = runner.run_gate(("security", "reliability", "billing"), tmp_path)

    assert result == 1
    assert [call[5] for call in calls] == ["tests/security/", "tests/reliability/"]
    failed_summary = (tmp_path / "reliability" / "summary.md").read_text(encoding="utf-8")
    assert "- Status: failed" in failed_summary
    assert not (tmp_path / "billing").exists()
    manifest = json.loads((tmp_path / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["overall_status"] == "failed"
    assert manifest["stopped_on_failure"] is True
    assert manifest["covered_regression_domains"] == [
        "operational-behavior",
        "security",
        "tenant-isolation",
    ]
    assert {entry["suite"]: entry["status"] for entry in manifest["suites"]} == {
        "security": "passed",
        "reliability": "failed",
        "billing": "not_run",
    }
    billing_entry = next(entry for entry in manifest["suites"] if entry["suite"] == "billing")
    assert billing_entry["blocking"] is True
    assert billing_entry["returncode"] is None


def test_gate_env_forces_repo_local_temp_dir(monkeypatch):
    runner = load_runner_module()

    monkeypatch.setenv("DEBUG", "invalid")

    env = runner.gate_env()

    assert env["DEBUG"] == "false"
    assert Path(env["TMPDIR"]).parts[-2:] == (".tmp", "production-readiness-pytest")
    assert env["TMP"] == env["TMPDIR"]
    assert env["TEMP"] == env["TMPDIR"]


def test_pr_checks_requires_production_readiness_manifest() -> None:
    workflow = PR_CHECKS_WORKFLOW.read_text(encoding="utf-8")

    assert "make production-readiness-gate" in workflow
    assert "test -s artifacts/production-readiness/manifest.json" in workflow
    assert "Manifest: artifacts/production-readiness/manifest.json" in workflow
