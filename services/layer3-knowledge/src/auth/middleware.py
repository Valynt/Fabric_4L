from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    AuthorizationError,
)

"""FastAPI authentication middleware and dependencies."""

from collections.abc import Callable

from fastapi import Depends, Request, Security
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

from src.logging_config import get_logger

from ..auth.api_keys import (
    APIKey,
    APIKeyManager,
    AuthorizationChecker,
    Permission,
    Role,
    get_api_key_manager,
    get_authorization_checker,
)

logger = get_logger(__name__)


# HTTP Bearer token scheme for API keys
security = HTTPBearer(auto_error=False)


class AuthenticationMiddleware(BaseHTTPMiddleware):
    """Middleware to handle API key authentication."""

    def __init__(self, app, api_key_manager: APIKeyManager | None = None):
        """Initialize authentication middleware.

        Args:
            app: ASGI application
            api_key_manager: API key manager instance
        """
        super().__init__(app)
        self.api_key_manager = api_key_manager or get_api_key_manager()

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """Process request with authentication."""
        # Extract API key from header
        api_key = self._extract_api_key(request)

        # Authenticate if API key provided
        if api_key:
            auth_result = self.api_key_manager.authenticate_api_key(
                api_key, ip_address=request.client.host if request.client else None
            )

            if auth_result.success:
                # Store authenticated API key in request state
                request.state.authenticated_api_key = auth_result.api_key
                request.state.authenticated = True
            else:
                # Store authentication error
                request.state.authenticated = False
                request.state.auth_error = auth_result.error
        else:
            # No API key provided
            request.state.authenticated = False
            request.state.auth_error = None

        # Process request
        response = await call_next(request)

        # SECURITY: Intentionally do NOT add X-API-Key-* headers to responses.
        # Leaking key metadata (ID, name, role) creates an information disclosure
        # vulnerability. Request state retains auth context for internal use only.

        return response

    def _extract_api_key(self, request: Request) -> str | None:
        """Extract API key from request.

        Args:
            request: FastAPI request

        Returns:
            API key string or None
        """
        # Try Authorization header (Bearer token)
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            return auth_header[7:]  # Remove "Bearer " prefix

        # Try X-API-Key header
        api_key_header = request.headers.get("X-API-Key")
        if api_key_header:
            return api_key_header

        return None


async def get_current_api_key(
    credentials: HTTPAuthorizationCredentials | None = Security(security),
    request: Request = None,
    api_key_manager: APIKeyManager = Depends(get_api_key_manager),
) -> APIKey | None:
    """Get current authenticated API key.

    Args:
        credentials: HTTP authorization credentials
        request: FastAPI request
        api_key_manager: API key manager

    Returns:
        Authenticated API key or None

    Raises:
       : If authentication fails
    """
    # Check if already authenticated by middleware
    if hasattr(request.state, "authenticated") and request.state.authenticated:
        return request.state.authenticated_api_key

    # Extract API key
    api_key = None
    if credentials:
        api_key = credentials.credentials

    if not api_key:
        # Try to extract from request directly
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            api_key = auth_header[7:]
        else:
            api_key = request.headers.get("X-API-Key")

    if not api_key:
        raise AuthenticationError(message = "Request failed", details = {
                "error": "AUTHENTICATION_REQUIRED",
                "message": "API key required for this endpoint",
                "schemes": ["Bearer", "X-API-Key"],
            })

    # Authenticate API key
    auth_result = api_key_manager.authenticate_api_key(
        api_key, ip_address=request.client.host if request.client else None
    )

    if not auth_result.success:
        raise AuthenticationError(message = "Request failed", details = {"error": "AUTHENTICATION_FAILED", "message": auth_result.error})

    return auth_result.api_key


def require_permission(permission: Permission):
    """Dependency to require specific permission.

    Args:
        permission: Required permission

    Returns:
        Dependency function
    """

    async def permission_dependency(
        api_key: APIKey = Depends(get_current_api_key),
        auth_checker: AuthorizationChecker = Depends(get_authorization_checker),
    ) -> APIKey:
        """Check if API key has required permission."""
        if not api_key.has_permission(permission):
            raise AuthorizationError(message = "Request failed", details = {
                    "error": "INSUFFICIENT_PERMISSIONS",
                    "message": f"Insufficient permissions. Required: {permission.value}",
                    "required_permission": permission.value,
                    "current_permissions": list(api_key.permissions),
                })

        return api_key

    return permission_dependency


def require_role(role: "Role"):
    """Dependency to require specific role.

    Args:
        role: Required role

    Returns:
        Dependency function
    """

    async def role_dependency(
        api_key: APIKey = Depends(get_current_api_key),
    ) -> APIKey:
        """Check if API key has required role."""
        if api_key.role != role:
            raise AuthorizationError(message = "Request failed", details = {
                    "error": "INSUFFICIENT_ROLE",
                    "message": f"Insufficient role. Required: {role.value}",
                    "required_role": role.value,
                    "current_role": api_key.role.value,
                })

        return api_key

    return role_dependency


# Common permission dependencies
require_read_health = require_permission(Permission.READ_HEALTH)
require_read_metrics = require_permission(Permission.READ_METRICS)
require_read_search = require_permission(Permission.READ_SEARCH)
require_read_graphrag = require_permission(Permission.READ_GRAPHRAG)
require_write_ingestion = require_permission(Permission.WRITE_INGESTION)
require_admin_api_keys = require_permission(Permission.ADMIN_API_KEYS)
require_admin_users = require_permission(Permission.ADMIN_USERS)


# Common role dependencies
require_admin_role = require_role(Role.ADMIN)
require_developer_role = require_role(Role.DEVELOPER)
require_analyst_role = require_role(Role.ANALYST)


# Rate limiting integration
def get_api_key_rate_limit(api_key: APIKey) -> int | None:
    """Get rate limit for API key.

    Args:
        api_key: Authenticated API key

    Returns:
        Rate limit per minute or None
    """
    return api_key.rate_limit_per_minute
