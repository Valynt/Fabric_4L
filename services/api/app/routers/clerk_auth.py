"""Clerk-authenticated tenant resolution endpoints.

These endpoints are the canonical source for the frontend to map a Clerk
organization to a Fabric tenant. The backend is the authority: it verifies
the Clerk token, resolves the tenant from the directory, and returns the
canonical mapping. Frontend code must not trust localStorage or unverified
frontend state for tenant context.
"""

from __future__ import annotations

from typing import Any, Literal

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Path, Request, Response, status
from pydantic import BaseModel, ConfigDict, Field
from value_fabric.shared.error_handling.models import ErrorCode
from value_fabric.shared.identity.fabric_auth import AuthContext

from app.core.auth_directory import AuthDirectory, DirectoryTenant, get_auth_directory
from app.core.auth_telemetry import get_auth_health_summary
from app.core.clerk_auth import require_clerk_authenticated
from app.services.authorization_snapshot import AuthorizationSnapshot, AuthorizationSnapshotService

router = APIRouter(prefix="/auth/clerk", tags=["Platform", "Clerk Authentication"])
authorization_router = APIRouter(prefix="/auth", tags=["Platform", "Authorization"])


class ClerkTenantResponse(BaseModel):
    """Canonical mapping from a Clerk organization to a Fabric tenant."""

    fabric_tenant_id: str = Field(description="Unique Fabric internal tenant identifier")
    tenant_slug: str | None = Field(default=None, description="Human-readable unique tenant URL slug")
    clerk_org_id: str = Field(description="External Clerk organization identifier")
    status: Literal["active", "suspended", "deleted"] = Field(description="Operational tenant status")
    roles: list[str] = Field(description="List of mapped roles for the tenant actor")
    permissions: list[str] = Field(description="List of resolved effective permissions for the tenant actor")


class RevokeSessionRequest(BaseModel):
    """Payload to revoke a specific active Clerk session."""

    session_id: str | None = Field(default=None, description="Optional target Clerk session ID to revoke")

    model_config = ConfigDict(
        title="RevokeSessionRequest",
        json_schema_extra={
            "description": "Payload to revoke a specific active Clerk session.",
            "example": {
                "session_id": "sess_2exampleSessionId123456789"
            }
        }
    )


class RevokeSessionResponse(BaseModel):
    """Result of session revocation operation."""

    revoked: bool = Field(description="Whether the session or sessions were successfully revoked")
    session_id: str | None = Field(default=None, description="The session identifier that was revoked")
    message: str = Field(description="Human-readable outcome description message")

    model_config = ConfigDict(
        title="RevokeSessionResponse",
        json_schema_extra={
            "description": "Result of session revocation operation.",
            "example": {
                "revoked": True,
                "session_id": "sess_2exampleSessionId123456789",
                "message": "Session revoked successfully."
            }
        }
    )


class InvitationResponse(BaseModel):
    """Organization invitation projection schema model."""

    invitation_id: str = Field(description="Unique Clerk invitation identifier")
    org_id: str = Field(description="Unique Clerk organization identifier")
    email: str = Field(description="Email address of the invitee")
    role: str = Field(description="Assigned organization role for the invitee")
    status: str = Field(description="Status of the invitation (e.g. pending, accepted, revoked)")

    model_config = ConfigDict(
        title="InvitationResponse",
        json_schema_extra={
            "description": "Organization invitation projection schema model.",
            "example": {
                "invitation_id": "inv_2exampleInvitation123456789",
                "org_id": "org_2exampleOrg123456789",
                "email": "user@example.com",
                "role": "org:member",
                "status": "pending"
            }
        }
    )


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


@authorization_router.get("/health")
@router.get("/health")
async def get_auth_health() -> dict[str, Any]:
    """Return real-time health and verification SLO statistics for the auth plane."""
    return get_auth_health_summary()


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
        401: {
            "description": "Authentication is missing, invalid, or expired.",
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
    x_account_id: str | None = Header(
        default=None,
        alias="X-Account-ID",
        description="Optional exact Fabric account identifier to bind into the issued authorization scope.",
    ),
    auth: AuthContext = Depends(require_clerk_authenticated),
    directory: AuthDirectory = Depends(get_auth_directory),
) -> AuthorizationSnapshot:
    """Issue one non-cacheable candidate from the canonical authorization projection."""
    response.headers["Cache-Control"] = "private, no-store"
    claims = getattr(request.state, "clerk_claims", {})
    return AuthorizationSnapshotService(directory).issue(
        auth=auth, verified_claims=claims, account_id=x_account_id
    )


@router.post(
    "/sessions/revoke",
    response_model=RevokeSessionResponse,
    responses={
        200: {
            "description": "Session revoked successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "revoked": True,
                        "session_id": "sess_2exampleSessionId123456789",
                        "message": "Session revoked successfully.",
                    }
                }
            },
        }
    },
)
async def revoke_active_session(
    request: Request,
    body: RevokeSessionRequest = Body(
        default=...,
        description="Target Clerk session revocation request payload.",
        openapi_examples={
            "default": {
                "summary": "Revoke target session",
                "value": {"session_id": "sess_2exampleSessionId123456789"},
            }
        },
    ),
    auth: AuthContext = Depends(require_clerk_authenticated),
    directory: AuthDirectory = Depends(get_auth_directory),
) -> RevokeSessionResponse:
    """Revoke an active Clerk session discriminator."""
    claims = getattr(request.state, "clerk_claims", {})
    caller_sid = claims.get("sid")
    requested_sid = body.session_id if body and body.session_id else None

    if requested_sid and caller_sid and requested_sid != caller_sid:
        caller_role = getattr(auth.membership, "role", "") if hasattr(auth, "membership") else ""
        if caller_role not in ("tenant_admin", "org:admin"):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={"code": "auth.forbidden", "message": "Cannot revoke sessions belonging to other users."},
            )
        sid = requested_sid
    else:
        sid = requested_sid or caller_sid

    if not sid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "auth.session_id_missing", "message": "No session identifier to revoke."},
        )
    directory.revoke_session(sid)
    return RevokeSessionResponse(
        revoked=True,
        session_id=sid,
        message="Session revoked successfully.",
    )


@router.post(
    "/sessions/revoke-all",
    response_model=RevokeSessionResponse,
    responses={
        200: {
            "description": "All sessions revoked for user successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "revoked": True,
                        "session_id": None,
                        "message": "All sessions revoked for user.",
                    }
                }
            },
        }
    },
)
async def revoke_all_user_sessions(
    request: Request,
    auth: AuthContext = Depends(require_clerk_authenticated),
    directory: AuthDirectory = Depends(get_auth_directory),
) -> RevokeSessionResponse:
    """Revoke all active sessions for the authenticated user (sign out everywhere)."""
    directory.revoke_user_sessions(auth.clerk_user_id)
    return RevokeSessionResponse(
        revoked=True,
        message="All sessions revoked for user.",
    )


@router.get("/invitations", response_model=list[InvitationResponse])
async def list_org_invitations(
    auth: AuthContext = Depends(require_clerk_authenticated),
    directory: AuthDirectory = Depends(get_auth_directory),
) -> list[InvitationResponse]:
    """List pending invitations for the verified Clerk organization."""
    if not auth.clerk_org_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": ErrorCode.AUTH_TENANT_UNRESOLVED, "message": "No active organization."},
        )
    invitations = directory.list_invitations_for_org(auth.clerk_org_id)
    return [
        InvitationResponse(
            invitation_id=inv.clerk_invitation_id,
            org_id=inv.clerk_org_id,
            email=inv.email,
            role=inv.role,
            status=inv.status,
        )
        for inv in invitations
    ]


@router.post(
    "/invitations/{invitation_id}/accept",
    response_model=InvitationResponse,
    responses={
        200: {
            "description": "Invitation accepted successfully.",
            "content": {
                "application/json": {
                    "example": {
                        "invitation_id": "inv_2exampleInvitation123456789",
                        "org_id": "org_2exampleOrg123456789",
                        "email": "user@example.com",
                        "role": "org:member",
                        "status": "accepted"
                    }
                }
            }
        }
    }
)
async def accept_org_invitation(
    request: Request,
    invitation_id: str = Path(..., description="Unique Clerk organization invitation identifier to accept"),
    auth: AuthContext = Depends(require_clerk_authenticated),
    directory: AuthDirectory = Depends(get_auth_directory),
) -> InvitationResponse:
    """Accept a pending organization invitation and activate user membership."""
    inv = directory.get_invitation(invitation_id)
    if not inv or inv.status != "pending":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "code": "auth.invitation_not_found",
                "message": "Invitation not found or no longer pending.",
            },
        )

    # Verify caller email matches the invitation email recipient
    claims = getattr(request.state, "clerk_claims", {})
    user = directory.get_user_by_clerk(auth.clerk_user_id)
    caller_email = (
        (user.email if user else None)
        or claims.get("email")
        or getattr(auth.actor, "email", None)
    )

    if inv.email and caller_email and inv.email.strip().lower() != caller_email.strip().lower():
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={
                "code": "auth.invitation_email_mismatch",
                "message": "Invitation was issued for a different email address.",
            },
        )

    directory.revoke_invitation(invitation_id)
    directory.upsert_membership(
        clerk_org_id=inv.clerk_org_id,
        clerk_user_id=auth.clerk_user_id,
        clerk_membership_id=f"mem_{invitation_id[-8:]}",
        role=inv.role,
        status="active",
    )
    return InvitationResponse(
        invitation_id=inv.clerk_invitation_id,
        org_id=inv.clerk_org_id,
        email=inv.email,
        role=inv.role,
        status="accepted",
    )
