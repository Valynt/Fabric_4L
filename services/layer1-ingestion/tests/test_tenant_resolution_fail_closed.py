from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi import Request
from value_fabric.shared.error_handling.exceptions import AuthenticationError
from value_fabric.shared.identity.context import RequestContext

from layer1_ingestion.api.app_monolith import get_tenant_id


def _make_request(ctx: RequestContext | None = None) -> Request:
    request = Request({"type": "http", "method": "GET", "url": "http://test"})
    if ctx is not None:
        request.state.governance_context = ctx
    return request


def test_get_tenant_id_requires_governance_context() -> None:
    """Tenant resolution must fail closed when no identity context is present."""
    request = _make_request()
    with pytest.raises(AuthenticationError):
        get_tenant_id(request)


def test_get_tenant_id_returns_tenant_from_context() -> None:
    """Tenant resolution must use the verified governance context tenant_id."""
    tenant = uuid4()
    ctx = RequestContext(tenant_id=tenant, user_id="user-1")
    request = _make_request(ctx)
    assert get_tenant_id(request) == tenant
