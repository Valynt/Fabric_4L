"""Domain exception hierarchy for Layer 1 Ingestion Service.

Provides explicit exception classes for all failure modes that were
previously handled with bare or silent except blocks (M-02 remediation).
"""


class Layer1Exception(Exception):
    """Base exception for all Layer 1 ingestion errors."""

    def __init__(self, message: str, *, component: str = "layer1", error_code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.component = component
        self.error_code = error_code or self.__class__.__name__


class XBRLParseError(Layer1Exception):
    """Raised when XBRL parsing fails in a way that produces incorrect or incomplete data."""

    def __init__(
        self,
        message: str,
        *,
        concept: str | None = None,
        value_preview: str | None = None,
        context_ref: str | None = None,
        component: str = "xbrl_parser",
        error_code: str = "XBRL_PARSE_ERROR",
    ) -> None:
        super().__init__(message, component=component, error_code=error_code)
        self.concept = concept
        self.value_preview = value_preview
        self.context_ref = context_ref


class ConfigurationError(Layer1Exception):
    """Raised when service configuration is invalid or missing."""

    def __init__(
        self,
        message: str,
        *,
        component: str = "config",
        error_code: str = "CONFIGURATION_ERROR",
    ) -> None:
        super().__init__(message, component=component, error_code=error_code)


# =============================================================================
# SECURITY EXCEPTIONS
# =============================================================================

class SecurityError(Layer1Exception):
    """Base exception for all security-related errors that should not be silently retried."""

    def __init__(
        self,
        message: str,
        *,
        component: str = "security",
        error_code: str | None = None,
        tenant_id: str | None = None,
    ) -> None:
        super().__init__(message, component=component, error_code=error_code or "SECURITY_ERROR")
        self.tenant_id = tenant_id


class TenantContextError(SecurityError):
    """Raised when tenant context is missing, invalid, or improperly accessed."""

    def __init__(
        self,
        message: str,
        *,
        tenant_id: str | None = None,
        component: str = "tenant_context",
        error_code: str = "TENANT_CONTEXT_ERROR",
    ) -> None:
        super().__init__(message, component=component, error_code=error_code, tenant_id=tenant_id)


class InvalidTenantContextError(TenantContextError):
    """Raised when tenant_id is invalid or context cannot be established."""

    def __init__(
        self,
        message: str,
        *,
        tenant_id: str | None = None,
        component: str = "tenant_context",
        error_code: str = "INVALID_TENANT_CONTEXT",
    ) -> None:
        super().__init__(message, tenant_id=tenant_id, component=component, error_code=error_code)


class SystemMaintenanceAuthorizationError(SecurityError):
    """Raised when system maintenance operation lacks proper authorization."""

    def __init__(
        self,
        message: str,
        *,
        operation: str | None = None,
        component: str = "maintenance",
        error_code: str = "MAINTENANCE_AUTH_ERROR",
    ) -> None:
        super().__init__(message, component=component, error_code=error_code)
        self.operation = operation


class CrossTenantAccessError(TenantContextError):
    """Raised when attempting to access data across tenant boundaries."""

    def __init__(
        self,
        message: str,
        *,
        target_tenant: str | None = None,
        source_tenant: str | None = None,
        component: str = "tenant_isolation",
        error_code: str = "CROSS_TENANT_ACCESS",
    ) -> None:
        super().__init__(message, tenant_id=source_tenant, component=component, error_code=error_code)
        self.target_tenant = target_tenant


# =============================================================================
# ROBOTS CHECKER EXCEPTIONS
# =============================================================================

class RobotsCheckerError(Layer1Exception):
    """Base exception for robots.txt checker errors."""

    def __init__(
        self,
        message: str,
        *,
        domain: str | None = None,
        component: str = "robots_checker",
        error_code: str | None = None,
    ) -> None:
        super().__init__(message, component=component, error_code=error_code or "ROBOTS_CHECKER_ERROR")
        self.domain = domain


class RobotsCacheError(RobotsCheckerError):
    """Raised when robots.txt cache operations fail."""

    def __init__(
        self,
        message: str,
        *,
        domain: str | None = None,
        component: str = "robots_cache",
        error_code: str = "ROBOTS_CACHE_ERROR",
    ) -> None:
        super().__init__(message, domain=domain, component=component, error_code=error_code)


class RobotsFetchError(RobotsCheckerError):
    """Raised when robots.txt fetch fails (network, HTTP errors)."""

    def __init__(
        self,
        message: str,
        *,
        domain: str | None = None,
        status_code: int | None = None,
        component: str = "robots_fetch",
        error_code: str = "ROBOTS_FETCH_ERROR",
    ) -> None:
        super().__init__(message, domain=domain, component=component, error_code=error_code)
        self.status_code = status_code


class RobotsParseError(RobotsCheckerError):
    """Raised when robots.txt parsing fails due to malformed content."""

    def __init__(
        self,
        message: str,
        *,
        domain: str | None = None,
        content_preview: str | None = None,
        component: str = "robots_parse",
        error_code: str = "ROBOTS_PARSE_ERROR",
    ) -> None:
        super().__init__(message, domain=domain, component=component, error_code=error_code)
        self.content_preview = content_preview
