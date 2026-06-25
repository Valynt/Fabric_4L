"""Tenant context propagation guardrails for layer1-ingestion.

These tests prove that the L1 FastAPI dependencies extract tenant and user
identity from the canonical governance context and fail closed when the
context is missing or malformed.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from value_fabric.shared.error_handling.exceptions import AuthenticationError
from value_fabric.shared.identity.context import RequestContext

from layer1_ingestion.api.dependencies import get_current_user_id, get_tenant_id


def _make_request(context: RequestContext | None = None) -> SimpleNamespace:
    return SimpleNamespace(
        state=SimpleNamespace(governance_context=context),
        url=SimpleNamespace(path="/test"),
    )


def test_get_tenant_id_extracts_from_governance_context() -> None:
    tenant_id = uuid.uuid4()
    request = _make_request(context=RequestContext(tenant_id=tenant_id))
    assert get_tenant_id(request) == tenant_id


def test_get_tenant_id_fails_closed_without_context() -> None:
    request = _make_request(context=None)
    with pytest.raises(AuthenticationError, match="Authentication required"):
        get_tenant_id(request)


def test_get_current_user_id_extracts_uuid_from_governance_context() -> None:
    user_id = uuid.uuid4()
    request = _make_request(context=RequestContext(tenant_id=uuid.uuid4(), user_id=str(user_id)))
    assert get_current_user_id(request) == user_id


def test_get_current_user_id_fails_closed_without_context() -> None:
    request = _make_request(context=None)
    with pytest.raises(AuthenticationError, match="Authentication required"):
        get_current_user_id(request)


def test_get_current_user_id_rejects_invalid_uuid_format() -> None:
    request = _make_request(context=RequestContext(tenant_id=uuid.uuid4(), user_id="not-a-uuid"))
    with pytest.raises(AuthenticationError, match="Invalid user ID format"):
        get_current_user_id(request)
