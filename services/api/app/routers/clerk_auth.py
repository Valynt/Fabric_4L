"""Clerk-authenticated tenant resolution endpoints.

These endpoints are the canonical source for the frontend to map a Clerk
organization to a Fabric tenant. The backend is the authority: it verifies
the Clerk token, resolves the tenant from the directory, and returns the
canonical mapping. Frontend code must not trust localStorage or unverified
frontend state for tenant context.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Request
from pydantic import BaseModel

from app.core.auth_directory import AuthDirectory, DirectoryTenant, get_auth_directory
from app.core.clerk_auth import require_clerk_authenticated
from value_fabric.shared.identity.fabric_auth import AuthContext

router = APIRouter(prefix="/auth/clerk", tags=["Clerk Authentication"])


class ClerkTenantResponse(BaseModel):
    """Canonical mapping from a Clerk organization to a Fabric tenant."""

    fabric_tenant_id: str
    tenant_slug: str | None
    clerk_org_id: str
    status: str
    roles: list[str]
    permissions: list[str]


def _resolve_directory_tenant(
    directory: AuthDirectory, clerk_org_id: str | None
) -> DirectoryTenant:
    """Look up the directory tenant record for the verified Clerk org.

    Raises:
        RuntimeError: when the directory no longer contains the tenant that
        was validated by ``require_clerk_authenticated``. This should be
        impossible in normal operation and indicates a race or data-loss bug.
    """
    if clerk_org_id is None:
        raise RuntimeError("clerk_org_id is required for tenant resolution")
    tenant = directory.get_tenant_by_clerk_org(clerk_org_id)
    if tenant is None:
        raise RuntimeError(
            f"directory tenant missing for clerk_org_id={clerk_org_id!r}"
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
        fabric_tenant_id=auth.tenant_id,
        tenant_slug=tenant.slug,
        clerk_org_id=auth.clerk_org_id or "",
        status=tenant.status,
        roles=sorted(auth.roles),
        permissions=sorted(auth.permissions),
    )
