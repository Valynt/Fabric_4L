from __future__ import annotations

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
