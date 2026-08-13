"""Regression protection: every OpenAPI endpoint must have an endpoint-hook
registry entry.

Failure mode covered: new backend/gateway endpoints were added to
``contracts/openapi/*.json`` without updating
``apps/web/contracts/endpoint-hook-registry.json``, leaving the
``check_endpoint_coverage.py`` CI gate red on main (observed 2026-08-12,
27 unmapped endpoints). Running the checker here ties the gate into the
contract test suite (``make contract-tests`` / ``make verify``) so the drift
fails at the earliest local gate instead of only in a non-required CI lane.

Intended behavior: the checker exits 0 (no missing/stale/orphan mappings,
no duplicates, no policy breaches). Unintended behavior fails: any OpenAPI
endpoint absent from the registry fails this test with the checker's full
report.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

pytestmark = [pytest.mark.contract_static, pytest.mark.unit]

REPO_ROOT = Path(__file__).resolve().parents[2]
CHECKER_PATH = REPO_ROOT / "scripts" / "ci" / "check_endpoint_coverage.py"
REGISTRY_PATH = REPO_ROOT / "apps" / "web" / "contracts" / "endpoint-hook-registry.json"
OPENAPI_DIR = REPO_ROOT / "contracts" / "openapi"


def _load_checker():
    spec = importlib.util.spec_from_file_location("check_endpoint_coverage", CHECKER_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module  # dataclasses resolve cls.__module__ via sys.modules
    spec.loader.exec_module(module)
    return module


def test_openapi_endpoints_all_registered_in_endpoint_hook_registry() -> None:
    checker = _load_checker()
    exit_code, report = checker.check_registry(REGISTRY_PATH, OPENAPI_DIR)
    assert exit_code == 0, (
        "endpoint-hook registry drifted from OpenAPI specs; "
        "add registry entries per the existing generated-entry convention "
        "(do not weaken the checker):\n" + report
    )
