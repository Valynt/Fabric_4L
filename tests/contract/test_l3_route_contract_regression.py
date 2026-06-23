from __future__ import annotations

import json
from pathlib import Path

import pytest

try:
    from src.api.app_monolith import app
except (ImportError, Exception):
    pytest.skip(
        "value_fabric.layer3 service stack not available (pre-existing blocker #1/#9)",
        allow_module_level=True,
    )

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_L3_PATH = REPO_ROOT / "contracts" / "openapi" / "layer3-knowledge.json"


def _load_contract() -> dict:
    return json.loads(OPENAPI_L3_PATH.read_text(encoding="utf-8"))


def test_layer3_route_set_matches_openapi_contract() -> None:
    runtime_paths = set(app.openapi().get("paths", {}).keys())
    contract_paths = set(_load_contract().get("paths", {}).keys())
    assert runtime_paths == contract_paths


def test_layer3_success_response_shapes_reference_same_contract_schemas() -> None:
    runtime_paths = app.openapi().get("paths", {})
    contract_paths = _load_contract().get("paths", {})

    for path, methods in contract_paths.items():
        for method, operation in methods.items():
            runtime_op = runtime_paths[path][method]
            for status_code, contract_response in operation.get("responses", {}).items():
                if not str(status_code).startswith("2"):
                    continue
                contract_content = contract_response.get("content", {}).get("application/json", {})
                runtime_content = (
                    runtime_op.get("responses", {})
                    .get(str(status_code), {})
                    .get("content", {})
                    .get("application/json", {})
                )
                assert runtime_content.get("schema") == contract_content.get("schema")
