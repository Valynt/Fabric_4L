"""Unit tests for the AuditOrchestrator LangGraph state machine.

These tests exercise the compiled graph end-to-end on the current repository
and assert that the expected artifacts (scorecard, findings, report) are
produced.
"""

from __future__ import annotations

import pytest

from layer4_agents.agents.audit_orchestrator.graph import (
    create_audit_graph,
    run_audit,
)
from layer4_agents.agents.audit_orchestrator.models import AuditArea, AuditConfig


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
