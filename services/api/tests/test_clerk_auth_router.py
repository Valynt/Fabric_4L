"""Tests for the Clerk tenant resolution endpoint.

These tests import the route module directly to avoid pulling in the full API
service dependency tree (e.g., rate-limiting packages required by unrelated
routers).
"""
from __future__ import annotations

import pytest
from fastapi import Request

from app.core.auth_directory import AuthDirectory, get_auth_directory
from value_fabric.shared.identity.fabric_auth import AuthContext
from app.routers import clerk_auth as clerk_auth_module


def _build_request() -> Request:
    return Request(scope={"type": "http", "method": "GET", "path": "/v1/auth/clerk/tenant"})


def _build_auth_context(tenant_id: str = "ten_1", org_id: str = "org_1") -> AuthContext:
    return AuthContext(
        clerk_user_id="user_1",
        clerk_org_id=org_id,
        user_id="u1",
        tenant_id=tenant_id,
        roles=frozenset(["org:admin"]),
        permissions=frozenset(["tenant:read"]),
        request_id="req_1",
        iat=1_700_000_000,
        exp=2_000_000_000,
        kid="test-key",
        iss="fabric4l-gateway",
        aud="fabric4l-internal",
    )


async def test_clerk_tenant_resolves_active_org() -> None:
    directory = get_auth_directory()
    directory.upsert_tenant(
        clerk_org_id="org_1",
        name="Acme",
        slug="acme",
        status="active",
    )

    auth = _build_auth_context()
    request = _build_request()
    response = await clerk_auth_module.get_clerk_tenant(
        request=request,
        auth=auth,
        directory=directory,
    )

    assert response.fabric_tenant_id == "ten_1"
    assert response.tenant_slug == "acme"
    assert response.clerk_org_id == "org_1"
    assert response.status == "active"
    assert response.roles == ["org:admin"]
    assert response.permissions == ["tenant:read"]


def test_clerk_tenant_response_schema() -> None:
    schema = clerk_auth_module.ClerkTenantResponse.model_json_schema()
    assert set(schema["properties"].keys()) == {
        "fabric_tenant_id",
        "tenant_slug",
        "clerk_org_id",
        "status",
        "roles",
        "permissions",
    }
    assert schema["required"] == [
        "fabric_tenant_id",
        "tenant_slug",
        "clerk_org_id",
        "status",
        "roles",
        "permissions",
    ]
