"""Teeth test for the OTel TracerProvider centralization gate (PR5)."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
SCRIPT_PATH = REPO_ROOT / "scripts" / "ci" / "check_otel_tracer_provider_centralization.py"


def _load():
    name = "_vf_otel_centralization_gate"
    spec = importlib.util.spec_from_file_location(name, SCRIPT_PATH)
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod
    spec.loader.exec_module(mod)
    return mod


def test_gate_passes_on_clean_baseline() -> None:
    mod = _load()
    rc = mod.main(["--quiet"])
    assert rc == 0


def test_gate_unit_detects_name_form(tmp_path) -> None:
    mod = _load()
    f = tmp_path / "r.py"
    f.write_text(
        "from opentelemetry.sdk.trace import TracerProvider\n"
        "def boot():\n"
        "    provider = TracerProvider()\n",
        encoding="utf-8",
    )
    offenders = mod._find_tracer_provider_offenders(f)
    assert len(offenders) == 1
    assert offenders[0][1] == "TracerProvider(...)"


def test_gate_unit_detects_attribute_form(tmp_path) -> None:
    mod = _load()
    f = tmp_path / "r.py"
    f.write_text(
        "import opentelemetry.sdk.trace as t\n"
        "def x():\n"
        "    p = t.TracerProvider()\n",
        encoding="utf-8",
    )
    offenders = mod._find_tracer_provider_offenders(f)
    assert len(offenders) == 1
    assert offenders[0][1] == "TracerProvider(...)"


def test_find_offenders_skips_unrelated_raises(tmp_path) -> None:
    mod = _load()
    f = tmp_path / "x.py"
    f.write_text(
        "class Foo(Exception):\n"
        "    pass\n"
        "def x():\n"
        "    raise Foo('msg')\n"
        "    raise ValueError('bad')\n",
        encoding="utf-8",
    )
    offenders = mod._find_tracer_provider_offenders(f)
    assert offenders == []
