from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from scripts.ci.check_p0_security_skip_governance import evaluate

TODAY = date(2026, 8, 27)
GOVERNED = ("tests/security/gov_test.py",)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _allowlist(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    path = tmp_path / "allowlist.yaml"
    path.write_text(yaml.safe_dump({"entries": entries}, sort_keys=False), encoding="utf-8")
    return path


def _entry(**overrides: object) -> dict[str, object]:
    entry = {
        "id": "allow-001",
        "path_pattern": "tests/security/gov_test.py",
        "reason_pattern": "Requires (L2|L3|L5|L6|L7) service integration",
        "owner": "@platform-security",
        "reason": "No in-process seam; needs live stack.",
        "expiry": "2026-09-30",
        "issue": "VF-SKIP-TEST",
        "classification": "live-stack",
    }
    entry.update(overrides)
    return entry


def _skip_line(reason: str) -> str:
    return f'import pytest\npytest.skip("{reason}")\n'


def test_exact_single_match_passes(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/gov_test.py", _skip_line("Requires L2 service integration"))
    report = evaluate(
        tmp_path, _allowlist(tmp_path, [_entry()]), TODAY, governed_paths=GOVERNED
    )
    assert report["violation_count"] == 0
    assert report["covered_skips"] == ["allow-001"]


def test_uncovered_skip_fails(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/gov_test.py", _skip_line("unrelated reason"))
    report = evaluate(
        tmp_path, _allowlist(tmp_path, [_entry()]), TODAY, governed_paths=GOVERNED
    )
    assert report["violation_count"] == 1
    assert any("unapproved P0/security skip" in v for v in report["violations"])


def test_expired_allowlist_entry_fails(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/gov_test.py", _skip_line("Requires L2 service integration"))
    report = evaluate(
        tmp_path,
        _allowlist(tmp_path, [_entry(expiry="2026-01-01")]),
        TODAY,
        governed_paths=GOVERNED,
    )
    assert report["violation_count"] >= 1
    assert any("expired" in v for v in report["violations"])


def test_stale_allowlist_entry_flagged(tmp_path: Path) -> None:
    # No skips at all in the governed tree -> entry matches nothing and is stale.
    _write(tmp_path / "tests/security/gov_test.py", "import pytest\nassert True\n")
    report = evaluate(
        tmp_path, _allowlist(tmp_path, [_entry()]), TODAY, governed_paths=GOVERNED
    )
    assert report["stale_allowlist_entries"] == ["allow-001"]


def test_ambiguous_multiple_match_fails(tmp_path: Path) -> None:
    """A skip matched by more than one allowlist entry is a governance violation."""
    _write(tmp_path / "tests/security/gov_test.py", _skip_line("Requires L2 service integration"))
    entries = [
        _entry(id="allow-001", reason_pattern="Requires L2 service integration"),
        _entry(id="allow-002", reason_pattern="service integration"),
    ]
    report = evaluate(
        tmp_path, _allowlist(tmp_path, entries), TODAY, governed_paths=GOVERNED
    )
    assert report["ambiguous_skips"] == [
        {"path": "tests/security/gov_test.py", "line": 2, "matched_ids": ["allow-001", "allow-002"]}
    ]
    assert report["violation_count"] == 1
    assert any("ambiguous allowlist match" in v for v in report["violations"])
