"""Tests for PATCH /targets/{id}/status and POST /targets/batch endpoints."""

import pytest
from uuid import uuid4, UUID
from sqlalchemy.orm import Session

from layer1_ingestion.shared.models import TargetStatus, ScrapingTarget


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def other_org_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


def _make_target(db: Session, tenant_id: UUID, status: str = "ACTIVE") -> ScrapingTarget:
    from layer1_ingestion.shared.models import create_scraping_target
    t = create_scraping_target(
        tenant_id=tenant_id,
        name="Test Target",
        url="https://example.com",
        source_category="general",
        extraction_config={"method": "llm"},
    )
    t.status = status
    db.add(t)
    db.flush()
    db.refresh(t)
    return t


# ── PATCH /targets/{id}/status ────────────────────────────────────────────────

class TestUpdateTargetStatus:
    def test_active_to_paused(self, client, db, org_id):
        target = _make_target(db, org_id, "ACTIVE")
        resp = client.patch(
            f"/api/v1/ingestion/targets/{target.id}/status",
            json={"status": "PAUSED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PAUSED"
        db.refresh(target)
        assert target.status == "PAUSED"

    def test_paused_to_active(self, client, db, org_id):
        target = _make_target(db, org_id, "PAUSED")
        resp = client.patch(
            f"/api/v1/ingestion/targets/{target.id}/status",
            json={"status": "ACTIVE"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"

    def test_active_to_archived(self, client, db, org_id):
        target = _make_target(db, org_id, "ACTIVE")
        resp = client.patch(
            f"/api/v1/ingestion/targets/{target.id}/status",
            json={"status": "ARCHIVED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"

    def test_archived_is_terminal(self, client, db, org_id):
        target = _make_target(db, org_id, "ARCHIVED")
        resp = client.patch(
            f"/api/v1/ingestion/targets/{target.id}/status",
            json={"status": "ACTIVE"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 422
        assert "terminal" in resp.json()["detail"].lower()

    def test_invalid_transition_rejected(self, client, db, org_id):
        # PAUSED → ARCHIVED is valid, but ACTIVE → ACTIVE is not a real transition
        # Test an actually invalid one: there's no invalid transition in the enum
        # so test that a bad status value is rejected
        target = _make_target(db, org_id, "ACTIVE")
        resp = client.patch(
            f"/api/v1/ingestion/targets/{target.id}/status",
            json={"status": "INVALID_STATUS"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 422

    def test_cross_tenant_returns_404(self, client, db, org_id, other_org_id):
        target = _make_target(db, org_id, "ACTIVE")
        resp = client.patch(
            f"/api/v1/ingestion/targets/{target.id}/status",
            json={"status": "PAUSED"},
            headers={"X-Organization-ID": str(other_org_id)},
        )
        assert resp.status_code == 404

    def test_nonexistent_target_returns_404(self, client, org_id):
        resp = client.patch(
            f"/api/v1/ingestion/targets/{uuid4()}/status",
            json={"status": "PAUSED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 404


# ── POST /targets/batch ───────────────────────────────────────────────────────

class TestBatchTargetOperation:
    def test_batch_pause(self, client, db, org_id):
        t1 = _make_target(db, org_id, "ACTIVE")
        t2 = _make_target(db, org_id, "ACTIVE")
        resp = client.post(
            "/api/v1/ingestion/targets/batch",
            json={"operation": "pause", "target_ids": [str(t1.id), str(t2.id)]},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["succeeded"] == 2
        assert data["failed"] == 0
        db.refresh(t1)
        db.refresh(t2)
        assert t1.status == "PAUSED"
        assert t2.status == "PAUSED"

    def test_batch_archive(self, client, db, org_id):
        t = _make_target(db, org_id, "ACTIVE")
        resp = client.post(
            "/api/v1/ingestion/targets/batch",
            json={"operation": "archive", "target_ids": [str(t.id)]},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 202
        assert resp.json()["succeeded"] == 1
        db.refresh(t)
        assert t.status == "ARCHIVED"

    def test_cross_tenant_ids_silently_skipped(self, client, db, org_id, other_org_id):
        """IDs belonging to another tenant are skipped, not errored."""
        other_target = _make_target(db, other_org_id, "ACTIVE")
        resp = client.post(
            "/api/v1/ingestion/targets/batch",
            json={"operation": "pause", "target_ids": [str(other_target.id)]},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["succeeded"] == 0
        # skipped, not failed
        assert data["results"][0]["status"] == "skipped"
        # Target not modified
        db.refresh(other_target)
        assert other_target.status == "ACTIVE"

    def test_batch_skips_already_archived(self, client, db, org_id):
        t = _make_target(db, org_id, "ARCHIVED")
        resp = client.post(
            "/api/v1/ingestion/targets/batch",
            json={"operation": "pause", "target_ids": [str(t.id)]},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["results"][0]["status"] == "skipped"

    def test_batch_execute_queues_jobs(self, client, db, org_id, user_id):
        t = _make_target(db, org_id, "ACTIVE")
        resp = client.post(
            "/api/v1/ingestion/targets/batch",
            json={"operation": "execute", "target_ids": [str(t.id)]},
            headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["succeeded"] == 1
        assert data["results"][0]["job_id"] is not None

    def test_batch_empty_list_rejected(self, client, org_id):
        resp = client.post(
            "/api/v1/ingestion/targets/batch",
            json={"operation": "pause", "target_ids": []},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 422
