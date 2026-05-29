from value_fabric.shared.error_handling.exceptions import AuthenticationError
"""Shared dependencies for Layer 6 API."""

from typing import TYPE_CHECKING

from fastapi import Query, Request, status

if TYPE_CHECKING:
    from value_fabric.shared.identity.context import RequestContext


def industry_filter(industry: str | None = Query(None, description="Filter by industry")) -> str | None:
    return industry


def segment_filter(segment: str | None = Query(None, description="Filter by segment")) -> str | None:
    return segment


def get_request_context(request: Request) -> "RequestContext":
    """Return the canonical tenant context set by GovernanceMiddleware."""
    ctx = getattr(request.state, "governance_context", None)
    if ctx is None or not getattr(ctx, "tenant_id", None):
        raise AuthenticationError(message = "Tenant context required")
    return ctx
