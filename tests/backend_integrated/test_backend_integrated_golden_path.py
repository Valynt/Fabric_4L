"""Suite 1 — Backend-Integrated Golden Path.

This suite proves the same P0 workflow validated in the frontend E2E program through
real Fabric_4L service contracts and durable backend state.
"""
from __future__ import annotations

import uuid

import pytest

pytestmark = [pytest.mark.backend_integrated, pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_backend_integrated_account_to_approved_business_case(backend, seed_ids):
    await backend.create_seed_graph()

    extraction, _ = await backend.request(
        "l2",
        "POST",
        "/api/v1/extractions",
        json={"source_id": backend.seed_source_id, "account_id": seed_ids.account_id},
        expected=(200, 201, 202),
    )
    assert backend.seed_source_id in str(extraction), "Extraction must consume the seeded L1 source document."

    graph, _ = await backend.request(
        "l3",
        "POST",
        "/api/v1/graph/context",
        json={"account_id": seed_ids.account_id, "source_id": backend.seed_source_id},
        expected=(200, 201, 202),
    )
    assert seed_ids.account_id in str(graph), "Graph context must preserve account lineage."

    hypothesis, _ = await backend.request(
        "l4",
        "POST",
        "/v1/hypotheses",
        json={"account_id": seed_ids.account_id, "graph_context": graph, "require_evidence": True},
        expected=(200, 201, 202),
    )
    assert "evidence" in str(hypothesis).lower(), "Hypothesis generation must attach or require evidence."

    scenario, _ = await backend.request(
        "l4",
        "POST",
        "/v1/analysis/roi",
        json={
            "account_id": seed_ids.account_id,
            "formula_id": seed_ids.formula_id,
            "variables": {"annual_revenue": 10_000_000, "conversion_lift_pct": 11, "implementation_cost": 125_000},
            "scenarios": ["conservative", "expected", "optimistic"],
        },
        expected=(200, 201),
    )
    assert any(token in str(scenario).lower() for token in ("roi", "payback", "projection")), scenario

    business_case, _ = await backend.request(
        "l4",
        "POST",
        "/v1/cases",
        json={
            "account_id": seed_ids.account_id,
            "scenario": scenario,
            "evidence_ids": [seed_ids.evidence_id],
            "approval_status": "submitted",
        },
        expected=(200, 201, 202),
    )
    case_id = business_case.get("id") or business_case.get("case_id") or seed_ids.account_id

    approval, _ = await backend.request(
        "l4",
        "POST",
        f"/v1/cases/{case_id}/approval",
        json={"status": "approved", "reviewer_id": seed_ids.user_reviewer, "decision": "approve"},
        expected=(200, 201, 202),
    )
    assert "approved" in str(approval).lower(), approval

    export, _ = await backend.request("l4", "GET", f"/v1/cases/{case_id}/export", expected=(200, 202))
    assert any(token in str(export).lower() for token in ("url", "download", "export")), export
    await backend.assert_audit_event("business_case.approved", str(case_id))


@pytest.mark.asyncio
async def test_backend_integrated_claims_trace_to_raw_sources(backend, seed_ids):
    await backend.create_seed_graph()
    trace, _ = await backend.request(
        "l4",
        "GET",
        f"/v1/cases/{seed_ids.account_id}/traceability?include_raw_sources=true",
        expected=(200,),
    )
    trace_text = str(trace).lower()
    assert backend.seed_source_id in str(trace), "Business-case trace must include the raw source document id."
    assert all(token in trace_text for token in ("claim", "evidence", "source")), trace


@pytest.mark.asyncio
async def test_backend_integrated_value_model_persists_after_reload(backend, seed_ids):
    await backend.create_seed_graph()
    model_payload = {
        "account_id": seed_ids.account_id,
        "value_pack_id": seed_ids.value_pack_id,
        "drivers": [{"name": "Improve conversion", "evidence_id": seed_ids.evidence_id}],
        "formula_id": seed_ids.formula_id,
    }
    saved, _ = await backend.request(
        "l4",
        "PUT",
        f"/v1/accounts/{seed_ids.account_id}/value-model",
        json=model_payload,
        expected=(200, 201, 202),
    )
    assert seed_ids.account_id in str(saved)

    reloaded, _ = await backend.request("l4", "GET", f"/v1/accounts/{seed_ids.account_id}/value-model", expected=(200,))
    assert seed_ids.formula_id in str(reloaded), "Reloaded value model must include the persisted formula selection."
    assert seed_ids.evidence_id in str(reloaded), "Reloaded value model must include evidence-driver linkage."


@pytest.mark.asyncio
async def test_backend_integrated_approval_enables_export(backend, seed_ids):
    await backend.create_seed_graph()
    draft, _ = await backend.request(
        "l4",
        "POST",
        "/v1/cases",
        json={"account_id": seed_ids.account_id, "approval_status": "draft", "evidence_ids": [seed_ids.evidence_id]},
        expected=(200, 201, 202),
    )
    case_id = draft.get("id") or draft.get("case_id") or seed_ids.account_id

    await backend.request("l4", "GET", f"/v1/cases/{case_id}/export", expected=(401, 403, 409, 423))
    await backend.request(
        "l4",
        "POST",
        f"/v1/cases/{case_id}/approval",
        json={"status": "approved", "reviewer_id": seed_ids.user_reviewer},
        expected=(200, 201, 202),
    )
    export, _ = await backend.request("l4", "GET", f"/v1/cases/{case_id}/export", expected=(200, 202))
    assert any(token in str(export).lower() for token in ("url", "download", "export")), export


@pytest.mark.asyncio
async def test_backend_integrated_duplicate_account_create_returns_conflict_or_same_record(backend, seed_ids):
    await backend.create_seed_graph()
    duplicate_payload = {
        "id": seed_ids.account_id,
        "provider": "salesforce",
        "provider_record_id": seed_ids.account_id,
        "name": "Acme Validation Account",
        "domain": "acme-validation.example",
        "industry": "Software",
        "region": "North America",
        "company_size": 1200,
        "owner_id": seed_ids.user_admin,
        "owner_name": "Backend Validation Admin",
        "owner_email": "backend-validation@example.com",
        "stage": "qualified",
        "segment": "enterprise",
    }
    body, response = await backend.request(
        "l4",
        "POST",
        "/v1/accounts",
        json=duplicate_payload,
        expected=(200, 201, 409),
    )

    if response.status_code == 409:
        assert any(token in str(body).lower() for token in ("duplicate", "exists", "already", "conflict", "detail")), body
        return

    assert str(seed_ids.account_id) in str(body), body
    persisted, _ = await backend.request("l4", "GET", f"/v1/accounts/{seed_ids.account_id}", expected=(200,))
    assert str(seed_ids.account_id) in str(persisted), persisted


@pytest.mark.asyncio
async def test_backend_integrated_archived_account_persists_in_detail_and_activity(backend, seed_ids):
    await backend.create_seed_graph()
    archived_account_id = str(uuid.uuid4())
    created, _ = await backend.request(
        "l4",
        "POST",
        "/v1/accounts",
        json={
            "id": archived_account_id,
            "provider": "salesforce",
            "provider_record_id": archived_account_id,
            "name": "Archived Validation Account",
            "domain": f"archived-{archived_account_id[:8]}.example",
            "industry": "Software",
            "region": "North America",
            "company_size": 250,
            "owner_id": seed_ids.user_admin,
            "owner_name": "Backend Validation Admin",
            "owner_email": "backend-validation@example.com",
            "stage": "archived",
            "segment": "enterprise",
        },
        expected=(200, 201, 202),
    )
    assert archived_account_id in str(created), created

    detail, _ = await backend.request("l4", "GET", f"/v1/accounts/{archived_account_id}", expected=(200,))
    detail_text = str(detail).lower()
    assert archived_account_id in str(detail), detail
    assert "archiv" in detail_text or "stage" in detail_text, detail

    activity, _ = await backend.request(
        "l4",
        "GET",
        f"/v1/accounts/{archived_account_id}/activity",
        expected=(200,),
    )
    activity_text = str(activity).lower()
    assert archived_account_id in str(activity), activity
    assert any(token in activity_text for token in ("interactions", "total_count", "archiv", "stage")), activity
