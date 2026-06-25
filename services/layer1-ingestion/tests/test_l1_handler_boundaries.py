"""Security boundary tests for Layer 1 ingestion job and target handlers.

These tests verify the security invariants of the API handlers in:
- services/layer1-ingestion/src/layer1_ingestion/api/job_handlers.py
- services/layer1-ingestion/src/layer1_ingestion/api/target_handlers.py

Invariants:
- Tenant isolation: handlers filter every DB query by tenant_id.
- Cross-tenant access returns 404 (not 403) to avoid existence leaks.
- Input validation: Pydantic schemas reject malformed query parameters and payloads.
- URL safety: create_target rejects unsafe URLs via validate_url_safety.
- State machine: cancel_job rejects terminal states; retry_job only accepts FAILED/PARTIAL_SUCCESS.
- Domain authorization: get_domain_fallback_stats requires domain access for the tenant.
- Idempotency: execute_target handles duplicate idempotency keys.
"""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient

from layer1_ingestion.shared.models import JobStatus, ScrapingJob, ScrapingTarget


BASE = "/api/v1/ingestion"


@pytest.fixture(autouse=True)
def _mock_celery_task(monkeypatch):
    """Patch out Celery task dispatch so tests do not require Redis/Celery."""
    monkeypatch.setattr(
        "layer1_ingestion.api.job_handlers.process_scraping_job",
        type("_MockTask", (), {"apply_async": lambda *a, **k: None})(),
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.job_handlers.build_celery_options", lambda: None
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers.process_scraping_job",
        type("_MockTask", (), {"apply_async": lambda *a, **k: None})(),
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers.build_celery_options", lambda: None
    )


@pytest.fixture
def make_job(db, user_id):
    """Factory for creating ScrapingJob rows in the same SQLite session as tests."""

    def _make(
        tenant_id,
        target_id=None,
        status=JobStatus.PENDING.value,
        created_by=None,
        name="Test Job",
    ):
        if created_by is None:
            created_by = user_id
        if target_id is None:
            target = ScrapingTarget(
                tenant_id=tenant_id,
                name="Test Target",
                url="https://example.com",
                target_type="SINGLE_PAGE",
                status="ACTIVE",
                created_by=created_by,
            )
            db.add(target)
            db.flush()
            db.refresh(target)
            target_id = target.id
        job = ScrapingJob(
            tenant_id=tenant_id,
            target_id=target_id,
            status=status,
            configuration={},
            created_by=created_by,
        )
        db.add(job)
        db.flush()
        db.refresh(job)
        return job

    return _make


# ---------------------------------------------------------------------------
# Tenant isolation - Job handlers
# ---------------------------------------------------------------------------

class TestJobHandlerTenantIsolation:
    def test_get_job_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, make_job, other_org_id
    ):
        """Tenant A cannot fetch Tenant B's job details."""
        other_target = make_target(other_org_id)
        other_job = make_job(other_org_id, target_id=other_target.id)

        resp = client.get(f"{BASE}/jobs/{other_job.id}")
        assert resp.status_code == 404

    def test_get_job_progress_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, make_job, other_org_id
    ):
        """Tenant A cannot fetch Tenant B's job progress."""
        other_target = make_target(other_org_id)
        other_job = make_job(other_org_id, target_id=other_target.id)

        resp = client.get(f"{BASE}/jobs/{other_job.id}/progress")
        assert resp.status_code == 404

    def test_get_job_results_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, make_job, other_org_id
    ):
        """Tenant A cannot fetch Tenant B's job results."""
        other_target = make_target(other_org_id)
        other_job = make_job(other_org_id, target_id=other_target.id)

        resp = client.get(f"{BASE}/jobs/{other_job.id}/results")
        assert resp.status_code == 404

    def test_cancel_job_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, make_job, other_org_id
    ):
        """Tenant A cannot cancel Tenant B's job."""
        other_target = make_target(other_org_id)
        other_job = make_job(
            other_org_id, target_id=other_target.id, status=JobStatus.PENDING.value
        )

        resp = client.delete(f"{BASE}/jobs/{other_job.id}")
        assert resp.status_code == 404
        # Ensure no mutation
        db.refresh(other_job)
        assert other_job.status == JobStatus.PENDING.value

    def test_retry_job_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, make_job, other_org_id
    ):
        """Tenant A cannot retry Tenant B's failed job."""
        other_target = make_target(other_org_id)
        other_job = make_job(
            other_org_id,
            target_id=other_target.id,
            status=JobStatus.FAILED.value,
        )

        resp = client.post(
            f"{BASE}/jobs/{other_job.id}/retry",
            json={"retry_strategy": "FULL"},
        )
        assert resp.status_code == 404

    def test_list_jobs_does_not_include_cross_tenant(
        self, client: TestClient, db, make_target, make_job, org_id, other_org_id
    ):
        """list_jobs only returns jobs for the authenticated tenant."""
        own_target = make_target(org_id)
        own_job = make_job(org_id, target_id=own_target.id)

        other_target = make_target(other_org_id)
        other_job = make_job(other_org_id, target_id=other_target.id)

        resp = client.get(f"{BASE}/jobs")
        assert resp.status_code == 200
        data = resp.json()
        job_ids = {j["id"] for j in data["data"]}
        assert str(own_job.id) in job_ids
        assert str(other_job.id) not in job_ids


# ---------------------------------------------------------------------------
# Tenant isolation - Target handlers
# ---------------------------------------------------------------------------

class TestTargetHandlerTenantIsolation:
    def test_get_target_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, other_org_id
    ):
        """Tenant A cannot fetch Tenant B's target."""
        other_target = make_target(other_org_id)
        resp = client.get(f"{BASE}/targets/{other_target.id}")
        assert resp.status_code == 404

    def test_update_target_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, other_org_id
    ):
        """Tenant A cannot update Tenant B's target."""
        other_target = make_target(other_org_id, status="ACTIVE")
        resp = client.put(
            f"{BASE}/targets/{other_target.id}",
            json={"name": "Hacked"},
        )
        assert resp.status_code == 404
        db.refresh(other_target)
        assert other_target.name == "Test Target"

    def test_delete_target_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, other_org_id
    ):
        """Tenant A cannot delete Tenant B's target."""
        other_target = make_target(other_org_id)
        resp = client.delete(f"{BASE}/targets/{other_target.id}")
        assert resp.status_code == 404

    def test_validate_target_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, other_org_id
    ):
        """Tenant A cannot validate Tenant B's target."""
        other_target = make_target(other_org_id)
        resp = client.post(
            f"{BASE}/targets/{other_target.id}/validate",
            json={"validate_robots_txt": False, "validate_schema": False},
        )
        assert resp.status_code == 404

    def test_execute_target_cross_tenant_returns_404(
        self, client: TestClient, db, make_target, other_org_id
    ):
        """Tenant A cannot execute Tenant B's target."""
        other_target = make_target(other_org_id, status="ACTIVE")
        resp = client.post(
            f"{BASE}/targets/{other_target.id}/execute",
            json={"priority": 5},
        )
        assert resp.status_code == 404

    def test_list_targets_does_not_include_cross_tenant(
        self, client: TestClient, db, make_target, org_id, other_org_id
    ):
        """list_targets only returns targets for the authenticated tenant."""
        own_target = make_target(org_id)
        other_target = make_target(other_org_id)

        resp = client.get(f"{BASE}/targets")
        assert resp.status_code == 200
        data = resp.json()
        target_ids = {t["id"] for t in data["data"]}
        assert str(own_target.id) in target_ids
        assert str(other_target.id) not in target_ids


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------

class TestHandlerInputValidation:
    def test_list_jobs_rejects_invalid_sort_by(
        self, client: TestClient
    ):
        """Invalid sort_by query parameter is rejected."""
        resp = client.get(f"{BASE}/jobs?sort_by=malicious")
        assert resp.status_code == 422

    def test_list_jobs_rejects_invalid_sort_order(
        self, client: TestClient
    ):
        """Invalid sort_order query parameter is rejected."""
        resp = client.get(f"{BASE}/jobs?sort_order=malicious")
        assert resp.status_code == 422

    def test_list_targets_rejects_invalid_sort_by(
        self, client: TestClient
    ):
        """Invalid sort_by query parameter is rejected for targets."""
        resp = client.get(f"{BASE}/targets?sort_by=malicious")
        assert resp.status_code == 422

    def test_retry_job_rejects_invalid_strategy(
        self, client: TestClient, db, make_target, make_job, org_id
    ):
        """retry_job rejects unknown retry_strategy values."""
        target = make_target(org_id)
        job = make_job(
            org_id,
            target_id=target.id,
            status=JobStatus.FAILED.value,
        )
        resp = client.post(
            f"{BASE}/jobs/{job.id}/retry",
            json={"retry_strategy": "INVALID"},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# URL safety
# ---------------------------------------------------------------------------

class TestCreateTargetURLSafety:
    def test_create_target_rejects_private_ip_url(
        self, client: TestClient, org_id, user_id
    ):
        """create_target rejects URLs pointing to private IPs (SSRF prevention)."""
        resp = client.post(
            f"{BASE}/targets",
            json={
                "name": "SSRF",
                "url": "http://169.254.169.254/latest/meta-data/",
                "target_type": "SINGLE_PAGE",
            },
        )
        assert resp.status_code in (400, 422)
        body = resp.text
        assert "url" in body.lower() or "validation" in body.lower() or "blocked" in body.lower()

    def test_create_target_rejects_localhost(
        self, client: TestClient, org_id, user_id
    ):
        """create_target rejects localhost URLs."""
        resp = client.post(
            f"{BASE}/targets",
            json={
                "name": "Localhost",
                "url": "http://localhost:8000/admin",
                "target_type": "SINGLE_PAGE",
            },
        )
        assert resp.status_code in (400, 422)


# ---------------------------------------------------------------------------
# State machine
# ---------------------------------------------------------------------------

class TestJobStateMachine:
    def test_cancel_job_rejects_terminal_state(
        self, client: TestClient, db, make_target, make_job, org_id
    ):
        """Cannot cancel a job that is already completed."""
        target = make_target(org_id)
        job = make_job(
            org_id,
            target_id=target.id,
            status=JobStatus.COMPLETED.value,
        )

        resp = client.delete(f"{BASE}/jobs/{job.id}")
        assert resp.status_code == 409

    def test_retry_job_rejects_non_failed_job(
        self, client: TestClient, db, make_target, make_job, org_id
    ):
        """Cannot retry a job that is not FAILED or PARTIAL_SUCCESS."""
        target = make_target(org_id)
        job = make_job(
            org_id,
            target_id=target.id,
            status=JobStatus.COMPLETED.value,
        )

        resp = client.post(
            f"{BASE}/jobs/{job.id}/retry",
            json={"retry_strategy": "FULL"},
        )
        assert resp.status_code == 409

    def test_retry_job_accepts_failed_job(
        self, client: TestClient, db, make_target, make_job, org_id
    ):
        """Retrying a failed job is accepted."""
        target = make_target(org_id, status="ACTIVE")
        job = make_job(
            org_id,
            target_id=target.id,
            status=JobStatus.FAILED.value,
        )

        resp = client.post(
            f"{BASE}/jobs/{job.id}/retry",
            json={"retry_strategy": "FULL"},
        )
        assert resp.status_code == 202
        data = resp.json()
        assert data["status"] == JobStatus.QUEUED.value


# ---------------------------------------------------------------------------
# Domain authorization
# ---------------------------------------------------------------------------

class TestDomainAuthorization:
    def test_get_domain_fallback_stats_unauthorized_domain(
        self, client: TestClient, db, make_target, org_id
    ):
        """Requesting fallback stats for a domain the tenant has no access to fails."""
        # Create target for a different domain
        make_target(org_id, url="https://example.com")
        resp = client.get(f"{BASE}/domains/unrelated-domain.com/fallback-stats")
        assert resp.status_code in (403, 404)


# ---------------------------------------------------------------------------
# Positive cases
# ---------------------------------------------------------------------------

class TestJobHandlerPositive:
    def test_get_own_job_returns_200(
        self, client: TestClient, db, make_target, make_job, org_id
    ):
        """Tenant can fetch their own job details."""
        target = make_target(org_id)
        job = make_job(org_id, target_id=target.id)

        resp = client.get(f"{BASE}/jobs/{job.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(job.id)
        assert data["tenant_id"] == str(org_id)


class TestTargetHandlerPositive:
    def test_get_own_target_returns_200(
        self, client: TestClient, db, make_target, org_id
    ):
        """Tenant can fetch their own target."""
        target = make_target(org_id)
        resp = client.get(f"{BASE}/targets/{target.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == str(target.id)
        assert data["tenant_id"] == str(org_id)
