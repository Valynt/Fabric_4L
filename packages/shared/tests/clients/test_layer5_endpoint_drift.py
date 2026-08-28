"""Endpoint-drift regression guard for the Layer 5 client family.

Every endpoint literal owned by ``value_fabric.shared.clients.layer5`` must
remain live in the authoritative OpenAPI contract
(``contracts/openapi/layer5-ground-truth.json``, hermetic-generated from the
Layer 5 source).  If a Layer 5 route is removed or a client literal is
changed without regenerating the contract, this test fails instead of letting
production callers hit dead endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from value_fabric.shared.clients.layer5 import (
    LAYER5_ENDPOINTS,
    MATURITY_LADDER_PATH,
    TRUTH_AUDIT_PATH,
    TRUTH_ITEM_PATH,
    TRUTH_SOURCES_PATH,
    TRUTH_VALIDATE_PATH,
    TRUTHS_CHECK_STALE_PATH,
    TRUTHS_FRESHNESS_SUMMARY_PATH,
    TRUTHS_PATH,
    TRUTHS_STALE_PATH,
    TRUTHS_SYNC_KG_PATH,
)


def _find_repo_root() -> Path:
    """Walk up from this file to the repository root (has ``contracts/openapi``)."""
    current = Path(__file__).resolve().parent
    while current != current.parent:
        if (current / "contracts" / "openapi").is_dir():
            return current
        current = current.parent
    raise RuntimeError("Could not locate repository root from test file")


_REPO_ROOT = _find_repo_root()
_OPENAPI_PATH = _REPO_ROOT / "contracts" / "openapi" / "layer5-ground-truth.json"

_METHOD_EXPECTATIONS: dict[str, set[str]] = {
    TRUTHS_PATH: {"get", "post"},
    TRUTH_ITEM_PATH: {"get", "delete"},
    TRUTH_VALIDATE_PATH: {"post"},
    TRUTH_AUDIT_PATH: {"get"},
    TRUTH_SOURCES_PATH: {"post"},
    TRUTHS_SYNC_KG_PATH: {"post"},
    TRUTHS_CHECK_STALE_PATH: {"post"},
    TRUTHS_STALE_PATH: {"get"},
    TRUTHS_FRESHNESS_SUMMARY_PATH: {"get"},
    MATURITY_LADDER_PATH: {"get"},
}


@pytest.fixture(scope="module")
def openapi_spec() -> dict:
    if not _OPENAPI_PATH.exists():
        pytest.skip(f"OpenAPI contract not found at {_OPENAPI_PATH}")
    return json.loads(_OPENAPI_PATH.read_text(encoding="utf-8"))


def test_openapi_contract_exists() -> None:
    assert _OPENAPI_PATH.exists(), (
        "Missing canonical contract; regenerate with scripts/export_openapi.py"
    )


def test_every_registered_literal_is_live(openapi_spec: dict) -> None:
    paths = openapi_spec.get("paths", {})
    missing = [name for name, path in LAYER5_ENDPOINTS.items() if path not in paths]
    assert not missing, (
        f"Client endpoint literals point at routes that do not exist in the "
        f"Layer 5 OpenAPI contract: {missing}"
    )


def test_http_methods_match_openapi(openapi_spec: dict) -> None:
    paths = openapi_spec.get("paths", {})
    mismatches: list[str] = []
    for path, expected in _METHOD_EXPECTATIONS.items():
        methods = {m.lower() for m in paths.get(path, {})}
        missing_methods = expected - methods
        if missing_methods:
            mismatches.append(f"{path} lacks {sorted(missing_methods)}")
    assert not mismatches, (
        f"Client methods disagree with the OpenAPI contract: {mismatches}"
    )


def test_templated_paths_share_parameter_name(openapi_spec: dict) -> None:
    paths = openapi_spec.get("paths", {})
    for path in (TRUTH_ITEM_PATH, TRUTH_VALIDATE_PATH, TRUTH_AUDIT_PATH, TRUTH_SOURCES_PATH):
        assert path in paths, f"Missing contract path {path}"
        item = paths[path]
        for method, operation in item.items():
            if method not in {"get", "post", "put", "patch", "delete"}:
                continue
            params = {
                p["name"]
                for p in operation.get("parameters", [])
                if p.get("in") == "path"
            }
            assert "truth_id" in params, f"{method.upper()} {path} lost path param 'truth_id'"