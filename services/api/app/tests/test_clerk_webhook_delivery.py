"""Step 4 tests: webhook delivery semantics (idempotency, replay, ordering).

Covers the delivery-state owner (``app.core.clerk_webhook_delivery``) and its
effect through the HTTP router:
- A correctly signed duplicate event id never creates duplicate rows.
- Dedup is by event id, not by body.
- Out-of-order membership events are retained as pending and recover once the
  user/org dependency arrives.
- A pending event that exhausts its lifecycle bounds is terminal, dead-lettered
  exactly once, and re-delivery does not re-transition.
- Rate limiting (429) is transient: it does not drop, apply, or dead-letter the
  event, so legitimate Clerk retries are not lost.
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
from fastapi import FastAPI
from fastapi.testclient import TestClient

SECRET = "whsec_" + base64.b64encode(b"phase1-test-secret").decode()


@pytest.fixture
def clerk_env(monkeypatch) -> Iterator[None]:
    """Minimal Clerk + a very high webhook rate limit for delivery tests."""
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
    # Fresh router (rebuilt rate-limit dependency) + fresh app per test.
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


def _post(
    client: TestClient,
    payload: dict,
    *,
    svix_id: str,
    secret: str = SECRET,
    svix_timestamp: str | None = None,
):
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


def _user_payload(clerk_id: str, email: str) -> dict:
    return {
        "type": "user.created",
        "data": {
            "id": clerk_id,
            "primary_email_address_id": f"ema_{clerk_id}",
            "email_addresses": [{"id": f"ema_{clerk_id}", "email_address": email}],
            "first_name": "A",
            "last_name": "B",
        },
    }


def _org_payload(clerk_id: str, name: str = "Acme") -> dict:
    return {"type": "organization.created", "data": {"id": clerk_id, "name": name, "slug": name.lower()}}


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


def test_duplicate_event_id_does_not_duplicate_rows(client):
    """Two deliveries of the same svix-id create exactly one user row."""
    payload = _user_payload("user_dup", "dup@example.com")
    assert _post(client, payload, svix_id="msg_dup").status_code == 204
    assert _post(client, payload, svix_id="msg_dup").status_code == 204

    from app.core.auth_directory import get_auth_directory

    directory = get_auth_directory()
    user = directory.get_user_by_clerk("user_dup")
    assert user is not None
    assert user.email == "dup@example.com"


def test_dedup_is_by_event_id_not_body(client):
    """A different body under the same event id is still a no-op (dedup by id)."""
    first = _user_payload("user_diff_b1", "b1@example.com")
    tweaked = {
        "type": "user.created",
        "data": {
            "id": "user_diff_b2",
            "primary_email_address_id": "ema_x",
            "email_addresses": [{"id": "ema_x", "email_address": "b2@example.com"}],
        },
    }
    assert _post(client, first, svix_id="msg_same_id").status_code == 204
    # Same svix-id but different body/row -> deduped as processed.
    assert _post(client, tweaked, svix_id="msg_same_id").status_code == 204

    from app.core.auth_directory import get_auth_directory

    directory = get_auth_directory()
    assert directory.get_user_by_clerk("user_diff_b1") is not None
    assert directory.get_user_by_clerk("user_diff_b2") is None


def test_out_of_order_membership_recovers_after_dependency_arrives(client):
    """Membership before its user/org is pending+409, then recovers via redelivery."""
    mbr = _membership_payload("user_o2o", "org_o2o")
    pending_resp = _post(client, mbr, svix_id="msg_mbr_o2o")
    assert pending_resp.status_code == 409

    from app.core.clerk_webhook_delivery import get_webhook_delivery_tracker

    tracker = get_webhook_delivery_tracker()
    assert tracker.is_pending("msg_mbr_o2o")
    assert not tracker.is_processed("msg_mbr_o2o")

    # User + org arrive.
    assert _post(client, _user_payload("user_o2o", "o2o@example.com"), svix_id="msg_user_o2o").status_code == 204
    assert _post(client, _org_payload("org_o2o"), svix_id="msg_org_o2o").status_code == 204

    # Same membership event redelivered (Clerk retry): now applies.
    assert _post(client, mbr, svix_id="msg_mbr_o2o").status_code == 204

    from app.core.auth_directory import get_auth_directory

    membership = get_auth_directory().get_active_membership(
        clerk_org_id="org_o2o", clerk_user_id="user_o2o"
    )
    assert membership is not None and membership.role == "org:admin"
    assert not tracker.is_pending("msg_mbr_o2o")
    assert tracker.is_processed("msg_mbr_o2o")


def test_membership_role_change_is_an_update_not_a_duplicate(client):
    """Upsert-style membership events do not create duplicate rows."""
    assert _post(client, _user_payload("user_role", "role@example.com"), svix_id="msg_u_role").status_code == 204
    assert _post(client, _org_payload("org_role"), svix_id="msg_o_role").status_code == 204
    assert _post(client, _membership_payload("user_role", "org_role", role="org:admin"), svix_id="msg_m1").status_code == 204
    assert _post(client, _membership_payload("user_role", "org_role", role="org:member"), svix_id="msg_m2").status_code == 204

    from app.core.auth_directory import get_auth_directory

    directory = get_auth_directory()
    membership = directory.get_active_membership(clerk_org_id="org_role", clerk_user_id="user_role")
    assert membership is not None and membership.role == "org:member"
    # Exactly one membership row keyed by (org, user).
    assert len([m for m in directory._memberships.values() if m.clerk_org_id == "org_role"]) == 1


def test_pending_event_exhausting_attempts_is_dead_lettered_once(client, monkeypatch):
    """A pending event that outlives its attempt bound becomes terminal once."""
    monkeypatch.setattr("app.core.clerk_webhook_delivery.MAX_PENDING_ATTEMPTS", 2)

    from app.core import clerk_webhook_delivery, webhook_dlq

    clerk_webhook_delivery.reset_webhook_delivery_tracker()
    webhook_dlq.reset_webhook_dlq()

    mbr = _membership_payload("user_ex", "org_ex")

    # 1st and 2nd deliveries: pending, retryable (non-2xx).
    assert _post(client, mbr, svix_id="msg_ex").status_code == 409
    assert _post(client, mbr, svix_id="msg_ex").status_code == 409
    dlq = webhook_dlq.get_webhook_dlq()
    assert dlq.list_records(unresolved_only=False) == []

    # 3rd delivery: exceeds MAX_PENDING_ATTEMPTS -> terminal, DLQ once.
    assert _post(client, mbr, svix_id="msg_ex").status_code == 409
    dead = [r for r in dlq.list_records(unresolved_only=False) if r.error_reason == "pending_exhausted"]
    assert len(dead) == 1

    tracker = clerk_webhook_delivery.get_webhook_delivery_tracker()
    assert tracker.snapshot()["dead_pending"] == 1

    # A further redelivery does not re-transition / re-enqueue.
    assert _post(client, mbr, svix_id="msg_ex").status_code == 409
    dead_again = [r for r in dlq.list_records(unresolved_only=False) if r.error_reason == "pending_exhausted"]
    assert len(dead_again) == 1
    assert tracker.snapshot()["dead_pending"] == 1


def test_pending_event_exhausting_age_is_terminal():
    """Age-based exhaustion (independent of attempts) reaches the dead state."""
    from app.core.clerk_webhook_delivery import (
        MAX_PENDING_AGE_SECONDS,
        WebhookDeliveryTracker,
    )

    tracker = WebhookDeliveryTracker()
    now = 1_000_000.0
    first = tracker.register_pending("msg_age", "organizationMembership.created", now=now)
    assert first.retryable and not first.transitioned_to_dead

    # Advance clock beyond max age on the next delivery.
    outcome = tracker.register_pending(
        "msg_age", "organizationMembership.created", now=now + MAX_PENDING_AGE_SECONDS + 1
    )
    assert outcome.retryable is False
    assert outcome.transitioned_to_dead is True

    # Re-transition is suppressed once terminal.
    repeat = tracker.register_pending(
        "msg_age", "organizationMembership.created", now=now + MAX_PENDING_AGE_SECONDS + 2
    )
    assert repeat.retryable is False and repeat.transitioned_to_dead is False
    assert tracker.snapshot()["dead_pending"] == 1


def test_rate_limit_429_is_transient_and_does_not_drop_or_apply(monkeypatch):
    """A rate-limit 429 must not drop, apply, or dead-letter the event."""
    monkeypatch.setenv("CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE", "1")
    monkeypatch.setenv("AUTH_PROVIDER", "legacy")
    monkeypatch.setenv("CLERK_ISSUER", "https://example.clerk.accounts.dev")
    monkeypatch.setenv("CLERK_JWT_AUDIENCE", "fabric4l-api")
    monkeypatch.setenv("CLERK_AUTHORIZED_PARTIES", "http://localhost:3001")
    monkeypatch.setenv("CLERK_WEBHOOK_SIGNING_SECRET", SECRET)

    from app.core import auth_directory, clerk_config, clerk_webhook_delivery, webhook_dlq

    clerk_config.reset_auth_settings_cache()
    auth_directory.reset_auth_directory()
    clerk_webhook_delivery.reset_webhook_delivery_tracker()
    webhook_dlq.reset_webhook_dlq()

    # Build a standalone app from a freshly reloaded router (low rate limit).
    from app.routers import clerk_webhooks as router_mod

    importlib.reload(router_mod)
    standalone = FastAPI()
    standalone.include_router(router_mod.router)
    client = TestClient(standalone)

    # First delivery consumes the single allowed token -> 204 applied.
    assert _post(client, _user_payload("user_rt_a", "a@example.com"), svix_id="msg_rt_a").status_code == 204
    # Second delivery (different event) within the same minute -> 429 transient.
    assert _post(client, _user_payload("user_rt_b", "b@example.com"), svix_id="msg_rt_b").status_code == 429

    directory = auth_directory.get_auth_directory()
    tracker = clerk_webhook_delivery.get_webhook_delivery_tracker()
    dlq = webhook_dlq.get_webhook_dlq()

    # The rate-limited event was not applied, not committed as processed, and
    # not dropped into the DLQ — it will simply be retried by the sender.
    assert directory.get_user_by_clerk("user_rt_a") is not None
    assert directory.get_user_by_clerk("user_rt_b") is None
    assert tracker.is_processed("msg_rt_b") is False
    assert dlq.list_records(unresolved_only=False) == []


def test_pending_snapshot_reflects_delivery_state():
    """snapshot() gives operators visibility into processed/pending/dead counts."""
    from app.core.clerk_webhook_delivery import WebhookDeliveryTracker

    tracker = WebhookDeliveryTracker()
    tracker.mark_processed("msg_done", "user.created")
    tracker.register_pending("msg_wait", "organizationMembership.created")

    snap = tracker.snapshot()
    assert snap["processed"] == 1
    assert snap["pending"] == 1
    assert snap["dead_pending"] == 0
