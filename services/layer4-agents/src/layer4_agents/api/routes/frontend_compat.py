from __future__ import annotations

"""Frontend compatibility aliases for path mismatches.

ROUTE LIFECYCLE DOCUMENTATION
------------------------------
Canonical API routes (do NOT delete without frontend coordination):
  GET  /auth/session        -> current request context as a session profile

Removed aliases (removal dates passed; see contracts/deprecations/):
  POST /auth/register       -> REMOVED 2026-08-10 (was alias for
                               POST /v1/tenants/register; removal target
                               2026-07-01 per x-deprecated-removal-date)
  GET  /tenant/settings     -> REMOVED 2026-08-10 (was alias for
                               GET /v1/tenants/current/settings; removal
                               target 2026-08-01)
  PATCH /tenant/settings    -> REMOVED 2026-08-10 (same canonical target)

NOTES
-----
- This router is mounted at prefix="/v1" in src/api/main.py.
- All aliases must enforce the same auth/tenant isolation as canonical routes.
- When adding a new alias, document it above and update the contract map.
"""

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

router = APIRouter(tags=["Frontend Compatibility"])


class AuthSessionResponse(BaseModel):
    """Minimal authenticated session profile for compatibility smoke checks."""

    authenticated: bool
    user_id: str
    tenant_id: str
    roles: list[str]
    permissions: list[str]


@router.get("/auth/session", response_model=AuthSessionResponse)
async def get_auth_session_frontend_alias(
    ctx: RequestContext = Depends(require_authenticated),
) -> AuthSessionResponse:
    """Compatibility alias exposing the current request context as a session profile."""
    return AuthSessionResponse(
        authenticated=True,
        user_id=str(ctx.user_id),
        tenant_id=str(ctx.tenant_id),
        roles=[getattr(role, "value", str(role)) for role in ctx.roles],
        permissions=[getattr(permission, "value", str(permission)) for permission in ctx.permissions],
    )
