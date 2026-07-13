"""Unit tests for the AuditOrchestrator LangGraph state machine.

These tests exercise the compiled graph end-to-end on the current repository
and assert that the expected artifacts (scorecard, findings, report) are
produced.
"""

from __future__ import annotations

import asyncio

import pytest

from layer4_agents.agents.audit_orchestrator.graph import (
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
    )

    async def _failing_node(state):
        return {"error": "async injected failure", "current_step": "analyze_code"}

    monkeypatch.setattr(
        "layer4_agents.agents.audit_orchestrator.graph.node_analyze_code",
        _failing_node,
    )

    with pytest.raises(RuntimeError, match="async injected failure"):
        await run_audit_async(config, trigger_type="manual")
