"""Contract checks for externally consumed Layer 4/5 response envelopes."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

import pytest

pytestmark = pytest.mark.contract_static_no_service

CONTRACT_ROOT = Path(__file__).resolve().parents[2] / "contracts" / "openapi"


def _as_dict(value: object, label: str) -> dict[str, Any]:
    assert isinstance(value, dict), f"{label} must be an object"
    return cast(dict[str, Any], value)


def _spec(name: str) -> dict[str, Any]:
    return _as_dict(json.loads((CONTRACT_ROOT / name).read_text(encoding="utf-8")), name)


def _schema(spec: dict[str, Any], name: str) -> dict[str, Any]:
    return _as_dict(spec["components"]["schemas"][name], name)


def _response_schema(spec: dict[str, Any], path: str, method: str = "get") -> dict[str, Any]:
    response = spec["paths"][path][method]["responses"]["200"]
    return _as_dict(response["content"]["application/json"]["schema"], f"{method.upper()} {path}")


def test_layer4_workflow_routes_publish_concrete_response_models() -> None:
    spec = _spec("layer4-agents.json")

    assert _response_schema(spec, "/v1/workflows/types") == {
        "$ref": "#/components/schemas/AvailableWorkflowsResponse"
    }
    assert _response_schema(spec, "/v1/workflows/{workflow_id}", "delete") == {
        "$ref": "#/components/schemas/WorkflowCancelResponse"
    }
    assert _response_schema(spec, "/v1/workflows/{workflow_id}/result") == {
        "$ref": "#/components/schemas/WorkflowResultResponse"
    }

    workflow_result = _schema(spec, "WorkflowResultResponse")
    assert {"workflow_id", "status"}.issubset(set(workflow_result["required"]))
    output_schema = workflow_result["properties"]["output"]["anyOf"][0]
    if "$ref" in output_schema:
        ref_name = output_schema["$ref"].split("/")[-1]
        resolved = _schema(spec, ref_name)
        assert resolved["type"] == "object"
        assert "additionalProperties" in resolved
    else:
        assert output_schema["type"] == "object"
        assert "additionalProperties" in output_schema


def test_layer5_freshness_and_sync_routes_publish_concrete_response_models() -> None:
    spec = _spec("layer5-ground-truth.json")

    assert _response_schema(spec, "/api/v1/truths/sync-kg", "post") == {
        "$ref": "#/components/schemas/SyncToKgResponse"
    }
    assert _response_schema(spec, "/api/v1/truths/check-stale", "post") == {
        "$ref": "#/components/schemas/FreshnessCheckResponse"
    }
    assert _response_schema(spec, "/api/v1/truths/stale") == {
        "$ref": "#/components/schemas/StaleTruthsResponse"
    }
    assert _response_schema(spec, "/api/v1/truths/freshness-summary") == {
        "$ref": "#/components/schemas/FreshnessSummaryResponse"
    }

    assert set(_schema(spec, "SyncToKgResponse")["required"]) >= {"synced", "failed", "total_pending"}
    assert set(_schema(spec, "FreshnessCheckResponse")["required"]) >= {
        "checked",
        "marked_stale",
        "dry_run",
        "timestamp",
    }
    assert set(_schema(spec, "FreshnessSummaryResponse")["required"]) >= {
        "tenant_id",
        "timestamp",
        "summary",
        "warning_threshold_days",
    }


def test_error_envelope_shape_is_canonical_for_layer4_and_layer5() -> None:
    for spec_name in ("layer4-agents.json", "layer5-ground-truth.json"):
        error_schema = _schema(_spec(spec_name), "ErrorResponse")
        assert error_schema["required"] == ["error"]
        assert error_schema["additionalProperties"] is False
        assert set(error_schema["properties"]) == {"error"}
