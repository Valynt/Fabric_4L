from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    AuthorizationError,
)

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Service-local JWT bearer context extraction used by model registry
and other endpoints that need tenant_id + user_id from a raw Request object
before the FastAPI dependency graph has resolved RequestContext.

Canonical auth path for route handlers is ``require_tenant_context`` from
``value_fabric.shared.identity.dependencies``. Use this module only when a
raw ``Request`` object must be inspected outside the dependency graph (e.g.
in unit tests or middleware that runs before FastAPI resolves dependencies).
"""


import base64
import json
from dataclasses import dataclass

from starlette.requests import Request


@dataclass
class TenantBearerContext:
    """Tenant context extracted from a JWT bearer token.

    Fields mirror the subset of ``RequestContext`` used by model registry
    tests and middleware. ``source`` and ``auth_method`` are fixed constants
    for bearer-token extraction.
    """

    tenant_id: str
    user_id: str
    source: str = "authorization_bearer"
    auth_method: str = "jwt"


def extract_tenant_from_bearer(request: Request) -> TenantBearerContext:
    """Resolve tenant context from verified request state before bearer fallback.

    Service APIs must scope data from the gateway-signed Fabric auth envelope
    or canonical governance context, not from browser-controlled tenant headers.
    The bearer fallback exists only for legacy paths that run after upstream
    verification but before FastAPI dependencies execute.
    """
    ctx = getattr(request.state, "governance_context", None)
    if ctx is not None and getattr(ctx, "tenant_id", None):
        return TenantBearerContext(
            tenant_id=str(ctx.tenant_id),
            user_id=str(getattr(ctx, "user_id", "") or ""),
            source="governance_context",
        )

    auth = getattr(request.state, "auth", None)
    if auth is not None and getattr(auth, "tenant_id", None):
        return TenantBearerContext(
            tenant_id=str(auth.tenant_id),
            user_id=str(getattr(auth, "user_id", "") or ""),
            source="fabric_auth_envelope",
        )

    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise AuthenticationError(message="Missing or invalid authorization header")

    token = auth_header[7:]
    parts = token.split(".")
    if len(parts) != 3:
        raise AuthenticationError(message="Malformed JWT token")

    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except Exception:
        raise AuthenticationError(message="Could not decode JWT payload")

    tenant_claim = (
        payload["tenant_id"] if "tenant_id" in payload else payload.get("tid", "")
    )
    tenant_id = str(tenant_claim).strip()
    if not tenant_id:
        raise AuthenticationError(message="JWT token missing tenant_id claim")

    req_tenant_id = request.headers.get("x-tenant-id")
    if req_tenant_id and req_tenant_id.strip() != tenant_id:
        raise AuthorizationError(message="Tenant context mismatch")

    user_id = payload.get("sub") or payload.get("user_id") or ""

    return TenantBearerContext(tenant_id=tenant_id, user_id=user_id)


# ---------------------------------------------------------------------------
# Backward-compat alias used by tests/layer3/test_model_registry_tenant_context.py
# via value_fabric.layer3.api.routes.models._get_tenant_context.
# Remove when the test is updated to import extract_tenant_from_bearer directly.
# ---------------------------------------------------------------------------
_get_tenant_context = extract_tenant_from_bearer
