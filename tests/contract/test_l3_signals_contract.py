"""Contract guardrails for canonical Layer 3 ValueSignal graph routes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from .schema_assertions import assert_matches_schema

pytestmark = pytest.mark.contract_static_no_service

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_L3_PATH = REPO_ROOT / "contracts" / "openapi" / "layer3-knowledge.json"
SIGNALS_PATH = "/v1/graph/signals"


def _load_l3_openapi() -> dict[str, Any]:
    return json.loads(OPENAPI_L3_PATH.read_text(encoding="utf-8"))


def _schema_ref(doc: dict[str, Any], name: str) -> dict[str, Any]:
    return {
        "$ref": f"#/components/schemas/{name}",
        "components": doc.get("components", {}),
    }


def test_signal_graph_routes_are_mounted_in_layer3_openapi() -> None:
    """Canonical ValueSignal graph routes must be present in Layer 3 OpenAPI."""
    l3_openapi = _load_l3_openapi()

    assert SIGNALS_PATH in l3_openapi["paths"]
    assert f"{SIGNALS_PATH}/{{signal_id}}" in l3_openapi["paths"]
    assert f"{SIGNALS_PATH}/{{signal_id}}/related" in l3_openapi["paths"]


def test_persist_signal_response_uses_declared_signal_node_envelope() -> None:
    """POST /v1/graph/signals returns SignalNode, not an ad-hoc status wrapper."""
    l3_openapi = _load_l3_openapi()
    created_response = l3_openapi["paths"][SIGNALS_PATH]["post"]["responses"]["201"]
    schema = created_response["content"]["application/json"]["schema"]

    assert schema == {"$ref": "#/components/schemas/SignalNode"}

    sample_response = {
        "id": "sig-001",
        "tenant_id": "tenant-001",
        "account_id": "acct-001",
        "type": "PainSignal",
        "content": "Manual invoice triage slows month-end close.",
        "confidence": 0.91,
        "trust_score": 0.87,
        "lifecycle_state": "validated",
        "impact_area": "finance_operations",
        "created_at": "2026-05-30T00:00:00Z",
        "updated_at": "2026-05-30T00:00:00Z",
    }
    assert_matches_schema(
        sample_response, _schema_ref(l3_openapi, "SignalNode"), root=l3_openapi
    )
    assert "status" not in sample_response
    assert "signal" not in sample_response
