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
import tempfile
from collections.abc import AsyncGenerator, Callable, Sequence
from contextlib import asynccontextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from .models import (
    AuditArea,
    AuditRun,
    Finding,
    FindingStatus,
    FindingUpdate,
    Scorecard,
    ScoreHistory,
    ScoreHistoryEntry,
    Severity,
    Sprint,
)

# ---------------------------------------------------------------------------
# Lazy, guarded imports for heavy persistence drivers
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

_SQLALCHEMY_AVAILABLE = False
_NEO4J_AVAILABLE = False

try:  # pragma: no cover
    from sqlalchemy import (
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
# Serializers and ORM row models (extracted to serialization.py)
# ---------------------------------------------------------------------------

from .serialization import (
    AreaScoreDB,
    AuditRunDB,
    Base,
    FindingDB,
    FindingOccurrenceDB,
    ScorecardDB,
    SprintDB,
    _area_score_from_db,
    _area_score_to_db,
    _finding_from_db,
    _finding_from_dict,
    _finding_to_db,
    _finding_to_dict,
    _git_metadata_to_json,
    _isoformat,
    _parse_datetime,
    _repo_name_from_path,
    _run_from_db_with_scorecard,
    _run_from_dict_with_repo,
    _run_to_db,
    _run_to_dict,
    _scorecard_from_db,
    _scorecard_from_dict,
    _scorecard_to_db,
    _scorecard_to_dict,
    _sprint_from_db,
    _sprint_from_dict,
    _sprint_to_db,
    _sprint_to_dict,
)
from .serialization import (
    _as_json_dict as _as_json_dict,
)
from .serialization import (
    _repo_name_from_git_url as _repo_name_from_git_url,
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

        if self._use_fallback:
            self._fallback_write_scorecard(scorecard, run_id, scorecard.tenant_id)
            return

        git_meta = _git_metadata_to_json(scorecard)

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
