"""Cross-tenant hostile invariants for layer1-ingestion.

These tests prove that the L1 database session dependency binds tenant A to a
different RLS context than tenant B, and that it fails closed when the
authenticated tenant context is missing or invalid.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from value_fabric.shared.error_handling.exceptions import AuthenticationError
from value_fabric.shared.identity.context import RequestContext

from layer1_ingestion.shared.database import get_db_with_tenant


def _make_request(context: RequestContext | None = None) -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(governance_context=context))


def _capture_session_execute():
    """Return a mocked SessionLocal that records SET LOCAL app.tenant_id calls."""
    calls = []

    class _FakeSession:
        def __init__(self):
            self.info = {}

        def execute(self, statement, params=None):
            calls.append((str(statement), params))

        def commit(self):
            pass

        def rollback(self):
            pass

        def close(self):
            pass

    return _FakeSession, calls


def test_get_db_with_tenant_sets_rls_context_for_tenant_a():
    tenant_id = uuid.uuid4()
    request = _make_request(context=RequestContext(tenant_id=tenant_id))

    FakeSession, calls = _capture_session_execute()
    with patch("layer1_ingestion.shared.database.SessionLocal", FakeSession):
        gen = get_db_with_tenant(request)
        next(gen)
        gen.close()

    assert any("SET LOCAL app.tenant_id" in stmt and params["tenant_id"] == str(tenant_id) for stmt, params in calls)


def test_get_db_with_tenant_isolates_tenant_a_from_tenant_b():
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()

    FakeSession, calls_a = _capture_session_execute()
    with patch("layer1_ingestion.shared.database.SessionLocal", FakeSession):
        gen = get_db_with_tenant(_make_request(context=RequestContext(tenant_id=tenant_a)))
        next(gen)
        gen.close()

    assert calls_a[0][1]["tenant_id"] == str(tenant_a)

    FakeSession, calls_b = _capture_session_execute()
    with patch("layer1_ingestion.shared.database.SessionLocal", FakeSession):
        gen = get_db_with_tenant(_make_request(context=RequestContext(tenant_id=tenant_b)))
        next(gen)
        gen.close()

    assert calls_b[0][1]["tenant_id"] == str(tenant_b)
    assert calls_a[0][1]["tenant_id"] != calls_b[0][1]["tenant_id"]


def test_get_db_with_tenant_fails_closed_without_context():
    request = _make_request(context=None)
    with pytest.raises(AuthenticationError, match="Authentication required"):
        gen = get_db_with_tenant(request)
        next(gen)


def test_get_db_with_tenant_fails_closed_with_invalid_tenant_id():
    request = _make_request(context=RequestContext(tenant_id="   "))
    with pytest.raises(Exception):
        gen = get_db_with_tenant(request)
        next(gen)
