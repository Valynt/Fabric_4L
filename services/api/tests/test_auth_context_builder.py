from __future__ import annotations

import time

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from value_fabric.shared.identity.fabric_auth import (
    KeySet,
    SigningKey,
    VerificationKey,
    sign_envelope,
    verify_envelope,
)
from value_fabric.shared.identity.fabric_auth.signer import ALGORITHM

from app.core.auth_context_builder import build_auth_context, normalize_clerk_role
from app.core.auth_directory import AuthDirectory
from app.core.clerk_config import InternalEnvelopeSettings
from app.core.clerk_verifier import ClerkClaims


def _ed25519_envelope_settings() -> InternalEnvelopeSettings:
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
    return InternalEnvelopeSettings(
        signing_key=SigningKey(kid="gateway-k1", private_pem=private_pem),
        verification_keys=KeySet([VerificationKey(kid="gateway-k1", public_pem=public_pem)]),
        issuer="gateway-test",
        audience="internal-test",
        envelope_ttl_seconds=120,
    )


def test_normalize_clerk_role_maps_clerk_org_roles_to_fabric_rbac() -> None:
    assert normalize_clerk_role("org:admin") == "tenant_admin"
    assert normalize_clerk_role("admin") == "tenant_admin"
    assert normalize_clerk_role("org:member") == "analyst"
    assert normalize_clerk_role("basic_member") == "analyst"
    assert normalize_clerk_role("org:guest") == "read_only"
    assert normalize_clerk_role("custom_role") == "custom_role"


def test_build_auth_context_normalizes_roles_and_uses_envelope_settings() -> None:
    directory = AuthDirectory()
    directory.upsert_user(
        id="user_1",
        clerk_user_id="clerk_user_1",
        email="alice@example.com",
        display_name="Alice",
        status="active",
    )
    directory.upsert_tenant(
        id="tenant_1",
        clerk_org_id="org_1",
        name="Acme",
        slug="acme",
        status="active",
    )
    directory.upsert_membership(
        clerk_org_id="org_1",
        clerk_user_id="clerk_user_1",
        clerk_membership_id="mem_1",
        role="org:admin",
        status="active",
    )

    context = build_auth_context(
        claims=ClerkClaims(
            sub="clerk_user_1",
            org_id="org_1",
            org_role="org:member",
            org_permissions=("tenant:read",),
            azp="https://app.example.com",
            raw={},
        ),
        directory=directory,
        envelope_settings=_ed25519_envelope_settings(),
        request_id="req_1",
        now=1_700_000_000,
    )

    assert context.roles == frozenset({"tenant_admin", "analyst"})
    assert context.permissions == frozenset({"tenant:read"})
    assert context.iss == "gateway-test"
    assert context.aud == "internal-test"
    assert context.exp == 1_700_000_120
    assert context.kid == "gateway-k1"


def test_resolved_auth_context_signs_as_eddsa_internal_envelope() -> None:
    directory = AuthDirectory()
    directory.upsert_user(
        id="fabric-user-1",
        clerk_user_id="clerk-user-1",
        email="alice@example.com",
        display_name="Alice",
        status="active",
    )
    directory.upsert_tenant(
        id="fabric-tenant-1",
        clerk_org_id="org-1",
        name="Acme",
        slug="acme",
        status="active",
    )
    directory.upsert_membership(
        clerk_org_id="org-1",
        clerk_user_id="clerk-user-1",
        clerk_membership_id="mem-1",
        role="org:admin",
        status="active",
    )
    envelope_settings = _ed25519_envelope_settings()
    now = int(time.time())

    context = build_auth_context(
        claims=ClerkClaims(
            sub="clerk-user-1",
            org_id="org-1",
            org_role="org:member",
            org_permissions=("tenant:read", "agent:run"),
            azp="https://app.example.com",
            raw={"tenant_id": "attacker-controlled-body-value"},
        ),
        directory=directory,
        envelope_settings=envelope_settings,
        request_id="req-gateway",
        now=now,
    )
    token = sign_envelope(context, signing_key=envelope_settings.signing_key)
    verified = verify_envelope(
        token,
        key_set=envelope_settings.verification_keys,
        expected_issuer="gateway-test",
        expected_audience="internal-test",
    )

    assert ALGORITHM == "EdDSA"
    assert verified.kid == "gateway-k1"
    assert verified.tenant_id == "fabric-tenant-1"
    assert verified.user_id == "fabric-user-1"
    assert verified.clerk_org_id == "org-1"
    assert verified.exp == now + envelope_settings.envelope_ttl_seconds
    assert verified.permissions == frozenset({"tenant:read", "agent:run"})
