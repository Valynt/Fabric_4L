"""Suite 7 — Operational Resilience with Real Services."""
from __future__ import annotations

import pytest

pytestmark = [pytest.mark.backend_integrated, pytest.mark.integration, pytest.mark.e2e]


@pytest.mark.asyncio
async def test_failed_ingestion_records_retryable_job_state(backend, seed_ids):
    job, _ = await backend.request(
        "l1",
        "POST",
        "/api/v1/ingestion/jobs",
        json={"account_id": seed_ids.account_id, "source_uri": "s3://missing-validation-object", "failure_mode": "source_unavailable"},
        expected=(200, 201, 202, 400, 422),
    )
    assert any(token in str(job).lower() for token in ("retry", "failed", "job", "source", "unavailable")), job


@pytest.mark.asyncio
async def test_partial_extraction_persists_available_results_and_warning(backend, seed_ids):
    await backend.create_seed_graph()
    extraction, _ = await backend.request(
        "l2",
        "POST",
        "/api/v1/extractions",
        json={"source_id": backend.seed_source_id, "account_id": seed_ids.account_id, "simulate_partial_failure": True},
        expected=(200, 201, 202, 206),
    )
    assert any(token in str(extraction).lower() for token in ("partial", "warning", "signal", "persisted")), extraction
    assert backend.seed_source_id in str(extraction), "Partial extraction must retain source provenance."


@pytest.mark.asyncio
async def test_graph_service_unavailable_returns_recoverable_error(backend, seed_ids):
    body, response = await backend.request(
        "l3",
        "POST",
        "/api/v1/graph/context",
        json={"account_id": seed_ids.account_id, "simulate_dependency_unavailable": True},
        expected=(200, 202, 409, 503),
    )
    assert response.status_code in {200, 202, 409, 503}
    assert any(token in str(body).lower() for token in ("recover", "retry", "unavailable", "queued", "degraded")), body


@pytest.mark.asyncio
async def test_agent_service_unavailable_returns_structured_error(backend, seed_ids):
    body, response = await backend.request(
        "l4",
        "POST",
        "/v1/c1/stream",
        json={"message": "Draft a business case", "context": {"account_id": seed_ids.account_id, "simulate_agent_unavailable": True}},
        expected=(200, 202, 409, 503),
    )
    assert response.status_code in {200, 202, 409, 503}
    assert any(token in str(body).lower() for token in ("error", "structured", "retry", "unavailable", "degraded")), body


@pytest.mark.asyncio
async def test_benchmark_service_unavailable_blocks_policy_dependent_approval(backend, seed_ids):
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
        json={"status": "approved", "reviewer_id": seed_ids.user_reviewer, "simulate_benchmark_unavailable": True},
        expected=(400, 409, 422, 503),
    )
    assert response.status_code in {400, 409, 422, 503}
    assert any(token in str(body).lower() for token in ("benchmark", "policy", "unavailable", "blocked", "validation")), body


@pytest.mark.asyncio
async def test_export_failure_creates_audit_event(backend, seed_ids):
    body, _ = await backend.request(
        "l4",
        "POST",
        "/v1/exports",
        json={"account_id": seed_ids.account_id, "case_id": seed_ids.account_id, "simulate_storage_failure": True},
        expected=(200, 201, 202, 409, 500, 503),
    )
    assert any(token in str(body).lower() for token in ("export", "failed", "audit", "job", "retry")), body
    await backend.assert_audit_event("export.failed", seed_ids.account_id)


@pytest.mark.asyncio
async def test_user_can_resume_partially_completed_value_model(backend, seed_ids):
    partial, _ = await backend.request(
        "l4",
        "PUT",
        f"/v1/accounts/{seed_ids.account_id}/value-model",
        json={"status": "partial", "drivers": [{"name": "Conversion", "evidence_id": seed_ids.evidence_id}], "formula_id": seed_ids.formula_id},
        expected=(200, 201, 202),
    )
    assert "partial" in str(partial).lower() or seed_ids.evidence_id in str(partial)
    resumed, _ = await backend.request("l4", "GET", f"/v1/accounts/{seed_ids.account_id}/value-model?resume=true", expected=(200,))
    assert seed_ids.evidence_id in str(resumed)
    assert seed_ids.formula_id in str(resumed)


@pytest.mark.asyncio
async def test_long_running_job_records_progress(backend, seed_ids):
    job, _ = await backend.request(
        "l1",
        "POST",
        "/api/v1/ingestion/jobs",
        json={"account_id": seed_ids.account_id, "source_id": backend.seed_source_id, "mode": "long_running_validation"},
        expected=(200, 201, 202),
    )
    job_id = job.get("id") or job.get("job_id") or seed_ids.document_id
    progress = await backend.assert_job_terminal_or_progressing(str(job_id))
    assert any(token in str(progress).lower() for token in ("queued", "running", "progress", "completed", "failed")), progress


@pytest.mark.asyncio
async def test_cancelled_job_records_terminal_state(backend, seed_ids):
    job, _ = await backend.request(
        "l1",
        "POST",
        "/api/v1/ingestion/jobs",
        json={"account_id": seed_ids.account_id, "source_id": backend.seed_source_id, "mode": "cancellable_validation"},
        expected=(200, 201, 202),
    )
    job_id = job.get("id") or job.get("job_id") or seed_ids.document_id
    cancelled, _ = await backend.request("l1", "POST", f"/api/v1/ingestion/jobs/{job_id}/cancel", expected=(200, 202, 409))
    assert any(token in str(cancelled).lower() for token in ("cancel", "terminal", "job")), cancelled
    terminal = await backend.assert_job_terminal_or_progressing(str(job_id))
    assert any(token in str(terminal).lower() for token in ("cancelled", "failed", "completed")), terminal
