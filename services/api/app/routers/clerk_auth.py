"""Clerk-authenticated tenant resolution endpoints.

These endpoints are the canonical source for the frontend to map a Clerk
organization to a Fabric tenant. The backend is the authority: it verifies
the Clerk token, resolves the tenant from the directory, and returns the
canonical mapping. Frontend code must not trust localStorage or unverified
frontend state for tenant context.
"""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response, status
from pydantic import BaseModel
from value_fabric.shared.error_handling.models import ErrorCode
from value_fabric.shared.identity.fabric_auth import AuthContext

from app.core.auth_directory import AuthDirectory, DirectoryTenant, get_auth_directory
from app.core.clerk_auth import require_clerk_authenticated
from app.services.authorization_snapshot import AuthorizationSnapshot, AuthorizationSnapshotService

router = APIRouter(prefix="/auth/clerk", tags=["Clerk Authentication"])
authorization_router = APIRouter(prefix="/auth", tags=["Authorization"])


class ClerkTenantResponse(BaseModel):
    """Canonical mapping from a Clerk organization to a Fabric tenant."""

    fabric_tenant_id: str
    tenant_slug: str | None
    clerk_org_id: str
    status: Literal["active", "suspended", "deleted"]
    roles: list[str]
    permissions: list[str]


def _resolve_directory_tenant(
    directory: AuthDirectory, clerk_org_id: str | None
) -> DirectoryTenant:
    """Look up the directory tenant record for the verified Clerk org.

    Raises:
        HTTPException: 403 when the directory does not contain the tenant that
        was validated by ``require_clerk_authenticated``, or when the tenant is
        not active. This should be impossible in normal operation but is handled
        as a controlled authorization failure rather than a 500.
    """
    if clerk_org_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCode.AUTH_TENANT_UNRESOLVED,
                "message": "No active Clerk organization is associated with this request.",
            },
        )
    tenant = directory.get_tenant_by_clerk_org(clerk_org_id)
    if tenant is None or tenant.status != "active":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": ErrorCode.AUTH_TENANT_UNRESOLVED,
                "message": "The tenant for this organization is not active or no longer exists.",
            },
        )
    return tenant


@router.get("/tenant", response_model=ClerkTenantResponse)
async def get_clerk_tenant(
    request: Request,
    auth: AuthContext = Depends(require_clerk_authenticated),
    directory: AuthDirectory = Depends(get_auth_directory),
) -> ClerkTenantResponse:
    """Return the Fabric tenant mapping for the active Clerk organization.

    This endpoint is the single source of truth for Clerk org → Fabric tenant
    resolution. Callers must present a valid Clerk Bearer token. Failures map
    to the standard codes from ``require_clerk_authenticated``:

    - 401: missing/invalid/expired token
    - 403: no active Clerk org, no tenant mapping, inactive membership, or
      suspended/deleted tenant
    """
    tenant = _resolve_directory_tenant(directory, auth.clerk_org_id)
    return ClerkTenantResponse(
        fabric_tenant_id=tenant.id,
        tenant_slug=tenant.slug,
        clerk_org_id=auth.clerk_org_id or "",
        status=tenant.status,
        roles=sorted(auth.roles),
        permissions=sorted(auth.permissions),
    )


@authorization_router.get(
    "/authorization-snapshot",
    response_model=AuthorizationSnapshot,
    response_model_by_alias=True,
    responses={
        200: {
            "headers": {
                "Cache-Control": {
                    "description": "Always `private, no-store`; snapshots must not be cached by intermediaries.",
                    "schema": {"type": "string"},
                }
            }
        },
        403: {
            "description": "Authorization or account scope denied. Nonexistent, foreign-tenant, and inaccessible accounts all use `account_scope_denied`.",
            "headers": {
                "Cache-Control": {
                    "description": "Always `private, no-store`.",
                    "schema": {"type": "string"},
                }
            },
        },
    },
)
async def get_authorization_snapshot(
    request: Request,
    response: Response,
    x_account_id: str | None = Header(default=None, alias="X-Account-ID"),
    auth: AuthContext = Depends(require_clerk_authenticated),
    directory: AuthDirectory = Depends(get_auth_directory),
) -> AuthorizationSnapshot:
    """Issue one non-cacheable candidate from the canonical authorization projection."""
    response.headers["Cache-Control"] = "private, no-store"
    claims = getattr(request.state, "clerk_claims", {})
    return AuthorizationSnapshotService(directory).issue(
        auth=auth, verified_claims=claims, account_id=x_account_id
    )
