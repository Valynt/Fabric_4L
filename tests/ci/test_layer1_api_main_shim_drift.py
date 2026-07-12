from __future__ import annotations

import ast
import importlib.util
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_PATH = REPO_ROOT / "scripts/ci/check_layer1_api_main_shim_drift.py"


def _load_gate_module():
    spec = importlib.util.spec_from_file_location("check_layer1_api_main_shim_drift", SCRIPT_PATH)
    assert spec is not None
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module


def _parse(source: str) -> ast.Module:
    return ast.parse(source, filename="shim.py")


def test_layer1_api_main_shim_drift_gate_passes_current_repo() -> None:
    result = subprocess.run(
        [sys.executable, str(SCRIPT_PATH)],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert result.returncode == 0, result.stdout + result.stderr
    assert "Layer 1 API main shim drift check passed." in result.stdout


def test_layer1_api_main_shim_drift_gate_accepts_reexport_shim() -> None:
    gate = _load_gate_module()
    tree = _parse(
        "from layer1_ingestion.api import main as _canonical_main\n"
        "for _name in dir(_canonical_main):\n"
        "    globals()[_name] = getattr(_canonical_main, _name)\n"
    )

    assert gate._imports_canonical_main(tree)
    assert gate._implementation_nodes(tree) == []


def test_layer1_api_main_shim_drift_gate_rejects_independent_routes() -> None:
    gate = _load_gate_module()
    tree = _parse(
        "from fastapi import FastAPI\n"
        "app = FastAPI()\n"
        "@app.get('/drift')\n"
        "async def drift():\n"
        "    return {'ok': True}\n"
    )

    findings = gate._implementation_nodes(tree)

    assert findings
    assert (2, "call:FastAPI") in findings
    assert (4, "AsyncFunctionDef") in findings
    assert not gate._imports_canonical_main(tree)
