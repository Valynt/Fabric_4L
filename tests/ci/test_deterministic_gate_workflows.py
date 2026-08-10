from __future__ import annotations

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
PR_CHECKS = ROOT / ".github/workflows/pr-checks.yml"
CONTRACT_COMPLIANCE = ROOT / ".github/workflows/contract-compliance.yml"
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


def test_root_test_lock_contains_json_report_plugin() -> None:
    requirements = (ROOT / "tests/requirements-test.txt").read_text(encoding="utf-8")
    lock = (ROOT / "tests/requirements-test.lock").read_text(encoding="utf-8")
    assert "pytest-json-report" in requirements
    assert "pytest-json-report==" in lock
