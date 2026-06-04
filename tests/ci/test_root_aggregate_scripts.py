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

    assert (
        scripts["typecheck"]
        == "python scripts/ci/run_root_aggregate_checks.py typecheck"
    )
    assert scripts["lint"] == "python scripts/ci/run_root_aggregate_checks.py lint"
    assert scripts["test"] == "python scripts/ci/run_root_aggregate_checks.py test"


def test_required_root_gate_parity_scripts_delegate_to_canonical_commands():
    root_package = load_json(REPO_ROOT / "package.json")
    scripts = root_package["scripts"]

    expected_scripts = {
        "test:security": "make security-test",
        "test:schema": "python scripts/ci/validate_schema_contract_surface.py",
        "test:isolation": "make gate-tenant-isolation",
        "test:crawler": "python -m pytest services/layer1-ingestion/tests/crawler services/layer1-ingestion/tests/unit/test_playwright_crawler.py services/layer1-ingestion/tests/unit/test_crawler_config.py services/layer1-ingestion/tests/unit/test_crawler_telemetry.py -v --tb=short",
        "test:router": "python scripts/ci/validate_router_contract_surface.py && pnpm --dir apps/web exec vitest run src/navigation src/routes",
        "db:migrate:status": "make check-migration-heads",
    }

    for script_name, command in expected_scripts.items():
        assert scripts[script_name] == command


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


def test_expected_package_scripts_exist_in_current_checkout():
    runner = load_runner_module()

    for target in runner.EXPECTED_CHECKS:
        checks = runner.validate_expected_checks(target, REPO_ROOT)
        assert checks


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
