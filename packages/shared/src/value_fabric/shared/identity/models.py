"""Pydantic models for Tenant, User, and APIKey.

These are the canonical *data-transfer* models used for:
- API request / response payloads
- JWT claim validation
- In-memory representation after reading from the DB

The corresponding SQLAlchemy ORM models live in
``layer4-agents/src/tenants/models/``.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, FrozenSet, List, Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field, field_validator, model_validator

from ..testability import Clock, SystemClock
from .permissions import Permission, Role, ROLE_PERMISSIONS


# ---------------------------------------------------------------------------
# Token Claims (JWT)
# ---------------------------------------------------------------------------


class TokenClaims(BaseModel):
    """Validated JWT claims extracted from a token.

    This is the canonical representation of a verified JWT's payload,
    used after signature verification and claim validation.
    Supports both internal (HS256) and Keycloak (RS256) tokens.
    """

    sub: str = Field(..., description="Subject identifier (user ID)")
    tenant_id: Optional[str] = Field(None, description="Tenant identifier (L2 boundary)")
    org_id: Optional[str] = Field(None, description="Organization identifier (L1 billing entity)")
    workspace_id: Optional[str] = Field(None, description="Workspace identifier (L3 project)")
    roles: List[str] = Field(default_factory=list, description="User roles/permissions")
    email: Optional[str] = Field(None, description="User email from identity provider")
    name: Optional[str] = Field(None, description="User display name from identity provider")
    impersonator_id: Optional[str] = Field(None, description="Actor ID if this token was exchanged for impersonation")
    exp: Optional[int] = Field(None, description="Expiration timestamp (Unix epoch)")
    iat: Optional[int] = Field(None, description="Issued at timestamp (Unix epoch)")
    jti: Optional[str] = Field(None, description="JWT unique identifier")

    # Extra claims not in the standard set
    extra_claims: Dict[str, Any] = Field(default_factory=dict, description="Additional custom claims")


# ---------------------------------------------------------------------------
# Enumerations
# ---------------------------------------------------------------------------


class TenantStatus(str, Enum):
    """Lifecycle status of a tenant."""

    ACTIVE = "active"
    SUSPENDED = "suspended"
    DELETED = "deleted"


class UserStatus(str, Enum):
    """Lifecycle status of a user."""

    INVITED = "invited"
    ACTIVE = "active"
    DEACTIVATED = "deactivated"


# ---------------------------------------------------------------------------
# Tenant
# ---------------------------------------------------------------------------


class TenantModel(BaseModel):
    """Read-only representation of a tenant (returned by API)."""

    id: UUID = Field(default_factory=uuid4, description="Tenant UUID (PK)")
    name: str = Field(..., min_length=1, max_length=200, description="Display name")
    slug: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
        description="URL-safe unique identifier (lowercase kebab-case)",
    )
    status: TenantStatus = Field(default=TenantStatus.ACTIVE)
    settings: Dict[str, Any] = Field(default_factory=dict, description="Tenant-level config blob")
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class TenantCreateRequest(BaseModel):
    """Payload to create a new tenant (super_admin only)."""

    name: str = Field(..., min_length=1, max_length=200)
    slug: str = Field(
        ...,
        min_length=1,
        max_length=63,
        pattern=r"^[a-z0-9]+(?:-[a-z0-9]+)*$",
    )
    settings: Dict[str, Any] = Field(default_factory=dict)


class TenantUpdateRequest(BaseModel):
    """Payload to update tenant metadata."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    status: Optional[TenantStatus] = None
    settings: Optional[Dict[str, Any]] = None


# ---------------------------------------------------------------------------
# User
# ---------------------------------------------------------------------------


class UserModel(BaseModel):
    """Read-only representation of a user (returned by API — no password)."""

    id: UUID = Field(default_factory=uuid4)
    tenant_id: UUID = Field(..., description="Owning tenant")
    email: str = Field(..., description="Email address (unique within tenant)")
    display_name: Optional[str] = None
    role: Role = Field(default=Role.ANALYST)
    status: UserStatus = Field(default=UserStatus.INVITED)
    last_login_at: Optional[datetime] = None
    invited_by: Optional[UUID] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class UserInviteRequest(BaseModel):
    """Invite a new user to the tenant (tenant_admin only)."""

    email: str = Field(..., description="Email to invite")
    display_name: Optional[str] = None
    role: Role = Field(default=Role.ANALYST)

    @field_validator("role")
    @classmethod
    def role_cannot_be_super_admin(cls, v: Role) -> Role:
        if v == Role.SUPER_ADMIN:
            raise ValueError("Cannot invite a user with super_admin role via this endpoint")
        return v


class UserUpdateRequest(BaseModel):
    """Update a user's role or status."""

    display_name: Optional[str] = None
    role: Optional[Role] = None
    status: Optional[UserStatus] = None

    @field_validator("role")
    @classmethod
    def role_cannot_be_super_admin(cls, v: Optional[Role]) -> Optional[Role]:
        if v == Role.SUPER_ADMIN:
            raise ValueError("Cannot grant super_admin role via this endpoint")
        return v


class UserAcceptInviteRequest(BaseModel):
    """Accept an invitation by setting a password and activating the account."""

    token: str = Field(..., min_length=1, description="Invitation token from email")
    password: str = Field(..., min_length=12, description="Password for the new account")
    display_name: Optional[str] = None


# ---------------------------------------------------------------------------
# API Key
# ---------------------------------------------------------------------------


class APIKeyModel(BaseModel):
    """Read-only representation of an API key (never returns raw secret)."""

    key_id: str = Field(..., description="Unique identifier (vf_<uuid>)")
    tenant_id: UUID = Field(..., description="Owning tenant")
    user_id: Optional[UUID] = Field(None, description="Issuing user (None for system keys)")
    name: str = Field(..., min_length=1, max_length=100)
    prefix: str = Field(..., description="First 8 chars of the key for identification")
    role: Role
    permissions: FrozenSet[Permission]
    enabled: bool = True
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    expires_at: Optional[datetime] = None
    last_used_at: Optional[datetime] = None
    rate_limit_per_minute: Optional[int] = Field(
        None, ge=1, le=10_000, description="Per-key override; None inherits tenant limit"
    )
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def populate_permissions_from_role(cls, data: Any) -> Any:
        """Fill permissions from role if caller didn't supply them."""
        if isinstance(data, dict):
            if not data.get("permissions") and "role" in data:
                try:
                    role = Role(data["role"])
                    data["permissions"] = ROLE_PERMISSIONS[role].permissions
                except (ValueError, KeyError):
                    pass
        return data

    def has_permission(self, permission: Permission) -> bool:
        """Return True if this key carries the given permission."""
        return permission in self.permissions

    def is_expired(self, clock: Clock | None = None) -> bool:
        """Return True if this key has passed its expiry timestamp.

        Args:
            clock: Optional injectable clock.  Defaults to the system clock.
        """
        if self.expires_at is None:
            return False
        now = (clock or SystemClock()).now()
        return now > self.expires_at


class APIKeyCreateRequest(BaseModel):
    """Create a new persistent API key (tenant_admin only)."""

    name: str = Field(..., min_length=1, max_length=100)
    role: Role = Field(default=Role.ANALYST)
    permissions: Optional[FrozenSet[Permission]] = None
    expires_at: Optional[datetime] = None
    rate_limit_per_minute: Optional[int] = Field(None, ge=1, le=10_000)
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator("role")
    @classmethod
    def role_cannot_be_super_admin(cls, v: Role) -> Role:
        if v in (Role.SUPER_ADMIN, Role.SYSTEM):
            raise ValueError("Cannot create a key with super_admin or system role")
        return v


class APIKeyCreateResponse(BaseModel):
    """Returned once on key creation — includes the raw secret (shown only once)."""

    key_id: str
    tenant_id: UUID
    name: str
    api_key: str = Field(..., description="Full key — shown ONCE, store securely")
    prefix: str
    role: Role
    permissions: FrozenSet[Permission]
    expires_at: Optional[datetime]
    rate_limit_per_minute: Optional[int]
    created_at: datetime

# Merged from root shared/identity/models.py
class IsolationTier(str, Enum):
    """Tenant data isolation tier (Task 4.1).

    - SHARED: Shared schema with RLS (current)
    - SCHEMA: Dedicated schema per tenant (future)
    - DATABASE: Dedicated database per tenant (future)
    """

    SHARED = "shared"
    SCHEMA = "schema"
    DATABASE = "database"

class TenantSettings(BaseModel):
    """Tenant settings schema with isolation tier support."""

    isolation_tier: IsolationTier = Field(
        default=IsolationTier.SHARED,
        description="Data isolation tier: shared (RLS), schema (dedicated), or database (dedicated)",
    )
    rate_limits: dict[str, Any] | None = None
    feature_flags: dict[str, Any] | None = None
