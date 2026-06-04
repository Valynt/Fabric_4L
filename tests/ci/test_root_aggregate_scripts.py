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
    spec = importlib.util.spec_from_file_location("run_root_aggregate_checks", SCRIPT_PATH)
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
    scripts = load_json(REPO_ROOT / "package.json")["scripts"]
    expected = {
        "typecheck": "python scripts/ci/run_root_aggregate_checks.py typecheck",
        "lint": "python scripts/ci/run_root_aggregate_checks.py lint",
        "test": "python scripts/ci/run_root_aggregate_checks.py test",
        "test:security": "python scripts/ci/run_root_aggregate_checks.py security",
        "test:isolation": "python scripts/ci/run_root_aggregate_checks.py isolation",
        "test:schema": "python scripts/ci/run_root_aggregate_checks.py schema",
        "test:crawler": "python scripts/ci/run_root_aggregate_checks.py crawler",
        "test:router": "python scripts/ci/run_root_aggregate_checks.py router",
        "db:migrate:status": "python scripts/ci/run_root_aggregate_checks.py db-migrate-status",
    }
    for script, command in expected.items():
        assert scripts[script] == command


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
        assert {
            (check.package_path, check.script)
            for check in runner.EXPECTED_CHECKS[target]
        } == expected_pairs


def test_named_gate_registry_exposes_maturity_gates():
    runner = load_runner_module()

    assert set(runner.GATES) == {
        "typecheck",
        "lint",
        "test",
        "security",
        "schema",
        "isolation",
        "crawler",
        "router",
        "db-migrate-status",
    }
    assert runner.ALL_GATE_NAMES == (
        "lint",
        "test",
        "security",
        "schema",
        "isolation",
        "crawler",
        "router",
        "db-migrate-status",
    )


def test_list_outputs_every_supported_gate():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--list"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    assert result.stdout.splitlines() == [
        "typecheck",
        "lint",
        "test",
        "security",
        "schema",
        "isolation",
        "crawler",
        "router",
        "db-migrate-status",
        "all",
    ]


def test_json_outputs_machine_readable_gate_metadata():
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH), "--json"],
        cwd=REPO_ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0
    payload = json.loads(result.stdout)
    gate_names = [gate["name"] for gate in payload["gates"]]
    assert "security" in gate_names
    assert "db-migrate-status" in gate_names
    assert payload["aggregate_targets"]["all"] == list(load_runner_module().ALL_GATE_NAMES)
    assert payload["exit_codes"] == {
        "passed": 0,
        "failed": 1,
        "configuration_error": 2,
        "command_not_found": 127,
        "not_applicable": 0,
    }
    assert payload["annotations"]


def test_expected_package_scripts_exist_in_current_checkout():
    runner = load_runner_module()

    for target in runner.EXPECTED_CHECKS:
        assert runner.validate_expected_checks(target, REPO_ROOT)


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
    monkeypatch.setitem(runner.GATES, "empty", runner.Gate("empty", "Empty test gate", "package", ()))

    try:
        runner.validate_expected_checks("empty", REPO_ROOT)
    except runner.AggregateCheckError as exc:
        assert "zero checks" in str(exc)
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
        runner.GATES,
        "test",
        runner.Gate("test", "Test gate", "package", (runner.PackageCheck("apps/web", "test"),)),
    )
    monkeypatch.setattr(runner, "validate_expected_checks", lambda target, repo_root: runner.GATES[target].checks)

    def fake_runner(command, cwd):
        calls.append((list(command), cwd))
        return subprocess.CompletedProcess(command, 0)

    assert runner.run_aggregate_check("test", tmp_path, fake_runner) == 0
    assert calls == [(["pnpm", "--dir", "apps/web", "run", "test"], tmp_path)]


def test_command_gate_failure_returns_one():
    runner = load_runner_module()
    calls: list[tuple[list[str], Path]] = []

    def fake_runner(command, cwd):
        calls.append((list(command), cwd))
        return subprocess.CompletedProcess(command, 9)

    result = runner.run_gate("security", REPO_ROOT, fake_runner)

    assert result.status == runner.GateStatus.FAILED
    assert result.exit_code == 1
    assert calls == [
        (
            [
                sys.executable,
                "-m",
                "pytest",
                "-v",
                "--tb=short",
                "-x",
                "tests/security/test_security_smoke.py",
            ],
            REPO_ROOT,
        )
    ]


def test_missing_command_executable_returns_127():
    runner = load_runner_module()

    def missing_runner(command, cwd):
        return subprocess.CompletedProcess(command, 127)

    result = runner.run_gate("schema", REPO_ROOT, missing_runner)

    assert result.status == runner.GateStatus.FAILED
    assert result.exit_code == 127


def test_invalid_gate_returns_configuration_error(capsys):
    runner = load_runner_module()

    assert runner.main(["definitely-not-a-gate"]) == 2
    assert "Unsupported gate" in capsys.readouterr().err


def test_missing_optional_gate_is_not_applicable_not_silent_success(monkeypatch):
    runner = load_runner_module()
    tmp_path = repo_tmp_path("missing-optional-gate")
    monkeypatch.setitem(
        runner.GATES,
        "optional-demo",
        runner.Gate(
            name="optional-demo",
            description="Optional demo gate",
            kind="command",
            checks=(
                runner.CommandCheck(
                    ("demo",),
                    "optional demo",
                    required_paths=(Path("missing/demo.txt"),),
                    optional=True,
                ),
            ),
        ),
    )

    result = runner.run_gate(
        "optional-demo",
        tmp_path,
        lambda command, cwd: subprocess.CompletedProcess(command, 99),
    )

    assert result.status == runner.GateStatus.NOT_APPLICABLE
    assert result.exit_code == 0
    assert result.checks[0].status == runner.GateStatus.NOT_APPLICABLE
    assert result.checks[0].missing_paths == ("missing/demo.txt",)


def test_all_aggregates_results_deterministically(monkeypatch):
    runner = load_runner_module()
    calls: list[str] = []

    def fake_run_gate(target, repo_root=runner.REPO_ROOT, runner_arg=runner.default_runner, *, emit_text=True):
        calls.append(target)
        if target == "router":
            return runner.GateResult(target, target, runner.GateStatus.FAILED, 1, ())
        if target == "crawler":
            return runner.GateResult(target, target, runner.GateStatus.NOT_APPLICABLE, 0, ())
        return runner.GateResult(target, target, runner.GateStatus.PASSED, 0, ())

    monkeypatch.setattr(runner, "run_gate", fake_run_gate)
    results = runner.run_all()

    assert calls == list(runner.ALL_GATE_NAMES)
    assert [result.status for result in results].count(runner.GateStatus.PASSED) == len(runner.ALL_GATE_NAMES) - 2
    assert [result.status for result in results].count(runner.GateStatus.FAILED) == 1
    assert [result.status for result in results].count(runner.GateStatus.NOT_APPLICABLE) == 1
    assert runner._exit_code_for_results(results) == 1
