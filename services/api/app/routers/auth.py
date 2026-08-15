"""Authentication router for signup, login, and token management."""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid

from datetime import UTC, datetime, timedelta
from typing import Literal

import structlog
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, EmailStr
from value_fabric.shared.error_handling.exceptions import AuthorizationError, BadRequestError, ConflictError, NotFoundError, RateLimitError, ServiceUnavailableError, ValidationError

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
from app.repositories.session_store import ImpersonationSessionRepository
from app.services.distributed_store import StorePayloadError, StoreUnavailableError, get_distributed_store
router = APIRouter(prefix="/auth", tags=["Authentication"])
logger = structlog.get_logger(__name__)


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
    # The single-use invite token issued by POST /v1/auth/invite. The email is
    # deliberately NOT part of this schema: binding acceptance to possession of
    # the token (not knowledge of the email) closes the unauthenticated
    # cross-tenant account-takeover vector.
    token: str
    password: str
    name: str


class UserResponse(BaseModel):
    id: str
    email: str
    name: str
    role: str
    tenant_id: str
    status: str


class InviteResponse(UserResponse):
    """Response returned once when an invitation is created.

    ``invite_token`` is the plaintext single-use invite secret. It is returned
    exactly once in this response; only its SHA-256 hash (plus expiry) is
    persisted on the invited user's record. Production delivery of the token
    to the invitee is via email (out of scope for this service); returning it
    here is the development/test delivery channel.
    """

    invite_token: str


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
# Invite token helpers
# ---------------------------------------------------------------------------


def _hash_invite_token(token: str) -> str:
    """Return the SHA-256 hex digest of a plaintext invite token.

    Only this digest is ever persisted; the plaintext token is returned once
    at invite creation time and delivered to the invitee out-of-band.
    """
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# Uniform rejection for every accept-invite failure mode (unknown token,
# expired token, already-consumed token, account not in "invited" status).
# Returning a single indistinguishable 401 prevents the endpoint from being
# used as a cross-tenant email census or invitation-state oracle.
_INVALID_INVITE = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail="Invalid or expired invitation token",
    headers={"WWW-Authenticate": "Bearer"},
)


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
        logger.warning("Password strength validation failed", error=str(exc))
        raise ValidationError(message="Password does not meet strength requirements") from exc

    # Cross-tenant email uniqueness check — requires explicit allow_system_scope
    # so the bypass cannot be triggered by an arbitrary caller passing "system".
    existing = db.users.list(tenant_id=SYSTEM_TENANT_ID, filter_fn=lambda u: u.email == payload.email, allow_system_scope=True)
    if existing:
        raise ConflictError(message="An account with this email already exists")

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
        raise RateLimitError(message="Account temporarily locked due to repeated failed login attempts. Try again later.")

    if user.status == "invited":
        raise AuthorizationError(message="Account pending activation. Please accept your invitation.")
    if user.status == "deactivated":
        raise AuthorizationError(message="Account deactivated. Contact your tenant administrator.")
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



def get_impersonation_repo() -> ImpersonationSessionRepository:
    return ImpersonationSessionRepository(get_distributed_store())


@router.post("/invite", response_model=InviteResponse, status_code=status.HTTP_201_CREATED)
async def invite_user(
    payload: InviteRequest,
    current_user: User = Depends(get_current_user),
) -> InviteResponse:
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
        raise AuthorizationError(message="Cannot invite a user to a role equal to or higher than your own")

    existing = db.users.list(tenant_id=SYSTEM_TENANT_ID, filter_fn=lambda u: u.email == payload.email, allow_system_scope=True)
    if existing:
        raise ConflictError(message="User with this email already exists")

    # Issue a cryptographically random, single-use invite token. Only its
    # SHA-256 hash and expiry are persisted; the plaintext is returned once
    # below (production delivery to the invitee is via email — out of scope).
    invite_token = secrets.token_urlsafe(32)
    invite_expires_at = datetime.now(UTC) + timedelta(
        hours=get_settings().invite_token_expire_hours
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
        invite_token_hash=_hash_invite_token(invite_token),
        invite_token_expires_at=invite_expires_at.isoformat(),
    )
    db.users.insert(user.id, user)

    return InviteResponse(
        id=user.id,
        email=user.email,
        name=user.name,
        role=user.role,
        tenant_id=user.tenant_id,
        status=user.status,
        invite_token=invite_token,
    )


@router.post("/accept-invite", response_model=TokenResponse)
async def accept_invite(payload: AcceptInviteRequest) -> TokenResponse:
    """Accept an invitation with the single-use invite token.

    The presented token is SHA-256 hashed and matched against the stored hash
    on the invited user's record — never by email. Every failure mode (unknown
    token, expired token, already-consumed token, non-invited account) returns
    the same uniform 401 so the endpoint cannot be used as a cross-tenant
    email census or invitation-state oracle. On success the token is consumed
    (cleared) so it can never be replayed.
    """
    # Reject unusable tokens before any other work. A missing/empty token can
    # never match a stored hash, and rejecting it here keeps the failure
    # indistinguishable from any other invalid-token rejection.
    if not payload.token:
        raise _INVALID_INVITE

    token_hash = _hash_invite_token(payload.token)
    # Cross-tenant lookup keyed ONLY by the token hash (constant-time
    # compare). Knowing a victim's email is useless without the token, which
    # closes the unauthenticated account-takeover vector.
    users = db.users.list(
        tenant_id=SYSTEM_TENANT_ID,
        filter_fn=lambda u: (
            u.invite_token_hash is not None
            and hmac.compare_digest(u.invite_token_hash, token_hash)
        ),
        allow_system_scope=True,
    )
    if not users:
        raise _INVALID_INVITE

    user = users[0]
    if user.status != "invited":
        raise _INVALID_INVITE

    if not user.invite_token_expires_at:
        raise _INVALID_INVITE
    try:
        expires_at = datetime.fromisoformat(user.invite_token_expires_at)
    except ValueError:
        raise _INVALID_INVITE from None
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=UTC)
    if datetime.now(UTC) >= expires_at:
        raise _INVALID_INVITE

    try:
        validate_password_strength(payload.password)
    except ValueError as exc:
        logger.warning("Password strength validation failed", error=str(exc))
        raise ValidationError(message="Password does not meet strength requirements") from exc

    # Activate the account and consume the token (single-use): clearing the
    # hash and expiry makes any replay of the same token fail as unknown.
    updated = user.model_copy(update={
        "status": "active",
        "password_hash": hash_password(payload.password),
        "name": payload.name,
        "invite_token_hash": None,
        "invite_token_expires_at": None,
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
    repo: ImpersonationSessionRepository = Depends(get_impersonation_repo),
) -> ImpersonationStartResponse:
    if current_user.role not in {"tenant_admin", "super_admin"}:
        raise AuthorizationError(message="Insufficient role for impersonation")
    target_user = db.users.get(payload.target_user_id, tenant_id=current_user.tenant_id)
    if target_user is None:
        raise NotFoundError(message="Target user not found in tenant scope")
    if target_user.tenant_id != current_user.tenant_id:
        raise AuthorizationError(message="Cross-tenant impersonation is forbidden")

    session_id = str(uuid.uuid4())
    try:
        repo.create(
            tenant_id=current_user.tenant_id,
            session_id=session_id,
            target_user_id=target_user.id,
            impersonated_by=current_user.id,
            reason=payload.reason,
            notify_email=payload.notify_email,
            notify_webhook=payload.notify_webhook,
        )
    except (StoreUnavailableError, StorePayloadError):
        raise ServiceUnavailableError(message="Impersonation store unavailable")
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
    audit_event_id = str(uuid.uuid4())
    db.audit_logs.insert(audit_event_id, AuditLogEvent(
        id=audit_event_id,
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
    request: Request,
    auth: TokenPayload = Depends(require_authenticated),
    repo: ImpersonationSessionRepository = Depends(get_impersonation_repo),
) -> None:
    if not auth.impersonation_session_id:
        raise BadRequestError(message="No active impersonation session")
    try:
        session = repo.pop(tenant_id=auth.tenant_id, session_id=auth.impersonation_session_id)
    except (StoreUnavailableError, StorePayloadError):
        raise ServiceUnavailableError(message="Impersonation store unavailable")
    stop_event_id = str(uuid.uuid4())
    db.audit_logs.insert(stop_event_id, AuditLogEvent(
        id=stop_event_id,
        tenant_id=auth.tenant_id,
        actor_type="user",
        actor_id=auth.sub,
        action="impersonation.stop",
        resource_type="user",
        resource_id=session["target_user_id"] if session else auth.sub,
        payload={
            "actor_user_id": auth.sub,
            "impersonated_user_id": str(session.get("target_user_id")) if session else auth.sub,
            "impersonated_tenant_id": auth.tenant_id,
            "impersonated_by": auth.impersonated_by,
            "correlation_id": request.headers.get("X-Request-ID"),
            "timestamp": datetime.now(UTC).isoformat(),
            "action_code": "impersonation.stop",
            "reason": str(session.get("reason")) if session else auth.impersonation_reason,
            "impersonation_session_id": auth.impersonation_session_id,
            "tenant_notifications": {"in_app": True, "email": bool(session.get("notify_email")) if session else False, "webhook": bool(session.get("notify_webhook")) if session else False},
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
