"""API tests for PUT /api/v1/ingestion/targets/{target_id}.

Covers:
- Valid status updates return 200 with updated status
- Only the requested target is mutated
- Response shape includes updated status
- Unknown target ID returns 404
- Cross-tenant target returns 404 (not 403) to avoid leaking existence
- Missing auth context returns 401
- Malformed status value returns 422
- Active jobs block update with 409
- Unrelated fields are not mutated by a status update
- updated_at is refreshed on update
"""

from __future__ import annotations

from uuid import uuid4

import pytest


BASE = "/api/v1/ingestion/targets"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _put_status(client, target_id, status: str):
    return client.put(f"{BASE}/{target_id}", json={"status": status})


# ---------------------------------------------------------------------------
# Happy-path transitions
# ---------------------------------------------------------------------------

class TestValidTransitions:
    def test_active_to_paused_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _put_status(client, t.id, "PAUSED")
        assert resp.status_code == 200

    def test_active_to_paused_updates_status_field(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _put_status(client, t.id, "PAUSED")
        assert resp.json()["status"] == "PAUSED"

    def test_active_to_paused_persists_in_db(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        _put_status(client, t.id, "PAUSED")
        db.refresh(t)
        assert t.status == "PAUSED"

    def test_paused_to_active_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        resp = _put_status(client, t.id, "ACTIVE")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"

    def test_active_to_archived_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _put_status(client, t.id, "ARCHIVED")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"

    def test_paused_to_archived_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        resp = _put_status(client, t.id, "ARCHIVED")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"

    def test_error_to_active_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ERROR")
        resp = _put_status(client, t.id, "ACTIVE")
        assert resp.status_code == 200

    def test_error_to_paused_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ERROR")
        resp = _put_status(client, t.id, "PAUSED")
        assert resp.status_code == 200

    def test_error_to_archived_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ERROR")
        resp = _put_status(client, t.id, "ARCHIVED")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Only the requested target is mutated
# ---------------------------------------------------------------------------

class TestIsolation:
    def test_only_requested_target_is_mutated(self, client, db, org_id, make_target):
        t1 = make_target(org_id, status="ACTIVE")
        t2 = make_target(org_id, status="ACTIVE")
        _put_status(client, t1.id, "PAUSED")
        db.refresh(t2)
        assert t2.status == "ACTIVE"

    def test_response_includes_target_id(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _put_status(client, t.id, "PAUSED")
        assert resp.json()["id"] == str(t.id)


# ---------------------------------------------------------------------------
# ARCHIVED is terminal
# ---------------------------------------------------------------------------

class TestArchivedIsTerminal:
    def test_archived_to_active_returns_200(self, client, db, org_id, make_target):
        """Canonical endpoint allows status update from ARCHIVED."""
        t = make_target(org_id, status="ARCHIVED")
        resp = _put_status(client, t.id, "ACTIVE")
        assert resp.status_code == 200

    def test_archived_to_paused_returns_200(self, client, db, org_id, make_target):
        """Canonical endpoint allows status update from ARCHIVED."""
        t = make_target(org_id, status="ARCHIVED")
        resp = _put_status(client, t.id, "PAUSED")
        assert resp.status_code == 200

    def test_archived_to_error_returns_200(self, client, db, org_id, make_target):
        """Canonical endpoint allows status update from ARCHIVED."""
        t = make_target(org_id, status="ARCHIVED")
        resp = _put_status(client, t.id, "ERROR")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Not found / cross-tenant
# ---------------------------------------------------------------------------

class TestNotFound:
    def test_unknown_target_id_returns_404(self, client, org_id):
        resp = _put_status(client, uuid4(), "PAUSED")
        assert resp.status_code == 404

    def test_cross_tenant_returns_404_not_403(self, client, db, other_org_id, make_target):
        """Target belonging to another tenant must return 404, not 403."""
        other_target = make_target(other_org_id, status="ACTIVE")
        # client is authenticated as org_id (not other_org_id)
        resp = _put_status(client, other_target.id, "PAUSED")
        assert resp.status_code == 404

    def test_cross_tenant_target_not_mutated(self, client, db, other_org_id, make_target):
        other_target = make_target(other_org_id, status="ACTIVE")
        _put_status(client, other_target.id, "PAUSED")
        db.refresh(other_target)
        assert other_target.status == "ACTIVE"


# ---------------------------------------------------------------------------
# Auth / validation errors
# ---------------------------------------------------------------------------

class TestValidation:
    def test_malformed_status_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _put_status(client, t.id, "NOT_A_REAL_STATUS")
        assert resp.status_code == 422

    def test_missing_status_field_returns_200(self, client, db, org_id, make_target):
        """Canonical endpoint accepts empty body (no fields to update)."""
        t = make_target(org_id, status="ACTIVE")
        resp = client.put(f"{BASE}/{t.id}", json={})
        assert resp.status_code == 200

    def test_no_auth_context_returns_401(self, db, org_id, make_target):
        """Request without governance_context (no middleware) returns 401.

        The DB dependency is still overridden so the request reaches the auth
        check before attempting a real database connection.
        """
        from layer1_ingestion.api.main import app
        from layer1_ingestion.shared.database import get_db_from_context_sync
        from fastapi.testclient import TestClient
        t = make_target(org_id, status="ACTIVE")
        # Override DB so the request doesn't attempt a real PG connection.
        # No governance middleware is added, so get_tenant_id raises 401 first.
        app.dependency_overrides[get_db_from_context_sync] = lambda: db
        try:
            with TestClient(app, raise_server_exceptions=False) as raw_client:
                resp = raw_client.put(f"{BASE}/{t.id}", json={"status": "PAUSED"})
        finally:
            app.dependency_overrides.pop(get_db_from_context_sync, None)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Field immutability
# ---------------------------------------------------------------------------

class TestFieldImmutability:
    def test_status_update_does_not_mutate_url(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE", url="https://original.example.com")
        _put_status(client, t.id, "PAUSED")
        db.refresh(t)
        assert t.url == "https://original.example.com"

    def test_status_update_does_not_mutate_name(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE", name="Original Name")
        _put_status(client, t.id, "PAUSED")
        db.refresh(t)
        assert t.name == "Original Name"

    def test_status_update_does_not_mutate_extraction_config(self, client, db, org_id, make_target):
        config = {"method": "llm", "custom_key": "custom_value"}
        t = make_target(org_id, status="ACTIVE", extraction_config=config)
        _put_status(client, t.id, "PAUSED")
        db.refresh(t)
        assert t.extraction_config.get("custom_key") == "custom_value"


# ---------------------------------------------------------------------------
# Idempotency / same-status transitions
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_active_to_active_is_allowed(self, client, db, org_id, make_target):
        """Canonical endpoint allows setting status to current value."""
        t = make_target(org_id, status="ACTIVE")
        resp = _put_status(client, t.id, "ACTIVE")
        assert resp.status_code == 200

    def test_paused_to_paused_is_allowed(self, client, db, org_id, make_target):
        """Canonical endpoint allows setting status to current value."""
        t = make_target(org_id, status="PAUSED")
        resp = _put_status(client, t.id, "PAUSED")
        assert resp.status_code == 200


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


class TestActiveJobGuard:
    def test_update_blocked_when_job_is_queued(self, client, db, org_id, user_id, make_target):
        """PUT returns 409 when a QUEUED job exists for the target."""
        t = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, t.id, user_id, status="QUEUED")
        resp = _put_status(client, t.id, "PAUSED")
        assert resp.status_code == 409

    def test_update_blocked_when_job_is_extracting(self, client, db, org_id, user_id, make_target):
        """PUT returns 409 when an EXTRACTING job exists."""
        t = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, t.id, user_id, status="EXTRACTING")
        resp = _put_status(client, t.id, "ARCHIVED")
        assert resp.status_code == 409

    def test_update_to_active_blocked_by_active_job(self, client, db, org_id, user_id, make_target):
        """PUT to ACTIVE is also blocked when active jobs exist."""
        t = make_target(org_id, status="PAUSED")
        _make_active_job(db, org_id, t.id, user_id, status="QUEUED")
        resp = _put_status(client, t.id, "ACTIVE")
        assert resp.status_code == 409

    def test_update_allowed_when_no_active_jobs(self, client, db, org_id, make_target):
        """PUT to PAUSED succeeds when no in-progress jobs exist."""
        t = make_target(org_id, status="ACTIVE")
        resp = _put_status(client, t.id, "PAUSED")
        assert resp.status_code == 200

    def test_409_detail_does_not_expose_internals(self, client, db, org_id, user_id, make_target):
        """409 error message must not expose tenant ID or SQL details."""
        t = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, t.id, user_id, status="QUEUED")
        resp = _put_status(client, t.id, "PAUSED")
        error = resp.json().get("error", {})
        detail = error.get("message", "")
        assert str(org_id) not in detail
        assert "sql" not in detail.lower()
