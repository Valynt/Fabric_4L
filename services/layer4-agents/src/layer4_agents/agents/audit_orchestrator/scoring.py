"""
Score calculation engine for the AuditOrchestrator agent.

This module implements the scoring algorithms used to compute area scores,
overall scorecards, and trend detection. It follows the SPEC scoring rubric
with baseline deduction, confidence multiplier, and area-specific adjustments.

Key functions:

- :func:`calculate_overall_score` — Weighted overall score + grade
- :func:`score_to_grade` — Numeric score → letter grade
- :func:`calculate_area_score` — Per-area scoring with finding deductions
- :func:`detect_trend` — Trend detection from historical scores
- :func:`build_scorecard` — Build a full Scorecard from findings and metrics
"""

from __future__ import annotations

import statistics
from typing import Any

from .models import (
    DEFAULT_AREA_WEIGHTS,
    DEFAULT_GRADE_THRESHOLDS,
    AreaScore,
    AuditArea,
    Confidence,
    Finding,
    Scorecard,
    confidence_multiplier,
    severity_deduction,
)

# ---------------------------------------------------------------------------
# Grade thresholds (canonical copy used by score_to_grade)
# ---------------------------------------------------------------------------

GRADE_THRESHOLDS: dict[str, tuple[int, int]] = DEFAULT_GRADE_THRESHOLDS.copy()

# Ordered from highest to lowest for grade-to-index mapping.
GRADE_ORDER: list[str] = [
    "A+", "A", "A-",
    "B+", "B", "B-",
    "C+", "C", "C-",
    "D+", "D", "D-",
    "F",
]

# ---------------------------------------------------------------------------
# Area-specific metric adjustment handlers
# ---------------------------------------------------------------------------

# Mapping of AuditArea → metric key patterns that trigger deductions.
# Each handler returns a float deduction (≥ 0) to apply to the area score.


def _adjust_architecture(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Architecture area.

    Deducts for:
    - Oversized modules (>1400 lines for Python, >800 for JS/TS)
    - Relative imports
    - Duplicate files (by content hash)
    - Shared package size

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    # Oversized modules
    oversized_python = metrics.get("oversized_python_modules", 0)
    oversized_js = metrics.get("oversized_js_modules", 0)
    deduction += min(oversized_python * 2.0, 10.0)
    deduction += min(oversized_js * 1.5, 8.0)

    # Relative imports
    relative_imports = metrics.get("relative_import_count", 0)
    deduction += min(relative_imports * 0.5, 5.0)

    # Duplicate files
    duplicate_files = metrics.get("duplicate_file_count", 0)
    deduction += min(duplicate_files * 1.5, 6.0)

    # Shared package size (in files)
    shared_pkg_files = metrics.get("shared_package_file_count", 0)
    if shared_pkg_files > 50:
        deduction += min((shared_pkg_files - 50) * 0.1, 5.0)

    return float(deduction)


def _adjust_code_quality(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Code Quality area.

    Deducts for:
    - Disabled type checking (mypy overrides)
    - Bare except clauses
    - Inconsistent linting configuration
    - Low type annotation coverage

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    # Disabled mypy error codes
    disabled_codes = metrics.get("mypy_disabled_codes", 0)
    deduction += min(disabled_codes * 1.0, 8.0)

    # Bare except count
    bare_excepts = metrics.get("bare_except_count", 0)
    deduction += min(bare_excepts * 2.0, 10.0)

    # Inconsistent linting (boolean or count)
    lint_inconsistent = metrics.get("inconsistent_linting", False)
    if lint_inconsistent:
        deduction += 4.0

    # Type annotation coverage (0.0–1.0)
    type_coverage = metrics.get("type_annotation_coverage", 1.0)
    if type_coverage < 0.8:
        deduction += min((0.8 - type_coverage) * 20.0, 10.0)

    # TODO/FIXME count
    todo_count = metrics.get("todo_fixme_count", 0)
    deduction += min(todo_count * 0.3, 4.0)

    return float(deduction)


def _adjust_correctness(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Correctness area.

    Deducts for:
    - Contract drift
    - Missing idempotency
    - Migration issues

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    contract_drift = metrics.get("contract_drift_count", 0)
    deduction += min(contract_drift * 2.5, 10.0)

    missing_idempotency = metrics.get("missing_idempotency_count", 0)
    deduction += min(missing_idempotency * 2.0, 8.0)

    migration_issues = metrics.get("migration_issue_count", 0)
    deduction += min(migration_issues * 3.0, 10.0)

    return float(deduction)


def _adjust_testing(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Testing area.

    Deducts for:
    - Low test coverage
    - Missing quality gates
    - Slow tests
    - No parallel execution support

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    # Test coverage (0.0–1.0)
    coverage = metrics.get("test_coverage", 1.0)
    if coverage < 0.7:
        deduction += min((0.7 - coverage) * 30.0, 15.0)

    # Missing quality gates (count or boolean)
    missing_gates = metrics.get("missing_quality_gates", 0)
    if isinstance(missing_gates, bool):
        deduction += 5.0 if missing_gates else 0.0
    else:
        deduction += min(missing_gates * 2.5, 8.0)

    # Slow test suite (seconds)
    test_duration = metrics.get("test_duration_seconds", 0)
    if test_duration > 300:
        deduction += min((test_duration - 300) / 60.0, 8.0)

    # No parallel execution
    no_parallel = metrics.get("no_parallel_tests", False)
    if no_parallel:
        deduction += 3.0

    # Flaky test count
    flaky_tests = metrics.get("flaky_test_count", 0)
    deduction += min(flaky_tests * 1.5, 6.0)

    return float(deduction)


def _adjust_security(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Security area.

    Deducts for:
    - Missing LLM guardrails
    - Injection risk vectors
    - Secret rotation gaps

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    missing_guardrails = metrics.get("missing_llm_guardrails", False)
    if missing_guardrails:
        deduction += 8.0

    injection_vectors = metrics.get("injection_vector_count", 0)
    deduction += min(injection_vectors * 3.0, 12.0)

    secret_gaps = metrics.get("secret_rotation_gaps", 0)
    deduction += min(secret_gaps * 2.5, 8.0)

    # Dependency vulnerabilities
    vuln_count = metrics.get("dependency_vulnerability_count", 0)
    deduction += min(vuln_count * 2.0, 10.0)

    return float(deduction)


def _adjust_cicd(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the CI/CD area.

    Deducts for:
    - Invisible branch protection
    - Slow CI pipeline
    - Missing timeouts

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    no_branch_protection = metrics.get("missing_branch_protection", False)
    if no_branch_protection:
        deduction += 6.0

    # Slow CI (minutes)
    ci_duration = metrics.get("ci_duration_minutes", 0)
    if ci_duration > 15:
        deduction += min((ci_duration - 15) * 0.5, 8.0)

    missing_timeouts = metrics.get("missing_ci_timeouts", False)
    if missing_timeouts:
        deduction += 4.0

    # Missing required checks
    missing_checks = metrics.get("missing_required_checks", 0)
    deduction += min(missing_checks * 2.0, 6.0)

    return float(deduction)


def _adjust_reliability(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Reliability area.

    Deducts for:
    - Missing circuit breakers
    - No graceful shutdown
    - Stale runbooks

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    missing_circuit_breakers = metrics.get("missing_circuit_breakers", False)
    if missing_circuit_breakers:
        deduction += 6.0

    no_graceful_shutdown = metrics.get("no_graceful_shutdown", False)
    if no_graceful_shutdown:
        deduction += 4.0

    stale_runbooks = metrics.get("stale_runbook_count", 0)
    deduction += min(stale_runbooks * 2.0, 6.0)

    # Missing health checks
    missing_health = metrics.get("missing_health_checks", False)
    if missing_health:
        deduction += 5.0

    # Missing observability
    missing_observability = metrics.get("missing_observability", False)
    if missing_observability:
        deduction += 4.0

    return float(deduction)


def _adjust_documentation(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Documentation area.

    Deducts for:
    - Missing root documentation files
    - Structural sprawl
    - Conflicting claims

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    # Missing required root docs
    missing_root_docs = metrics.get("missing_root_doc_count", 0)
    deduction += min(missing_root_docs * 2.0, 10.0)

    # Structural sprawl (excessive doc files scattered)
    doc_sprawl = metrics.get("documentation_sprawl_score", 0)
    if doc_sprawl > 5:
        deduction += min((doc_sprawl - 5) * 1.0, 5.0)

    # Conflicting claims
    conflicting_claims = metrics.get("conflicting_claim_count", 0)
    deduction += min(conflicting_claims * 2.5, 8.0)

    # Missing ADRs
    missing_adrs = metrics.get("missing_adr_count", 0)
    deduction += min(missing_adrs * 1.5, 6.0)

    # Outdated docs (fraction 0.0–1.0)
    outdated_docs = metrics.get("outdated_doc_fraction", 0.0)
    deduction += min(outdated_docs * 10.0, 8.0)

    return float(deduction)


def _adjust_agent_readiness(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Agent Readiness area.

    Deducts for:
    - Dangling references
    - Unconfigured tools
    - Missing guardrails

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    dangling_refs = metrics.get("dangling_reference_count", 0)
    deduction += min(dangling_refs * 1.5, 6.0)

    unconfigured_tools = metrics.get("unconfigured_tool_count", 0)
    deduction += min(unconfigured_tools * 2.0, 8.0)

    missing_agent_guardrails = metrics.get("missing_agent_guardrails", False)
    if missing_agent_guardrails:
        deduction += 5.0

    # Missing skill definitions
    missing_skills = metrics.get("missing_skill_definition_count", 0)
    deduction += min(missing_skills * 1.5, 5.0)

    return float(deduction)


def _adjust_dev_experience(metrics: dict[str, Any]) -> float:
    """Apply metric-based deductions for the Developer Experience area.

    Deducts for:
    - Missing debug configuration
    - Slow tests / build
    - Secret management barriers

    Args:
        metrics: Dictionary of collected metrics for the area.

    Returns:
        Total deduction (≥ 0) to subtract from the area score.
    """
    deduction = 0.0

    missing_debug_config = metrics.get("missing_debug_config", False)
    if missing_debug_config:
        deduction += 4.0

    # Build time (seconds)
    build_time = metrics.get("build_time_seconds", 0)
    if build_time > 120:
        deduction += min((build_time - 120) / 30.0, 6.0)

    # Secret management barrier
    secret_barrier = metrics.get("secret_management_barrier", False)
    if secret_barrier:
        deduction += 3.0

    # Local dev setup complexity
    setup_steps = metrics.get("local_setup_steps", 0)
    if setup_steps > 10:
        deduction += min((setup_steps - 10) * 0.5, 4.0)

    return deduction


# Registry mapping audit areas to their adjustment handlers
_AREA_ADJUSTERS = {
    AuditArea.ARCHITECTURE: _adjust_architecture,
    AuditArea.CODE_QUALITY: _adjust_code_quality,
    AuditArea.CORRECTNESS: _adjust_correctness,
    AuditArea.TESTING: _adjust_testing,
    AuditArea.SECURITY: _adjust_security,
    AuditArea.CICD: _adjust_cicd,
    AuditArea.RELIABILITY: _adjust_reliability,
    AuditArea.DOCUMENTATION: _adjust_documentation,
    AuditArea.AGENT_READINESS: _adjust_agent_readiness,
    AuditArea.DEV_EXPERIENCE: _adjust_dev_experience,
}

# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def score_to_grade(score: float, thresholds: dict[str, tuple[int, int]] | None = None) -> str:
    """Convert a numeric score to a letter grade.

    Uses the grade thresholds defined in the configuration. Scores are
    compared against inclusive (low, high) bounds for each grade.

    Args:
        score: The numeric score (0–100, may be float from weighted calc).
        thresholds: Optional custom grade thresholds. Uses
            :data:`GRADE_THRESHOLDS` when ``None``.

    Returns:
        The letter grade string (e.g., ``"A+"``, ``"B-"``, ``"F"``).
        Returns ``"F"`` for scores below all defined thresholds.
    """
    thr = thresholds or GRADE_THRESHOLDS
    rounded = round(score)
    for grade, (low, high) in thr.items():
        if low <= rounded <= high:
            return grade
    return "F"


def grade_to_index(grade: str) -> int:
    """Convert a letter grade to a numeric index for comparison.

    Higher indexes correspond to better grades. ``"F"`` is 0, ``"A+"`` is 12.
    Unknown grades fall back to ``"F"`` (index 0).

    Args:
        grade: A letter grade string.

    Returns:
        Integer index from 0 (F) to 12 (A+).
    """
    try:
        return len(GRADE_ORDER) - 1 - GRADE_ORDER.index(grade.upper())
    except ValueError:
        return 0


def calculate_overall_score(
    area_scores: list[AreaScore],
    thresholds: dict[str, tuple[int, int]] | None = None,
) -> tuple[int, str]:
    """Calculate the weighted overall score and grade.

    The overall score is a weighted sum of individual area scores using
    each area's configured weight. The grade is derived via
    :func:`score_to_grade`.

    Args:
        area_scores: List of :class:`AreaScore` objects for all audited areas.
        thresholds: Optional custom grade thresholds.

    Returns:
        A tuple of ``(overall_score: int, overall_grade: str)``.

    Raises:
        ValueError: If ``area_scores`` is empty.
    """
    if not area_scores:
        raise ValueError("Cannot calculate overall score: no area scores provided")

    total = sum(a.score * a.weight for a in area_scores)
    rounded = round(total)
    grade = score_to_grade(rounded, thresholds=thresholds)
    return rounded, grade


def calculate_area_score(
    area: AuditArea,
    findings: list[Finding],
    metrics: dict[str, Any],
    weight: float | None = None,
    grade_thresholds: dict[str, tuple[int, int]] | None = None,
) -> AreaScore:
    """Calculate the score for a single audit area.

    Algorithm:
        1. Start from a baseline score of 100 for each area.
        2. Deduct for findings: Critical=-8, High=-5, Medium=-3, Low=-1.
        3. Apply the confidence multiplier per finding:
           High confidence = 1.0x, Medium = 0.8x, Low = 0.5x.
        4. Apply area-specific metric adjustments.
        5. Floor at 0, cap at 100.

    The resulting score is clamped to the [0, 100] range and a grade,
    confidence, and trend risk are computed.

    Args:
        area: The audit area being scored.
        findings: List of findings that apply to this area.
        metrics: Dictionary of collected metrics for the area.
        weight: Optional weight for this area. Falls back to
            :data:`DEFAULT_AREA_WEIGHTS` if not provided.
        grade_thresholds: Optional custom grade thresholds. Uses
            :data:`GRADE_THRESHOLDS` when ``None``.

    Returns:
        An :class:`AreaScore` instance with the computed score and metadata.
    """
    baseline = 100

    area_weight = weight if weight is not None else DEFAULT_AREA_WEIGHTS.get(area, 0.1)

    # --- Step 2 & 3: Deduct for findings with confidence multiplier ---
    finding_deduction = 0.0
    for finding in findings:
        sev_deduction = abs(severity_deduction(finding.severity))
        conf_mult = confidence_multiplier(finding.confidence)
        finding_deduction += sev_deduction * conf_mult

    # Cap finding deductions at 60 (prevents any single category from
    # tanking the score too aggressively)
    finding_deduction = min(finding_deduction, 60.0)

    # --- Step 4: Area-specific metric adjustments ---
    adjuster = _AREA_ADJUSTERS.get(area)
    if adjuster and metrics:
        metric_deduction = adjuster(metrics)
    else:
        metric_deduction = 0.0

    # Cap metric deductions at 30
    metric_deduction = min(metric_deduction, 30.0)

    # --- Step 5: Calculate final score ---
    raw_score = baseline - finding_deduction - metric_deduction
    final_score = max(0, min(100, round(raw_score)))

    # --- Determine confidence ---
    if not findings and not metrics:
        area_confidence = Confidence.LOW
    elif all(f.confidence == Confidence.HIGH for f in findings):
        area_confidence = Confidence.HIGH
    elif any(f.confidence == Confidence.LOW for f in findings):
        area_confidence = Confidence.LOW
    else:
        area_confidence = Confidence.MEDIUM

    # --- Determine grade ---
    grade = score_to_grade(final_score, thresholds=grade_thresholds)

    # --- Build diagnosis ---
    if finding_deduction > metric_deduction:
        diagnosis = (
            f"{len(findings)} finding(s) in this area; "
            f"{finding_deduction:.1f} pts deducted from code issues"
        )
    elif metric_deduction > 0:
        diagnosis = (
            f"{metric_deduction:.1f} pts deducted from metric gaps; "
            f"{len(findings)} structural finding(s)"
        )
    else:
        diagnosis = "Area appears healthy — no significant issues detected"

    return AreaScore(
        area=area,
        weight=area_weight,
        score=final_score,
        grade=grade,
        confidence=area_confidence,
        trend_risk="Stable",  # Will be updated by detect_trend if history available
        diagnosis=diagnosis,
        findings_count=len(findings),
    )


def detect_trend(
    current_score: int,
    historical_scores: list[int],
    window_size: int = 3,
) -> str:
    """Detect the score trend from historical data.

    Analyzes the most recent ``window_size`` historical scores against
    the current score to determine if the trend is Improving, Stable,
    or Declining.

    Algorithm:
        - If fewer than 2 historical scores: returns ``"Stable"``
        - Computes the average of the last ``window_size`` scores
        - Compares current score against that average
        - ``+3`` or more: ``"Improving"``
        - ``-3`` or less: ``"Declining"``
        - Otherwise: ``"Stable"``

    Args:
        current_score: The most recent score (0–100).
        historical_scores: Chronological list of past scores.
        window_size: Number of recent scores to consider for the average.

    Returns:
        One of ``"Improving"``, ``"Stable"``, or ``"Declining"``.
    """
    if len(historical_scores) < 2:
        return "Stable"

    # Use the most recent window
    recent = historical_scores[-window_size:]
    avg_recent = statistics.mean(recent)

    delta = current_score - avg_recent

    if delta >= 3:
        return "Improving"
    if delta <= -3:
        return "Declining"
    return "Stable"


def detect_trend_with_variance(
    current_score: int,
    historical_scores: list[int],
    window_size: int = 3,
) -> tuple[str, float]:
    """Detect trend with additional variance information.

    Like :func:`detect_trend`, but also returns the variance of the
    recent scores to indicate confidence in the trend direction.

    Args:
        current_score: The most recent score (0–100).
        historical_scores: Chronological list of past scores.
        window_size: Number of recent scores to consider.

    Returns:
        A tuple of ``(trend: str, variance: float)`` where variance is
        the population variance of the recent score window.
    """
    trend = detect_trend(current_score, historical_scores, window_size)

    if len(historical_scores) < 2:
        return trend, 0.0

    recent = historical_scores[-window_size:]
    if len(recent) < 2:
        return trend, 0.0

    variance = statistics.pvariance(recent)
    return trend, variance


def build_scorecard(
    repo_name: str,
    findings: list[Finding],
    metrics_by_area: dict[AuditArea, dict[str, Any]] | None = None,
    historical_scores: dict[AuditArea | None, list[int]] | None = None,
    area_weights: dict[AuditArea, float] | None = None,
    grade_thresholds: dict[str, tuple[int, int]] | None = None,
    branch: str = "main",
    commit_sha: str | None = None,
    total_files: int = 0,
    total_directories: int = 0,
    total_commits: int = 0,
    total_contributors: int = 0,
    confidence: Confidence | None = None,
) -> Scorecard:
    """Build a complete :class:`Scorecard` from findings and metrics.

    Computes an :class:`AreaScore` for each audit area, derives the overall
    weighted score and grade, and optionally applies trend detection using
    historical scores per area.

    Args:
        repo_name: Repository name for the scorecard.
        findings: All findings from the audit.
        metrics_by_area: Optional mapping of audit area to metric dict.
        historical_scores: Optional mapping of audit area to chronological
            list of past scores for trend detection. The ``None`` key holds
            the overall score history.
        area_weights: Optional custom area weights. Uses
            :data:`DEFAULT_AREA_WEIGHTS` when ``None``.
        grade_thresholds: Optional custom grade thresholds. Uses
            :data:`DEFAULT_GRADE_THRESHOLDS` when ``None``.
        branch: Git branch that was audited.
        commit_sha: Optional git commit SHA.
        total_files: Total number of files analyzed.
        total_directories: Total number of directories analyzed.
        total_commits: Total number of commits analyzed.
        total_contributors: Total number of unique contributors.
        confidence: Optional overall confidence. If ``None``, confidence is
            derived from area confidence levels.

    Returns:
        A validated :class:`Scorecard` instance.
    """
    metrics_by_area = metrics_by_area or {}
    historical_scores = historical_scores or {}
    weights = area_weights or DEFAULT_AREA_WEIGHTS
    thresholds = grade_thresholds or DEFAULT_GRADE_THRESHOLDS

    arch_metrics = metrics_by_area.get(AuditArea.ARCHITECTURE, {})
    git_metric_completeness = dict(arch_metrics.get("git_metric_completeness", {}) or {})
    git_warnings = list(arch_metrics.get("git_warnings", []) or [])

    area_scores: list[AreaScore] = []
    for area in AuditArea:
        area_findings = [f for f in findings if f.area == area]
        area_metrics = metrics_by_area.get(area, {})
        area_weight = weights.get(area, DEFAULT_AREA_WEIGHTS.get(area, 0.1))
        area_score = calculate_area_score(
            area, area_findings, area_metrics, weight=area_weight, grade_thresholds=thresholds
        )

        # Apply trend if historical data exists
        history = historical_scores.get(area, [])
        if history:
            area_score.trend_risk = detect_trend(area_score.score, history)

        area_scores.append(area_score)

    overall_score, overall_grade = calculate_overall_score(area_scores, thresholds=thresholds)

    if confidence is None:
        if all(a.confidence == Confidence.HIGH for a in area_scores):
            overall_confidence = Confidence.HIGH
        elif any(a.confidence == Confidence.LOW for a in area_scores):
            overall_confidence = Confidence.LOW
        else:
            overall_confidence = Confidence.MEDIUM
    else:
        overall_confidence = confidence

    overall_history = historical_scores.get(None, [])
    trend = detect_trend(overall_score, overall_history)

    return Scorecard(
        repo_name=repo_name,
        branch=branch,
        commit_sha=commit_sha,
        overall_score=overall_score,
        overall_grade=overall_grade,
        confidence=overall_confidence,
        trend=trend,
        area_scores=area_scores,
        total_files=total_files,
        total_directories=total_directories,
        total_commits=total_commits,
        total_contributors=total_contributors,
        git_metric_completeness=git_metric_completeness,
        git_warnings=git_warnings,
        findings=findings,
    )


__all__ = [
    "GRADE_THRESHOLDS",
    "score_to_grade",
    "grade_to_index",
    "calculate_overall_score",
    "calculate_area_score",
    "detect_trend",
    "detect_trend_with_variance",
    "build_scorecard",
]
