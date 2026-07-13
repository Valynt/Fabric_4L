"""Integration smoke test for the AuditOrchestrator agent.

Runs the full audit graph end-to-end on the current repository and asserts
that a complete scorecard and report are produced.
"""

from __future__ import annotations

import pytest

from layer4_agents.agents.audit_orchestrator import run_audit
from layer4_agents.agents.audit_orchestrator.models import AuditArea, AuditConfig


@pytest.mark.unit
@pytest.mark.timeout(120)
def test_audit_orchestrator_smoke_on_current_repo():
    """A full audit run on the current repo must produce a scorecard and report."""
    config = AuditConfig(
        repo_url=".",
        repo_name="bmsull560/Fabric_4L",
        incremental=False,
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
    assert {a.area for a in scorecard.area_scores} == set(AuditArea)

    for area_score in scorecard.area_scores:
        assert 0 <= area_score.score <= 100
        assert area_score.weight > 0
        assert area_score.grade
        assert area_score.diagnosis

    assert state["report_markdown"]
    assert "# Repository Health Audit" in state["report_markdown"]
