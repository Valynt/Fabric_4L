from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path
import pytest
import yaml

from scripts.ci import check_security_exceptions
from scripts.ci.check_security_exceptions import (
    validate_registry,
    iter_exceptions,
)

REFERENCE_DATE = date(2030, 1, 1)


@pytest.fixture
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> date:
    class _FixedDate(date):
        @classmethod
        def reference(cls) -> date:
            return REFERENCE_DATE

    monkeypatch.setattr(check_security_exceptions, "ReferenceDate", _FixedDate)
    return REFERENCE_DATE


def test_empty_registry_is_valid(fixed_today: date):
    data = {"schema_version": 1, "exceptions": {}}
    errors, warnings = validate_registry(data, fixed_today)
    assert errors == []


def test_valid_exception_entry_passes(fixed_today: date):
    future = (fixed_today + timedelta(days=30)).isoformat()
    data = {
        "schema_version": 1,
        "exceptions": {
            "semgrep:rule-1": {
                "owner": "security.team",
                "expires_on": future,
                "justification": "False positive due to mock wrapper",
                "compensating_control": "Protected by upstream gateway auth validation",
                "ticket": "SEC-101",
            }
        },
    }
    errors, warnings = validate_registry(data, fixed_today)
    assert errors == []


def test_valid_exception_with_yaml_date_object(fixed_today: date):
    future_date = fixed_today + timedelta(days=30)
    data = {
        "schema_version": 1,
        "exceptions": {
            "semgrep:rule-2": {
                "owner": "security.team",
                "expires_on": future_date,
                "justification": "False positive",
                "compensating_control": "Protected by auth gateway",
                "ticket": "SEC-102",
            }
        },
    }
    errors, warnings = validate_registry(data, fixed_today)
    assert errors == []


def test_expired_exception_fails_closed(fixed_today: date):
    past = (fixed_today - timedelta(days=1)).isoformat()
    data = {
        "schema_version": 1,
        "exceptions": {
            "semgrep:rule-expired": {
                "owner": "security.team",
                "expires_on": past,
                "justification": "Reviewed debt",
                "compensating_control": "Manual review",
                "ticket": "SEC-103",
            }
        },
    }
    errors, warnings = validate_registry(data, fixed_today)
    assert len(errors) == 1
    assert "EXPIRED on" in errors[0]


def test_missing_required_fields_fails_closed(fixed_today: date):
    future = (fixed_today + timedelta(days=30)).isoformat()
    data = {
        "schema_version": 1,
        "exceptions": {
            "missing-fields": {
                "expires_on": future,
            }
        },
    }
    errors, warnings = validate_registry(data, fixed_today)
    assert len(errors) >= 4
    assert any("missing required 'owner'" in m for m in errors)
    assert any("missing required 'justification'" in m for m in errors)
    assert any("missing required 'compensating_control'" in m for m in errors)
    assert any("missing required 'ticket'" in m for m in errors)


def test_invalid_date_format_fails_closed(fixed_today: date):
    data = {
        "schema_version": 1,
        "exceptions": {
            "bad-date": {
                "owner": "sec",
                "expires_on": "2030/01/01",
                "justification": "reason",
                "compensating_control": "control",
                "ticket": "SEC-104",
            }
        },
    }
    errors, warnings = validate_registry(data, fixed_today)
    assert any("must be an ISO YYYY-MM-DD date" in e for e in errors)


def test_main_cli_with_repo_registry(tmp_path: Path):
    registry_file = tmp_path / "security_exceptions.yaml"
    registry_file.write_text(
        yaml.safe_dump({"schema_version": 1, "exceptions": {}}),
        encoding="utf-8",
    )
    rc = check_security_exceptions.main(
        [
            "--registry",
            str(registry_file),
            "--reference",
            "2030-01-01",
        ]
    )
    assert rc == 0

