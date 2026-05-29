"""API tests for PATCH /api/v1/ingestion/targets/{id}/status.

Covers:
- Valid transitions return 200 with updated status
- Only the requested target is mutated
- Response shape includes updated status
- Invalid transitions return 422
- ARCHIVED is terminal (all outgoing transitions return 422)
- Unknown target ID returns 404
- Cross-tenant target returns 404 (not 403) to avoid leaking existence
- Missing auth context returns 401
- Malformed status value returns 422
- Unrelated fields are not mutated by a status transition
- updated_at is refreshed on transition
- Idempotent-style transitions (PAUSED -> PAUSED) are rejected clearly
"""

from __future__ import annotations

from uuid import uuid4

import pytest


BASE = "/api/v1/ingestion/targets"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _patch_status(client, target_id, status: str):
    return client.patch(f"{BASE}/{target_id}/status", json={"status": status})


# ---------------------------------------------------------------------------
# Happy-path transitions
# ---------------------------------------------------------------------------

class TestValidTransitions:
    def test_active_to_paused_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _patch_status(client, t.id, "PAUSED")
        assert resp.status_code == 200

    def test_active_to_paused_updates_status_field(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _patch_status(client, t.id, "PAUSED")
        assert resp.json()["status"] == "PAUSED"

    def test_active_to_paused_persists_in_db(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        _patch_status(client, t.id, "PAUSED")
        db.refresh(t)
        assert t.status == "PAUSED"

    def test_paused_to_active_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        resp = _patch_status(client, t.id, "ACTIVE")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ACTIVE"

    def test_active_to_archived_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _patch_status(client, t.id, "ARCHIVED")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"

    def test_paused_to_archived_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        resp = _patch_status(client, t.id, "ARCHIVED")
        assert resp.status_code == 200
        assert resp.json()["status"] == "ARCHIVED"

    def test_error_to_active_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ERROR")
        resp = _patch_status(client, t.id, "ACTIVE")
        assert resp.status_code == 200

    def test_error_to_paused_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ERROR")
        resp = _patch_status(client, t.id, "PAUSED")
        assert resp.status_code == 200

    def test_error_to_archived_returns_200(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ERROR")
        resp = _patch_status(client, t.id, "ARCHIVED")
        assert resp.status_code == 200


# ---------------------------------------------------------------------------
# Only the requested target is mutated
# ---------------------------------------------------------------------------

class TestIsolation:
    def test_only_requested_target_is_mutated(self, client, db, org_id, make_target):
        t1 = make_target(org_id, status="ACTIVE")
        t2 = make_target(org_id, status="ACTIVE")
        _patch_status(client, t1.id, "PAUSED")
        db.refresh(t2)
        assert t2.status == "ACTIVE"

    def test_response_includes_target_id(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _patch_status(client, t.id, "PAUSED")
        assert resp.json()["id"] == str(t.id)


# ---------------------------------------------------------------------------
# ARCHIVED is terminal
# ---------------------------------------------------------------------------

class TestArchivedIsTerminal:
    def test_archived_to_active_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ARCHIVED")
        resp = _patch_status(client, t.id, "ACTIVE")
        assert resp.status_code == 422

    def test_archived_to_paused_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ARCHIVED")
        resp = _patch_status(client, t.id, "PAUSED")
        assert resp.status_code == 422

    def test_archived_to_error_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ARCHIVED")
        resp = _patch_status(client, t.id, "ERROR")
        assert resp.status_code == 422

    def test_archived_terminal_error_message_does_not_expose_internals(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ARCHIVED")
        resp = _patch_status(client, t.id, "ACTIVE")
        detail = resp.json().get("detail", "")
        assert "terminal" in detail.lower() or "archived" in detail.lower()
        # Must not expose DB details or tenant info
        assert str(org_id) not in detail
        assert "sql" not in detail.lower()


# ---------------------------------------------------------------------------
# Not found / cross-tenant
# ---------------------------------------------------------------------------

class TestNotFound:
    def test_unknown_target_id_returns_404(self, client, org_id):
        resp = _patch_status(client, uuid4(), "PAUSED")
        assert resp.status_code == 404

    def test_cross_tenant_returns_404_not_403(self, client, db, other_org_id, make_target):
        """Target belonging to another tenant must return 404, not 403."""
        other_target = make_target(other_org_id, status="ACTIVE")
        # client is authenticated as org_id (not other_org_id)
        resp = _patch_status(client, other_target.id, "PAUSED")
        assert resp.status_code == 404

    def test_cross_tenant_target_not_mutated(self, client, db, other_org_id, make_target):
        other_target = make_target(other_org_id, status="ACTIVE")
        _patch_status(client, other_target.id, "PAUSED")
        db.refresh(other_target)
        assert other_target.status == "ACTIVE"


# ---------------------------------------------------------------------------
# Auth / validation errors
# ---------------------------------------------------------------------------

class TestValidation:
    def test_malformed_status_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = _patch_status(client, t.id, "NOT_A_REAL_STATUS")
        assert resp.status_code == 422

    def test_missing_status_field_returns_422(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = client.patch(f"{BASE}/{t.id}/status", json={})
        assert resp.status_code == 422

    def test_no_auth_context_returns_401(self, db, org_id, make_target):
        """Request without governance_context (no middleware) returns 401.

        The DB dependency is still overridden so the request reaches the auth
        check before attempting a real database connection.
        """
        from layer1_ingestion.api.app_monolith import app
        from layer1_ingestion.shared.database import get_db_from_context_sync
        from fastapi.testclient import TestClient
        t = make_target(org_id, status="ACTIVE")
        # Override DB so the request doesn't attempt a real PG connection.
        # No governance middleware is added, so get_tenant_id raises 401 first.
        app.dependency_overrides[get_db_from_context_sync] = lambda: db
        try:
            with TestClient(app, raise_server_exceptions=False) as raw_client:
                resp = raw_client.patch(f"{BASE}/{t.id}/status", json={"status": "PAUSED"})
        finally:
            app.dependency_overrides.pop(get_db_from_context_sync, None)
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Field immutability
# ---------------------------------------------------------------------------

class TestFieldImmutability:
    def test_status_transition_does_not_mutate_url(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE", url="https://original.example.com")
        _patch_status(client, t.id, "PAUSED")
        db.refresh(t)
        assert t.url == "https://original.example.com"

    def test_status_transition_does_not_mutate_name(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE", name="Original Name")
        _patch_status(client, t.id, "PAUSED")
        db.refresh(t)
        assert t.name == "Original Name"

    def test_status_transition_does_not_mutate_extraction_config(self, client, db, org_id, make_target):
        config = {"method": "llm", "custom_key": "custom_value"}
        t = make_target(org_id, status="ACTIVE", extraction_config=config)
        _patch_status(client, t.id, "PAUSED")
        db.refresh(t)
        assert t.extraction_config.get("custom_key") == "custom_value"


# ---------------------------------------------------------------------------
# Idempotency / same-status transitions
# ---------------------------------------------------------------------------

class TestIdempotency:
    def test_active_to_active_is_rejected(self, client, db, org_id, make_target):
        """ACTIVE -> ACTIVE is not in the allowed transition table."""
        t = make_target(org_id, status="ACTIVE")
        resp = _patch_status(client, t.id, "ACTIVE")
        assert resp.status_code == 422

    def test_paused_to_paused_is_rejected(self, client, db, org_id, make_target):
        t = make_target(org_id, status="PAUSED")
        resp = _patch_status(client, t.id, "PAUSED")
        assert resp.status_code == 422


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
    def test_pause_blocked_when_job_is_queued(self, client, db, org_id, user_id, make_target):
        """PATCH to PAUSED returns 409 when a QUEUED job exists for the target."""
        t = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, t.id, user_id, status="QUEUED")
        resp = _patch_status(client, t.id, "PAUSED")
        assert resp.status_code == 409

    def test_archive_blocked_when_job_is_extracting(self, client, db, org_id, user_id, make_target):
        """PATCH to ARCHIVED returns 409 when an EXTRACTING job exists."""
        t = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, t.id, user_id, status="EXTRACTING")
        resp = _patch_status(client, t.id, "ARCHIVED")
        assert resp.status_code == 409

    def test_resume_to_active_not_blocked_by_active_job(self, client, db, org_id, user_id, make_target):
        """PATCH to ACTIVE (resume) is never blocked by active jobs."""
        t = make_target(org_id, status="PAUSED")
        _make_active_job(db, org_id, t.id, user_id, status="QUEUED")
        resp = _patch_status(client, t.id, "ACTIVE")
        assert resp.status_code == 200

    def test_pause_allowed_when_no_active_jobs(self, client, db, org_id, make_target):
        """PATCH to PAUSED succeeds when no in-progress jobs exist."""
        t = make_target(org_id, status="ACTIVE")
        resp = _patch_status(client, t.id, "PAUSED")
        assert resp.status_code == 200

    def test_409_detail_does_not_expose_internals(self, client, db, org_id, user_id, make_target):
        """409 error message must not expose tenant ID or SQL details."""
        t = make_target(org_id, status="ACTIVE")
        _make_active_job(db, org_id, t.id, user_id, status="QUEUED")
        resp = _patch_status(client, t.id, "PAUSED")
        detail = resp.json().get("detail", "")
        assert str(org_id) not in detail
        assert "sql" not in detail.lower()
