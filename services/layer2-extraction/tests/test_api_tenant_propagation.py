"""Tenant context propagation guardrails for layer2-extraction.

These tests prove that the L2 route dependency ``require_authenticated`` extracts
tenant context from the canonical governance context and rejects unauthenticated
or unknown-auth-source requests.
"""

from __future__ import annotations

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from value_fabric.shared.identity.context import AUTH_SOURCE_API_KEY, AUTH_SOURCE_UNKNOWN, RequestContext

from layer2_extraction.api.deps import require_authenticated


def _make_request(context: RequestContext | None = None) -> SimpleNamespace:
    return SimpleNamespace(state=SimpleNamespace(governance_context=context))


@pytest.mark.asyncio
async def test_require_authenticated_extracts_tenant_context():
    tenant_id = uuid.uuid4()
    ctx = RequestContext(tenant_id=tenant_id, user_id="user-1", auth_source=AUTH_SOURCE_API_KEY)
    request = _make_request(context=ctx)

    result = await require_authenticated(ctx=ctx)

    assert result.tenant_id == tenant_id
    assert result.user_id == "user-1"


@pytest.mark.asyncio
async def test_require_authenticated_fails_closed_without_context():
    with pytest.raises(HTTPException) as exc_info:
        await require_authenticated(ctx=None)

    assert exc_info.value.status_code == 401
    assert "Authentication context is required" in str(exc_info.value.detail)


@pytest.mark.asyncio
async def test_require_authenticated_rejects_unknown_auth_source():
    ctx = RequestContext(tenant_id=uuid.uuid4(), user_id="user-1", auth_source=AUTH_SOURCE_UNKNOWN)
    with pytest.raises(HTTPException) as exc_info:
        await require_authenticated(ctx=ctx)

    assert exc_info.value.status_code == 401
    assert "Authentication context is invalid" in str(exc_info.value.detail)


def test_l2_request_context_import_is_available():
    """Layer2 must resolve the shared RequestContext, not the fallback object."""
    from layer2_extraction.api.deps import RequestContext as L2RequestContext

    assert L2RequestContext is not object
    assert hasattr(L2RequestContext, "tenant_id")
