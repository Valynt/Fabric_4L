from __future__ import annotations

"""H-01 regression tests for admin tenant suspension behavior."""


from uuid import uuid4

import pytest
from fastapi import HTTPException

from value_fabric.layer4.tools import admin
from value_fabric.shared.identity.context import RequestContext


class _FakeDb:
    def __init__(self) -> None:
        self.committed = False

    async def commit(self) -> None:
        self.committed = True


@pytest.mark.asyncio
async def test_suspend_tenant_requires_real_db_session() -> None:
    """The admin tool must not report success when no persistence layer is present."""
    ctx = RequestContext(tenant_id=uuid4(), user_id="admin-user", roles=["super_admin"])

    with pytest.raises(HTTPException) as excinfo:
        await admin.suspend_tenant(uuid4(), context=ctx)

    assert excinfo.value.status_code == 501
    assert "database session" in excinfo.value.detail


@pytest.mark.asyncio
async def test_suspend_tenant_uses_lifecycle_service_and_commits(monkeypatch: pytest.MonkeyPatch) -> None:
    tenant_id = uuid4()
    ctx = RequestContext(tenant_id=tenant_id, user_id="admin-user", roles=["tenant_admin"])
    db = _FakeDb()
    calls = {}

    async def fake_update_tenant_status(db_arg, tenant_id_arg, status_arg, *, reason, changed_by):
        calls["db"] = db_arg
        calls["tenant_id"] = tenant_id_arg
        calls["status"] = status_arg
        calls["reason"] = reason
        calls["changed_by"] = changed_by
        return object()

    def fake_emit_audit_event(*args, **kwargs):
        calls["audit_action"] = args[0]
        calls["audit_kwargs"] = kwargs
        return object()

    monkeypatch.setattr(admin, "update_tenant_status", fake_update_tenant_status)
    monkeypatch.setattr(admin, "emit_audit_event", fake_emit_audit_event)

    result = await admin.suspend_tenant(tenant_id, context=ctx, db=db, reason="policy violation")

    assert result["success"] is True
    assert result["tenant_id"] == str(tenant_id)
    assert result["status"] == "suspended"
    assert calls["db"] is db
    assert calls["tenant_id"] == tenant_id
    assert calls["status"] == "suspended"
    assert calls["reason"] == "policy violation"
    assert calls["changed_by"] == "admin-user"
    assert db.committed is True
    assert calls["audit_kwargs"]["resource_id"] == str(tenant_id)


@pytest.mark.asyncio
async def test_suspend_tenant_rejects_non_admin_context() -> None:
    ctx = RequestContext(tenant_id=uuid4(), user_id="regular-user", roles=["user"])

    with pytest.raises(HTTPException) as excinfo:
        await admin.suspend_tenant(uuid4(), context=ctx, db=_FakeDb())

    assert excinfo.value.status_code == 403
