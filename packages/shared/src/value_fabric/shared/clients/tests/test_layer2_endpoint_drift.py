"""Endpoint-drift regression guard for the Layer 2 client family.

Every endpoint literal owned by ``value_fabric.shared.clients.layer2`` must
remain live in the authoritative OpenAPI contract
(``contracts/openapi/layer2-extraction.json``, hermetic-generated from the
Layer 2 source).  If a Layer 2 route is removed or a client literal is
changed without regenerating the contract, this test fails instead of letting
production callers hit dead endpoints.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from value_fabric.shared.clients.layer2 import (
    EXTRACT_AND_INGEST_PATH,
    EXTRACT_BATCH_PATH,
    EXTRACT_PATH,
    EXTRACT_STATUS_PATH,
    LAYER2_ENDPOINTS,
)

_REPO_ROOT = Path(__file__).resolve().parents[7]
_OPENAPI_PATH = _REPO_ROOT / "contracts" / "openapi" / "layer2-extraction.json"

_METHOD_EXPECTATIONS: dict[str, set[str]] = {
    EXTRACT_PATH: {"post"},
    EXTRACT_AND_INGEST_PATH: {"post"},
    EXTRACT_STATUS_PATH: {"get"},
    EXTRACT_BATCH_PATH: {"post"},
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
    missing = [name for name, path in LAYER2_ENDPOINTS.items() if path not in paths]
    assert not missing, (
        f"Client endpoint literals point at routes that do not exist in the "
        f"Layer 2 OpenAPI contract: {missing}"
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
    assert EXTRACT_STATUS_PATH in paths, f"Missing contract path {EXTRACT_STATUS_PATH}"
    for method, operation in paths[EXTRACT_STATUS_PATH].items():
        if method not in {"get", "post", "put", "patch", "delete"}:
            continue
        params = {
            p["name"]
            for p in operation.get("parameters", [])
            if p.get("in") == "path"
        }
        assert "job_id" in params, f"{method.upper()} {EXTRACT_STATUS_PATH} lost path param 'job_id'"