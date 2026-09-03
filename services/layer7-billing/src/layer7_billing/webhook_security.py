from __future__ import annotations

import hashlib
import hmac
import time
from dataclasses import dataclass


DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS = 300


@dataclass(frozen=True)
class StripeSignature:
    """Parsed Stripe webhook signature header components."""

    timestamp: int
    signatures: tuple[str, ...]


def parse_stripe_signature_header(signature_header: str | None) -> StripeSignature:
    """Parse Stripe's ``Stripe-Signature`` header.

    Stripe sends comma-separated fields such as ``t=1710000000,v1=<hmac>``.
    Only v1 HMAC signatures are accepted.
    """

    if signature_header is None or not signature_header.strip():
        raise ValueError("Missing Stripe-Signature header")

    timestamp: int | None = None
    signatures: list[str] = []
    for raw_part in signature_header.split(","):
        key, separator, value = raw_part.strip().partition("=")
        if not separator:
            continue
        if key == "t":
            try:
                timestamp = int(value)
            except ValueError as exc:
                raise ValueError("Invalid Stripe signature timestamp") from exc
        elif key == "v1" and value:
            signatures.append(value)

    if timestamp is None:
        raise ValueError("Missing Stripe signature timestamp")
    if not signatures:
        raise ValueError("Missing Stripe v1 signature")
    return StripeSignature(timestamp=timestamp, signatures=tuple(signatures))


def verify_stripe_webhook_signature(
    payload: bytes,
    signature_header: str | None,
    webhook_secret: str | None,
    *,
    tolerance_seconds: int = DEFAULT_STRIPE_WEBHOOK_TOLERANCE_SECONDS,
    now: int | None = None,
) -> StripeSignature:
    """Verify a Stripe webhook payload using the endpoint secret.

    Verification follows Stripe's HMAC-SHA256 scheme over
    ``<timestamp>.<raw_payload>`` and rejects stale timestamps to reduce replay
    risk. The raw request bytes must be used; parsed/re-serialized JSON is not
    safe for signature verification.
    """

    if webhook_secret is None or not webhook_secret.strip():
        raise ValueError("Stripe webhook secret is not configured")
    if tolerance_seconds < 1:
        raise ValueError("Stripe webhook timestamp tolerance must be positive")

    parsed = parse_stripe_signature_header(signature_header)
    current_time = int(time.time()) if now is None else now
    if abs(current_time - parsed.timestamp) > tolerance_seconds:
        raise ValueError("Stripe webhook timestamp is outside tolerance")

    signed_payload = f"{parsed.timestamp}.".encode("utf-8") + payload
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    if not any(
        hmac.compare_digest(expected_signature, candidate) for candidate in parsed.signatures
    ):
        raise ValueError("Invalid Stripe webhook signature")

    return parsed
