"""API tests for POST /api/v1/ingestion/jobs/batch.

Covers execute operation including:
- Happy-path per-operation behaviour
- Per-item result shape (succeeded/failed/skipped counts)
- Cross-tenant IDs silently skipped
- Unknown IDs silently skipped
- Archived targets not mutated
- Duplicate IDs handled without double-execution
- Empty list rejected with 422
- Mixed valid/invalid/cross-tenant IDs produce correct per-item results
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from sqlalchemy.orm import Session

from layer1_ingestion.api.app_monolith import BatchOperationRequest, BatchOperationType

BASE = "/api/v1/ingestion/jobs/batch"


@pytest.fixture(autouse=True)
def _mock_process_scraping_job(monkeypatch):
    """Mock Celery task delay so batch tests don't fail when broker is unavailable."""
    import layer1_ingestion.api.app_monolith as _app_mod
    monkeypatch.setattr(_app_mod, "process_scraping_job", type("_MockTask", (), {"delay": lambda *a, **k: None})())


def _batch(client, operation: BatchOperationType, target_ids: list):
    request = BatchOperationRequest(
        operation=operation,
        target_ids=[str(i) for i in target_ids],
    )
    return client.post(BASE, json=request.model_dump(mode="json"))


# ---------------------------------------------------------------------------
# Batch execute
# ---------------------------------------------------------------------------

class TestBatchExecute:
    def test_execute_active_target_returns_202(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, BatchOperationType.EXECUTE, [t.id])
        assert resp.status_code == 202

    def test_execute_returns_job_id_per_item(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, BatchOperationType.EXECUTE, [t.id])
        result = resp.json()["results"][0]
        assert result["status"] == "succeeded"
        assert result["job_id"] is not None

    def test_execute_succeeded_count_correct(self, client, db, org_id, make_target):
        t1 = make_target(org_id, status="ACTIVE")
        t2 = make_target(org_id, status="ACTIVE")
        resp = _batch(client, BatchOperationType.EXECUTE, [t1.id, t2.id])
        assert resp.json()["succeeded"] == 2

    def test_execute_archived_target_is_skipped(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ARCHIVED")
        resp = _batch(client, BatchOperationType.EXECUTE, [t.id])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_execute_paused_target_is_skipped(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        resp = _batch(client, BatchOperationType.EXECUTE, [t.id])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_execute_cross_tenant_is_skipped(self, client, db, other_org_id, make_target):
        other = make_target(other_org_id, status="ACTIVE")
        resp = _batch(client, BatchOperationType.EXECUTE, [other.id])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_execute_unknown_id_is_skipped(self, client, org_id):
        resp = _batch(client, BatchOperationType.EXECUTE, [uuid4()])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_execute_duplicate_ids_create_multiple_jobs(self, client, db, org_id, make_target):
        """Duplicate IDs in batch are processed independently — multiple jobs created."""
        from layer1_ingestion.shared.models import ScrapingJob
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, BatchOperationType.EXECUTE, [t.id, t.id])
        data = resp.json()
        assert data["requested"] == 2
        assert data["succeeded"] == 2
        assert len(data["results"]) == 2
        job_count = db.query(ScrapingJob).filter(ScrapingJob.target_id == t.id).count()
        assert job_count == 2

    def test_execute_mixed_valid_archived_unknown_cross_tenant(
        self, client, db, org_id, other_org_id, make_target
    ):
        active = make_target(org_id, status="ACTIVE")
        archived = make_target(org_id, status="ARCHIVED")
        cross = make_target(other_org_id, status="ACTIVE")
        unknown = uuid4()

        resp = _batch(client, BatchOperationType.EXECUTE, [active.id, archived.id, cross.id, unknown])
        data = resp.json()
        assert data["requested"] == 4
        assert data["succeeded"] == 1

        statuses = {r["id"]: r["status"] for r in data["results"]}
        assert statuses[str(active.id)] == "succeeded"
        assert statuses[str(archived.id)] == "skipped"
        assert statuses[str(cross.id)] == "skipped"
        assert statuses[str(unknown)] == "skipped"


# ---------------------------------------------------------------------------
# Response shape
# ---------------------------------------------------------------------------

class TestResponseShape:
    def test_response_includes_operation_field(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, BatchOperationType.EXECUTE, [t.id])
        assert resp.json()["operation"] == "execute"

    def test_response_includes_requested_count(self, client, db, org_id, make_target):
        t1 = make_target(org_id, status="ACTIVE")
        t2 = make_target(org_id, status="ACTIVE")
        resp = _batch(client, BatchOperationType.EXECUTE, [t1.id, t2.id])
        assert resp.json()["requested"] == 2

    def test_response_includes_per_item_results(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, BatchOperationType.EXECUTE, [t.id])
        results = resp.json()["results"]
        assert len(results) == 1
        assert "id" in results[0]
        assert "status" in results[0]

    def test_skipped_item_does_not_reveal_cross_tenant_details(
        self, client, db, other_org_id, make_target
    ):
        other = make_target(other_org_id, status="ACTIVE", name="Secret Target")
        resp = _batch(client, BatchOperationType.EXECUTE, [other.id])
        result = resp.json()["results"][0]
        # Must not expose the target name or tenant ID of the other tenant
        result_str = str(result)
        assert "Secret Target" not in result_str
        assert str(other_org_id) not in result_str


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestBatchValidation:
    def test_empty_target_ids_returns_422(self, client, org_id):
        resp = _batch(client, BatchOperationType.EXECUTE, [])
        assert resp.status_code == 422

    def test_unknown_operation_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        # Send raw JSON with invalid enum to bypass Pydantic client-side validation
        resp = client.post(BASE, json={"operation": "teleport", "target_ids": [str(t.id)]})
        assert resp.status_code == 422

    def test_missing_operation_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = client.post(BASE, json={"target_ids": [str(t.id)]})
        assert resp.status_code == 422

    def test_missing_target_ids_returns_422(self, client, org_id):
        resp = client.post(BASE, json={"operation": "execute"})
        assert resp.status_code == 422
