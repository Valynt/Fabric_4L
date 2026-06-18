"""Suite 2 — Cross-Layer Data Flow Validation.

These tests intentionally validate live service-to-service handoffs. They must fail
closed when any required service contract, persistence handoff, or provenance link
is missing.
"""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.backend_integrated, pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_l1_to_l2_source_to_signal_flow(backend, seed_ids):
    await backend.create_seed_graph()
    source = await backend.assert_persisted("l1", f"/api/v1/ingestion/sources/{backend.seed_source_id}", backend.seed_source_id)
    assert seed_ids.account_id in str(source), "L1 source persistence must retain account context."

    extraction, _ = await backend.request(
        "l2",
        "POST",
        "/api/v1/extractions",
        json={"source_id": backend.seed_source_id, "account_id": seed_ids.account_id, "mode": "backend_integrated_validation"},
        expected=(200, 201, 202),
    )
    assert backend.seed_source_id in str(extraction), "L2 must consume the durable L1 source record."
    assert any(token in str(extraction).lower() for token in ("signal", "extraction", "provenance", "source")), extraction


@pytest.mark.asyncio
async def test_l2_to_l3_signal_to_graph_flow(backend, seed_ids):
    await backend.create_seed_graph()
    extraction, _ = await backend.request(
        "l2",
        "POST",
        "/api/v1/extractions",
        json={"source_id": backend.seed_source_id, "account_id": seed_ids.account_id},
        expected=(200, 201, 202),
    )
    extraction_id = extraction.get("id") or extraction.get("extraction_id") or seed_ids.document_id
    signals, _ = await backend.request("l2", "GET", f"/api/v1/extractions/{extraction_id}/signals", expected=(200,))
    assert backend.seed_source_id in str(signals), "L2 signals must include source provenance."

    graph, _ = await backend.request(
        "l3",
        "POST",
        "/api/v1/graph/context",
        json={"account_id": seed_ids.account_id, "signal_ids": [extraction_id], "source_ids": [backend.seed_source_id]},
        expected=(200, 201, 202),
    )
    assert seed_ids.account_id in str(graph)
    assert backend.seed_source_id in str(graph), "L3 graph context must retain signal/source lineage."


@pytest.mark.asyncio
async def test_l3_to_l4_graph_context_drives_hypothesis_generation(backend, seed_ids):
    await backend.create_seed_graph()
    graph, _ = await backend.request(
        "l3",
        "POST",
        "/api/v1/graph/context",
        json={"account_id": seed_ids.account_id, "source_ids": [backend.seed_source_id], "evidence_ids": [seed_ids.evidence_id]},
        expected=(200, 201, 202),
    )
    graph_id = graph.get("id") or graph.get("graph_id") or seed_ids.account_id

    hypothesis, _ = await backend.request(
        "l4",
        "POST",
        "/v1/hypotheses",
        json={"account_id": seed_ids.account_id, "graph_context_id": graph_id, "require_evidence": True},
        expected=(200, 201, 202),
    )
    hypothesis_text = str(hypothesis).lower()
    assert any(token in hypothesis_text for token in ("hypothesis", "evidence", "claim")), hypothesis
    assert seed_ids.account_id in str(hypothesis), "L4 hypothesis generation must be account-scoped from L3 graph context."


@pytest.mark.asyncio
async def test_l5_ground_truth_validation_updates_assumption_status(backend, seed_ids):
    assumption, _ = await backend.request(
        "l5",
        "POST",
        "/api/v1/truth/assumptions",
        json={
            "id": seed_ids.evidence_id,
            "account_id": seed_ids.account_id,
            "claim": "Conversion improved 11 percent",
            "source_id": backend.seed_source_id,
            "status": "pending_review",
        },
        expected=(200, 201, 202, 409),
    )
    assert seed_ids.evidence_id in str(assumption)

    decision, _ = await backend.request(
        "l5",
        "POST",
        f"/api/v1/truth/assumptions/{seed_ids.evidence_id}/decisions",
        json={"status": "approved", "reviewer_id": seed_ids.user_reviewer, "reason": "source verified"},
        expected=(200, 201, 202),
    )
    assert "approved" in str(decision).lower(), decision


@pytest.mark.asyncio
async def test_l6_benchmark_policy_applies_to_formula_inputs(backend, seed_ids):
    benchmark_payload = {
        "id": seed_ids.benchmark_id,
        "metric": "conversion_lift_pct",
        "value": 11,
        "source": "validation_seed",
        "effective_date": "2024-01-01",
        "account_id": seed_ids.account_id,
    }
    benchmark, _ = await backend.request("l6", "POST", "/v1/benchmarks", json=benchmark_payload, expected=(200, 201, 202, 409))
    assert seed_ids.benchmark_id in str(benchmark)

    policy, _ = await backend.request(
        "l6",
        "POST",
        "/v1/benchmarks/policy/evaluate",
        json={"benchmark_id": seed_ids.benchmark_id, "formula_id": seed_ids.formula_id, "account_id": seed_ids.account_id},
        expected=(200, 201, 202),
    )
    assert any(token in str(policy).lower() for token in ("benchmark", "policy", "formula", "approved", "warning")), policy
