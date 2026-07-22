"""Exception classes for the governance middleware and rate limiting."""

from __future__ import annotations


class RateLimitExceeded(Exception):
    """Raised when rate limit is exceeded."""

    def __init__(self, retry_after: int):
        self.retry_after = retry_after
        super().__init__(f"Rate limit exceeded. Retry after {retry_after} seconds.")


class MultiWorkerRateLimitError(RuntimeError):
    """Raised when rate limiting is enabled in multi-worker mode without Redis."""

    def __init__(self):
        super().__init__(
            "Multi-worker deployment detected but REDIS_URL is not configured. "
            "Rate limiting requires Redis for shared state across workers. "
            "Set REDIS_URL or disable rate limiting with enable_per_tenant_rate_limiting=False."
        )


class RateLimiterConfigurationError(RuntimeError):
    """Raised when rate limiter backend is unsafe for the current environment."""

    def __init__(self, environment: str):
        super().__init__(
            f"Rate limiter initialization failed for environment '{environment}'. "
            "Redis backend is required in prod/staging but REDIS_URL or Redis client "
            "is unavailable."
        )


class SuspendedTenantError(Exception):
    """Raised when tenant is suspended and cannot access resources."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        super().__init__(f"Tenant {tenant_id} is suspended. Please contact support.")


class PendingTenantError(Exception):
    """Raised when tenant is pending activation and cannot access resources."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        super().__init__(f"Tenant {tenant_id} is pending activation.")


class DeletedTenantError(Exception):
    """Raised when tenant has been deleted and cannot access resources."""

    def __init__(self, tenant_id: str):
        self.tenant_id = tenant_id
        super().__init__(f"Tenant {tenant_id} not found.")
