from __future__ import annotations

"""Tenant context propagation guardrails for layer5-ground-truth.

These tests prove that the L5 auth dependency extracts tenant identity from the
canonical governance context and fails closed when context is missing or when
untrusted tenant hints are supplied.
"""

import uuid
from types import SimpleNamespace

import pytest
from fastapi import HTTPException
from value_fabric.shared.identity.context import RequestContext

from layer5_ground_truth.api.auth import TokenClaims, authorize_action, get_current_user


def _make_request(*, query_tenant_id: str | None = None, header_tenant_id: str | None = None, context: RequestContext | None = None) -> SimpleNamespace:
    headers = []
    if header_tenant_id is not None:
        headers.append((b"x-tenant-id", header_tenant_id.encode("utf-8")))
    query_string = f"tenant_id={query_tenant_id}" if query_tenant_id else ""
    request = SimpleNamespace(
        state=SimpleNamespace(governance_context=context),
        query_params=SimpleNamespace(get=lambda key, default=None: query_tenant_id if key == "tenant_id" else default),
        headers={"X-Tenant-ID": header_tenant_id} if header_tenant_id else {},
    )
    return request


def test_get_current_user_extracts_tenant_from_governance_context():
    tenant_id = uuid.uuid4()
    ctx = RequestContext(tenant_id=tenant_id, user_id="user-1", roles=["content_admin"])
    request = _make_request(context=ctx)

    claims = get_current_user(request)

    assert isinstance(claims, TokenClaims)
    assert claims.tenant_id == tenant_id
    assert claims.user_id == "user-1"


def test_get_current_user_fails_closed_without_context():
    request = _make_request()

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request)

    assert exc_info.value.status_code == 401
    assert exc_info.value.detail["error_code"] == "AUTH_CONTEXT_REQUIRED"


def test_get_current_user_rejects_query_param_tenant_hint():
    request = _make_request(query_tenant_id="some-tenant-id")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error_code"] == "AUTH_TENANT_HINT_REJECTED"


def test_get_current_user_rejects_header_tenant_hint():
    request = _make_request(header_tenant_id="some-tenant-id")

    with pytest.raises(HTTPException) as exc_info:
        get_current_user(request)

    assert exc_info.value.status_code == 403
    assert exc_info.value.detail["error_code"] == "AUTH_TENANT_HINT_REJECTED"


def test_authorize_action_propagates_tenant_to_shared_authorizer(monkeypatch: pytest.MonkeyPatch):
    captured = {}

    def _fake_authorize(action, ctx, target_tenant_id=None):
        captured.update({"action": action, "target_tenant_id": target_tenant_id})

    monkeypatch.setattr(
        "layer5_ground_truth.api.auth.authorize_shared_action",
        _fake_authorize,
    )

    tenant_id = uuid.uuid4()
    caller = TokenClaims(tenant_id=tenant_id, user_id="user-1", roles=["content_admin"])
    authorized = authorize_action("truth:create", caller)

    assert authorized.tenant_id == tenant_id
    assert captured["target_tenant_id"] == str(tenant_id)
    assert captured["action"] == "truth:create"
