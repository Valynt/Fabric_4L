"""API tests for POST /api/v1/ingestion/targets/batch.

Covers execute, pause, archive operations including:
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

BASE = "/api/v1/ingestion/targets/batch"


def _batch(client, operation: str, target_ids: list):
    return client.post(BASE, json={"operation": operation, "target_ids": [str(i) for i in target_ids]})


# ---------------------------------------------------------------------------
# Batch pause
# ---------------------------------------------------------------------------

class TestBatchPause:
    def test_pause_active_targets_returns_202(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "pause", [t.id])
        assert resp.status_code == 202

    def test_pause_changes_status_to_paused(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        _batch(client, "pause", [t.id])
        db.refresh(t)
        assert t.status == "PAUSED"

    def test_pause_multiple_targets(self, client, db, org_id, make_target):
        t1 = make_target(org_id, status="ACTIVE")
        t2 = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "pause", [t1.id, t2.id])
        assert resp.json()["succeeded"] == 2
        db.refresh(t1); db.refresh(t2)
        assert t1.status == "PAUSED"
        assert t2.status == "PAUSED"

    def test_pause_already_paused_is_skipped(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        resp = _batch(client, "pause", [t.id])
        data = resp.json()
        assert data["results"][0]["status"] == "skipped"

    def test_pause_archived_target_is_skipped(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ARCHIVED")
        resp = _batch(client, "pause", [t.id])
        assert resp.json()["results"][0]["status"] == "skipped"
        db.refresh(t)
        assert t.status == "ARCHIVED"

    def test_pause_cross_tenant_is_skipped(self, client, db, other_org_id, make_target):
        other = make_target(other_org_id, status="ACTIVE")
        resp = _batch(client, "pause", [other.id])
        assert resp.json()["results"][0]["status"] == "skipped"
        db.refresh(other)
        assert other.status == "ACTIVE"

    def test_pause_unknown_id_is_skipped(self, client, org_id):
        resp = _batch(client, "pause", [uuid4()])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_pause_partial_success_counts_accurate(self, client, db, org_id, other_org_id, make_target):
        good = make_target(org_id, status="ACTIVE")
        cross = make_target(other_org_id, status="ACTIVE")
        resp = _batch(client, "pause", [good.id, cross.id])
        data = resp.json()
        assert data["succeeded"] == 1
        assert data["requested"] == 2


# ---------------------------------------------------------------------------
# Batch archive
# ---------------------------------------------------------------------------

class TestBatchArchive:
    def test_archive_active_target(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "archive", [t.id])
        assert resp.status_code == 202
        assert resp.json()["succeeded"] == 1
        db.refresh(t)
        assert t.status == "ARCHIVED"

    def test_archive_paused_target(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        _batch(client, "archive", [t.id])
        db.refresh(t)
        assert t.status == "ARCHIVED"

    def test_archive_already_archived_is_skipped(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ARCHIVED")
        resp = _batch(client, "archive", [t.id])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_archive_cross_tenant_is_skipped(self, client, db, other_org_id, make_target):
        other = make_target(other_org_id, status="ACTIVE")
        resp = _batch(client, "archive", [other.id])
        assert resp.json()["results"][0]["status"] == "skipped"
        db.refresh(other)
        assert other.status == "ACTIVE"

    def test_archive_unknown_id_is_skipped(self, client, org_id):
        resp = _batch(client, "archive", [uuid4()])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_archived_target_cannot_be_reactivated_via_status_endpoint(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        _batch(client, "archive", [t.id])
        resp = client.patch(
            f"/api/v1/ingestion/targets/{t.id}/status",
            json={"status": "ACTIVE"},
        )
        assert resp.status_code == 422

    def test_archive_partial_success_counts(self, client, db, org_id, other_org_id, make_target):
        good = make_target(org_id, status="ACTIVE")
        cross = make_target(other_org_id, status="ACTIVE")
        resp = _batch(client, "archive", [good.id, cross.id])
        data = resp.json()
        assert data["succeeded"] == 1
        assert data["requested"] == 2


# ---------------------------------------------------------------------------
# Batch execute
# ---------------------------------------------------------------------------

class TestBatchExecute:
    def test_execute_active_target_returns_202(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "execute", [t.id])
        assert resp.status_code == 202

    def test_execute_returns_job_id_per_item(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "execute", [t.id])
        result = resp.json()["results"][0]
        assert result["status"] == "succeeded"
        assert result["job_id"] is not None

    def test_execute_succeeded_count_correct(self, client, db, org_id, make_target):
        t1 = make_target(org_id, status="ACTIVE")
        t2 = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "execute", [t1.id, t2.id])
        assert resp.json()["succeeded"] == 2

    def test_execute_archived_target_is_skipped(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ARCHIVED")
        resp = _batch(client, "execute", [t.id])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_execute_paused_target_is_skipped(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        resp = _batch(client, "execute", [t.id])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_execute_cross_tenant_is_skipped(self, client, db, other_org_id, make_target):
        other = make_target(other_org_id, status="ACTIVE")
        resp = _batch(client, "execute", [other.id])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_execute_unknown_id_is_skipped(self, client, org_id):
        resp = _batch(client, "execute", [uuid4()])
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_execute_duplicate_ids_do_not_double_execute(self, client, db, org_id, make_target):
        """Duplicate IDs are deduplicated before processing — exactly one job is created."""
        from layer1_ingestion.shared.models import ScrapingJob
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "execute", [t.id, t.id])
        data = resp.json()
        # Deduplication means only one entry in results and one job created
        assert data["requested"] == 1
        assert data["succeeded"] == 1
        assert len(data["results"]) == 1
        job_count = db.query(ScrapingJob).filter(ScrapingJob.target_id == t.id).count()
        assert job_count == 1

    def test_execute_mixed_valid_archived_unknown_cross_tenant(
        self, client, db, org_id, other_org_id, make_target
    ):
        active = make_target(org_id, status="ACTIVE")
        archived = make_target(org_id, status="ARCHIVED")
        cross = make_target(other_org_id, status="ACTIVE")
        unknown = uuid4()

        resp = _batch(client, "execute", [active.id, archived.id, cross.id, unknown])
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
        resp = _batch(client, "pause", [t.id])
        assert resp.json()["operation"] == "pause"

    def test_response_includes_requested_count(self, client, db, org_id, make_target):
        t1 = make_target(org_id, status="ACTIVE")
        t2 = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "pause", [t1.id, t2.id])
        assert resp.json()["requested"] == 2

    def test_response_includes_per_item_results(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "pause", [t.id])
        results = resp.json()["results"]
        assert len(results) == 1
        assert "id" in results[0]
        assert "status" in results[0]

    def test_skipped_item_does_not_reveal_cross_tenant_details(
        self, client, db, other_org_id, make_target
    ):
        other = make_target(other_org_id, status="ACTIVE", name="Secret Target")
        resp = _batch(client, "pause", [other.id])
        result = resp.json()["results"][0]
        # Must not expose the target name or tenant ID of the other tenant
        result_str = str(result)
        assert "Secret Target" not in result_str
        assert str(other_org_id) not in result_str


# ---------------------------------------------------------------------------
# Active-job guard
# ---------------------------------------------------------------------------

def _make_active_job(db, tenant_id, target_id, user_id, status="QUEUED"):
    """Insert a ScrapingJob in an in-progress state for the given target."""
    from layer1_ingestion.shared.models import create_scraping_job
    job = create_scraping_job(
        tenant_id=tenant_id,
        target_id=target_id,
        created_by=user_id,
        configuration={},
    )
    job.status = status
    db.add(job)
    db.flush()
    return job


class TestBatchActiveJobGuard:
    def test_batch_pause_skipped_when_job_is_queued(self, client, db, org_id, user_id, make_target):
        """Batch pause skips a target that has an in-progress job."""
        t = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, t.id, user_id, status="QUEUED")
        resp = _batch(client, "pause", [t.id])
        assert resp.status_code == 202
        result = resp.json()["results"][0]
        assert result["status"] == "skipped"
        assert "active job" in result["error"].lower()

    def test_batch_archive_skipped_when_job_is_extracting(self, client, db, org_id, user_id, make_target):
        """Batch archive skips a target that has an EXTRACTING job."""
        t = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, t.id, user_id, status="EXTRACTING")
        resp = _batch(client, "archive", [t.id])
        assert resp.status_code == 202
        result = resp.json()["results"][0]
        assert result["status"] == "skipped"

    def test_batch_pause_succeeds_when_no_active_jobs(self, client, db, org_id, make_target):
        """Batch pause proceeds normally when no in-progress jobs exist."""
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "pause", [t.id])
        assert resp.json()["results"][0]["status"] == "succeeded"

    def test_batch_execute_not_blocked_by_active_job_guard(self, client, db, org_id, make_target):
        """Execute operation is not subject to the active-job guard (it creates jobs)."""
        t = make_target(org_id, status="ACTIVE")
        resp = _batch(client, "execute", [t.id])
        assert resp.json()["results"][0]["status"] == "succeeded"

    def test_batch_mixed_active_job_and_clean_target(self, client, db, org_id, user_id, make_target):
        """In a mixed batch, blocked targets are skipped while clean ones succeed."""
        blocked = make_target(org_id, status="ACTIVE")
        clean = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, blocked.id, user_id, status="QUEUED")
        resp = _batch(client, "pause", [blocked.id, clean.id])
        data = resp.json()
        assert data["succeeded"] == 1
        statuses = {r["id"]: r["status"] for r in data["results"]}
        assert statuses[str(blocked.id)] == "skipped"
        assert statuses[str(clean.id)] == "succeeded"


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------

class TestBatchValidation:
    def test_empty_target_ids_returns_422(self, client, org_id):
        resp = _batch(client, "pause", [])
        assert resp.status_code == 422

    def test_unknown_operation_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = client.post(BASE, json={"operation": "teleport", "target_ids": [str(t.id)]})
        assert resp.status_code == 422

    def test_missing_operation_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = client.post(BASE, json={"target_ids": [str(t.id)]})
        assert resp.status_code == 422

    def test_missing_target_ids_returns_422(self, client, org_id):
        resp = client.post(BASE, json={"operation": "pause"})
        assert resp.status_code == 422
