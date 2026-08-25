"""Unit tests for the AuditOrchestrator analyzer package."""

from __future__ import annotations

import json
import re
import time
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
from layer4_agents.agents.audit_orchestrator.analyzers.git_analyzer import (
    GitCommandResult,
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


# ---------------------------------------------------------------------------
# GitAnalyzer contributor-counting refactor tests
# ---------------------------------------------------------------------------


class _FakeReadStream:
    """File-like object exposing a bounded ``read(n)`` for the reader thread."""

    def __init__(self, content: str = ""):
        self._content = content
        self._pos = 0

    def read(self, n: int = -1) -> str:
        if self._pos >= len(self._content):
            return ""
        chunk = self._content[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk


class _SlowReadStream:
    """Stream whose first ``read`` sleeps (simulates a slow/hung subprocess)."""

    def __init__(self, first_sleep: float, content: str = ""):
        self._first_sleep = first_sleep
        self._content = content
        self._pos = 0
        self._slept = False

    def read(self, n: int = -1) -> str:
        if not self._slept:
            time.sleep(self._first_sleep)
            self._slept = True
        if self._pos >= len(self._content):
            return ""
        chunk = self._content[self._pos : self._pos + n]
        self._pos += len(chunk)
        return chunk


class _FakeGitProc:
    """Stand-in for a ``subprocess.Popen`` handle used by ``GitAnalyzer._git_cmd``."""

    def __init__(self, content: str = "", returncode=0, stream=None):
        self.stdout = stream if stream is not None else _FakeReadStream(content)
        self.stderr = None
        self.returncode = returncode
        self.terminate_called = False

    def terminate(self):
        self.terminate_called = True
        self.returncode = -15

    def kill(self):
        self.returncode = -9

    def wait(self, timeout=None):
        return self.returncode


def _make_analyzer(**_kwargs):
    from layer4_agents.agents.audit_orchestrator.models import AuditConfig

    return GitAnalyzer(
        AuditConfig(
            repo_url="https://github.com/bmsull560/Fabric_4L",
            repo_name="bmsull560/Fabric_4L",
        ),
        **_kwargs,
    )


def test_git_cmd_caps_large_streamed_output_by_lines(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A huge simulated stream is cut short and marked truncated, not buffered."""
    content = "".join(
        f"{i}  A <a{i}@example.com>\n" for i in range(100_000)
    )
    monkeypatch.setattr(
        GitAnalyzer, "_git_popen", lambda *a, **k: _FakeGitProc(content=content)
    )
    analyzer = _make_analyzer(max_output_lines=3, max_output_bytes=10**9)

    result = analyzer._git_cmd(tmp_path, ["shortlog", "-sne", "HEAD"])

    assert result.status == "truncated"
    assert result.truncated is True
    # Only the first few lines survived; nothing like the full 100k buffered.
    assert len(result.stdout.splitlines()) == 3
    assert result.bytes_read <= 100_000


def test_git_cmd_caps_single_enormous_line_still_respected(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """An enormous single line (no newlines) is bounded by the byte cap, not
    buffered in full."""
    content = ("x" * 5_000_000) + "\n"
    monkeypatch.setattr(
        GitAnalyzer, "_git_popen", lambda *a, **k: _FakeGitProc(content=content)
    )
    analyzer = _make_analyzer(max_output_lines=10**6, max_output_bytes=8192)

    result = analyzer._git_cmd(tmp_path, ["log", "-1"])

    assert result.status == "truncated"
    assert result.truncated is True
    # Only a bounded head of the huge line was retained.
    assert len(result.stdout) <= 8192


def test_git_cmd_caps_large_streamed_output_by_bytes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A stream exceeding the byte cap is terminated and marked truncated."""
    long_line = "x" * 2000 + "\n"
    content = long_line * 100
    monkeypatch.setattr(
        GitAnalyzer, "_git_popen", lambda *a, **k: _FakeGitProc(content=content)
    )
    analyzer = _make_analyzer(max_output_lines=10**6, max_output_bytes=5000)

    result = analyzer._git_cmd(tmp_path, ["log", "-1"])

    assert result.status == "truncated"
    assert result.truncated is True
    assert result.stdout.count("\n") <= 4  # ~5000 / 2001-byte lines


def test_git_cmd_timeout_terminates_and_marks_truncated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """A slow command is terminated once it exceeds the wall-clock timeout."""
    proc = _FakeGitProc(stream=_SlowReadStream(first_sleep=0.05, content="partial\n"))

    def _popen(*a, **k):
        return proc

    monkeypatch.setattr(GitAnalyzer, "_git_popen", _popen)
    analyzer = _make_analyzer(timeout_seconds=0.01, max_output_lines=10**6)

    result = analyzer._git_cmd(tmp_path, ["shortlog", "-sne", "HEAD"])

    assert result.status == "timeout"
    assert result.truncated is True
    assert proc.terminate_called is True
    assert result.stdout == ""


def test_git_cmd_error_status_on_nonzero_return(tmp_path, monkeypatch):
    """A nonzero exit with no cap breach is surfaced as ``error``, not ok."""
    monkeypatch.setattr(
        GitAnalyzer,
        "_git_popen",
        lambda *a, **k: _FakeGitProc(content="", returncode=128),
    )
    analyzer = _make_analyzer()
    result = analyzer._git_cmd(tmp_path, ["rev-list", "HEAD", "--count"])
    assert result.status == "error"
    assert result.truncated is False


def test_git_metrics_normal_contributor_counting(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    """shortlog lines are aggregated to a contributor count; no emails leaked."""
    analyzer = _make_analyzer()

    def fake_cmd(_path, args):
        name = args[0]
        if name == "rev-list":
            return GitCommandResult(stdout="42")
        if name == "shortlog":
            return GitCommandResult(
                stdout=" 10  Ada Lovelace <ada@example.com>\n"
                "  3  Bob <bob@example.com>\n"
                "  1  carol@example.com\n"
            )
        if name == "branch":
            return GitCommandResult(stdout="* main\n  dev\n  feature/x\n")
        if name == "tag":
            return GitCommandResult(stdout="v1.0.0\nv1.1.0\n")
        return GitCommandResult(stdout=str(int(time.time())))

    monkeypatch.setattr(analyzer, "_git_cmd", fake_cmd)

    metrics = analyzer._collect_git_metrics(tmp_path, True)

    assert metrics["total_commits"] == 42
    assert metrics["total_contributors"] == 3
    assert metrics["branch_count"] == 3
    assert metrics["tag_count"] == 2
    assert isinstance(metrics["recent_commit_days"], int)
    assert metrics["git_warnings"] == []
    assert all(
        entry["complete"] for entry in metrics["git_metric_completeness"].values()
    )

    rendered = json.dumps(metrics, default=str)
    assert "ada@example.com" not in rendered
    assert "bob@example.com" not in rendered
    assert "carol@example.com" not in rendered


def test_git_metrics_truncated_contributors_yield_warning_and_incomplete(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    analyzer = _make_analyzer()

    def fake_cmd(_path, args):
        name = args[0]
        if name == "rev-list":
            return GitCommandResult(stdout="5000")
        if name == "shortlog":
            return GitCommandResult(
                stdout="  1  Ada <ada@example.com>\n",
                status="truncated",
                truncated=True,
                bytes_read=40,
                max_bytes=1_000_000,
            )
        if name == "branch":
            return GitCommandResult(stdout="* main\n")
        if name == "tag":
            return GitCommandResult(stdout="v1.0.0\n")
        return GitCommandResult(stdout=str(int(time.time())))

    monkeypatch.setattr(analyzer, "_git_cmd", fake_cmd)

    metrics = analyzer._collect_git_metrics(tmp_path, True)

    # The undercount is surfaced, but it is explicitly flagged incomplete.
    assert metrics["total_contributors"] == 1
    completeness = metrics["git_metric_completeness"]["total_contributors"]
    assert completeness["complete"] is False
    assert completeness["status"] == "truncated"
    assert completeness["truncated"] is True

    codes = {w["code"] for w in metrics["git_warnings"]}
    assert "GIT_CMD_OUTPUT_TRUNCATED" in codes
    # The structured warning references the metric, never the raw output/emails.
    rendered = json.dumps(metrics["git_warnings"])
    assert "ada@example.com" not in rendered


def test_git_metrics_timeout_warning(tmp_path, monkeypatch):
    analyzer = _make_analyzer()

    def fake_cmd(_path, args):
        name = args[0]
        if name == "shortlog":
            return GitCommandResult(status="timeout", truncated=True, bytes_read=0)
        if name == "rev-list":
            return GitCommandResult(stdout="99")
        if name == "branch":
            return GitCommandResult(stdout="* main\n")
        if name == "tag":
            return GitCommandResult(stdout="v1.0.0\n")
        return GitCommandResult(stdout=str(int(time.time())))

    monkeypatch.setattr(analyzer, "_git_cmd", fake_cmd)

    metrics = analyzer._collect_git_metrics(tmp_path, True)

    assert metrics["total_contributors"] == 0
    codes = {w["code"] for w in metrics["git_warnings"]}
    assert "GIT_CMD_TIMEOUT" in codes
    assert metrics["git_metric_completeness"]["total_contributors"]["complete"] is False


def test_git_metrics_malformed_timestamp_is_graceful(tmp_path, monkeypatch):
    analyzer = _make_analyzer()

    def fake_cmd(_path, args):
        name = args[0]
        if name == "shortlog":
            return GitCommandResult(stdout="  1  Ada <ada@example.com>\n")
        if name == "log":
            return GitCommandResult(stdout="not-a-timestamp")
        if name == "rev-list":
            return GitCommandResult(stdout="1")
        if name == "branch":
            return GitCommandResult(stdout="* main\n")
        if name == "tag":
            return GitCommandResult(stdout="")

    monkeypatch.setattr(analyzer, "_git_cmd", fake_cmd)

    metrics = analyzer._collect_git_metrics(tmp_path, True)

    assert metrics["recent_commit_days"] is None
    assert metrics["git_metric_completeness"]["recent_commit_days"]["complete"] is True
    assert metrics["tag_count"] == 0
