"""Integration tests for L2.5 Signal Refinery REST API routes.

Tests cover:
- CRUD lifecycle
- Review (approve/reject)
- Promote
- Lifecycle state validation
- 404 handling
- /refine endpoint (raw_signals and source_refs paths)
"""

from __future__ import annotations

import pytest
import pytest_asyncio

from .conftest import ACCOUNT_A, ACCOUNT_B, TENANT_A, make_signal_payload


pytestmark = pytest.mark.asyncio


# ---------------------------------------------------------------------------
# POST /api/v1/signals — create
# ---------------------------------------------------------------------------


async def test_create_signal_returns_201(client):
    payload = make_signal_payload()
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["type"] == "pain"
    assert data["account_id"] == str(ACCOUNT_A)
    assert data["tenant_id"] == str(TENANT_A)
    assert "id" in data
    assert "created_at" in data


async def test_create_signal_sets_tenant_from_request_context(client):
    """tenant_id must come from canonical request context, not request body."""
    payload = make_signal_payload()
    response = await client.post("/api/v1/signals", json=payload)
    assert response.status_code == 201
    assert response.json()["tenant_id"] == str(TENANT_A)


async def test_create_signal_missing_required_fields(client):
    response = await client.post("/api/v1/signals", json={"type": "pain"})
    assert response.status_code == 422


# ---------------------------------------------------------------------------
# GET /api/v1/signals — list
# ---------------------------------------------------------------------------


async def test_list_signals_returns_created(client):
    payload = make_signal_payload(content="Unique list test signal")
    create_resp = await client.post("/api/v1/signals", json=payload)
    assert create_resp.status_code == 201

    list_resp = await client.get("/api/v1/signals", params={"account_id": str(ACCOUNT_A)})
    assert list_resp.status_code == 200
    data = list_resp.json()
    assert "items" in data
    assert "total" in data
    ids = [s["id"] for s in data["items"]]
    assert create_resp.json()["id"] in ids


async def test_list_signals_requires_account_id(client):
    response = await client.get("/api/v1/signals")
    assert response.status_code == 422


async def test_list_signals_filters_by_type(client):
    await client.post("/api/v1/signals", json=make_signal_payload(signal_type="pain"))
    await client.post("/api/v1/signals", json=make_signal_payload(signal_type="opportunity"))

    resp = await client.get("/api/v1/signals", params={"account_id": str(ACCOUNT_A), "types": ["opportunity"]})
    assert resp.status_code == 200
    items = resp.json()["items"]
    assert all(s["type"] == "opportunity" for s in items)


# ---------------------------------------------------------------------------
# GET /api/v1/signals/{signal_id} — single
# ---------------------------------------------------------------------------


async def test_get_signal_returns_correct_signal(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    get_resp = await client.get(f"/api/v1/signals/{signal_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["id"] == signal_id


async def test_get_signal_not_found(client):
    response = await client.get("/api/v1/signals/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# PATCH /api/v1/signals/{signal_id} — update
# ---------------------------------------------------------------------------


async def test_patch_signal_updates_lifecycle_state(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    patch_resp = await client.patch(
        f"/api/v1/signals/{signal_id}",
        json={"lifecycle_state": "validated"},
    )
    assert patch_resp.status_code == 200
    assert patch_resp.json()["lifecycle_state"] == "validated"


async def test_patch_signal_empty_body_returns_422(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    patch_resp = await client.patch(f"/api/v1/signals/{signal_id}", json={})
    assert patch_resp.status_code == 422


# ---------------------------------------------------------------------------
# DELETE /api/v1/signals/{signal_id} — soft-delete
# ---------------------------------------------------------------------------


async def test_delete_signal_returns_204(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/api/v1/signals/{signal_id}")
    assert del_resp.status_code == 204


async def test_deleted_signal_not_in_list(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    await client.delete(f"/api/v1/signals/{signal_id}")

    list_resp = await client.get("/api/v1/signals", params={"account_id": str(ACCOUNT_A)})
    ids = [s["id"] for s in list_resp.json()["items"]]
    assert signal_id not in ids


async def test_delete_nonexistent_signal_returns_404(client):
    response = await client.delete("/api/v1/signals/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404


# ---------------------------------------------------------------------------
# POST /api/v1/signals/{signal_id}/review — review
# ---------------------------------------------------------------------------


async def test_review_approve_sets_validated(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    review_resp = await client.post(
        f"/api/v1/signals/{signal_id}/review",
        json={"status": "validated", "notes": "Looks good"},
    )
    assert review_resp.status_code == 200
    data = review_resp.json()
    assert data["lifecycle_state"] == "validated"
    assert data["validation_notes"] == "Looks good"


async def test_review_reject_sets_rejected(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    review_resp = await client.post(
        f"/api/v1/signals/{signal_id}/review",
        json={"status": "rejected"},
    )
    assert review_resp.status_code == 200
    assert review_resp.json()["lifecycle_state"] == "rejected"


async def test_review_invalid_status_returns_422(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    review_resp = await client.post(
        f"/api/v1/signals/{signal_id}/review",
        json={"status": "promoted"},  # not a valid review state
    )
    assert review_resp.status_code == 422


# ---------------------------------------------------------------------------
# POST /api/v1/signals/{signal_id}/promote — promote
# ---------------------------------------------------------------------------


async def test_promote_validated_signal(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    # First validate
    await client.post(f"/api/v1/signals/{signal_id}/review", json={"status": "validated"})

    promote_resp = await client.post(
        f"/api/v1/signals/{signal_id}/promote",
        json={"value_path_category": "revenue_uplift"},
    )
    assert promote_resp.status_code == 200
    data = promote_resp.json()
    assert data["lifecycle_state"] == "promoted"
    assert data["value_path_category"] == "revenue_uplift"


async def test_promote_rejected_signal_returns_409(client):
    create_resp = await client.post("/api/v1/signals", json=make_signal_payload())
    signal_id = create_resp.json()["id"]

    await client.post(f"/api/v1/signals/{signal_id}/review", json={"status": "rejected"})

    promote_resp = await client.post(
        f"/api/v1/signals/{signal_id}/promote",
        json={"value_path_category": "cost_savings"},
    )
    assert promote_resp.status_code == 409


# ---------------------------------------------------------------------------
# GET /api/v1/signals/account/{account_id}
# ---------------------------------------------------------------------------


async def test_get_account_signals_endpoint(client):
    await client.post("/api/v1/signals", json=make_signal_payload())
    resp = await client.get(f"/api/v1/signals/account/{ACCOUNT_A}")
    assert resp.status_code == 200
    assert "items" in resp.json()


# ---------------------------------------------------------------------------
# POST /api/v1/signals/refine — refinement batch
# ---------------------------------------------------------------------------


async def test_refine_with_raw_signals_returns_202(client):
    """Refine with actual raw_signals payloads — preferred path."""
    payload = {
        "account_id": str(ACCOUNT_A),
        "raw_signals": [
            {
                "account_id": str(ACCOUNT_A),
                "type": "pain_point",
                "content": "Customer reports slow onboarding process.",
                "confidence": 0.85,
                "evidence": [],
                "provenance": {
                    "extractor": "ai",
                    "method": "llm_extraction",
                    "extracted_at": "2026-05-14T12:00:00Z",
                },
                "source_refs": ["doc://test/onboarding-feedback"],
            },
            {
                "account_id": str(ACCOUNT_A),
                "type": "opportunity",
                "content": "Expansion opportunity in EMEA region.",
                "confidence": 0.72,
                "evidence": [],
                "provenance": {
                    "extractor": "ai",
                    "method": "llm_extraction",
                    "extracted_at": "2026-05-14T12:00:00Z",
                },
                "source_refs": ["doc://test/emea-report"],
            },
        ],
        "extraction_run_id": "run-test-refine-001",
    }
    resp = await client.post("/api/v1/signals/refine", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert data["refined"] == 2
    assert len(data["signal_ids"]) == 2


async def test_refine_raw_signals_maps_type_correctly(client):
    """Type mapping: 'pain_point' from L2 should be stored as 'pain'."""
    payload = {
        "account_id": str(ACCOUNT_A),
        "raw_signals": [
            {
                "account_id": str(ACCOUNT_A),
                "type": "pain_point",
                "content": "Slow API response times causing user frustration.",
                "confidence": 0.9,
                "evidence": [],
                "provenance": {
                    "extractor": "ai",
                    "method": "llm_extraction",
                    "extracted_at": "2026-05-14T12:00:00Z",
                },
                "source_refs": [],
            }
        ],
    }
    resp = await client.post("/api/v1/signals/refine", json=payload)
    assert resp.status_code == 202
    signal_id = resp.json()["signal_ids"][0]

    get_resp = await client.get(f"/api/v1/signals/{signal_id}")
    assert get_resp.status_code == 200
    data = get_resp.json()
    assert data["type"] == "pain"
    assert data["lifecycle_state"] == "extracted"
    assert data["content"] == "Slow API response times causing user frustration."
    assert data["tenant_id"] == str(TENANT_A)


async def test_refine_raw_signals_computes_trust_score(client):
    """Refined signals must have a non-zero trust_score derived from confidence."""
    payload = {
        "account_id": str(ACCOUNT_A),
        "raw_signals": [
            {
                "account_id": str(ACCOUNT_A),
                "type": "risk",
                "content": "Contract renewal at risk due to competitor pricing.",
                "confidence": 0.8,
                "evidence": [],
                "provenance": {
                    "extractor": "ai",
                    "method": "llm_extraction",
                    "extracted_at": "2026-05-14T12:00:00Z",
                },
                "source_refs": [],
            }
        ],
    }
    resp = await client.post("/api/v1/signals/refine", json=payload)
    assert resp.status_code == 202
    signal_id = resp.json()["signal_ids"][0]

    get_resp = await client.get(f"/api/v1/signals/{signal_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["trust_score"] > 0.0


async def test_refine_source_refs_fallback_returns_202(client):
    """source_refs-only path still returns 202 (backward compatibility)."""
    payload = {
        "account_id": str(ACCOUNT_A),
        "source_refs": ["doc://test/source-a", "doc://test/source-b"],
        "extraction_run_id": "run-compat-001",
    }
    resp = await client.post("/api/v1/signals/refine", json=payload)
    assert resp.status_code == 202
    data = resp.json()
    assert data["refined"] == 2
    assert len(data["signal_ids"]) == 2


async def test_refine_empty_body_returns_422(client):
    """Neither raw_signals nor source_refs provided — must be rejected."""
    payload = {
        "account_id": str(ACCOUNT_A),
    }
    resp = await client.post("/api/v1/signals/refine", json=payload)
    assert resp.status_code == 422
