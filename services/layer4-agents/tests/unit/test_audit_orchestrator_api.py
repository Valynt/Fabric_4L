"""Unit tests for the AuditOrchestrator FastAPI router.

These tests use a minimal FastAPI app with the audit orchestrator router
mounted under ``/v1/repo-audit`` and a JSON-file fallback persistence manager
so no live database is required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI

from layer4_agents.agents.audit_orchestrator import api as audit_api
from layer4_agents.agents.audit_orchestrator.api import (
    get_manager,
)
from layer4_agents.agents.audit_orchestrator.api import (
    router as audit_orchestrator_router,
)
from layer4_agents.agents.audit_orchestrator.models import (
    AuditArea,
    AuditConfig,
    AuditRun,
    Confidence,
    Finding,
    FindingStatus,
    Severity,
    Sprint,
    SprintStatus,
)
from layer4_agents.agents.audit_orchestrator.persistence import PersistenceManager
from layer4_agents.agents.audit_orchestrator.scoring import build_scorecard


@pytest.fixture
def app(tmp_path):
    """Create a minimal FastAPI app with the audit orchestrator router."""
    application = FastAPI()
    application.include_router(
        audit_orchestrator_router,
        prefix="/v1/repo-audit",
        tags=["repo-audit"],
    )

    def _manager():
        return PersistenceManager(fallback_dir=tmp_path / "fallback")

    application.dependency_overrides[get_manager] = _manager
    return application


@pytest.fixture
def client(app):
    """Return a synchronous TestClient for the app."""
    from fastapi.testclient import TestClient

    return TestClient(app)


def _make_run_artifact(
    manager: PersistenceManager,
    run_id: str,
    repo_name: str,
    finding_ids: list[str],
) -> None:
    """Seed a completed audit run with findings for a repository."""
    findings = [
        Finding(
            id=fid,
            severity=Severity.MEDIUM,
            confidence=Confidence.HIGH,
            area=AuditArea.CODE_QUALITY,
            evidence=f"src/{fid.lower()}.py:1",
            observed_fact=f"Observation for {fid}",
            inference_risk="Risk description",
            business_impact="Business impact",
            recommended_fix="Fix it",
            effort="S",
            risk_of_change="Low",
            owner="platform-team",
            status=FindingStatus.OPEN,
            analyzer_type="code",
        )
        for fid in finding_ids
    ]

    scorecard = build_scorecard(
        repo_name=repo_name,
        findings=findings,
        branch="main",
        commit_sha="abc123",
        total_files=10,
        total_directories=2,
        total_commits=5,
        total_contributors=1,
    )

    run = AuditRun(
        id=run_id,
        status="completed",
        trigger_type="manual",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        repo_path="/tmp/repo",
        scorecard=scorecard,
    )

    sprints = [
        Sprint(
            id=1,
            theme=f"Stabilize {repo_name}",
            objectives=["Fix findings"],
            deliverables=["PR"],
            findings_targeted=finding_ids,
            status=SprintStatus.PLANNED,
            score_impact_projected=5,
        )
    ]

    import asyncio

    asyncio.run(manager.save_run(run))
    asyncio.run(manager.save_scorecard(run_id, scorecard))
    asyncio.run(manager.save_sprints(run_id, sprints, repo_name=repo_name))


@pytest.mark.unit
def test_trigger_audit_returns_run_id(client: Any, monkeypatch: pytest.MonkeyPatch):
    """POST /run must accept a trigger and return a run ID immediately."""
    captured = {}

    def fake_background_run(
        config: AuditConfig,
        trigger_type: str,
        previous_run_id: str | None,
        run_id: str | None = None,
    ) -> None:
        captured["run_id"] = run_id
        captured["repo_name"] = config.repo_name

    monkeypatch.setattr(audit_api, "_background_run", fake_background_run)

    response = client.post(
        "/v1/repo-audit/run",
        json={
            "repo_url": "https://github.com/owner/repo-a",
            "branch": "main",
            "incremental": False,
        },
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["run_id"]
    assert data["run_id"] == captured["run_id"]
    assert captured["repo_name"] == "owner/repo-a"


@pytest.mark.unit
def test_get_audit_run(client: Any, tmp_path: Any):
    """GET /runs/{run_id} must return run details for an existing run."""
    manager = PersistenceManager(fallback_dir=tmp_path / "fallback")
    run_id = "run-111"
    _make_run_artifact(manager, run_id, "owner/repo-a", ["CQ-001"])

    response = client.get(f"/v1/repo-audit/runs/{run_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["run_id"] == run_id
    assert data["repo_name"] == "owner/repo-a"
    assert data["status"] == "completed"
    assert data["overall_score"] is not None
    assert data["findings_count"] == 1
    assert data["sprints_count"] == 1


@pytest.mark.unit
def test_get_audit_run_not_found(client: Any):
    """GET /runs/{run_id} must 404 for an unknown run."""
    response = client.get("/v1/repo-audit/runs/does-not-exist")
    assert response.status_code == 404


@pytest.mark.unit
def test_list_findings_filters_by_repo(client: Any, tmp_path: Any, monkeypatch: pytest.MonkeyPatch):
    """GET /findings must only return findings for the requested repository."""
    manager = PersistenceManager(fallback_dir=tmp_path / "fallback")

    # Seed data for two different repositories.
    _make_run_artifact(manager, "run-repo-a", "owner/repo-a", ["CQ-001", "CQ-002"])
    _make_run_artifact(manager, "run-repo-b", "owner/repo-b", ["CQ-003"])

    # Override the background task so the POST endpoint does not overwrite data.
    monkeypatch.setattr(audit_api, "_background_run", lambda *args, **kwargs: None)

    repo_a_response = client.get("/v1/repo-audit/findings?repo=owner/repo-a")
    assert repo_a_response.status_code == 200
    repo_a_data = repo_a_response.json()
    repo_a_ids = {f["id"] for f in repo_a_data}

    repo_b_response = client.get("/v1/repo-audit/findings?repo=owner/repo-b")
    assert repo_b_response.status_code == 200
    repo_b_data = repo_b_response.json()
    repo_b_ids = {f["id"] for f in repo_b_data}

    assert repo_a_ids == {"CQ-001", "CQ-002"}
    assert repo_b_ids == {"CQ-003"}
    assert repo_a_ids.isdisjoint(repo_b_ids)


@pytest.mark.unit
def test_trigger_audit_requires_repo_url(client: Any):
    """POST /run must reject requests without a repository URL."""
    response = client.post("/v1/repo-audit/run", json={})
    assert response.status_code == 400
    assert "repo_url" in response.json()["detail"].lower()


@pytest.mark.unit
def test_github_webhook_requires_valid_signature(client: Any):
    """The GitHub webhook endpoint must reject requests with an invalid HMAC."""
    import os

    os.environ["GITHUB_WEBHOOK_SECRET"] = "super-secret"
    payload = b'{"ref":"refs/heads/main","repository":{"clone_url":"https://github.com/owner/repo.git","full_name":"owner/repo"}}'
    response = client.post(
        "/v1/repo-audit/webhook/github",
        content=payload,
        headers={"x-github-event": "push", "x-hub-signature-256": "sha256=invalid"},
    )
    assert response.status_code == 403
