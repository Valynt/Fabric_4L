from __future__ import annotations

"""Tenant context domain model for secure multi-tenant operations.

This module provides the canonical TenantContext model used across Layer 4
to enforce tenant isolation at the tool and service level.
"""

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

from value_fabric.shared.identity.context import get_request_context
from value_fabric.shared.models.typed_dict import TypedDictModel


class TenantContext_to_metadata_filterResult(TypedDictModel):
    tenant_id: Any


class TenantContextError(Exception):
    """Raised when tenant context is required but not available."""
    
    def __init__(self, message: str = "Tenant context required but not available"):
        self.message = message
        super().__init__(self.message)


@dataclass(frozen=True)
class TenantContext:
    """Immutable tenant context for secure multi-tenant operations.
    
    This model enforces that all database, graph, and vector store operations
    include proper tenant scoping. It is used by tools to inject tenant filters
    into queries before execution.
    
    Attributes:
        tenant_id: The UUID of the tenant for scoping all operations
        user_id: Optional user identifier for audit logging
        roles: List of roles for permission checking
        source: How the context was authenticated (jwt, api_key, service)
    """
    tenant_id: UUID
    user_id: str | None = None
    roles: list[str] = field(default_factory=list)
    source: str = "unknown"
    
    @classmethod
    def from_request_context(cls) -> TenantContext:
        """Extract tenant context from the current request context.
        
        This method retrieves the context from GovernanceMiddleware's
        ContextVar and converts it to a TenantContext.
        
        Raises:
            TenantContextError: If no request context is available
        """
        try:
            ctx = get_request_context()

            if ctx is None:
                raise TenantContextError(
                    "No request context available. Ensure GovernanceMiddleware is installed."
                )

            tenant_id = ctx.tenant_id
            if isinstance(tenant_id, str):
                tenant_id = UUID(tenant_id)
            return cls(
                tenant_id=tenant_id,
                user_id=ctx.user_id,
                roles=list(ctx.roles) if hasattr(ctx, 'roles') else [],
                source=ctx.source,
            )
        except AttributeError as e:
            raise TenantContextError(
                f"Request context missing required attributes: {e}"
            ) from e
    
    @classmethod
    def from_explicit_tenant_id(cls, tenant_id: UUID | str, user_id: str | None = None) -> TenantContext:
        """Create context from explicit tenant_id (for service-to-service calls).
        
        Use with caution - only for internal service calls where tenant_id
        has already been validated by the calling service.
        """
        if isinstance(tenant_id, str):
            tenant_id = UUID(tenant_id)
        return cls(tenant_id=tenant_id, user_id=user_id, source="explicit")
    
    def to_cypher_filter(self, node_alias: str = "n") -> str:
        """Generate Cypher WHERE clause for tenant filtering.
        
        Args:
            node_alias: The alias used for the node in the Cypher query
            
        Returns:
            Cypher WHERE clause string for tenant filtering
        """
        return f"{node_alias}.tenant_id = '{self.tenant_id}'"
    
    def to_metadata_filter(self) -> dict[str, Any]:
        """Generate metadata filter for vector store queries.
        
        Returns:
            Dictionary suitable for Pinecone/other vector store filters
        """
        return TenantContext_to_metadata_filterResult.model_validate({"tenant_id": str(self.tenant_id)})
    
    def assert_valid(self) -> None:
        """Assert that this context is valid for tenant operations.
        
        Raises:
            TenantContextError: If tenant_id is missing or invalid
        """
        if not self.tenant_id:
            raise TenantContextError("tenant_id is required")
        
        if not isinstance(self.tenant_id, UUID):
            raise TenantContextError(f"tenant_id must be UUID, got {type(self.tenant_id)}")


def get_current_tenant_context() -> TenantContext:
    """Get the current tenant context from request scope.
    
    This is the primary entry point for tools to obtain tenant context.
    It wraps from_request_context with better error messages.
    
    Raises:
        TenantContextError: If no context is available (fail-closed)
    """
    return TenantContext.from_request_context()


def get_current_tenant_context_optional() -> TenantContext | None:
    """Get tenant context if available, None otherwise.
    
    Use only for operations where tenant scoping is optional (rare).
    Most operations should use get_current_tenant_context() to fail closed.
    """
    try:
        return TenantContext.from_request_context()
    except TenantContextError:
        return None
