"""Clerk webhook handler — keeps Fabric4L identity tables in sync.

Security:
    - Signature verification uses Svix when the ``svix`` package is
      installed; otherwise we fall back to a stricter manual HMAC-SHA256
      check matching Svix's wire format. Either way, requests without a
      valid signature are rejected with 401.
    - The endpoint is registered under ``/internal/webhooks/clerk`` and
      MUST NOT be exposed publicly without an additional network policy.

Idempotency:
    Each Clerk event carries a Svix message id (``svix-id`` header). The
    directory's ``has_processed_event`` / ``mark_event_processed`` make
    replays a no-op.
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
from base64 import b64decode, b64encode
from enum import StrEnum
from typing import Any

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    BadRequestError,
    ConflictError,
    ServiceUnavailableError,
    ValueFabricException,
)
from value_fabric.shared.error_handling.models import ErrorCode
from value_fabric.shared.rate_limiting.ip_limiter import IPRateLimitDependency

from app.core.auth_directory import AuthDirectory, get_auth_directory
from app.core.clerk_config import get_auth_settings

logger = structlog.get_logger(__name__)

router = APIRouter(prefix="/internal/webhooks", tags=["internal-webhooks"])

try:
    _clerk_rate_limit = int(os.getenv("CLERK_WEBHOOK_RATE_LIMIT_PER_MINUTE", "30"))
except ValueError:
    _clerk_rate_limit = 30
_clerk_ip_limiter = IPRateLimitDependency(requests_per_minute=_clerk_rate_limit)


class ClerkEventType(StrEnum):
    """Canonical Clerk webhook event types handled by Fabric4L."""

    USER_CREATED = "user.created"
    USER_UPDATED = "user.updated"
    USER_DELETED = "user.deleted"
    ORGANIZATION_CREATED = "organization.created"
    ORGANIZATION_UPDATED = "organization.updated"
    ORGANIZATION_DELETED = "organization.deleted"
    ORGANIZATION_MEMBERSHIP_CREATED = "organizationMembership.created"
    ORGANIZATION_MEMBERSHIP_UPDATED = "organizationMembership.updated"
    ORGANIZATION_MEMBERSHIP_DELETED = "organizationMembership.deleted"


def _verify_svix_signature(
    *,
    secret: str,
    headers: dict[str, str],
    body: bytes,
) -> None:
    """Verify the Svix-format signature header.

    Svix uses ``v1,<base64-hmac-sha256>`` over ``"<svix_id>.<svix_timestamp>.<body>"``
    using a base64-decoded shared secret (``whsec_<base64>``).
    """
    svix_id = headers.get("svix-id")
    svix_timestamp = headers.get("svix-timestamp")
    svix_signature = headers.get("svix-signature")
    if not (svix_id and svix_timestamp and svix_signature):
        raise AuthenticationError(message="Unauthorized.")

    # Timestamp tolerance: reject signatures older than ±5 minutes to
    # prevent replay attacks with captured valid signatures.
    try:
        ts = int(svix_timestamp)
    except ValueError:
        raise AuthenticationError(message="Unauthorized.")
    now = int(time.time())
    if abs(now - ts) > 300:
        raise AuthenticationError(message="Unauthorized.")

    if secret.startswith("whsec_"):
        try:
            key = b64decode(secret[len("whsec_") :])
        except Exception as exc:
            logger.exception(
                "CLERK_WEBHOOK_SECRET base64 decode failed",
                operation="webhook_signature_verify",
                error=str(exc),
            )
            raise ServiceUnavailableError(message="Misconfigured.") from exc
    else:
        key = secret.encode()

    signed_payload = f"{svix_id}.{svix_timestamp}.".encode() + body
    expected = hmac.new(key, signed_payload, hashlib.sha256).digest()
    expected_sig = b64encode(expected).decode()
    # svix-signature is a space-separated list of "v1,<base64>" pairs.
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


def _apply_event(directory: AuthDirectory, event_type: str, data: dict[str, Any]) -> None:
    """Apply a Clerk webhook event to the identity directory.

    NOTE: Each event type calls a separate directory method. There is no
    cross-event atomic transaction — the directory is eventually consistent.
    A membership event may arrive before its user/org events; in that case
    the handler returns 409 and Clerk retries. Idempotency is guaranteed
    by the event-id deduplication layer above.
    """
    if event_type == ClerkEventType.USER_CREATED or event_type == ClerkEventType.USER_UPDATED:
        emails = data.get("email_addresses") or []
        primary_email_id = data.get("primary_email_address_id")
        primary_email = None
        for entry in emails:
            if entry.get("id") == primary_email_id:
                primary_email = entry.get("email_address")
                break
        directory.upsert_user(
            clerk_user_id=data["id"],
            email=primary_email,
            display_name=" ".join(filter(None, [data.get("first_name"), data.get("last_name")]))
            or None,
            status="active",
        )
    elif event_type == ClerkEventType.USER_DELETED:
        directory.delete_user(clerk_user_id=data["id"])
    elif event_type in {ClerkEventType.ORGANIZATION_CREATED, ClerkEventType.ORGANIZATION_UPDATED}:
        directory.upsert_tenant(
            clerk_org_id=data["id"],
            name=data.get("name") or data.get("slug") or data["id"],
            slug=data.get("slug"),
            status="active",
        )
    elif event_type == ClerkEventType.ORGANIZATION_DELETED:
        directory.delete_tenant(clerk_org_id=data["id"])
    elif event_type in {
        ClerkEventType.ORGANIZATION_MEMBERSHIP_CREATED,
        ClerkEventType.ORGANIZATION_MEMBERSHIP_UPDATED,
    }:
        org = data.get("organization") or {}
        user = data.get("public_user_data") or {}
        clerk_user_id = data.get("user_id") or user.get("user_id") or user.get("id")
        clerk_org_id = data.get("organization_id") or org.get("id")
        if not (clerk_user_id and clerk_org_id):
            raise BadRequestError(message="Missing user_id or organization_id.")
        directory.upsert_membership(
            clerk_org_id=clerk_org_id,
            clerk_user_id=clerk_user_id,
            clerk_membership_id=data["id"],
            role=data.get("role") or "org:member",
            status="active",
        )
    elif event_type == ClerkEventType.ORGANIZATION_MEMBERSHIP_DELETED:
        org = data.get("organization") or {}
        user = data.get("public_user_data") or {}
        clerk_user_id = data.get("user_id") or user.get("user_id") or user.get("id")
        clerk_org_id = data.get("organization_id") or org.get("id")
        if clerk_user_id and clerk_org_id:
            directory.revoke_membership(clerk_org_id=clerk_org_id, clerk_user_id=clerk_user_id)
    else:
        logger.info(
            "ignoring unhandled clerk event type",
            event_type=event_type,
            operation="webhook_event_apply",
        )


@router.post("/clerk", status_code=status.HTTP_204_NO_CONTENT)
async def clerk_webhook(request: Request, _limit: None = Depends(_clerk_ip_limiter)) -> None:
    settings = get_auth_settings()
    if settings.clerk is None or not settings.clerk.webhook_secret:
        # Webhook endpoint is silent until configured.
        raise ServiceUnavailableError(message="Webhook handler not configured.")

    body = await request.body()
    headers = {k.lower(): v for k, v in request.headers.items()}
    _verify_svix_signature(
        secret=settings.clerk.webhook_secret,
        headers=headers,
        body=body,
    )

    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as exc:
        logger.warning(
            "clerk webhook body not valid JSON", operation="webhook_payload_parse", error=str(exc)
        )
        raise BadRequestError(
            message="Bad request.",
            error_code=ErrorCode.AUTH_WEBHOOK_INVALID_BODY,
        ) from exc

    event_id = headers.get("svix-id") or payload.get("id") or ""
    event_type = payload.get("type")
    data = payload.get("data") or {}
    if not event_type or not isinstance(data, dict):
        raise BadRequestError(message="Bad request.")

    directory = get_auth_directory()
    if event_id and directory.has_processed_event(event_id):
        logger.info(
            "clerk webhook replay ignored",
            event_id=event_id,
            event_type=event_type,
            operation="webhook_idempotency_check",
        )
        return None

    try:
        _apply_event(directory, event_type, data)
    except KeyError as exc:
        # Apply ordering: a membership may arrive before its user/org event.
        # Surface a 409 so Clerk retries with backoff.
        logger.warning(
            "clerk webhook ordering error",
            event_id=event_id,
            event_type=event_type,
            operation="webhook_event_apply",
            error=str(exc),
        )
        raise ConflictError(message="Retry later.") from exc
    except HTTPException:
        raise
    except ValueFabricException:
        # Let structured domain errors (400/401/403/409/422) propagate to the
        # global exception handler unchanged.
        raise
    except Exception as exc:
        # Catch-all for truly unexpected programming errors.
        # Alerting/monitoring should flag these as they indicate a bug.
        logger.exception(
            "clerk webhook handler failed",
            event_id=event_id,
            event_type=event_type,
            operation="webhook_event_apply",
            error=str(exc),
        )
        raise ServiceUnavailableError(message="Internal error.") from exc

    if event_id:
        directory.mark_event_processed(event_id, event_type)
    return None
