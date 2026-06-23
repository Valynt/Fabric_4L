"""Suite 3 — Tenant Isolation and Security Persistence.

These tests are production gates and intentionally contain no skip or xfail paths.
They validate tenant isolation across API, persistence, graph, search, agent,
export, and audit surfaces.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.backend_integrated, pytest.mark.integration, pytest.mark.security, pytest.mark.tenant_boundary]


@pytest.mark.asyncio
async def test_cross_tenant_account_access_fails_closed(backend, seed_ids):
    await backend.create_seed_graph()
    await backend.assert_cross_tenant_denied("l4", f"/v1/accounts/{seed_ids.account_id}")


@pytest.mark.asyncio
async def test_cross_tenant_document_access_fails_closed(backend, seed_ids):
    await backend.create_seed_graph()
    await backend.assert_cross_tenant_denied("l1", f"/api/v1/ingestion/sources/{backend.seed_source_id}")


@pytest.mark.asyncio
async def test_cross_tenant_graph_query_returns_no_foreign_entities(backend, seed_ids):
    await backend.create_seed_graph()
    graph, _ = await backend.request(
        "l3",
        "GET",
        f"/api/v1/graph/search?q={seed_ids.account_id}&tenant_id={seed_ids.tenant_b}",
        tenant_id=seed_ids.tenant_b,
        expected=(200, 401, 403, 404),
    )
    assert seed_ids.account_id not in str(graph), "Foreign tenant graph query leaked account entity."
    assert seed_ids.document_id not in str(graph), "Foreign tenant graph query leaked document entity."


@pytest.mark.asyncio
async def test_cross_tenant_search_returns_no_foreign_evidence(backend, seed_ids):
    await backend.create_seed_graph()
    search, _ = await backend.request(
        "l4",
        "GET",
        f"/v1/search?q={seed_ids.evidence_id}&scope=all",
        tenant_id=seed_ids.tenant_b,
        expected=(200, 401, 403, 404),
    )
    assert seed_ids.evidence_id not in str(search), "Foreign tenant search returned evidence from tenant A."
    assert seed_ids.account_id not in str(search), "Foreign tenant search returned account from tenant A."


@pytest.mark.asyncio
async def test_agent_cannot_retrieve_cross_tenant_context(backend, seed_ids):
    await backend.create_seed_graph()
    body, response = await backend.request(
        "l4",
        "POST",
        "/v1/c1/stream",
        tenant_id=seed_ids.tenant_b,
        json={"message": "Retrieve context for the specified account", "context": {"account_id": seed_ids.account_id}},
        expected=(200, 401, 403, 404),
    )
    assert seed_ids.account_id not in str(body), "Agent response leaked foreign tenant account context."
    if response.status_code == 200:
        assert any(token in str(body).lower() for token in ("not found", "denied", "unauthorized", "insufficient")), body


@pytest.mark.asyncio
async def test_export_cannot_include_foreign_tenant_claims(backend, seed_ids):
    await backend.create_seed_graph()
    export, response = await backend.request(
        "l4",
        "GET",
        f"/v1/cases/{seed_ids.account_id}/export?include_claims=true&claim_tenant={seed_ids.tenant_b}",
        expected=(200, 401, 403, 404, 409),
    )
    assert seed_ids.tenant_b not in str(export), "Export included a foreign tenant identifier."
    assert seed_ids.evidence_id not in str(export) or response.status_code in {401, 403, 404, 409}, export


@pytest.mark.asyncio
async def test_audit_logs_do_not_leak_foreign_tenant_data(backend, seed_ids):
    await backend.create_seed_graph()
    audit, _ = await backend.request(
        "l4",
        "GET",
        f"/v1/audit/logs?entity_id={seed_ids.account_id}",
        tenant_id=seed_ids.tenant_b,
        expected=(200, 401, 403, 404),
    )
    assert seed_ids.account_id not in str(audit), "Foreign tenant audit query leaked tenant A entity id."
    assert seed_ids.document_id not in str(audit), "Foreign tenant audit query leaked tenant A document id."


@pytest.mark.asyncio
async def test_missing_tenant_context_fails_closed(backend, seed_ids):
    body, response = await backend.request(
        "l4",
        "POST",
        "/v1/accounts",
        tenant_id="",
        json={"id": "missing-tenant-account", "name": "Missing Tenant"},
        expected=(400, 401, 403, 422),
    )
    assert response.status_code in {400, 401, 403, 422}
    assert any(token in str(body).lower() for token in ("tenant", "unauthorized", "forbidden", "validation", "detail")), body


@pytest.mark.asyncio
async def test_tenant_deletion_blocks_follow_up_access_or_returns_retention_hold(backend, seed_ids):
    await backend.create_seed_graph()
    body, response = await backend.request(
        "l4",
        "DELETE",
        f"/v1/tenants/{seed_ids.tenant_a}",
        expected=(200, 202, 204, 409, 423),
    )

    if response.status_code in {200, 202, 204}:
        _, blocked = await backend.request(
            "l4",
            "GET",
            f"/v1/accounts/{seed_ids.account_id}",
            tenant_id=seed_ids.tenant_a,
            expected=(401, 403, 404),
        )
        assert blocked.status_code in {401, 403, 404}
        return

    tenant_state, _ = await backend.request(
        "l4",
        "GET",
        f"/v1/tenants/{seed_ids.tenant_a}",
        expected=(200,),
    )
    tenant_text = str(tenant_state).lower()
    assert str(seed_ids.tenant_a) in str(tenant_state), tenant_state
    assert any(token in tenant_text for token in ("active", "suspended", "pending", "retention", "hold", "status")), tenant_state
    assert response.status_code in {409, 423}
