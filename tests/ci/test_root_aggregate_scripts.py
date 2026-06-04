from __future__ import annotations

import importlib.util
import json
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "run_root_aggregate_checks.py"


def load_runner_module():
    spec = importlib.util.spec_from_file_location(
        "run_root_aggregate_checks", SCRIPT_PATH
    )
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def repo_tmp_path(name: str) -> Path:
    path = REPO_ROOT / ".tmp" / "root-aggregate-script-tests" / name
    if path.exists():
        shutil.rmtree(path)
    path.mkdir(parents=True)
    return path


def test_root_scripts_use_fail_closed_orchestrator():
    root_package = load_json(REPO_ROOT / "package.json")
    scripts = root_package["scripts"]

    expected_routed_gates = (
        "lint",
        "test",
        "typecheck",
        "security",
        "schema",
        "isolation",
        "crawler",
        "router",
        "db-migrate-status",
    )
    for gate in expected_routed_gates:
        assert scripts[gate] == f"python scripts/ci/run_root_aggregate_checks.py {gate}"

    assert (
        scripts["checks:list"]
        == "python scripts/ci/run_root_aggregate_checks.py --list"
    )
    assert (
        scripts["checks:json"]
        == "python scripts/ci/run_root_aggregate_checks.py --json"
    )
    assert scripts["checks:all"] == "python scripts/ci/run_root_aggregate_checks.py all"
    assert scripts["all"] == "python scripts/ci/run_root_aggregate_checks.py all"


def test_expected_check_matrix_is_non_empty_and_references_canonical_packages():
    runner = load_runner_module()

    expected = {
        "typecheck": {
            ("apps/web", "typecheck"),
            ("packages/config", "typecheck"),
            ("packages/platform-contract", "typecheck"),
            ("packages/eslint-plugin-fabric-contracts", "typecheck"),
        },
        "lint": {
            ("apps/web", "lint"),
            ("packages/eslint-plugin-fabric-contracts", "lint"),
        },
        "test": {
            ("apps/web", "test"),
            ("packages/config", "test"),
            ("packages/platform-contract", "test"),
            ("packages/eslint-plugin-fabric-contracts", "test"),
        },
    }

    assert set(runner.EXPECTED_CHECKS) == set(expected)
    for target, expected_pairs in expected.items():
        checks = runner.EXPECTED_CHECKS[target]
        assert checks
        assert {
            (check.package_path, check.script) for check in checks
        } == expected_pairs


def test_supported_gates_include_named_maturity_gates():
    runner = load_runner_module()

    assert runner.SUPPORTED_GATES == (
        "lint",
        "test",
        "security",
        "schema",
        "isolation",
        "crawler",
        "router",
        "db-migrate-status",
        "typecheck",
    )

    assert "all" in runner._supported_gate_names(include_all=True)


def test_expected_package_scripts_exist_in_current_checkout():
    runner = load_runner_module()

    for target in runner.EXPECTED_CHECKS:
        checks = runner.validate_expected_checks(target, REPO_ROOT)
        assert checks


def test_optional_gate_without_config_is_not_applicable():
    runner = load_runner_module()

    result = runner.run_gate("crawler", REPO_ROOT, quiet=True)

    assert result.status == "not_applicable"
    assert result.exit_code == 0
    assert result.checks_planned == 0
    assert "not_applicable" in result.message


def test_json_inventory_marks_missing_optional_gates_not_applicable():
    runner = load_runner_module()

    inventory = runner.gate_inventory()
    gates = {gate["name"]: gate for gate in inventory["gates"]}

    assert gates["lint"]["status"] == "configured"
    assert gates["crawler"]["status"] == "not_applicable"
    assert gates["all"]["status"] == "configured"


def test_missing_required_package_script_fails_before_running():
    runner = load_runner_module()
    tmp_path = repo_tmp_path("missing-script")
    package_dir = tmp_path / "apps" / "web"
    package_dir.mkdir(parents=True)
    (package_dir / "package.json").write_text(
        json.dumps({"name": "web", "scripts": {"test": "vitest run"}}),
        encoding="utf-8",
    )

    try:
        runner.validate_expected_checks("typecheck", tmp_path)
    except runner.AggregateCheckError as exc:
        assert "Missing required script" in str(exc)
        assert "typecheck" in str(exc)
    else:
        raise AssertionError("missing script did not fail")


def test_zero_check_target_fails_closed(monkeypatch):
    runner = load_runner_module()
    tmp_path = repo_tmp_path("zero-check")
    monkeypatch.setitem(runner.EXPECTED_CHECKS, "empty", ())
    monkeypatch.setitem(
        runner.GATE_DEFINITIONS,
        "empty",
        runner.GateDefinition("empty", "Empty required gate", True),
    )
    monkeypatch.setattr(runner, "SUPPORTED_GATES", (*runner.SUPPORTED_GATES, "empty"))

    try:
        runner.validate_expected_checks("empty", tmp_path)
    except runner.AggregateCheckError as exc:
        assert "zero package checks" in str(exc)
    else:
        raise AssertionError("empty check matrix did not fail")


def test_runner_invokes_explicit_pnpm_dir_commands(monkeypatch):
    runner = load_runner_module()
    calls: list[tuple[list[str], Path]] = []
    tmp_path = repo_tmp_path("runner-commands")
    package_dir = tmp_path / "apps" / "web"
    package_dir.mkdir(parents=True)
    (package_dir / "package.json").write_text(
        json.dumps({"name": "web", "scripts": {"test": "vitest run"}}),
        encoding="utf-8",
    )
    monkeypatch.setitem(
        runner.EXPECTED_CHECKS,
        "test",
        (runner.PackageCheck("apps/web", "test"),),
    )

    def fake_runner(command, cwd):
        calls.append((list(command), cwd))
        return subprocess.CompletedProcess(command, 0)

    assert runner.run_aggregate_check("test", tmp_path, fake_runner) == 0
    assert calls == [(["pnpm", "--dir", "apps/web", "run", "test"], tmp_path)]
