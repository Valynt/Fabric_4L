"""Integration smoke test for the AuditOrchestrator agent.

Runs the full audit graph end-to-end on the current repository and asserts
that a complete scorecard and report are produced.
"""

from __future__ import annotations

import subprocess
from urllib.parse import urlparse

import pytest

from layer4_agents.agents.audit_orchestrator import run_audit
from layer4_agents.agents.audit_orchestrator.models import AuditArea, AuditConfig


def _derive_repo_name() -> str:
    """Derive owner/repo from the working tree origin remote, or fall back."""
    try:
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            capture_output=True,
            text=True,
            check=True,
            timeout=5,
        )
        url = result.stdout.strip()
    except Exception:
        return "local/audit-target"

    if url.endswith(".git"):
        url = url[:-4]

    path: str
    if url.startswith(("http://", "https://")):
        parsed = urlparse(url)
        path = parsed.path.lstrip("/")
    elif "@" in url:
        # SSH-ish: git@host:owner/repo or git@host/owner/repo
        remainder = url.split("@", 1)[1]
        if ":" in remainder:
            path = remainder.split(":", 1)[1]
        elif "/" in remainder:
            path = remainder.split("/", 1)[1]
        else:
            path = remainder
    else:
        path = url

    if path.count("/") == 1 and ":" not in path:
        return path
    return "local/audit-target"


@pytest.mark.unit
@pytest.mark.timeout(30)
def test_audit_orchestrator_smoke_on_current_repo():
    """A full audit run on the current repo must produce a scorecard and report."""
    config = AuditConfig(
        repo_url=".",
        repo_name=_derive_repo_name(),
        incremental=False,
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
    assert {a.area for a in scorecard.area_scores} == set(AuditArea)

    for area_score in scorecard.area_scores:
        assert 0 <= area_score.score <= 100
        assert area_score.weight > 0
        assert area_score.grade
        assert area_score.diagnosis

    assert state["report_markdown"]
    assert "# Repository Health Audit" in state["report_markdown"]
