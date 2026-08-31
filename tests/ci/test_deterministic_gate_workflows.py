from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PR_CHECKS = ROOT / ".github/workflows/pr-checks.yml"
CONTRACT_COMPLIANCE = ROOT / ".github/workflows/contract-compliance.yml"
FRONTEND_ESLINT_CONFIG = ROOT / "apps/web/.eslintrc.cjs"
GRAPH_MODULE_TESTS = ROOT / ".github/workflows/graph-module-tests.yml"
DRIFT_CHECK = ROOT / ".github/workflows/drift-check.yml"
SETUP_ACTION = "./.github/actions/setup-fabric-ci"


def _load(path: Path) -> dict:
    return yaml.safe_load(path.read_text(encoding="utf-8"))


def _uses_setup(job: dict) -> dict:
    matches = [step for step in job["steps"] if step.get("uses") == SETUP_ACTION]
    assert len(matches) == 1
    return matches[0]


def test_contract_shape_regression_uses_hash_locked_root_test_setup() -> None:
    job = _load(CONTRACT_COMPLIANCE)["jobs"]["contract-shape-regression"]
    setup = _uses_setup(job)
    assert setup["with"]["python-dependency-mode"] == "root-test"
    assert setup["with"]["install-node-deps"] == "false"
    assert setup["with"]["cache"] == ""
    runs = "\n".join(step.get("run", "") for step in job["steps"])
    assert "pip install" not in runs
    assert "python -m pytest tests/contract/test_api_shape_regression.py" in runs


def test_gate_engineering_uses_shared_locked_setup() -> None:
    job = _load(PR_CHECKS)["jobs"]["gate-engineering"]
    setup = _uses_setup(job)
    assert setup["with"]["python-dependency-mode"] == "root-test"
    assert setup["with"]["install-node-deps"] == "true"
    runs = "\n".join(step.get("run", "") for step in job["steps"])
    assert "pip install" not in runs
    assert "pnpm run gate-engineering:validate --strict" in runs
    assert "pnpm run gate-engineering:test" in runs


def test_runtime_contract_checks_use_shared_locked_setup() -> None:
    job = _load(PR_CHECKS)["jobs"]["runtime-contract-checks"]
    setup = _uses_setup(job)
    assert setup["with"]["python-dependency-mode"] == "root-test"
    assert setup["with"]["install-node-deps"] == "false"
    assert setup["with"]["cache"] == ""
    runs = "\n".join(step.get("run", "") for step in job["steps"])
    assert "pip install" not in runs
    assert (
        "pytest tests/contract/test_layer_integration.py -m runtime_contract -v --tb=short" in runs
    )


def test_root_test_lock_contains_json_report_plugin() -> None:
    requirements = (ROOT / "tests/requirements-test.txt").read_text(encoding="utf-8")
    lock = (ROOT / "tests/requirements-test.lock").read_text(encoding="utf-8")
    assert "pytest-json-report" in requirements
    assert "pytest-json-report==" in lock


def test_graph_contract_job_uses_hash_locked_root_test_dependencies() -> None:
    job = _load(GRAPH_MODULE_TESTS)["jobs"]["contract-tests"]
    runs = "\n".join(step.get("run", "") for step in job["steps"])

    assert "python -m pip install --require-hashes -r tests/requirements-test.lock" in runs
    assert "pip install pytest jsonschema" not in runs


def test_openapi_drift_job_uses_hash_locked_pytest_plugins() -> None:
    job = _load(DRIFT_CHECK)["jobs"]["detect-drift"]
    runs = "\n".join(step.get("run", "") for step in job["steps"])

    assert "python -m pip install --require-hashes -r tests/requirements-test.lock" in runs
    assert "pip install fastapi uvicorn" not in runs
    assert "pip install -e services/layer1-ingestion/ --no-deps" in runs


def test_frontend_contract_lint_configures_type_information() -> None:
    config = FRONTEND_ESLINT_CONFIG.read_text(encoding="utf-8")

    assert '"./tsconfig.json"' in config
    assert "tsconfigRootDir: __dirname" in config
