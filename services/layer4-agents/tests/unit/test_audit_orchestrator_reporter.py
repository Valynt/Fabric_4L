"""Unit tests for AuditOrchestrator report generator."""

from __future__ import annotations

from typing import Any

import pytest

from layer4_agents.agents.audit_orchestrator.models import (
    Confidence,
    Finding,
    FindingStatus,
    Severity,
    Sprint,
)
from layer4_agents.agents.audit_orchestrator.reporter import (
    generate_diff_report,
    generate_findings_register,
    generate_full_report,
)
from layer4_agents.agents.audit_orchestrator.scoring import build_scorecard


@pytest.fixture
def sample_finding() -> Finding:
    """Return a representative open finding."""
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
def quick_finding() -> Finding:
    """Return a low-effort finding suitable for the quick-wins section."""
    return Finding(
        id="DOC-001",
        severity=Severity.MEDIUM,
        confidence=Confidence.HIGH,
        area="H: Documentation, Decisions, Knowledge",
        evidence="README.md:1",
        observed_fact="Missing setup section",
        inference_risk="Contributors struggle to onboard",
        business_impact="Slower contributor velocity",
        recommended_fix="Add setup instructions",
        effort="XS",
        risk_of_change="Low",
        owner="docs-team",
        analyzer_type="doc",
    )


@pytest.fixture
def sample_scorecard(sample_finding: Finding, quick_finding: Finding) -> Any:
    """Return a scorecard with findings across multiple areas."""
    return build_scorecard(
        repo_name="owner/repo",
        findings=[sample_finding, quick_finding],
        branch="main",
        commit_sha="abc123",
        total_files=120,
        total_directories=15,
        total_commits=42,
        total_contributors=5,
    )


@pytest.fixture
def sample_sprints(sample_finding: Finding, quick_finding: Finding) -> list[Sprint]:
    """Return a small remediation roadmap."""
    return [
        Sprint(
            id=1,
            theme="Fix correctness gaps",
            objectives=["Add idempotency handling"],
            deliverables=["PR with idempotency keys"],
            findings_targeted=[sample_finding.id],
            score_impact_projected=5,
        ),
        Sprint(
            id=2,
            theme="Improve documentation",
            objectives=["Complete README setup section"],
            deliverables=["Updated README"],
            findings_targeted=[quick_finding.id],
            score_impact_projected=3,
        ),
    ]


EXPECTED_SECTIONS = [
    "# Repository Health Audit:",
    "## Executive Summary",
    "## Reconnaissance",
    "## Scorecard",
    "## Findings Register",
    "## Governance Gap Matrix",
    "## Agent Readiness",
    "## Quality Gates Plan",
    "## Quick Wins",
    "## Sprint Roadmap",
    "## Roadmap Summary",
    "## Projected Scorecard",
    "## Roadmap Draft",
    "## Verification Appendix",
]


@pytest.mark.unit
def test_full_report_contains_all_sections(
    sample_scorecard: Any,
    sample_sprints: list[Sprint],
) -> None:
    report = generate_full_report(sample_scorecard, sample_sprints)
    missing = [heading for heading in EXPECTED_SECTIONS if heading not in report]
    assert not missing, f"Missing sections: {missing}"


@pytest.mark.unit
def test_full_report_includes_key_findings(
    sample_scorecard: Any,
    sample_sprints: list[Sprint],
) -> None:
    report = generate_full_report(sample_scorecard, sample_sprints)
    assert sample_scorecard.findings[0].id in report
    assert sample_scorecard.findings[1].id in report
    assert sample_scorecard.repo_name in report
    assert str(sample_scorecard.overall_score) in report


@pytest.mark.unit
def test_full_report_quick_wins_lists_low_effort_items(
    sample_scorecard: Any,
    sample_sprints: list[Sprint],
) -> None:
    report = generate_full_report(sample_scorecard, sample_sprints)
    quick_heading_idx = report.index("## Quick Wins")
    next_section_idx = report.index("## Sprint Roadmap")
    quick_section = report[quick_heading_idx:next_section_idx]
    assert sample_scorecard.findings[1].id in quick_section


@pytest.mark.unit
def test_diff_report_shows_new_and_resolved_findings() -> None:
    previous_finding = Finding(
        id="OLD-001",
        severity=Severity.LOW,
        confidence=Confidence.MEDIUM,
        area="H: Documentation, Decisions, Knowledge",
        evidence="README.md",
        observed_fact="Old issue",
        inference_risk="Minor",
        business_impact="Low",
        recommended_fix="Fix it",
        effort="XS",
        risk_of_change="Low",
        owner="team",
        status=FindingStatus.RESOLVED,
        analyzer_type="doc",
    )
    current_finding = Finding(
        id="NEW-001",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        area="C: Correctness, Data Integrity, Contracts",
        evidence="src/app.py:42",
        observed_fact="New issue",
        inference_risk="Major",
        business_impact="High",
        recommended_fix="Fix it now",
        effort="M",
        risk_of_change="Low",
        owner="team",
        analyzer_type="code",
    )

    previous = build_scorecard(repo_name="owner/repo", findings=[previous_finding])
    current = build_scorecard(repo_name="owner/repo", findings=[current_finding])

    report = generate_diff_report(current, previous)
    assert "## New Findings" in report
    assert "## Resolved Findings" in report
    assert "NEW-001" in report
    assert "OLD-001" in report
    assert "## Score Changes" in report


@pytest.mark.unit
def test_diff_report_shows_score_changes() -> None:
    previous = build_scorecard(repo_name="owner/repo", findings=[])
    # Force a lower overall score by adding a high-severity finding.
    bad_finding = Finding(
        id="SEC-001",
        severity=Severity.CRITICAL,
        confidence=Confidence.HIGH,
        area="E: Security and Supply Chain",
        evidence="src/auth.py:1",
        observed_fact="No guardrails",
        inference_risk="Injection",
        business_impact="High",
        recommended_fix="Add guardrails",
        effort="L",
        risk_of_change="High",
        owner="team",
        analyzer_type="code",
    )
    current = build_scorecard(repo_name="owner/repo", findings=[bad_finding])

    report = generate_diff_report(current, previous)
    assert "Overall score" in report
    assert "Overall grade" in report
    assert "Trend" in report
    # Verify area change rows are emitted.
    assert "| Area | Previous | Current | Change |" in report


@pytest.mark.unit
def test_diff_report_handles_no_changes() -> None:
    scorecard = build_scorecard(repo_name="owner/repo", findings=[])
    report = generate_diff_report(scorecard, scorecard)
    assert "_No new findings since the previous audit._" in report
    assert "_No findings were resolved since the previous audit._" in report
    assert "→ 0" in report


@pytest.mark.unit
def test_findings_register_escapes_pipes_in_cells() -> None:
    """Pipe characters inside table cells must be escaped so Markdown renders correctly."""
    finding = Finding(
        id="COR-PIPE",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        area="C: Correctness, Data Integrity, Contracts",
        evidence="src/a.py:1|src/b.py:2",
        observed_fact="Value contains a pipe",
        inference_risk="Table breaks",
        business_impact="Low",
        recommended_fix="Escape it",
        effort="XS",
        risk_of_change="Low",
        owner="team|platform",
        analyzer_type="code",
    )
    report = generate_findings_register([finding])
    assert "src/a.py:1\\|src/b.py:2" in report
    assert "team\\|platform" in report
    # Verify the escaped pipes prevent extra Markdown table columns.
    row = [line for line in report.splitlines() if line.startswith("| COR-PIPE")][0]
    assert row.count("\\|") == 2
    # Without escaping there would be 4 unescaped pipes; escaping keeps 8 separators.
    unescaped_pipes = row.replace("\\|", "").count("|")
    assert unescaped_pipes == 8
