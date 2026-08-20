from __future__ import annotations

from datetime import date
from pathlib import Path

import yaml
from scripts.ci.check_test_skip_governance import evaluate

TODAY = date(2026, 5, 11)


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _register(tmp_path: Path, entries: list[dict[str, object]]) -> Path:
    path = tmp_path / "register.yaml"
    path.write_text(yaml.safe_dump({"entries": entries}, sort_keys=False), encoding="utf-8")
    return path


def _entry(**overrides: object) -> dict[str, object]:
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
        "classification": "temporary_bug_waiver",
        "disposition": "replace_with_characterization",
        "remediation": {
            "ticket_id": "VF-SKIP-001",
            "due_on": "2026-06-30",
            "work_item": "Replace waiver with executable allow and deny coverage.",
        },
    }
    entry.update(overrides)
    return entry


def test_unregistered_p0_skip_fails(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    report = evaluate(tmp_path, _register(tmp_path, []), ["tests/security"], TODAY)
    assert report["unregistered"]
    assert report["unregistered"][0]["marker"] == "pytest.skip"
    assert "TDG201" in {item["code"] for item in report["violations"]}


def test_registered_non_expired_skip_passes(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    report = evaluate(tmp_path, _register(tmp_path, [_entry()]), ["tests/security"], TODAY)
    assert report["register_errors"] == []
    assert report["unregistered"] == []
    assert report["forbidden"] == []
    assert report["summary"] | {"elapsed_seconds": 0} == {
        "total_registered_markers": 1,
        "total_detected_markers": 1,
        "expired_register_entries": 0,
        "unregistered_markers": 0,
        "forbidden_markers": 0,
        "matched_register_entries": 1,
        "mandatory_p0_register_entries": 1,
        "classification_counts": {
            "obsolete_test": 0,
            "temporary_bug_waiver": 1,
            "unacceptable_coverage_gap": 0,
            "valid_environment_limitation": 0,
        },
        "elapsed_seconds": 0,
        "ambiguous_markers": 0,
        "stale_register_entries": 0,
        "violation_count": 0,
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


def test_register_entry_requires_classification(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    bad_entry = _entry()
    del bad_entry["classification"]
    report = evaluate(tmp_path, _register(tmp_path, [bad_entry]), ["tests/security"], TODAY)
    assert any("classification" in error for error in report["register_errors"])


def test_classification_counts_are_reported(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'import pytest\npytest.skip("dependency missing")\n')
    report = evaluate(tmp_path, _register(tmp_path, [_entry()]), ["tests/security"], TODAY)
    assert report["summary"]["classification_counts"]["temporary_bug_waiver"] == 1


def test_valid_environment_limitation_is_grouped_as_valid(tmp_path: Path) -> None:
    _write(tmp_path / "tests/integration/test_db.py", 'pytest.skip("postgres unavailable")\n')
    entry = _entry(
        path_pattern="tests/integration/test_db.py",
        reason_pattern="postgres unavailable",
        classification="valid_environment_limitation",
        severity="P2",
        launch_gate="optional",
        disposition="retain",
    )
    report = evaluate(tmp_path, _register(tmp_path, [entry]), ["tests"], TODAY)
    assert report["violations"] == []
    assert [item["id"] for item in report["inventory"]["VALID"]] == ["skip-001"]


def test_duplicate_and_ambiguous_entries_are_denied(tmp_path: Path) -> None:
    _write(tmp_path / "tests/unit/test_worker.py", 'pytest.skip("dependency missing")\n')
    entries = [
        _entry(path_pattern="tests/unit/*.py", severity="P1", launch_gate="optional"),
        _entry(id="skip-002", path_pattern="tests/**/*.py", severity="P1", launch_gate="optional"),
    ]
    report = evaluate(tmp_path, _register(tmp_path, entries), ["tests"], TODAY)
    codes = {item["code"] for item in report["violations"]}
    assert "TDG202" in codes


def test_unknown_severity_has_stable_violation_code(tmp_path: Path) -> None:
    _write(tmp_path / "tests/unit/test_worker.py", 'pytest.skip("dependency missing")\n')
    report = evaluate(
        tmp_path,
        _register(tmp_path, [_entry(path_pattern="tests/unit/test_worker.py", severity="URGENT")]),
        ["tests"],
        TODAY,
    )
    assert "TDG105" in {item["code"] for item in report["violations"]}


def test_stale_registration_is_denied(tmp_path: Path) -> None:
    _write(tmp_path / "tests/unit/test_worker.py", "def test_worker(): pass\n")
    report = evaluate(
        tmp_path,
        _register(tmp_path, [_entry(path_pattern="tests/unit/test_worker.py")]),
        ["tests"],
        TODAY,
    )
    assert "TDG203" in {item["code"] for item in report["violations"]}


def test_critical_path_obsolete_skip_is_denied(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'pytest.skip("dependency missing")\n')
    report = evaluate(
        tmp_path,
        _register(
            tmp_path,
            [_entry(classification="obsolete_test", disposition="remove")],
        ),
        ["tests"],
        TODAY,
    )
    assert "TDG301" in {item["code"] for item in report["violations"]}


def test_default_scan_discovers_nested_service_test_debt(tmp_path: Path) -> None:
    _write(
        tmp_path / "services/layer9/tests/test_hidden.py",
        'pytest.skip("previously invisible")\n',
    )
    report = evaluate(tmp_path, _register(tmp_path, []), [], TODAY)
    assert "TDG201" in {item["code"] for item in report["violations"]}
    assert report["unregistered"][0]["path"] == "services/layer9/tests/test_hidden.py"


def test_report_contains_deterministic_remediation_queue(tmp_path: Path) -> None:
    _write(tmp_path / "tests/security/test_auth.py", 'pytest.skip("dependency missing")\n')
    report = evaluate(tmp_path, _register(tmp_path, [_entry()]), ["tests"], TODAY)
    assert report["schema_version"] == "1.0"
    assert report["remediation_queue"][0]["id"] == "skip-001"
