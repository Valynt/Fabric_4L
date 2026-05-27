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


def test_gate_detects_new_tracer_provider(tmp_path, monkeypatch) -> None:
    mod = _load()
    svc = tmp_path / "services" / "newsvc" / "src" / "main.py"
    svc.parent.mkdir(parents=True, exist_ok=True)
    svc.write_text(
        "from opentelemetry.sdk.trace import TracerProvider\n"
        "from opentelemetry import trace\n"
        "def boot():\n"
        "    provider = TracerProvider()\n"
        "    trace.set_tracer_provider(provider)\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "config" / "ci" / "otel_tracer_provider_baseline.txt"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("# empty\n", encoding="utf-8")

    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "BASELINE_FILE", baseline)
    monkeypatch.setattr(
        mod,
        "SCAN_ROOTS",
        (tmp_path / "services",),
    )

    rc = mod.main(["--quiet"])
    assert rc == 1


def test_gate_skips_test_files(tmp_path, monkeypatch) -> None:
    mod = _load()
    test_file = tmp_path / "services" / "newsvc" / "tests" / "test_boot.py"
    test_file.parent.mkdir(parents=True, exist_ok=True)
    test_file.write_text(
        "from opentelemetry.sdk.trace import TracerProvider\n"
        "def fixture():\n"
        "    return TracerProvider()\n",
        encoding="utf-8",
    )
    baseline = tmp_path / "config" / "ci" / "otel_tracer_provider_baseline.txt"
    baseline.parent.mkdir(parents=True, exist_ok=True)
    baseline.write_text("# empty\n", encoding="utf-8")

    monkeypatch.setattr(mod, "REPO_ROOT", tmp_path)
    monkeypatch.setattr(mod, "BASELINE_FILE", baseline)
    monkeypatch.setattr(mod, "SCAN_ROOTS", (tmp_path / "services",))

    rc = mod.main(["--quiet"])
    assert rc == 0


def test_find_offenders_detects_attribute_form(tmp_path) -> None:
    mod = _load()
    f = tmp_path / "x.py"
    f.write_text(
        "import opentelemetry.sdk.trace as t\n"
        "def x():\n"
        "    p = t.TracerProvider()\n",
        encoding="utf-8",
    )
    offenders = mod._find_tracer_provider_offenders(f)
    assert len(offenders) == 1
