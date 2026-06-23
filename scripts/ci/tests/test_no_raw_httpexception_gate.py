"""Teeth test for the router HTTPException baseline gate.

Asserts that the CI script in
``scripts/ci/check_no_raw_httpexception_in_routers.py`` actually fails when a
new raw ``raise HTTPException(...)`` appears in router code outside the frozen
baseline. Without this, the gate could silently regress to a no-op.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "check_no_raw_httpexception_in_routers.py"


def _load_gate_module():
    name = "_vf_gate_httpexception"
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_gate_passes_on_clean_baseline() -> None:
    module = _load_gate_module()
    exit_code = module.main(["--quiet"])
    assert exit_code == 0, "Baseline should match current state; run --update-baseline locally."


def test_gate_detects_new_offender(tmp_path, monkeypatch) -> None:
    """Inject a synthetic router file and confirm the gate fails."""

    module = _load_gate_module()

    # Build a fake repo layout with a single router file containing a raise.
    fake_router = tmp_path / "services" / "fakesvc" / "src" / "fakesvc" / "api" / "routes" / "x.py"
    fake_router.parent.mkdir(parents=True, exist_ok=True)
    fake_router.write_text(
        "from fastapi import HTTPException\n"
        "def handler():\n"
        "    raise HTTPException(status_code=400, detail='nope')\n",
        encoding="utf-8",
    )

    # Empty baseline in the fake repo.
    baseline_dir = tmp_path / "config" / "ci"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = baseline_dir / "httpexception_router_allowlist.txt"
    baseline_path.write_text("# empty\n", encoding="utf-8")

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "BASELINE_FILE", baseline_path)

    exit_code = module.main(["--quiet"])
    assert exit_code == 1


def test_gate_passes_when_offender_is_in_baseline(tmp_path, monkeypatch) -> None:
    module = _load_gate_module()

    fake_router = tmp_path / "services" / "fakesvc" / "src" / "fakesvc" / "api" / "routes" / "x.py"
    fake_router.parent.mkdir(parents=True, exist_ok=True)
    source = (
        "from fastapi import HTTPException\n"
        "def handler():\n"
        "    raise HTTPException(status_code=400, detail='nope')\n"
    )
    fake_router.write_text(source, encoding="utf-8")

    baseline_dir = tmp_path / "config" / "ci"
    baseline_dir.mkdir(parents=True, exist_ok=True)
    baseline_path = baseline_dir / "httpexception_router_allowlist.txt"

    monkeypatch.setattr(module, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(module, "BASELINE_FILE", baseline_path)

    # Seed the baseline with the actual offender.
    module.main(["--update-baseline"])
    assert baseline_path.exists()

    # A second run with the same file should pass.
    exit_code = module.main(["--quiet"])
    assert exit_code == 0


def test_find_http_exception_raises_detects_attribute_form(tmp_path) -> None:
    module = _load_gate_module()
    f = tmp_path / "r.py"
    f.write_text(
        "import fastapi\n"
        "def x():\n"
        "    raise fastapi.HTTPException(status_code=500)\n",
        encoding="utf-8",
    )
    offenders = module._find_http_exception_raises(f)
    assert len(offenders) == 1
    assert offenders[0][1].endswith("HTTPException(...)")


def test_find_http_exception_raises_skips_unrelated_raises(tmp_path) -> None:
    module = _load_gate_module()
    f = tmp_path / "r.py"
    f.write_text(
        "class Foo(Exception):\n"
        "    pass\n"
        "def x():\n"
        "    raise Foo('msg')\n"
        "    raise ValueError('bad')\n",
        encoding="utf-8",
    )
    offenders = module._find_http_exception_raises(f)
    assert offenders == []
