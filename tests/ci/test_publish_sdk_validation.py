"""Fail-closed contracts for Python SDK publication validation."""

from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-sdk.yml"


def _workflow() -> dict:
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def test_sdk_contract_changes_trigger_publication_validation() -> None:
    workflow = _workflow()
    triggers = workflow[True]
    paths = triggers["pull_request"]["paths"]

    assert "sdk/python/**" in paths
    assert "contracts/openapi/layer3-knowledge.json" in paths
    assert "contracts/openapi/layer4-agents.json" in paths


def test_sdk_build_runs_full_quality_suite_before_building() -> None:
    steps = _workflow()["jobs"]["build"]["steps"]
    names = [step.get("name") for step in steps]
    validation = next(step for step in steps if step.get("name") == "Validate Python SDK")
    command = validation["run"]

    for required in (
        "ruff check src tests scripts",
        "ruff format --check src tests scripts",
        "mypy src tests",
        "pytest --cov=valuefabric",
        "python -m compileall -q src tests scripts",
    ):
        assert required in command
    assert names.index("Validate Python SDK") < names.index("Build wheel and sdist")
