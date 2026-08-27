"""Markdown report generator for the AuditOrchestrator agent.

Produces the full repository health audit report and incremental diff reports
using section generators that match SPEC Section 8.1.
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import UTC, datetime

from .models import AuditArea, Finding, FindingStatus, Scorecard, Sprint
from .scoring import score_to_grade

# ---------------------------------------------------------------------------
# Public report builders
# ---------------------------------------------------------------------------


def generate_full_report(scorecard: Scorecard, sprints: Sequence[Sprint]) -> str:
    """Generate the complete Markdown audit report."""
    sections = [
        generate_header(scorecard),
        generate_executive_summary(scorecard),
        generate_reconnaissance(scorecard),
        generate_scorecard_table(scorecard),
        generate_findings_register(scorecard.findings),
        generate_governance_gap_matrix(scorecard),
        generate_agent_readiness(scorecard),
        generate_quality_gates_plan(scorecard),
        generate_quick_wins(scorecard.findings),
        generate_sprint_roadmap(sprints),
        generate_roadmap_summary(sprints),
        generate_projected_scorecard(scorecard, sprints),
        generate_roadmap_draft(sprints),
        generate_verification_appendix(scorecard),
    ]
    return "\n\n---\n\n".join(sections)


def generate_diff_report(current: Scorecard, previous: Scorecard) -> str:
    """Generate an incremental diff report between two scorecards."""
    current_ids = {f.id for f in current.findings}
    previous_ids = {f.id for f in previous.findings}

    new_findings = [f for f in current.findings if f.id not in previous_ids]
    resolved_findings = [f for f in previous.findings if f.id not in current_ids]

    score_delta = current.overall_score - previous.overall_score
    grade_delta = _grade_delta(current.overall_grade, previous.overall_grade)

    lines = [
        "# Incremental Audit Diff Report",
        "",
        f"**Repository:** `{current.repo_name}`",
        f"**Current run:** {current.audit_timestamp.isoformat()}",
        f"**Previous run:** {previous.audit_timestamp.isoformat()}",
        "",
        "## Score Changes",
        "",
        f"- Overall score: **{previous.overall_score}** → **{current.overall_score}** "
        f"({_format_delta(score_delta)})",
        f"- Overall grade: **{previous.overall_grade}** → **{current.overall_grade}** "
        f"({_format_grade_delta(grade_delta)})",
        f"- Trend: **{current.trend}**",
        "",
        "### Area Score Changes",
        "",
        "| Area | Previous | Current | Change |",
        "|------|----------|---------|--------|",
    ]

    prev_by_area = {a.area.value: a for a in previous.area_scores}
    for area in current.area_scores:
        area_name = _escape_md_table_cell(area.area.value)
        prev = prev_by_area.get(area.area.value)
        if prev:
            delta = area.score - prev.score
            prev_grade = _escape_md_table_cell(prev.grade or "")
            grade = _escape_md_table_cell(area.grade or "")
            lines.append(
                f"| {area_name} | {prev.score} ({prev_grade}) | "
                f"{area.score} ({grade}) | {_format_delta(delta)} |"
            )
        else:
            grade = _escape_md_table_cell(area.grade or "")
            lines.append(f"| {area_name} | — | {area.score} ({grade}) | new |")

    lines.extend(["", "## New Findings", ""])
    if new_findings:
        for finding in new_findings:
            lines.append(_finding_bullet(finding))
    else:
        lines.append("_No new findings since the previous audit._")

    lines.extend(["", "## Resolved Findings", ""])
    if resolved_findings:
        for finding in resolved_findings:
            lines.append(f"- ~~{finding.id}~~ — {finding.observed_fact}")
    else:
        lines.append("_No findings were resolved since the previous audit._")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Section generators
# ---------------------------------------------------------------------------


def generate_header(scorecard: Scorecard) -> str:
    """Generate the report header section."""
    commit = scorecard.commit_sha or "unknown"
    return (
        f"# Repository Health Audit: `{scorecard.repo_name}`\n\n"
        f"- **Branch:** `{scorecard.branch}`\n"
        f"- **Commit:** `{commit}`\n"
        f"- **Audit timestamp:** {scorecard.audit_timestamp.isoformat()}\n"
        f"- **Overall score:** {scorecard.overall_score}/100 ({scorecard.overall_grade})\n"
        f"- **Overall confidence:** {scorecard.confidence.value}\n"
        f"- **Trend:** {scorecard.trend}"
    )


def generate_executive_summary(scorecard: Scorecard) -> str:
    """Generate the executive summary section."""
    open_count = len(scorecard.open_findings())
    total = len(scorecard.findings)
    critical = len([f for f in scorecard.findings if f.severity.value == "critical"])
    high = len([f for f in scorecard.findings if f.severity.value == "high"])

    summary = scorecard.executive_summary or (
        f"The repository scored **{scorecard.overall_score}/100 ({scorecard.overall_grade})** "
        f"with **{open_count}** open findings out of **{total}** total. "
        f"There are **{critical}** critical and **{high}** high-severity findings requiring attention."
    )

    return (
        "## Executive Summary\n\n"
        f"{summary}\n\n"
        "### Key Metrics\n\n"
        f"- **Overall score:** {scorecard.overall_score} ({scorecard.overall_grade})\n"
        f"- **Open findings:** {open_count}/{total}\n"
        f"- **Critical findings:** {critical}\n"
        f"- **High findings:** {high}\n"
        f"- **Files analyzed:** {scorecard.total_files}\n"
        f"- **Directories analyzed:** {scorecard.total_directories}\n"
        f"- **Commits analyzed:** {scorecard.total_commits}\n"
        f"- **Contributors analyzed:** {scorecard.total_contributors}"
        + _git_completeness_note(scorecard)
    )


def _git_completeness_note(scorecard: Scorecard) -> str:
    """Return a markdown note signalling incomplete git metrics, if any.

    Includes only each structured warning's safe ``message``; never raw git
    output or contributor email addresses.
    """
    messages = [
        w["message"]
        for w in scorecard.git_warnings
        if isinstance(w, dict) and w.get("message")
    ]
    if not messages:
        return ""
    lines = "\n".join(f"- {msg}" for msg in messages)
    return (
        "\n\n> **Note:** Some git metrics were incomplete (timed out, truncated "
        f"or failed); reported counts may be understated.\n{lines}"
    )


def generate_reconnaissance(scorecard: Scorecard) -> str:
    """Generate the reconnaissance / repository context section."""
    return (
        "## Reconnaissance\n\n"
        "Basic repository telemetry collected at audit time:\n\n"
        f"- **Repository:** `{scorecard.repo_name}`\n"
        f"- **Branch:** `{scorecard.branch}`\n"
        f"- **Commit SHA:** `{scorecard.commit_sha or 'unknown'}`\n"
        f"- **Version/tag:** `{scorecard.version or 'unknown'}`\n"
        f"- **Total files:** {scorecard.total_files}\n"
        f"- **Total directories:** {scorecard.total_directories}\n"
        f"- **Total commits:** {scorecard.total_commits}\n"
        f"- **Total contributors:** {scorecard.total_contributors}\n"
        f"- **Audit timestamp:** {scorecard.audit_timestamp.isoformat()}"
    )


def generate_scorecard_table(scorecard: Scorecard) -> str:
    """Generate the scorecard area-breakdown table."""
    lines = [
        "## Scorecard",
        "",
        "| Area | Weight | Score | Grade | Confidence | Trend Risk | Findings |",
        "|------|--------|-------|-------|------------|------------|----------|",
    ]
    for area in scorecard.area_scores:
        area_name = _escape_md_table_cell(area.area.value)
        grade = _escape_md_table_cell(area.grade or "")
        confidence = _escape_md_table_cell(area.confidence.value)
        trend_risk = _escape_md_table_cell(area.trend_risk or "")
        lines.append(
            f"| {area_name} | {area.weight:.0%} | {area.score} | "
            f"{grade} | {confidence} | {trend_risk} | "
            f"{area.findings_count} |"
        )
    lines.extend(
        [
            "",
            f"**Overall:** {scorecard.overall_score}/100 ({scorecard.overall_grade}) — "
            f"{scorecard.confidence.value} confidence",
        ]
    )
    return "\n".join(lines)


def generate_findings_register(findings: Sequence[Finding]) -> str:
    """Generate the findings register table."""
    lines = [
        "## Findings Register",
        "",
        "| ID | Severity | Area | Status | Effort | Owner | Evidence |",
        "|----|----------|------|--------|--------|-------|----------|",
    ]
    for finding in sorted(findings, key=lambda f: (f.severity.value, f.id)):
        evidence = _escape_md_table_cell(finding.evidence)
        owner = _escape_md_table_cell(finding.owner)
        area = _escape_md_table_cell(finding.area.value)
        status = _escape_md_table_cell(finding.status.value)
        finding_id = _escape_md_table_cell(finding.id)
        severity = _escape_md_table_cell(finding.severity.value)
        effort = _escape_md_table_cell(finding.effort)
        lines.append(
            f"| {finding_id} | {severity} | {area} | {status} | {effort} | {owner} | `{evidence}` |"
        )
    return "\n".join(lines)


def _escape_md_table_cell(value: str) -> str:
    """Escape pipe and newline characters inside a Markdown table cell."""
    return value.replace("|", "\\|").replace("\r", "").replace("\n", " ")


def generate_governance_gap_matrix(scorecard: Scorecard) -> str:
    """Generate a governance gap matrix from area scores."""
    lines = [
        "## Governance Gap Matrix",
        "",
        "| Area | Grade | Risk | Diagnosis |",
        "|------|-------|------|-----------|",
    ]
    for area in scorecard.area_scores:
        risk = _risk_level(area.score)
        area_name = _escape_md_table_cell(area.area.value)
        grade = _escape_md_table_cell(area.grade or "")
        diagnosis = _escape_md_table_cell(area.diagnosis or "")
        lines.append(f"| {area_name} | {grade} | {risk} | {diagnosis} |")
    return "\n".join(lines)


def generate_agent_readiness(scorecard: Scorecard) -> str:
    """Generate the AI-agent readiness section."""
    agent_area = scorecard.get_area_score(AuditArea.AGENT_READINESS)
    if agent_area is None:
        return "## Agent Readiness\n\n_No agent readiness data available._"

    agent_findings = [f for f in scorecard.findings if f.area == AuditArea.AGENT_READINESS]
    return (
        "## Agent Readiness\n\n"
        f"**Score:** {agent_area.score}/100 ({agent_area.grade}) — "
        f"{agent_area.confidence.value} confidence\n\n"
        f"**Diagnosis:** {agent_area.diagnosis}\n\n"
        f"**Findings in this area:** {len(agent_findings)}\n\n"
        + (
            "### Key agent-readiness gaps\n\n"
            + "\n".join(_finding_bullet(f) for f in agent_findings)
            if agent_findings
            else "_No agent-readiness findings._"
        )
    )


def generate_quality_gates_plan(scorecard: Scorecard) -> str:
    """Generate the quality gates remediation plan section."""
    cicd = scorecard.get_area_score(AuditArea.CICD)
    testing = scorecard.get_area_score(AuditArea.TESTING)
    quality_findings = [
        f for f in scorecard.findings if f.area in (AuditArea.CICD, AuditArea.TESTING)
    ]
    return (
        "## Quality Gates Plan\n\n"
        "Improvements needed in CI/CD and testing to raise confidence and score.\n\n"
        f"- **CI/CD score:** {cicd.score if cicd else 'N/A'} "
        f"({cicd.grade if cicd else 'N/A'})\n"
        f"- **Testing score:** {testing.score if testing else 'N/A'} "
        f"({testing.grade if testing else 'N/A'})\n"
        f"- **Related findings:** {len(quality_findings)}\n\n"
        + (
            "### Priority actions\n\n" + "\n".join(_finding_bullet(f) for f in quality_findings)
            if quality_findings
            else "_No CI/CD or testing findings._"
        )
    )


def generate_quick_wins(findings: Sequence[Finding]) -> str:
    """Generate the quick wins section (low effort, high impact)."""
    quick = [
        f
        for f in findings
        if f.effort in {"XS", "S"}
        and f.status in (FindingStatus.OPEN, FindingStatus.IN_PROGRESS)
        and f.severity.value in {"critical", "high", "medium"}
    ]
    quick.sort(key=lambda f: (f.severity.value, f.effort))

    lines = [
        "## Quick Wins",
        "",
        "Low-effort, high-impact fixes that can be completed quickly.",
        "",
    ]
    if quick:
        lines.extend(_finding_bullet(f) for f in quick)
    else:
        lines.append("_No quick wins identified._")
    return "\n".join(lines)


def generate_sprint_roadmap(sprints: Sequence[Sprint]) -> str:
    """Generate the sprint roadmap table."""
    lines = [
        "## Sprint Roadmap",
        "",
        "| Sprint | Theme | Status | Findings | Projected Impact |",
        "|--------|-------|--------|----------|------------------|",
    ]
    for sprint in sorted(sprints, key=lambda s: s.id):
        theme = _escape_md_table_cell(sprint.theme)
        status = _escape_md_table_cell(sprint.status.value)
        lines.append(
            f"| {sprint.id} | {theme} | {status} | "
            f"{len(sprint.findings_targeted)} | +{sprint.score_impact_projected} pts |"
        )
    total_impact = sum(s.score_impact_projected for s in sprints)
    lines.extend(["", f"**Total projected score impact:** +{total_impact} points"])
    return "\n".join(lines)


def generate_roadmap_summary(sprints: Sequence[Sprint]) -> str:
    """Generate a narrative summary of the remediation roadmap."""
    if not sprints:
        return "## Roadmap Summary\n\n_No remediation sprints planned._"

    total_impact = sum(s.score_impact_projected for s in sprints)
    in_progress = [s for s in sprints if s.status.value == "in_progress"]
    completed = [s for s in sprints if s.status.value == "completed"]

    return (
        "## Roadmap Summary\n\n"
        f"The remediation plan consists of **{len(sprints)}** sprints with a "
        f"projected total score improvement of **+{total_impact} points**. "
        f"**{len(completed)}** sprints are completed and **{len(in_progress)}** "
        "are in progress. Each sprint groups related findings by theme to "
        "maximize focus and minimize context switching."
    )


def generate_projected_scorecard(
    scorecard: Scorecard,
    sprints: Sequence[Sprint],
) -> str:
    """Generate a projected scorecard assuming all sprints are completed."""
    total_projected_impact = sum(s.score_impact_projected for s in sprints)
    projected_overall = min(100, scorecard.overall_score + total_projected_impact)
    projected_grade = score_to_grade(projected_overall)

    lines = [
        "## Projected Scorecard",
        "",
        f"Assuming all planned sprints are completed, the projected overall score "
        f"is **{projected_overall}/100 ({projected_grade})**, an improvement of "
        f"**+{total_projected_impact} points**.",
        "",
        "| Area | Current | Projected |",
        "|------|---------|-----------|",
    ]

    # Distribute projected impact proportionally by weight for illustration.
    total_weight = sum(a.weight for a in scorecard.area_scores) or 1.0
    for area in scorecard.area_scores:
        share = (area.weight / total_weight) * total_projected_impact
        projected = min(100, round(area.score + share))
        area_name = _escape_md_table_cell(area.area.value)
        grade = _escape_md_table_cell(area.grade or "")
        lines.append(f"| {area_name} | {area.score} ({grade}) | {projected} |")

    return "\n".join(lines)


def generate_roadmap_draft(sprints: Sequence[Sprint]) -> str:
    """Generate a detailed roadmap draft with objectives and deliverables."""
    lines = ["## Roadmap Draft", ""]
    if not sprints:
        lines.append("_No sprints planned._")
        return "\n".join(lines)

    for sprint in sorted(sprints, key=lambda s: s.id):
        lines.append(f"### Sprint {sprint.id}: {sprint.theme}")
        lines.append("")
        lines.append(f"**Status:** {sprint.status.value}")
        lines.append(f"**Projected impact:** +{sprint.score_impact_projected} points")
        lines.append("")
        lines.append("**Objectives:**")
        for obj in sprint.objectives:
            lines.append(f"- {obj}")
        lines.append("")
        lines.append("**Deliverables:**")
        for deliv in sprint.deliverables:
            lines.append(f"- {deliv}")
        lines.append("")
        lines.append(f"**Findings targeted:** {', '.join(sprint.findings_targeted) or 'None'}")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def generate_verification_appendix(scorecard: Scorecard) -> str:
    """Generate the verification appendix section."""
    return (
        "## Verification Appendix\n\n"
        "Use the following steps to reproduce and verify this audit:\n\n"
        f"1. Check out branch `{scorecard.branch}` at commit `{scorecard.commit_sha or 'HEAD'}`.\n"
        "2. Run the static analyzers (git, code, documentation).\n"
        "3. Compare generated findings against the Findings Register above.\n"
        "4. Validate area scores using the documented scoring rubric.\n"
        "5. Re-run after each sprint and verify the projected score impact.\n\n"
        "### Audit metadata\n\n"
        f"- **Report generated at:** {datetime.now(UTC).isoformat()}\n"
        f"- **Repository:** {scorecard.repo_name}\n"
        f"- **Overall score:** {scorecard.overall_score} ({scorecard.overall_grade})\n"
        f"- **Total findings:** {len(scorecard.findings)}"
    )


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _finding_bullet(finding: Finding) -> str:
    """Return a markdown bullet for a finding."""
    return (
        f"- **{finding.id}** ({finding.severity.value}, {finding.effort}) — "
        f"{finding.observed_fact} _[{finding.status.value}]_"
    )


def _risk_level(score: int) -> str:
    """Return a qualitative risk level for a numeric score."""
    if score >= 80:
        return "Low"
    if score >= 60:
        return "Medium"
    return "High"


# Grade order from best to worst for delta calculations.
_GRADE_ORDER = [
    "A+",
    "A",
    "A-",
    "B+",
    "B",
    "B-",
    "C+",
    "C",
    "C-",
    "D+",
    "D",
    "D-",
    "F",
]


def _grade_delta(current: str, previous: str) -> int:
    """Return numeric grade improvement (positive) or regression (negative)."""
    try:
        current_idx = _GRADE_ORDER.index(current.upper())
        prev_idx = _GRADE_ORDER.index(previous.upper())
    except ValueError:
        return 0
    return prev_idx - current_idx


def _format_delta(delta: int) -> str:
    """Format a numeric delta with sign and arrow."""
    if delta > 0:
        return f"↗ +{delta}"
    if delta < 0:
        return f"↘ {delta}"
    return "→ 0"


def _format_grade_delta(delta: int) -> str:
    """Format a grade-level delta."""
    if delta > 0:
        return f"improved {delta} grade level(s)"
    if delta < 0:
        return f"regressed {abs(delta)} grade level(s)"
    return "unchanged"


__all__ = [
    "generate_full_report",
    "generate_diff_report",
    "generate_header",
    "generate_executive_summary",
    "generate_reconnaissance",
    "generate_scorecard_table",
    "generate_findings_register",
    "generate_governance_gap_matrix",
    "generate_agent_readiness",
    "generate_quality_gates_plan",
    "generate_quick_wins",
    "generate_sprint_roadmap",
    "generate_roadmap_summary",
    "generate_projected_scorecard",
    "generate_roadmap_draft",
    "generate_verification_appendix",
]
