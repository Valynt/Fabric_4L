"""Tenant isolation and security tests for target status and batch endpoints.

Invariants:
- Tenant A cannot patch Tenant B's target status
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
BATCH_BASE = "/api/v1/ingestion/targets/batch"


# ---------------------------------------------------------------------------
# Status endpoint — cross-tenant isolation
# ---------------------------------------------------------------------------

class TestStatusEndpointTenantIsolation:
    def test_tenant_a_cannot_patch_tenant_b_status(
        self, client, db, other_org_id, make_target
    ):
        """client is authenticated as org_id; target belongs to other_org_id."""
        b_target = make_target(other_org_id, status="ACTIVE")
        resp = client.patch(
            f"{STATUS_BASE}/{b_target.id}/status",
            json={"status": "PAUSED"},
        )
        assert resp.status_code == 404

    def test_cross_tenant_status_returns_404_not_403(
        self, client, db, other_org_id, make_target
    ):
        """404 avoids leaking that the target exists in another tenant."""
        b_target = make_target(other_org_id, status="ACTIVE")
        resp = client.patch(
            f"{STATUS_BASE}/{b_target.id}/status",
            json={"status": "PAUSED"},
        )
        assert resp.status_code == 404, (
            f"Expected 404 to avoid existence leak, got {resp.status_code}"
        )

    def test_cross_tenant_status_does_not_mutate_target(
        self, client, db, other_org_id, make_target
    ):
        b_target = make_target(other_org_id, status="ACTIVE")
        client.patch(
            f"{STATUS_BASE}/{b_target.id}/status",
            json={"status": "PAUSED"},
        )
        db.refresh(b_target)
        assert b_target.status == "ACTIVE"

    def test_cross_tenant_404_response_does_not_leak_tenant_id(
        self, client, db, other_org_id, make_target
    ):
        b_target = make_target(other_org_id, status="ACTIVE")
        resp = client.patch(
            f"{STATUS_BASE}/{b_target.id}/status",
            json={"status": "PAUSED"},
        )
        body = resp.text
        assert str(other_org_id) not in body
        assert str(b_target.id) not in body or "not found" in body.lower()

    def test_unauthenticated_status_request_returns_401(self, db, org_id, make_target):
        from layer1_ingestion.api.app_monolith import app
        t = make_target(org_id, status="ACTIVE")
        with TestClient(app, raise_server_exceptions=False) as raw:
            resp = raw.patch(
                f"{STATUS_BASE}/{t.id}/status",
                json={"status": "PAUSED"},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Batch endpoint — cross-tenant isolation
# ---------------------------------------------------------------------------

class TestBatchEndpointTenantIsolation:
    def test_tenant_a_batch_skips_tenant_b_ids(
        self, client, db, other_org_id, make_target
    ):
        b_target = make_target(other_org_id, status="ACTIVE")
        resp = client.post(
            BATCH_BASE,
            json={"operation": "pause", "target_ids": [str(b_target.id)]},
        )
        assert resp.status_code == 202
        assert resp.json()["results"][0]["status"] == "skipped"

    def test_batch_skipped_cross_tenant_does_not_mutate_target(
        self, client, db, other_org_id, make_target
    ):
        b_target = make_target(other_org_id, status="ACTIVE")
        client.post(
            BATCH_BASE,
            json={"operation": "pause", "target_ids": [str(b_target.id)]},
        )
        db.refresh(b_target)
        assert b_target.status == "ACTIVE"

    def test_batch_skipped_result_does_not_disclose_existence(
        self, client, db, other_org_id, make_target
    ):
        """
        The skipped result for a cross-tenant ID must be indistinguishable
        from a skipped result for a completely unknown ID.
        """
        b_target = make_target(other_org_id, status="ACTIVE", name="Tenant B Secret")
        unknown_id = uuid4()

        resp = client.post(
            BATCH_BASE,
            json={"operation": "pause", "target_ids": [str(b_target.id), str(unknown_id)]},
        )
        results = {r["id"]: r for r in resp.json()["results"]}

        cross_result = results[str(b_target.id)]
        unknown_result = results[str(unknown_id)]

        # Both must be "skipped" — same status, no distinguishing info
        assert cross_result["status"] == "skipped"
        assert unknown_result["status"] == "skipped"

        # Cross-tenant result must not expose the target name or other tenant's ID
        cross_str = str(cross_result)
        assert "Tenant B Secret" not in cross_str
        assert str(other_org_id) not in cross_str

    def test_batch_cannot_archive_cross_tenant_target(
        self, client, db, other_org_id, make_target
    ):
        b_target = make_target(other_org_id, status="ACTIVE")
        client.post(
            BATCH_BASE,
            json={"operation": "archive", "target_ids": [str(b_target.id)]},
        )
        db.refresh(b_target)
        assert b_target.status == "ACTIVE"

    def test_batch_cannot_execute_cross_tenant_target(
        self, client, db, other_org_id, make_target
    ):
        from layer1_ingestion.shared.models import ScrapingJob
        b_target = make_target(other_org_id, status="ACTIVE")
        client.post(
            BATCH_BASE,
            json={"operation": "execute", "target_ids": [str(b_target.id)]},
        )
        job_count = (
            db.query(ScrapingJob)
            .filter(ScrapingJob.target_id == b_target.id)
            .count()
        )
        assert job_count == 0

    def test_unauthenticated_batch_request_returns_401(self, db, org_id, make_target):
        from layer1_ingestion.api.app_monolith import app
        t = make_target(org_id, status="ACTIVE")
        with TestClient(app, raise_server_exceptions=False) as raw:
            resp = raw.post(
                BATCH_BASE,
                json={"operation": "pause", "target_ids": [str(t.id)]},
            )
        assert resp.status_code == 401


# ---------------------------------------------------------------------------
# Mixed-tenant batch: own targets succeed, foreign targets skip
# ---------------------------------------------------------------------------

class TestMixedTenantBatch:
    def test_own_targets_succeed_foreign_targets_skip(
        self, client, db, org_id, other_org_id, make_target
    ):
        own = make_target(org_id, status="ACTIVE")
        foreign = make_target(other_org_id, status="ACTIVE")

        resp = client.post(
            BATCH_BASE,
            json={"operation": "pause", "target_ids": [str(own.id), str(foreign.id)]},
        )
        data = resp.json()
        assert data["succeeded"] == 1

        results = {r["id"]: r["status"] for r in data["results"]}
        assert results[str(own.id)] == "succeeded"
        assert results[str(foreign.id)] == "skipped"

        db.refresh(own)
        db.refresh(foreign)
        assert own.status == "PAUSED"
        assert foreign.status == "ACTIVE"
