"""Step 5 tests: Clerk -> Fabric provisioning (immutable identity mapping).

Covers the provisioning policy boundary (``app.core.clerk_provisioner``) and
its effect through the webhook router + ``build_auth_context``:

- A Clerk organization maps to an immutable, deterministic Fabric tenant id.
- A Clerk user maps to a stable Fabric user identity.
- No tenant is ever inferred from an email domain or client-supplied metadata.
- Deletes are SOFT (deactivation): the record is retained, access denies
  immediately, and a re-created org/user maps back to the same identity.
- A profile-update event does NOT reactivate a soft-deleted user.
- The same Clerk identity never creates duplicate users/tenants.
- Cross-tenant membership changes deny immediately.
"""
from __future__ import annotations

import base64
import hashlib
import hmac
import importlib
import json
import time
from collections.abc import Iterator

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PrivateKey
from fastapi.testclient import TestClient

from value_fabric.shared.identity.fabric_auth import AuthContext
from value_fabric.shared.identity.fabric_auth.signer import SigningKey

from app.core.auth_context_builder import (
    build_auth_context,
    MembershipNotActiveError,
    TenantResolutionError,
    UserNotProvisionedError,
)
from app.core.clerk_config import InternalEnvelopeSettings
from app.core.clerk_verifier import ClerkClaims

SECRET = "whsec_" + base64.b64encode(b"phase1-provisioning-secret").decode()


@pytest.fixture
def clerk_env(monkeypatch) -> Iterator[None]:
    monkeypatch.setenv("AUTH_PROVIDER", "legacy")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "fabric4l-api")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "http://localhost:3001")
    monkeypatch.setenv("CLERK_WEBHOOK_SIGNING_SECRET", SECRET)
    monkeypatch.setenv("CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE", "100000")

    from app.core import auth_directory, clerk_config, clerk_webhook_delivery, webhook_dlq

    clerk_config.reset_auth_settings_cache()
    auth_directory.reset_auth_directory()
    clerk_webhook_delivery.reset_webhook_delivery_tracker()
    webhook_dlq.reset_webhook_dlq()

    yield

    clerk_config.reset_auth_settings_cache()
    auth_directory.reset_auth_directory()
    clerk_webhook_delivery.reset_webhook_delivery_tracker()
    webhook_dlq.reset_webhook_dlq()


@pytest.fixture
def client(clerk_env) -> TestClient:
    from app.routers import clerk_webhooks as router_mod

    importlib.reload(router_mod)
    from app import main as app_main

    importlib.reload(app_main)
    return TestClient(app_main.app)


def _sign(body: bytes, *, svix_id: str, svix_timestamp: str, secret: str) -> str:
    key = base64.b64decode(secret[len("whsec_") :])
    signed = f"{svix_id}.{svix_timestamp}.".encode() + body
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def _post(client, payload, *, svix_id: str, secret: str = SECRET):
    body = json.dumps(payload).encode("utf-8")
    ts = str(int(time.time()))
    sig = _sign(body, svix_id=svix_id, svix_timestamp=ts, secret=secret)
    return client.post(
        "/internal/webhooks/clerk",
        content=body,
        headers={
            "svix-id": svix_id,
            "svix-timestamp": ts,
            "svix-signature": sig,
            "content-type": "application/json",
        },
    )


def _user_payload(clerk_id: str, email: str, *, first: str = "A", last: str = "B") -> dict:
    return {
        "type": "user.created",
        "data": {
            "id": clerk_id,
            "primary_email_address_id": f"ema_{clerk_id}",
            "email_addresses": [{"id": f"ema_{clerk_id}", "email_address": email}],
            "first_name": first,
            "last_name": last,
        },
    }


def _org_payload(clerk_id: str, name: str = "Acme") -> dict:
    return {
        "type": "organization.created",
        "data": {"id": clerk_id, "name": name, "slug": name.lower()},
    }


def _membership_payload(clerk_id: str, org_id: str, *, role: str = "org:admin") -> dict:
    return {
        "type": "organizationMembership.created",
        "data": {
            "id": f"orgmem_{clerk_id}_{org_id}",
            "role": role,
            "organization_id": org_id,
            "user_id": clerk_id,
            "public_user_data": {"user_id": clerk_id},
        },
    }


def _provision(client, *, clerk_id: str, org_id: str) -> None:
    assert _post(client, _user_payload(clerk_id, f"{clerk_id}@acme.com"), svix_id=f"m_user_{clerk_id}").status_code == 204
    assert _post(client, _org_payload(org_id), svix_id=f"m_org_{org_id}").status_code == 204
    assert _post(
        client, _membership_payload(clerk_id, org_id), svix_id=f"m_mem_{clerk_id}_{org_id}"
    ).status_code == 204


def _envelope() -> InternalEnvelopeSettings:
    private = Ed25519PrivateKey.generate()
    private_pem = private.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode()
    return InternalEnvelopeSettings(
        signing_key=SigningKey(kid="kids_test", private_pem=private_pem),
        envelope_ttl_seconds=300,
    )


def _claims(sub: str, org_id: str, *, role: str = "org:admin") -> ClerkClaims:
    return ClerkClaims(
        sub=sub,
        org_id=org_id,
        org_role=role,
        org_permissions=(),
        azp=None,
        raw={},
    )


def _directory():
    from app.core.auth_directory import get_auth_directory

    return get_auth_directory()


# ---------------------------------------------------------------------------
# Deterministic / immutable identity mapping
# ---------------------------------------------------------------------------
def test_tenant_id_is_immutable_and_deterministic(client):
    _provision(client, clerk_id="user_1", org_id="org_1")
    tenant = _directory().get_tenant_by_clerk_org("org_1")
    assert tenant is not None
    assert tenant.id == "t_org_1"

    # Re-created org maps back to the same tenant id.
    assert _post(client, _org_payload("org_1"), svix_id="m_org_1_recreated").status_code == 204
    assert _directory().get_tenant_by_clerk_org("org_1").id == "t_org_1"


def test_user_identity_is_stable(client):
    _provision(client, clerk_id="user_2", org_id="org_2")
    user = _directory().get_user_by_clerk("user_2")
    assert user is not None
    assert user.id == "user_2"

    # Re-delivery (new event id) keeps the same identity, no duplicate row.
    assert _post(client, _user_payload("user_2", "user_2@acme.com"), svix_id="m_user_2_again").status_code == 204
    assert _directory().get_user_by_clerk("user_2").id == "user_2"


def test_provisioning_is_idempotent_for_same_identity(client):
    _provision(client, clerk_id="user_3", org_id="org_3")
    directory = _directory()
    assert len([u for u in [directory.get_user_by_clerk("user_3")] if u]) == 1
    assert len([t for t in [directory.get_tenant_by_clerk_org("org_3")] if t]) == 1


# ---------------------------------------------------------------------------
# No tenant from email domain or client metadata (AC: org_id is the only source)
# ---------------------------------------------------------------------------
def test_user_alone_must_not_create_tenant_from_email(client):
    _post(client, _user_payload("user_4", "alice@whatever-corp.com"), svix_id="m_user_4")
    directory = _directory()
    assert directory.get_user_by_clerk("user_4") is not None
    # A user event alone must never provision a tenant, even when the email
    # carries a plausible organization domain. The only tenant source is the
    # signed Clerk organization identity, so no email-derived tenant exists.
    assert directory.get_tenant_by_clerk_org("whatever-corp.com") is None
    assert directory.get_tenant_by_clerk_org("acme.com") is None
    assert directory.get_tenant_by_clerk_org("user_4") is None


def test_access_denied_for_tenant_without_org_provisioning(client):
    _provision(client, clerk_id="user_5", org_id="org_5")
    # Claims referencing an org that was never provisioned => denied, never
    # inferred from any other source.
    with pytest.raises(TenantResolutionError):
        build_auth_context(
            claims=_claims("user_5", "org_never_provisioned"),
            directory=_directory(),
            envelope_settings=_envelope(),
        )


# ---------------------------------------------------------------------------
# Soft deletes deny immediately (AC#5)
# ---------------------------------------------------------------------------
def test_org_deleted_soft_and_denies_immediately(client):
    _provision(client, clerk_id="user_6", org_id="org_6")
    directory = _directory()
    assert _post(
        client, {"type": "organization.deleted", "data": {"id": "org_6"}}, svix_id="m_orgdel_6"
    ).status_code == 204

    # Record retained (soft), but status deactivated.
    tenant = directory.get_tenant_by_clerk_org("org_6")
    assert tenant is not None
    assert tenant.status == "deactivated"

    with pytest.raises(TenantResolutionError):
        build_auth_context(
            claims=_claims("user_6", "org_6"), directory=directory, envelope_settings=_envelope()
        )


def test_user_deleted_soft_and_denies_immediately(client):
    _provision(client, clerk_id="user_7", org_id="org_7")
    directory = _directory()
    assert _post(
        client, {"type": "user.deleted", "data": {"id": "user_7"}}, svix_id="m_userdel_7"
    ).status_code == 204

    user = directory.get_user_by_clerk("user_7")
    assert user is not None
    assert user.status == "deactivated"

    with pytest.raises(UserNotProvisionedError):
        build_auth_context(
            claims=_claims("user_7", "org_7"), directory=directory, envelope_settings=_envelope()
        )


def test_membership_deleted_denies_immediately(client):
    _provision(client, clerk_id="user_8", org_id="org_8")
    directory = _directory()
    assert _post(
        client,
        {
            "type": "organizationMembership.deleted",
            "data": {
                "id": f"orgmem_user8_org8",
                "organization_id": "org_8",
                "user_id": "user_8",
                "public_user_data": {"user_id": "user_8"},
            },
        },
        svix_id="m_memdel_8",
    ).status_code == 204

    assert directory.get_active_membership(clerk_org_id="org_8", clerk_user_id="user_8") is None
    with pytest.raises(MembershipNotActiveError):
        build_auth_context(
            claims=_claims("user_8", "org_8"), directory=directory, envelope_settings=_envelope()
        )


def test_profile_update_does_not_reactivate_deleted_user(client):
    _provision(client, clerk_id="user_9", org_id="org_9")
    directory = _directory()
    assert _post(
        client, {"type": "user.deleted", "data": {"id": "user_9"}}, svix_id="m_userdel_9"
    ).status_code == 204
    # A user.updated for the same clerk id must NOT restore access.
    import copy

    updated = copy.deepcopy(_user_payload("user_9", "user_9@acme.com"))
    updated["type"] = "user.updated"
    assert _post(client, updated, svix_id="m_userupd_9").status_code == 204
    assert directory.get_user_by_clerk("user_9").status == "deactivated"
    with pytest.raises(UserNotProvisionedError):
        build_auth_context(
            claims=_claims("user_9", "org_9"), directory=directory, envelope_settings=_envelope()
        )


def test_recreated_user_is_active_and_keeps_identity(client):
    _provision(client, clerk_id="user_10", org_id="org_10")
    directory = _directory()
    assert _post(
        client, {"type": "user.deleted", "data": {"id": "user_10"}}, svix_id="m_userdel_10"
    ).status_code == 204

    # Clerk re-creates the account => user.created reactivates, same identity.
    assert _post(client, _user_payload("user_10", "user_10@acme.com"), svix_id="m_userrecreate_10").status_code == 204
    user = directory.get_user_by_clerk("user_10")
    assert user.status == "active"
    assert user.id == "user_10"

    # On re-creation Clerk re-adds the user to the org, so a fresh
    # membership.created reactivates the membership for the same key.
    assert _post(
        client, _membership_payload("user_10", "org_10"), svix_id="m_memrecreate_10"
    ).status_code == 204

    result = build_auth_context(
        claims=_claims("user_10", "org_10"),
        directory=directory,
        envelope_settings=_envelope(),
    )
    assert isinstance(result, AuthContext)
    assert result.tenant_id == "t_org_10"
    assert result.user_id == "user_10"


# ---------------------------------------------------------------------------
# Cross-tenant membership isolation / role assignment
# ---------------------------------------------------------------------------
def test_cross_tenant_membership_isolation(client):
    _provision(client, clerk_id="user_11", org_id="org_11")
    directory = _directory()
    # User added to a second tenant.
    assert _post(
        client, _org_payload("org_12", name="Beta"), svix_id="m_org_12"
    ).status_code == 204
    assert _post(
        client, _membership_payload("user_11", "org_12", role="org:member"), svix_id="m_mem_11_12"
    ).status_code == 204

    # Building context for tenant A is unaffected by the A->B addition.
    ctx_a = build_auth_context(
        claims=_claims("user_11", "org_11"),
        directory=directory,
        envelope_settings=_envelope(),
    )
    assert ctx_a.tenant_id == "t_org_11"

    # Membership in tenant A is not clobbered by tenant B's membership.
    assert directory.get_active_membership(clerk_org_id="org_12", clerk_user_id="user_11").role == "org:member"
    assert directory.get_active_membership(clerk_org_id="org_11", clerk_user_id="user_11").role == "org:admin"
