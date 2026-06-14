from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.testclient import TestClient

# P0-008: Dev auth bypass permanently removed.
# Contract tests rely on GovernanceMiddleware + test JWT or mocked auth context.
os.environ.setdefault("ENVIRONMENT", "development")

from layer4_agents.api.routes import governance_workflows
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.permissions import Role

_TEST_CTX = RequestContext(
    tenant_id="tenant-governance",
    user_id="governance-contract-test",
    roles=[Role.CONTENT_ADMIN.value],
)

app = FastAPI()
app.include_router(governance_workflows.router, prefix="/v1")
register_exception_handlers(app)
app.dependency_overrides[governance_workflows.require_authenticated] = lambda: _TEST_CTX
app.dependency_overrides[governance_workflows.require_content_admin] = lambda: _TEST_CTX

client = TestClient(app)


def _error_message(response) -> str:
    """Return the API error message across canonical and legacy response envelopes."""

    body = response.json()
    error = body.get("error")
    if isinstance(error, dict):
        return str(error.get("message") or "")
    return str(body.get("message") or body.get("detail", ""))


def _lineage(correlation_id: str, business_case_id: str = "bc-1") -> dict:
    return {
        "business_case_id": business_case_id,
        "value_model_id": None,
        "correlation_id": correlation_id,
        "trace_id": correlation_id,
    }


def test_approval_gated_export_blocks_without_approval() -> None:
    review_payload = {
        "review_id": "rev-blocked",
        "status": "submitted",
        "subject_type": "business_case",
        "submitted_at": "2026-05-06T00:00:00Z",
        "lineage": _lineage("corr-blocked"),
    }
    review_resp = client.post("/v1/governance/reviews", json=review_payload)
    assert review_resp.status_code == 201

    export_resp = client.post(
        "/v1/governance/audit/exports",
        json={"review_id": "rev-blocked", "correlation_id": "corr-blocked"},
    )
    assert export_resp.status_code == 201
    assert export_resp.json()["status"] == "blocked"
    assert export_resp.json()["reason"] == "approval_required"
    assert export_resp.json()["immutable_audit_hash"].startswith("sha256:")


def test_lineage_retrieval_contains_review_decision_version_and_export() -> None:
    review_id = "rev-lineage"
    correlation_id = "corr-lineage"

    client.post(
        "/v1/governance/reviews",
        json={
            "review_id": review_id,
            "status": "submitted",
            "subject_type": "business_case",
            "submitted_at": "2026-05-06T00:00:00Z",
            "lineage": _lineage(correlation_id),
        },
    )

    decision_resp = client.post(
        f"/v1/governance/reviews/{review_id}/decisions",
        json={
            "decision_id": "dec-1",
            "review_id": review_id,
            "decision": "approved",
            "immutable_audit_hash": "sha256:abc",
            "decided_at": "2026-05-06T00:01:00Z",
            "lineage": _lineage(correlation_id),
        },
    )
    assert decision_resp.status_code == 201

    version_resp = client.post(
        "/v1/governance/versions",
        json={
            "version_id": "ver-1",
            "version_status": "active",
            "created_at": "2026-05-06T00:02:00Z",
            "lineage": _lineage(correlation_id),
        },
    )
    assert version_resp.status_code == 201

    export_resp = client.post(
        "/v1/governance/audit/exports",
        json={"review_id": review_id, "correlation_id": correlation_id},
    )
    assert export_resp.status_code == 201
    assert export_resp.json()["status"] == "pending"

    lineage_resp = client.get(f"/v1/governance/lineage/{correlation_id}")
    assert lineage_resp.status_code == 200
    payload = lineage_resp.json()
    assert len(payload["reviews"]) >= 1
    assert len(payload["decisions"]) >= 1
    assert len(payload["versions"]) >= 1
    assert len(payload["exports"]) >= 1
    assert payload["reviews"][0]["lineage"]["correlation_id"] == correlation_id
    assert payload["reviews"][0]["lineage"]["trace_id"] == correlation_id
    assert payload["exports"][0]["lineage"]["business_case_id"] == "bc-1"


def test_frontend_query_key_route_contracts_are_reachable() -> None:
    review_id = "rev-query-key"
    correlation_id = "corr-query-key"

    created = client.post(
        "/v1/governance/reviews",
        json={
            "review_id": review_id,
            "status": "submitted",
            "subject_type": "business_case",
            "submitted_at": "2026-05-06T00:00:00Z",
            "lineage": _lineage(correlation_id),
        },
    )
    assert created.status_code == 201

    review_detail = client.get(f"/v1/governance/reviews/{review_id}")
    assert review_detail.status_code == 200
    assert review_detail.json()["review_id"] == review_id

    review_queue = client.get("/v1/governance/reviews", params={"status": "submitted"})
    assert review_queue.status_code == 200
    assert any(item["review_id"] == review_id for item in review_queue.json())

    version = client.post(
        "/v1/governance/versions",
        json={
            "version_id": "ver-query-key-a",
            "version_status": "active",
            "created_at": "2026-05-06T00:02:00Z",
            "lineage": _lineage(correlation_id),
            "snapshot": {"arr": 1, "npv": 10},
        },
    )
    assert version.status_code == 201

    version_compare = client.post(
        "/v1/governance/versions",
        json={
            "version_id": "ver-query-key-b",
            "version_status": "superseded",
            "created_at": "2026-05-06T00:03:00Z",
            "lineage": _lineage(correlation_id),
            "snapshot": {"arr": 2, "npv": 10},
        },
    )
    assert version_compare.status_code == 201

    version_detail = client.get("/v1/governance/versions/ver-query-key-a")
    assert version_detail.status_code == 200
    assert version_detail.json()["version_id"] == "ver-query-key-a"

    diff = client.get(
        "/v1/governance/versions/ver-query-key-a/diff",
        params={"compare_to_version_id": "ver-query-key-b"},
    )
    assert diff.status_code == 200
    assert set(diff.json()["changed_fields"]) == {"arr", "version_status"}

    export = client.post(
        "/v1/governance/audit/exports",
        json={"review_id": review_id, "correlation_id": correlation_id},
    )
    assert export.status_code == 201
    export_id = export.json()["audit_export_id"]

    export_detail = client.get(f"/v1/governance/audit/exports/{export_id}")
    assert export_detail.status_code == 200
    assert export_detail.json()["audit_export_id"] == export_id

    lineage = client.get(f"/v1/governance/lineage/{correlation_id}")
    assert lineage.status_code == 200


def test_immutable_governance_objects_reject_duplicate_ids() -> None:
    payload = {
        "review_id": "rev-immutable",
        "status": "submitted",
        "subject_type": "business_case",
        "submitted_at": "2026-05-06T00:00:00Z",
        "lineage": _lineage("corr-immutable"),
    }

    first = client.post("/v1/governance/reviews", json=payload)
    assert first.status_code == 201

    duplicate = client.post("/v1/governance/reviews", json={**payload, "status": "approved"})
    assert duplicate.status_code == 409
    assert "immutable" in _error_message(duplicate)


def test_export_fails_closed_when_correlation_id_does_not_match_review() -> None:
    review_id = "rev-lineage-mismatch"
    review = client.post(
        "/v1/governance/reviews",
        json={
            "review_id": review_id,
            "status": "submitted",
            "subject_type": "business_case",
            "submitted_at": "2026-05-06T00:00:00Z",
            "lineage": _lineage("corr-review"),
        },
    )
    assert review.status_code == 201

    export = client.post(
        "/v1/governance/audit/exports",
        json={"review_id": review_id, "correlation_id": "corr-other"},
    )

    assert export.status_code == 422
    assert _error_message(export) == "export lineage mismatch"
