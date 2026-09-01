"""Launch-hardening regressions for Layer 1 target handlers."""

from __future__ import annotations

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
    detail = payload.get("detail", payload)
    assert detail["code"] == "SERVICE_UNAVAILABLE"

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
