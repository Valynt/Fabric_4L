from __future__ import annotations

"""P0: Webhook Security Tests - executable behavioral verification.

Validates the real Stripe webhook verification and idempotency boundaries:

- ``verify_stripe_webhook_signature`` / ``parse_stripe_signature_header``
  (``layer7_billing.webhook_security``) for signature/HMAC + timestamp
  tolerance.
- ``IdempotencyService`` / ``InMemoryIdempotencyStore``
  (``value_fabric.shared.idempotency``) for replay rejection, duplicate
  delivery/idempotency, tenant-boundary enforcement, and retry safety.

Remediation (2026-08-27):
The previous version of this file skipped every security assertion. Each
skip has been converted to an executable test that exercises a real
verification or idempotency boundary with only external dependencies mocked.
Retained skips are limited to true live-stack behaviors (e.g. rate limiting
and secret-rotation rollover that require deployed infrastructure) and are
governed by the P0/security skip-governance ratchet in
``scripts/ci/check_p0_security_skip_governance.py``.
"""

import hashlib
import hmac
import time
from datetime import UTC, datetime, timedelta

import pytest
from layer7_billing.webhook_security import (
    parse_stripe_signature_header,
    verify_stripe_webhook_signature,
)
from value_fabric.shared.idempotency.core import (
    IdempotencyConflictError,
    IdempotencyRecord,
    IdempotencyRequest,
    IdempotencyService,
    build_request_fingerprint,
)
from value_fabric.shared.idempotency.store import InMemoryIdempotencyStore

pytestmark = [
    pytest.mark.security,
    pytest.mark.p0,
    pytest.mark.billing,
    pytest.mark.mandatory,
]

WEBHOOK_SECRET = "whsec_test_dummy_secret_1234567890"
OTHER_SECRET = "whsec_test_dummy_secret_other_9876543210"
PAYLOAD = b'{"id": "evt_123", "type": "payment.created", "data": {"amount": 1000}}'
CURRENT_TS = int(time.time())
STALE_TS = CURRENT_TS - 301
FUTURE_TS = CURRENT_TS + 301


def _make_signature(payload: bytes, secret: str, timestamp: int | None = None) -> str:
    signed_at = int(time.time()) if timestamp is None else timestamp
    signed_payload = f"{signed_at}.".encode() + payload
    digest = hmac.new(secret.encode("utf-8"), signed_payload, hashlib.sha256).hexdigest()
    return f"t={signed_at},v1={digest}"


def _verify(payload: bytes, signature: str | None, secret: str | None, **kwargs):
    """Verify with a pinned ``now`` so timing never makes these tests flaky."""
    kwargs.setdefault("now", CURRENT_TS)
    return verify_stripe_webhook_signature(payload, signature, secret, **kwargs)


def test_valid_signed_delivery_is_accepted() -> None:
    """A correctly signed, in-tolerance delivery verifies successfully."""
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS)
    parsed = _verify(PAYLOAD, sig, WEBHOOK_SECRET)
    assert parsed.timestamp == CURRENT_TS


def test_parse_stripe_signature_header_extracts_timestamp_and_signatures() -> None:
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS)
    parsed = parse_stripe_signature_header(sig)
    assert parsed.timestamp == CURRENT_TS
    assert len(parsed.signatures) == 1


def test_signature_tampering_rejected() -> None:
    """A payload signed once but delivered with a different body is rejected."""
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS)
    tampered = b'{"id": "evt_123", "type": "payment.created", "data": {"amount": 999999}}'
    with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
        _verify(tampered, sig, WEBHOOK_SECRET)


def test_signature_invalidated_by_timestamp_tampering() -> None:
    """Swapping the signed timestamp invalidates the HMAC."""
    signed_at = CURRENT_TS
    signed_payload = f"{signed_at}.".encode() + PAYLOAD
    digest = hmac.new(WEBHOOK_SECRET.encode(), signed_payload, hashlib.sha256).hexdigest()
    tampered_timestamp_sig = f"t={CURRENT_TS - 5},v1={digest}"

    with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
        _verify(PAYLOAD, tampered_timestamp_sig, WEBHOOK_SECRET)


def test_modified_signature_rejected() -> None:
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS)
    prefix, v1 = sig.rsplit("v1=", 1)
    modified = prefix + "v1=" + ("0" if v1[0] != "0" else "1") + v1[1:]
    with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
        _verify(PAYLOAD, modified, WEBHOOK_SECRET)


def test_missing_signature_rejected() -> None:
    with pytest.raises(ValueError, match="Missing Stripe-Signature header"):
        _verify(PAYLOAD, None, WEBHOOK_SECRET)


def test_malformed_signatures_rejected() -> None:
    for sig in ["invalid", "t=123", "v1=abc", "", "t=abc"]:
        with pytest.raises(ValueError):
            _verify(PAYLOAD, sig, WEBHOOK_SECRET)


def test_signature_version_validation() -> None:
    """v1 is accepted; unknown version alone (no v1) is rejected."""
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS)
    assert _verify(PAYLOAD, sig, WEBHOOK_SECRET) is not None

    with pytest.raises(ValueError, match="Missing Stripe v1 signature"):
        _verify(PAYLOAD, "t=123,v2=abc", WEBHOOK_SECRET)


def test_wrong_secret_rejected() -> None:
    wrong_sig = _make_signature(PAYLOAD, OTHER_SECRET, CURRENT_TS)
    with pytest.raises(ValueError, match="Invalid Stripe webhook signature"):
        _verify(PAYLOAD, wrong_sig, WEBHOOK_SECRET)


def test_unconfigured_secret_rejected() -> None:
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS)
    with pytest.raises(ValueError, match="secret is not configured"):
        _verify(PAYLOAD, sig, None)


def test_empty_secret_rejected() -> None:
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS)
    with pytest.raises(ValueError, match="secret is not configured"):
        _verify(PAYLOAD, sig, "   ")


def test_stale_timestamp_rejected() -> None:
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, STALE_TS)
    with pytest.raises(ValueError, match="outside tolerance"):
        _verify(
            PAYLOAD, sig, WEBHOOK_SECRET, tolerance_seconds=300, now=CURRENT_TS
        )


def test_future_timestamp_outside_tolerance_rejected() -> None:
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, FUTURE_TS)
    with pytest.raises(ValueError, match="outside tolerance"):
        _verify(
            PAYLOAD, sig, WEBHOOK_SECRET, tolerance_seconds=300, now=CURRENT_TS
        )


def test_timestamp_tolerance_boundary_accepted() -> None:
    """A timestamp exactly at the tolerance edge is accepted."""
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS - 300)
    assert _verify(
        PAYLOAD, sig, WEBHOOK_SECRET, tolerance_seconds=300, now=CURRENT_TS
    )


def test_missing_timestamp_rejected() -> None:
    with pytest.raises(ValueError, match="Missing Stripe signature timestamp"):
        _verify(
            PAYLOAD, f"v1={_make_signature(PAYLOAD, WEBHOOK_SECRET, CURRENT_TS).split('v1=')[1]}", WEBHOOK_SECRET
        )


# --- Idempotency / replay protection --------------------------------------


def _request(event_id: str, key: str, tenant_id: str, payload: bytes = PAYLOAD) -> IdempotencyRequest:
    # Include a digest of the raw payload so the idempotency fingerprint
    # actually changes when the same key is replayed with a different body.
    body = {
        "id": event_id,
        "type": "payment.created",
        "payload_sha256": hashlib.sha256(payload).hexdigest(),
    }
    return IdempotencyRequest(
        tenant_id=tenant_id,
        endpoint_key="stripe-webhook",
        idempotency_key=key,
        request_fingerprint=build_request_fingerprint("POST", "/v1/billing/webhook", body),
    )


def test_duplicate_webhook_event_id_idempotently_handled() -> None:
    """Same event ID under the same idempotency key returns the stored response."""
    service = IdempotencyService(InMemoryIdempotencyStore())
    tenant = "tenant-a"
    request = _request("evt_dup", "evt_dup", tenant)
    assert service.check_replay(request) is None

    service.store_response(request, IdempotencyRecord(status_code=200, body={"received": True}, headers={}))
    # simulate a duplicate delivery of the same event/key
    replayed = service.check_replay(request)
    assert replayed is not None
    assert replayed.status_code == 200


def test_replay_with_different_payload_conflict() -> None:
    """Replay of the same idempotency key with a different payload is rejected."""
    service = IdempotencyService(InMemoryIdempotencyStore())
    tenant = "tenant-a"
    request = _request("evt_replay", "evt_replay", tenant)
    service.store_response(
        request, IdempotencyRecord(status_code=200, body={"received": True}, headers={})
    )
    # Same event id + same key, only the payload differs -> the fingerprint must
    # change so the replay is detected as a conflicting payload (not identical).
    conflicting = _request(
        "evt_replay", "evt_replay", tenant, payload=b'{"id":"evt_replay","type":"payment.created"}'
    )
    with pytest.raises(IdempotencyConflictError, match="different payload"):
        service.check_replay(conflicting)


def test_retry_safe_duplicate_side_effect_prevented() -> None:
    """A delivered event must be processable exactly once per tenant/key."""
    service = IdempotencyService(InMemoryIdempotencyStore())
    tenant = "tenant-a"
    request = _request("evt_retry", "evt_retry", tenant)

    side_effects = 0

    def process() -> int:
        nonlocal side_effects
        if service.check_replay(request) is not None:
            return 0
        side_effects += 1
        service.store_response(
            request, IdempotencyRecord(status_code=200, body={"received": True}, headers={})
        )
        return 1

    assert process() == 1
    assert process() == 0
    assert side_effects == 1


def test_idempotency_key_scoped_within_tenant() -> None:
    """The same event across different tenants is independent (no cross-tenant leak)."""
    service = IdempotencyService(InMemoryIdempotencyStore())
    request_a = _request("evt_shared", "evt_shared", "tenant-a")
    request_b = _request("evt_shared", "evt_shared", "tenant-b")

    service.store_response(
        request_a, IdempotencyRecord(status_code=200, body={"received": True}, headers={})
    )
    # Tenant B sees no record: no cross-tenant replay visibility.
    assert service.check_replay(request_b) is None


def test_tenant_boundary_mismatch_rejected() -> None:
    """Idempotency request tenant must match the authenticated tenant."""
    service = IdempotencyService(InMemoryIdempotencyStore())
    request = _request("evt_tb", "evt_tb", "tenant-caller")
    with pytest.raises(IdempotencyConflictError, match="does not match authenticated tenant"):
        service.check_replay(request, tenant_id="tenant-other")


def test_webhook_error_does_not_leak_payload_via_error_message() -> None:
    """Verification errors are stable and do not echo the payload body."""
    sig = _make_signature(PAYLOAD, WEBHOOK_SECRET, STALE_TS)
    try:
        _verify(PAYLOAD, sig, WEBHOOK_SECRET)
    except ValueError as exc:
        assert PAYLOAD.decode() not in str(exc)
        assert WEBHOOK_SECRET not in str(exc)
    else:
        pytest.fail("stale signature should have been rejected")


class TestWebhookLiveStackOnly:
    """Cases that require a deployed live stack; retained as governed skips.

    - ``secret_rotation_handled``: exercising multiple-signature rollover
      requires a deployed endpoint seed, not an in-process unit boundary.
    - ``rate_limit_enforced`` / ``burst_rate_limit_enforced``: rate limiting
      is enforced against the live Redis-backed limiter.
    """

    def test_secret_rotation_handled(self) -> None:
        pytest.skip("Live-stack: multiple-secret rollover requires deployed endpoint")

    def test_webhook_rate_limit_enforced(self) -> None:
        pytest.skip("Live-stack: relies on deployed Redis rate limiter")

    def test_webhook_burst_rate_limit_enforced(self) -> None:
        pytest.skip("Live-stack: relies on deployed Redis rate limiter")

