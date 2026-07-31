from __future__ import annotations

import importlib.util
import sys
from pathlib import Path


def _load_checker():
    path = Path(__file__).resolve().parents[2] / "scripts" / "ci" / "check_deprecation_drift.py"
    spec = importlib.util.spec_from_file_location("test_check_deprecation_drift_module", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


def test_checker_loads_canonical_baseline():
    checker = _load_checker()

    assert checker.BASELINE_PATH == (
        checker.REPO_ROOT / "config" / "baselines" / "deprecation-drift-baseline.json"
    )
    assert len(checker._load_baseline()) == 24


def test_optional_request_check_only_flags_fastapi_route_parameters(tmp_path):
    checker = _load_checker()
    source = tmp_path / "routes.py"
    source.write_text(
        "from fastapi import Request\n"
        "def helper(request: Request | None): ...\n"
        "def other(value: StatusChangeRequest | None): ...\n"
        "@router.get('/items')\n"
        "async def items(request: Request | None = None): ...\n",
        encoding="utf-8",
    )
    checker.SCAN_ROOTS = (tmp_path,)
    checker.REPO_ROOT = tmp_path

    findings = checker.scan()

    assert [(item.category, item.line) for item in findings] == [("request_type_response", 5)]
