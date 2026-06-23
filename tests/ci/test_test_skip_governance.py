from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml

from scripts.ci.check_test_skip_governance import evaluate


TODAY = date(2026, 5, 11)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _register(tmp_path: Path, entries: list[dict[str, str]]) -> Path:
    path = tmp_path / "register.yaml"
    path.write_text(yaml.safe_dump({"entries": entries}, sort_keys=False), encoding="utf-8")
    return path


def _entry(**overrides: str) -> dict[str, str]:
    entry = {
        "id": "skip-001",
        "path_pattern": "tests/security/test_auth.py",
        "marker": "pytest.skip",
        "reason_pattern": "dependency missing",
        "owner": "@platform-quality",
        "reason": "Temporary dependency-gated security test skip.",
        "expires_on": "2026-06-30",
        "severity": "P0",
        "launch_gate": "mandatory",
    }
    entry.update(overrides)
    return entry


def test_unregistered_p0_skip_fails(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    report = evaluate(tmp_path, _register(tmp_path, []), ["tests/security"], TODAY)
    assert report["unregistered"]
    assert report["unregistered"][0]["marker"] == "pytest.skip"


def test_registered_non_expired_skip_passes(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    report = evaluate(tmp_path, _register(tmp_path, [_entry()]), ["tests/security"], TODAY)
    assert report["register_errors"] == []
    assert report["unregistered"] == []
    assert report["forbidden"] == []
    assert report["summary"] == {
        "total_registered_markers": 1,
        "total_detected_markers": 1,
        "expired_register_entries": 0,
        "unregistered_markers": 0,
        "forbidden_markers": 0,
        "matched_register_entries": 1,
        "mandatory_p0_register_entries": 1,
    }


def test_expired_register_entry_fails(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    report = evaluate(
        tmp_path,
        _register(tmp_path, [_entry(expires_on="2026-01-01")]),
        ["tests/security"],
        TODAY,
    )
    assert any("expired" in error for error in report["register_errors"])
    assert report["expired_register_entries"] == 1


def test_malformed_register_entry_fails(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    bad_entry = _entry()
    del bad_entry["owner"]
    report = evaluate(tmp_path, _register(tmp_path, [bad_entry]), ["tests/security"], TODAY)
    assert any("missing required" in error for error in report["register_errors"])


def test_only_marker_always_fails_even_when_registered(tmp_path: Path) -> None:
    _write(tmp_path / "apps/web/e2e/foo.spec.ts", "test" + ".only('focus leak', async () => {});\n")
    report = evaluate(
        tmp_path,
        _register(
            tmp_path,
            [
                _entry(
                    id="only-001",
                    path_pattern="apps/web/e2e/foo.spec.ts",
                    marker="test.only",
                    reason_pattern="focus leak",
                    severity="P1",
                )
            ],
        ),
        ["apps/web/e2e"],
        TODAY,
    )
    assert report["forbidden"]
    assert report["forbidden"][0]["marker"] == "test.only"


def test_excluded_generated_paths_are_ignored(tmp_path: Path) -> None:
    _write(tmp_path / "apps/web/e2e/node_modules/bad.spec.ts", "test" + ".skip('generated');\n")
    _write(tmp_path / "apps/web/e2e/coverage/bad.spec.ts", "test" + ".skip('generated');\n")
    report = evaluate(tmp_path, _register(tmp_path, []), ["apps/web/e2e"], TODAY)
    assert report["findings"] == []


def test_release_mode_reports_mandatory_p0_entries(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    report = evaluate(tmp_path, _register(tmp_path, [_entry()]), ["tests/security"], TODAY)
    assert report["register_errors"] == []
    assert report["mandatory_p0_entries"][0]["id"] == "skip-001"
    assert report["summary"]["mandatory_p0_register_entries"] == 1
