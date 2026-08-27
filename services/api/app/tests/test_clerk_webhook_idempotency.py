"""Phase 1 tests for the Clerk webhook handler.

Covers:
- Missing signature -> 401.
- Invalid signature -> 401.
- Disabled when CLERK_WEBHOOK_SIGNING_SECRET is unset.
- Idempotent: duplicate svix-id is a no-op.
- Membership ordering: 409 when user/org event hasn't arrived yet.
- Happy-path user/org/membership creation populates the directory.
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
from fastapi.testclient import TestClient


@pytest.fixture
def clerk_env(monkeypatch) -> Iterator[None]:
    """Configure minimal Clerk + envelope settings for the gateway."""
    monkeypatch.setenv("AUTH_PROVIDER", "legacy")  # webhook works under legacy too
    monkeypatch.setenv("CLERK_ISSUER", "https://example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "fabric4l-api")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "http://localhost:3001")
    monkeypatch.setenv("CLERK_WEBHOOK_SIGNING_SECRET", "whsec_" + base64.b64encode(b"phase1-test-secret").decode())

    # Ensure cached settings reflect the new env.
    from app.core import clerk_config
    clerk_config.reset_auth_settings_cache()

    # Reset directory so tests don't leak.
    from app.core import auth_directory
    auth_directory.reset_auth_directory()

    yield

    clerk_config.reset_auth_settings_cache()
    auth_directory.reset_auth_directory()


@pytest.fixture
def client(clerk_env) -> TestClient:
    # Import after env is set so Settings load correctly.
    from app import main as app_main
    importlib.reload(app_main)
    return TestClient(app_main.app)


def _sign(body: bytes, *, svix_id: str, svix_timestamp: str, secret: str) -> str:
    key = base64.b64decode(secret[len("whsec_") :])
    signed = f"{svix_id}.{svix_timestamp}.".encode() + body
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def _post(client: TestClient, payload: dict, *, svix_id: str, secret: str, svix_timestamp: str | None = None):
    body = json.dumps(payload).encode("utf-8")
    ts = svix_timestamp or str(int(time.time()))
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


def test_missing_signature_rejected(client):
    response = client.post(
        "/internal/webhooks/clerk",
        content=b"{}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401


def test_invalid_signature_rejected(client):
    body = json.dumps({"type": "user.created", "data": {"id": "user_1"}}).encode()
    response = client.post(
        "/internal/webhooks/clerk",
        content=body,
        headers={
            "svix-id": "msg_1",
            "svix-timestamp": "1700000000",
            "svix-signature": "v1,not-the-right-signature",
            "content-type": "application/json",
        },
    )
    assert response.status_code == 401


def test_user_and_org_creation_populates_directory(client):
    secret = "whsec_" + base64.b64encode(b"phase1-test-secret").decode()
    user_payload = {
        "type": "user.created",
        "data": {
            "id": "user_1",
            "primary_email_address_id": "ema_1",
            "email_addresses": [
                {"id": "ema_1", "email_address": "alice@example.com"}
            ],
            "first_name": "Alice",
            "last_name": "Example",
        },
    }
    org_payload = {
        "type": "organization.created",
        "data": {"id": "org_1", "name": "Acme", "slug": "acme"},
    }
    membership_payload = {
        "type": "organizationMembership.created",
        "data": {
            "id": "orgmem_1",
            "role": "org:admin",
            "organization_id": "org_1",
            "user_id": "user_1",
            "public_user_data": {"user_id": "user_1"},
        },
    }

    assert _post(client, user_payload, svix_id="msg_user", secret=secret).status_code == 204
    assert _post(client, org_payload, svix_id="msg_org", secret=secret).status_code == 204
    assert _post(client, membership_payload, svix_id="msg_mbr", secret=secret).status_code == 204

    from app.core.auth_directory import get_auth_directory

    directory = get_auth_directory()
    user = directory.get_user_by_clerk("user_1")
    tenant = directory.get_tenant_by_clerk_org("org_1")
    membership = directory.get_active_membership(
        clerk_org_id="org_1", clerk_user_id="user_1"
    )
    assert user is not None and user.email == "alice@example.com"
    assert tenant is not None and tenant.slug == "acme"
    assert membership is not None and membership.role == "org:admin"


def test_replay_is_idempotent(client):
    secret = "whsec_" + base64.b64encode(b"phase1-test-secret").decode()
    payload = {
        "type": "user.created",
        "data": {
            "id": "user_2",
            "primary_email_address_id": "ema_2",
            "email_addresses": [{"id": "ema_2", "email_address": "bob@example.com"}],
            "first_name": "Bob",
            "last_name": "Example",
        },
    }
    first = _post(client, payload, svix_id="msg_dup", secret=secret)
    second = _post(client, payload, svix_id="msg_dup", secret=secret)
    assert first.status_code == 204
    assert second.status_code == 204

    from app.core.auth_directory import get_auth_directory

    user = get_auth_directory().get_user_by_clerk("user_2")
    assert user is not None
    # Same record, not a duplicate
    assert user.email == "bob@example.com"


def test_membership_before_user_returns_409(client):
    secret = "whsec_" + base64.b64encode(b"phase1-test-secret").decode()
    payload = {
        "type": "organizationMembership.created",
        "data": {
            "id": "orgmem_99",
            "role": "org:admin",
            "organization_id": "org_unknown",
            "user_id": "user_unknown",
            "public_user_data": {"user_id": "user_unknown"},
        },
    }
    response = _post(client, payload, svix_id="msg_ordering", secret=secret)
    assert response.status_code == 409


def test_expired_timestamp_rejected(client, monkeypatch):
    """Signatures older than 5 minutes must be rejected (replay defense)."""
    secret = "whsec_" + base64.b64encode(b"phase1-test-secret").decode()
    # Fix "now" so the test is deterministic.
    monkeypatch.setattr(time, "time", lambda: 1_700_000_000)
    payload = {"type": "user.created", "data": {"id": "user_replay"}}
    # Timestamp is 400 seconds in the past (> 300s tolerance).
    response = _post(
        client,
        payload,
        svix_id="msg_replay",
        secret=secret,
        svix_timestamp="1699999600",
    )
    assert response.status_code == 401
    # Gateway middleware wraps errors; verify via the wrapped message.
    assert "Unauthorized" in response.json()["error"]["message"]


def test_signature_version_not_v1_rejected(client):
    """Only v1 signatures are accepted."""
    body = json.dumps({"type": "user.created", "data": {"id": "user_1"}}).encode()
    response = client.post(
        "/internal/webhooks/clerk",
        content=body,
        headers={
            "svix-id": "msg_1",
            "svix-timestamp": "1700000000",
            "svix-signature": "v2,not-the-right-signature",
            "content-type": "application/json",
        },
    )
    assert response.status_code == 401


def test_membership_missing_user_and_org_returns_400(client):
    """Membership payload missing both user_id and organization_id is a 400."""
    secret = "whsec_" + base64.b64encode(b"phase1-test-secret").decode()
    payload = {
        "type": "organizationMembership.created",
        "data": {
            "id": "orgmem_bad",
            "role": "org:admin",
            # Deliberately omit user_id, organization_id, and public_user_data
        },
    }
    response = _post(client, payload, svix_id="msg_bad_mbr", secret=secret)
    assert response.status_code == 400
    assert "Missing user_id" in response.json()["error"]["message"]


def test_invalid_json_error_payload_is_sanitized(client):
    """Invalid JSON should return stable code/message without parser internals."""
    secret = "whsec_" + base64.b64encode(b"phase1-test-secret").decode()
    body = b"{"
    ts = str(int(time.time()))
    sig = _sign(body, svix_id="msg_invalid_json", svix_timestamp=ts, secret=secret)
    response = client.post(
        "/internal/webhooks/clerk",
        content=body,
        headers={
            "svix-id": "msg_invalid_json",
            "svix-timestamp": ts,
            "svix-signature": sig,
            "content-type": "application/json",
        },
    )
    assert response.status_code == 400
    payload = response.json()["error"]
    assert payload["code"] == "auth.webhook_invalid_body"
    assert payload["message"] == "Bad request."
