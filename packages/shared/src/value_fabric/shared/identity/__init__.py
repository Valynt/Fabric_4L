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

from .auth_mode import (
    assert_safe_jwt_and_bypass_configuration,
    is_dev_bypass_enabled,
    log_auth_mode_report,
    validate_dev_bypass_configuration,
)
from .context import (
    RequestContext,
    get_request_context,
    set_request_context,
    require_context,
)
from .dependencies import (
    get_current_context,
    get_optional_context,
    require_action,
    require_any_permission,
    require_all_permissions,
    require_authenticated,
    require_permission,
    require_role,
    require_super_admin,
    require_tenant,
    require_tenant_context,
    require_tenant_admin,
)
from .feature_flags import (
    is_enabled,
    init_feature_flags,
    get_feature_flags_redis,
    register_feature_flag_lookup,
)
from .hashing import generate_api_key, hash_api_key, verify_api_key, extract_key_prefix
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
from .middleware import GovernanceMiddleware
from .models import APIKeyModel, TenantModel, UserModel
from .oidc import (
    OIDCClient,
    OIDCDiscoveryError,
    TransientOIDCDiscoveryError,
    map_role_from_claims,
)
from .oidc_config import OIDCProviderConfig
from .permissions import Permission, Role, ROLE_PERMISSIONS
from .policy_registry import (
    ACTION_POLICIES,
    authorize_action,
    get_action_policy,
    get_tool_action,
    list_action_policies,
)
from .rate_limiter import RedisRateLimiter, RateLimitResult
from .rate_limiting import RateLimitConfig, RateLimitScope, ROLE_DEFAULT_RATE_LIMITS

# Versioned surface marker (R2 versioned shared boundaries).
# The public API of this boundary is ``__all__``; changing it requires a coordinated
# ``SURFACE_VERSION`` bump and a regeneration of ``config/ci/shared_surface_contract.json``
# (via scripts/ci/check_shared_boundary_surfaces.py --update). This marker is intentionally
# NOT part of ``__all__``: it is boundary metadata, not exported API.
SURFACE_VERSION = "1.0.0"

__all__ = [
    # Auth mode
    "assert_safe_jwt_and_bypass_configuration",
    "is_dev_bypass_enabled",
    "log_auth_mode_report",
    "validate_dev_bypass_configuration",
    # Context
    "RequestContext",
    "get_request_context",
    "set_request_context",
    "require_context",
    # Dependencies
    "get_current_context",
    "get_optional_context",
    "require_action",
    "require_any_permission",
    "require_all_permissions",
    "require_authenticated",
    "require_permission",
    "require_role",
    "require_super_admin",
    "require_tenant",
    "require_tenant_context",
    "require_tenant_admin",
    # Feature flags
    "is_enabled",
    "init_feature_flags",
    "get_feature_flags_redis",
    "register_feature_flag_lookup",
    # Hashing
    "generate_api_key",
    "hash_api_key",
    "verify_api_key",
    "extract_key_prefix",
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
    # Middleware
    "GovernanceMiddleware",
    # Models
    "APIKeyModel",
    "TenantModel",
    "UserModel",
    # OIDC
    "OIDCClient",
    "OIDCDiscoveryError",
    "TransientOIDCDiscoveryError",
    "map_role_from_claims",
    "OIDCProviderConfig",
    # Permissions
    "Permission",
    "Role",
    "ROLE_PERMISSIONS",
    # Policy registry
    "ACTION_POLICIES",
    "authorize_action",
    "get_action_policy",
    "get_tool_action",
    "list_action_policies",
    # Rate limiting
    "RedisRateLimiter",
    "RateLimitResult",
    "RateLimitConfig",
    "RateLimitScope",
    "ROLE_DEFAULT_RATE_LIMITS",
    # Lazy-loaded helpers
    "check_vault_health",
    "resolve_vault_secret",
    "validate_jwt_config",
]

_LAZY_VAULT_NAMES = frozenset({"check_vault_health", "resolve_vault_secret"})
_LAZY_DEPENDENCY_NAMES = frozenset({"validate_jwt_config"})


def __getattr__(name: str) -> Any:
    """Lazy-load helpers to avoid circular imports."""
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
