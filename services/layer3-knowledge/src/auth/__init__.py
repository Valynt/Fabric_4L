"""Authentication package initialization.

Re-exports from value_fabric.shared.infrastructure.auth during migration.
"""

from value_fabric.shared.infrastructure.auth import (
    ROLE_PERMISSIONS,
    APIKey,
    APIKeyCreateRequest,
    APIKeyCreateResponse,
    APIKeyManager,
    APIKeyResponse,
    APIKeyUpdateRequest,
    AuthenticationResult,
    AuthorizationChecker,
    Permission,
    Role,
    get_api_key_manager,
    get_authorization_checker,
    initialize_authentication,
)

__all__ = [
    "Permission",
    "Role",
    "APIKey",
    "APIKeyCreateRequest",
    "APIKeyResponse",
    "APIKeyCreateResponse",
    "APIKeyUpdateRequest",
    "AuthenticationResult",
    "APIKeyManager",
    "AuthorizationChecker",
    "get_api_key_manager",
    "get_authorization_checker",
    "initialize_authentication",
    "ROLE_PERMISSIONS",
]
