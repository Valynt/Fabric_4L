"""Tests for the Clerk tenant resolution endpoint.

These tests import the route module directly to avoid pulling in the full API
service dependency tree (e.g., rate-limiting packages required by unrelated
routers). The authentication-gate tests at the end use the full app via
``TestClient`` because they exercise the ``require_clerk_authenticated``
dependency, not the resolution helper in isolation.
"""
from __future__ import annotations

import json

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi import Request
from fastapi.testclient import TestClient
from value_fabric.shared.error_handling.exceptions import AuthorizationError
from value_fabric.shared.error_handling.models import ErrorCode
from value_fabric.shared.identity.fabric_auth import AuthContext

from app.core.auth_directory import get_auth_directory
from app.core.clerk_config import reset_auth_settings_cache
from app.main import app
from app.routers import clerk_auth as clerk_auth_module


def _ed25519_keypair() -> tuple[str, str]:
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _rsa_keypair() -> tuple[str, str]:
    from cryptography.hazmat.primitives.asymmetric import rsa

    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    public_pem = (
        private.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


@pytest.fixture
def clerk_env_setup(monkeypatch: pytest.MonkeyPatch) -> None:
    signing_private_pem, signing_public_pem = _ed25519_keypair()
    _, clerk_public_pem = _rsa_keypair()
    monkeypatch.setenv("AUTH_PROVIDER", "clerk")
    monkeypatch.setenv("CLERK_ISSUER", "https://accounts.example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "fabric4l-api")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "https://app.example.com")
    monkeypatch.setenv("CLERK_PINNED_JWT_PEM", clerk_public_pem)
    monkeypatch.setenv("FABRIC_AUTH_SIGNING_KEY", signing_private_pem)
    monkeypatch.setenv("FABRIC_AUTH_SIGNING_KID", "gateway-k1")
    monkeypatch.setenv(
        "FABRIC_AUTH_PUBLIC_KEYS",
        json.dumps([{"kid": "gateway-k1", "public_pem": signing_public_pem}]),
    )
    reset_auth_settings_cache()


def _build_request() -> Request:
    return Request(scope={"type": "http", "method": "GET", "path": "/v1/auth/clerk/tenant"})


def _build_auth_context(tenant_id: str = "ten_1", org_id: str = "org_1") -> AuthContext:
    return AuthContext(
        clerk_user_id="user_1",
        clerk_org_id=org_id,
        user_id="u1",
        tenant_id=tenant_id,
        roles=frozenset(["tenant_admin"]),
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
        id="ten_1",
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
    assert response.roles == ["tenant_admin"]
    assert response.permissions == ["tenant:read"]


def test_clerk_tenant_response_schema() -> None:
    schema = clerk_auth_module.ClerkTenantResponse.model_json_schema()
    expected_fields = {
        "fabric_tenant_id",
        "tenant_slug",
        "clerk_org_id",
        "status",
        "roles",
        "permissions",
    }
    assert set(schema["properties"].keys()) == expected_fields
    assert set(schema["required"]) == {
        "fabric_tenant_id",
        "clerk_org_id",
        "status",
        "roles",
        "permissions",
    }


async def test_clerk_tenant_fails_closed_when_org_id_missing() -> None:
    directory = get_auth_directory()
    auth = _build_auth_context(org_id=None)  # type: ignore[arg-type]

    with pytest.raises(AuthorizationError) as exc_info:
        clerk_auth_module._resolve_directory_tenant(directory, auth.clerk_org_id)

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == ErrorCode.AUTH_TENANT_UNRESOLVED


async def test_clerk_tenant_fails_closed_when_tenant_missing() -> None:
    directory = get_auth_directory()

    with pytest.raises(AuthorizationError) as exc_info:
        clerk_auth_module._resolve_directory_tenant(directory, "org_unknown")

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == ErrorCode.AUTH_TENANT_UNRESOLVED


@pytest.mark.parametrize("status", ["suspended", "deleted", "inactive"])
async def test_clerk_tenant_fails_closed_for_non_active_tenant(status: str) -> None:
    directory = get_auth_directory()
    directory.upsert_tenant(
        id="ten_suspended",
        clerk_org_id="org_suspended",
        name="Suspended",
        slug="suspended",
        status=status,
    )

    with pytest.raises(AuthorizationError) as exc_info:
        clerk_auth_module._resolve_directory_tenant(directory, "org_suspended")

    assert exc_info.value.status_code == 403
    assert exc_info.value.error_code == ErrorCode.AUTH_TENANT_UNRESOLVED


async def test_clerk_tenant_wrong_org_cannot_resolve_other_tenant() -> None:
    directory = get_auth_directory()
    directory.upsert_tenant(
        id="ten_1",
        clerk_org_id="org_1",
        name="Acme",
        slug="acme",
        status="active",
    )
    directory.upsert_tenant(
        id="ten_2",
        clerk_org_id="org_2",
        name="Hooli",
        slug="hooli",
        status="active",
    )

    # Auth context claims org_2 but the request fabric tenant id is ten_1.
    # The backend must resolve from the verified Clerk org id, not the tenant id
    # asserted in the auth context, so org_2 resolves to a different tenant.
    auth = _build_auth_context(tenant_id="ten_1", org_id="org_2")
    request = _build_request()
    response = await clerk_auth_module.get_clerk_tenant(
        request=request,
        auth=auth,
        directory=directory,
    )

    assert response.clerk_org_id == "org_2"
    assert response.tenant_slug == "hooli"
    assert response.fabric_tenant_id == "ten_2"


async def test_clerk_tenant_response_does_not_leak_unauthorized_metadata() -> None:
    directory = get_auth_directory()
    directory.upsert_tenant(
        id="ten_1",
        clerk_org_id="org_1",
        name="SecretInternalName",
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

    # The response must expose only the canonical fields; internal directory
    # metadata such as the raw tenant name must not leak.
    response_dict = response.model_dump()
    assert set(response_dict.keys()) == {
        "fabric_tenant_id",
        "tenant_slug",
        "clerk_org_id",
        "status",
        "roles",
        "permissions",
    }
    assert "SecretInternalName" not in str(response_dict)


def test_clerk_tenant_missing_token_returns_401(clerk_env_setup: None) -> None:
    client = TestClient(app)
    response = client.get("/v1/auth/clerk/tenant")
    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.AUTH_TOKEN_MISSING


def test_clerk_tenant_invalid_token_returns_401(clerk_env_setup: None) -> None:
    client = TestClient(app)
    response = client.get(
        "/v1/auth/clerk/tenant",
        headers={"Authorization": "Bearer not-a-real-jwt"},
    )
    assert response.status_code == 401
    assert response.json()["error"]["code"] == ErrorCode.AUTH_TOKEN_INVALID
