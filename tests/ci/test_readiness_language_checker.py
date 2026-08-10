from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest


def _load_checker():
    path = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "check_readiness_language.py"
    spec = importlib.util.spec_from_file_location("test_check_readiness_language_module", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_checker_loads_canonical_baseline():
    checker = _load_checker()

    assert checker.BASELINE_PATH == (
        checker.REPO_ROOT / "config" / "baselines" / "readiness-language-baseline.json"
    )
    assert len(checker._load_baseline()) == 9


@pytest.mark.parametrize(
    "text",
    [
        "Status: NOT FINAL PRODUCTION READY — remaining failures are listed below.",
        "Launch if all gates pass.",
        "Before declaring Core GA ready, resolve every launch blocker.",
    ],
)
def test_checker_recognizes_explicit_readiness_boundaries(tmp_path, text):
    checker = _load_checker()
    document = tmp_path / "status.md"
    document.write_text(text, encoding="utf-8")
    checker.SCAN_ROOTS = (tmp_path,)
    checker.REPO_ROOT = tmp_path

    assert checker.scan() == []
