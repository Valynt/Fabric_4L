from __future__ import annotations

import base64
import json

import pytest
from fastapi import HTTPException
from starlette.requests import Request

from value_fabric.layer3.api.auth_context import TenantBearerContext, extract_tenant_from_bearer

# Alias kept for test readability — tests call extract_tenant_from_bearer directly below.
_get_tenant_context = extract_tenant_from_bearer


def _token(payload: dict[str, str]) -> str:
    def encode(part: dict[str, str]) -> str:
        raw = json.dumps(part, separators=(",", ":")).encode("utf-8")
        return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")

    return f"{encode({'alg': 'none'})}.{encode(payload)}.signature"


def _request(token: str, *, tenant_header: str | None = None) -> Request:
    headers = [(b"authorization", f"Bearer {token}".encode("utf-8"))]
    if tenant_header is not None:
        headers.append((b"x-tenant-id", tenant_header.encode("utf-8")))
    return Request({"type": "http", "method": "GET", "path": "/v1/models", "headers": headers})


def test_model_registry_tenant_context_requires_tenant_claim() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _get_tenant_context(_request(_token({"sub": "user-1"})))

    assert exc_info.value.status_code == 401
    assert "tenant_id" in str(exc_info.value.detail)


def test_model_registry_tenant_context_rejects_forged_header_tenant() -> None:
    with pytest.raises(HTTPException) as exc_info:
        _get_tenant_context(_request(_token({"sub": "user-1", "tenant_id": "tenant-a"}), tenant_header="tenant-b"))

    assert exc_info.value.status_code == 403


def test_model_registry_tenant_context_returns_canonical_payload() -> None:
    context = extract_tenant_from_bearer(
        _request(_token({"sub": "user-1", "tenant_id": "tenant-a"}), tenant_header="tenant-a")
    )

    assert isinstance(context, TenantBearerContext)
    assert context.tenant_id == "tenant-a"
    assert context.user_id == "user-1"
    assert context.source == "authorization_bearer"
    assert context.auth_method == "jwt"
