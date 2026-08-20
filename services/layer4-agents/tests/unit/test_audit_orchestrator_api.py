"""Unit tests for the AuditOrchestrator FastAPI router.

These tests use a minimal FastAPI app with the audit orchestrator router
mounted under ``/v1/repo-audit`` and a JSON-file fallback persistence manager
so no live database is required.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi import FastAPI
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin

from layer4_agents.agents.audit_orchestrator import api as audit_api
from layer4_agents.agents.audit_orchestrator.api import (
    _background_run_async,
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


def _fake_require_tenant_admin():
    return RequestContext(
        tenant_id="tenant-a",
        user_id="user-1",
        auth_source="jwt_claim",
        roles=["tenant_admin"],
    )


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
    application.dependency_overrides[require_tenant_admin] = _fake_require_tenant_admin
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
    tenant_id: str = "tenant-a",
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
            tenant_id=tenant_id,
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
    scorecard.tenant_id = tenant_id

    run = AuditRun(
        id=run_id,
        status="completed",
        trigger_type="manual",
        started_at=datetime.now(UTC),
        completed_at=datetime.now(UTC),
        repo_path="/tmp/repo",
        scorecard=scorecard,
        tenant_id=tenant_id,
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
            tenant_id=tenant_id,
        )
    ]

    asyncio.run(manager.save_run(run, tenant_id=tenant_id))
    asyncio.run(manager.save_scorecard(run_id, scorecard, tenant_id=tenant_id))
    asyncio.run(manager.save_findings(run_id, findings, repo_name=repo_name, tenant_id=tenant_id))
    asyncio.run(manager.save_sprints(run_id, sprints, repo_name=repo_name, tenant_id=tenant_id))


@pytest.mark.unit
def test_trigger_audit_returns_run_id(client: Any, monkeypatch: pytest.MonkeyPatch):
    """POST /run must accept a trigger and return a run ID immediately."""
    captured = {}

    async def fake_background_run_async(
        config: AuditConfig,
        trigger_type: str,
        previous_run_id: str | None,
        run_id: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        captured["run_id"] = run_id
        captured["repo_name"] = config.repo_name
        captured["tenant_id"] = tenant_id

    monkeypatch.setattr(audit_api, "_background_run_async", fake_background_run_async)

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
    assert captured["tenant_id"] == "tenant-a"


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
    assert response.status_code == 422
    assert any(error["loc"][-1] == "repo_url" for error in response.json()["detail"])


@pytest.mark.unit
def test_github_webhook_requires_valid_signature(client: Any, monkeypatch: pytest.MonkeyPatch):
    """The GitHub webhook endpoint must reject requests with an invalid HMAC."""
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", "super-secret")
    monkeypatch.delenv("DEV_WEBHOOK_UNSAFE", raising=False)
    payload = b'{"ref":"refs/heads/main","repository":{"clone_url":"https://github.com/owner/repo.git","full_name":"owner/repo"}}'
    response = client.post(
        "/v1/repo-audit/webhook/github?tenant_id=tenant-webhook",
        content=payload,
        headers={"x-github-event": "push", "x-hub-signature-256": "sha256=invalid"},
    )
    assert response.status_code == 403


@pytest.mark.unit
def test_github_webhook_rejects_unsigned_when_secret_missing(
    client: Any, monkeypatch: pytest.MonkeyPatch
):
    """Unsigned webhooks are rejected when no secret is configured."""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    monkeypatch.delenv("DEV_WEBHOOK_UNSAFE", raising=False)
    payload = b'{"ref":"refs/heads/main","repository":{"clone_url":"https://github.com/owner/repo.git","full_name":"owner/repo"}}'
    response = client.post(
        "/v1/repo-audit/webhook/github?tenant_id=tenant-webhook",
        content=payload,
        headers={"x-github-event": "push"},
    )
    assert response.status_code == 401


@pytest.mark.unit
def test_github_webhook_accepts_unsigned_with_dev_flag(
    client: Any, monkeypatch: pytest.MonkeyPatch
):
    """Unsigned webhooks are accepted only when the explicit dev flag is set."""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("DEV_WEBHOOK_UNSAFE", "true")
    payload = b'{"ref":"refs/heads/main","repository":{"clone_url":"https://github.com/owner/repo.git","full_name":"owner/repo"}}'
    response = client.post(
        "/v1/repo-audit/webhook/github?tenant_id=tenant-webhook",
        content=payload,
        headers={"x-github-event": "push"},
    )
    assert response.status_code == 200


@pytest.mark.unit
def test_get_manager_uses_postgres_dsn_from_env(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_manager must use AUDIT__POSTGRES_DSN when it is configured."""
    monkeypatch.setenv("AUDIT__POSTGRES_DSN", "postgresql+asyncpg://user:pass@localhost/audit")
    monkeypatch.delenv("AUDIT__CACHE_DIR", raising=False)

    manager = get_manager()
    try:
        assert manager._use_fallback is False
        assert manager._engine is not None
        assert "postgresql" in str(manager._engine.url)
    finally:
        if manager._engine is not None:
            asyncio.run(manager._engine.dispose())


@pytest.mark.unit
def test_update_finding_requires_repo_and_scopes_to_repo(client: Any, tmp_path: Any) -> None:
    """PATCH /findings/{id} must require a repo query parameter."""
    manager = PersistenceManager(fallback_dir=tmp_path / "fallback")
    _make_run_artifact(manager, "run-123", "owner/repo-x", ["CQ-010"])

    response = client.patch("/v1/repo-audit/findings/CQ-010")
    assert response.status_code == 422

    response = client.patch(
        "/v1/repo-audit/findings/CQ-010?repo=owner/repo-x",
        json={"status": "resolved"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "resolved"


@pytest.mark.unit
def test_github_webhook_url_with_push_does_not_trigger_on_pull_request(
    client: Any, monkeypatch: pytest.MonkeyPatch
):
    """A repo URL containing 'push' but event_type 'pull_request' must not trigger."""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("DEV_WEBHOOK_UNSAFE", "true")

    captured = {}

    async def fake_background_run_async(
        config: AuditConfig,
        trigger_type: str,
        previous_run_id: str | None,
        run_id: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        captured["triggered"] = True

    monkeypatch.setattr(audit_api, "_background_run_async", fake_background_run_async)

    payload = b'{"ref":"refs/heads/main","repository":{"clone_url":"https://github.com/push-to-deploy/repo.git","full_name":"push-to-deploy/repo"}}'
    response = client.post(
        "/v1/repo-audit/webhook/github?tenant_id=tenant-webhook",
        content=payload,
        headers={"x-github-event": "pull_request"},
    )
    assert response.status_code == 200
    assert "triggered" not in captured


@pytest.mark.unit
def test_github_webhook_requires_tenant_id(client: Any, monkeypatch: pytest.MonkeyPatch):
    """The GitHub webhook endpoint must reject requests without a tenant_id."""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("DEV_WEBHOOK_UNSAFE", "true")

    payload = b'{"ref":"refs/heads/main","repository":{"clone_url":"https://github.com/owner/repo.git","full_name":"owner/repo"}}'
    response = client.post(
        "/v1/repo-audit/webhook/github",
        content=payload,
        headers={"x-github-event": "push"},
    )
    assert response.status_code == 422


@pytest.mark.unit
def test_github_webhook_scopes_run_to_provided_tenant(
    client: Any, monkeypatch: pytest.MonkeyPatch
):
    """A webhook with ?tenant_id=... must pass that tenant to the background run."""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("DEV_WEBHOOK_UNSAFE", "true")

    captured = {}

    async def fake_background_run_async(
        config: AuditConfig,
        trigger_type: str,
        previous_run_id: str | None,
        run_id: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        captured["tenant_id"] = tenant_id
        captured["config_tenant_id"] = config.tenant_id

    monkeypatch.setattr(audit_api, "_background_run_async", fake_background_run_async)

    payload = b'{"ref":"refs/heads/main","repository":{"clone_url":"https://github.com/owner/repo.git","full_name":"owner/repo"}}'
    response = client.post(
        "/v1/repo-audit/webhook/github?tenant_id=tenant-webhook",
        content=payload,
        headers={"x-github-event": "push"},
    )
    assert response.status_code == 200
    assert captured["tenant_id"] == "tenant-webhook"
    assert captured["config_tenant_id"] == "tenant-webhook"


@pytest.mark.unit
def test_github_webhook_with_secret_and_tenant_id(
    client: Any, monkeypatch: pytest.MonkeyPatch
):
    """A signed webhook must still require and forward tenant_id."""
    secret = "super-secret"
    monkeypatch.setenv("GITHUB_WEBHOOK_SECRET", secret)
    monkeypatch.delenv("DEV_WEBHOOK_UNSAFE", raising=False)

    captured = {}

    async def fake_background_run_async(
        config: AuditConfig,
        trigger_type: str,
        previous_run_id: str | None,
        run_id: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        captured["tenant_id"] = tenant_id

    monkeypatch.setattr(audit_api, "_background_run_async", fake_background_run_async)

    payload = b'{"ref":"refs/heads/main","repository":{"clone_url":"https://github.com/owner/repo.git","full_name":"owner/repo"}}'
    signature = "sha256=" + hmac.new(
        secret.encode("utf-8"), payload, hashlib.sha256
    ).hexdigest()

    response = client.post(
        "/v1/repo-audit/webhook/github?tenant_id=tenant-signed",
        content=payload,
        headers={"x-github-event": "push", "x-hub-signature-256": signature},
    )
    assert response.status_code == 200
    assert captured["tenant_id"] == "tenant-signed"


@pytest.mark.unit
def test_get_manager_caches_engine_per_dsn(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_manager must reuse the same engine for identical DSNs."""
    dsn = "postgresql+asyncpg://user:pass@localhost/audit"
    monkeypatch.setenv("AUDIT__POSTGRES_DSN", dsn)
    monkeypatch.delenv("AUDIT__CACHE_DIR", raising=False)

    from layer4_agents.agents.audit_orchestrator.persistence import _engine_cache

    # Clear any cached engine for this DSN so the test starts fresh.
    _engine_cache.pop(dsn, None)

    manager_a = get_manager()
    manager_b = get_manager()
    try:
        assert manager_a._engine is not None
        assert manager_a._engine is manager_b._engine
        assert dsn in _engine_cache
    finally:
        if manager_a._engine is not None:
            asyncio.run(manager_a._engine.dispose())
        _engine_cache.pop(dsn, None)


@pytest.mark.unit
def test_background_run_async_persists_failure(
    tmp_path: Any, monkeypatch: pytest.MonkeyPatch
) -> None:
    """_background_run_async must persist a failed run when run_audit_async raises."""

    async def failing_audit(*args: Any, **kwargs: Any) -> None:
        raise RuntimeError("simulated audit failure")

    monkeypatch.setattr(audit_api, "run_audit_async", failing_audit)

    config = AuditConfig(
        repo_url="https://github.com/owner/repo",
        repo_name="owner/repo",
        cache_dir=str(tmp_path / "cache"),
    )
    run_id = "failed-run-001"
    tenant_id = "tenant-fail"

    asyncio.run(
        _background_run_async(config, "manual", None, run_id=run_id, tenant_id=tenant_id)
    )

    manager = PersistenceManager(fallback_dir=config.cache_dir)
    run = asyncio.run(manager.get_run(run_id, tenant_id=tenant_id))
    assert run is not None
    assert run.status == "failed"
    assert run.tenant_id == tenant_id
    assert "simulated audit failure" in run.error_message


@pytest.mark.unit
def test_openapi_matches_audit_trigger_and_report_contract(app):
    spec = app.openapi()
    request_schema = spec["paths"]["/v1/repo-audit/run"]["post"]["requestBody"][
        "content"
    ]["application/json"]["schema"]
    model_name = request_schema["$ref"].rsplit("/", 1)[-1]
    trigger_model = spec["components"]["schemas"][model_name]
    assert "repo_url" in trigger_model.get("required", [])

    report_content = spec["paths"]["/v1/repo-audit/report/{run_id}"]["get"][
        "responses"
    ]["200"]["content"]
    assert {"application/json", "text/markdown"} <= set(report_content)


@pytest.mark.unit
@pytest.mark.parametrize(
    "hostile_url",
    [
        "/",
        "/etc",
        "/etc/passwd",
        "C:\\Windows",
        ".",
        "../secret",
        "../../etc/shadow",
        "file:///etc/passwd",
        "file://localhost/etc/hosts",
        "ext::sh -c evil",
        "fd::1",
        "ftp://github.com/org/repo",
        "gopher://github.com/org/repo",
        "git@github.com:org/repo;rm -rf /",
        "https://github.com/org/repo\nevil",
        "http://169.254.169.254/latest/meta-data",
        "http://localhost:8080/repo",
        "http://127.0.0.1:8000/repo",
        "git@localhost:owner/repo.git",
        "git@127.0.0.1:owner/repo.git",
        "git@10.0.0.1:owner/repo.git",
        "http://10.0.0.1/repo",
        "http://192.168.1.1/repo",
        "http://172.16.0.1/repo",
        "ssh://git@10.0.0.1/repo.git",
        "http://metadata.google.internal/repo",
    ],
)
def test_trigger_audit_rejects_hostile_repo_urls(client, hostile_url: str):
    """POST /run must reject local filesystem paths, file://, traversal, and dangerous schemes."""
    response = client.post(
        "/v1/repo-audit/run",
        json={"repo_url": hostile_url, "branch": "main"},
    )
    assert response.status_code == 422


@pytest.mark.unit
@pytest.mark.parametrize(
    "valid_url",
    [
        "https://github.com/org/repo.git",
        "http://github.com/org/repo",
        "git@github.com:org/repo.git",
        "ssh://git@github.com/org/repo.git",
    ],
)
def test_trigger_audit_accepts_valid_repo_urls(
    client, monkeypatch: pytest.MonkeyPatch, valid_url: str
):
    """POST /run must accept valid Git URLs."""
    async def fake_background_run_async(*args, **kwargs) -> None:
        pass

    monkeypatch.setattr(audit_api, "_background_run_async", fake_background_run_async)
    response = client.post(
        "/v1/repo-audit/run",
        json={"repo_url": valid_url, "branch": "main"},
    )
    assert response.status_code == 200
    assert response.json()["status"] == "pending"


@pytest.mark.unit
@pytest.mark.parametrize(
    "hostile_clone_url",
    [
        "/",
        "/etc",
        "/etc/shadow",
        "file:///etc/passwd",
        "ext::evil",
        "ftp://evil.com/repo",
        "../traversal",
    ],
)
def test_github_webhook_rejects_hostile_clone_url(
    client, monkeypatch: pytest.MonkeyPatch, hostile_clone_url: str
):
    """The GitHub webhook endpoint must reject payloads with hostile clone_urls."""
    monkeypatch.delenv("GITHUB_WEBHOOK_SECRET", raising=False)
    monkeypatch.setenv("DEV_WEBHOOK_UNSAFE", "true")

    captured = {}

    async def fake_background_run_async(*args, **kwargs):
        captured["triggered"] = True

    monkeypatch.setattr(audit_api, "_background_run_async", fake_background_run_async)

    import json
    payload = json.dumps({
        "ref": "refs/heads/main",
        "repository": {
            "clone_url": hostile_clone_url,
            "full_name": "owner/repo",
        },
    }).encode("utf-8")

    response = client.post(
        "/v1/repo-audit/webhook/github?tenant_id=tenant-webhook",
        content=payload,
        headers={"x-github-event": "push"},
    )
    assert response.status_code == 400
    assert "triggered" not in captured


@pytest.mark.unit
def test_build_config_enforces_untrusted_source():
    """_build_config must always return an AuditConfig with trusted_source=False."""
    from layer4_agents.agents.audit_orchestrator.api import _build_config
    from layer4_agents.agents.audit_orchestrator.models import AuditTriggerRequest

    req = AuditTriggerRequest(repo_url="https://github.com/owner/repo.git")
    cfg = _build_config(req)
    assert cfg.trusted_source is False
    assert cfg.repo_url == "https://github.com/owner/repo.git"

