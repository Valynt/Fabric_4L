from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ValidationError,
)

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Service-local implementation permitted by runtime path governance.
"""

from fastapi import Request


def extract_tenant_id(request: Request | None, *, tenant_support_enabled: bool) -> str | None:
    if not request or not tenant_support_enabled:
        return None
    ctx = getattr(request.state, "governance_context", None)
    if ctx and ctx.tenant_id:
        return str(ctx.tenant_id)
    return None


def resolve_ingest_tenant_id(
    authenticated_tenant_id: str,
    header_tenant_id: str | None,
    body_tenant_id: str | None,
    *,
    allow_tenant_hints: bool,
) -> str:
    normalized_authenticated = authenticated_tenant_id.strip()
    if not normalized_authenticated:
        raise ValidationError(message = "tenant_id is required for RDF ingestion")
    normalized_header = header_tenant_id.strip() if header_tenant_id else ""
    normalized_body = body_tenant_id.strip() if body_tenant_id else ""

    # Authenticated tenant context is mandatory; tenant hints are compatibility-only and restricted.
    if not allow_tenant_hints and (normalized_header or normalized_body):
        raise AuthorizationError(message = "Tenant hints are not allowed for this principal")

    if normalized_header and normalized_header != normalized_authenticated:
        raise AuthorizationError(message = "X-Tenant-ID header does not match authenticated tenant context")

    if normalized_body and normalized_body != normalized_authenticated:
        raise AuthorizationError(message = "Request tenant_id does not match authenticated tenant context")

    return normalized_authenticated
