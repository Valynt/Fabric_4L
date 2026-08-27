"""Clerk webhook transport security boundary (Svix wire format).

This module is the *only* place that decides whether an incoming Clerk webhook
is authentic. It deliberately contains **no** delivery semantics — event
deduplication, idempotency, replay, ordering, and provisioning live in the
router and the idempotency/provisioning layers, so that the security boundary
stays independently reviewable from delivery behavior (see Step 3 vs Step 4
of plans/clerk-implementation/plan.md).

Verification contract (matches Clerk's documented webhook format):
- Required Svix headers: ``svix-id``, ``svix-timestamp``, ``svix-signature``.
- The signature is verified against the **raw request body** — never a
  re-serialized body — exactly once, before any JSON parsing.
- A body larger than ``MAX_WEBHOOK_BODY_BYTES`` is rejected with 413 before
  verification work is spent.
"""

from __future__ import annotations

import hashlib
import hmac
import time
from base64 import b64decode, b64encode

from fastapi import HTTPException, Request
from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    ServiceUnavailableError,
)

# Replay/skew window: a signature older than this is rejected to stop
# replays of captured valid signatures with stale timestamps.
SKEW_TOLERANCE_SECONDS = 300

# Maximum accepted raw webhook body. Clerk webhook payloads are small (a few
# KB); 1 MiB is a generous ceiling that still prevents memory-exhaustion.
MAX_WEBHOOK_BODY_BYTES = 1_048_576


async def read_webhook_body_limited(request: Request) -> bytes:
    """Read the raw request body once, enforcing the size limit.

    Returns:
        The raw body bytes (used directly for signature verification).

    Raises:
        HTTPException: 413 if the declared or actual body exceeds the limit.
    """
    content_length = request.headers.get("content-length")
    if content_length is not None:
        try:
            declared = int(content_length)
        except ValueError:
            declared = None
        if declared is not None and declared > MAX_WEBHOOK_BODY_BYTES:
            raise HTTPException(status_code=413, detail="Webhook payload too large.")

    body = await request.body()
    if len(body) > MAX_WEBHOOK_BODY_BYTES:
        raise HTTPException(status_code=413, detail="Webhook payload too large.")
    return body


def verify_svix_signature(
    *,
    secret: str,
    headers: dict[str, str],
    body: bytes,
) -> None:
    """Verify the Svix-format signature header against the raw body.

    Svix signs ``"<svix_id>.<svix_timestamp>.<raw_body>"`` with keyed-HMAC
    SHA-256 using a base64-decoded shared secret (``whsec_<base64>``).

    Raises:
        AuthenticationError: 401 when required headers are missing, the
            signature is invalid/not ``v1``, or the timestamp is stale.
        ServiceUnavailableError: 503 when the signing secret is malformed.
    """
    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")
    if not (svix_id and svix_timestamp and svix_signature):
        raise AuthenticationError(message="Unauthorized.")

    # Timestamp tolerance: reject signatures outside the skew window to stop
    # replay attacks with captured valid signatures.
    try:
        ts = int(svix_timestamp)
    except ValueError:
        raise AuthenticationError(message="Unauthorized.")
    now = int(time.time())
    if abs(now - ts) > SKEW_TOLERANCE_SECONDS:
        raise AuthenticationError(message="Unauthorized.")

    key = _decode_secret(secret)

    signed_payload = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected_digest = hmac.new(key, signed_payload, hashlib.sha256).digest()
    expected_sig = b64encode(expected_digest).decode()

    # ``svix-signature`` is a space-separated list of "v1,<base64>" pairs so
    # that a rotation window can present multiple valid signatures.
    valid = False
    for sig_entry in svix_signature.split(" "):
        if "," not in sig_entry:
            continue
        version, value = sig_entry.split(",", 1)
        if version != "v1":
            continue
        if hmac.compare_digest(value.strip(), expected_sig):
            valid = True
            break
    if not valid:
        raise AuthenticationError(message="Unauthorized.")


def _decode_secret(secret: str) -> bytes:
    """Decode a ``whsec_``-prefixed base64 secret to the raw HMAC key."""
    if secret.startswith("whsec_"):
        try:
            return b64decode(secret[len("whsec_") :])
        except Exception as exc:  # noqa: BLE001 - boundary translates to 503
            raise ServiceUnavailableError(message="Misconfigured.") from exc
    return secret.encode()
