"""Unit tests for the AuditOrchestrator LangGraph state machine.

These tests exercise the compiled graph end-to-end on the current repository
and assert that the expected artifacts (scorecard, findings, report) are
produced.
"""

from __future__ import annotations

import asyncio
import subprocess
from pathlib import Path

import pytest

from layer4_agents.agents.audit_orchestrator.graph import (
    _resolve_repo_path,
    create_audit_graph,
    run_audit,
    run_audit_async,
)
from layer4_agents.agents.audit_orchestrator.models import AuditArea, AuditConfig
from layer4_agents.agents.audit_orchestrator.persistence import PersistenceManager


@pytest.mark.unit
@pytest.mark.timeout(120)
def test_create_audit_graph_compiles():
    """The graph must compile into a runnable state machine."""
    graph = create_audit_graph()
    assert graph is not None


@pytest.mark.unit
@pytest.mark.timeout(180)
def test_run_audit_on_current_repo():
    """Running the graph on the current repo must produce a complete scorecard."""
    config = AuditConfig(
        repo_url=".",
        repo_name="test/repo",
        incremental=False,
        sprints_enabled=True,
        output_dir=".audit_cache/test_reports",
        trusted_source=True,
    )

    state = run_audit(config, trigger_type="manual")

    assert state["status"] == "completed", f"run failed: {state.get('error')}"
    assert state["error"] is None
    assert state["scorecard"] is not None
    scorecard = state["scorecard"]

    assert 0 <= scorecard.overall_score <= 100
    assert scorecard.overall_grade
    assert len(scorecard.area_scores) == len(AuditArea)

    areas = {a.area for a in scorecard.area_scores}
    assert areas == set(AuditArea)

    for area_score in scorecard.area_scores:
        assert 0 <= area_score.score <= 100
        assert area_score.weight > 0
        assert area_score.grade
        assert area_score.diagnosis

    assert state["report_markdown"]
    assert "# Repository Health Audit" in state["report_markdown"]

    if config.sprints_enabled:
        assert state["sprints"]
        for sprint in state["sprints"]:
            assert sprint.theme
            assert sprint.objectives
            assert sprint.findings_targeted


@pytest.mark.unit
@pytest.mark.timeout(120)
def test_run_audit_without_sprints():
    """The graph completes successfully when sprint planning is disabled."""
    config = AuditConfig(
        repo_url=".",
        repo_name="test/repo-no-sprints",
        incremental=False,
        sprints_enabled=False,
        output_dir=".audit_cache/test_reports",
        trusted_source=True,
    )

    state = run_audit(config, trigger_type="manual")

    assert state["status"] == "completed", f"run failed: {state.get('error')}"
    assert state["scorecard"] is not None
    assert state["sprints"] == []
    assert state["report_markdown"]


@pytest.mark.unit
@pytest.mark.timeout(60)
def test_graph_failure_persists_failed_audit_run(tmp_path, monkeypatch):
    """An internal graph failure must persist a failed AuditRun record."""
    run_id = "failed-run-001"
    cache_dir = str(tmp_path / "audit_cache")
    config = AuditConfig(
        repo_url=".",
        repo_name="test/failed-repo",
        incremental=False,
        sprints_enabled=False,
        output_dir=str(tmp_path / "reports"),
        cache_dir=cache_dir,
        trusted_source=True,
    )

    async def _failing_node(state):
        return {"error": "injected analyzer failure", "current_step": "analyze_code"}

    monkeypatch.setattr(
        "layer4_agents.agents.audit_orchestrator.graph.node_analyze_code",
        _failing_node,
    )

    with pytest.raises(RuntimeError, match="injected analyzer failure"):
        run_audit(config, trigger_type="manual", run_id=run_id)

    manager = PersistenceManager(fallback_dir=cache_dir)
    run = asyncio.run(manager.get_run(run_id))
    assert run is not None
    assert run.status == "failed"
    assert run.error_message is not None
    assert "injected analyzer failure" in run.error_message
    assert run.completed_at is not None


@pytest.mark.unit
@pytest.mark.timeout(60)
async def test_run_audit_async_raises_on_failed_state(tmp_path, monkeypatch):
    """run_audit_async must raise when the graph terminates with an error."""
    config = AuditConfig(
        repo_url=".",
        repo_name="test/async-failed-repo",
        incremental=False,
        sprints_enabled=False,
        output_dir=str(tmp_path / "reports"),
        cache_dir=str(tmp_path / "audit_cache"),
        trusted_source=True,
    )

    async def _failing_node(state):
        return {"error": "async injected failure", "current_step": "analyze_code"}

    monkeypatch.setattr(
        "layer4_agents.agents.audit_orchestrator.graph.node_analyze_code",
        _failing_node,
    )

    with pytest.raises(RuntimeError, match="async injected failure"):
        await run_audit_async(config, trigger_type="manual")


@pytest.mark.unit
def test_resolve_repo_path_trusted_source_allows_within_root(tmp_path: Path):
    """When trusted_source=True, paths inside allowed_repo_root resolve cleanly."""
    root = tmp_path / "repos"
    repo_dir = root / "tenant-a" / "my-repo"
    repo_dir.mkdir(parents=True)

    config = AuditConfig(
        repo_url=str(repo_dir),
        repo_name="tenant-a/my-repo",
        trusted_source=True,
        allowed_repo_root=str(root),
    )

    resolved, _ = _resolve_repo_path(config)
    assert resolved == repo_dir.resolve()


@pytest.mark.unit
def test_resolve_repo_path_trusted_source_rejects_escape_from_root(tmp_path: Path):
    """When trusted_source=True, traversal (..) outside allowed_repo_root is rejected."""
    root = tmp_path / "repos"
    root.mkdir(parents=True)
    outside = tmp_path / "secret_volume"
    outside.mkdir(parents=True)

    config = AuditConfig(
        repo_url=str(outside),
        repo_name="secret",
        trusted_source=True,
        allowed_repo_root=str(root),
    )

    with pytest.raises(PermissionError, match="escapes allowed repository root"):
        _resolve_repo_path(config)


@pytest.mark.unit
def test_resolve_repo_path_trusted_source_rejects_symlink_escape(tmp_path: Path):
    """When trusted_source=True, a symlink inside allowed_root pointing outside is rejected."""
    root = tmp_path / "repos"
    root.mkdir(parents=True)
    outside = tmp_path / "secret_volume"
    outside.mkdir(parents=True)

    link = root / "symlink_repo"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks not supported in this environment")

    config = AuditConfig(
        repo_url=str(link),
        repo_name="secret-via-link",
        trusted_source=True,
        allowed_repo_root=str(root),
    )

    with pytest.raises(PermissionError, match="escapes allowed repository root"):
        _resolve_repo_path(config)


@pytest.mark.unit
def test_resolve_repo_path_trusted_source_rejects_nonexistent_directory(tmp_path: Path):
    """When trusted_source=True, nonexistent directories fail closed."""
    root = tmp_path / "repos"
    root.mkdir(parents=True)
    nonexistent = root / "does_not_exist"

    config = AuditConfig(
        repo_url=str(nonexistent),
        repo_name="nonexistent",
        trusted_source=True,
        allowed_repo_root=str(root),
    )

    with pytest.raises(FileNotFoundError, match="does not exist or is not a directory"):
        _resolve_repo_path(config)


@pytest.mark.unit
def test_resolve_repo_path_untrusted_fails_closed_on_clone_error(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When trusted_source=False and git clone fails, it must raise RuntimeError and never fall back to cwd."""
    config = AuditConfig(
        repo_url="https://github.com/owner/nonexistent-repo.git",
        repo_name="owner/nonexistent-repo",
        trusted_source=False,
        cache_dir=str(tmp_path / "audit_cache"),
    )

    def fake_subprocess_run(cmd, **kwargs):
        raise subprocess.CalledProcessError(
            returncode=128,
            cmd=cmd,
            stderr="fatal: repository 'https://github.com/owner/nonexistent-repo.git' not found",
        )

    monkeypatch.setattr("subprocess.run", fake_subprocess_run)

    with pytest.raises(RuntimeError, match="Failed to clone repository from 'https://github.com/owner/nonexistent-repo.git':"):
        _resolve_repo_path(config)


@pytest.mark.unit
def test_resolve_repo_path_untrusted_clones_to_cache_dir(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """When trusted_source=False and git clone succeeds, target path in cache_dir is returned."""
    cache_dir = tmp_path / "audit_cache"
    config = AuditConfig(
        repo_url="https://github.com/owner/good-repo.git",
        repo_name="owner/good-repo",
        trusted_source=False,
        cache_dir=str(cache_dir),
    )

    def fake_subprocess_run(cmd, **kwargs):
        # cmd: ["git", "clone", "--depth", "1", "--single-branch", "--branch", branch, repo_url, str(target)]
        target_path = Path(cmd[-1])
        target_path.mkdir(parents=True, exist_ok=True)
        class Res:
            returncode = 0
            stderr = ""
            stdout = ""
        return Res()

    monkeypatch.setattr("subprocess.run", fake_subprocess_run)

    resolved, _ = _resolve_repo_path(config)
    assert resolved.is_relative_to(cache_dir.resolve())
    assert resolved.exists()

