"""Tests for target status transitions (PUT /targets/{id})."""

from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from layer1_ingestion.shared.models import ScrapingTarget, SourceCategory, TargetType

pytestmark = [pytest.mark.integration, pytest.mark.postgres]


@pytest.fixture(autouse=True)
def _clear_dependency_overrides():
    """Ensure no dependency override leaks out of integration tests."""
    yield
    from layer1_ingestion.api.main import app

    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def _mock_process_scraping_job(monkeypatch):
    """Mock Celery task delay so batch tests don't fail when broker is unavailable."""
    import layer1_ingestion.api._batch_and_stats as _app_mod
    monkeypatch.setattr(_app_mod, "process_scraping_job", type("_MockTask", (), {"delay": lambda *a, **k: None})())


@pytest.fixture
def org_id():
    return uuid4()


@pytest.fixture
def other_org_id():
    return uuid4()


@pytest.fixture
def user_id():
    return uuid4()


def _make_target(db: Session, tenant_id: UUID, user_id: UUID, status: str = "ACTIVE") -> ScrapingTarget:
    from layer1_ingestion.shared.models import create_scraping_target
    t = create_scraping_target(
        tenant_id=tenant_id,
        name="Test Target",
        url="https://example.com",
        target_type=TargetType.SINGLE_PAGE,
        created_by=user_id,
        source_category=SourceCategory.GENERAL,
        extraction_config={"method": "llm"},
    )
    t.status = status
    db.add(t)
    db.flush()
    db.refresh(t)
    return t


# ── PATCH /targets/{id}/status ────────────────────────────────────────────────

class TestUpdateTargetStatus:
    def test_active_to_paused(self, client, db, org_id, user_id):
        target = _make_target(db, org_id, user_id, "ACTIVE")
        resp = client.put(
            f"/api/v1/ingestion/targets/{target.id}",
            json={"status": "PAUSED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "PAUSED"
        db.refresh(target)
        assert target.status == "PAUSED"

    def test_paused_to_active(self, client, db, org_id, user_id):
        target = _make_target(db, org_id, user_id, "PAUSED")
        resp = client.put(
            f"/api/v1/ingestion/targets/{target.id}",
            json={"status": "ACTIVE"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"
        db.refresh(target)
        assert target.status == "ACTIVE"

    def test_active_to_archived(self, client, db, org_id, user_id):
        target = _make_target(db, org_id, user_id, "ACTIVE")
        resp = client.put(
            f"/api/v1/ingestion/targets/{target.id}",
            json={"status": "ARCHIVED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"
        db.refresh(target)
        assert target.status == "ARCHIVED"

    def test_archived_can_be_reactivated(self, client, db, org_id, user_id):
        # The app does not enforce terminal state restrictions on targets
        target = _make_target(db, org_id, user_id, "ARCHIVED")
        resp = client.put(
            f"/api/v1/ingestion/targets/{target.id}",
            json={"status": "ACTIVE"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"
        db.refresh(target)
        assert target.status == "ACTIVE"

    def test_invalid_status_value_rejected(self, client, db, org_id, user_id):
        target = _make_target(db, org_id, user_id, "ACTIVE")
        resp = client.put(
            f"/api/v1/ingestion/targets/{target.id}",
            json={"status": "INVALID_STATUS"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 422

    def test_cross_tenant_returns_404(self, db, org_id, other_org_id, user_id):
        from fastapi.testclient import TestClient

        from layer1_ingestion.api.main import app
        from layer1_ingestion.shared.database import get_db_from_context_sync
        from tests.conftest import _InjectGovernanceMiddleware

        target = _make_target(db, org_id, user_id, "ACTIVE")

        # Create a client authenticated as other_org_id
        app.dependency_overrides[get_db_from_context_sync] = lambda: db
        wrapped = _InjectGovernanceMiddleware(app, tenant_id=other_org_id, user_id=user_id)
        with TestClient(wrapped) as other_client:
            resp = other_client.put(
                f"/api/v1/ingestion/targets/{target.id}",
                json={"status": "PAUSED"},
                headers={"X-Organization-ID": str(other_org_id)},
            )
            assert resp.status_code == 404
        app.dependency_overrides.clear()

    def test_nonexistent_target_returns_404(self, client, org_id):
        resp = client.put(
            f"/api/v1/ingestion/targets/{uuid4()}",
            json={"status": "PAUSED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 404


# ── POST /targets/batch ───────────────────────────────────────────────────────

class TestBatchTargetOperation:
    def test_batch_pause_via_put(self, client, db, org_id, user_id):
        t1 = _make_target(db, org_id, user_id, "ACTIVE")
        t2 = _make_target(db, org_id, user_id, "ACTIVE")
        for t in (t1, t2):
            resp = client.put(
                f"/api/v1/ingestion/targets/{t.id}",
                json={"status": "PAUSED"},
                headers={"X-Organization-ID": str(org_id)},
            )
            assert resp.status_code == 200
        db.refresh(t1)
        db.refresh(t2)
        assert t1.status == "PAUSED"
        assert t2.status == "PAUSED"

    def test_batch_archive_via_put(self, client, db, org_id, user_id):
        t = _make_target(db, org_id, user_id, "ACTIVE")
        resp = client.put(
            f"/api/v1/ingestion/targets/{t.id}",
            json={"status": "ARCHIVED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        db.refresh(t)
        assert t.status == "ARCHIVED"

    def test_cross_tenant_put_returns_404(self, client, db, org_id, other_org_id, user_id):
        """Cross-tenant target updates return 404 (fail closed)."""
        other_target = _make_target(db, other_org_id, user_id, "ACTIVE")
        resp = client.put(
            f"/api/v1/ingestion/targets/{other_target.id}",
            json={"status": "PAUSED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 404
        db.refresh(other_target)
        assert other_target.status == "ACTIVE"

    def test_put_on_archived_target_succeeds(self, client, db, org_id, user_id):
        t = _make_target(db, org_id, user_id, "ARCHIVED")
        resp = client.put(
            f"/api/v1/ingestion/targets/{t.id}",
            json={"status": "PAUSED"},
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 200
        db.refresh(t)
        assert t.status == "PAUSED"

    def test_batch_execute_queues_jobs(self, client, db, org_id, user_id):
        from layer1_ingestion.api.main import BatchOperationRequest, BatchOperationType
        t = _make_target(db, org_id, user_id, "ACTIVE")
        request = BatchOperationRequest(
            operation=BatchOperationType.EXECUTE,
            target_ids=[t.id],
        )
        resp = client.post(
            "/api/v1/ingestion/jobs/batch",
            json=request.model_dump(mode="json"),
            headers={"X-Organization-ID": str(org_id), "X-User-ID": str(user_id)},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["succeeded"] == 1
        assert data["results"][0]["job_id"] is not None

    def test_batch_empty_target_ids_rejected(self, client, org_id):
        from layer1_ingestion.api.main import BatchOperationRequest, BatchOperationType
        request = BatchOperationRequest(
            operation=BatchOperationType.EXECUTE,
            target_ids=[],
        )
        resp = client.post(
            "/api/v1/ingestion/jobs/batch",
            json=request.model_dump(mode="json"),
            headers={"X-Organization-ID": str(org_id)},
        )
        assert resp.status_code == 422
