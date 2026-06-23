from __future__ import annotations

"""Compatibility tenant context API backed by shared RequestContext storage.

This module preserves the historical ``layer4_agents.tenant`` API without
creating a second tenant ContextVar. The canonical request context store lives
in ``value_fabric.shared.identity.context``.
"""

from dataclasses import dataclass
from typing import Any

from value_fabric.shared.identity.context import (
    AUTH_SOURCE_JWT,
    RequestContext,
    get_request_context,
    set_request_context,
)
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


def get_current_tenant() -> TenantContext | None:
    """Get the current tenant context.

    Returns:
        Current tenant context or None
    """
    ctx = get_request_context()
    if ctx is None or not ctx.tenant_id:
        return None
    return TenantContext(
        tenant_id=str(ctx.tenant_id),
        user_id=str(ctx.user_id) if ctx.user_id is not None else None,
        roles=list(ctx.roles),
        metadata=dict(ctx.raw),
    )


def set_current_tenant(tenant: TenantContext | None) -> None:
    """Set the current tenant context.

    Args:
        tenant: Tenant context to set
    """
    if tenant is None:
        set_request_context(None)
        return
    set_request_context(
        RequestContext(
            tenant_id=tenant.tenant_id,
            user_id=tenant.user_id,
            roles=[str(role) for role in tenant.roles],
            source=AUTH_SOURCE_JWT,
            auth_source=AUTH_SOURCE_JWT,
            raw=dict(tenant.metadata),
        )
    )


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
        self.previous_context = None

    def __enter__(self):
        """Enter context."""
        self.previous_context = get_request_context()
        set_current_tenant(self.tenant)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit context."""
        set_request_context(self.previous_context)
