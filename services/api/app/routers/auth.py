"""Authentication router for signup, login, and token management."""

from __future__ import annotations

import hashlib
import uuid

from datetime import UTC, datetime
from typing import Literal

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr

from app.core.config import get_settings
from app.core.database import db
from value_fabric.shared.database.tenant_validation import SYSTEM_TENANT_ID
from app.core.security import (
    TokenPayload,
    create_access_token,
    get_current_user,
    require_authenticated,
    revoke_token,
    hash_password,
    is_account_locked,
    record_failed_login,
    record_successful_login,
    validate_password_strength,
    verify_password,
)
from app.models.schemas import AuditLogEvent, Tenant, User

router = APIRouter(prefix="/auth", tags=["Authentication"])


# ---------------------------------------------------------------------------
# Request/response schemas
# ---------------------------------------------------------------------------

class SignupRequest(BaseModel):
    email: EmailStr
    password: str
    name: str
    tenant_name: str
    # plan is intentionally absent: unauthenticated callers must not self-assign
    # a billing tier. New tenants always start on "free". Plan upgrades require
    # a separate authenticated + authorized flow (F-04).


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class InviteRequest(BaseModel):
    email: EmailStr
    name: str
    # Canonical role schema — must match User.role (F-14).
    # super_admin cannot be granted via invite (F-11).
    role: Literal["tenant_admin", "content_admin", "analyst", "read_only"] = "analyst"


class AcceptInviteRequest(BaseModel):
    email: EmailStr
    password: str
    name: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
    status: str


class ImpersonationStartRequest(BaseModel):
    target_user_id: str
    reason: str
    notify_email: bool = False
    notify_webhook: bool = False


class ImpersonationStartResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    impersonation_session_id: str


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post("/signup", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest) -> TokenResponse:
    """Create a new tenant and user, then return a JWT."""
    # Validate password strength server-side before any DB work (F-02).
    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    # Cross-tenant email uniqueness check — requires explicit allow_system_scope
    # so the bypass cannot be triggered by an arbitrary caller passing "system".
    existing = db.users.list(tenant_id=SYSTEM_TENANT_ID, filter_fn=lambda u: u.email == payload.email, allow_system_scope=True)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="An account with this email already exists",
        )

    tenant_id = str(uuid.uuid4())
    tenant = Tenant(
        id=tenant_id,
        name=payload.tenant_name,
        plan="free",  # always start on free; upgrades require a separate authorized flow
    )
    db.tenants.insert(tenant.id, tenant)

    # User IDs must be opaque UUIDs — never derived from email or any
    # user-supplied input (F-01: predictable IDs enable enumeration/IDOR).
    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        tenant_id=tenant_id,
        email=payload.email,
        name=payload.name,
        role="tenant_admin",
        password_hash=hash_password(payload.password),
        status="active",
    )
    db.users.insert(user.id, user)

    access_token = create_access_token(
        subject=user.id,
        tenant_id=tenant_id,
        # expires_delta=None → uses settings.access_token_expire_minutes (F-08)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


@router.post("/login", response_model=TokenResponse)
async def login(payload: LoginRequest) -> TokenResponse:
    """Authenticate a user and return a JWT."""
    # Use a generic error for all auth failures to prevent email enumeration (F-05).
    _auth_fail = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid email or password",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Cross-tenant email lookup — requires explicit allow_system_scope.
    users = db.users.list(tenant_id=SYSTEM_TENANT_ID, filter_fn=lambda u: u.email == payload.email, allow_system_scope=True)
    if not users:
        raise _auth_fail

    user = users[0]

    # Check account lockout before any other status check (F-05).
    if is_account_locked(user):
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Account temporarily locked due to repeated failed login attempts. Try again later.",
            headers={"WWW-Authenticate": "Bearer", "Retry-After": "900"},
        )

    if user.status == "invited":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account pending activation. Please accept your invitation.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if user.status == "deactivated":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account deactivated. Contact your tenant administrator.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    if not user.password_hash or not verify_password(payload.password, user.password_hash):
        # Record the failure and persist the updated attempt count.
        updated = record_failed_login(user)
        db.users.insert(updated.id, updated)
        raise _auth_fail

    # Successful login — reset the failure counter.
    updated = record_successful_login(user)
    db.users.insert(updated.id, updated)

    access_token = create_access_token(
        subject=updated.id,
        tenant_id=updated.tenant_id,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


# Role hierarchy for escalation guard (F-11).
# An inviter may only grant roles strictly below their own rank.
_ROLE_RANK: dict[str, int] = {
    "super_admin": 100,
    "tenant_admin": 80,
    "content_admin": 60,
    "analyst": 40,
    "read_only": 20,
}

_IMPERSONATION_SESSIONS: dict[str, dict[str, str]] = {}


@router.post("/invite", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: InviteRequest,
    current_user: User = Depends(get_current_user),
) -> UserResponse:
    """Invite a new user to the current tenant.

    An inviter may only grant roles with a rank strictly lower than their own
    (F-11). This applies to all authenticated roles: a content_admin can invite
    analysts and read_only users; an analyst cannot invite anyone because no
    canonical role has a rank below theirs except read_only, and read_only has
    rank 20 < analyst rank 40, so analysts can invite read_only users.
    Roles with an unrecognised name resolve to rank 0 and are always blocked.
    """
    inviter_rank = _ROLE_RANK.get(current_user.role, 0)
    invitee_rank = _ROLE_RANK.get(payload.role, 0)
    if inviter_rank == 0 or invitee_rank >= inviter_rank:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Cannot invite a user to a role equal to or higher than your own",
        )

    existing = db.users.list(tenant_id=SYSTEM_TENANT_ID, filter_fn=lambda u: u.email == payload.email, allow_system_scope=True)
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="User with this email already exists",
        )

    user_id = str(uuid.uuid4())
    user = User(
        id=user_id,
        tenant_id=current_user.tenant_id,
        email=payload.email,
        name=payload.name,
        role=payload.role,
        status="invited",
        invited_by=current_user.id,
    )
    db.users.insert(user.id, user)

    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        tenant_id=user.tenant_id,
        status=user.status,
    )


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(payload: AcceptInviteRequest) -> TokenResponse:
    """Accept an invitation by setting a password and activating the account."""
    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))

    users = db.users.list(tenant_id=SYSTEM_TENANT_ID, filter_fn=lambda u: u.email == payload.email, allow_system_scope=True)
    if not users:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Invitation not found",
        )

    user = users[0]
    if user.status != "invited":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Invitation already accepted or account deactivated",
        )

    # Update user to active with password
    updated = user.model_copy(update={
        "status": "active",
        "password_hash": hash_password(payload.password),
        "name": payload.name,
    })
    db.users.insert(updated.id, updated)

    access_token = create_access_token(
        subject=updated.id,
        tenant_id=updated.tenant_id,
        # expires_delta=None → uses settings.access_token_expire_minutes (F-08)
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=get_settings().access_token_expire_minutes * 60,
    )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    request: Request,
    auth: TokenPayload = Depends(require_authenticated),
    _user: User = Depends(get_current_user),
) -> None:
    """Invalidate the current session via token blocklist until token expiry."""
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        return None
    raw_token = header.removeprefix("Bearer ").strip()
    if not raw_token:
        return None
    fingerprint_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()
    exp_dt = auth.exp
    expires_at_ts = int(exp_dt.timestamp()) if isinstance(exp_dt, datetime) else int(datetime.now(UTC).timestamp())
    revoke_token(
        tenant_id=auth.tenant_id,
        jti=auth.jti,
        fingerprint_hash=fingerprint_hash,
        expires_at_ts=expires_at_ts,
    )


@router.post("/impersonation/start", response_model=ImpersonationStartResponse)
async def start_impersonation(
    payload: ImpersonationStartRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> ImpersonationStartResponse:
    if current_user.role not in {"tenant_admin", "super_admin"}:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role for impersonation")
    target_user = db.users.get(payload.target_user_id, tenant_id=current_user.tenant_id)
    if target_user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Target user not found in tenant scope")
    if target_user.tenant_id != current_user.tenant_id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Cross-tenant impersonation is forbidden")

    session_id = str(uuid.uuid4())
    _IMPERSONATION_SESSIONS[session_id] = {
        "tenant_id": current_user.tenant_id,
        "target_user_id": target_user.id,
        "impersonated_by": current_user.id,
        "reason": payload.reason,
        "started_at": datetime.now(UTC).isoformat(),
        "notify_email": str(payload.notify_email),
        "notify_webhook": str(payload.notify_webhook),
    }
    event_payload = {
        "actor_user_id": current_user.id,
        "impersonated_user_id": target_user.id,
        "impersonated_tenant_id": target_user.tenant_id,
        "impersonated_by": current_user.id,
        "correlation_id": request.headers.get("X-Request-ID"),
        "timestamp": datetime.now(UTC).isoformat(),
        "action_code": "impersonation.start",
        "reason": payload.reason,
        "impersonation_session_id": session_id,
        "tenant_notifications": {
            "in_app": True,
            "email": payload.notify_email,
            "webhook": payload.notify_webhook,
        },
    }
    db.audit_logs.insert(str(uuid.uuid4()), AuditLogEvent(
        id=str(uuid.uuid4()),
        tenant_id=target_user.tenant_id,
        actor_type="user",
        actor_id=current_user.id,
        action="impersonation.start",
        resource_type="user",
        resource_id=target_user.id,
        payload=event_payload,
    ))
    token = create_access_token(
        subject=target_user.id,
        tenant_id=target_user.tenant_id,
        extra_claims={
            "impersonated_by": current_user.id,
            "impersonation_session_id": session_id,
            "impersonation_reason": payload.reason,
        },
    )
    return ImpersonationStartResponse(
        access_token=token,
        expires_in=get_settings().access_token_expire_minutes * 60,
        impersonation_session_id=session_id,
    )


@router.post("/impersonation/stop", status_code=status.HTTP_204_NO_CONTENT)
async def stop_impersonation(
    auth: TokenPayload = Depends(require_authenticated),
) -> None:
    if not auth.impersonation_session_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No active impersonation session")
    session = _IMPERSONATION_SESSIONS.pop(auth.impersonation_session_id, None)
    db.audit_logs.insert(str(uuid.uuid4()), AuditLogEvent(
        id=str(uuid.uuid4()),
        tenant_id=auth.tenant_id,
        actor_type="user",
        actor_id=auth.sub,
        action="impersonation.stop",
        resource_type="user",
        resource_id=session["target_user_id"] if session else auth.sub,
        payload={
            "actor_user_id": auth.sub,
            "impersonated_user_id": session["target_user_id"] if session else auth.sub,
            "impersonated_tenant_id": auth.tenant_id,
            "impersonated_by": auth.impersonated_by,
            "correlation_id": None,
            "timestamp": datetime.now(UTC).isoformat(),
            "action_code": "impersonation.stop",
            "reason": session["reason"] if session else auth.impersonation_reason,
            "impersonation_session_id": auth.impersonation_session_id,
            "tenant_notifications": {"in_app": True, "email": session["notify_email"] == "True" if session else False, "webhook": session["notify_webhook"] == "True" if session else False},
        },
    ))
    return None


@router.get("/me", response_model=UserResponse)
async def get_me(user: User = Depends(get_current_user)) -> UserResponse:
    """Return the currently authenticated user (requires valid JWT)."""
    return UserResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        tenant_id=user.tenant_id,
        status=user.status,
    )
