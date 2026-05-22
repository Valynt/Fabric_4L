"""Auth helpers for L2.5 Signal Refinery.

Wraps value_fabric.shared.identity with a graceful fallback for
environments where the shared package is not installed (e.g. isolated tests).
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import Depends, HTTPException, status

logger = logging.getLogger(__name__)

try:
    from value_fabric.shared.identity.context import RequestContext, get_request_context
    from value_fabric.shared.identity.dependencies import require_authenticated

    SHARED_IDENTITY_AVAILABLE = True
except ImportError:
    SHARED_IDENTITY_AVAILABLE = False
    RequestContext = Any  # type: ignore[assignment,misc]

    def get_request_context() -> Any:  # type: ignore[misc]
        return None

    def require_authenticated() -> Any:  # type: ignore[misc]
        return None


def get_tenant_id_from_context() -> str:
    """Extract tenant_id from RequestContext. Fail closed if missing."""
    ctx = get_request_context()
    if ctx is not None and getattr(ctx, "tenant_id", None):
        return str(ctx.tenant_id)

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Tenant context required.",
    )
