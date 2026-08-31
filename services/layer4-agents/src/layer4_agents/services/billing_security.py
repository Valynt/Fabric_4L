from __future__ import annotations

"""Canonical Stripe billing webhook security primitives.

This module is the single source of truth for Stripe webhook source-IP checks,
Stripe-Signature header parsing/HMAC verification, and request metadata
extraction used by billing webhook entry points.
"""

import hashlib
import hmac
import ipaddress
import os
import re
import time
from collections.abc import Iterable
from dataclasses import dataclass

from fastapi import Request
from value_fabric.shared.error_handling.exceptions import AuthorizationError

_DEFAULT_STRIPE_WEBHOOK_IP_CIDRS: tuple[str, ...] = (
    "3.18.12.63/32",
    "3.130.192.231/32",
    "13.235.14.237/32",
    "13.235.122.149/32",
    "35.154.171.200/32",
    "35.154.171.208/32",
    "52.15.183.38/32",
    "52.15.183.39/32",
    "54.88.130.27/32",
    "54.88.130.28/32",
    "54.187.174.169/32",
    "54.187.174.170/32",
)


def _parse_cidrs(cidr_values: Iterable[str]) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw in cidr_values:
        value = raw.strip()
        if not value:
            continue
        networks.append(ipaddress.ip_network(value, strict=False))
    return networks


def _load_stripe_webhook_ip_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    configured = os.environ.get("STRIPE_WEBHOOK_IP_CIDRS", "")
    if configured.strip():
        return _parse_cidrs(configured.split(","))
    return _parse_cidrs(_DEFAULT_STRIPE_WEBHOOK_IP_CIDRS)


STRIPE_WEBHOOK_IPS = _load_stripe_webhook_ip_networks()
STRIPE_WEBHOOK_SKIP_IP_CHECK = os.environ.get("STRIPE_WEBHOOK_SKIP_IP_CHECK", "").lower() in ("true", "1", "yes")

if os.environ.get("ENVIRONMENT") == "production" and STRIPE_WEBHOOK_SKIP_IP_CHECK:
    raise RuntimeError("STRIPE_WEBHOOK_SKIP_IP_CHECK cannot be enabled in production")


def is_stripe_webhook_ip(client_ip: str) -> bool:
    try:
        ip = ipaddress.ip_address(client_ip)
        if ip.is_loopback:
            return True
        return any(ip in network for network in STRIPE_WEBHOOK_IPS)
    except ValueError:
        return False


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if hasattr(request, "client") and request.client:
        return request.client.host
    return ""


_STRIPE_TIMESTAMP_TOLERANCE_SECONDS = int(os.environ.get("STRIPE_WEBHOOK_TIMESTAMP_TOLERANCE_SECONDS", "300"))
_SIG_PART_RE = re.compile(r"^([a-zA-Z0-9_]+)=(.+)$")


@dataclass(frozen=True)
class StripeSignatureComponents:
    timestamp: int
    signatures: tuple[str, ...]


def parse_stripe_signature_header(signature_header: str) -> StripeSignatureComponents:
    if not signature_header or not signature_header.strip():
        raise ValueError("Missing Stripe-Signature header")

    timestamp: int | None = None
    signatures: list[str] = []
    for part in signature_header.split(','):
        match = _SIG_PART_RE.match(part.strip())
        if not match:
            continue
        key, value = match.groups()
        if key == "t":
            timestamp = int(value)
        elif key == "v1":
            signatures.append(value)

    if timestamp is None:
        raise ValueError("Missing Stripe signature timestamp")
    if not signatures:
        raise ValueError("Missing Stripe v1 signature")
    return StripeSignatureComponents(timestamp=timestamp, signatures=tuple(signatures))


def ensure_timestamp_within_tolerance(timestamp: int, now: int | None = None) -> None:
    current = now if now is not None else int(time.time())
    if abs(current - timestamp) > _STRIPE_TIMESTAMP_TOLERANCE_SECONDS:
        raise ValueError("Timestamp outside tolerance (stale/replay)")


def verify_stripe_webhook_signature(
    payload: bytes,
    signature_header: str | None,
    webhook_secret: str | None,
    *,
    tolerance_seconds: int = 300,
    now: int | None = None,
) -> StripeSignatureComponents:
    """Verify a Stripe webhook payload using the endpoint secret.

    Verification follows Stripe's HMAC-SHA256 scheme over
    ``<timestamp>.<raw_payload>`` and rejects stale timestamps to reduce replay
    risk. The raw request bytes must be used; parsed/re-serialized JSON is not
    safe for signature verification. ``now`` pins the reference time for tests.

    Canonical Layer 4 webhook verification implementation.
    """
    if webhook_secret is None or not webhook_secret.strip():
        raise ValueError("Stripe webhook secret is not configured")
    if tolerance_seconds < 1:
        raise ValueError("Stripe webhook timestamp tolerance must be positive")
    if signature_header is None:
        raise ValueError("Missing Stripe-Signature header")

    parsed = parse_stripe_signature_header(signature_header)
    current_time = int(time.time()) if now is None else now
    if abs(current_time - parsed.timestamp) > tolerance_seconds:
        raise ValueError("Stripe webhook timestamp is outside tolerance")

    signed_payload = f"{parsed.timestamp}.".encode() + payload
    expected_signature = hmac.new(
        webhook_secret.encode("utf-8"), signed_payload, hashlib.sha256
    ).hexdigest()
    if not any(
        hmac.compare_digest(expected_signature, candidate) for candidate in parsed.signatures
    ):
        raise ValueError("Invalid Stripe webhook signature")

    return parsed


def validate_webhook_request_security(request: Request, stripe_signature: str, *, enforce_ip_check: bool = True) -> StripeSignatureComponents:
    client_ip = get_client_ip(request)
    if enforce_ip_check and not is_stripe_webhook_ip(client_ip):
        raise AuthorizationError(message="Invalid origin")

    components = parse_stripe_signature_header(stripe_signature)
    ensure_timestamp_within_tolerance(components.timestamp)
    return components
