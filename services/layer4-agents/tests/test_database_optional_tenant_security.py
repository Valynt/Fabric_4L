from __future__ import annotations

from pathlib import Path
import sys
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from starlette.requests import Request

SERVICE_ROOT = Path(__file__).resolve().parents[1]
if str(SERVICE_ROOT) not in sys.path:
    sys.path.insert(0, str(SERVICE_ROOT))

import src.database as database
from value_fabric.shared.identity.context import RequestContext


class _AsyncFactory:
    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_request(reason: str | None = None) -> Request:
    headers = []
    if reason is not None:
        headers.append((b"x-privileged-reason", reason.encode("utf-8")))
    return Request({"type": "http", "headers": headers})


@pytest.mark.asyncio
async def test_optional_tenant_rejects_non_super_admin_without_tenant(monkeypatch: pytest.MonkeyPatch) -> None:
    database.reset_privileged_db_session_metrics()
    fake_session = MagicMock()
    fake_session.info = {}
    monkeypatch.setattr(database, "get_session_factory", lambda: _AsyncFactory(fake_session))

    context = RequestContext(
        tenant_id=None,
        user_id="user-1",
        roles=["tenant_admin"],
        auth_source="jwt_claim",
    )

    agen = database.get_db_with_optional_tenant(request=_make_request("case-review"), context=context)
    with pytest.raises(HTTPException, match="super admin role"):
        await agen.__anext__()

    assert database.get_privileged_db_session_metrics()["denials_total"] == 1


@pytest.mark.asyncio
async def test_optional_tenant_super_admin_requires_privileged_reason(monkeypatch: pytest.MonkeyPatch) -> None:
    database.reset_privileged_db_session_metrics()
    fake_session = MagicMock()
    fake_session.info = {}
    monkeypatch.setattr(database, "get_session_factory", lambda: _AsyncFactory(fake_session))

    context = RequestContext(
        tenant_id=None,
        user_id="admin-1",
        roles=["super_admin"],
        auth_source="jwt_claim",
    )

    agen = database.get_db_with_optional_tenant(request=_make_request(), context=context)
    with pytest.raises(HTTPException, match="X-Privileged-Reason"):
        await agen.__anext__()

    assert database.get_privileged_db_session_metrics()["missing_reason_total"] == 1


@pytest.mark.asyncio
async def test_optional_tenant_super_admin_uses_privileged_mode_without_empty_tenant_sql(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    database.reset_privileged_db_session_metrics()
    fake_session = MagicMock()
    fake_session.info = {}
    fake_session.execute = AsyncMock()
    metrics = MagicMock()
    monkeypatch.setattr(database, "get_session_factory", lambda: _AsyncFactory(fake_session))
    monkeypatch.setattr("src.metrics.get_metrics", lambda: metrics)
    audit_mock = AsyncMock()
    monkeypatch.setattr(database, "_emit_tenant_context_set_audit", audit_mock)

    context = RequestContext(
        tenant_id=None,
        user_id="admin-1",
        roles=["super_admin"],
        auth_source="jwt_claim",
        request_id="req-1",
    )

    agen = database.get_db_with_optional_tenant(
        request=_make_request("incident-review"),
        context=context,
    )
    session = await agen.__anext__()
    await agen.aclose()

    assert session is fake_session
    fake_session.execute.assert_not_awaited()
    assert fake_session.info[database._TENANT_CONTEXT_STATE_KEY] == "bypass"
    assert fake_session.info[database._TENANT_CONTEXT_VALUE_KEY] is None
    assert fake_session.info[database._TENANT_BYPASS_REASON_KEY] == "privileged_cross_tenant:incident-review"
    assert database.get_privileged_db_session_metrics()["activations_total"] == 1
    metrics.increment_privileged_db_session_activation.assert_called_once_with(None, "cross_tenant_admin")
    audit_mock.assert_awaited_once()


def test_database_module_source_contains_no_empty_tenant_bypass_sql() -> None:
    source = Path(database.__file__).read_text(encoding="utf-8")
    assert "SET LOCAL app.tenant_id = ''" not in source
    assert "set_config('app.tenant_id', '', true)" not in source
