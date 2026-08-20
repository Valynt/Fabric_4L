"""FastAPI router for the AuditOrchestrator agent.

Exposes endpoints to trigger audits, query runs, scorecards, findings, and
sprints, and to receive GitHub webhook events. Persistence uses the shared
``PersistenceManager`` with a JSON-file fallback so the router can be tested
without a live database.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import os
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from fastapi.responses import JSONResponse, PlainTextResponse
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_admin

from .config import ConfigManager
from .graph import run_audit_async
from .models import (
    AuditArea,
    AuditConfig,
    AuditRun,
    AuditRunDetail,
    AuditRunResponse,
    AuditRunSummary,
    AuditTriggerRequest,
    Finding,
    FindingStatus,
    FindingUpdate,
    ReportFormat,
    Scorecard,
    ScoreHistory,
    Severity,
    Sprint,
    validate_repo_url,
)
from .persistence import PersistenceManager, get_engine

try:  # pragma: no cover
    from prometheus_client import Counter, Gauge, Histogram

    _PROMETHEUS_AVAILABLE = True
except ImportError:  # pragma: no cover
    _PROMETHEUS_AVAILABLE = False

    class _FakeMetric:
        def __init__(self, *args: Any, **kwargs: Any) -> None:
            pass

        def inc(self, *args: Any, **kwargs: Any) -> None:
            pass

        def observe(self, *args: Any, **kwargs: Any) -> None:
            pass

        def set(self, *args: Any, **kwargs: Any) -> None:
            pass

        def labels(self, *args: Any, **kwargs: Any) -> _FakeMetric:
            return self

    Counter = Gauge = Histogram = _FakeMetric  # type: ignore[misc,assignment]


logger = logging.getLogger(__name__)
router = APIRouter()


# ---------------------------------------------------------------------------
# Prometheus metrics (no-op when prometheus_client is unavailable)
# ---------------------------------------------------------------------------

AUDIT_RUNS_TOTAL = Counter(
    "audit_runs_total",
    "Total audit runs",
    ["trigger_type", "status"],
)
AUDIT_DURATION = Histogram("audit_duration_seconds", "Audit run duration")
FINDINGS_TOTAL = Gauge(
    "audit_findings_total",
    "Current open findings",
    ["severity", "area"],
)
SCORE_OVERALL = Gauge("audit_score_overall", "Overall repository score")
SCORE_AREA = Gauge("audit_score_area", "Score by area", ["area"])


# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------


def _get_manager(fallback_dir: str = ".audit_cache/fallback") -> PersistenceManager:
    """Return a persistence manager using JSON fallback by default."""
    return PersistenceManager(fallback_dir=fallback_dir)


def get_manager() -> PersistenceManager:
    """FastAPI dependency providing a persistence manager.

    Uses the resolved audit configuration so API reads and the graph write to
    the same store. When ``AUDIT__POSTGRES_DSN`` (or a YAML config DSN) is set
    PostgreSQL is used; otherwise the JSON fallback under the configured cache
    directory is used.

    PostgreSQL engines are cached per DSN by :func:`get_engine`, so constructing
    this dependency on every request does not recreate the connection pool.
    """
    config = ConfigManager().load_or_default(
        overrides={
            "repo_url": "https://github.com/unknown/unknown",
            "repo_name": "unknown/unknown",
        }
    )
    if config.postgres_dsn:
        # Warm the module-level engine cache so the manager shares the pool.
        get_engine(config.postgres_dsn)
    return PersistenceManager(
        postgres_dsn=config.postgres_dsn,
        fallback_dir=config.cache_dir,
    )


def _build_config(request: AuditTriggerRequest) -> AuditConfig:
    """Merge request overrides with configuration defaults.

    API-originated audit requests are never allowed to execute in trusted-source
    local filesystem mode.
    """
    from .persistence import _repo_name_from_git_url

    config_manager = ConfigManager()
    overrides: dict[str, Any] = {
        "trusted_source": False,
    }

    if request.repo_url is not None:
        overrides["repo_url"] = request.repo_url
    if request.branch is not None:
        overrides["branch"] = request.branch
    if request.incremental is not None:
        overrides["incremental"] = request.incremental
    if request.areas is not None:
        overrides["areas_enabled"] = request.areas

    # repo_name is required; derive it from the URL when missing.
    if not overrides.get("repo_name") and overrides.get("repo_url"):
        overrides["repo_name"] = _repo_name_from_git_url(overrides["repo_url"])

    config = config_manager.load_or_default(overrides=overrides)
    config.trusted_source = False

    if not config.repo_name or config.repo_name.strip() == "":
        config.repo_name = _repo_name_from_git_url(config.repo_url)

    return config


async def _background_run_async(
    config: AuditConfig,
    trigger_type: str,
    previous_run_id: str | None,
    run_id: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """Run an audit asynchronously and persist a failure record on error."""
    started_at = datetime.now(UTC)
    actual_run_id = run_id or str(uuid4())
    try:
        await run_audit_async(config, trigger_type, previous_run_id, actual_run_id, tenant_id)
    except Exception as exc:
        logger.exception("Background audit run failed")
        try:
            manager = PersistenceManager(
                postgres_dsn=config.postgres_dsn,
                fallback_dir=config.cache_dir,
            )
            failed_run = AuditRun(
                id=actual_run_id,
                status="failed",
                trigger_type=trigger_type,
                started_at=started_at,
                completed_at=datetime.now(UTC),
                repo_path=config.repo_name,
                error_message=str(exc),
                previous_run_id=previous_run_id,
                tenant_id=tenant_id,
            )
            await manager.save_run(failed_run, tenant_id=tenant_id)
        except Exception:
            logger.exception("Failed to persist failed audit run")


def _background_run(
    config: AuditConfig,
    trigger_type: str,
    previous_run_id: str | None,
    run_id: str | None = None,
    tenant_id: str | None = None,
) -> None:
    """Synchronous wrapper that runs the async background task in one event loop."""
    asyncio.run(_background_run_async(config, trigger_type, previous_run_id, run_id, tenant_id))


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/run", response_model=AuditRunResponse)
async def trigger_audit(
    request: AuditTriggerRequest,
    context: RequestContext = Depends(require_tenant_admin),
) -> AuditRunResponse:
    """Trigger a new audit run. Returns a run ID immediately."""
    if not request.repo_url or not request.repo_url.strip():
        raise HTTPException(status_code=400, detail="repo_url is required")

    config = _build_config(request)
    config.tenant_id = str(context.tenant_id)

    if not config.repo_url or not config.repo_url.strip():
        raise HTTPException(status_code=400, detail="repo_url is required")

    trigger_type = request.trigger_type or "manual"
    run_id = str(uuid4())
    asyncio.create_task(
        _background_run_async(config, trigger_type, None, run_id, str(context.tenant_id))
    )

    if _PROMETHEUS_AVAILABLE:
        AUDIT_RUNS_TOTAL.labels(trigger_type=trigger_type, status="pending").inc()

    return AuditRunResponse(
        run_id=run_id,
        status="pending",
    )


@router.get("/runs/{run_id}", response_model=AuditRunDetail)
async def get_audit_run(
    run_id: str,
    manager: PersistenceManager = Depends(get_manager),
    context: RequestContext = Depends(require_tenant_admin),
) -> AuditRunDetail:
    """Get the status and results of a single audit run."""
    tenant_id = str(context.tenant_id)
    run = await manager.get_run(run_id, tenant_id=tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Audit run not found")

    scorecard = run.scorecard
    repo_name = scorecard.repo_name if scorecard else "unknown/repo"
    sprints = await manager.get_sprints(repo_name, tenant_id=tenant_id)
    return AuditRunDetail(
        run_id=run.id,
        status=run.status,
        trigger_type=run.trigger_type,
        repo_name=repo_name,
        branch=scorecard.branch if scorecard else "main",
        started_at=run.started_at,
        completed_at=run.completed_at,
        overall_score=scorecard.overall_score if scorecard else None,
        overall_grade=scorecard.overall_grade if scorecard else None,
        findings_count=len(scorecard.findings) if scorecard else 0,
        sprints_count=len(sprints),
        error_message=run.error_message,
        areas_reanalyzed=run.areas_reanalyzed,
        previous_run_id=run.previous_run_id,
    )


@router.get("/runs", response_model=list[AuditRunSummary])
async def list_audit_runs(
    repo: str,
    limit: int = Query(20, ge=1, le=100),
    manager: PersistenceManager = Depends(get_manager),
    context: RequestContext = Depends(require_tenant_admin),
) -> list[AuditRunSummary]:
    """List recent audit runs for a repository."""
    tenant_id = str(context.tenant_id)
    runs = await manager.list_runs(repo, limit=limit, tenant_id=tenant_id)
    return [
        AuditRunSummary(
            run_id=run.id,
            status=run.status,
            trigger_type=run.trigger_type,
            repo_name=run.scorecard.repo_name if run.scorecard else repo,
            branch=run.scorecard.branch if run.scorecard else "main",
            started_at=run.started_at,
            completed_at=run.completed_at,
            overall_score=run.scorecard.overall_score if run.scorecard else None,
            overall_grade=run.scorecard.overall_grade if run.scorecard else None,
            findings_count=len(run.scorecard.findings) if run.scorecard else 0,
        )
        for run in runs
    ]


@router.get("/scorecard/latest", response_model=Scorecard)
async def get_latest_scorecard(
    repo: str,
    manager: PersistenceManager = Depends(get_manager),
    context: RequestContext = Depends(require_tenant_admin),
) -> Scorecard:
    """Return the latest scorecard for a repository."""
    tenant_id = str(context.tenant_id)
    scorecard = await manager.get_latest_scorecard(repo, tenant_id=tenant_id)
    if scorecard is None:
        raise HTTPException(status_code=404, detail="No scorecard found for repository")
    return scorecard


@router.get("/scorecard/history", response_model=ScoreHistory)
async def get_score_history(
    repo: str,
    area: AuditArea | None = None,
    manager: PersistenceManager = Depends(get_manager),
    context: RequestContext = Depends(require_tenant_admin),
) -> ScoreHistory:
    """Return score history over time for a repository."""
    tenant_id = str(context.tenant_id)
    return await manager.get_score_history(repo, area=area, tenant_id=tenant_id)


@router.get("/findings", response_model=list[Finding])
async def list_findings(
    repo: str,
    status: FindingStatus | None = None,
    severity: Severity | None = None,
    area: AuditArea | None = None,
    manager: PersistenceManager = Depends(get_manager),
    context: RequestContext = Depends(require_tenant_admin),
) -> list[Finding]:
    """List findings for a repository, filtered by status, severity, and area."""
    tenant_id = str(context.tenant_id)
    findings = await manager.list_findings(
        repo, status=status, severity=severity, area=area, tenant_id=tenant_id
    )
    return findings


@router.patch("/findings/{finding_id}", response_model=Finding)
async def update_finding(
    finding_id: str,
    update: FindingUpdate,
    repo: str,
    manager: PersistenceManager = Depends(get_manager),
    context: RequestContext = Depends(require_tenant_admin),
) -> Finding:
    """Update a finding's status, owner, sprint, or resolution note.

    The ``repo`` query parameter scopes the update to a single repository and
    prevents accidental cross-repo modifications.
    """
    tenant_id = str(context.tenant_id)
    updated = await manager.update_finding(
        finding_id, update, repo=repo, tenant_id=tenant_id
    )
    if updated is None:
        raise HTTPException(status_code=404, detail="Finding not found")
    return updated


@router.get("/sprints", response_model=list[Sprint])
async def get_sprint_plan(
    repo: str,
    manager: PersistenceManager = Depends(get_manager),
    context: RequestContext = Depends(require_tenant_admin),
) -> list[Sprint]:
    """Return the current sprint plan for a repository."""
    tenant_id = str(context.tenant_id)
    return await manager.get_sprints(repo, tenant_id=tenant_id)


@router.get(
    "/report/{run_id}",
    response_model=None,
    responses={
        200: {
            "description": "Audit report as Markdown or JSON",
            "content": {
                "text/markdown": {"schema": {"type": "string"}},
                "application/json": {"schema": {"type": "object"}},
            },
        }
    },
)
async def get_report(
    run_id: str,
    format: ReportFormat = ReportFormat.MARKDOWN,
    manager: PersistenceManager = Depends(get_manager),
    context: RequestContext = Depends(require_tenant_admin),
) -> PlainTextResponse | JSONResponse:
    """Download the audit report for a run as Markdown or JSON."""
    tenant_id = str(context.tenant_id)
    run = await manager.get_run(run_id, tenant_id=tenant_id)
    if run is None:
        raise HTTPException(status_code=404, detail="Audit run not found")

    if format == ReportFormat.MARKDOWN:
        if run.scorecard is None:
            raise HTTPException(status_code=404, detail="Scorecard not available")
        from .reporter import generate_full_report

        sprints = await manager.get_sprints(run.scorecard.repo_name, tenant_id=tenant_id)
        content = generate_full_report(run.scorecard, sprints)
        return PlainTextResponse(content=content, media_type="text/markdown")

    # JSON format returns the scorecard with sprint plan metadata.
    if run.scorecard is None:
        raise HTTPException(status_code=404, detail="Scorecard not available")
    sprints = await manager.get_sprints(run.scorecard.repo_name, tenant_id=tenant_id)
    return JSONResponse(
        content={
            "run_id": run_id,
            "repo": run.scorecard.repo_name,
            "scorecard": json.loads(run.scorecard.model_dump_json()),
            "sprints": [json.loads(s.model_dump_json()) for s in sprints],
        }
    )


@router.post("/webhook/github")
async def github_webhook(
    request: Request,
    tenant_id: str = Query(..., description="Tenant that owns the triggered audit run"),
) -> dict[str, str]:
    """Receive GitHub push/release webhooks and trigger audits after HMAC verification.

    The webhook URL must include ``?tenant_id=<tenant>`` so the resulting audit
    run is scoped to a tenant. Requests without ``tenant_id`` are rejected with
    a 400 error.
    """
    body = await request.body()
    signature = request.headers.get("x-hub-signature-256", "")

    secret = os.environ.get("GITHUB_WEBHOOK_SECRET", "")
    if secret:
        expected = (
            "sha256="
            + hmac.new(
                secret.encode("utf-8"),
                body,
                hashlib.sha256,
            ).hexdigest()
        )
        if not hmac.compare_digest(expected, signature):
            raise HTTPException(status_code=403, detail="Invalid webhook signature")
    elif os.environ.get("DEV_WEBHOOK_UNSAFE", "").lower() not in (
        "true",
        "1",
        "yes",
        "on",
    ):
        # Fail closed: unsigned webhooks are rejected unless an explicit dev flag
        # is set. Never enable DEV_WEBHOOK_UNSAFE in production.
        raise HTTPException(
            status_code=401,
            detail="Missing webhook signature",
        )
    else:
        logger.warning("DEV_WEBHOOK_UNSAFE is set; accepting unsigned GitHub webhook")

    try:
        payload = json.loads(body.decode("utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid JSON payload") from exc

    event_type = request.headers.get("x-github-event", "")
    ref = payload.get("ref", "")
    repo_url = payload.get("repository", {}).get("clone_url", "")
    repo_name = payload.get("repository", {}).get("full_name", "")

    trigger_type = "webhook"
    should_trigger = False

    if event_type == "push" and ref.startswith("refs/heads/"):
        should_trigger = True
    elif event_type in {"release", "released"}:
        should_trigger = True
        trigger_type = "post_merge"

    if should_trigger and repo_url:
        try:
            validate_repo_url(repo_url)
        except ValueError as exc:
            raise HTTPException(
                status_code=400,
                detail="Invalid repository URL in webhook payload",
            ) from exc

        config_manager = ConfigManager()
        config = config_manager.load_or_default(
            overrides={"repo_url": repo_url, "repo_name": repo_name, "trusted_source": False}
        )
        config.trusted_source = False
        config.tenant_id = tenant_id
        asyncio.create_task(
            _background_run_async(config, trigger_type, None, None, tenant_id)
        )

        if _PROMETHEUS_AVAILABLE:
            AUDIT_RUNS_TOTAL.labels(trigger_type=trigger_type, status="pending").inc()

    return {"status": "accepted"}
