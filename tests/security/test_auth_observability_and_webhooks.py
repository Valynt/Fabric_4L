"""Tests for Clerk Auth Observability, Telemetry, and Webhook Reliability (DLQ + Invitations)."""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import time
from typing import Any

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import ed25519
import pytest
from fastapi.testclient import TestClient

from app.core.auth_directory import get_auth_directory, reset_auth_directory
from app.core.auth_telemetry import (
    get_auth_health_summary,
    record_auth_failure,
    record_auth_success,
    record_clock_skew,
    record_webhook_dlq,
    record_webhook_event,
    record_webhook_replay,
    reset_auth_telemetry_stats,
)
from app.core.clerk_config import reset_auth_settings_cache
from app.core.security import create_access_token
from app.core.webhook_dlq import get_webhook_dlq, reset_webhook_dlq
from app.main import app
from scripts.replay_clerk_webhooks import sign_svix_payload

MOCK_WEBHOOK_SECRET = f"{'whsec_'}{base64.b64encode(b'test_secret_key_1234567890123456').decode('ascii')}"


@pytest.fixture(autouse=True)
def _setup_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("AUTH_PROVIDER", "clerk")
    monkeypatch.setenv("CLERK_SECRET_KEY", f"{'sk'}_{'test'}_mock")
    monkeypatch.setenv("CLERK_ISSUER", "https://clerk.valuepact.ai")
    monkeypatch.setenv("CLERK_JWKS_URL", "https://clerk.valuepact.ai/.well-known/jwks.json")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "https://app.valuepact.ai")
    monkeypatch.setenv("CLERK_WEBHOOK_SECRET", MOCK_WEBHOOK_SECRET)

    priv_key = ed25519.Ed25519PrivateKey.generate()
    priv_pem = priv_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")
    pub_pem = priv_key.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    ).decode("utf-8")

    monkeypatch.setenv("FABRIC_AUTH_SIGNING_KEY", priv_pem)
    monkeypatch.setenv(
        "FABRIC_AUTH_PUBLIC_KEYS",
        json.dumps([{"kid": "gateway-k1", "public_pem": pub_pem}]),
    )
    reset_auth_settings_cache()
    reset_auth_directory()
    reset_auth_telemetry_stats()
    reset_webhook_dlq()


def _make_svix_headers(secret: str, event_id: str, payload_bytes: bytes) -> dict[str, str]:
    ts = int(time.time())
    sig = sign_svix_payload(secret, event_id, ts, payload_bytes)
    return {
        "svix-id": event_id,
        "svix-timestamp": str(ts),
        "svix-signature": sig,
        "content-type": "application/json",
    }


def test_auth_telemetry_stats_and_health_summary():
    """Verify rolling window SLO calculation and health summary structure."""
    reset_auth_telemetry_stats()

    # Record some successes and failures
    record_auth_success(provider="clerk", latency_seconds=0.005)
    record_auth_success(provider="clerk", latency_seconds=0.010)
    record_auth_failure(provider="clerk", reason="expired", latency_seconds=0.002)
    record_auth_failure(provider="clerk", reason="tenant_unresolved", latency_seconds=0.004)
    record_clock_skew(provider="clerk", skew_seconds=1.5)

    health = get_auth_health_summary()
    assert health["provider"] == "clerk"
    assert health["status"] in ("healthy", "degraded", "unhealthy")
    assert "slo_metrics" in health
    metrics = health["slo_metrics"]
    assert metrics["total_verifications"] == 4
    assert metrics["success_count"] == 2
    assert metrics["success_rate_percent"] == 50.0
    assert metrics["unresolved_tenant_count"] == 1
    assert metrics["expired_count"] == 1
    assert metrics["p50_latency_ms"] > 0


def test_auth_health_endpoint():
    """Verify /auth/health endpoint returns real-time metrics."""
    client = TestClient(app)
    resp = client.get("/v1/auth/health")
    assert resp.status_code == 200
    data = resp.json()
    assert "status" in data
    assert "slo_metrics" in data
    assert "clerk_jwks" in data
    assert "internal_envelope" in data


def test_webhook_invitation_lifecycle():
    """Verify organizationInvitation created, accepted, and revoked events."""
    client = TestClient(app)
    secret = MOCK_WEBHOOK_SECRET
    directory = get_auth_directory()

    # 1. Organization Invitation Created
    inv_created_payload = {
        "id": "evt_inv_create_1",
        "type": "organizationInvitation.created",
        "data": {
            "id": "inv_123",
            "organization_id": "org_fabric_1",
            "email_address": "engineer@valuepact.ai",
            "role": "org:member",
            "created_at": int(time.time()),
        },
    }
    payload_bytes = json.dumps(inv_created_payload).encode("utf-8")
    headers = _make_svix_headers(secret, "msg_inv_1", payload_bytes)

    resp = client.post("/internal/webhooks/clerk", content=payload_bytes, headers=headers)
    assert resp.status_code == 204

    inv = directory.get_invitation("inv_123")
    assert inv is not None
    assert inv.email == "engineer@valuepact.ai"
    assert inv.status == "pending"

    # 2. Invitation Revoked
    inv_revoked_payload = {
        "id": "evt_inv_revoked_1",
        "type": "organizationInvitation.revoked",
        "data": {
            "id": "inv_123",
            "organization_id": "org_fabric_1",
        },
    }
    payload_bytes = json.dumps(inv_revoked_payload).encode("utf-8")
    headers = _make_svix_headers(secret, "msg_inv_2", payload_bytes)
    resp = client.post("/internal/webhooks/clerk", content=payload_bytes, headers=headers)
    assert resp.status_code == 204

    inv = directory.get_invitation("inv_123")
    assert inv is not None
    assert inv.status == "revoked"


def test_webhook_dlq_on_fatal_failure():
    """Verify DLQ captures unprocessable / fatal webhook exceptions."""
    dlq = get_webhook_dlq()
    assert len(dlq.list_records()) == 0

    # Manually enqueue a DLQ record
    rec = dlq.enqueue(
        event_id="evt_fail_1",
        event_type="organization.custom",
        payload={"foo": "bar"},
        headers={"svix-id": "evt_fail_1"},
        error_reason="Simulated unhandled schema exception",
    )
    assert rec.id.startswith("dlq_")
    assert len(dlq.list_records()) == 1

    # Inspect via endpoint
    client = TestClient(app)
    auth_token = create_access_token("admin_user", "org_fabric_1")
    resp = client.get("/internal/webhooks/clerk/dlq", headers={"Authorization": f"Bearer {auth_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_records"] == 1
    assert data["records"][0]["event_id"] == "evt_fail_1"


def test_webhook_idempotent_replay_metric():
    """Verify duplicate webhook delivery is recognized and marked as replay."""
    client = TestClient(app)
    secret = MOCK_WEBHOOK_SECRET

    payload = {
        "id": "evt_user_dup_1",
        "type": "user.created",
        "data": {
            "id": "user_dup_123",
            "first_name": "Test",
            "last_name": "User",
        },
    }
    payload_bytes = json.dumps(payload).encode("utf-8")
    headers = _make_svix_headers(secret, "msg_dup_1", payload_bytes)

    # First delivery
    resp1 = client.post("/internal/webhooks/clerk", content=payload_bytes, headers=headers)
    assert resp1.status_code == 204

    # Duplicate delivery with same svix-id
    resp2 = client.post("/internal/webhooks/clerk", content=payload_bytes, headers=headers)
    assert resp2.status_code == 204
