"""Unit tests for the AuditOrchestrator analyzer package."""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from layer4_agents.agents.audit_orchestrator.analyzers import (
    CodeAnalyzer,
    DocAnalyzer,
    FindingCatalog,
    GitAnalyzer,
    run_all_analyzers,
)
from layer4_agents.agents.audit_orchestrator.analyzers.code_analyzer import (
    COMPILED_PATTERNS,
)
from layer4_agents.agents.audit_orchestrator.models import (
    AuditArea,
    AuditConfig,
    Finding,
)

REPO_PATH = "."

VALID_PREFIXES = {
    "ARCH": AuditArea.ARCHITECTURE,
    "CQ": AuditArea.CODE_QUALITY,
    "COR": AuditArea.CORRECTNESS,
    "TEST": AuditArea.TESTING,
    "SEC": AuditArea.SECURITY,
    "CICD": AuditArea.CICD,
    "REL": AuditArea.RELIABILITY,
    "DOC": AuditArea.DOCUMENTATION,
    "AGENT": AuditArea.AGENT_READINESS,
    "DX": AuditArea.DEV_EXPERIENCE,
}

REQUIRED_FINDING_FIELDS = {
    "id",
    "severity",
    "confidence",
    "area",
    "evidence",
    "observed_fact",
    "inference_risk",
    "business_impact",
    "recommended_fix",
    "effort",
    "risk_of_change",
    "owner",
    "analyzer_type",
}


@pytest.fixture
def audit_config() -> AuditConfig:
    return AuditConfig(
        repo_url="https://github.com/bmsull560/Fabric_4L",
        repo_name="bmsull560/Fabric_4L",
    )


def test_finding_catalog_has_44_entries_with_unique_ids():
    entries = FindingCatalog.entries
    assert len(entries) == 44, f"Expected 44 catalog entries, got {len(entries)}"

    ids = [entry["id"] for entry in entries]
    assert len(ids) == len(set(ids)), "Catalog finding IDs must be unique"


def test_finding_catalog_ids_use_valid_prefixes_and_areas():
    prefix_numbers: dict[str, list[int]] = {prefix: [] for prefix in VALID_PREFIXES}

    for entry in FindingCatalog.entries:
        finding_id = entry["id"]
        assert "-" in finding_id, f"ID {finding_id} must contain a hyphen"
        prefix, number_part = finding_id.split("-", 1)
        assert prefix in VALID_PREFIXES, f"Unknown ID prefix {prefix} in {finding_id}"

        expected_area = VALID_PREFIXES[prefix]
        assert (
            entry["area"] == expected_area
        ), f"ID {finding_id} maps to {expected_area.value}, got {entry['area'].value}"

        assert (
            number_part.isdigit() and len(number_part) == 3
        ), f"ID {finding_id} must end in a three-digit zero-padded number"
        prefix_numbers[prefix].append(int(number_part))

    for prefix, numbers in prefix_numbers.items():
        if not numbers:
            continue
        numbers.sort()
        expected = list(range(1, len(numbers) + 1))
        assert (
            numbers == expected
        ), f"{prefix} finding numbers are not sequential from 001: {numbers}"


def test_base_analyzer_auto_increments_ids():
    config = AuditConfig(repo_url="https://example.com/repo", repo_name="repo")
    analyzer = GitAnalyzer(config)

    f1 = analyzer.create_finding(
        id_prefix="TEST",
        severity="low",
        confidence="high",
        area=AuditArea.CODE_QUALITY,
        evidence="src/foo.py:1",
        observed_fact="x",
        inference_risk="y",
        business_impact="z",
        recommended_fix="a",
        effort="XS",
        risk_of_change="Low",
        owner="Team",
    )
    f2 = analyzer.create_finding(
        id_prefix="TEST",
        severity="low",
        confidence="high",
        area=AuditArea.CODE_QUALITY,
        evidence="src/foo.py:2",
        observed_fact="x",
        inference_risk="y",
        business_impact="z",
        recommended_fix="a",
        effort="XS",
        risk_of_change="Low",
        owner="Team",
    )

    assert f1.id == "TEST-001"
    assert f2.id == "TEST-002"


def test_base_analyzer_resets_id_counters_per_instance():
    """Each analyzer instance must start its ID counters from zero."""
    config = AuditConfig(repo_url="https://example.com/repo", repo_name="repo")

    first = GitAnalyzer(config)
    f1 = first.create_finding(
        id_prefix="TEST",
        severity="low",
        confidence="high",
        area=AuditArea.CODE_QUALITY,
        evidence="src/foo.py:1",
        observed_fact="x",
        inference_risk="y",
        business_impact="z",
        recommended_fix="a",
        effort="XS",
        risk_of_change="Low",
        owner="Team",
    )
    assert f1.id == "TEST-001"

    second = GitAnalyzer(config)
    f2 = second.create_finding(
        id_prefix="TEST",
        severity="low",
        confidence="high",
        area=AuditArea.CODE_QUALITY,
        evidence="src/foo.py:2",
        observed_fact="x",
        inference_risk="y",
        business_impact="z",
        recommended_fix="a",
        effort="XS",
        risk_of_change="Low",
        owner="Team",
    )
    assert f2.id == "TEST-001"


def test_base_analyzer_reset_clears_counters():
    """reset() must restart ID counters so a re-run does not continue numbering."""
    config = AuditConfig(repo_url="https://example.com/repo", repo_name="repo")
    analyzer = GitAnalyzer(config)

    f1 = analyzer.create_finding(
        id_prefix="TEST",
        severity="low",
        confidence="high",
        area=AuditArea.CODE_QUALITY,
        evidence="src/foo.py:1",
        observed_fact="x",
        inference_risk="y",
        business_impact="z",
        recommended_fix="a",
        effort="XS",
        risk_of_change="Low",
        owner="Team",
    )
    assert f1.id == "TEST-001"

    analyzer.reset()

    f2 = analyzer.create_finding(
        id_prefix="TEST",
        severity="low",
        confidence="high",
        area=AuditArea.CODE_QUALITY,
        evidence="src/foo.py:2",
        observed_fact="x",
        inference_risk="y",
        business_impact="z",
        recommended_fix="a",
        effort="XS",
        risk_of_change="Low",
        owner="Team",
    )
    assert f2.id == "TEST-001"


def test_git_analyzer_runs_on_current_repo(audit_config: AuditConfig):
    analyzer = GitAnalyzer(audit_config)
    findings, metrics = analyzer.analyze(REPO_PATH)

    assert isinstance(findings, list)
    assert isinstance(metrics, dict)
    assert metrics
    assert metrics.get("git_available") is True

    for finding in findings:
        assert isinstance(finding, Finding)
        _assert_finding_fields(finding)


def test_read_lines_not_cached_across_repos(tmp_path: Path):
    """_read_lines must return current file contents, not a stale cache entry."""
    from layer4_agents.agents.audit_orchestrator.analyzers.finding_catalog import _read_lines

    repo_a = tmp_path / "repo_a"
    repo_b = tmp_path / "repo_b"
    repo_a.mkdir()
    repo_b.mkdir()

    file_a = repo_a / "test.txt"
    file_b = repo_b / "test.txt"
    file_a.write_text("repo a content", encoding="utf-8")
    file_b.write_text("repo b content", encoding="utf-8")

    assert _read_lines(file_a) == ["repo a content"]
    assert _read_lines(file_b) == ["repo b content"]
    assert _read_lines(file_a) == ["repo a content"]

    # Updating a file must be reflected on the next read.
    file_a.write_text("updated content", encoding="utf-8")
    assert _read_lines(file_a) == ["updated content"]


def test_code_analyzer_runs_on_current_repo(audit_config: AuditConfig):
    analyzer = CodeAnalyzer(audit_config)
    findings, metrics = analyzer.analyze(REPO_PATH)

    assert isinstance(findings, list)
    assert isinstance(metrics, dict)
    assert metrics

    for finding in findings:
        assert isinstance(finding, Finding)
        _assert_finding_fields(finding)


def test_doc_analyzer_runs_on_current_repo(audit_config: AuditConfig):
    analyzer = DocAnalyzer(audit_config)
    findings, metrics = analyzer.analyze(REPO_PATH)

    assert isinstance(findings, list)
    assert isinstance(metrics, dict)
    assert metrics

    for finding in findings:
        assert isinstance(finding, Finding)
        _assert_finding_fields(finding)


def test_run_all_analyzers_combines_results(audit_config: AuditConfig):
    findings, metrics = run_all_analyzers(REPO_PATH, audit_config)

    assert isinstance(findings, list)
    assert isinstance(metrics, dict)
    assert "by_analyzer" in metrics
    assert set(metrics["by_analyzer"].keys()) == {"git", "code", "doc"}
    assert metrics["total_findings"] == len(findings)

    # No duplicate IDs across analyzers (areas are disjoint).
    ids = [f.id for f in findings]
    assert len(ids) == len(set(ids))


def test_code_analyzer_regexes_compile():
    assert COMPILED_PATTERNS
    for name, pattern in COMPILED_PATTERNS.items():
        assert isinstance(pattern, re.Pattern), f"{name} is not a compiled pattern"
        # Re-compiling the pattern string should succeed and match the original.
        recompiled = re.compile(pattern.pattern, pattern.flags)
        assert recompiled.pattern == pattern.pattern


def test_finding_catalog_check_all_runs(audit_config: AuditConfig):
    findings, metrics = FindingCatalog.check_all(REPO_PATH, audit_config)

    assert isinstance(findings, list)
    assert isinstance(metrics, dict)
    assert metrics["checks_run"] == 44
    assert metrics["checks_triggered"] <= 44
    assert metrics["findings_count"] == len(findings)

    ids = [f.id for f in findings]
    assert len(ids) == len(set(ids))


def test_analyzers_handle_non_git_or_empty_tree(
    tmp_path: Path, audit_config: AuditConfig, monkeypatch: pytest.MonkeyPatch
):
    """Analyzers should run without raising on a plain, empty directory."""
    (tmp_path / "package.json").write_text('{"name":"x"}')

    monkeypatch.setattr(GitAnalyzer, "_git_available", lambda self, p: (p / ".git").exists())
    git_analyzer = GitAnalyzer(audit_config)
    findings, metrics = git_analyzer.analyze(str(tmp_path))
    assert isinstance(findings, list)
    assert metrics.get("git_available") is False

    code_analyzer = CodeAnalyzer(audit_config)
    findings, metrics = code_analyzer.analyze(str(tmp_path))
    assert isinstance(findings, list)
    assert metrics.get("total_python_files", -1) == 0

    doc_analyzer = DocAnalyzer(audit_config)
    findings, metrics = doc_analyzer.analyze(str(tmp_path))
    assert isinstance(findings, list)
    assert "agent_skill_count" in metrics


def _assert_finding_fields(finding: Finding) -> None:
    missing = REQUIRED_FINDING_FIELDS - set(finding.model_dump().keys())
    assert not missing, f"Finding {finding.id} missing required fields: {missing}"
    assert finding.id
    assert finding.area in set(AuditArea)
    assert finding.effort in {"XS", "S", "M", "L", "XL"}
    assert finding.analyzer_type
