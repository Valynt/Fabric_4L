"""Unit tests for AuditOrchestrator models, enums, and configuration."""

from __future__ import annotations

import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest

from layer4_agents.agents.audit_orchestrator.config import (
    ConfigManager,
    _convert_env_value,
)
from layer4_agents.agents.audit_orchestrator.models import (
    DEFAULT_AREA_WEIGHTS,
    DEFAULT_GRADE_THRESHOLDS,
    AuditArea,
    AuditConfig,
    AuditRun,
    AuditRunDetail,
    AuditRunResponse,
    AuditRunSummary,
    AuditTriggerRequest,
    Confidence,
    Finding,
    FindingStatus,
    FindingUpdate,
    ReportFormat,
    Scorecard,
    ScoreHistory,
    ScoreHistoryEntry,
    Severity,
    Sprint,
    SprintStatus,
)


@pytest.fixture
def sample_finding() -> Finding:
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


@pytest.fixture
def sample_scorecard(sample_finding: Finding) -> Scorecard:
    """Return a Scorecard with all ten areas and one finding."""
    from layer4_agents.agents.audit_orchestrator.scoring import build_scorecard

    return build_scorecard(
        repo_name="test/repo",
        findings=[sample_finding],
    )


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_severity_enum_values() -> None:
    assert Severity.CRITICAL.value == "critical"
    assert Severity.HIGH.value == "high"
    assert Severity.MEDIUM.value == "medium"
    assert Severity.LOW.value == "low"


@pytest.mark.unit
def test_confidence_enum_values() -> None:
    assert Confidence.HIGH.value == "high"
    assert Confidence.MEDIUM.value == "medium"
    assert Confidence.LOW.value == "low"


@pytest.mark.unit
def test_audit_area_enum_values() -> None:
    assert AuditArea.ARCHITECTURE.value.startswith("A:")
    assert AuditArea.DEV_EXPERIENCE.value.startswith("J:")


@pytest.mark.unit
def test_sprint_status_enum_values() -> None:
    assert SprintStatus.PLANNED.value == "planned"
    assert SprintStatus.IN_PROGRESS.value == "in_progress"
    assert SprintStatus.COMPLETED.value == "completed"
    assert SprintStatus.DEFERRED.value == "deferred"


@pytest.mark.unit
def test_finding_status_enum_values() -> None:
    assert FindingStatus.OPEN.value == "open"
    assert FindingStatus.RESOLVED.value == "resolved"
    assert FindingStatus.WAIVED.value == "waived"


@pytest.mark.unit
def test_report_format_enum_values() -> None:
    assert ReportFormat.MARKDOWN.value == "markdown"
    assert ReportFormat.JSON.value == "json"


# ---------------------------------------------------------------------------
# Finding model
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_finding_defaults_and_methods(sample_finding: Finding) -> None:
    assert sample_finding.status == FindingStatus.OPEN
    assert sample_finding.target_sprint == 0
    assert sample_finding.times_seen == 1

    sample_finding.mark_seen()
    assert sample_finding.times_seen == 2
    assert sample_finding.last_seen_at >= sample_finding.first_seen_at

    sample_finding.mark_resolved(note="fixed in PR #123")
    assert sample_finding.status == FindingStatus.RESOLVED
    assert sample_finding.resolved_at is not None
    assert sample_finding.resolution_note == "fixed in PR #123"


@pytest.mark.unit
def test_finding_effort_validation() -> None:
    with pytest.raises(ValueError):
        Finding(
            id="BAD-001",
            severity=Severity.LOW,
            confidence=Confidence.LOW,
            area=AuditArea.DOCUMENTATION,
            evidence="README.md",
            observed_fact="typo",
            inference_risk="low",
            business_impact="low",
            recommended_fix="fix typo",
            effort="XXL",  # invalid
            risk_of_change="Low",
            owner="team",
            analyzer_type="doc",
        )


# ---------------------------------------------------------------------------
# Scorecard model
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_scorecard_requires_all_areas(sample_finding: Finding) -> None:
    from layer4_agents.agents.audit_orchestrator.scoring import AreaScore

    partial_area = AreaScore(
        area=AuditArea.SECURITY,
        weight=1.0,
        score=80,
        grade="B-",
        confidence=Confidence.HIGH,
        trend_risk="Stable",
        diagnosis="ok",
    )
    with pytest.raises(ValueError, match="Missing area scores"):
        Scorecard(
            repo_name="test/repo",
            overall_score=80,
            overall_grade="B-",
            confidence=Confidence.HIGH,
            trend="Stable",
            area_scores=[partial_area],
            findings=[sample_finding],
        )


@pytest.mark.unit
def test_scorecard_weight_sum_validation(sample_finding: Finding) -> None:
    from layer4_agents.agents.audit_orchestrator.scoring import AreaScore

    area_scores = [
        AreaScore(
            area=area,
            weight=0.5 if area == AuditArea.SECURITY else 0.0,
            score=80,
            grade="B-",
            confidence=Confidence.HIGH,
            trend_risk="Stable",
            diagnosis="ok",
        )
        for area in AuditArea
    ]
    with pytest.raises(ValueError, match="Area weights must sum to 1.0"):
        Scorecard(
            repo_name="test/repo",
            overall_score=80,
            overall_grade="B-",
            confidence=Confidence.HIGH,
            trend="Stable",
            area_scores=area_scores,
            findings=[sample_finding],
        )


@pytest.mark.unit
def test_scorecard_allows_empty_area_scores() -> None:
    """An empty area_scores list is explicitly permitted by the validator."""
    scorecard = Scorecard(
        repo_name="test/repo",
        overall_score=0,
        overall_grade="F",
        confidence=Confidence.LOW,
        trend="Stable",
        area_scores=[],
    )
    assert scorecard.area_scores == []


@pytest.mark.unit
def test_scorecard_helpers(sample_scorecard: Scorecard) -> None:
    assert sample_scorecard.get_area_score(AuditArea.CORRECTNESS) is not None
    assert sample_scorecard.get_area_score(AuditArea.SECURITY) is not None
    assert sample_scorecard.open_findings()
    assert sample_scorecard.findings_by_severity(Severity.HIGH)


# ---------------------------------------------------------------------------
# Sprint model
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_sprint_lifecycle() -> None:
    sprint = Sprint(
        id=1,
        theme="Stabilize core",
        objectives=["fix critical bugs"],
        deliverables=["release v1.1"],
        findings_targeted=["COR-001"],
    )
    assert sprint.status == SprintStatus.PLANNED
    sprint.start()
    assert sprint.status == SprintStatus.IN_PROGRESS
    assert sprint.started_at is not None
    sprint.complete(actual_score_impact=5)
    assert sprint.status == SprintStatus.COMPLETED
    assert sprint.score_impact_actual == 5


# ---------------------------------------------------------------------------
# AuditRun model
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_audit_run_lifecycle(sample_scorecard: Scorecard) -> None:
    run = AuditRun(status="pending", trigger_type="manual", repo_path="/tmp/repo")
    assert run.status == "pending"
    run.mark_completed(sample_scorecard)
    assert run.status == "completed"
    assert run.scorecard is not None

    run2 = AuditRun(status="running", trigger_type="scheduled", repo_path="/tmp/repo")
    run2.mark_failed("git clone failed")
    assert run2.status == "failed"
    assert run2.error_message == "git clone failed"
    assert run2.completed_at is not None


# ---------------------------------------------------------------------------
# AuditConfig model
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_audit_config_defaults() -> None:
    config = AuditConfig(repo_url="https://github.com/org/repo", repo_name="repo")
    assert config.branch == "main"
    assert config.incremental is True
    assert config.severity_threshold == Severity.LOW
    assert sum(config.area_weights.values()) == pytest.approx(1.0, abs=0.01)


@pytest.mark.unit
def test_audit_config_weight_validation() -> None:
    config = AuditConfig(repo_url="https://github.com/org/repo", repo_name="repo")
    bad_weights = dict(config.area_weights)
    bad_weights[AuditArea.SECURITY] = 1.0
    with pytest.raises(ValueError, match="Area weights must sum to 1.0"):
        AuditConfig(
            repo_url="https://github.com/org/repo",
            repo_name="repo",
            area_weights=bad_weights,
        )


@pytest.mark.unit
def test_audit_config_get_area_weight() -> None:
    config = AuditConfig(repo_url="https://github.com/org/repo", repo_name="repo")
    assert config.get_area_weight(AuditArea.SECURITY) == 0.16


@pytest.mark.unit
def test_audit_config_clone_depth_zero_allows_full_clone() -> None:
    config = AuditConfig(
        repo_url="https://github.com/org/repo",
        repo_name="repo",
        clone_depth=0,
    )
    assert config.clone_depth == 0


@pytest.mark.unit
@pytest.mark.parametrize(
    "raw,expected",
    [
        ("1", 1),
        ("0", 0),
        ("42", 42),
        ("3.14", 3.14),
        ("true", True),
        ("True", True),
        ("false", False),
        ("yes", True),
        ("no", False),
        ("on", True),
        ("off", False),
        ("null", None),
        ("none", None),
        ("", None),
        ("A,B,C", ["A", "B", "C"]),
        ("a, b ,c", ["a", "b", "c"]),
        ("plain string", "plain string"),
        ("https://github.com/org/repo", "https://github.com/org/repo"),
    ],
)
def test_convert_env_value_coercion(raw: str, expected: Any) -> None:
    assert _convert_env_value(raw) == expected


@pytest.mark.unit
def test_config_manager_env_numeric_and_boolean_coercion(
    tmp_path: Path, monkeypatch: Any
) -> None:
    for key in list(os.environ.keys()):
        if key.startswith("AUDIT__"):
            monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("AUDIT__REPO_URL", "https://github.com/env/repo")
    monkeypatch.setenv("AUDIT__REPO_NAME", "env-repo")
    monkeypatch.setenv("AUDIT__CLONE_DEPTH", "0")
    monkeypatch.setenv("AUDIT__INCREMENTAL", "0")
    monkeypatch.setenv("AUDIT__TEAM_SIZE", "1")
    monkeypatch.setenv("AUDIT__AREAS_ENABLED", "A,B,C")

    mgr = ConfigManager(yaml_path=str(tmp_path / "missing.yaml"))
    config = mgr.load()
    # "0" is coerced to int 0 (not bool False), which the int field accepts.
    assert config.clone_depth == 0
    # "0" is coerced to int 0, then Pydantic bool field serializes it as False.
    assert config.incremental is False
    assert config.team_size == 1
    assert config.areas_enabled == [
        AuditArea.ARCHITECTURE,
        AuditArea.CODE_QUALITY,
        AuditArea.CORRECTNESS,
    ]


@pytest.mark.unit
def test_config_manager_env_boolean_word_coercion(
    tmp_path: Path, monkeypatch: Any
) -> None:
    for key in list(os.environ.keys()):
        if key.startswith("AUDIT__"):
            monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("AUDIT__REPO_URL", "https://github.com/env/repo")
    monkeypatch.setenv("AUDIT__REPO_NAME", "env-repo")
    monkeypatch.setenv("AUDIT__INCREMENTAL", "false")
    monkeypatch.setenv("AUDIT__TRIGGER_ON_PUSH", "yes")
    monkeypatch.setenv("AUDIT__TRIGGER_ON_RELEASE", "off")

    mgr = ConfigManager(yaml_path=str(tmp_path / "missing.yaml"))
    config = mgr.load()
    assert config.incremental is False
    assert config.trigger_on_push is True
    assert config.trigger_on_release is False


# ---------------------------------------------------------------------------
# ConfigManager — environment and YAML
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_config_manager_loads_defaults(tmp_path: Path, monkeypatch: Any) -> None:
    # Ensure no AUDIT__ env vars leak in.
    for key in list(os.environ.keys()):
        if key.startswith("AUDIT__"):
            monkeypatch.delenv(key, raising=False)

    mgr = ConfigManager(yaml_path=str(tmp_path / "missing.yaml"))
    config = mgr.load(
        overrides={"repo_url": "https://github.com/org/repo", "repo_name": "repo"}
    )
    assert config.repo_url == "https://github.com/org/repo"
    assert config.branch == "main"


@pytest.mark.unit
def test_config_manager_env_overrides(tmp_path: Path, monkeypatch: Any) -> None:
    for key in list(os.environ.keys()):
        if key.startswith("AUDIT__"):
            monkeypatch.delenv(key, raising=False)
    monkeypatch.setenv("AUDIT__REPO_URL", "https://github.com/env/repo")
    monkeypatch.setenv("AUDIT__REPO_NAME", "env-repo")
    monkeypatch.setenv("AUDIT__BRANCH", "develop")
    monkeypatch.setenv("AUDIT__INCREMENTAL", "false")

    mgr = ConfigManager(yaml_path=str(tmp_path / "missing.yaml"))
    config = mgr.load()
    assert config.repo_url == "https://github.com/env/repo"
    assert config.repo_name == "env-repo"
    assert config.branch == "develop"
    assert config.incremental is False


@pytest.mark.unit
def test_config_manager_yaml_overrides(tmp_path: Path, monkeypatch: Any) -> None:
    for key in list(os.environ.keys()):
        if key.startswith("AUDIT__"):
            monkeypatch.delenv(key, raising=False)

    yaml_path = tmp_path / "config.yaml"
    yaml_path.write_text(
        "repo_url: https://github.com/yaml/repo\n"
        "repo_name: yaml-repo\n"
        "branch: staging\n"
        "severity_threshold: medium\n"
    )
    mgr = ConfigManager(yaml_path=str(yaml_path))
    config = mgr.load()
    assert config.repo_url == "https://github.com/yaml/repo"
    assert config.repo_name == "yaml-repo"
    assert config.branch == "staging"
    assert config.severity_threshold == Severity.MEDIUM


@pytest.mark.unit
def test_config_manager_area_weights_from_env(
    tmp_path: Path, monkeypatch: Any
) -> None:
    for key in list(os.environ.keys()):
        if key.startswith("AUDIT__"):
            monkeypatch.delenv(key, raising=False)
    # Provide all weights so they still sum to 1.0.
    weights = {
        "ARCHITECTURE": 0.10,
        "CODE_QUALITY": 0.10,
        "CORRECTNESS": 0.14,
        "TESTING": 0.14,
        "SECURITY": 0.18,
        "CICD": 0.10,
        "RELIABILITY": 0.08,
        "DOCUMENTATION": 0.06,
        "AGENT_READINESS": 0.05,
        "DEV_EXPERIENCE": 0.05,
    }
    for name, value in weights.items():
        monkeypatch.setenv(f"AUDIT__AREA_WEIGHTS__{name}", str(value))
    monkeypatch.setenv("AUDIT__REPO_URL", "https://github.com/w/repo")
    monkeypatch.setenv("AUDIT__REPO_NAME", "w-repo")

    mgr = ConfigManager(yaml_path=str(tmp_path / "missing.yaml"))
    config = mgr.load()
    assert config.get_area_weight(AuditArea.SECURITY) == pytest.approx(0.18)
    assert sum(config.area_weights.values()) == pytest.approx(1.0, abs=0.01)


@pytest.mark.unit
def test_config_manager_load_or_default(tmp_path: Path, monkeypatch: Any) -> None:
    for key in list(os.environ.keys()):
        if key.startswith("AUDIT__"):
            monkeypatch.delenv(key, raising=False)

    bad_yaml = tmp_path / "bad.yaml"
    bad_yaml.write_text("area_weights: not_a_dict\n")
    mgr = ConfigManager(yaml_path=str(bad_yaml))
    config = mgr.load_or_default(
        overrides={"repo_url": "https://github.com/fallback/repo", "repo_name": "fb"}
    )
    assert config.repo_url == "https://github.com/fallback/repo"


# ---------------------------------------------------------------------------
# API models
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_audit_trigger_request_defaults() -> None:
    req = AuditTriggerRequest(repo_url="https://github.com/test/repo")
    assert req.trigger_type == "manual"
    assert req.branch is None


@pytest.mark.unit
def test_audit_run_response() -> None:
    resp = AuditRunResponse(run_id="run-1", status="pending")
    assert resp.run_id == "run-1"
    assert resp.message
    assert resp.started_at is not None


@pytest.mark.unit
def test_audit_run_detail_and_summary() -> None:
    detail = AuditRunDetail(
        run_id="run-1",
        status="completed",
        trigger_type="manual",
        repo_name="repo",
        started_at=datetime.now(UTC),
    )
    assert detail.overall_score is None

    summary = AuditRunSummary(
        run_id="run-1",
        status="completed",
        trigger_type="manual",
        repo_name="repo",
        started_at=datetime.now(UTC),
    )
    assert summary.findings_count == 0


@pytest.mark.unit
def test_score_history_properties() -> None:
    history = ScoreHistory(
        repo_name="repo",
        entries=[
            ScoreHistoryEntry(
                run_id="r1", score=70, grade="C-", timestamp=datetime.now(UTC)
            ),
            ScoreHistoryEntry(
                run_id="r2", score=75, grade="C", timestamp=datetime.now(UTC)
            ),
        ],
    )
    assert history.latest_score == 75
    assert history.score_change == 5


@pytest.mark.unit
def test_finding_update() -> None:
    update = FindingUpdate(status=FindingStatus.RESOLVED, resolution_note="done")
    assert update.status == FindingStatus.RESOLVED
    assert update.resolution_note == "done"


# ---------------------------------------------------------------------------
# Constant exposure
# ---------------------------------------------------------------------------

@pytest.mark.unit
def test_default_constants_available() -> None:
    assert DEFAULT_AREA_WEIGHTS[AuditArea.SECURITY] == 0.16
    assert DEFAULT_GRADE_THRESHOLDS["A+"] == (97, 100)


# ---------------------------------------------------------------------------
# Repository URL Validation
# ---------------------------------------------------------------------------

@pytest.mark.unit
@pytest.mark.parametrize(
    "valid_url",
    [
        "https://github.com/org/repo",
        "https://github.com/org/repo.git",
        "http://github.com/org/repo.git",
        "ssh://git@github.com/org/repo.git",
        "git://github.com/org/repo.git",
        "git@github.com:org/repo.git",
        "git@gitlab.com:team/subgroup/project.git",
    ],
)
def test_validate_repo_url_allowed(valid_url: str) -> None:
    from layer4_agents.agents.audit_orchestrator.models import validate_repo_url

    assert validate_repo_url(valid_url) == valid_url


@pytest.mark.unit
@pytest.mark.parametrize(
    "hostile_url",
    [
        "/",
        "/etc",
        "/etc/passwd",
        "C:\\Windows",
        "\\\\server\\share",
        "../secret",
        "foo/../../bar",
        "file:///etc/shadow",
        "file://localhost/etc/passwd",
        "ext::sh -c 'touch /tmp/pwned'",
        "fd::3",
        "ftp://github.com/org/repo.git",
        "gopher://github.com/org/repo.git",
        "data:text/plain;base64,SGVsbG8=",
        "javascript:alert(1)",
        "http://localhost/repo",
        "http://127.0.0.1/repo",
        "http://169.254.169.254/repo",
        "http://10.0.0.1/repo",
        "http://192.168.1.1/repo",
        "http://172.16.0.1/repo",
        "http://metadata.google.internal/repo",
        "git@localhost:owner/repo.git",
        "git@127.0.0.1:owner/repo.git",
        "git@10.0.0.1:owner/repo.git",
        "git@192.168.1.1:owner/repo.git",
        "ssh://git@10.0.0.1/repo.git",
        "ssh://git@127.0.0.1/repo.git",
    ],
)
def test_validate_repo_url_hostile_rejected(hostile_url: str) -> None:
    from layer4_agents.agents.audit_orchestrator.models import validate_repo_url

    with pytest.raises(ValueError):
        validate_repo_url(hostile_url)

