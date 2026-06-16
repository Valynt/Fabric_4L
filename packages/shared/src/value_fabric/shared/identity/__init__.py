"""Shared identity and governance library for Value Fabric.

This package is imported by all layers (L1–L4) and provides:
- Canonical Role/Permission enums
- Pydantic models for Tenant, User, APIKey
- Verified JWT encode/decode
- Unified RequestContext propagated via ContextVar
- GovernanceMiddleware (single replacement for L3 AuthMiddleware + L4 TenantMiddleware)
- FastAPI dependency helpers
"""

from typing import Any

from .context import RequestContext, get_request_context, set_request_context, require_context
from .hashing import generate_api_key, hash_api_key, verify_api_key, extract_key_prefix
from .feature_flags import is_enabled, init_feature_flags, get_feature_flags_redis, register_feature_flag_lookup
from .isolation import (
    DEFAULT_TENANT_LABEL_POLICY,
    QueryScope,
    ScopedQuery,
    SystemCypher,
    TenantLabelPolicy,
    TenantScopedCypher,
    TenantScopedMixin,
    tenant_cache_key,
)
from .jwt import TokenClaims, decode_jwt, encode_jwt, get_jwks
from .oidc import OIDCClient, OIDCDiscoveryError, TransientOIDCDiscoveryError, map_role_from_claims
from .oidc_config import OIDCProviderConfig
from .rate_limiter import RedisRateLimiter, RateLimitResult
from .rate_limiting import RateLimitConfig, RateLimitScope, ROLE_DEFAULT_RATE_LIMITS
from .dependencies import (
    get_current_context,
    require_authenticated,
    require_role,
    require_permission,
    require_any_permission,
    require_all_permissions,
    require_action,
    require_tenant,
    get_optional_context,
)
from .middleware import GovernanceMiddleware
from .models import APIKeyModel, TenantModel, UserModel
from .permissions import Permission, Role, ROLE_PERMISSIONS
from .policy_registry import (
    ACTION_POLICIES,
    authorize_action,
    get_action_policy,
    get_tool_action,
    list_action_policies,
)

from .dependencies import (
    require_tenant_admin,
    require_super_admin,
)
from .auth_mode import (
    assert_safe_jwt_and_bypass_configuration,
    is_dev_bypass_enabled,
    log_auth_mode_report,
    validate_dev_bypass_configuration,
)
__all__ = [
    # Dependencies (merged from root)
    "require_tenant_admin",
    "validate_jwt_config",
    "require_super_admin",
    # Vault (merged from root)
    "check_vault_health",
    "resolve_vault_secret",
    # Models (merged from root)
    "TenantStatus",
    "UserStatus",
    "TenantCreateRequest",
    "TenantUpdateRequest",
    "UserInviteRequest",
    "UserUpdateRequest",
    "APIKeyCreateRequest",
    "APIKeyCreateResponse",
    # Context
    "RequestContext",
    "get_request_context",
    "set_request_context",
    "require_context",
    # Hashing
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "extract_key_prefix",
    # Feature flags
    "is_enabled",
    "init_feature_flags",
    "get_feature_flags_redis",
    "register_feature_flag_lookup",
    # Isolation
        "DEFAULT_TENANT_LABEL_POLICY",
        "QueryScope",
        "ScopedQuery",
        "SystemCypher",
        "TenantLabelPolicy",
        "TenantScopedCypher",
        "TenantScopedMixin",
        "tenant_cache_key",
    # JWT
    "TokenClaims",
    "decode_jwt",
    "encode_jwt",
    "get_jwks",
    # OIDC
    "OIDCClient",
    "OIDCDiscoveryError",
    "TransientOIDCDiscoveryError",
    "map_role_from_claims",
    "OIDCProviderConfig",
    # Rate limiting
    "RedisRateLimiter",
    "RateLimitResult",
    "RateLimitConfig",
    "RateLimitScope",
    "ROLE_DEFAULT_RATE_LIMITS",
    # Dependencies
    "get_current_context",
    "require_authenticated",
    "require_role",
    "require_permission",
    "require_any_permission",
    "require_all_permissions",
    "require_action",
    "require_tenant",
    "get_optional_context",
    # Middleware
    "GovernanceMiddleware",
    # Models
    "APIKeyModel",
    "TenantModel",
    "UserModel",
    # Permissions
    "Permission",
    "Role",
    "ROLE_PERMISSIONS",
    "ACTION_POLICIES",
    "authorize_action",
    "get_action_policy",
    "get_tool_action",
    "list_action_policies",
    # Auth mode
    "assert_safe_jwt_and_bypass_configuration",
    "is_dev_bypass_enabled",
    "log_auth_mode_report",
    "validate_dev_bypass_configuration",
]


_LAZY_VAULT_NAMES = frozenset({"check_vault_health", "resolve_vault_secret"})
_LAZY_DEPENDENCY_NAMES = frozenset({"validate_jwt_config"})


def __getattr__(name: str) -> Any:
    """Lazy-load helpers to avoid a circular import with ``security.config``."""
    if name in _LAZY_VAULT_NAMES:
        from . import vault_check

        value = getattr(vault_check, name)
        globals()[name] = value
        return value
    if name in _LAZY_DEPENDENCY_NAMES:
        from . import dependencies

        value = getattr(dependencies, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
