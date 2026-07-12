"""Tests for the temporal skip guard.

These tests verify that scripts/ci/check_temporal_skips.py correctly flags
unregistered temporal skips and allows tracked/registered ones.
"""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path

import pytest
from scripts.ci.check_temporal_skips import (
    _extract_reason,
    _has_temporal_language,
    _has_ticket_reference,
    _is_registered,
    _scan_file,
    main,
)


class _FakeFinding:
    def __init__(self, path: str, line: int, marker: str, reason: str, matched_pattern: str):
        self.path = path
        self.line = line
        self.marker = marker
        self.reason = reason
        self.matched_pattern = matched_pattern


def test_extract_reason_double_quoted() -> None:
    assert _extract_reason('pytest.skip("Need DB");', "pytest.skip") == "Need DB"


def test_extract_reason_single_quoted() -> None:
    assert _extract_reason("pytest.skip('Need DB');", "pytest.skip") == "Need DB"


def test_extract_reason_no_quotes_returns_argument() -> None:
    reason = _extract_reason("pytest.skip(some_variable)", "pytest.skip")
    assert reason == "some_variable"


def test_has_temporal_language_detects_date() -> None:
    flag, matched = _has_temporal_language("Skip until 2026-06-30")
    assert flag is True
    assert "date" in matched


def test_has_temporal_language_detects_todo() -> None:
    flag, matched = _has_temporal_language("TODO: fix this later")
    assert flag is True
    assert "keyword" in matched


def test_has_temporal_language_detects_temporary() -> None:
    flag, matched = _has_temporal_language("temporary skip")
    assert flag is True
    assert "keyword" in matched


def test_has_temporal_language_clean_reason() -> None:
    flag, _ = _has_temporal_language("PostgreSQL not reachable")
    assert flag is False


def test_has_ticket_reference_vf_skip() -> None:
    assert _has_ticket_reference("Skip until fix, see VF-SKIP-123") is True


def test_has_ticket_reference_jira() -> None:
    assert _has_ticket_reference("Tracked under PROJ-42") is True


def test_has_ticket_reference_missing() -> None:
    assert _has_ticket_reference("Skip until later") is False


def test_is_registered_matches() -> None:
    register = {
        ("tests/example.py", "pytest.skip", r"No\ DB"): {
            "remediation": {"ticket_id": "VF-SKIP-001"},
        }
    }
    finding = _FakeFinding("tests/example.py", 5, "pytest.skip", "No DB", "keyword:until")
    assert _is_registered(finding, register) is True


def test_is_registered_missing_ticket() -> None:
    register = {
        ("tests/example.py", "pytest.skip", r"No\ DB"): {
            "remediation": {},
        }
    }
    finding = _FakeFinding("tests/example.py", 5, "pytest.skip", "No DB", "keyword:until")
    assert _is_registered(finding, register) is False


def test_scan_file_flags_temporal_skip(tmp_path: Path) -> None:
    test_file = tmp_path / "test_x.py"
    test_file.write_text('def test_x():\n    pytest.skip("TODO: fix before 2026-07-01")\n')
    findings = _scan_file(test_file, tmp_path)
    assert len(findings) == 1
    assert findings[0].marker == "pytest.skip"
    assert "TODO" in findings[0].reason


def test_scan_file_allows_ticket_referenced_skip(tmp_path: Path) -> None:
    test_file = tmp_path / "test_x.py"
    test_file.write_text('def test_x():\n    pytest.skip("TODO fix VF-SKIP-001")\n')
    findings = _scan_file(test_file, tmp_path)
    # Detection happens; ticket-reference filtering is separate.
    assert len(findings) == 1
    assert findings[0].reason == "TODO fix VF-SKIP-001"


def test_main_fails_on_unregistered_temporal_skip(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    tests = root / "tests"
    tests.mkdir(parents=True)
    (tests / "test_x.py").write_text('def test_x():\n    pytest.skip("TODO fix me")\n')
    register = root / "register.yaml"
    register.write_text("entries: []\n")

    exit_code = main([
        "--root", str(root),
        "--register", str(register),
        "--scan-root", "tests",
    ])
    assert exit_code == 1


def test_main_passes_with_ticket_reference(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    tests = root / "tests"
    tests.mkdir(parents=True)
    (tests / "test_x.py").write_text('def test_x():\n    pytest.skip("TODO fix VF-SKIP-999")\n')
    register = root / "register.yaml"
    register.write_text("entries: []\n")

    exit_code = main([
        "--root", str(root),
        "--register", str(register),
        "--scan-root", "tests",
    ])
    assert exit_code == 0


def test_main_writes_json_report(tmp_path: Path) -> None:
    root = tmp_path / "repo"
    tests = root / "tests"
    tests.mkdir(parents=True)
    (tests / "test_x.py").write_text('def test_x():\n    pytest.skip("TODO fix me")\n')
    register = root / "register.yaml"
    register.write_text("entries: []\n")
    json_out = root / "report.json"

    main([
        "--root", str(root),
        "--register", str(register),
        "--scan-root", "tests",
        "--json-out", str(json_out),
    ])

    report = json.loads(json_out.read_text(encoding="utf-8"))
    assert report["unregistered_temporal_findings"] == 1
    assert report["findings"][0]["path"] == "tests/test_x.py"
