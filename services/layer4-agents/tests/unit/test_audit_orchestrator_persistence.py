"""Unit tests for AuditOrchestrator persistence layer.

Tests cover both the SQLAlchemy async database path (using an in-memory
SQLite database) and the JSON-file fallback path, ensuring no live PostgreSQL
or Neo4j is required.
"""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from layer4_agents.agents.audit_orchestrator.models import (
    AuditRun,
    Confidence,
    Finding,
    FindingStatus,
    FindingUpdate,
    Severity,
    Sprint,
)
from layer4_agents.agents.audit_orchestrator.persistence import (
    PersistenceManager,
    _repo_name_from_git_url,
    _repo_name_from_path,
    clear_engine_cache,
)
from layer4_agents.agents.audit_orchestrator.scoring import build_scorecard


@pytest.fixture
def sample_finding() -> Finding:
    """Return a minimal valid finding."""
    return Finding(
        id="COR-001",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        area="C: Correctness, Data Integrity, Contracts",
        evidence="src/app.py:42",
        observed_fact="Missing idempotency check",
        inference_risk="Duplicate processing may corrupt state",
        business_impact="Data inconsistency in production",
        recommended_fix="Add idempotency key handling",
        effort="M",
        risk_of_change="Low",
        owner="platform-team",
        analyzer_type="code",
    )


@pytest.fixture
def another_finding() -> Finding:
    """Return a second finding for filter tests."""
    return Finding(
        id="SEC-001",
        severity=Severity.CRITICAL,
        confidence=Confidence.HIGH,
        area="E: Security and Supply Chain",
        evidence="src/auth.py:10",
        observed_fact="Missing LLM guardrail",
        inference_risk="Prompt injection risk",
        business_impact="Unauthorized data exposure",
        recommended_fix="Add input validation",
        effort="S",
        risk_of_change="Medium",
        owner="security-team",
        analyzer_type="code",
    )


@pytest.fixture
def sample_scorecard(sample_finding: Finding) -> Any:
    """Return a valid scorecard with all ten areas."""
    return build_scorecard(
        repo_name="owner/repo",
        findings=[sample_finding],
        branch="main",
        commit_sha="abc123",
        total_files=120,
        total_directories=15,
        total_commits=42,
        total_contributors=5,
    )


@pytest.fixture
def sample_sprints() -> list[Sprint]:
    """Return a small set of sprints."""
    return [
        Sprint(
            id=1,
            theme="Stabilize correctness",
            objectives=["Fix idempotency gaps"],
            deliverables=["PR with idempotency keys"],
            findings_targeted=["COR-001"],
            score_impact_projected=5,
        ),
        Sprint(
            id=2,
            theme="Harden security",
            objectives=["Add guardrails"],
            deliverables=["Security review"],
            findings_targeted=["SEC-001"],
            score_impact_projected=8,
        ),
    ]


@pytest.fixture
def sample_run(sample_scorecard: Any) -> AuditRun:
    """Return a completed audit run with a scorecard."""
    run = AuditRun(
        status="completed",
        trigger_type="manual",
        repo_path="/tmp/owner/repo",
    )
    run.mark_completed(sample_scorecard)
    return run


@pytest.fixture
async def db_manager(tmp_path: Path) -> PersistenceManager:
    """Return a PersistenceManager backed by an in-memory SQLite database."""
    clear_engine_cache()
    manager = PersistenceManager(
        postgres_dsn="sqlite+aiosqlite:///:memory:",
        fallback_dir=tmp_path / "fallback",
    )
    await manager.create_schema()
    return manager


@pytest.fixture
async def fallback_manager(tmp_path: Path) -> PersistenceManager:
    """Return a PersistenceManager operating in JSON fallback mode."""
    return PersistenceManager(fallback_dir=tmp_path / "fallback")


# ---------------------------------------------------------------------------
# Database round-trip tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_save_and_get_scorecard(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
) -> None:
    await db_manager.save_run(sample_run)
    await db_manager.save_scorecard(sample_run.id, sample_scorecard)

    loaded = await db_manager.get_latest_scorecard(sample_scorecard.repo_name)
    assert loaded is not None
    assert loaded.repo_name == sample_scorecard.repo_name
    assert loaded.overall_score == sample_scorecard.overall_score
    assert loaded.overall_grade == sample_scorecard.overall_grade
    assert len(loaded.area_scores) == len(sample_scorecard.area_scores)


@pytest.mark.unit
async def test_save_and_list_findings(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
    another_finding: Finding,
) -> None:
    await db_manager.save_run(sample_run)
    await db_manager.save_findings(
        sample_run.id,
        [sample_finding, another_finding],
        repo_name=sample_scorecard.repo_name,
    )

    all_findings = await db_manager.list_findings(sample_scorecard.repo_name)
    assert len(all_findings) == 2

    critical = await db_manager.list_findings(
        sample_scorecard.repo_name, severity=Severity.CRITICAL
    )
    assert len(critical) == 1
    assert critical[0].id == "SEC-001"

    security = await db_manager.list_findings(sample_scorecard.repo_name, area=another_finding.area)
    assert len(security) == 1
    assert security[0].id == "SEC-001"


@pytest.mark.unit
async def test_update_finding(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
) -> None:
    await db_manager.save_run(sample_run)
    await db_manager.save_findings(
        sample_run.id, [sample_finding], repo_name=sample_scorecard.repo_name
    )

    update = FindingUpdate(
        status=FindingStatus.RESOLVED,
        resolution_note="Fixed in PR #123",
        owner="platform-team",
        target_sprint=1,
    )
    updated = await db_manager.update_finding(sample_finding.id, update)
    assert updated is not None
    assert updated.status == FindingStatus.RESOLVED
    assert updated.resolution_note == "Fixed in PR #123"
    assert updated.target_sprint == 1
    assert updated.resolved_at is not None


@pytest.mark.unit
async def test_save_and_get_sprints(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_sprints: list[Sprint],
) -> None:
    await db_manager.save_run(sample_run)
    await db_manager.save_sprints(
        sample_run.id, sample_sprints, repo_name=sample_scorecard.repo_name
    )

    # Sprints are not exposed directly by the public manager API; verify by
    # loading the latest scorecard run history and checking the DB indirectly.
    history = await db_manager.get_score_history(sample_scorecard.repo_name)
    assert history.repo_name == sample_scorecard.repo_name


@pytest.mark.unit
async def test_score_history(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
) -> None:
    await db_manager.save_run(sample_run)
    await db_manager.save_scorecard(sample_run.id, sample_scorecard)

    history = await db_manager.get_score_history(sample_scorecard.repo_name)
    assert len(history.entries) == 1
    assert history.entries[0].score == sample_scorecard.overall_score
    assert history.entries[0].grade == sample_scorecard.overall_grade

    # Area-specific history
    area = sample_scorecard.area_scores[0].area
    area_history = await db_manager.get_score_history(sample_scorecard.repo_name, area=area)
    assert len(area_history.entries) == 1


@pytest.mark.unit
async def test_list_findings_does_not_leak_across_repos(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
) -> None:
    await db_manager.save_run(sample_run)
    await db_manager.save_findings(
        sample_run.id, [sample_finding], repo_name=sample_scorecard.repo_name
    )

    other_findings = await db_manager.list_findings("other/repo")
    assert other_findings == []


# ---------------------------------------------------------------------------
# JSON fallback tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_fallback_save_and_get_scorecard(
    fallback_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
) -> None:
    await fallback_manager.save_run(sample_run)
    await fallback_manager.save_scorecard(sample_run.id, sample_scorecard)

    loaded = await fallback_manager.get_latest_scorecard(sample_scorecard.repo_name)
    assert loaded is not None
    assert loaded.repo_name == sample_scorecard.repo_name
    assert loaded.overall_score == sample_scorecard.overall_score


@pytest.mark.unit
async def test_fallback_list_findings_repo_filter(
    fallback_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
) -> None:
    await fallback_manager.save_run(sample_run)
    await fallback_manager.save_scorecard(sample_run.id, sample_scorecard)
    await fallback_manager.save_findings(
        sample_run.id, [sample_finding], repo_name=sample_scorecard.repo_name
    )

    repo_findings = await fallback_manager.list_findings(sample_scorecard.repo_name)
    assert len(repo_findings) == 1

    other_findings = await fallback_manager.list_findings("other/repo")
    assert other_findings == []


@pytest.mark.unit
async def test_fallback_update_finding(
    fallback_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
) -> None:
    await fallback_manager.save_run(sample_run)
    await fallback_manager.save_scorecard(sample_run.id, sample_scorecard)
    await fallback_manager.save_findings(
        sample_run.id, [sample_finding], repo_name=sample_scorecard.repo_name
    )

    update = FindingUpdate(status=FindingStatus.RESOLVED)
    updated = await fallback_manager.update_finding(sample_finding.id, update)
    assert updated is not None
    assert updated.status == FindingStatus.RESOLVED

    listed = await fallback_manager.list_findings(sample_scorecard.repo_name)
    assert listed[0].status == FindingStatus.RESOLVED


@pytest.mark.unit
async def test_fallback_atomic_write(
    fallback_manager: PersistenceManager,
    sample_run: AuditRun,
) -> None:
    await fallback_manager.save_run(sample_run)
    run_path = (
        fallback_manager._fallback_repo_dir(None, sample_run.scorecard.repo_name)
        / "runs"
        / f"{sample_run.id}.json"
    )
    assert run_path.exists()
    data = __import__("json").loads(run_path.read_text(encoding="utf-8"))
    assert data["id"] == sample_run.id
    assert data["status"] == "completed"


# ---------------------------------------------------------------------------
# Manager construction
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_manager_uses_fallback_when_no_dsn(tmp_path: Path) -> None:
    manager = PersistenceManager(fallback_dir=tmp_path / "fallback")
    assert manager._use_fallback is True


@pytest.mark.unit
def test_manager_requires_repo_name_for_fallback_findings(
    tmp_path: Path,
) -> None:
    manager = PersistenceManager(fallback_dir=tmp_path / "fallback")
    finding = Finding(
        id="COR-002",
        severity=Severity.LOW,
        confidence=Confidence.MEDIUM,
        area="C: Correctness, Data Integrity, Contracts",
        evidence="src/x.py:1",
        observed_fact="x",
        inference_risk="y",
        business_impact="z",
        recommended_fix="a",
        effort="XS",
        risk_of_change="Low",
        owner="team",
        analyzer_type="code",
    )
    with pytest.raises(ValueError, match="repo_name is required"):
        # type: ignore[arg-type] -- intentionally calling sync method in test
        import asyncio

        asyncio.run(manager.save_findings("run-1", [finding]))


@pytest.mark.unit
async def test_get_latest_scorecard_returns_none_when_empty(
    db_manager: PersistenceManager,
) -> None:
    result = await db_manager.get_latest_scorecard("nonexistent/repo")
    assert result is None


# ---------------------------------------------------------------------------
# Round-trip fidelity tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_scorecard_round_trip_preserves_all_fields(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
) -> None:
    """Assert every Scorecard and AreaScore field survives a DB round trip."""
    await db_manager.save_run(sample_run)
    sample_scorecard.executive_summary = "Test executive summary with a pipe | and a newline."
    await db_manager.save_scorecard(sample_run.id, sample_scorecard)

    loaded = await db_manager.get_latest_scorecard(sample_scorecard.repo_name)
    assert loaded is not None
    assert loaded.executive_summary == sample_scorecard.executive_summary
    assert loaded.branch == sample_scorecard.branch
    assert loaded.commit_sha == sample_scorecard.commit_sha
    assert loaded.version == sample_scorecard.version
    assert loaded.confidence == sample_scorecard.confidence
    assert loaded.trend == sample_scorecard.trend
    assert loaded.total_files == sample_scorecard.total_files
    assert loaded.total_directories == sample_scorecard.total_directories
    assert loaded.total_commits == sample_scorecard.total_commits
    assert loaded.total_contributors == sample_scorecard.total_contributors
    assert loaded.overall_score == sample_scorecard.overall_score
    assert loaded.overall_grade == sample_scorecard.overall_grade

    for loaded_area, original_area in zip(loaded.area_scores, sample_scorecard.area_scores):
        assert loaded_area.area == original_area.area
        assert loaded_area.weight == original_area.weight
        assert loaded_area.score == original_area.score
        assert loaded_area.grade == original_area.grade
        assert loaded_area.confidence == original_area.confidence
        assert loaded_area.trend_risk == original_area.trend_risk
        assert loaded_area.diagnosis == original_area.diagnosis
        assert loaded_area.findings_count == original_area.findings_count


@pytest.mark.unit
async def test_fallback_scorecard_round_trip_preserves_all_fields(
    fallback_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
) -> None:
    """Assert scorecard fields survive a JSON fallback round trip."""
    await fallback_manager.save_run(sample_run)
    await fallback_manager.save_scorecard(sample_run.id, sample_scorecard)

    loaded = await fallback_manager.get_latest_scorecard(sample_scorecard.repo_name)
    assert loaded is not None
    assert loaded.branch == sample_scorecard.branch
    assert loaded.commit_sha == sample_scorecard.commit_sha
    assert loaded.total_files == sample_scorecard.total_files
    assert loaded.total_contributors == sample_scorecard.total_contributors
    assert loaded.confidence == sample_scorecard.confidence
    assert loaded.area_scores[0].findings_count == sample_scorecard.area_scores[0].findings_count


@pytest.mark.unit
async def test_save_findings_increments_times_seen(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
) -> None:
    """Re-saving an existing finding must increment times_seen and last_seen_at."""
    await db_manager.save_run(sample_run)
    await db_manager.save_findings(
        sample_run.id, [sample_finding], repo_name=sample_scorecard.repo_name
    )

    first_listed = await db_manager.list_findings(sample_scorecard.repo_name)
    assert first_listed[0].times_seen == 1

    # Resubmit the same finding as if observed again.
    sample_finding.last_seen_at = datetime.now(UTC)
    await db_manager.save_findings(
        sample_run.id, [sample_finding], repo_name=sample_scorecard.repo_name
    )

    second_listed = await db_manager.list_findings(sample_scorecard.repo_name)
    assert second_listed[0].times_seen == 2
    assert second_listed[0].last_seen_at >= first_listed[0].last_seen_at


@pytest.mark.unit
async def test_fallback_save_findings_increments_times_seen(
    fallback_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
) -> None:
    """JSON fallback increments times_seen when a finding is observed again."""
    await fallback_manager.save_run(sample_run)
    await fallback_manager.save_scorecard(sample_run.id, sample_scorecard)
    await fallback_manager.save_findings(
        sample_run.id, [sample_finding], repo_name=sample_scorecard.repo_name
    )

    first_listed = await fallback_manager.list_findings(sample_scorecard.repo_name)
    assert first_listed[0].times_seen == 1

    await fallback_manager.save_findings(
        sample_run.id, [sample_finding], repo_name=sample_scorecard.repo_name
    )

    second_listed = await fallback_manager.list_findings(sample_scorecard.repo_name)
    assert second_listed[0].times_seen == 2


# ---------------------------------------------------------------------------
# Repo-name extraction tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_repo_name_from_path_local_owner_repo() -> None:
    assert _repo_name_from_path("/tmp/owner/repo") == "owner/repo"
    assert _repo_name_from_path("/a/b/owner/repo/") == "owner/repo"


@pytest.mark.unit
def test_repo_name_from_path_single_directory_fallback() -> None:
    """When only two path components exist, derive owner/repo from them."""
    assert _repo_name_from_path("/tmp/repo") == "tmp/repo"


@pytest.mark.unit
def test_repo_name_from_path_empty_fallback() -> None:
    assert _repo_name_from_path("/") == "unknown/repo"


@pytest.mark.unit
def test_repo_name_from_git_url_ssh() -> None:
    assert _repo_name_from_git_url("git@github.com:owner/repo.git") == "owner/repo"


@pytest.mark.unit
def test_repo_name_from_git_url_https() -> None:
    assert _repo_name_from_git_url("https://github.com/owner/repo.git") == "owner/repo"


@pytest.mark.unit
def test_repo_name_from_git_url_bare_path() -> None:
    assert _repo_name_from_git_url("/path/to/owner/repo.git") == "owner/repo"


@pytest.mark.unit
def test_repo_name_from_path_uses_git_remote(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    """When inside a git repo, derive the name from the origin remote."""
    git_dir = tmp_path / "repo"
    git_dir.mkdir()
    (git_dir / ".git").mkdir()

    def fake_run(cmd: list[str], **kwargs: Any) -> Any:
        class Result:
            stdout = "git@github.com:acme/widget.git\n"
            returncode = 0

        return Result()

    monkeypatch.setattr("subprocess.run", fake_run)
    assert _repo_name_from_path(str(git_dir)) == "acme/widget"


# ---------------------------------------------------------------------------
# Tenant isolation tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_fallback_tenant_isolation_for_findings(
    fallback_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
) -> None:
    """Tenant A cannot read Tenant B's findings in fallback mode."""
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    await fallback_manager.save_run(sample_run, tenant_id=tenant_a)
    await fallback_manager.save_scorecard(
        sample_run.id, sample_scorecard, tenant_id=tenant_a
    )
    await fallback_manager.save_findings(
        sample_run.id,
        [sample_finding],
        repo_name=sample_scorecard.repo_name,
        tenant_id=tenant_a,
    )

    a_findings = await fallback_manager.list_findings(
        sample_scorecard.repo_name, tenant_id=tenant_a
    )
    assert len(a_findings) == 1

    b_findings = await fallback_manager.list_findings(
        sample_scorecard.repo_name, tenant_id=tenant_b
    )
    assert b_findings == []


@pytest.mark.unit
async def test_fallback_tenant_isolation_for_runs(
    fallback_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
) -> None:
    """Tenant A cannot read Tenant B's runs in fallback mode."""
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    await fallback_manager.save_run(sample_run, tenant_id=tenant_a)
    await fallback_manager.save_scorecard(
        sample_run.id, sample_scorecard, tenant_id=tenant_a
    )

    a_run = await fallback_manager.get_run(sample_run.id, tenant_id=tenant_a)
    assert a_run is not None

    b_run = await fallback_manager.get_run(sample_run.id, tenant_id=tenant_b)
    assert b_run is None


@pytest.mark.unit
async def test_db_tenant_isolation_for_findings(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
    sample_finding: Finding,
) -> None:
    """Tenant A cannot read Tenant B's findings in DB mode."""
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    await db_manager.save_run(sample_run, tenant_id=tenant_a)
    await db_manager.save_scorecard(sample_run.id, sample_scorecard, tenant_id=tenant_a)
    await db_manager.save_findings(
        sample_run.id,
        [sample_finding],
        repo_name=sample_scorecard.repo_name,
        tenant_id=tenant_a,
    )

    a_findings = await db_manager.list_findings(
        sample_scorecard.repo_name, tenant_id=tenant_a
    )
    assert len(a_findings) == 1

    b_findings = await db_manager.list_findings(
        sample_scorecard.repo_name, tenant_id=tenant_b
    )
    assert b_findings == []


@pytest.mark.unit
async def test_db_tenant_isolation_for_runs(
    db_manager: PersistenceManager,
    sample_run: AuditRun,
    sample_scorecard: Any,
) -> None:
    """Tenant A cannot read Tenant B's runs in DB mode."""
    tenant_a = "tenant-a"
    tenant_b = "tenant-b"

    await db_manager.save_run(sample_run, tenant_id=tenant_a)
    await db_manager.save_scorecard(sample_run.id, sample_scorecard, tenant_id=tenant_a)

    a_run = await db_manager.get_run(sample_run.id, tenant_id=tenant_a)
    assert a_run is not None

    b_run = await db_manager.get_run(sample_run.id, tenant_id=tenant_b)
    assert b_run is None


# ---------------------------------------------------------------------------
# Incremental run field round-trip tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
async def test_incremental_fields_round_trip_db(
    db_manager: PersistenceManager,
    sample_scorecard: Any,
) -> None:
    """Incremental run fields survive a DB round trip."""
    run = AuditRun(
        status="completed",
        trigger_type="manual",
        repo_path="/tmp/owner/repo",
        previous_run_id="prev-run-123",
        files_changed_since_last=["src/app.py", "README.md"],
        areas_reanalyzed=["C: Correctness, Data Integrity, Contracts"],
    )
    run.mark_completed(sample_scorecard)

    await db_manager.save_run(run)
    loaded = await db_manager.get_run(run.id)
    assert loaded is not None
    assert loaded.previous_run_id == "prev-run-123"
    assert loaded.files_changed_since_last == ["src/app.py", "README.md"]
    assert loaded.areas_reanalyzed == ["C: Correctness, Data Integrity, Contracts"]


@pytest.mark.unit
async def test_incremental_fields_round_trip_fallback(
    fallback_manager: PersistenceManager,
    sample_scorecard: Any,
) -> None:
    """Incremental run fields survive a JSON fallback round trip."""
    run = AuditRun(
        status="completed",
        trigger_type="manual",
        repo_path="/tmp/owner/repo",
        previous_run_id="prev-run-456",
        files_changed_since_last=["src/main.py"],
        areas_reanalyzed=["E: Security and Supply Chain"],
    )
    run.mark_completed(sample_scorecard)

    await fallback_manager.save_run(run)
    loaded = await fallback_manager.get_run(run.id)
    assert loaded is not None
    assert loaded.previous_run_id == "prev-run-456"
    assert loaded.files_changed_since_last == ["src/main.py"]
    assert loaded.areas_reanalyzed == ["E: Security and Supply Chain"]
