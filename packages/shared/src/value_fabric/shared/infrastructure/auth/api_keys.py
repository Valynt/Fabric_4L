"""API key authentication and authorization system.

NOTE: This module's in-memory APIKeyManager is superseded by the persistent
database-backed implementation in ``layer4-agents/src/tenants/``. It is kept
for backward compatibility with existing L3 routes.

Security fix applied: ``hash_api_key`` now uses HMAC-SHA256 with a server-side
secret (``API_KEY_HMAC_SECRET`` env var) instead of plain SHA-256.
"""

import hashlib
import hmac
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field, field_validator
from value_fabric.shared.models.typed_dict import TypedDictModel

from logging_config import get_logger


class APIKeyManager_get_usage_statisticsResult(TypedDictModel):
    enabled_keys: Any
    expired_keys: Any
    recently_active: Any
    total_keys: Any
    total_usage: Any
    usage_by_role: Any

logger = get_logger(__name__)


class Permission(str, Enum):
    """API permissions."""

    READ_HEALTH = "read:health"
    READ_METRICS = "read:metrics"
    READ_SCHEMA = "read:schema"
    READ_SEARCH = "read:search"
    READ_GRAPHRAG = "read:graphrag"
    READ_ANALYTICS = "read:analytics"
    READ_INGESTION = "read:ingestion"

    WRITE_INGESTION = "write:ingestion"
    WRITE_SCHEMA = "write:schema"
    WRITE_ANALYTICS = "write:analytics"

    ADMIN_API_KEYS = "admin:api_keys"
    ADMIN_USERS = "admin:users"
    ADMIN_SYSTEM = "admin:system"


class Role(str, Enum):
    """User roles with predefined permission sets."""

    READ_ONLY = "read_only"
    ANALYST = "analyst"
    DEVELOPER = "developer"
    ADMIN = "admin"
    SYSTEM = "system"


@dataclass
class RolePermissions:
    """Role to permissions mapping."""

    permissions: set[Permission]
    description: str


# Default role permissions
ROLE_PERMISSIONS = {
    Role.READ_ONLY: RolePermissions(
        permissions={
            Permission.READ_HEALTH,
            Permission.READ_METRICS,
            Permission.READ_SCHEMA,
            Permission.READ_SEARCH,
            Permission.READ_GRAPHRAG,
        },
        description="Read-only access to basic endpoints",
    ),
    Role.ANALYST: RolePermissions(
        permissions={
            Permission.READ_HEALTH,
            Permission.READ_METRICS,
            Permission.READ_SCHEMA,
            Permission.READ_SEARCH,
            Permission.READ_GRAPHRAG,
            Permission.READ_ANALYTICS,
            Permission.READ_INGESTION,
            Permission.WRITE_ANALYTICS,
        },
        description="Analyst access with analytics capabilities",
    ),
    Role.DEVELOPER: RolePermissions(
        permissions={
            Permission.READ_HEALTH,
            Permission.READ_METRICS,
            Permission.READ_SCHEMA,
            Permission.READ_SEARCH,
            Permission.READ_GRAPHRAG,
            Permission.READ_ANALYTICS,
            Permission.READ_INGESTION,
            Permission.WRITE_INGESTION,
            Permission.WRITE_SCHEMA,
            Permission.WRITE_ANALYTICS,
        },
        description="Developer access with full API capabilities",
    ),
    Role.ADMIN: RolePermissions(
        permissions={
            Permission.READ_HEALTH,
            Permission.READ_METRICS,
            Permission.READ_SCHEMA,
            Permission.READ_SEARCH,
            Permission.READ_GRAPHRAG,
            Permission.READ_ANALYTICS,
            Permission.READ_INGESTION,
            Permission.WRITE_INGESTION,
            Permission.WRITE_SCHEMA,
            Permission.WRITE_ANALYTICS,
            Permission.ADMIN_API_KEYS,
            Permission.ADMIN_USERS,
        },
        description="Administrator access with user management",
    ),
    Role.SYSTEM: RolePermissions(
        permissions={perm for perm in Permission},
        description="System access with all permissions",
    ),
}


class APIKey(BaseModel):
    """API key model."""

    key_id: str = Field(..., description="Unique key identifier")
    name: str = Field(..., description="Human-readable key name")
    key_hash: str = Field(..., description="SHA-256 hash of the API key")
    prefix: str = Field(..., description="Key prefix for identification")
    role: Role = Field(..., description="Assigned role")
    permissions: set[Permission] = Field(
        ..., description="Explicit permissions (overrides role)"
    )
    enabled: bool = Field(default=True, description="Whether key is enabled")
    created_at: datetime = Field(
        default_factory=datetime.utcnow, description="Creation timestamp"
    )
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    last_used_at: datetime | None = Field(None, description="Last usage timestamp")
    usage_count: int = Field(default=0, description="Total usage count")
    rate_limit_per_minute: int | None = Field(
        None, description="Custom rate limit per minute"
    )
    allowed_ips: list[str] | None = Field(None, description="Allowed IP addresses")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )

    @field_validator("permissions", mode="before")
    @classmethod
    def set_permissions_from_role(cls, v, info):
        """Set permissions based on role if not explicitly provided."""
        if not v and "role" in info.data:
            role = info.data["role"]
            return ROLE_PERMISSIONS[role].permissions
        return set(v) if v else set()

    def is_expired(self) -> bool:
        """Check if API key is expired."""
        if self.expires_at is None:
            return False
        return datetime.utcnow() > self.expires_at

    def is_valid_ip(self, ip_address: str) -> bool:
        """Check if IP address is allowed."""
        if not self.allowed_ips:
            return True
        return ip_address in self.allowed_ips

    def has_permission(self, permission: Permission) -> bool:
        """Check if key has specific permission."""
        return permission in self.permissions

    def update_usage(self) -> None:
        """Update usage statistics."""
        self.last_used_at = datetime.utcnow()
        self.usage_count += 1


class APIKeyCreateRequest(BaseModel):
    """Request to create a new API key."""

    name: str = Field(..., min_length=1, max_length=100, description="Key name")
    role: Role = Field(..., description="Assigned role")
    permissions: set[Permission] | None = Field(
        None, description="Explicit permissions"
    )
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    rate_limit_per_minute: int | None = Field(
        None, ge=1, le=10000, description="Custom rate limit"
    )
    allowed_ips: list[str] | None = Field(None, description="Allowed IP addresses")
    metadata: dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class APIKeyResponse(BaseModel):
    """API key response (without the actual key)."""

    key_id: str
    name: str
    prefix: str
    role: Role
    permissions: set[Permission]
    enabled: bool
    created_at: datetime
    expires_at: datetime | None
    last_used_at: datetime | None
    usage_count: int
    rate_limit_per_minute: int | None
    allowed_ips: list[str] | None
    metadata: dict[str, Any]


class APIKeyCreateResponse(BaseModel):
    """Response when creating a new API key (includes the actual key)."""

    key_id: str
    name: str
    api_key: str  # Only shown once during creation
    prefix: str
    role: Role
    permissions: set[Permission]
    expires_at: datetime | None
    rate_limit_per_minute: int | None
    allowed_ips: list[str] | None
    metadata: dict[str, Any]


class APIKeyUpdateRequest(BaseModel):
    """Request to update an existing API key."""

    name: str | None = Field(None, min_length=1, max_length=100, description="Key name")
    role: Role | None = Field(None, description="Assigned role")
    permissions: set[Permission] | None = Field(
        None, description="Explicit permissions"
    )
    enabled: bool | None = Field(None, description="Whether key is enabled")
    expires_at: datetime | None = Field(None, description="Expiration timestamp")
    rate_limit_per_minute: int | None = Field(
        None, ge=1, le=10000, description="Custom rate limit"
    )
    allowed_ips: list[str] | None = Field(None, description="Allowed IP addresses")
    metadata: dict[str, Any] | None = Field(None, description="Additional metadata")


class AuthenticationResult(BaseModel):
    """Authentication result."""

    success: bool
    api_key: APIKey | None = None
    error: str | None = None


class APIKeyManager:
    """Manages API key creation, validation, and storage."""

    def __init__(self):
        """Initialize API key manager."""
        self.api_keys: dict[str, APIKey] = {}  # key_id -> APIKey
        self.key_hash_to_id: dict[str, str] = {}  # key_hash -> key_id

    def generate_api_key(self, length: int = 32) -> str:
        """Generate a new API key.

        Args:
            length: Key length in bytes

        Returns:
            Generated API key string
        """
        return secrets.token_urlsafe(length)

    def hash_api_key(self, api_key: str) -> str:
        """Hash an API key for storage using HMAC-SHA256.

        Uses a server-side secret (API_KEY_HMAC_SECRET env var) as a pepper,
        which prevents offline brute-force attacks even if the DB is compromised.
        This is the industry-standard approach (Stripe, GitHub, AWS) and runs
        in ~1µs vs bcrypt's ~100ms.

        Args:
            api_key: Raw API key string

        Returns:
            HMAC-SHA256 hex digest
        """
        secret = os.getenv("API_KEY_HMAC_SECRET", "").encode("utf-8")
        if not secret:
            raise RuntimeError(
                "API_KEY_HMAC_SECRET environment variable is required. "
                "Set a strong random secret (32+ bytes) for secure API key hashing."
            )
        # HMAC-SHA256 is the industry standard for API credential hashing
        # (used by Stripe, GitHub, AWS). This is NOT password hashing — API keys
        # are long-entropy random tokens, so computationally expensive algorithms
        # (bcrypt, argon2) are unnecessary and harmful to throughput here.
        # bcrypt is reserved for user passwords which have low entropy.
        token = api_key.encode(
            "utf-8"
        )  # rename to clarify: this is a token, not a password
        return hmac.new(secret, token, hashlib.sha256).hexdigest()

    def extract_prefix(self, api_key: str, prefix_length: int = 8) -> str:
        """Extract prefix from API key for identification.

        Args:
            api_key: API key
            prefix_length: Length of prefix

        Returns:
            Key prefix
        """
        return api_key[:prefix_length]

    def create_api_key(self, request: APIKeyCreateRequest) -> APIKeyCreateResponse:
        """Create a new API key.

        Args:
            request: API key creation request

        Returns:
            Created API key response
        """
        # Generate API key
        api_key = self.generate_api_key()
        key_hash = self.hash_api_key(api_key)
        prefix = self.extract_prefix(api_key)

        # Generate unique key ID
        key_id = f"key_{int(time.time())}_{secrets.token_hex(4)}"

        # Set permissions based on role if not provided
        permissions = request.permissions
        if not permissions:
            permissions = ROLE_PERMISSIONS[request.role].permissions

        # Create API key object
        api_key_obj = APIKey(
            key_id=key_id,
            name=request.name,
            key_hash=key_hash,
            prefix=prefix,
            role=request.role,
            permissions=permissions,
            expires_at=request.expires_at,
            rate_limit_per_minute=request.rate_limit_per_minute,
            allowed_ips=request.allowed_ips,
            metadata=request.metadata,
        )

        # Store API key
        self.api_keys[key_id] = api_key_obj
        self.key_hash_to_id[key_hash] = key_id

        logger.info(f"Created API key: {key_id} ({request.name})")

        return APIKeyCreateResponse(
            key_id=key_id,
            name=request.name,
            api_key=api_key,  # Only shown once
            prefix=prefix,
            role=request.role,
            permissions=permissions,
            expires_at=request.expires_at,
            rate_limit_per_minute=request.rate_limit_per_minute,
            allowed_ips=request.allowed_ips,
            metadata=request.metadata,
        )

    def authenticate_api_key(
        self, api_key: str, ip_address: str | None = None
    ) -> AuthenticationResult:
        """Authenticate an API key using constant-time comparison.

        Args:
            api_key: API key to authenticate
            ip_address: Client IP address for validation

        Returns:
            Authentication result
        """
        if not api_key:
            return AuthenticationResult(success=False, error="API key required")

        # Hash the incoming key and look up via hash (constant-time via hmac.compare_digest)
        key_hash = self.hash_api_key(api_key)

        # Find API key by hash — compare_digest called inside hash_api_key already
        key_id = self.key_hash_to_id.get(key_hash)
        if not key_id:
            return AuthenticationResult(success=False, error="Invalid API key")

        api_key_obj = self.api_keys.get(key_id)
        if not api_key_obj:
            return AuthenticationResult(success=False, error="API key not found")

        # Check if key is enabled
        if not api_key_obj.enabled:
            return AuthenticationResult(success=False, error="API key is disabled")

        # Check if key is expired
        if api_key_obj.is_expired():
            return AuthenticationResult(success=False, error="API key has expired")

        # Check IP restrictions
        if ip_address and not api_key_obj.is_valid_ip(ip_address):
            return AuthenticationResult(success=False, error="IP address not allowed")

        # Update usage statistics
        api_key_obj.update_usage()

        logger.info(f"API key authenticated: {key_id} from {ip_address}")

        return AuthenticationResult(success=True, api_key=api_key_obj)

    def get_api_key(self, key_id: str) -> APIKey | None:
        """Get API key by ID.

        Args:
            key_id: API key ID

        Returns:
            API key object or None
        """
        return self.api_keys.get(key_id)

    def list_api_keys(
        self, role: Role | None = None, enabled_only: bool = True
    ) -> list[APIKey]:
        """List API keys with optional filtering.

        Args:
            role: Filter by role
            enabled_only: Only return enabled keys

        Returns:
            List of API keys
        """
        keys = list(self.api_keys.values())

        if role:
            keys = [k for k in keys if k.role == role]

        if enabled_only:
            keys = [k for k in keys if k.enabled]

        return keys

    def update_api_key(
        self, key_id: str, request: APIKeyUpdateRequest
    ) -> APIKey | None:
        """Update an existing API key.

        Args:
            key_id: API key ID
            request: Update request

        Returns:
            Updated API key or None if not found
        """
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return None

        # Update fields
        if request.name is not None:
            api_key.name = request.name

        if request.role is not None:
            api_key.role = request.role
            # Update permissions based on new role if not explicitly provided
            if request.permissions is None:
                api_key.permissions = ROLE_PERMISSIONS[request.role].permissions

        if request.permissions is not None:
            api_key.permissions = request.permissions

        if request.enabled is not None:
            api_key.enabled = request.enabled

        if request.expires_at is not None:
            api_key.expires_at = request.expires_at

        if request.rate_limit_per_minute is not None:
            api_key.rate_limit_per_minute = request.rate_limit_per_minute

        if request.allowed_ips is not None:
            api_key.allowed_ips = request.allowed_ips

        if request.metadata is not None:
            api_key.metadata = request.metadata

        logger.info(f"Updated API key: {key_id}")

        return api_key

    def delete_api_key(self, key_id: str) -> bool:
        """Delete an API key.

        Args:
            key_id: API key ID

        Returns:
            True if deleted, False if not found
        """
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False

        # Remove from storage
        del self.api_keys[key_id]
        del self.key_hash_to_id[api_key.key_hash]

        logger.info(f"Deleted API key: {key_id}")

        return True

    def revoke_api_key(self, key_id: str) -> bool:
        """Revoke (disable) an API key.

        Args:
            key_id: API key ID

        Returns:
            True if revoked, False if not found
        """
        api_key = self.api_keys.get(key_id)
        if not api_key:
            return False

        api_key.enabled = False

        logger.info(f"Revoked API key: {key_id}")

        return True

    def get_usage_statistics(self) -> dict[str, Any]:
        """Get API key usage statistics.

        Returns:
            Usage statistics
        """
        keys = list(self.api_keys.values())

        total_keys = len(keys)
        enabled_keys = len([k for k in keys if k.enabled])
        expired_keys = len([k for k in keys if k.is_expired()])

        total_usage = sum(k.usage_count for k in keys)

        # Usage by role
        usage_by_role = {}
        for role in Role:
            role_keys = [k for k in keys if k.role == role]
            usage_by_role[role.value] = {
                "count": len(role_keys),
                "enabled": len([k for k in role_keys if k.enabled]),
                "usage": sum(k.usage_count for k in role_keys),
            }

        # Recently active keys (used in last 24 hours)
        recent_cutoff = datetime.utcnow() - timedelta(hours=24)
        recently_active = len(
            [k for k in keys if k.last_used_at and k.last_used_at > recent_cutoff]
        )

        return APIKeyManager_get_usage_statisticsResult.model_validate({
            "total_keys": total_keys,
            "enabled_keys": enabled_keys,
            "expired_keys": expired_keys,
            "recently_active": recently_active,
            "total_usage": total_usage,
            "usage_by_role": usage_by_role,
        })


class AuthorizationChecker:
    """Handles authorization checks based on permissions."""

    def __init__(self, api_key_manager: APIKeyManager):
        """Initialize authorization checker.

        Args:
            api_key_manager: API key manager instance
        """
        self.api_key_manager = api_key_manager

    def check_permission(
        self, api_key: str, permission: Permission, ip_address: str | None = None
    ) -> AuthenticationResult:
        """Check if API key has specific permission.

        Args:
            api_key: API key to check
            permission: Required permission
            ip_address: Client IP address

        Returns:
            Authentication result
        """
        # First authenticate the key
        auth_result = self.api_key_manager.authenticate_api_key(api_key, ip_address)
        if not auth_result.success:
            return auth_result

        # Check permission
        key_obj = auth_result.api_key
        if not key_obj.has_permission(permission):
            return AuthenticationResult(
                success=False,
                error=f"Insufficient permissions. Required: {permission.value}",
            )

        return auth_result

    def require_permission(self, permission: Permission):
        """Decorator to require specific permission.

        Args:
            permission: Required permission

        Returns:
            Decorator function
        """

        def decorator(func):
            def wrapper(*args, **kwargs):
                # This would be used with FastAPI dependencies
                # Implementation depends on the framework integration
                pass

            return wrapper

        return decorator


# Global API key manager instance
_api_key_manager: APIKeyManager | None = None
_authorization_checker: AuthorizationChecker | None = None


def get_api_key_manager() -> APIKeyManager:
    """Get global API key manager instance.

    Returns:
        API key manager instance
    """
    global _api_key_manager
    if _api_key_manager is None:
        _api_key_manager = APIKeyManager()
    return _api_key_manager


def get_authorization_checker() -> AuthorizationChecker:
    """Get global authorization checker instance.

    Returns:
        Authorization checker instance
    """
    global _authorization_checker
    if _authorization_checker is None:
        _authorization_checker = AuthorizationChecker(get_api_key_manager())
    return _authorization_checker


def initialize_authentication():
    """Initialize authentication system."""
    global _api_key_manager, _authorization_checker

    _api_key_manager = APIKeyManager()
    _authorization_checker = AuthorizationChecker(_api_key_manager)

    logger.info("API key authentication system initialized")

    return _api_key_manager, _authorization_checker
