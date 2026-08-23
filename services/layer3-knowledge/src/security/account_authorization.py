"""Phase 4: Account Authorization Helper and Middleware.

Provides account-scoped authorization for entity access:
- Helper functions to check account access to entities
- Middleware to enforce account guards on routes
- Authorization checks for account-scoped entity types
"""

from typing import Any

from fastapi import Request
from value_fabric.shared.error_handling.exceptions import AuthorizationError

from ..schema.entity_scope import (
    EntityScope,
    get_account_scoped_entity_types,
    get_entity_scope,
    is_account_scoped,
)


class AccountAuthorizationError(AuthorizationError):
    """Raised when account authorization fails."""

    def __init__(
        self, message: str, entity_id: str | None = None, account_id: str | None = None
    ):
        self.entity_id = entity_id
        self.account_id = account_id
        super().__init__(message)


def check_account_access(
    entity_type: str,
    entity_account_id: str | None,
    request_account_id: str | None,
    tenant_id: str,
) -> None:
    """Check if the request account has access to the entity.

    Args:
        entity_type: Type of entity being accessed
        entity_account_id: Account ID associated with the entity (if account-scoped)
        request_account_id: Account ID from the request context
        tenant_id: Tenant ID for context

    Raises:
        AccountAuthorizationError: If access is denied
    """
    # If entity is not account-scoped, allow access
    if not is_account_scoped(entity_type):
        return

    # If entity is account-scoped but has no account_id, allow (legacy data)
    if entity_account_id is None:
        return

    # If request has no account_id, deny access to account-scoped entities
    if request_account_id is None:
        raise AccountAuthorizationError(
            f"Account context required to access account-scoped entity type '{entity_type}'",
            entity_id=None,
            account_id=entity_account_id,
        )

    # Check if account IDs match
    if entity_account_id != request_account_id:
        raise AccountAuthorizationError(
            f"Account '{request_account_id}' does not have access to entity owned by account '{entity_account_id}'",
            entity_id=None,
            account_id=entity_account_id,
        )


def check_account_scope_for_query(
    entity_type: str,
    request_account_id: str | None,
    tenant_id: str,
) -> str | None:
    """Get the account_id filter for a query based on entity scope.

    Args:
        entity_type: Type of entity being queried
        request_account_id: Account ID from the request context
        tenant_id: Tenant ID for context

    Returns:
        Account ID to filter by, or None if no filter needed

    Raises:
        AccountAuthorizationError: If account context is required but missing
    """
    scope = get_entity_scope(entity_type)

    if scope == EntityScope.ACCOUNT_SCOPED:
        if request_account_id is None:
            raise AccountAuthorizationError(
                f"Account context required to query account-scoped entity type '{entity_type}'",
            )
        return request_account_id

    # Tenant-wide or global entities don't need account filtering
    return None


def enrich_query_with_account_filter(
    cypher_query: str,
    entity_type: str,
    request_account_id: str | None,
    account_id_param: str = "account_id",
) -> tuple[str, dict[str, Any]]:
    """Enrich a Cypher query with account filtering if needed.

    Args:
        cypher_query: Original Cypher query
        entity_type: Type of entity being queried
        request_account_id: Account ID from the request context
        account_id_param: Parameter name to use for account_id

    Returns:
        Tuple of (enriched_query, additional_params)
    """
    if not is_account_scoped(entity_type):
        return cypher_query, {}

    if request_account_id is None:
        raise AccountAuthorizationError(
            f"Account context required to query account-scoped entity type '{entity_type}'",
        )

    # Add account_id filter to WHERE clause using regex for safer replacement
    import re

    where_pattern = re.compile(r"\bWHERE\b", re.IGNORECASE)
    return_pattern = re.compile(r"\bRETURN\b", re.IGNORECASE)

    if where_pattern.search(cypher_query):
        # Append to existing WHERE clause
        enriched_query = where_pattern.sub(
            f"WHERE n.{account_id_param} = ${account_id_param} AND",
            cypher_query,
            count=1,
        )
    elif return_pattern.search(cypher_query):
        # Add new WHERE clause before RETURN
        enriched_query = return_pattern.sub(
            f"WHERE n.{account_id_param} = ${account_id_param}\nRETURN",
            cypher_query,
            count=1,
        )
    else:
        # Append WHERE clause at end
        enriched_query = (
            f"{cypher_query}\nWHERE n.{account_id_param} = ${account_id_param}"
        )

    return enriched_query, {account_id_param: request_account_id}


async def get_request_account_id(request: Request) -> str | None:
    """Extract account_id from request state.

    Args:
        request: FastAPI request object

    Returns:
        Account ID if present, None otherwise
    """
    return getattr(request.state, "account_id", None)


async def get_request_tenant_id(request: Request) -> str | None:
    """Extract tenant_id from request state.

    Args:
        request: FastAPI request object

    Returns:
        Tenant ID if present, None otherwise
    """
    return getattr(request.state, "tenant_id", None)


class AccountAuthorizationMiddleware:
    """Middleware to enforce account authorization on routes."""

    def __init__(self, account_scoped_entity_types: set[str] | None = None):
        """Initialize the middleware.

        Args:
            account_scoped_entity_types: Set of entity types that require account authorization.
                                         If None, uses the default from entity_scope module.
        """
        self.account_scoped_entity_types = (
            account_scoped_entity_types or get_account_scoped_entity_types()
        )

    async def __call__(self, request: Request, call_next):
        """Process request and enforce account authorization.

        Args:
            request: FastAPI request
            call_next: Next middleware/endpoint

        Returns:
            Response from next middleware/endpoint
        """
        # Extract account and tenant context
        account_id = await get_request_account_id(request)
        tenant_id = await get_request_tenant_id(request)

        # Store in request state for use in endpoints
        request.state.account_id = account_id
        request.state.tenant_id = tenant_id

        # Continue to next middleware/endpoint
        response = await call_next(request)
        return response


def require_account_context(request: Request) -> str:
    """Require account context in the request.

    Args:
        request: FastAPI request object

    Returns:
        Account ID

    Raises:
       : If account context is missing
    """
    account_id = getattr(request.state, "account_id", None)
    if account_id is None:
        raise AuthorizationError(
            message="Account context is required for this operation"
        )
    return account_id
