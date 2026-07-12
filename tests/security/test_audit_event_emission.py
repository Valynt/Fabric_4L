"""Test audit event emission invariants.

Verifies that TENANT_CONTEXT_SET audit events are emitted for all database session types.
"""

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import uuid4

import database_facade as database
import pytest


def _canonical_db():
    """Return the module whose globals _emit_tenant_context_set_audit reads.

    The facade copies names from src.database into its own globals, but the
    canonical functions still read globals from their defining module.
    Patching the facade's namespace has no effect on those functions.
    """
    canonical = getattr(database, "_CANONICAL", None)
    return canonical if canonical is not None else database


@pytest.mark.asyncio
async def test_emit_tenant_context_set_audit_emits_event_when_audit_available(monkeypatch):
    """Audit helper emits TENANT_CONTEXT_SET with expected context payload."""
    fake_emit = AsyncMock()
    _db = _canonical_db()
    monkeypatch.setattr(_db, "AUDIT_AVAILABLE", True)
    monkeypatch.setattr(_db, "emit_audit_event", fake_emit)
    monkeypatch.setattr(_db, "AuditAction", SimpleNamespace(TENANT_CONTEXT_SET="TENANT_CONTEXT_SET"))
    monkeypatch.setattr(_db, "AuditOutcome", SimpleNamespace(SUCCESS="SUCCESS"))

    class _Details:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def model_dump(self, exclude_none=True):
            return dict(self.kwargs)

    monkeypatch.setattr(_db, "TenantContextSetDetails", _Details)

    context = SimpleNamespace(
        isolation_tier="shared",
        tenant_id=str(uuid4()),
        user_id="user-123",
        api_key_id=None,
        service_account_id=None,
        request_id="req-123",
    )

    tenant_id = str(uuid4())
    await database._emit_tenant_context_set_audit(context, tenant_id)

    fake_emit.assert_awaited_once()
    _, kwargs = fake_emit.await_args
    assert kwargs["action"] == "TENANT_CONTEXT_SET"
    assert kwargs["outcome"] == "SUCCESS"
    assert kwargs["resource_type"] == "database_session"
    assert kwargs["resource_id"] == tenant_id
    assert kwargs["tenant_id"] == context.tenant_id
    assert kwargs["request_id"] == context.request_id
    assert kwargs["details"]["tenant_id"] == tenant_id
    assert kwargs["details"]["bypass"] is False


@pytest.mark.asyncio
async def test_emit_tenant_context_set_audit_is_non_blocking_on_emit_error(monkeypatch):
    """Audit emission failures must not raise and break request flow."""
    _db = _canonical_db()
    monkeypatch.setattr(_db, "AUDIT_AVAILABLE", True)

    async def _boom(**_kwargs):
        raise RuntimeError("audit backend unavailable")

    monkeypatch.setattr(_db, "emit_audit_event", _boom)
    monkeypatch.setattr(_db, "AuditAction", SimpleNamespace(TENANT_CONTEXT_SET="TENANT_CONTEXT_SET"))
    monkeypatch.setattr(_db, "AuditOutcome", SimpleNamespace(SUCCESS="SUCCESS"))

    class _Details:
        def __init__(self, **kwargs):
            self.kwargs = kwargs

        def model_dump(self, exclude_none=True):
            return dict(self.kwargs)

    monkeypatch.setattr(_db, "TenantContextSetDetails", _Details)

    context = SimpleNamespace(
        isolation_tier="shared",
        tenant_id=str(uuid4()),
        user_id="user-123",
        api_key_id=None,
        service_account_id=None,
        request_id="req-123",
    )

    await database._emit_tenant_context_set_audit(context, str(uuid4()))
