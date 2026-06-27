"""Shared FastAPI dependencies for Layer 1 API routes."""

from __future__ import annotations

from uuid import UUID

import structlog
from fastapi import Request
from value_fabric.shared.error_handling.exceptions import AuthenticationError

from ..metrics import get_metrics

logger = structlog.get_logger()


def get_tenant_id(request: Request) -> UUID:
    """Extract organization (tenant) ID from verified identity context."""
    ctx = getattr(request.state, "governance_context", None)
    if ctx is not None:
        return ctx.tenant_id

    raise AuthenticationError(message="Authentication required")


def get_current_user_id(request: Request) -> UUID:
    """Extract user ID from the GovernanceMiddleware context."""
    ctx = getattr(request.state, "governance_context", None)
    if ctx is not None and ctx.user_id:
        try:
            return UUID(ctx.user_id)
        except ValueError:
            logger.error(
                "invalid_user_id_format",
                user_id=ctx.user_id,
                path=request.url.path,
                error="UUID parsing failed",
            )
            metrics = get_metrics()
            if metrics:
                metrics.increment_errors(error_type="invalid_uuid", component="auth")
            raise AuthenticationError(message="Invalid user ID format") from None
    raise AuthenticationError(message="Authentication required")


def get_current_user_roles(request: Request) -> list[str]:
    """Extract user roles from the GovernanceMiddleware context."""
    ctx = getattr(request.state, "governance_context", None)
    if ctx is not None:
        return list(ctx.roles or [])
    raise AuthenticationError(message="Authentication required")
