"""Launch-hardening regressions for Layer 1 target handlers."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from fastapi.testclient import TestClient

from layer1_ingestion.shared.models import JobStatus, ScrapingJob

BASE = "/api/v1/ingestion"


class _UnavailableTask:
    """Model task infrastructure that accepted no work."""

    def apply_async(self, *args, **kwargs) -> None:  # noqa: ANN002, ANN003
        raise HTTPException(
            status_code=503,
            detail={
                "code": "SERVICE_UNAVAILABLE",
                "message": "Background processing is temporarily unavailable.",
            },
        )


def test_execute_target_dispatch_failure_does_not_leave_queued_job(
    client: TestClient,
    db,
    make_target,
    org_id,
    monkeypatch,
) -> None:
    """A failed task dispatch must persist a terminal failure, never a false QUEUED state."""
    target = make_target(org_id, status="ACTIVE")
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers.process_scraping_job",
        _UnavailableTask(),
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers.build_celery_options",
        lambda: None,
    )

    response = client.post(
        f"{BASE}/targets/{target.id}/execute",
        json={"priority": 5},
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["error"]["code"] == "SERVICE_UNAVAILABLE"

    jobs = (
        db.query(ScrapingJob)
        .filter(
            ScrapingJob.tenant_id == org_id,
            ScrapingJob.target_id == target.id,
        )
        .all()
    )
    assert len(jobs) == 1
    assert jobs[0].status == JobStatus.FAILED.value


def test_execute_target_dispatch_failure_leaves_other_placeholder_intact(
    client: TestClient,
    db,
    make_target,
    org_id,
    monkeypatch,
) -> None:
    """Only the request that owns the placeholder may delete it on dispatch failure."""
    target = make_target(org_id, status="ACTIVE")
    delete_key = MagicMock()
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers._delete_idempotency_key",
        delete_key,
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers._check_idempotency_key",
        AsyncMock(return_value=(None, None)),
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers._update_idempotency_key",
        lambda *args, **kwargs: None,
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers.process_scraping_job",
        _UnavailableTask(),
    )
    monkeypatch.setattr(
        "layer1_ingestion.api.target_handlers.build_celery_options",
        lambda: None,
    )

    response = client.post(
        f"{BASE}/targets/{target.id}/execute",
        json={"priority": 5, "idempotency_key": "existing-key"},
    )

    assert response.status_code == 503
    delete_key.assert_not_called()
