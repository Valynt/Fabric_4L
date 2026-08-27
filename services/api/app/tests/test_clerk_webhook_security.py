"""Transport-security tests for the Clerk webhook endpoint (Step 3).

These tests prove the security boundary in ``app.core.clerk_webhook_signing``
in isolation from delivery semantics (dedup/idempotency/ordering are covered
separately in ``test_clerk_webhook_idempotency.py``). A bad or missing
signature must be rejected with 401 **before** any parsing or provisioning
runs; an oversized body must be rejected with 413.

Negative cases required by the locked acceptance criteria:
- altered raw body is rejected (401)
- missing/invalid Svix headers are rejected (401)
- stale timestamp is rejected (401)
- oversized body is rejected (413)
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

from app.core.clerk_webhook_signing import MAX_WEBHOOK_BODY_BYTES, SKEW_TOLERANCE_SECONDS


@pytest.fixture
def clerk_env(monkeypatch) -> Iterator[None]:
    """Configure minimal Clerk + envelope settings for the gateway."""
    monkeypatch.setenv("AUTH_PROVIDER", "legacy")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "fabric4l-api")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "http://localhost:3001")
    monkeypatch.setenv("CLERK_WEBHOOK_SIGNING_SECRET", "whsec_" + base64.b64encode(b"phase1-test-secret").decode())

    from app.core import clerk_config
    clerk_config.reset_auth_settings_cache()

    from app.core import auth_directory
    auth_directory.reset_auth_directory()

    yield

    clerk_config.reset_auth_settings_cache()
    auth_directory.reset_auth_directory()


@pytest.fixture
def client(clerk_env) -> TestClient:
    from app import main as app_main
    importlib.reload(app_main)
    return TestClient(app_main.app)


SECRET = "whsec_" + base64.b64encode(b"phase1-test-secret").decode()


def _sign(body: bytes, *, svix_id: str, svix_timestamp: str, secret: str) -> str:
    key = base64.b64decode(secret[len("whsec_"):])
    signed = f"{svix_id}.{svix_timestamp}.".encode() + body
    digest = hmac.new(key, signed, hashlib.sha256).digest()
    return "v1," + base64.b64encode(digest).decode()


def _post(client: TestClient, body: bytes, *, svix_id: str, svix_timestamp: str, svix_signature: str):
    return client.post(
        "/internal/webhooks/clerk",
        content=body,
        headers={
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
            "content-type": "application/json",
        },
    )


def test_altered_raw_body_rejected(client):
    """Signature is bound to the original raw body; a tampered body fails with 401."""
    original = json.dumps({"type": "user.created", "data": {"id": "user_orig"}}).encode("utf-8")
    forged = json.dumps({"type": "user.created", "data": {"id": "user_forged"}}).encode("utf-8")
    ts = str(int(time.time()))
    sig = _sign(original, svix_id="msg_alter", svix_timestamp=ts, secret=SECRET)

    response = _post(client, forged, svix_id="msg_alter", svix_timestamp=ts, svix_signature=sig)

    assert response.status_code == 401


def test_missing_signature_headers_rejected(client):
    response = client.post(
        "/internal/webhooks/clerk",
        content=b"{}",
        headers={"content-type": "application/json"},
    )
    assert response.status_code == 401


def test_invalid_signature_rejected(client):
    body = json.dumps({"type": "user.created", "data": {"id": "user_1"}}).encode()
    response = _post(
        client,
        body,
        svix_id="msg_inv",
        svix_timestamp=str(int(time.time())),
        svix_signature="v1,not-the-right-signature",
    )
    assert response.status_code == 401


def test_non_v1_signature_rejected(client):
    body = json.dumps({"type": "user.created", "data": {"id": "user_1"}}).encode()
    ts = str(int(time.time()))
    response = _post(client, body, svix_id="msg_nov1", svix_timestamp=ts, svix_signature="v2,abc")
    assert response.status_code == 401


def test_stale_timestamp_rejected(client):
    """A captured signature replayed outside the skew window -> 401."""
    body = json.dumps({"type": "user.created", "data": {"id": "user_1"}}).encode()
    old_ts = str(int(time.time()) - SKEW_TOLERANCE_SECONDS - 1)
    sig = _sign(body, svix_id="msg_stale", svix_timestamp=old_ts, secret=SECRET)

    response = _post(client, body, svix_id="msg_stale", svix_timestamp=old_ts, svix_signature=sig)

    assert response.status_code == 401


def test_oversized_body_rejected_413(client):
    """A body above MAX_WEBHOOK_BODY_BYTES is rejected before verification."""
    big = b"x" * (MAX_WEBHOOK_BODY_BYTES + 1)
    response = _post(
        client,
        big,
        svix_id="msg_big",
        svix_timestamp=str(int(time.time())),
        svix_signature="v1,ignored",
    )
    assert response.status_code == 413
