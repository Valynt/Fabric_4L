"""Unit tests for Layer 7 Stripe webhook security (P0-004)."""

from __future__ import annotations

import hashlib
import hmac
import time

import pytest
from layer7_billing.webhook_security import (
    DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS,
    StripeSignature,
    parse_stripe_signature_header,
    verify_stripe_webhook_signature,
)

pytestmark = [pytest.mark.unit]


class TestParseStripeSignatureHeader:
    """Stripe-Signature header parsing."""

    def test_parses_valid_header(self) -> None:
        header = "t=1710000000,v1=abc123"
        sig = parse_stripe_signature_header(header)
        assert sig.timestamp == 1710000000
        assert sig.signatures == ("abc123",)

    def test_parses_multiple_signatures(self) -> None:
        header = "t=1710000000,v1=abc123,v1=def456"
        sig = parse_stripe_signature_header(header)
        assert sig.signatures == ("abc123", "def456")

    def test_rejects_none_header(self) -> None:
        with pytest.raises(ValueError, match="Missing"):
            parse_stripe_signature_header(None)

    def test_rejects_empty_header(self) -> None:
        with pytest.raises(ValueError, match="Missing"):
            parse_stripe_signature_header("  ")

    def test_rejects_missing_timestamp(self) -> None:
        with pytest.raises(ValueError, match="timestamp"):
            parse_stripe_signature_header("v1=abc123")

    def test_rejects_missing_v1_signature(self) -> None:
        with pytest.raises(ValueError, match="v1"):
            parse_stripe_signature_header("t=1710000000")

    def test_rejects_invalid_timestamp(self) -> None:
        with pytest.raises(ValueError, match="timestamp"):
            parse_stripe_signature_header("t=notanumber,v1=abc")

    def test_ignores_unknown_fields(self) -> None:
        header = "t=1710000000,v0=old,v1=abc123,v2=future"
        sig = parse_stripe_signature_header(header)
        assert sig.signatures == ("abc123",)

    def test_result_is_frozen(self) -> None:
        sig = parse_stripe_signature_header("t=1710000000,v1=abc")
        with pytest.raises(AttributeError):
            sig.timestamp = 1  # type: ignore[misc]


class TestVerifyStripeWebhookSignature:
    """Stripe webhook HMAC verification."""

    def _make_signature(
        self,
        payload: bytes,
        secret: str,
        timestamp: int,
    ) -> str:
        signed = f"{timestamp}.".encode() + payload
        sig = hmac.new(secret.encode("utf-8"), signed, hashlib.sha256).hexdigest()
        return f"t={timestamp},v1={sig}"

    def test_verifies_valid_signature(self) -> None:
        payload = b'{"id":"evt_1"}'
        secret = "whsec_test_dummy_secret"
        ts = int(time.time())
        header = self._make_signature(payload, secret, ts)
        result = verify_stripe_webhook_signature(payload, header, secret)
        assert isinstance(result, StripeSignature)
        assert result.timestamp == ts

    def test_rejects_wrong_secret(self) -> None:
        payload = b'{"id":"evt_1"}'
        ts = int(time.time())
        header = self._make_signature(payload, "whsec_test_dummy_correct", ts)
        with pytest.raises(ValueError, match="Invalid"):
            verify_stripe_webhook_signature(payload, header, "whsec_test_dummy_wrong")

    def test_rejects_stale_timestamp(self) -> None:
        payload = b'{"id":"evt_1"}'
        secret = "whsec_test_dummy_secret"
        old_ts = int(time.time()) - DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS - 10
        header = self._make_signature(payload, secret, old_ts)
        with pytest.raises(ValueError, match="tolerance"):
            verify_stripe_webhook_signature(payload, header, secret)

    def test_accepts_timestamp_within_tolerance(self) -> None:
        payload = b'{"id":"evt_1"}'
        secret = "whsec_test_dummy_secret"
        ts = int(time.time()) - 10
        header = self._make_signature(payload, secret, ts)
        result = verify_stripe_webhook_signature(payload, header, secret)
        assert result.timestamp == ts

    def test_rejects_missing_secret(self) -> None:
        with pytest.raises(ValueError, match="secret is not configured"):
            verify_stripe_webhook_signature(b"payload", "t=1,v1=a", None)

    def test_rejects_empty_secret(self) -> None:
        with pytest.raises(ValueError, match="secret is not configured"):
            verify_stripe_webhook_signature(b"payload", "t=1,v1=a", "  ")

    def test_rejects_zero_tolerance(self) -> None:
        with pytest.raises(ValueError, match="tolerance must be positive"):
            verify_stripe_webhook_signature(b"payload", "t=1,v1=a", "secret", tolerance_seconds=0)

    def test_custom_now_accepted(self) -> None:
        payload = b'{"id":"evt_1"}'
        secret = "whsec_test_dummy_secret"
        ts = 1710000000
        header = self._make_signature(payload, secret, ts)
        result = verify_stripe_webhook_signature(payload, header, secret, now=ts)
        assert result.timestamp == ts

    def test_custom_now_rejects_future(self) -> None:
        payload = b'{"id":"evt_1"}'
        secret = "whsec_test_dummy_secret"
        ts = 1710000000
        header = self._make_signature(payload, secret, ts)
        with pytest.raises(ValueError, match="tolerance"):
            verify_stripe_webhook_signature(
                payload, header, secret, now=ts + DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS + 10
            )
