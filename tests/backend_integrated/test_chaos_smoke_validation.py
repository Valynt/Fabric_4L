"""Backend integrated chaos smoke scenarios for cross-layer critical paths."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.backend_integrated, pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_chaos_redis_outage_degrades_l1_job_submission(backend, seed_ids):
    body, response = await backend.request(
        "l1",
        "POST",
        "/api/v1/ingestion/jobs",
        json={
            "account_id": seed_ids.account_id,
            "source_uri": "s3://chaos/redis-outage",
            "simulate_redis_unavailable": True,
        },
        expected=(200, 202, 409, 503),
    )
    assert response.status_code in {200, 202, 409, 503}
    assert any(token in str(body).lower() for token in ("redis", "retry", "queued", "degraded", "unavailable")), body


@pytest.mark.asyncio
async def test_chaos_database_latency_spike_surfaces_degraded_mode(backend, seed_ids):
    body, response = await backend.request(
        "l2",
        "POST",
        "/api/v1/extractions",
        json={
            "source_id": seed_ids.document_id,
            "account_id": seed_ids.account_id,
            "simulate_db_latency_ms": 3000,
        },
        expected=(200, 202, 206, 408, 504),
    )
    assert response.status_code in {200, 202, 206, 408, 504}
    assert any(token in str(body).lower() for token in ("latency", "timeout", "degraded", "partial", "retry")), body


@pytest.mark.asyncio
async def test_chaos_downstream_l3_timeout_blocks_l4_policy_path(backend, seed_ids):
    case, _ = await backend.request(
        "l4",
        "POST",
        "/v1/cases",
        json={"account_id": seed_ids.account_id, "requires_benchmark_policy": True, "approval_status": "submitted"},
        expected=(200, 201, 202),
    )
    case_id = case.get("id") or case.get("case_id") or seed_ids.account_id
    body, response = await backend.request(
        "l4",
        "POST",
        f"/v1/cases/{case_id}/approval",
        json={
            "status": "approved",
            "reviewer_id": seed_ids.user_reviewer,
            "simulate_downstream_layer_timeout": True,
        },
        expected=(400, 409, 422, 503, 504),
    )
    assert response.status_code in {400, 409, 422, 503, 504}
    assert any(token in str(body).lower() for token in ("timeout", "downstream", "benchmark", "policy", "blocked")), body
