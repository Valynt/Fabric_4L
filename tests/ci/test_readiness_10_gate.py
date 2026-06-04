from __future__ import annotations

import importlib.util
import json
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "readiness_10_gate.py"


def load_module():
    spec = importlib.util.spec_from_file_location("readiness_10_gate", SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_readiness_gate_defines_required_dimensions() -> None:
    gate = load_module()

    assert [dimension.key for dimension in gate.READINESS_DIMENSIONS] == [
        "script_parity",
        "schema_index",
        "openapi_breaking_change",
        "migration_status",
        "security_suite",
        "tenant_isolation_suite",
        "router_gate",
        "ci_workflow_registry",
        "evidence_bundle_generation",
        "maturity_scorecard_threshold",
    ]


def test_readiness_gate_writes_stable_artifacts(tmp_path: Path) -> None:
    gate = load_module()
    dimensions = (
        gate.GateDimension(
            "demo",
            "Demo Gate",
            (gate.GateCommand((sys.executable, "--version"), "python version"),),
        ),
    )

    def runner(command, cwd):
        return subprocess.CompletedProcess(command, 0, "ok", "")

    assert gate.run_readiness_gate(artifact_dir=tmp_path, runner=runner, dimensions=dimensions) == 0
    assert (tmp_path / "readiness-10-summary.json").exists()
    assert (tmp_path / "readiness-10-summary.md").exists()

    payload = json.loads((tmp_path / "readiness-10-summary.json").read_text(encoding="utf-8"))
    assert payload["gate"] == "readiness:10"
    assert payload["status"] == "PASS"
    assert payload["results"][0]["key"] == "demo"


def test_readiness_gate_failure_returns_nonzero_and_summarizes(tmp_path: Path) -> None:
    gate = load_module()
    dimensions = (
        gate.GateDimension(
            "demo",
            "Demo Gate",
            (gate.GateCommand((sys.executable, "--version"), "python version"),),
        ),
    )

    def runner(command, cwd):
        return subprocess.CompletedProcess(command, 9, "", "boom")

    assert gate.run_readiness_gate(artifact_dir=tmp_path, runner=runner, dimensions=dimensions) == 1
    payload = json.loads((tmp_path / "readiness-10-summary.json").read_text(encoding="utf-8"))
    assert payload["status"] == "FAIL"
    assert payload["failure_summary"] == ["Demo Gate: python version exited 9"]
    assert payload["results"][0]["commands"][0]["output_tail"] == "boom"


def test_required_root_script_parity_includes_readiness_10() -> None:
    gate = load_module()

    assert gate.REQUIRED_ROOT_SCRIPTS["readiness:10"] == "python scripts/ci/readiness_10_gate.py"
