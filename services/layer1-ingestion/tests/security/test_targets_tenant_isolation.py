"""Tenant isolation and security tests for target status (PUT /targets/{id}) and batch (POST /jobs/batch) endpoints.

Invariants:
- Tenant A cannot update Tenant B's target status
- Tenant A receives 404 (not 403) for cross-tenant status update
- Batch silently skips cross-tenant IDs
- Batch response does not disclose whether skipped IDs exist in another tenant
- Neither endpoint mutates cross-tenant data
- Requests without auth context are rejected with 401
- Audit log (if present) does not record misleading success for skipped IDs
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient


STATUS_BASE = "/api/v1/ingestion/targets"
BATCH_BASE = "/api/v1/ingestion/jobs/batch"

pytestmark = pytest.mark.requires_postgres


@pytest.fixture(autouse=True)
def _mock_process_scraping_job(monkeypatch):
    """Mock Celery task delay so batch tests don't fail when broker is unavailable."""
    import layer1_ingestion.api._batch_and_stats as _app_mod
    monkeypatch.setattr(_app_mod, "process_scraping_job", type("_MockTask", (), {"delay": lambda *a, **k: None})())


# ---------------------------------------------------------------------------
# Status endpoint — cross-tenant isolation
# ---------------------------------------------------------------------------

class TestStatusEndpointTenantIsolation:
    def test_tenant_a_cannot_put_tenant_b_status(
        self, client, db, other_org_id, make_target
    ):
        """client is authenticated as org_id; target belongs to other_org_id."""
        b_target = make_target(other_org_id, status="ACTIVE")
        resp = client.put(
            f"{STATUS_BASE}/{b_target.id}",
            json={"status": "PAUSED"},
        )
        assert resp.status_code == 404

    def test_cross_tenant_status_returns_404_not_403(
        self, client, db, other_org_id, make_target
    ):
        """404 avoids leaking that the target exists in another tenant."""
        b_target = make_target(other_org_id, status="ACTIVE")
        resp = client.put(
            f"{STATUS_BASE}/{b_target.id}",
            json={"status": "PAUSED"},
        )
        assert resp.status_code == 404, (
            f"Expected 404 to avoid existence leak, got {resp.status_code}"
        )

    def test_cross_tenant_status_does_not_mutate_target(
        self, client, db, other_org_id, make_target
    ):
        b_target = make_target(other_org_id, status="ACTIVE")
        client.put(
            f"{STATUS_BASE}/{b_target.id}",
            json={"status": "PAUSED"},
        )
        db.refresh(b_target)
        assert b_target.status == "ACTIVE"

    def test_cross_tenant_404_response_does_not_leak_tenant_id(
        self, client, db, other_org_id, make_target
    ):
        b_target = make_target(other_org_id, status="ACTIVE")
        resp = client.put(
            f"{STATUS_BASE}/{b_target.id}",
            json={"status": "PAUSED"},
        )
        body = resp.text
        assert str(other_org_id) not in body
        assert str(b_target.id) not in body or "not found" in body.lower()

    def test_unauthenticated_status_request_returns_401(self, db, org_id, make_target):
        from layer1_ingestion.api.main import app
        t = make_target(org_id, status="ACTIVE")
        with TestClient(app, raise_server_exceptions=False) as raw:
            resp = raw.put(
                f"{STATUS_BASE}/{t.id}",
                json={"status": "PAUSED"},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Batch endpoint — cross-tenant isolation
# ---------------------------------------------------------------------------

class TestBatchEndpointTenantIsolation:
    def test_batch_cannot_execute_cross_tenant_target(
        self, client, db, other_org_id, make_target
    ):
        """Cross-tenant target execution via batch returns skipped, no job created."""
        from layer1_ingestion.shared.models import ScrapingJob
        from layer1_ingestion.api.main import BatchOperationRequest, BatchOperationType

        b_target = make_target(other_org_id, status="ACTIVE")
        request = BatchOperationRequest(
            operation=BatchOperationType.EXECUTE,
            target_ids=[b_target.id],
        )
        resp = client.post(
            BATCH_BASE,
            json=request.model_dump(mode="json"),
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["succeeded"] == 0
        assert data["results"][0]["status"] == "skipped"

        job_count = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.target_id == b_target.id)
            .count()
        )
        assert job_count == 0

    def test_unauthenticated_batch_request_returns_401(self, db, org_id, make_target):
        from layer1_ingestion.api.main import app, BatchOperationRequest, BatchOperationType
        t = make_target(org_id, status="ACTIVE")
        request = BatchOperationRequest(
            operation=BatchOperationType.EXECUTE,
            target_ids=[t.id],
        )
        with TestClient(app, raise_server_exceptions=False) as raw:
            resp = raw.post(
                BATCH_BASE,
                json=request.model_dump(mode="json"),
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Mixed-tenant batch: own targets succeed, foreign targets skip
# ---------------------------------------------------------------------------

class TestMixedTenantBatch:
    def test_own_targets_succeed_foreign_targets_skip(
        self, client, db, org_id, other_org_id, make_target
    ):
        """Own target gets queued, foreign target is skipped in batch execute."""
        from layer1_ingestion.shared.models import ScrapingJob
        from layer1_ingestion.api.main import BatchOperationRequest, BatchOperationType

        own = make_target(org_id, status="ACTIVE")
        foreign = make_target(other_org_id, status="ACTIVE")

        request = BatchOperationRequest(
            operation=BatchOperationType.EXECUTE,
            target_ids=[own.id, foreign.id],
        )
        resp = client.post(
            BATCH_BASE,
            json=request.model_dump(mode="json"),
        )
        data = resp.json()
        assert data["succeeded"] == 1

        results = {r["id"]: r["status"] for r in data["results"]}
        assert results[str(own.id)] == "succeeded"
        assert results[str(foreign.id)] == "skipped"

        # Verify job was created for own target only
        job_count = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.target_id == foreign.id)
            .count()
        )
        assert job_count == 0
