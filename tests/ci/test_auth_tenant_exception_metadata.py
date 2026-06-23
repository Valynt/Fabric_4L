from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pytest
from scripts.ci import prod_stub_scan
from scripts.ci import python_contract_lint
from scripts.ci.python_contract_lint import check_file_with_regex

REFERENCE_DATE = date(2030, 1, 1)


@pytest.fixture
def fixed_today(monkeypatch: pytest.MonkeyPatch) -> date:
    class _FixedDate(date):
        @classmethod
        def today(cls) -> date:
            return REFERENCE_DATE

    monkeypatch.setattr(prod_stub_scan, "date", _FixedDate)
    monkeypatch.setattr(python_contract_lint, "date", _FixedDate)
    return REFERENCE_DATE


def test_prod_stub_scan_accepts_valid_structured_metadata_expires_on_or_after_today(
    fixed_today: date,
):
    future = (fixed_today + timedelta(days=30)).isoformat()
    metadata = f"temporary exception [auth-tenant-exception ticket=SEC-123 owner=platform.security expiry={future}]"
    assert prod_stub_scan._has_valid_exception_metadata(metadata)


def test_prod_stub_scan_rejects_missing_or_expired_metadata_expires_strictly_before_today(
    fixed_today: date,
):
    expired = (fixed_today - timedelta(days=1)).isoformat()
    invalid = f"[auth-tenant-exception ticket=SEC-123 owner=platform.security expiry={expired}]"
    assert not prod_stub_scan._has_valid_exception_metadata("no structured tag")
    assert not prod_stub_scan._has_valid_exception_metadata(invalid)


def test_prod_stub_scan_accepts_metadata_when_expiry_equals_today(fixed_today: date):
    same_day = fixed_today.isoformat()
    metadata = f"[auth-tenant-exception ticket=SEC-999 owner=platform.security expiry={same_day}]"
    assert prod_stub_scan._has_valid_exception_metadata(metadata)


def test_python_contract_lint_allows_security_todo_with_valid_tag_expires_on_or_after_today(
    tmp_path: Path,
    fixed_today: date,
):
    future = (fixed_today + timedelta(days=30)).isoformat()
    content = (
        "# TODO auth follow-up "
        f"[auth-tenant-exception ticket=SEC-321 owner=security.team expiry={future}]\n"
    )
    file_path = tmp_path / "services" / "layer1" / "api.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text(content, encoding="utf-8")
    findings = check_file_with_regex(Path("services/layer1/api.py"), content)
    assert not findings


def test_python_contract_lint_fails_security_todo_without_valid_tag(tmp_path):
    content = "# TODO tenant hardening follow-up\n"
    file_path = tmp_path / "services" / "layer1" / "api.py"
    file_path.parent.mkdir(parents=True)
    file_path.write_text(content, encoding="utf-8")

    findings = check_file_with_regex(Path("services/layer1/api.py"), content)
    assert findings
    assert any(
        finding.contract_id == "security_todo"
        and finding.severity == "critical"
        and "missing valid exception metadata" in finding.message
        for finding in findings
    )
