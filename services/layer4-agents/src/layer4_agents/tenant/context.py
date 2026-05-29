from __future__ import annotations

"""Tenant context management for multi-tenancy.

Provides thread-safe tenant context storage and retrieval.
"""


from contextvars import ContextVar
from dataclasses import dataclass
from typing import Any

from value_fabric.shared.models.typed_dict import TypedDictModel


class TenantContext_to_dictResult(TypedDictModel):
    metadata: Any
    roles: Any
    tenant_id: Any
    user_id: Any


@dataclass
class TenantContext:
    """Context for a tenant request.

    Attributes:
        tenant_id: Unique tenant identifier
        user_id: Current user identifier
        roles: User roles
        metadata: Additional context
    """

    tenant_id: str
    user_id: str | None = None
    roles: list = None
    metadata: dict[str, Any] = None

    def __post_init__(self):
        if self.roles is None:
            self.roles = []
        if self.metadata is None:
            self.metadata = {}

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return TenantContext_to_dictResult.model_validate({
            "tenant_id": self.tenant_id,
            "user_id": self.user_id,
            "roles": self.roles,
            "metadata": self.metadata,
        })


    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> TenantContext:
        """Create from dictionary."""
        return cls(
            tenant_id=data["tenant_id"],
            user_id=data.get("user_id"),
            roles=data.get("roles", []),
            metadata=data.get("metadata", {}),
        )


# Context variable for current tenant
_current_tenant: ContextVar[TenantContext | None] = ContextVar(
    "current_tenant",
    default=None,
)


def get_current_tenant() -> TenantContext | None:
    """Get the current tenant context.

    Returns:
        Current tenant context or None
    """
    return _current_tenant.get()


def set_current_tenant(tenant: TenantContext | None) -> None:
    """Set the current tenant context.

    Args:
        tenant: Tenant context to set
    """
    _current_tenant.set(tenant)


def require_tenant() -> TenantContext:
    """Get current tenant or raise error.

    Returns:
        Current tenant context

    Raises:
        RuntimeError: If no tenant context is set
    """
    tenant = get_current_tenant()
    if tenant is None:
        raise RuntimeError("No tenant context set")
    return tenant


class TenantContextManager:
    """Context manager for tenant scoping.

    Example:
        with TenantContextManager(tenant_context):
            # All operations within this block
            # have access to the tenant context
            result = await some_operation()
    """

    def __init__(self, tenant: TenantContext):
        """Initialize context manager.

        Args:
            tenant: Tenant context to set
        """
        self.tenant = tenant
        self.token = None

    def __enter__(self):
        """Enter context."""
        self.token = _current_tenant.set(self.tenant)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        _current_tenant.reset(self.token)
