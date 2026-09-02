"""Serialization layer for the AuditOrchestrator agent.

Holds the SQLAlchemy 2.0 ORM row models and the pure ``_x_to_db``/``_x_from_db``
and ``_x_to_dict``/``_x_from_dict`` conversion helpers extracted from
``persistence.py``, which keeps the persistence manager focused on I/O. All
converters are re-exported from ``persistence`` so existing imports keep
working.

The module can be imported without a live database; all SQLAlchemy imports
are guarded so lightweight tests do not require those packages.
"""

from __future__ import annotations

import subprocess
from collections.abc import Sequence
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
    Scorecard,
    Severity,
    Sprint,
    SprintStatus,
)

# ---------------------------------------------------------------------------
# Lazy, guarded import for heavy persistence drivers
# ---------------------------------------------------------------------------

_SQLALCHEMY_AVAILABLE = False

try:  # pragma: no cover
    from sqlalchemy import (
        JSON,
        DateTime,
        ForeignKey,
        String,
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


