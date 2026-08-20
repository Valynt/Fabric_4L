"""Unit tests for AuditOrchestrator scoring engine."""

from __future__ import annotations

from pathlib import Path

import pytest

from layer4_agents.agents.audit_orchestrator.models import (
    DEFAULT_AREA_WEIGHTS,
    AuditArea,
    Confidence,
    Finding,
    Severity,
)
from layer4_agents.agents.audit_orchestrator.scoring import (
    GRADE_THRESHOLDS,
    build_scorecard,
    calculate_area_score,
    calculate_overall_score,
    detect_trend,
    detect_trend_with_variance,
    grade_to_index,
    score_to_grade,
)


@pytest.fixture
def perfect_finding() -> Finding:
    """Return a minimal valid Finding."""
    return Finding(
        id="COR-001",
        severity=Severity.HIGH,
        confidence=Confidence.HIGH,
        area=AuditArea.CORRECTNESS,
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


# ---------------------------------------------------------------------------
# Grade mapping
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize(
    "score,expected_grade",
    [
        (100, "A+"),
        (97, "A+"),
        (93, "A"),
        (90, "A-"),
        (87, "B+"),
        (83, "B"),
        (80, "B-"),
        (77, "C+"),
        (73, "C"),
        (70, "C-"),
        (67, "D+"),
        (63, "D"),
        (60, "D-"),
        (59, "F"),
        (0, "F"),
    ],
)
def test_score_to_grade(score: int, expected_grade: str) -> None:
    assert score_to_grade(score) == expected_grade


@pytest.mark.unit
def test_score_to_grade_custom_thresholds() -> None:
    custom = {"Pass": (80, 100), "Fail": (0, 79)}
    assert score_to_grade(85, thresholds=custom) == "Pass"
    assert score_to_grade(50, thresholds=custom) == "Fail"


@pytest.mark.unit
def test_grade_to_index_ordering() -> None:
    assert grade_to_index("A+") > grade_to_index("A")
    assert grade_to_index("A") > grade_to_index("B")
    assert grade_to_index("F") == 0
    assert grade_to_index("UNKNOWN") == 0


# ---------------------------------------------------------------------------
# Overall score
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_overall_score_perfect() -> None:
    from layer4_agents.agents.audit_orchestrator.models import AreaScore

    area_scores = [
        AreaScore(
            area=area,
            weight=0.1,
            score=100,
            grade="A+",
            confidence=Confidence.HIGH,
            trend_risk="Stable",
            diagnosis="healthy",
        )
        for area in AuditArea
    ]
    overall, grade = calculate_overall_score(area_scores)
    assert overall == 100
    assert grade == "A+"


@pytest.mark.unit
def test_calculate_overall_score_empty_raises() -> None:
    with pytest.raises(ValueError, match="no area scores provided"):
        calculate_overall_score([])


@pytest.mark.unit
def test_calculate_overall_score_weighted() -> None:
    from layer4_agents.agents.audit_orchestrator.models import AreaScore

    area_scores = [
        AreaScore(
            area=AuditArea.SECURITY,
            weight=0.5,
            score=80,
            grade="B-",
            confidence=Confidence.HIGH,
            trend_risk="Stable",
            diagnosis="ok",
        ),
        AreaScore(
            area=AuditArea.TESTING,
            weight=0.5,
            score=60,
            grade="D-",
            confidence=Confidence.MEDIUM,
            trend_risk="Stable",
            diagnosis="ok",
        ),
    ]
    overall, grade = calculate_overall_score(area_scores)
    assert overall == 70
    assert grade == "C-"


# ---------------------------------------------------------------------------
# Area score
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_calculate_area_score_no_findings() -> None:
    area_score = calculate_area_score(AuditArea.SECURITY, [], {})
    assert area_score.score == 100
    assert area_score.grade == "A+"
    assert area_score.findings_count == 0


@pytest.mark.unit
def test_calculate_area_score_with_findings(perfect_finding: Finding) -> None:
    perfect_finding.area = AuditArea.CORRECTNESS
    area_score = calculate_area_score(AuditArea.CORRECTNESS, [perfect_finding], {})
    # High severity with high confidence: 5 pts deduction.
    assert area_score.score == 95
    assert area_score.grade == "A"


@pytest.mark.unit
def test_calculate_area_score_confidence_multiplier(
    perfect_finding: Finding,
) -> None:
    perfect_finding.area = AuditArea.CORRECTNESS
    perfect_finding.confidence = Confidence.LOW
    area_score = calculate_area_score(AuditArea.CORRECTNESS, [perfect_finding], {})
    # High severity with low confidence: 5 * 0.5 = 2.5, rounded.
    assert area_score.score == pytest.approx(97, abs=1)


@pytest.mark.unit
def test_calculate_area_score_metric_adjustments() -> None:
    area_score = calculate_area_score(
        AuditArea.SECURITY,
        [],
        {"missing_llm_guardrails": True, "injection_vector_count": 4},
    )
    # 8 + min(12, 12) = 20, capped at 30.
    assert area_score.score == 80


@pytest.mark.unit
def test_calculate_area_score_finding_deduction_cap() -> None:
    findings = [
        Finding(
            id=f"CRIT-{i:02d}",
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            area=AuditArea.SECURITY,
            evidence="src/x.py",
            observed_fact="risk",
            inference_risk="risk",
            business_impact="risk",
            recommended_fix="fix",
            effort="XS",
            risk_of_change="High",
            owner="team",
            analyzer_type="code",
        )
        for i in range(20)
    ]
    area_score = calculate_area_score(AuditArea.SECURITY, findings, {})
    # Deductions capped at 60, so score = 40.
    assert area_score.score == 40


# ---------------------------------------------------------------------------
# Trend detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_detect_trend_insufficient_history() -> None:
    assert detect_trend(80, []) == "Stable"
    assert detect_trend(80, [80]) == "Stable"


@pytest.mark.unit
def test_detect_trend_improving() -> None:
    assert detect_trend(85, [78, 79, 80]) == "Improving"


@pytest.mark.unit
def test_detect_trend_declining() -> None:
    assert detect_trend(75, [80, 81, 82]) == "Declining"


@pytest.mark.unit
def test_detect_trend_stable() -> None:
    assert detect_trend(80, [79, 80, 81]) == "Stable"


@pytest.mark.unit
def test_detect_trend_with_variance() -> None:
    trend, variance = detect_trend_with_variance(85, [78, 79, 80])
    assert trend == "Improving"
    assert variance >= 0


# ---------------------------------------------------------------------------
# Scorecard builder
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_build_scorecard_empty() -> None:
    scorecard = build_scorecard(repo_name="test/repo", findings=[])
    assert scorecard.repo_name == "test/repo"
    assert scorecard.overall_score == 100
    assert scorecard.overall_grade == "A+"
    assert len(scorecard.area_scores) == len(AuditArea)


@pytest.mark.unit
def test_build_scorecard_with_findings(perfect_finding: Finding) -> None:
    perfect_finding.area = AuditArea.CORRECTNESS
    scorecard = build_scorecard(
        repo_name="test/repo",
        findings=[perfect_finding],
        total_files=10,
        total_commits=5,
    )
    assert scorecard.total_files == 10
    assert scorecard.total_commits == 5
    assert scorecard.findings_by_severity(Severity.HIGH)
    correctness = scorecard.get_area_score(AuditArea.CORRECTNESS)
    assert correctness is not None
    assert correctness.score == 95


@pytest.mark.unit
def test_build_scorecard_with_trend(perfect_finding: Finding) -> None:
    perfect_finding.area = AuditArea.CORRECTNESS
    scorecard = build_scorecard(
        repo_name="test/repo",
        findings=[perfect_finding],
        historical_scores={AuditArea.CORRECTNESS: [88, 90, 92]},
    )
    correctness = scorecard.get_area_score(AuditArea.CORRECTNESS)
    assert correctness is not None
    assert correctness.trend_risk == "Improving"


@pytest.mark.unit
def test_build_scorecard_custom_weights(perfect_finding: Finding) -> None:
    perfect_finding.area = AuditArea.SECURITY
    custom_weights = dict.fromkeys(AuditArea, 0.1)
    scorecard = build_scorecard(
        repo_name="test/repo",
        findings=[perfect_finding],
        area_weights=custom_weights,
    )
    security = scorecard.get_area_score(AuditArea.SECURITY)
    assert security is not None
    assert security.weight == 0.1


@pytest.mark.unit
def test_calculate_area_score_custom_weight(perfect_finding: Finding) -> None:
    perfect_finding.area = AuditArea.CORRECTNESS
    area_score = calculate_area_score(
        AuditArea.CORRECTNESS,
        [perfect_finding],
        {},
        weight=0.25,
    )
    assert area_score.weight == 0.25


@pytest.mark.unit
def test_calculate_area_score_applies_catalog_metric_adjustments(
    tmp_path: Path,
) -> None:
    """Scoring adjusters must consume metric keys emitted by the finding catalog."""
    from layer4_agents.agents.audit_orchestrator.analyzers.finding_catalog import (
        _check_duplicate_files,
    )
    from layer4_agents.agents.audit_orchestrator.models import AuditConfig

    services_dir = tmp_path / "services" / "svc"
    packages_dir = tmp_path / "packages" / "pkg"
    services_dir.mkdir(parents=True)
    packages_dir.mkdir(parents=True)
    content = "x = 1\n"
    (services_dir / "dup.py").write_text(content)
    (packages_dir / "dup.py").write_text(content)

    config = AuditConfig(repo_url=".", repo_name="test/repo", trusted_source=True)
    result = _check_duplicate_files(tmp_path, config)
    assert "duplicate_file_count" in result
    assert result["duplicate_file_count"] > 0

    area_score = calculate_area_score(
        AuditArea.ARCHITECTURE,
        [],
        {"duplicate_file_count": result["duplicate_file_count"]},
    )
    assert area_score.score < 100
    assert area_score.diagnosis.startswith("1.5 pts deducted")


@pytest.mark.unit
def test_calculate_area_score_applies_mypy_disabled_codes_metric(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """mypy_disabled_codes emitted by the catalog must reduce Code Quality score."""
    from layer4_agents.agents.audit_orchestrator import analyzers
    from layer4_agents.agents.audit_orchestrator.analyzers.finding_catalog import (
        _check_mypy_disabled,
    )
    from layer4_agents.agents.audit_orchestrator.models import AuditConfig

    fake_mypy = {
        "disable_error_code": ["arg-type", "assignment"],
        "ignore_missing_imports": True,
    }
    monkeypatch.setattr(
        analyzers.finding_catalog,
        "_pyproject_sections",
        lambda _repo_path, _section: [(tmp_path / "pyproject.toml", fake_mypy)],
    )

    config = AuditConfig(repo_url=".", repo_name="test/repo", trusted_source=True)
    result = _check_mypy_disabled(tmp_path, config)
    assert "mypy_disabled_codes" in result
    assert result["mypy_disabled_codes"] == 3

    area_score = calculate_area_score(
        AuditArea.CODE_QUALITY,
        [],
        {"mypy_disabled_codes": result["mypy_disabled_codes"]},
    )
    assert area_score.score == 97
    assert (
        "mypy" in area_score.diagnosis.lower()
        or "metric gaps" in area_score.diagnosis.lower()
    )


@pytest.mark.unit
def test_calculate_area_score_applies_migration_issue_count_metric(
    tmp_path: Path,
) -> None:
    """migration_issue_count emitted by the catalog must reduce Correctness score."""
    from layer4_agents.agents.audit_orchestrator.analyzers.finding_catalog import (
        _check_migration_downgrades,
    )
    from layer4_agents.agents.audit_orchestrator.models import AuditConfig

    services_dir = tmp_path / "services" / "layerX"
    versions_dir = services_dir / "migrations" / "versions"
    versions_dir.mkdir(parents=True)
    (versions_dir / "001_initial.py").write_text("def upgrade(): pass\n")

    config = AuditConfig(repo_url=".", repo_name="test/repo", trusted_source=True)
    result = _check_migration_downgrades(tmp_path, config)
    assert "migration_issue_count" in result
    assert result["migration_issue_count"] == 1

    area_score = calculate_area_score(
        AuditArea.CORRECTNESS,
        [],
        {"migration_issue_count": result["migration_issue_count"]},
    )
    assert area_score.score == 97


@pytest.mark.unit
@pytest.mark.parametrize(
    "area",
    [
        AuditArea.TESTING,
        AuditArea.SECURITY,
        AuditArea.CICD,
        AuditArea.RELIABILITY,
        AuditArea.DOCUMENTATION,
        AuditArea.AGENT_READINESS,
    ],
)
def test_calculate_area_score_missing_optional_metrics_preserves_baseline(
    area: AuditArea,
) -> None:
    """Areas with only catalog-produced metrics must not KeyError or deduct when optional metrics are absent."""
    area_score = calculate_area_score(area, [], {})
    assert area_score.score == 100


@pytest.mark.unit
def test_calculate_area_score_missing_metrics_no_keyerror() -> None:
    """All area adjusters must tolerate entirely absent metric dictionaries."""
    for area in AuditArea:
        area_score = calculate_area_score(area, [], {})
        assert 0 <= area_score.score <= 100
        assert area_score.grade


@pytest.mark.unit
def test_calculate_area_score_default_weight(perfect_finding: Finding) -> None:
    perfect_finding.area = AuditArea.CORRECTNESS
    area_score = calculate_area_score(AuditArea.CORRECTNESS, [perfect_finding], {})
    assert area_score.weight == DEFAULT_AREA_WEIGHTS[AuditArea.CORRECTNESS]


@pytest.mark.unit
def test_build_scorecard_overall_history(perfect_finding: Finding) -> None:
    perfect_finding.area = AuditArea.CORRECTNESS
    scorecard = build_scorecard(
        repo_name="test/repo",
        findings=[perfect_finding],
        historical_scores={None: [88, 90, 92]},
    )
    assert scorecard.trend == "Improving"


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_grade_thresholds_exposed() -> None:
    assert GRADE_THRESHOLDS["A+"] == (97, 100)
    assert GRADE_THRESHOLDS["F"] == (0, 59)


# ---------------------------------------------------------------------------
# Edge cases
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_score_to_grade_float_rounding() -> None:
    assert score_to_grade(96.6) == "A+"
    assert score_to_grade(89.4) == "B+"


@pytest.mark.unit
def test_calculate_area_score_minimum_clamp() -> None:
    findings = [
        Finding(
            id="CRIT-001",
            severity=Severity.CRITICAL,
            confidence=Confidence.HIGH,
            area=AuditArea.SECURITY,
            evidence="src/x.py",
            observed_fact="risk",
            inference_risk="risk",
            business_impact="risk",
            recommended_fix="fix",
            effort="XS",
            risk_of_change="High",
            owner="team",
            analyzer_type="code",
        )
        for _ in range(50)
    ]
    area_score = calculate_area_score(
        AuditArea.SECURITY,
        findings,
        {
            "missing_llm_guardrails": True,
            "injection_vector_count": 10,
            "dependency_vulnerability_count": 10,
        },
    )
    # Finding cap 60 + metric cap 30 = 90 deduction, floor at 10.
    assert area_score.score == 10


@pytest.mark.unit
def test_build_scorecard_uses_custom_grade_thresholds(perfect_finding: Finding) -> None:
    """Custom grade_thresholds in build_scorecard must be honored for overall and area grades."""
    perfect_finding.area = AuditArea.CORRECTNESS
    custom_thresholds = {
        "Pass": (90, 100),
        "Marginal": (70, 89),
        "Fail": (0, 69),
    }
    scorecard = build_scorecard(
        repo_name="test/repo",
        findings=[perfect_finding],
        grade_thresholds=custom_thresholds,
    )
    assert scorecard.overall_grade == "Pass"
    correctness = scorecard.get_area_score(AuditArea.CORRECTNESS)
    assert correctness is not None
    assert correctness.grade == "Pass"
