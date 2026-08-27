"""Persistence layer for the AuditOrchestrator agent.

Provides SQLAlchemy 2.0 async ORM models for PostgreSQL, an optional Neo4j
knowledge-graph writer, and a JSON-file fallback used when no database DSN is
configured or the database is unreachable.

The module can be imported without a live database; all SQLAlchemy and Neo4j
imports are guarded so lightweight tests do not require those packages.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import shutil
import subprocess
import tempfile
from collections.abc import AsyncGenerator, Callable, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import (
    AreaScore,
    AuditArea,
    AuditRun,
    Confidence,
    Finding,
    FindingStatus,
    FindingUpdate,
    Scorecard,
    ScoreHistory,
    ScoreHistoryEntry,
    Severity,
    Sprint,
    SprintStatus,
)

# ---------------------------------------------------------------------------
# Lazy, guarded imports for heavy persistence drivers
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

_SQLALCHEMY_AVAILABLE = False
_NEO4J_AVAILABLE = False

try:  # pragma: no cover
    from sqlalchemy import (
        JSON,
        DateTime,
        ForeignKey,
        String,
        delete,
        distinct,
        select,
    )
    from sqlalchemy.ext.asyncio import (
        AsyncEngine,
        AsyncSession,
        async_sessionmaker,
        create_async_engine,
    )
    from sqlalchemy.orm import (
        DeclarativeBase,
        Mapped,
        mapped_column,
        relationship,
    )

    _SQLALCHEMY_AVAILABLE = True
except ImportError:  # pragma: no cover
    pass

try:  # pragma: no cover
    from neo4j import AsyncGraphDatabase

    _NEO4J_AVAILABLE = True
except ImportError:  # pragma: no cover
    AsyncGraphDatabase = None  # type: ignore[misc,assignment,no-redef]


# Module-level cache for async SQLAlchemy engines keyed by DSN.
# Engines are long-lived and reused across PersistenceManager instances so
# the manager remains lightweight to construct on every API request.
_engine_cache: dict[str, AsyncEngine] = {}


def _is_in_memory_sqlite(dsn: str) -> bool:
    """Return True when the DSN targets an in-memory SQLite database."""
    return ":memory:" in dsn


def get_engine(dsn: str) -> AsyncEngine:
    """Return a cached async engine for the given DSN, creating it if needed.

    Engines are intentionally cached by DSN so that repeated
    ``PersistenceManager`` constructions reuse the same connection pool.
    In-memory SQLite databases are never cached, because each such engine
    owns a distinct, ephemeral database and sharing one would leak state
    across tests or requests.

    Callers are responsible for disposing engines at application shutdown.
    """
    if not _is_in_memory_sqlite(dsn) and dsn in _engine_cache:
        return _engine_cache[dsn]

    if not _SQLALCHEMY_AVAILABLE:  # pragma: no cover
        raise RuntimeError("SQLAlchemy is required when using PostgreSQL persistence")

    engine = create_async_engine(dsn, pool_pre_ping=True, future=True)
    if not _is_in_memory_sqlite(dsn):
        _engine_cache[dsn] = engine
    return engine


def clear_engine_cache() -> None:
    """Clear the module-level engine cache.

    Useful in tests to guarantee a fresh engine (and therefore a fresh
    connection pool) between test cases.
    """
    _engine_cache.clear()


# ---------------------------------------------------------------------------
# SQLAlchemy declarative base and ORM models (SPEC Section 9.1)
# ---------------------------------------------------------------------------

if _SQLALCHEMY_AVAILABLE:

    class Base(DeclarativeBase):  # type: ignore[valid-type,misc]
        """Shared declarative base for audit persistence models."""

        pass

    class AuditRunDB(Base):  # type: ignore[valid-type,misc]
        """Persisted audit execution run."""

        __tablename__ = "audit_runs"

        id: Mapped[str] = mapped_column(String(36), primary_key=True)
        tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
        branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
        commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
        version: Mapped[str | None] = mapped_column(String(50), nullable=True)
        trigger_type: Mapped[str] = mapped_column(String(50), nullable=False)
        status: Mapped[str] = mapped_column(String(50), nullable=False)
        started_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
        completed_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
        overall_score: Mapped[int | None] = mapped_column(nullable=True)
        overall_grade: Mapped[str | None] = mapped_column(String(5), nullable=True)
        error_message: Mapped[str | None] = mapped_column(nullable=True)
        report_path: Mapped[str | None] = mapped_column(nullable=True)
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=lambda: datetime.now(UTC)
        )
        # Incremental audit tracking
        previous_run_id: Mapped[str | None] = mapped_column(String(36), nullable=True)
        files_changed_since_last: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
        areas_reanalyzed: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)

        findings: Mapped[list[FindingDB]] = relationship(
            "FindingDB",
            secondary="finding_occurrences",
            viewonly=True,
        )

    class FindingDB(Base):  # type: ignore[valid-type,misc]
        """Deduplicated audit finding persisted across runs."""

        __tablename__ = "findings"

        id: Mapped[str] = mapped_column(String(50), primary_key=True)
        tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        first_seen_run_id: Mapped[str | None] = mapped_column(
            ForeignKey("audit_runs.id"), nullable=True
        )
        severity: Mapped[str] = mapped_column(String(20), nullable=False)
        confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
        area: Mapped[str] = mapped_column(String(255), nullable=False)
        evidence: Mapped[str | None] = mapped_column(nullable=True)
        observed_fact: Mapped[str | None] = mapped_column(nullable=True)
        inference_risk: Mapped[str | None] = mapped_column(nullable=True)
        business_impact: Mapped[str | None] = mapped_column(nullable=True)
        recommended_fix: Mapped[str | None] = mapped_column(nullable=True)
        effort: Mapped[str | None] = mapped_column(String(10), nullable=True)
        risk_of_change: Mapped[str | None] = mapped_column(String(20), nullable=True)
        owner: Mapped[str | None] = mapped_column(String(255), nullable=True)
        target_sprint: Mapped[int] = mapped_column(default=0)
        status: Mapped[str] = mapped_column(String(20), default="open")
        created_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=lambda: datetime.now(UTC)
        )
        resolved_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        resolution_note: Mapped[str | None] = mapped_column(nullable=True)
        # Extra fields from the Pydantic Finding model required for round-trips.
        first_seen_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=lambda: datetime.now(UTC)
        )
        last_seen_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=lambda: datetime.now(UTC)
        )
        times_seen: Mapped[int] = mapped_column(default=1)
        analyzer_type: Mapped[str] = mapped_column(String(50), nullable=False, default="code")
        check_command: Mapped[str | None] = mapped_column(nullable=True)
        check_output: Mapped[str | None] = mapped_column(nullable=True)

    class FindingOccurrenceDB(Base):  # type: ignore[valid-type,misc]
        """Per-run evidence that a finding was checked."""

        __tablename__ = "finding_occurrences"

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        run_id: Mapped[str] = mapped_column(
            ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False
        )
        finding_id: Mapped[str] = mapped_column(
            ForeignKey("findings.id", ondelete="CASCADE"), nullable=False
        )
        still_present: Mapped[bool] = mapped_column(nullable=False, default=True)
        evidence_at_time: Mapped[str | None] = mapped_column(nullable=True)
        checked_at: Mapped[datetime] = mapped_column(
            DateTime(timezone=True), default=lambda: datetime.now(UTC)
        )

    class ScorecardDB(Base):  # type: ignore[valid-type,misc]
        """Persisted repository scorecard."""

        __tablename__ = "scorecards"

        id: Mapped[str] = mapped_column(String(36), primary_key=True)
        tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        run_id: Mapped[str] = mapped_column(
            ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False
        )
        repo_name: Mapped[str] = mapped_column(String(255), nullable=False)
        branch: Mapped[str] = mapped_column(String(255), nullable=False, default="main")
        commit_sha: Mapped[str | None] = mapped_column(String(40), nullable=True)
        version: Mapped[str | None] = mapped_column(String(50), nullable=True)
        overall_score: Mapped[int] = mapped_column(nullable=False)
        overall_grade: Mapped[str] = mapped_column(String(5), nullable=False)
        confidence: Mapped[str] = mapped_column(String(20), nullable=False, default="medium")
        trend: Mapped[str | None] = mapped_column(String(50), nullable=True)
        executive_summary: Mapped[str | None] = mapped_column(nullable=True)
        total_files: Mapped[int] = mapped_column(default=0)
        total_directories: Mapped[int] = mapped_column(default=0)
        total_commits: Mapped[int] = mapped_column(default=0)
        total_contributors: Mapped[int] = mapped_column(default=0)
        git_metric_completeness: Mapped[dict[str, Any] | None] = mapped_column(
            JSON, nullable=True, default=None
        )
        git_warnings: Mapped[list[Any] | None] = mapped_column(JSON, nullable=True, default=None)
        audit_timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

        area_scores: Mapped[list[AreaScoreDB]] = relationship(
            "AreaScoreDB",
            back_populates="scorecard",
            cascade="all, delete-orphan",
        )

    class AreaScoreDB(Base):  # type: ignore[valid-type,misc]
        """Persisted area score belonging to a scorecard."""

        __tablename__ = "area_scores"

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        scorecard_id: Mapped[str] = mapped_column(
            ForeignKey("scorecards.id", ondelete="CASCADE"), nullable=False
        )
        area: Mapped[str] = mapped_column(String(255), nullable=False)
        weight: Mapped[float] = mapped_column(nullable=False)
        score: Mapped[int] = mapped_column(nullable=False)
        grade: Mapped[str | None] = mapped_column(String(5), nullable=True)
        confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
        trend_risk: Mapped[str | None] = mapped_column(String(50), nullable=True)
        diagnosis: Mapped[str | None] = mapped_column(nullable=True)
        findings_count: Mapped[int] = mapped_column(default=0)

        scorecard: Mapped[ScorecardDB] = relationship("ScorecardDB", back_populates="area_scores")

    class SprintDB(Base):  # type: ignore[valid-type,misc]
        """Persisted remediation sprint."""

        __tablename__ = "sprints"

        id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
        tenant_id: Mapped[str | None] = mapped_column(String(255), nullable=True)
        run_id: Mapped[str] = mapped_column(
            ForeignKey("audit_runs.id", ondelete="CASCADE"), nullable=False
        )
        sprint_number: Mapped[int] = mapped_column(nullable=False)
        theme: Mapped[str] = mapped_column(String(255), nullable=False)
        objectives: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
        deliverables: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
        findings_targeted: Mapped[list[str] | None] = mapped_column(JSON, nullable=True)
        status: Mapped[str] = mapped_column(String(20), default="planned")
        started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
        completed_at: Mapped[datetime | None] = mapped_column(
            DateTime(timezone=True), nullable=True
        )
        score_impact_projected: Mapped[int | None] = mapped_column(nullable=True)
        score_impact_actual: Mapped[int | None] = mapped_column(nullable=True)

else:  # pragma: no cover
    # Stubs so the module remains importable when SQLAlchemy is absent.
    Base = None  # type: ignore[misc,assignment,no-redef]
    AuditRunDB = Any  # type: ignore[misc,assignment,no-redef]
    FindingDB = Any  # type: ignore[misc,assignment,no-redef]
    FindingOccurrenceDB = Any  # type: ignore[misc,assignment,no-redef]
    ScorecardDB = Any  # type: ignore[misc,assignment,no-redef]
    AreaScoreDB = Any  # type: ignore[misc,assignment,no-redef]
    SprintDB = Any  # type: ignore[misc,assignment,no-redef]


# ---------------------------------------------------------------------------
# JSON serialization helpers
# ---------------------------------------------------------------------------


def _isoformat(dt: datetime | None) -> str | None:
    """Return ISO 8601 string for a datetime, or None."""
    return dt.isoformat() if dt else None


def _parse_datetime(value: str | None) -> datetime | None:
    """Parse an ISO 8601 string into a timezone-aware datetime."""
    if value is None:
        return None
    dt = datetime.fromisoformat(value)
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=UTC)
    return dt


def _git_metadata_to_json(scorecard: Scorecard) -> dict[str, Any]:
    """Serialize git completeness/warning metadata to JSON-safe plain dicts.

    ``Scorecard.git_metric_completeness`` and ``git_warnings`` hold Pydantic
    models; convert them to plain dicts so SQLAlchemy ``JSON`` columns and the
    fallback ``json.dump`` can round-trip them losslessly.
    """
    return {
        "git_metric_completeness": {
            k: _as_json_dict(v)
            for k, v in (scorecard.git_metric_completeness or {}).items()
        },
        "git_warnings": [_as_json_dict(w) for w in (scorecard.git_warnings or [])],
    }


def _as_json_dict(value: Any) -> Any:
    """Return a JSON-safe value, dumping Pydantic models attrs when present."""
    if isinstance(value, dict):
        return value
    dump = getattr(value, "model_dump", None)
    if callable(dump):
        return dump(mode="json")
    return value


def _scorecard_to_dict(scorecard: Scorecard, run_id: str) -> dict[str, Any]:
    """Serialize a scorecard and its area scores for fallback storage."""
    git_meta = _git_metadata_to_json(scorecard)
    return {
        "id": scorecard.id,
        "run_id": run_id,
        "tenant_id": scorecard.tenant_id,
        "repo_name": scorecard.repo_name,
        "branch": scorecard.branch,
        "commit_sha": scorecard.commit_sha,
        "version": scorecard.version,
        "overall_score": scorecard.overall_score,
        "overall_grade": scorecard.overall_grade,
        "confidence": scorecard.confidence.value,
        "trend": scorecard.trend,
        "total_files": scorecard.total_files,
        "total_directories": scorecard.total_directories,
        "total_commits": scorecard.total_commits,
        "total_contributors": scorecard.total_contributors,
        "git_metric_completeness": git_meta["git_metric_completeness"],
        "git_warnings": git_meta["git_warnings"],
        "audit_timestamp": _isoformat(scorecard.audit_timestamp),
        "executive_summary": scorecard.executive_summary,
        "area_scores": [
            {
                "area": a.area.value,
                "weight": a.weight,
                "score": a.score,
                "grade": a.grade,
                "confidence": a.confidence.value,
                "trend_risk": a.trend_risk,
                "diagnosis": a.diagnosis,
                "findings_count": a.findings_count,
            }
            for a in scorecard.area_scores
        ],
    }


def _scorecard_from_dict(data: dict[str, Any], findings: list[Finding]) -> Scorecard:
    """Reconstruct a Scorecard from fallback storage."""
    return Scorecard(
        id=data["id"],
        repo_name=data["repo_name"],
        branch=data.get("branch", "main"),
        commit_sha=data.get("commit_sha"),
        version=data.get("version"),
        overall_score=data["overall_score"],
        overall_grade=data["overall_grade"],
        confidence=Confidence(data.get("confidence", "medium")),
        trend=data.get("trend", "Stable"),
        area_scores=[
            AreaScore(
                area=AuditArea(a["area"]),
                weight=a["weight"],
                score=a["score"],
                grade=a["grade"],
                confidence=Confidence(a.get("confidence", "medium")),
                trend_risk=a.get("trend_risk", "Stable"),
                diagnosis=a.get("diagnosis", ""),
                findings_count=a.get("findings_count", 0),
            )
            for a in data.get("area_scores", [])
        ],
        total_files=data.get("total_files", 0),
        total_directories=data.get("total_directories", 0),
        total_commits=data.get("total_commits", 0),
        total_contributors=data.get("total_contributors", 0),
        git_metric_completeness=dict(data.get("git_metric_completeness", {}) or {}),
        git_warnings=list(data.get("git_warnings", []) or []),
        audit_timestamp=_parse_datetime(data["audit_timestamp"]) or datetime.now(UTC),
        findings=findings,
        executive_summary=data.get("executive_summary"),
        tenant_id=data.get("tenant_id"),
    )


def _finding_to_dict(finding: Finding) -> dict[str, Any]:
    """Serialize a finding for fallback storage."""
    return {
        "id": finding.id,
        "tenant_id": finding.tenant_id,
        "severity": finding.severity.value,
        "confidence": finding.confidence.value,
        "area": finding.area.value,
        "evidence": finding.evidence,
        "observed_fact": finding.observed_fact,
        "inference_risk": finding.inference_risk,
        "business_impact": finding.business_impact,
        "recommended_fix": finding.recommended_fix,
        "effort": finding.effort,
        "risk_of_change": finding.risk_of_change,
        "owner": finding.owner,
        "target_sprint": finding.target_sprint,
        "status": finding.status.value,
        "created_at": _isoformat(finding.created_at),
        "resolved_at": _isoformat(finding.resolved_at),
        "resolution_note": finding.resolution_note,
        "first_seen_at": _isoformat(finding.first_seen_at),
        "last_seen_at": _isoformat(finding.last_seen_at),
        "times_seen": finding.times_seen,
        "analyzer_type": finding.analyzer_type,
        "check_command": finding.check_command,
        "check_output": finding.check_output,
    }


def _finding_from_dict(data: dict[str, Any]) -> Finding:
    """Reconstruct a Finding from fallback storage."""
    return Finding(
        id=data["id"],
        severity=Severity(data["severity"]),
        confidence=Confidence(data.get("confidence", "medium")),
        area=AuditArea(data["area"]),
        evidence=data.get("evidence", ""),
        observed_fact=data.get("observed_fact", ""),
        inference_risk=data.get("inference_risk", ""),
        business_impact=data.get("business_impact", ""),
        recommended_fix=data.get("recommended_fix", ""),
        effort=data.get("effort", "S"),
        risk_of_change=data.get("risk_of_change", "Low"),
        owner=data.get("owner", ""),
        target_sprint=data.get("target_sprint", 0),
        status=FindingStatus(data.get("status", "open")),
        created_at=_parse_datetime(data.get("created_at")) or datetime.now(UTC),
        resolved_at=_parse_datetime(data.get("resolved_at")),
        resolution_note=data.get("resolution_note"),
        first_seen_at=_parse_datetime(data.get("first_seen_at")) or datetime.now(UTC),
        last_seen_at=_parse_datetime(data.get("last_seen_at")) or datetime.now(UTC),
        times_seen=data.get("times_seen", 1),
        analyzer_type=data.get("analyzer_type", "code"),
        check_command=data.get("check_command"),
        check_output=data.get("check_output"),
        tenant_id=data.get("tenant_id"),
    )


def _sprint_to_dict(sprint: Sprint) -> dict[str, Any]:
    """Serialize a sprint for fallback storage."""
    return {
        "id": sprint.id,
        "tenant_id": sprint.tenant_id,
        "theme": sprint.theme,
        "objectives": sprint.objectives,
        "deliverables": sprint.deliverables,
        "findings_targeted": sprint.findings_targeted,
        "status": sprint.status.value,
        "started_at": _isoformat(sprint.started_at),
        "completed_at": _isoformat(sprint.completed_at),
        "actual_effort_days": sprint.actual_effort_days,
        "score_impact_projected": sprint.score_impact_projected,
        "score_impact_actual": sprint.score_impact_actual,
    }


def _sprint_from_dict(data: dict[str, Any]) -> Sprint:
    """Reconstruct a Sprint from fallback storage."""
    return Sprint(
        id=data["id"],
        theme=data["theme"],
        objectives=data.get("objectives", []),
        deliverables=data.get("deliverables", []),
        findings_targeted=data.get("findings_targeted", []),
        status=SprintStatus(data.get("status", "planned")),
        started_at=_parse_datetime(data.get("started_at")),
        completed_at=_parse_datetime(data.get("completed_at")),
        actual_effort_days=data.get("actual_effort_days"),
        score_impact_projected=data.get("score_impact_projected", 0),
        score_impact_actual=data.get("score_impact_actual"),
        tenant_id=data.get("tenant_id"),
    )


def _run_to_dict(run: AuditRun) -> dict[str, Any]:
    """Serialize an audit run for fallback storage."""
    return {
        "id": run.id,
        "tenant_id": run.tenant_id,
        "status": run.status,
        "trigger_type": run.trigger_type,
        "started_at": _isoformat(run.started_at),
        "completed_at": _isoformat(run.completed_at),
        "repo_path": run.repo_path,
        "error_message": run.error_message,
        "previous_run_id": run.previous_run_id,
        "files_changed_since_last": run.files_changed_since_last,
        "areas_reanalyzed": run.areas_reanalyzed,
    }


def _run_from_dict_with_repo(data: dict[str, Any], repo_name: str) -> AuditRun:
    """Reconstruct an AuditRun from fallback storage, attaching repo metadata."""
    return AuditRun(
        id=data["id"],
        status=data.get("status", "unknown"),
        trigger_type=data.get("trigger_type", "manual"),
        started_at=_parse_datetime(data.get("started_at")) or datetime.now(UTC),
        completed_at=_parse_datetime(data.get("completed_at")),
        repo_path=data.get("repo_path", ""),
        error_message=data.get("error_message"),
        previous_run_id=data.get("previous_run_id"),
        files_changed_since_last=data.get("files_changed_since_last", []),
        areas_reanalyzed=data.get("areas_reanalyzed", []),
        tenant_id=data.get("tenant_id"),
    )


def _run_from_db_with_scorecard(row: AuditRunDB, scorecard: Scorecard | None) -> AuditRun:
    """Reconstruct an AuditRun from a DB row, optionally attaching its scorecard."""
    return AuditRun(
        id=row.id,
        status=row.status,
        trigger_type=row.trigger_type,
        started_at=row.started_at or datetime.now(UTC),
        completed_at=row.completed_at,
        repo_path=scorecard.repo_name if scorecard else row.repo_name,
        scorecard=scorecard,
        error_message=row.error_message,
        previous_run_id=row.previous_run_id,
        files_changed_since_last=row.files_changed_since_last or [],
        areas_reanalyzed=row.areas_reanalyzed or [],
        tenant_id=row.tenant_id,
    )


def _repo_name_from_git_url(url: str) -> str:
    """Extract owner/repo from a git remote URL.

    Supports SSH (``git@host:owner/repo.git``), HTTPS
    (``https://host/owner/repo.git``), and file paths.
    """
    if url.startswith("git@"):
        path_part = url.split(":", 1)[-1]
    else:
        # https://host/path/to/repo.git -> path/to/repo.git
        path_part = url.split("://", 1)[-1].split("/", 1)[-1]
    path_part = path_part.removesuffix(".git").strip("/")
    parts = [p for p in path_part.split("/") if p]
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    return path_part or "unknown/repo"


def _repo_name_from_path(repo_path: str) -> str:
    """Derive a repo name from a local path for runs without a scorecard.

    Heuristic:
      1. If ``repo_path`` points to a git directory (contains ``.git`` or ends
         with ``.git``), attempt to read the ``origin`` remote URL and return
         ``owner/repo`` from it.
      2. For local paths with at least two trailing components, use the last
         two directories as ``owner/repo``.
      3. Otherwise use the directory name.
      4. Fall back to ``"unknown/repo"``.
    """
    path = Path(repo_path).resolve()
    if (path / ".git").is_dir() or path.suffix == ".git":
        git_dir = path if (path / ".git").is_dir() else path.parent
        try:
            result = subprocess.run(
                ["git", "-C", str(git_dir), "remote", "get-url", "origin"],
                capture_output=True,
                text=True,
                check=False,
                timeout=5,
            )
            url = result.stdout.strip()
            if url:
                return _repo_name_from_git_url(url)
        except Exception:  # pragma: no cover
            pass
    parts = [
        p
        for p in path.parts
        if p not in ("", "/", "\\") and not p.endswith(":\\") and not p.endswith(":")
    ]
    if len(parts) >= 2:
        return f"{parts[-2]}/{parts[-1]}"
    if parts:
        return parts[-1]
    return "unknown/repo"


# ---------------------------------------------------------------------------
# Database model conversion helpers
# ---------------------------------------------------------------------------


def _run_to_db(run: AuditRun) -> AuditRunDB:
    """Convert an AuditRun Pydantic model to a DB row."""
    repo_name = (
        run.scorecard.repo_name
        if run.scorecard is not None
        else _repo_name_from_path(run.repo_path)
    )
    return AuditRunDB(
        id=run.id,
        tenant_id=run.tenant_id,
        repo_name=repo_name,
        branch=run.scorecard.branch if run.scorecard else "main",
        commit_sha=run.scorecard.commit_sha if run.scorecard else None,
        version=run.scorecard.version if run.scorecard else None,
        trigger_type=run.trigger_type,
        status=run.status,
        started_at=run.started_at,
        completed_at=run.completed_at,
        overall_score=run.scorecard.overall_score if run.scorecard else None,
        overall_grade=run.scorecard.overall_grade if run.scorecard else None,
        error_message=run.error_message,
        previous_run_id=run.previous_run_id,
        files_changed_since_last=run.files_changed_since_last or [],
        areas_reanalyzed=run.areas_reanalyzed or [],
    )


def _finding_to_db(finding: Finding, first_seen_run_id: str | None = None) -> FindingDB:
    """Convert a Finding Pydantic model to a DB row."""
    return FindingDB(
        id=finding.id,
        tenant_id=finding.tenant_id,
        first_seen_run_id=first_seen_run_id,
        severity=finding.severity.value,
        confidence=finding.confidence.value,
        area=finding.area.value,
        evidence=finding.evidence,
        observed_fact=finding.observed_fact,
        inference_risk=finding.inference_risk,
        business_impact=finding.business_impact,
        recommended_fix=finding.recommended_fix,
        effort=finding.effort,
        risk_of_change=finding.risk_of_change,
        owner=finding.owner,
        target_sprint=finding.target_sprint,
        status=finding.status.value,
        created_at=finding.created_at,
        resolved_at=finding.resolved_at,
        resolution_note=finding.resolution_note,
        first_seen_at=finding.first_seen_at,
        last_seen_at=finding.last_seen_at,
        times_seen=finding.times_seen,
        analyzer_type=finding.analyzer_type,
        check_command=finding.check_command,
        check_output=finding.check_output,
    )


def _finding_from_db(row: FindingDB) -> Finding:
    """Reconstruct a Finding from a DB row."""
    return Finding(
        id=row.id,
        severity=Severity(row.severity),
        confidence=Confidence(row.confidence),
        area=AuditArea(row.area),
        evidence=row.evidence or "",
        observed_fact=row.observed_fact or "",
        inference_risk=row.inference_risk or "",
        business_impact=row.business_impact or "",
        recommended_fix=row.recommended_fix or "",
        effort=row.effort or "S",
        risk_of_change=row.risk_of_change or "Low",
        owner=row.owner or "",
        target_sprint=row.target_sprint,
        status=FindingStatus(row.status),
        created_at=row.created_at or datetime.now(UTC),
        resolved_at=row.resolved_at,
        resolution_note=row.resolution_note,
        first_seen_at=row.first_seen_at or datetime.now(UTC),
        last_seen_at=row.last_seen_at or datetime.now(UTC),
        times_seen=row.times_seen,
        analyzer_type=row.analyzer_type,
        check_command=row.check_command,
        check_output=row.check_output,
        tenant_id=row.tenant_id,
    )


def _area_score_to_db(area: AreaScore, scorecard_id: str) -> AreaScoreDB:
    """Convert an AreaScore to a DB row."""
    return AreaScoreDB(
        scorecard_id=scorecard_id,
        area=area.area.value,
        weight=area.weight,
        score=area.score,
        grade=area.grade,
        confidence=area.confidence.value,
        trend_risk=area.trend_risk,
        diagnosis=area.diagnosis,
        findings_count=area.findings_count,
    )


def _area_score_from_db(row: AreaScoreDB) -> AreaScore:
    """Reconstruct an AreaScore from a DB row."""
    return AreaScore(
        area=AuditArea(row.area),
        weight=row.weight,
        score=row.score,
        grade=row.grade or "F",
        confidence=Confidence(row.confidence or "medium"),
        trend_risk=row.trend_risk or "Stable",
        diagnosis=row.diagnosis or "",
        findings_count=row.findings_count or 0,
    )


def _scorecard_to_db(scorecard: Scorecard, run_id: str) -> ScorecardDB:
    """Convert a Scorecard to a DB row (area scores attached via relationship)."""
    git_meta = _git_metadata_to_json(scorecard)
    db_scorecard = ScorecardDB(
        id=scorecard.id,
        tenant_id=scorecard.tenant_id,
        run_id=run_id,
        repo_name=scorecard.repo_name,
        branch=scorecard.branch,
        commit_sha=scorecard.commit_sha,
        version=scorecard.version,
        overall_score=scorecard.overall_score,
        overall_grade=scorecard.overall_grade,
        confidence=scorecard.confidence.value,
        trend=scorecard.trend,
        total_files=scorecard.total_files,
        total_directories=scorecard.total_directories,
        total_commits=scorecard.total_commits,
        total_contributors=scorecard.total_contributors,
        git_metric_completeness=git_meta["git_metric_completeness"] or None,
        git_warnings=git_meta["git_warnings"] or None,
        audit_timestamp=scorecard.audit_timestamp,
        executive_summary=scorecard.executive_summary,
    )
    db_scorecard.area_scores = [_area_score_to_db(a, scorecard.id) for a in scorecard.area_scores]
    return db_scorecard


def _scorecard_from_db(
    row: ScorecardDB,
    area_scores: Sequence[AreaScore],
    findings: Sequence[Finding],
) -> Scorecard:
    """Reconstruct a Scorecard from a DB row."""
    return Scorecard(
        id=row.id,
        repo_name=row.repo_name,
        branch=row.branch,
        commit_sha=row.commit_sha,
        version=row.version,
        overall_score=row.overall_score,
        overall_grade=row.overall_grade,
        confidence=Confidence(row.confidence or "medium"),
        trend=row.trend or "Stable",
        area_scores=list(area_scores),
        total_files=row.total_files or 0,
        total_directories=row.total_directories or 0,
        total_commits=row.total_commits or 0,
        total_contributors=row.total_contributors or 0,
        git_metric_completeness=dict(row.git_metric_completeness or {}),
        git_warnings=list(row.git_warnings or []),
        audit_timestamp=row.audit_timestamp,
        findings=list(findings),
        executive_summary=row.executive_summary,
        tenant_id=row.tenant_id,
    )


def _sprint_to_db(sprint: Sprint, run_id: str) -> SprintDB:
    """Convert a Sprint to a DB row."""
    return SprintDB(
        run_id=run_id,
        tenant_id=sprint.tenant_id,
        sprint_number=sprint.id,
        theme=sprint.theme,
        objectives=sprint.objectives,
        deliverables=sprint.deliverables,
        findings_targeted=sprint.findings_targeted,
        status=sprint.status.value,
        started_at=sprint.started_at,
        completed_at=sprint.completed_at,
        score_impact_projected=sprint.score_impact_projected,
        score_impact_actual=sprint.score_impact_actual,
    )


def _sprint_from_db(row: SprintDB) -> Sprint:
    """Reconstruct a Sprint from a DB row."""
    return Sprint(
        id=row.sprint_number,
        theme=row.theme,
        objectives=row.objectives or [],
        deliverables=row.deliverables or [],
        findings_targeted=row.findings_targeted or [],
        status=SprintStatus(row.status),
        started_at=row.started_at,
        completed_at=row.completed_at,
        score_impact_projected=row.score_impact_projected or 0,
        score_impact_actual=row.score_impact_actual,
        tenant_id=row.tenant_id,
    )


# ---------------------------------------------------------------------------
# Persistence manager
# ---------------------------------------------------------------------------


class PersistenceManager:
    """Async persistence manager for audit runs, findings, scorecards and sprints.

    Supports PostgreSQL via SQLAlchemy 2.0 async sessions and a JSON-file fallback
    when no database is configured. All queries are scoped by ``repo_name`` to
    prevent cross-repository data leaks.
    """

    def __init__(
        self,
        session_factory: Callable[[], AsyncSession] | async_sessionmaker | None = None,
        postgres_dsn: str | None = None,
        fallback_dir: str | Path = ".audit_cache/fallback",
        neo4j_uri: str | None = None,
        neo4j_user: str | None = None,
        neo4j_password: str | None = None,
    ) -> None:
        """Initialize the persistence manager.

        Args:
            session_factory: Existing async session factory or callable returning
                an ``AsyncSession``. Takes precedence over ``postgres_dsn``.
            postgres_dsn: PostgreSQL DSN used to create an internal engine and
                session factory when ``session_factory`` is not provided.
            fallback_dir: Directory for JSON fallback storage when no DB is
                configured.
            neo4j_uri: Optional Neo4j Bolt URI for knowledge-graph updates.
            neo4j_user: Optional Neo4j username.
            neo4j_password: Optional Neo4j password.
        """
        self._session_factory: Callable[[], AsyncSession] | async_sessionmaker[Any] | None

        if session_factory is not None:
            self._session_factory = session_factory
            self._engine: AsyncEngine | None = None
        elif postgres_dsn is not None:
            engine = get_engine(postgres_dsn)
            self._engine = engine
            self._session_factory = async_sessionmaker(
                bind=engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        else:
            self._session_factory = None
            self._engine = None

        self._fallback_dir = Path(fallback_dir)
        self._neo4j_uri = neo4j_uri
        self._neo4j_user = neo4j_user
        self._neo4j_password = neo4j_password

    @property
    def _use_fallback(self) -> bool:
        """Return True when the manager is operating in JSON fallback mode."""
        return self._session_factory is None

    @asynccontextmanager
    async def _session(self) -> AsyncGenerator[AsyncSession, None]:
        """Yield a managed DB session or raise if fallback mode is active.

        The session marks tenant context as established so that Layer 4's
        global before-flush listener does not abort the commit. Audit
        persistence does not rely on PostgreSQL RLS tenant isolation;
        repository scoping is enforced via ``repo_name`` query filters.
        """
        if self._session_factory is None:
            raise RuntimeError("No database session factory configured")
        session = self._session_factory()
        session.info["tenant_context_state"] = "set"
        session.info["tenant_context_value"] = "audit"
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()

    async def create_schema(self) -> None:
        """Create all audit persistence tables (idempotent).

        No-op in JSON fallback mode.
        """
        if self._engine is None or not _SQLALCHEMY_AVAILABLE:
            return
        async with self._engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)

    # -----------------------------------------------------------------------
    # Fallback helpers
    # -----------------------------------------------------------------------

    def _fallback_tenant_dir(self, tenant_id: str | None) -> Path:
        """Return the sanitized fallback directory for a tenant."""
        safe = tenant_id.replace("/", "__").replace("\\", "__") if tenant_id else "_default"
        return self._fallback_dir / safe

    def _fallback_repo_dir(self, tenant_id: str | None, repo_name: str) -> Path:
        """Return the sanitized fallback directory for a repository within a tenant."""
        safe = repo_name.replace("/", "__").replace("\\", "__")
        return self._fallback_tenant_dir(tenant_id) / safe

    def _atomic_write_json(self, path: Path, data: dict[str, Any]) -> None:
        """Write JSON atomically using a temp file and rename."""
        path.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp = tempfile.mkstemp(
            dir=path.parent,
            prefix=f".{path.stem}_",
            suffix=".tmp",
        )
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                json.dump(data, fh, indent=2, default=str)
        except Exception:
            Path(tmp).unlink(missing_ok=True)
            raise
        shutil.move(tmp, path)

    def _fallback_write_run(
        self, run: AuditRun, tenant_id: str | None, repo_name: str
    ) -> None:
        """Persist an audit run to the fallback store under its tenant/repo scope."""
        path = self._fallback_repo_dir(tenant_id, repo_name) / "runs" / f"{run.id}.json"
        self._atomic_write_json(path, _run_to_dict(run))

    def _fallback_write_findings(
        self,
        tenant_id: str | None,
        repo_name: str,
        run_id: str,
        findings: Sequence[Finding],
    ) -> None:
        """Persist findings to the fallback store, creating one file per finding.

        Existing findings have their ``times_seen`` count incremented and
        ``last_seen_at`` refreshed.
        """
        base = self._fallback_repo_dir(tenant_id, repo_name) / "findings"
        for finding in findings:
            path = base / f"{finding.id}.json"
            if path.exists():
                data = json.loads(path.read_text(encoding="utf-8"))
                data["times_seen"] = data.get("times_seen", 1) + 1
                data["last_seen_at"] = _isoformat(datetime.now(UTC))
                self._atomic_write_json(path, data)
            else:
                self._atomic_write_json(path, _finding_to_dict(finding))
        # Track occurrences per run.
        occurrences_path = (
            self._fallback_repo_dir(tenant_id, repo_name) / "occurrences" / f"{run_id}.json"
        )
        self._atomic_write_json(
            occurrences_path,
            {"run_id": run_id, "finding_ids": [f.id for f in findings]},
        )

    def _fallback_write_scorecard(
        self, scorecard: Scorecard, run_id: str, tenant_id: str | None
    ) -> None:
        """Persist a scorecard to the fallback store."""
        path = (
            self._fallback_repo_dir(tenant_id, scorecard.repo_name)
            / "scorecards"
            / f"{scorecard.id}.json"
        )
        self._atomic_write_json(path, _scorecard_to_dict(scorecard, run_id))

    def _fallback_write_sprints(
        self,
        tenant_id: str | None,
        repo_name: str,
        run_id: str,
        sprints: Sequence[Sprint],
    ) -> None:
        """Persist sprints to the fallback store, grouped by run."""
        path = self._fallback_repo_dir(tenant_id, repo_name) / "sprints" / f"{run_id}.json"
        self._atomic_write_json(
            path, {"run_id": run_id, "sprints": [_sprint_to_dict(s) for s in sprints]}
        )

    def _fallback_list_scorecards(
        self, tenant_id: str | None, repo_name: str
    ) -> list[tuple[datetime, dict[str, Any], Path]]:
        """Return all fallback scorecards for a repo with timestamps."""
        base = self._fallback_repo_dir(tenant_id, repo_name) / "scorecards"
        if not base.exists():
            return []
        results: list[tuple[datetime, dict[str, Any], Path]] = []
        for path in base.glob("*.json"):
            data = json.loads(path.read_text(encoding="utf-8"))
            ts = _parse_datetime(data.get("audit_timestamp"))
            if ts is None:
                ts = datetime.fromtimestamp(0, tz=UTC)
            results.append((ts, data, path))
        return results

    def _fallback_load_findings_for_run(
        self, tenant_id: str | None, repo_name: str, run_id: str
    ) -> list[Finding]:
        """Load findings associated with a specific run from the fallback store."""
        occ_path = self._fallback_repo_dir(tenant_id, repo_name) / "occurrences" / f"{run_id}.json"
        if not occ_path.exists():
            return []
        occ = json.loads(occ_path.read_text(encoding="utf-8"))
        findings: list[Finding] = []
        for fid in occ.get("finding_ids", []):
            fpath = self._fallback_repo_dir(tenant_id, repo_name) / "findings" / f"{fid}.json"
            if fpath.exists():
                findings.append(_finding_from_dict(json.loads(fpath.read_text(encoding="utf-8"))))
        return findings

    def _fallback_all_findings(self, tenant_id: str | None, repo_name: str) -> list[Finding]:
        """Load all findings for a repository from the fallback store."""
        base = self._fallback_repo_dir(tenant_id, repo_name) / "findings"
        if not base.exists():
            return []
        findings: list[Finding] = []
        for path in base.glob("*.json"):
            findings.append(_finding_from_dict(json.loads(path.read_text(encoding="utf-8"))))
        return findings

    # -----------------------------------------------------------------------
    # Public API
    # -----------------------------------------------------------------------

    async def save_run(
        self,
        audit_run: AuditRun,
        tenant_id: str | None = None,
    ) -> None:
        """Persist an audit run.

        When a database is configured the run is written to PostgreSQL;
        otherwise it is written to the JSON fallback store under the tenant/repo
        scope. If ``tenant_id`` is provided it is set on the run and its scorecard
        before persistence.
        """
        if tenant_id is not None:
            audit_run.tenant_id = tenant_id
            if audit_run.scorecard is not None:
                audit_run.scorecard.tenant_id = tenant_id

        repo_name = (
            audit_run.scorecard.repo_name
            if audit_run.scorecard is not None
            else _repo_name_from_path(audit_run.repo_path)
        )
        if self._use_fallback:
            self._fallback_write_run(audit_run, audit_run.tenant_id, repo_name)
            return

        async with self._session() as session:
            session.add(_run_to_db(audit_run))

    async def save_findings(
        self,
        run_id: str,
        findings: Sequence[Finding],
        repo_name: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Persist findings for a run, deduplicating by finding ID.

        Args:
            run_id: Audit run identifier.
            findings: Findings to persist.
            repo_name: Optional repo name override required by the JSON fallback
                store; ignored when a database is configured.
            tenant_id: Tenant that owns these findings. When provided it is set
                on each finding and used to scope fallback storage.
        """
        if not findings:
            return

        for finding in findings:
            if tenant_id is not None:
                finding.tenant_id = tenant_id

        if self._use_fallback:
            if repo_name is None:
                raise ValueError("repo_name is required for fallback persistence of findings")
            self._fallback_write_findings(tenant_id, repo_name, run_id, findings)
            return

        async with self._session() as session:
            for finding in findings:
                existing = await session.get(FindingDB, finding.id)
                if existing is not None:
                    existing.severity = finding.severity.value
                    existing.confidence = finding.confidence.value
                    existing.area = finding.area.value
                    existing.evidence = finding.evidence
                    existing.observed_fact = finding.observed_fact
                    existing.inference_risk = finding.inference_risk
                    existing.business_impact = finding.business_impact
                    existing.recommended_fix = finding.recommended_fix
                    existing.effort = finding.effort
                    existing.risk_of_change = finding.risk_of_change
                    existing.owner = finding.owner
                    existing.target_sprint = finding.target_sprint
                    existing.status = finding.status.value
                    existing.resolved_at = finding.resolved_at
                    existing.resolution_note = finding.resolution_note
                    existing.last_seen_at = datetime.now(UTC)
                    existing.times_seen += 1
                    existing.check_command = finding.check_command
                    existing.check_output = finding.check_output
                    existing.tenant_id = finding.tenant_id
                else:
                    session.add(_finding_to_db(finding, first_seen_run_id=run_id))
                session.add(
                    FindingOccurrenceDB(
                        run_id=run_id,
                        finding_id=finding.id,
                        tenant_id=finding.tenant_id,
                        still_present=finding.status
                        in (FindingStatus.OPEN, FindingStatus.IN_PROGRESS),
                        evidence_at_time=finding.evidence,
                    )
                )

    async def save_scorecard(
        self,
        run_id: str,
        scorecard: Scorecard,
        tenant_id: str | None = None,
    ) -> None:
        """Persist a scorecard and its area scores.

        Args:
            run_id: Audit run identifier.
            scorecard: Scorecard to persist.
            tenant_id: Tenant that owns this scorecard. When provided it is set
                on the scorecard and used to scope fallback storage.
        """
        if tenant_id is not None:
            scorecard.tenant_id = tenant_id

        git_meta = _git_metadata_to_json(scorecard)

        if self._use_fallback:
            self._fallback_write_scorecard(scorecard, run_id, scorecard.tenant_id)
            return

        async with self._session() as session:
            existing = await session.get(ScorecardDB, scorecard.id)
            if existing is not None:
                existing.overall_score = scorecard.overall_score
                existing.overall_grade = scorecard.overall_grade
                existing.confidence = scorecard.confidence.value
                existing.trend = scorecard.trend
                existing.branch = scorecard.branch
                existing.commit_sha = scorecard.commit_sha
                existing.version = scorecard.version
                existing.total_files = scorecard.total_files
                existing.total_directories = scorecard.total_directories
                existing.total_commits = scorecard.total_commits
                existing.total_contributors = scorecard.total_contributors
                existing.git_metric_completeness = git_meta["git_metric_completeness"] or None
                existing.git_warnings = git_meta["git_warnings"] or None
                existing.audit_timestamp = scorecard.audit_timestamp
                existing.executive_summary = scorecard.executive_summary
                existing.tenant_id = scorecard.tenant_id
                await session.execute(
                    delete(AreaScoreDB).where(AreaScoreDB.scorecard_id == scorecard.id)
                )
                for area in scorecard.area_scores:
                    session.add(_area_score_to_db(area, scorecard.id))
            else:
                session.add(_scorecard_to_db(scorecard, run_id))

    async def save_sprints(
        self,
        run_id: str,
        sprints: Sequence[Sprint],
        repo_name: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        """Persist remediation sprints for a run.

        Args:
            run_id: Audit run identifier.
            sprints: Sprints to persist.
            repo_name: Optional repo name override required by the JSON fallback
                store; ignored when a database is configured.
            tenant_id: Tenant that owns these sprints. When provided it is set
                on each sprint and used to scope fallback storage.
        """
        for sprint in sprints:
            if tenant_id is not None:
                sprint.tenant_id = tenant_id

        if self._use_fallback:
            if repo_name is None:
                raise ValueError("repo_name is required for fallback persistence of sprints")
            self._fallback_write_sprints(tenant_id, repo_name, run_id, sprints)
            return

        async with self._session() as session:
            await session.execute(delete(SprintDB).where(SprintDB.run_id == run_id))
            for sprint in sprints:
                session.add(_sprint_to_db(sprint, run_id))

    async def get_latest_scorecard(
        self,
        repo_name: str,
        tenant_id: str | None = None,
    ) -> Scorecard | None:
        """Return the most recent scorecard for a repository, or None."""
        if self._use_fallback:
            scorecards = self._fallback_list_scorecards(tenant_id, repo_name)
            if not scorecards:
                return None
            scorecards.sort(key=lambda x: x[0], reverse=True)
            data = scorecards[0][1]
            run_id = data.get("run_id", "")
            findings = self._fallback_load_findings_for_run(tenant_id, repo_name, run_id)
            return _scorecard_from_dict(data, findings)

        async with self._session() as session:
            result = await session.execute(
                select(ScorecardDB)
                .where(
                    ScorecardDB.repo_name == repo_name,
                    ScorecardDB.tenant_id == tenant_id,
                )
                .order_by(ScorecardDB.audit_timestamp.desc())
                .limit(1)
            )
            row = result.scalar_one_or_none()
            if row is None:
                return None

            area_rows = await session.execute(
                select(AreaScoreDB).where(AreaScoreDB.scorecard_id == row.id)
            )
            area_scores = [_area_score_from_db(a) for a in area_rows.scalars()]

            finding_rows = await session.execute(
                select(FindingDB)
                .join(
                    FindingOccurrenceDB,
                    FindingDB.id == FindingOccurrenceDB.finding_id,
                )
                .where(
                    FindingOccurrenceDB.run_id == row.run_id,
                    FindingDB.tenant_id == tenant_id,
                )
                .distinct()
            )
            findings = [_finding_from_db(f) for f in finding_rows.scalars()]

            return _scorecard_from_db(row, area_scores, findings)

    async def get_score_history(
        self,
        repo_name: str,
        area: AuditArea | None = None,
        tenant_id: str | None = None,
    ) -> ScoreHistory:
        """Return score history for a repository, optionally filtered by area."""
        if self._use_fallback:
            entries: list[ScoreHistoryEntry] = []
            for ts, data, _path in sorted(
                self._fallback_list_scorecards(tenant_id, repo_name), key=lambda x: x[0]
            ):
                run_id = data.get("run_id", "")
                if area is None:
                    entries.append(
                        ScoreHistoryEntry(
                            run_id=run_id,
                            score=data["overall_score"],
                            grade=data["overall_grade"],
                            timestamp=ts,
                        )
                    )
                else:
                    for a in data.get("area_scores", []):
                        if a["area"] == area.value:
                            entries.append(
                                ScoreHistoryEntry(
                                    run_id=run_id,
                                    score=a["score"],
                                    grade=a.get("grade", ""),
                                    timestamp=ts,
                                )
                            )
                            break
            return ScoreHistory(
                repo_name=repo_name,
                area=area.value if area else None,
                entries=entries,
            )

        async with self._session() as session:
            result = await session.execute(
                select(ScorecardDB)
                .where(
                    ScorecardDB.repo_name == repo_name,
                    ScorecardDB.tenant_id == tenant_id,
                )
                .order_by(ScorecardDB.audit_timestamp.asc())
            )
            entries = []
            for row in result.scalars():
                if area is None:
                    entries.append(
                        ScoreHistoryEntry(
                            run_id=row.run_id,
                            score=row.overall_score,
                            grade=row.overall_grade,
                            timestamp=row.audit_timestamp,
                        )
                    )
                else:
                    area_row = await session.execute(
                        select(AreaScoreDB).where(
                            AreaScoreDB.scorecard_id == row.id,
                            AreaScoreDB.area == area.value,
                        )
                    )
                    arow = area_row.scalar_one_or_none()
                    if arow is not None:
                        entries.append(
                            ScoreHistoryEntry(
                                run_id=row.run_id,
                                score=arow.score,
                                grade=arow.grade or "",
                                timestamp=row.audit_timestamp,
                            )
                        )
            return ScoreHistory(
                repo_name=repo_name,
                area=area.value if area else None,
                entries=entries,
            )

    async def list_findings(
        self,
        repo: str,
        status: FindingStatus | None = None,
        severity: Severity | None = None,
        area: AuditArea | None = None,
        tenant_id: str | None = None,
    ) -> list[Finding]:
        """List findings for a repository with optional filters.

        Queries always filter by ``repo`` and ``tenant_id`` to prevent cross-repo
        and cross-tenant leaks.
        """
        if self._use_fallback:
            findings = self._fallback_all_findings(tenant_id, repo)
            if status is not None:
                findings = [f for f in findings if f.status == status]
            if severity is not None:
                findings = [f for f in findings if f.severity == severity]
            if area is not None:
                findings = [f for f in findings if f.area == area]
            return findings

        async with self._session() as session:
            query = (
                select(distinct(FindingDB.id))
                .select_from(FindingDB)
                .join(
                    FindingOccurrenceDB,
                    FindingDB.id == FindingOccurrenceDB.finding_id,
                )
                .join(AuditRunDB, FindingOccurrenceDB.run_id == AuditRunDB.id)
                .where(
                    AuditRunDB.repo_name == repo,
                    AuditRunDB.tenant_id == tenant_id,
                    FindingDB.tenant_id == tenant_id,
                )
            )
            if status is not None:
                query = query.where(FindingDB.status == status.value)
            if severity is not None:
                query = query.where(FindingDB.severity == severity.value)
            if area is not None:
                query = query.where(FindingDB.area == area.value)

            result = await session.execute(query)
            ids = list(result.scalars().all())
            if not ids:
                return []
            rows = await session.execute(
                select(FindingDB).where(
                    FindingDB.id.in_(ids),
                    FindingDB.tenant_id == tenant_id,
                )
            )
            return [_finding_from_db(row) for row in rows.scalars()]

    async def update_finding(
        self,
        finding_id: str,
        update: FindingUpdate,
        repo: str | None = None,
        tenant_id: str | None = None,
    ) -> Finding | None:
        """Update a finding's status, owner, sprint, or resolution note.

        When ``repo`` is provided the update is scoped to that repository; a
        finding that belongs to a different repository will not be modified.
        ``tenant_id`` scopes the search in fallback mode and is applied as a
        filter in SQL mode so cross-tenant updates fail closed.
        """
        if self._use_fallback:
            repo_dirs: list[Path]
            if repo is not None:
                repo_dirs = [self._fallback_repo_dir(tenant_id, repo)]
            else:
                tenant_dirs = [self._fallback_tenant_dir(tenant_id)] if tenant_id is not None else [
                    d for d in self._fallback_dir.glob("*") if d.is_dir()
                ]
                repo_dirs = []
                for tenant_dir in tenant_dirs:
                    repo_dirs.extend(d for d in tenant_dir.glob("*") if d.is_dir())
            for repo_dir in repo_dirs:
                path = repo_dir / "findings" / f"{finding_id}.json"
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if tenant_id is not None and data.get("tenant_id") != tenant_id:
                        continue
                    data["status"] = update.status.value
                    if update.resolution_note is not None:
                        data["resolution_note"] = update.resolution_note
                    if update.owner is not None:
                        data["owner"] = update.owner
                    if update.target_sprint is not None:
                        data["target_sprint"] = update.target_sprint
                    if update.status == FindingStatus.RESOLVED and data.get("resolved_at") is None:
                        data["resolved_at"] = _isoformat(datetime.now(UTC))
                    self._atomic_write_json(path, data)
                    return _finding_from_dict(data)
            return None

        async with self._session() as session:
            if repo is not None:
                result = await session.execute(
                    select(FindingDB)
                    .join(
                        FindingOccurrenceDB,
                        FindingDB.id == FindingOccurrenceDB.finding_id,
                    )
                    .join(AuditRunDB, FindingOccurrenceDB.run_id == AuditRunDB.id)
                    .where(
                        FindingDB.id == finding_id,
                        FindingDB.tenant_id == tenant_id,
                        AuditRunDB.repo_name == repo,
                        AuditRunDB.tenant_id == tenant_id,
                    )
                )
                row = result.scalar_one_or_none()
            else:
                row = await session.get(FindingDB, finding_id)
                if row is not None and row.tenant_id != tenant_id:
                    return None
            if row is None:
                return None
            row.status = update.status.value
            if update.resolution_note is not None:
                row.resolution_note = update.resolution_note
            if update.owner is not None:
                row.owner = update.owner
            if update.target_sprint is not None:
                row.target_sprint = update.target_sprint
            if update.status == FindingStatus.RESOLVED and row.resolved_at is None:
                row.resolved_at = datetime.now(UTC)
            return _finding_from_db(row)

    # -----------------------------------------------------------------------
    # Audit-run read API
    # -----------------------------------------------------------------------

    def _fallback_load_run(
        self,
        tenant_id: str | None,
        repo_name: str,
        run_id: str,
    ) -> AuditRun | None:
        """Load a single audit run from the JSON fallback store."""
        path = self._fallback_repo_dir(tenant_id, repo_name) / "runs" / f"{run_id}.json"
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        if tenant_id is not None and data.get("tenant_id") != tenant_id:
            return None
        return _run_from_dict_with_repo(data, repo_name)

    def _fallback_find_run(
        self,
        run_id: str,
        tenant_id: str | None = None,
    ) -> tuple[str, dict[str, Any]] | None:
        """Search tenant/repo fallback directories for a run file."""
        tenant_dirs = [self._fallback_tenant_dir(tenant_id)] if tenant_id is not None else [
            d for d in self._fallback_dir.glob("*") if d.is_dir()
        ]
        for tenant_dir in tenant_dirs:
            for repo_dir in tenant_dir.glob("*"):
                if not repo_dir.is_dir():
                    continue
                path = repo_dir / "runs" / f"{run_id}.json"
                if path.exists():
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if tenant_id is not None and data.get("tenant_id") != tenant_id:
                        continue
                    repo_name = repo_dir.name.replace("__", "/")
                    return repo_name, data
        return None

    def _fallback_load_scorecard_for_run(
        self,
        tenant_id: str | None,
        repo_name: str,
        run_id: str,
    ) -> Scorecard | None:
        """Load the scorecard associated with a specific run from fallback storage."""
        for ts, data, _path in self._fallback_list_scorecards(tenant_id, repo_name):
            if data.get("run_id") == run_id:
                findings = self._fallback_load_findings_for_run(tenant_id, repo_name, run_id)
                return _scorecard_from_dict(data, findings)
        return None

    async def get_run(
        self,
        run_id: str,
        tenant_id: str | None = None,
    ) -> AuditRun | None:
        """Return a single audit run by ID, or None if not found."""
        if self._use_fallback:
            found = self._fallback_find_run(run_id, tenant_id=tenant_id)
            if found is None:
                return None
            repo_name, data = found
            run = _run_from_dict_with_repo(data, repo_name)
            scorecard = self._fallback_load_scorecard_for_run(tenant_id, repo_name, run_id)
            if scorecard is not None:
                run.scorecard = scorecard
            return run

        async with self._session() as session:
            row = await session.get(AuditRunDB, run_id)
            if row is None or row.tenant_id != tenant_id:
                return None
            scorecard = await self._db_get_scorecard_for_run(session, run_id, tenant_id)
            return _run_from_db_with_scorecard(row, scorecard)

    async def list_runs(
        self,
        repo: str,
        limit: int = 20,
        tenant_id: str | None = None,
    ) -> list[AuditRun]:
        """List recent audit runs for a repository."""
        if self._use_fallback:
            runs: list[tuple[datetime, AuditRun]] = []
            base = self._fallback_repo_dir(tenant_id, repo) / "runs"
            if base.exists():
                for path in base.glob("*.json"):
                    data = json.loads(path.read_text(encoding="utf-8"))
                    if tenant_id is not None and data.get("tenant_id") != tenant_id:
                        continue
                    run = _run_from_dict_with_repo(data, repo)
                    scorecard = self._fallback_load_scorecard_for_run(tenant_id, repo, run.id)
                    if scorecard is not None:
                        run.scorecard = scorecard
                    runs.append((run.started_at or datetime.fromtimestamp(0, tz=UTC), run))
            runs.sort(key=lambda x: x[0], reverse=True)
            return [r for _, r in runs[:limit]]

        async with self._session() as session:
            result = await session.execute(
                select(AuditRunDB)
                .where(
                    AuditRunDB.repo_name == repo,
                    AuditRunDB.tenant_id == tenant_id,
                )
                .order_by(AuditRunDB.started_at.desc())
                .limit(limit)
            )
            rows = result.scalars().all()
            db_runs: list[AuditRun] = []
            for row in rows:
                scorecard = await self._db_get_scorecard_for_run(session, row.id, tenant_id)
                db_runs.append(_run_from_db_with_scorecard(row, scorecard))
            return db_runs

    async def _db_get_scorecard_for_run(
        self,
        session: AsyncSession,
        run_id: str,
        tenant_id: str | None = None,
    ) -> Scorecard | None:
        """Load the scorecard linked to a specific audit run."""
        result = await session.execute(
            select(ScorecardDB).where(
                ScorecardDB.run_id == run_id,
                ScorecardDB.tenant_id == tenant_id,
            )
        )
        row = result.scalar_one_or_none()
        if row is None:
            return None

        area_rows = await session.execute(
            select(AreaScoreDB).where(AreaScoreDB.scorecard_id == row.id)
        )
        area_scores = [_area_score_from_db(a) for a in area_rows.scalars()]

        finding_rows = await session.execute(
            select(FindingDB)
            .join(
                FindingOccurrenceDB,
                FindingDB.id == FindingOccurrenceDB.finding_id,
            )
            .where(
                FindingOccurrenceDB.run_id == run_id,
                FindingDB.tenant_id == tenant_id,
            )
            .distinct()
        )
        findings = [_finding_from_db(f) for f in finding_rows.scalars()]

        return _scorecard_from_db(row, area_scores, findings)

    async def get_sprints(
        self,
        repo: str,
        tenant_id: str | None = None,
    ) -> list[Sprint]:
        """Return the sprints for the most recent audit run of a repository."""
        if self._use_fallback:
            base = self._fallback_repo_dir(tenant_id, repo) / "sprints"
            if not base.exists():
                return []
            entries: list[tuple[datetime, list[Sprint], Path]] = []
            for path in base.glob("*.json"):
                data = json.loads(path.read_text(encoding="utf-8"))
                sprints = [_sprint_from_dict(s) for s in data.get("sprints", [])]
                if tenant_id is not None and any(
                    s.get("tenant_id") != tenant_id for s in data.get("sprints", [])
                ):
                    continue
                run_id = data.get("run_id", "")
                run_path = self._fallback_repo_dir(tenant_id, repo) / "runs" / f"{run_id}.json"
                started_at = datetime.fromtimestamp(0, tz=UTC)
                if run_path.exists():
                    run_data = json.loads(run_path.read_text(encoding="utf-8"))
                    started_at = _parse_datetime(run_data.get("started_at")) or started_at
                entries.append((started_at, sprints, path))
            if not entries:
                return []
            entries.sort(key=lambda x: x[0], reverse=True)
            return entries[0][1]

        async with self._session() as session:
            result = await session.execute(
                select(SprintDB)
                .join(AuditRunDB, SprintDB.run_id == AuditRunDB.id)
                .where(
                    AuditRunDB.repo_name == repo,
                    AuditRunDB.tenant_id == tenant_id,
                )
                .order_by(AuditRunDB.started_at.desc())
            )
            rows = result.scalars().all()
            if not rows:
                return []
            # Rows are ordered by run; take the latest run's sprints.
            latest_run_id = rows[0].run_id
            return [_sprint_from_db(r) for r in rows if r.run_id == latest_run_id]


# ---------------------------------------------------------------------------
# Neo4j knowledge-graph helper
# ---------------------------------------------------------------------------


async def update_knowledge_graph(
    run_id: str,
    repo_name: str,
    scorecard: Scorecard,
    findings: Sequence[Finding],
    sprints: Sequence[Sprint],
    tenant_id: str,
    neo4j_uri: str,
    neo4j_user: str | None = None,
    neo4j_password: str | None = None,
) -> None:
    """Write audit results into a Neo4j knowledge graph.

    Creates ``AuditRun``, ``Finding``, ``AuditArea`` and ``Sprint`` nodes and
    the relationships described in SPEC Section 9.2. The helper is a no-op if
    Neo4j driver imports are unavailable.

    Args:
        run_id: Audit run identifier.
        repo_name: Repository name.
        scorecard: Scorecard produced by the run.
        findings: Findings to link to the run.
        sprints: Sprints to link to findings.
        tenant_id: Tenant that owns every graph node and relationship written.
        neo4j_uri: Bolt URI of the Neo4j instance.
        neo4j_user: Neo4j username.
        neo4j_password: Neo4j password.
    """
    if not _NEO4J_AVAILABLE or AsyncGraphDatabase is None:
        logger.warning("Neo4j driver unavailable; skipping knowledge-graph update")
        return

    auth = (neo4j_user, neo4j_password) if neo4j_user and neo4j_password else None
    driver = AsyncGraphDatabase.driver(neo4j_uri, auth=auth)
    try:
        async with driver.session() as graph_session:
            await graph_session.execute_write(
                _write_kg_tx,
                run_id=run_id,
                repo_name=repo_name,
                scorecard=scorecard,
                findings=findings,
                sprints=sprints,
                tenant_id=tenant_id,
            )
    finally:
        await driver.close()


async def _write_kg_tx(
    tx: Any,
    *,
    run_id: str,
    repo_name: str,
    scorecard: Scorecard,
    findings: Sequence[Finding],
    sprints: Sequence[Sprint],
    tenant_id: str,
) -> None:
    """Cypher transaction writing the audit graph."""
    await tx.run(
        """
        MERGE (run:AuditRun {id: $run_id, tenant_id: $tenant_id}) // cypher-mutation-safe: composite key includes authenticated tenant_id
        SET run.repo = $repo_name,
            run.timestamp = $timestamp,
            run.score = $overall_score,
            run.grade = $overall_grade
        """,
        run_id=run_id,
        tenant_id=tenant_id,
        repo_name=repo_name,
        timestamp=scorecard.audit_timestamp.isoformat(),
        overall_score=scorecard.overall_score,
        overall_grade=scorecard.overall_grade,
    )

    for finding in findings:
        await tx.run(
            """
            MERGE (finding:Finding {id: $finding_id, tenant_id: $tenant_id}) // cypher-mutation-safe: composite key includes authenticated tenant_id
            SET finding.severity = $severity,
                finding.area = $area,
                finding.status = $status
            WITH finding
            MATCH (run:AuditRun {id: $run_id, tenant_id: $tenant_id})
            MERGE (run)-[:IDENTIFIED]->(finding) // cypher-mutation-safe: both endpoints are tenant scoped
            """,
            finding_id=finding.id,
            tenant_id=tenant_id,
            severity=finding.severity.value,
            area=finding.area.value,
            status=finding.status.value,
            run_id=run_id,
        )
        if finding.evidence:
            for ev in finding.evidence.split(";"):
                ev_path = ev.strip().split(":")[0]
                if ev_path:
                    await tx.run(
                        """
                        MERGE (file:SourceFile {path: $path, tenant_id: $tenant_id}) // cypher-mutation-safe: composite key includes authenticated tenant_id
                        WITH file
                        MATCH (finding:Finding {id: $finding_id, tenant_id: $tenant_id})
                        MERGE (finding)-[:EVIDENCE_IN]->(file) // cypher-mutation-safe: both endpoints are tenant scoped
                        """,
                        path=ev_path,
                        finding_id=finding.id,
                        tenant_id=tenant_id,
                    )

    for area in scorecard.area_scores:
        await tx.run(
            """
            MERGE (area:AuditArea {name: $area_name, tenant_id: $tenant_id}) // cypher-mutation-safe: composite key includes authenticated tenant_id
            SET area.weight = $weight,
                area.score = $score
            WITH area
            MATCH (run:AuditRun {id: $run_id, tenant_id: $tenant_id})
            MERGE (run)-[:SCORED {score: $score}]->(area) // cypher-mutation-safe: both endpoints are tenant scoped
            """,
            area_name=area.area.value,
            tenant_id=tenant_id,
            weight=area.weight,
            score=area.score,
            run_id=run_id,
        )

    for sprint in sprints:
        await tx.run(
            """
            MERGE (sprint:Sprint {number: $num, run_id: $run_id, tenant_id: $tenant_id}) // cypher-mutation-safe: composite key includes authenticated tenant_id
            SET sprint.theme = $theme,
                sprint.status = $status
            WITH sprint
            UNWIND $finding_ids AS fid
            MATCH (finding:Finding {id: fid, tenant_id: $tenant_id})
            MERGE (sprint)-[:ADDRESSES]->(finding) // cypher-mutation-safe: both endpoints are tenant scoped
            """,
            num=sprint.id,
            run_id=run_id,
            tenant_id=tenant_id,
            theme=sprint.theme,
            status=sprint.status.value,
            finding_ids=sprint.findings_targeted,
        )


__all__ = [
    "AuditRunDB",
    "FindingDB",
    "FindingOccurrenceDB",
    "ScorecardDB",
    "AreaScoreDB",
    "SprintDB",
    "PersistenceManager",
    "update_knowledge_graph",
]
