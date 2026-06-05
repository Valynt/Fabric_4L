from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request
from value_fabric.shared.error_handling import AuthorizationError, ValidationError

import layer1_ingestion.shared.database as database


def _make_request(reason: str | None = None) -> Request:
    headers = []
    if reason is not None:
        headers.append((b"x-privileged-reason", reason.encode("utf-8")))
    return Request({"type": "http", "headers": headers})


def _make_context(*, tenant_id=None, super_admin: bool = False):
    return SimpleNamespace(
        tenant_id=tenant_id,
        user_id="user-1" if not super_admin else "admin-1",
        api_key_id=None,
        request_id="req-1",
        is_super_admin=lambda: super_admin,
    )


def _make_session():
    session = MagicMock()
    session.info = {}
    return session


def test_optional_tenant_rejects_non_super_admin_without_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    database.reset_privileged_db_session_metrics()
    fake_session = _make_session()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)

    gen = database.get_db_with_optional_tenant_sync(
        request=_make_request("case-review"),
        context=_make_context(super_admin=False),
    )
    with pytest.raises(AuthorizationError, match="super admin role"):
        next(gen)

    assert database.get_privileged_db_session_metrics()["denials_total"] == 1


def test_optional_tenant_super_admin_requires_privileged_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    database.reset_privileged_db_session_metrics()
    fake_session = _make_session()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)

    gen = database.get_db_with_optional_tenant_sync(
        request=_make_request(),
        context=_make_context(super_admin=True),
    )
    with pytest.raises(ValidationError, match="X-Privileged-Reason"):
        next(gen)

    assert database.get_privileged_db_session_metrics()["missing_reason_total"] == 1


def test_optional_tenant_super_admin_uses_privileged_mode_without_empty_tenant_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database.reset_privileged_db_session_metrics()
    fake_session = _make_session()
    metrics = MagicMock()
    monkeypatch.setattr(database, "SessionLocal", lambda: fake_session)
    monkeypatch.setattr(database, "get_metrics", lambda: metrics)

    gen = database.get_db_with_optional_tenant_sync(
        request=_make_request("incident-review"),
        context=_make_context(super_admin=True),
    )
    session = next(gen)
    gen.close()

    assert session is fake_session
    fake_session.execute.assert_not_called()
    assert fake_session.info[database._TENANT_CONTEXT_STATE_KEY] == "bypass"
    assert fake_session.info[database._TENANT_CONTEXT_VALUE_KEY] is None
    assert fake_session.info[database._TENANT_BYPASS_REASON_KEY] == "privileged_cross_tenant:incident-review"
    assert database.get_privileged_db_session_metrics()["activations_total"] == 1
    metrics.increment_privileged_db_session_activation.assert_called_once_with("cross_tenant_admin")


def test_database_module_source_contains_no_empty_tenant_bypass_sql() -> None:
    source = Path(database.__file__).read_text(encoding="utf-8")
    assert "SET LOCAL app.tenant_id = ''" not in source
