"""Representative success/error shape regression tests for generated APIs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema_assertions import assert_matches_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
L4_OPENAPI = REPO_ROOT / "contracts" / "openapi" / "layer4-agents.json"
L5_OPENAPI = REPO_ROOT / "contracts" / "openapi" / "layer5-ground-truth.json"


def _load_openapi(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _response_schema(
    document: dict[str, Any],
    *,
    path: str,
    method: str,
    status_code: str,
) -> dict[str, Any]:
    operation = document["paths"][path][method]
    response = operation["responses"][status_code]
    content = response.get("content")
    if not content:
        raise AssertionError(
            f"{method.upper()} {path} {status_code} does not declare a response body schema"
        )
    return content["application/json"]["schema"]


def _assert_response_shape(
    document_path: Path,
    *,
    path: str,
    method: str,
    status_code: str,
    payload: dict[str, Any],
) -> None:
    document = _load_openapi(document_path)
    schema = _response_schema(document, path=path, method=method, status_code=status_code)
    assert_matches_schema(payload, schema, root=document)


def test_l4_workflow_status_success_shape_is_stable() -> None:
    payload = {
        "id": "wf-123",
        "workflow_type": "business_case",
        "status": "running",
        "current_state": "analyzing",
        "current_node": "prepare_inputs",
        "progress": 45.0,
        "started_at": "2026-05-13T12:00:00Z",
        "completed_at": None,
        "error_count": 0,
        "has_output": False,
        "results": None,
        "tenant_id": "tenant-123",
        "user_id": "user-123",
        "priority": 1,
        "scheduler_status": "running",
        "progress_meta": None,
    }
    _assert_response_shape(
        L4_OPENAPI,
        path="/v1/workflows/{workflow_id}",
        method="get",
        status_code="200",
        payload=payload,
    )


def test_l4_workflow_resume_validation_error_shape_is_stable() -> None:
    payload = {
        "error": {
            "message": "resume_data is required",
            "code": "validation_error",
            "request_id": "trace-l4-resume-001",
            "details": {"field": "resume_data"},
        },
    }
    _assert_response_shape(
        L4_OPENAPI,
        path="/v1/workflows/{workflow_id}/resume",
        method="post",
        status_code="422",
        payload=payload,
    )


def test_l5_truth_detail_success_shape_is_stable() -> None:
    payload = {
        "id": "11111111-1111-1111-1111-111111111111",
        "tenant_id": "22222222-2222-2222-2222-222222222222",
        "claim": "Invoice processing time was reduced by 40 percent.",
        "claim_type": "efficiency_gain",
        "confidence": 0.92,
        "status": "approved",
        "maturity_level": 4,
        "freshness": "2026-05-13T12:00:00Z",
        "is_stale": False,
        "created_at": "2026-05-12T12:00:00Z",
        "updated_at": "2026-05-13T12:00:00Z",
        "sources": [],
        "validation_events": [],
        "maturity_history": [],
        "value": {"annual_hours_saved": 1200},
        "applies_to": {"account_id": "acct-123"},
        "expires_at": None,
    }
    _assert_response_shape(
        L5_OPENAPI,
        path="/api/v1/truths/{truth_id}",
        method="get",
        status_code="200",
        payload=payload,
    )


def test_l5_truth_detail_validation_error_shape_is_stable() -> None:
    payload = {
        "error": {
            "message": "truth_id must be a valid UUID",
            "code": "validation_error",
            "request_id": "trace-l5-truth-001",
            "details": {"path": ["truth_id"]},
        },
    }
    _assert_response_shape(
        L5_OPENAPI,
        path="/api/v1/truths/{truth_id}",
        method="get",
        status_code="422",
        payload=payload,
    )
