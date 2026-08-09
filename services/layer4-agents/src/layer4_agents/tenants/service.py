from __future__ import annotations

"""Tenant Service — business logic for Tenant, User, and APIKey lifecycle.

This service is the single source of truth for:
- Creating / suspending / deleting tenants
- Inviting / activating / deactivating users
- Issuing / revoking API keys

All methods are async to integrate with SQLAlchemy's async session.
"""

import asyncio
import logging
import uuid
from datetime import UTC, datetime
from uuid import UUID

try:
    from value_fabric.shared.crypto import blind_index
    from value_fabric.shared.error_handling.exceptions import (
        AuthorizationError,
        ConflictError,
        TenantIsolationError,
        ValidationError,
    )
    from value_fabric.shared.identity.hashing import (
        extract_key_prefix,
        generate_api_key,
        hash_api_key,
    )
    from value_fabric.shared.identity.models import (
        APIKeyCreateRequest,
        APIKeyCreateResponse,
        APIKeyModel,
        TenantCreateRequest,
        TenantModel,
        TenantStatus,
        TenantUpdateRequest,
        UserAcceptInviteRequest,
        UserInviteRequest,
        UserModel,
        UserStatus,
        UserUpdateRequest,
    )
    from value_fabric.shared.identity.permissions import (
        ROLE_PERMISSIONS,
        Role,
        can_grant_role,
        get_role_rank,
    )
except ImportError as e:
    raise RuntimeError(
        "shared.identity package is required for tenant management. "
        "Install the shared package or set PYTHONPATH to include packages/shared/src/value_fabric/shared"
    ) from e
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel

try:
    from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event

    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False
    emit_audit_event = None  # type: ignore
    AuditAction = None  # type: ignore
    AuditOutcome = None  # type: ignore

from .invitations import InvitationService
from .models.api_key import APIKey
from .models.isolation_tier_history import TenantIsolationTierHistory
from .models.tenant import IsolationTier, Tenant
from .models.user import User
from .passwords import hash_password


class lookup_api_key_by_hashResult(TypedDictModel):
    enabled: Any
    key_id: Any
    permissions: Any
    rate_limit_per_minute: Any
    role: Any
    tenant_id: Any
    user_id: Any


logger = logging.getLogger(__name__)

# Task 4.1: Valid change sources for tier change audit logging
VALID_CHANGE_SOURCES = frozenset(
    {
        "system",
        "migration",
        "admin",
        "policy_engine",
        "api",
    }
)


# ---------------------------------------------------------------------------
# Tenant CRUD
# ---------------------------------------------------------------------------


async def create_tenant(db: AsyncSession, request: TenantCreateRequest) -> TenantModel:
    """Create a new tenant.  Caller must hold ADMIN_TENANTS permission."""
    tenant = Tenant(
        id=uuid.uuid4(),
        name=request.name,
        slug=request.slug,
        status=TenantStatus.ACTIVE.value,
        settings=request.settings,
    )
    db.add(tenant)
    await db.flush()
    logger.info("Created tenant %s (slug=%s)", tenant.id, tenant.slug)
    return _tenant_to_model(tenant)


async def get_tenant(db: AsyncSession, tenant_id: UUID) -> TenantModel | None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    return _tenant_to_model(tenant) if tenant else None


async def get_tenant_status(db: AsyncSession, tenant_id: UUID) -> str | None:
    """Get tenant status for middleware checks.

    Args:
        db: Database session
        tenant_id: Tenant UUID

    Returns:
        Tenant status string (active, suspended, pending, deleted) or None if not found
    """
    result = await db.execute(select(Tenant.status).where(Tenant.id == tenant_id))
    return result.scalar_one_or_none()


async def get_tenant_by_slug(db: AsyncSession, slug: str) -> TenantModel | None:
    """Get tenant by slug.

    Args:
        db: Database session
        slug: Tenant slug

    Returns:
        Tenant model or None if not found
    """
    result = await db.execute(select(Tenant).where(Tenant.slug == slug))
    tenant = result.scalar_one_or_none()
    return _tenant_to_model(tenant) if tenant else None


async def update_tenant_settings(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    name: str | None = None,
    settings_update: dict | None = None,
) -> TenantModel | None:
    """Update tenant settings.

    Args:
        db: Database session
        tenant_id: Tenant UUID
        name: New name (optional)
        settings_update: Settings to merge (optional)

    Returns:
        Updated tenant model or None if not found
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return None

    if name is not None:
        tenant.name = name

    if settings_update is not None:
        current_settings = tenant.settings or {}
        current_settings.update(settings_update)
        tenant.settings = current_settings

    tenant.updated_at = datetime.now(UTC)
    await db.flush()
    return _tenant_to_model(tenant)


async def count_users(db: AsyncSession, tenant_id: UUID) -> int:
    """Count active users in tenant for tier limit checking.

    Args:
        db: Database session
        tenant_id: Tenant UUID

    Returns:
        Number of active users
    """
    result = await db.execute(
        select(func.count()).where(User.tenant_id == tenant_id).where(User.status != "deleted")
    )
    return result.scalar() or 0


async def count_api_keys(db: AsyncSession, tenant_id: UUID) -> int:
    """Count enabled API keys in tenant for tier limit checking.

    Args:
        db: Database session
        tenant_id: Tenant UUID

    Returns:
        Number of enabled API keys
    """
    result = await db.execute(
        select(func.count()).where(APIKey.tenant_id == tenant_id).where(APIKey.enabled.is_(True))
    )
    return result.scalar() or 0


async def get_tier_api_key_limit(db: AsyncSession, tenant_id: UUID) -> int | None:
    """Get API key limit for tenant's tier.

    Args:
        db: Database session
        tenant_id: Tenant UUID

    Returns:
        API key limit or None for unlimited
    """
    from ...tiers import get_tier_limit

    tenant = await get_tenant(db, tenant_id)
    if not tenant:
        return None

    settings = tenant.settings or {}
    tier_id = settings.get("tier_id", "free")

    return get_tier_limit(tier_id, "max_users")  # Reuse max_users for API keys


async def get_tenant_settings(db: AsyncSession, tenant_id: UUID) -> dict | None:
    """Get tenant settings JSONB for rate limiting (Task 84).

    Args:
        db: Database session
        tenant_id: Tenant UUID

    Returns:
        Tenant settings dict or None if tenant not found
    """
    result = await db.execute(select(Tenant.settings).where(Tenant.id == tenant_id))
    settings = result.scalar_one_or_none()
    return settings if settings else {}


async def list_tenants(
    db: AsyncSession, *, status: str | None = None, limit: int = 100, offset: int = 0
) -> list[TenantModel]:
    q = select(Tenant).order_by(Tenant.created_at.desc()).limit(limit).offset(offset)
    if status:
        q = q.where(Tenant.status == status)
    result = await db.execute(q)
    return [_tenant_to_model(t) for t in result.scalars().all()]


async def update_tenant(
    db: AsyncSession, tenant_id: UUID, request: TenantUpdateRequest
) -> TenantModel | None:
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return None
    if request.name is not None:
        tenant.name = request.name
    if request.status is not None:
        tenant.status = request.status.value
    if request.settings is not None:
        tenant.settings = request.settings
    tenant.updated_at = datetime.now(UTC)
    await db.flush()
    return _tenant_to_model(tenant)


async def update_tenant_status(
    db: AsyncSession,
    tenant_id: UUID,
    status: str,
    *,
    reason: str | None = None,
    changed_by: str | None = None,
) -> bool:
    """Update tenant status with lifecycle validation and audit trail.

    Uses the ``Tenant.transition_to()`` state machine to ensure only valid
    transitions are executed.  Records ``status_changed_at``,
    ``status_reason``, and ``status_changed_by`` on the tenant row.

    Also updates the real-time kill-switch (Redis) so that in-flight
    requests, WebSockets, and background tasks are blocked immediately.

    Args:
        db: Database session
        tenant_id: UUID of tenant to update
        status: New status value (pending, active, suspended, deleted)
        reason: Optional reason for status change
        changed_by: User ID or service name that initiated the change

    Returns:
        True if status was updated, False if tenant not found

    Raises:
        ValueError: If the requested transition is invalid.
    """
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return False

    old_status = tenant.status
    tenant.transition_to(status, reason=reason, changed_by=changed_by)
    await db.flush()

    # Real-time kill-switch update
    try:
        from value_fabric.shared.tenant_kill_switch import TenantKillSwitch

        kill_switch = TenantKillSwitch()
        if status in ("suspended", "deleted"):
            await kill_switch.suspend(str(tenant_id))
        elif status == "active" and old_status in ("suspended", "deleted"):
            await kill_switch.unsuspend(str(tenant_id))
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        logger.warning("Kill-switch update failed for tenant %s: %s", tenant_id, exc)

    logger.info(
        "Updated tenant %s status: %s -> %s (reason: %s, by: %s)",
        tenant_id,
        old_status,
        status,
        reason or "unspecified",
        changed_by or "unknown",
    )
    return True


async def delete_tenant(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    reason: str | None = None,
    changed_by: str | None = None,
) -> bool:
    """Soft-delete by transitioning status to 'deleted' via the state machine."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return False
    tenant.transition_to(
        TenantStatus.DELETED.value,
        reason=reason or "soft-deleted",
        changed_by=changed_by,
    )
    await db.flush()
    logger.info("Soft-deleted tenant %s (reason: %s)", tenant_id, reason or "unspecified")
    return True


# ---------------------------------------------------------------------------
# Isolation Tier History (Task 4.1)
# ---------------------------------------------------------------------------


async def log_isolation_tier_change(
    db: AsyncSession,
    tenant_id: UUID,
    from_tier: str,
    to_tier: str,
    *,
    changed_by: UUID | None = None,
    reason: str | None = None,
    change_source: str = "admin",
    request_id: str | None = None,
) -> TenantIsolationTierHistory:
    """Log an isolation tier change to the audit history table.

    Args:
        db: Database session
        tenant_id: The tenant whose tier changed
        from_tier: Previous tier value
        to_tier: New tier value
        changed_by: User or service account that made the change
        reason: Human-readable reason for the change
        change_source: Source of change (system, migration, admin, policy_engine, api)
        request_id: Request ID for correlation with audit logs

    Returns:
        The created history record

    Raises:
        ValueError: If change_source is not valid or tier values are invalid
    """
    # P1: Validate change_source against allowed values
    if change_source not in VALID_CHANGE_SOURCES:
        raise ValueError(
            f"Invalid change_source: {change_source}. "
            f"Must be one of: {', '.join(sorted(VALID_CHANGE_SOURCES))}"
        )

    # P1: Validate tier values
    valid_tiers = {t.value for t in IsolationTier}
    if from_tier not in valid_tiers:
        raise ValueError(
            f"Invalid from_tier: {from_tier}. Must be one of: {', '.join(sorted(valid_tiers))}"
        )
    if to_tier not in valid_tiers:
        raise ValueError(
            f"Invalid to_tier: {to_tier}. Must be one of: {', '.join(sorted(valid_tiers))}"
        )

    history = TenantIsolationTierHistory(
        tenant_id=tenant_id,
        from_tier=from_tier,
        to_tier=to_tier,
        changed_by=changed_by,
        reason=reason,
        change_source=change_source,
        request_id=request_id,
    )
    db.add(history)
    await db.flush()
    logger.info(
        "Logged isolation tier change for tenant %s: %s -> %s (by=%s, source=%s)",
        tenant_id,
        from_tier,
        to_tier,
        changed_by,
        change_source,
    )
    return history


async def update_tenant_isolation_tier(
    db: AsyncSession,
    tenant_id: UUID,
    new_tier: str,
    *,
    changed_by: UUID | None = None,
    reason: str | None = None,
    change_source: str = "admin",
    request_id: str | None = None,
) -> TenantModel | None:
    """Update tenant isolation tier with full audit logging.

    This is the preferred method for changing isolation tiers as it
    ensures proper audit trail logging.

    Args:
        db: Database session
        tenant_id: The tenant to update
        new_tier: New isolation tier (shared, schema, database)
        changed_by: Who made the change
        reason: Why the change was made
        change_source: Source of the change
        request_id: Request ID for audit correlation

    Returns:
        Updated tenant model or None if tenant not found
    """
    # Validate tier
    if new_tier not in [t.value for t in IsolationTier]:
        raise ValueError(f"Invalid isolation tier: {new_tier}")

    # Get current tenant
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        return None

    # Get current tier from settings
    current_settings = tenant.settings or {}
    old_tier = current_settings.get("isolation_tier", IsolationTier.SHARED.value)

    # Only log if actually changing
    if old_tier != new_tier:
        # Update settings
        current_settings["isolation_tier"] = new_tier
        tenant.settings = current_settings
        tenant.updated_at = datetime.now(UTC)

        # Log the change
        await log_isolation_tier_change(
            db,
            tenant_id,
            old_tier,
            new_tier,
            changed_by=changed_by,
            reason=reason,
            change_source=change_source,
            request_id=request_id,
        )
        await db.flush()

        logger.info(
            "Updated tenant %s isolation tier: %s -> %s",
            tenant_id,
            old_tier,
            new_tier,
        )

    return _tenant_to_model(tenant)


# ---------------------------------------------------------------------------
# User management
# ---------------------------------------------------------------------------


async def invite_user(
    db: AsyncSession,
    tenant_id: UUID,
    request: UserInviteRequest,
    invited_by: UUID | None = None,
    inviter_roles: list[str] | None = None,
    invitation_service: InvitationService | None = None,
) -> tuple[UserModel, str]:
    """Invite a new user to the tenant.  Caller must hold ADMIN_USERS permission.

    Enforces:
    - Role escalation guard: inviter may only grant roles strictly below their
      own highest-ranked role (F-11).
    - Cross-tenant email uniqueness: the email must not already exist in any
      tenant.

    Returns:
        Tuple of (user_model, invitation_token).
    """
    # F-11: Role escalation guard
    if inviter_roles:
        inviter_highest = max(inviter_roles, key=get_role_rank)
        if not can_grant_role(inviter_highest, request.role):
            raise AuthorizationError(
                message="Cannot invite a user to a role equal to or higher than your own"
            )

    # Cross-tenant email uniqueness check
    email_hash = blind_index(request.email)
    result = await db.execute(select(User).where(User.email_hash == email_hash))
    existing = result.scalar_one_or_none()
    if existing:
        raise ConflictError(message="User with this email already exists")

    user = User(
        id=uuid.uuid4(),
        tenant_id=tenant_id,
        email=request.email,
        display_name=request.display_name,
        role=request.role.value,
        status=UserStatus.INVITED.value,
        invited_by=invited_by,
    )
    db.add(user)
    await db.flush()

    # Generate invitation token
    token = ""
    if invitation_service is not None:
        token = invitation_service.generate_token(tenant_id, user.id, request.email)

    logger.info("Invited user %s to tenant %s", request.email, tenant_id)
    return _user_to_model(user), token


async def accept_invitation(
    db: AsyncSession,
    request: UserAcceptInviteRequest,
    invitation_service: InvitationService,
) -> UserModel:
    """Accept an invitation by setting a password and activating the account.

    All failure modes (invalid/expired/consumed token, user not found, already
    accepted) return a uniform 401 to prevent information leakage.

    Args:
        db: Database session
        request: Accept invite request with token, password, and optional display_name
        invitation_service: Service for verifying invitation tokens

    Returns:
        Activated user model

    Raises:
        HTTPException: 401 for any token/user/state failure; 400 for bad password
    """
    from fastapi import HTTPException, status

    _auth_fail = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired invitation token",
    )

    # Atomically verify and consume the invitation token (GETDEL)
    token_data = await invitation_service.verify_token(request.token)
    if not token_data:
        raise _auth_fail

    # Look up user
    result = await db.execute(
        select(User).where(User.id == token_data.user_id, User.tenant_id == token_data.tenant_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise _auth_fail

    if user.status != UserStatus.INVITED.value:
        raise _auth_fail

    # Validate and hash password
    try:
        from .passwords import PasswordTooLongError

        hashed = hash_password(request.password)
    except (ValueError, PasswordTooLongError) as exc:
        raise ValidationError(message=f"Password does not meet requirements: {exc}") from exc

    # Activate user
    user.hashed_password = hashed
    user.status = UserStatus.ACTIVE.value
    if request.display_name is not None:
        user.display_name = request.display_name
    user.updated_at = datetime.now(UTC)
    await db.flush()

    # Consume the token only after successful activation
    await invitation_service.consume_token(request.token)

    logger.info("User %s accepted invitation in tenant %s", user.id, user.tenant_id)
    return _user_to_model(user)


async def get_user(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> UserModel | None:
    result = await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    user = result.scalar_one_or_none()
    return _user_to_model(user) if user else None


async def list_users(
    db: AsyncSession, tenant_id: UUID, *, limit: int = 100, offset: int = 0
) -> list[UserModel]:
    result = await db.execute(
        select(User)
        .where(User.tenant_id == tenant_id)
        .order_by(User.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return [_user_to_model(u) for u in result.scalars().all()]


async def update_user(
    db: AsyncSession, tenant_id: UUID, user_id: UUID, request: UserUpdateRequest
) -> UserModel | None:
    result = await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    user = result.scalar_one_or_none()
    if not user:
        return None
    if request.display_name is not None:
        user.display_name = request.display_name
    if request.role is not None:
        user.role = request.role.value
    if request.status is not None:
        user.status = request.status.value
    user.updated_at = datetime.now(UTC)
    await db.flush()
    return _user_to_model(user)


async def deactivate_user(db: AsyncSession, tenant_id: UUID, user_id: UUID) -> bool:
    result = await db.execute(select(User).where(User.id == user_id, User.tenant_id == tenant_id))
    user = result.scalar_one_or_none()
    if not user:
        return False
    user.status = UserStatus.DEACTIVATED.value
    user.updated_at = datetime.now(UTC)
    await db.flush()
    logger.info("Deactivated user %s in tenant %s", user_id, tenant_id)
    return True


# ---------------------------------------------------------------------------
# API key management
# ---------------------------------------------------------------------------


async def create_api_key(
    db: AsyncSession,
    tenant_id: UUID,
    request: APIKeyCreateRequest,
    *,
    user_id: UUID | None = None,
    creator_role: Role | str | None = None,
) -> APIKeyCreateResponse:
    """Issue a new API key.  Caller must hold ADMIN_API_KEYS permission.

    The raw key is returned **once** and never stored.  The HMAC-SHA256
    digest is stored in the database.

    Role constraint: the creator's effective role must outrank the requested
    key role (``can_grant_role``).  Low-privilege users cannot mint
    higher-privilege keys.
    """
    if creator_role is not None and not can_grant_role(creator_role, request.role):
        raise AuthorizationError(
            message=f"Cannot create API key with role {request.role.value}; "
            f"your role does not authorize granting that role."
        )

    # Tenant-scoped guard: the issuing user must exist in the target tenant.
    # This prevents service callers from minting a key for an arbitrary tenant
    # while attributing it to a user from another tenant.
    if user_id is not None:
        user_belongs = await db.execute(
            select(User).where(User.id == user_id, User.tenant_id == tenant_id)
        )
        if user_belongs.scalar_one_or_none() is None:
            raise TenantIsolationError(
                message="API key creator does not belong to the requested tenant"
            )

    raw_key = generate_api_key()
    key_hash = hash_api_key(raw_key)
    prefix = extract_key_prefix(raw_key)
    key_id = f"vf_{uuid.uuid4().hex}"

    permissions = request.permissions
    if not permissions:
        permissions = ROLE_PERMISSIONS[request.role].permissions

    key = APIKey(
        key_id=key_id,
        tenant_id=tenant_id,
        user_id=user_id,
        creator_user_id=user_id,
        name=request.name,
        key_hash=key_hash,
        prefix=prefix,
        role=request.role.value,
        permissions=[p.value for p in permissions],
        enabled=True,
        expires_at=request.expires_at,
        rate_limit_per_minute=request.rate_limit_per_minute,
        metadata_=request.metadata,
    )
    db.add(key)
    await db.flush()
    logger.info("Created API key %s for tenant %s", key_id, tenant_id)

    return APIKeyCreateResponse(
        key_id=key_id,
        tenant_id=tenant_id,
        name=request.name,
        api_key=raw_key,
        prefix=prefix,
        role=request.role,
        permissions=frozenset(permissions),
        expires_at=request.expires_at,
        rate_limit_per_minute=request.rate_limit_per_minute,
        created_at=key.created_at,
    )


async def list_api_keys(
    db: AsyncSession, tenant_id: UUID, *, active_only: bool = True
) -> list[APIKeyModel]:
    """List API keys for a tenant.

    By default returns only active (non-revoked, non-expired) keys. Set
    ``active_only=False`` to include revoked/expired keys for audit/history.
    """
    q = select(APIKey).where(APIKey.tenant_id == tenant_id)
    if active_only:
        q = q.where(
            APIKey.enabled.is_(True),
            APIKey.revoked_at.is_(None),
            (APIKey.expires_at.is_(None) | (APIKey.expires_at > datetime.now(UTC))),
        )
    result = await db.execute(q.order_by(APIKey.created_at.desc()))
    return [_api_key_to_model(k) for k in result.scalars().all()]


async def revoke_api_key(db: AsyncSession, tenant_id: UUID, key_id: str) -> bool:
    """Disable (soft-delete) an API key.

    Idempotent: revoking an already-revoked key returns True.
    """
    result = await db.execute(
        select(APIKey).where(APIKey.key_id == key_id, APIKey.tenant_id == tenant_id)
    )
    key = result.scalar_one_or_none()
    if not key:
        return False
    if key.is_revoked():
        return True
    key.enabled = False
    key.revoked_at = datetime.now(UTC)
    await db.flush()
    logger.info("Revoked API key %s for tenant %s", key_id, tenant_id)
    return True


async def lookup_api_key_by_hash(db: AsyncSession, raw_key: str) -> dict | None:
    """Look up an API key record by its raw value (for GovernanceMiddleware).

    Returns a dict suitable for ``GovernanceMiddleware``'s ``api_key_resolver``
    or ``None`` if the key is not found / revoked / expired.  On a successful
    lookup updates ``last_used_at`` and emits an ``api_key.used`` audit event.
    """
    key_hash = hash_api_key(raw_key)
    result = await db.execute(select(APIKey).where(APIKey.key_hash == key_hash))
    key = result.scalar_one_or_none()
    if not key or not key.is_active():
        return None

    now = datetime.now(UTC)
    key.last_used_at = now

    if AUDIT_AVAILABLE and emit_audit_event:
        try:
            await emit_audit_event(
                action=AuditAction.API_KEY_USED,
                outcome=AuditOutcome.SUCCESS,
                actor_id=str(key.user_id) if key.user_id else None,
                tenant_id=str(key.tenant_id),
                resource_type="api_key",
                resource_id=key.key_id,
                details={"last_used_at": now.isoformat()},
            )
        except asyncio.CancelledError:
            raise
        except Exception:
            logger.warning("Failed to emit api_key.used audit event", exc_info=True)

    return lookup_api_key_by_hashResult.model_validate(
        {
            "key_id": key.key_id,
            "tenant_id": str(key.tenant_id),
            "user_id": str(key.user_id) if key.user_id else None,
            "role": key.role,
            "permissions": key.permissions,
            "enabled": key.enabled and not key.is_revoked(),
            "rate_limit_per_minute": key.rate_limit_per_minute,
        }
    )


# ---------------------------------------------------------------------------
# Private converters
# ---------------------------------------------------------------------------


def _tenant_to_model(t: Tenant) -> TenantModel:
    return TenantModel(
        id=t.id,
        name=t.name,
        slug=t.slug,
        status=t.status,
        settings=t.settings or {},
        created_at=t.created_at,
        updated_at=t.updated_at,
    )


def _user_to_model(u: User) -> UserModel:
    return UserModel(
        id=u.id,
        tenant_id=u.tenant_id,
        email=u.email,
        display_name=u.display_name,
        role=u.role,
        status=u.status,
        last_login_at=u.last_login_at,
        invited_by=u.invited_by,
        created_at=u.created_at,
        updated_at=u.updated_at,
    )


def _api_key_to_model(k: APIKey) -> APIKeyModel:
    from value_fabric.shared.identity.permissions import Permission

    perms: frozenset = frozenset()
    if k.permissions:
        perms = frozenset(
            Permission(p) for p in k.permissions if p in Permission._value2member_map_
        )

    return APIKeyModel(
        key_id=k.key_id,
        tenant_id=k.tenant_id,
        user_id=k.user_id,
        name=k.name,
        prefix=k.prefix,
        role=k.role,
        permissions=perms,
        enabled=k.enabled and not k.is_revoked(),
        revoked_at=k.revoked_at,
        created_at=k.created_at,
        expires_at=k.expires_at,
        last_used_at=k.last_used_at,
        rate_limit_per_minute=k.rate_limit_per_minute,
        metadata=k.metadata_ or {},
    )
