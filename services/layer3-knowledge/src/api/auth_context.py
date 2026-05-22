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

from __future__ import annotations

import base64
import json
from dataclasses import dataclass

from fastapi import HTTPException
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
    """Extract and validate tenant context from a JWT bearer token on a raw Request.

    Raises HTTPException(401) if the token is absent, malformed, or missing
    the ``tenant_id`` claim.
    Raises HTTPException(403) if the ``X-Tenant-ID`` header is present but
    conflicts with the token claim.

    Note: signature verification is intentionally omitted — the auth
    middleware upstream is responsible for that. This function only decodes
    the payload to extract claims.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid authorization header")

    token = auth_header[7:]
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=401, detail="Malformed JWT token")

    try:
        padded = parts[1] + "=" * (-len(parts[1]) % 4)
        payload = json.loads(base64.urlsafe_b64decode(padded).decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=401, detail="Could not decode JWT payload")

    tenant_id = str(payload.get("tenant_id") or payload.get("tid") or "").strip()
    if not tenant_id:
        raise HTTPException(status_code=401, detail="JWT token missing tenant_id claim")

    user_id = payload.get("sub") or payload.get("user_id") or ""

    header_tenant = request.headers.get("x-tenant-id", "")
    if header_tenant and header_tenant != tenant_id:
        raise HTTPException(
            status_code=403,
            detail="X-Tenant-ID header does not match authenticated tenant context",
        )

    return TenantBearerContext(tenant_id=tenant_id, user_id=user_id)


# ---------------------------------------------------------------------------
# Backward-compat alias used by tests/layer3/test_model_registry_tenant_context.py
# via value_fabric.layer3.api.routes.models._get_tenant_context.
# Remove when the test is updated to import extract_tenant_from_bearer directly.
# ---------------------------------------------------------------------------
_get_tenant_context = extract_tenant_from_bearer
