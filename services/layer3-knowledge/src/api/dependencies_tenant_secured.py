from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    AuthorizationError,
    ServiceUnavailableError,
    ValidationError,
)

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Tenant-aware Neo4j dependencies with query validation (Phase 4).

Provides secure Neo4j session injection with:
1. Automatic tenant_id extraction from RequestContext
2. Query validation before execution (blocks unscoped reads)
3. Defense-in-depth for multi-tenant data isolation
"""


import inspect
import logging
import re
from typing import TYPE_CHECKING, Any

from fastapi import Depends, HTTPException, Request, status
from value_fabric.shared.identity.protocols import (
    ProviderUnavailableError,
    RequestContextProvider,
)

from ..db.query_execution import TenantExecutionContext, TenantQueryExecutor
from ..security import QueryValidator, UnscopedQueryError

try:
    from value_fabric.shared.identity.isolation import QueryScope, ScopedQuery
    TENANT_ISOLATION_AVAILABLE = True
except ImportError:
    QueryScope = None  # type: ignore[assignment]
    ScopedQuery = None  # type: ignore[assignment]
    TENANT_ISOLATION_AVAILABLE = False

if TYPE_CHECKING:
    from neo4j import AsyncSession

try:
    from value_fabric.shared.identity.context import RequestContext
    from value_fabric.shared.identity.dependencies import (
        get_current_context,
        get_request_context,
    )
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False
    RequestContext = None  # type: ignore
    get_current_context = None
    get_request_context = None


logger = logging.getLogger(__name__)
_request_context_provider: RequestContextProvider | None = get_request_context or get_current_context

# QueryValidator entrypoints and risk profile for security audits.
QUERY_VALIDATION_ENTRYPOINTS: tuple[tuple[str, str], ...] = (
    ("Neo4jTenantSessionSecured.run", "read/write/admin"),
    ("ValidatedNeo4jSession.run", "read/write/admin"),
)

# Highest-risk paths (write/admin) must use approved templates or structural validation.
APPROVED_QUERY_TEMPLATES: tuple[str, ...] = (
    "MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) DETACH DELETE e",
)
_BROAD_MATCH_PATTERN = re.compile(r"\bMATCH\s*\(\s*[A-Za-z_][A-Za-z0-9_]*\s*\)", re.IGNORECASE)


def _require_request_context_provider() -> RequestContextProvider:
    if _request_context_provider is None:
        raise ProviderUnavailableError(
            provider="value_fabric.shared.identity.dependencies.get_request_context",
            code="IDENTITY_PROVIDER_UNAVAILABLE",
            detail="shared.identity request context provider is required.",
        )
    return _request_context_provider

# Query validator instance (singleton)
_query_validator: QueryValidator | None = None


def get_query_validator() -> QueryValidator:
    """Get singleton query validator instance."""
    global _query_validator
    if _query_validator is None:
        _query_validator = QueryValidator(fail_closed=True)
    return _query_validator


class Neo4jTenantSessionSecured:
    """Tenant-scoped Neo4j session with query validation.
    
    This class wraps Neo4j sessions to provide defense-in-depth
    for multi-tenant query isolation. It:
    
    1. Validates all Cypher queries for tenant_id scoping
    2. Injects tenant_id into query parameters automatically
    3. Blocks unscoped Entity MATCH clauses that could leak data
    
    Example:
        Use this wrapper as the approved execution boundary for route-scoped
        Cypher. Queries that include tenant predicates pass validation; queries
        missing tenant predicates raise ``UnscopedQueryError`` before reaching
        the underlying Neo4j session.
    """
    
    def __init__(
        self,
        driver,
        tenant_id: str,
        *,
        strict_validation: bool = True,
        session: AsyncSession | None = None,
    ):
        """Initialize secured tenant session.
        
        Args:
            driver: Neo4j async driver
            tenant_id: Tenant ID for query scoping
            strict_validation: If True, block all unscoped queries
        """
        self._driver = driver
        self._tenant_id = tenant_id
        self._strict = strict_validation
        self._validator = get_query_validator()
        self._session: AsyncSession | None = session
    
    async def __aenter__(self) -> Neo4jTenantSessionSecured:
        """Enter async context and create underlying session."""
        if self._session is None:
            self._session = self._driver.session()
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb) -> None:
        """Exit context and cleanup session."""
        if self._session:
            await self._session.close()
            self._session = None
    
    @property
    def tenant_id(self) -> str:
        return self._tenant_id

    @property
    def is_bypass(self) -> bool:
        return False

    async def close(self) -> None:
        if self._session:
            await self._session.close()
            self._session = None

    def _validate_cypher_text(self, query_text: str, allow_system_query: bool) -> None:
        """Validate raw Cypher text against broad match and tenant isolation policies."""
        if _BROAD_MATCH_PATTERN.search(query_text) and not allow_system_query:
            raise UnscopedQueryError(
                "Denied broad MATCH traversal without explicit tenant-owned label and tenant predicate"
            )
        risk = QueryValidator.classify_risk(query_text)
        normalized = " ".join(query_text.split())
        if risk in {"write", "admin"}:
            if normalized in APPROVED_QUERY_TEMPLATES:
                self._validator.validate(query_text, query_name="neo4j.run.template")
            else:
                self._validator.validate_structural_tenant_scope(query_text, query_name="neo4j.run.structural")
        findings = self._validator.validate(query_text, query_name="neo4j.run")
        if findings:
            errors = [f for f in findings if f.severity.value == "error"]
            if errors:
                raise UnscopedQueryError(
                    f"Query validation failed: {errors[0].message}"
                )

    async def _run_scoped_query(self, query: Any, raw_params: dict) -> Any:
        """Execute a ScopedQuery object with verified tenant parameters."""
        scoped_tenant = query.tenant_id or self._tenant_id
        if query.scope == QueryScope.TENANT and not scoped_tenant:
            raise UnscopedQueryError("Tenant-scoped Cypher requires tenant context")
        params = {**query.params, **raw_params}
        params.setdefault("tenant_id", scoped_tenant)
        params.setdefault("_tenant_id", scoped_tenant)
        allow_system_query = bool(params.pop("allow_system_query", False))
        return await TenantQueryExecutor.run(
            self._session.run,
            query.cypher,
            params,
            TenantExecutionContext(
                tenant_id=self._tenant_id,
                allow_system_query=allow_system_query,
                allow_multi_clause_tenant_query=True,
            ),
        )

    async def run(self, query: Any, parameters: dict | None = None, **kwargs) -> Any:
        """Execute query with validation and tenant scoping.
        
        Args:
            query: Cypher query string
            parameters: Query parameters
            **kwargs: Additional parameters
            
        Returns:
            Query result
            
        Raises:
            UnscopedQueryError: If query fails tenant isolation validation
            HTTPException: 500 if session not initialized
        """
        if not self._session:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Neo4j session not initialized"
            )
        
        params = dict(parameters or {})
        params.update(kwargs)

        if TENANT_ISOLATION_AVAILABLE and isinstance(query, ScopedQuery):
            return await self._run_scoped_query(query, params)

        query_text = str(query)
        allow_system_query = bool(params.pop("allow_system_query", False))

        # Validate query for tenant scoping
        if self._strict:
            try:
                self._validate_cypher_text(query_text, allow_system_query)
            except UnscopedQueryError:
                logger.warning(
                    f"Blocked unscoped query for tenant {self._tenant_id}: {query_text[:100]}..."
                )
                raise
        
        # Inject tenant_id into parameters. The authenticated/session tenant always wins.
        params["tenant_id"] = self._tenant_id
        params["_tenant_id"] = self._tenant_id

        return await TenantQueryExecutor.run(
            self._session.run,
            query_text,
            params,
            TenantExecutionContext(tenant_id=self._tenant_id, allow_system_query=allow_system_query),
        )

    async def execute_query(self, query: Any, parameters: dict | None = None, **kwargs) -> list[dict]:
        result = await self.run(query, parameters, **kwargs)
        records: list[dict] = []
        async for record in result:
            records.append(record.data())
        return records


async def get_neo4j_secured(
    request: Request,
    context: RequestContext | None = Depends(_require_request_context_provider()),
) -> Neo4jTenantSessionSecured:
    """FastAPI dependency for secured, tenant-scoped Neo4j sessions.
    
    This is the RECOMMENDED dependency for all endpoints that query Neo4j.
    It provides automatic tenant extraction and query validation.
    
    Usage:
        @router.get("/entities/{id}")
        async def get_entity(
            id: str,
            neo4j: Neo4jTenantSessionSecured = Depends(get_neo4j_secured)
        ):
            async with neo4j:
                result = await neo4j.run(
                    "MATCH (e:Entity {id: $id, tenant_id: $tenant_id}) RETURN e",
                    id=id
                )
                ...
    
    Args:
        request: FastAPI request object
        context: Request context with tenant_id
        
    Returns:
        Configured Neo4jTenantSessionSecured instance
        
    Raises:
        HTTPException: 400 if tenant context missing, 503 if Neo4j unavailable
    """
    if not IDENTITY_AVAILABLE:
        _require_request_context_provider()
    
    if not context or not context.tenant_id:
        raise ValidationError(message = "Tenant context required")
    
    driver = getattr(request.app.state, "neo4j_driver", None)
    if not driver:
        try:
            from .dependencies import get_neo4j_driver

            # get_neo4j_driver requires the active request (it reads the
            # driver from application state); calling it without one raised
            # TypeError and surfaced as a false 503 (observed via the
            # Meridian certification journey, 2026-08-12).
            driver = get_neo4j_driver(request)
        except Exception as exc:
            logger.error("Failed to create Neo4j session: %s", exc)
            raise ServiceUnavailableError(message = "Neo4j service unavailable") from exc
    
    session = Neo4jTenantSessionSecured(
        driver=driver,
        tenant_id=str(context.tenant_id),
        strict_validation=True,
    )
    # The wrapper lazily creates the underlying driver session in __aenter__;
    # dependencies return (not yield) this object, so initialize eagerly or
    # the first run() fails with HTTP 500 "Neo4j session not initialized"
    # (observed via the Meridian certification journey, 2026-08-12).
    # TODO(lifecycle): per-request cleanup is not wired; sessions are returned
    # to the driver pool on close(), which callers do not currently invoke.
    await session.__aenter__()
    return session


async def create_neo4j_tenant_session(tenant_id: str | None) -> Neo4jTenantSessionSecured:
    """Create the canonical secured Neo4j tenant session from an explicit tenant ID.

    Route modules that resolve tenant context through API-key/JWT helpers should
    use this factory instead of importing the deprecated ``dependencies_tenant``
    compatibility module.
    """
    if not tenant_id:
        raise ValueError("tenant_id is required for tenant-scoped sessions")

    from ..db.driver import get_driver

    driver = await get_driver()
    session = Neo4jTenantSessionSecured(
        driver=driver,
        tenant_id=str(tenant_id),
        strict_validation=True,
    )
    # Same eager-initialization requirement as get_neo4j_secured above.
    await session.__aenter__()
    return session


async def get_neo4j_with_tenant(
    request: Request,
    context: RequestContext | None = Depends(_require_request_context_provider()),
) -> Neo4jTenantSessionSecured:
    """Canonical FastAPI dependency for tenant-scoped Neo4j route access."""
    return await get_neo4j_secured(request, context)


async def get_neo4j_with_validation(
    request: Request,
    context: RequestContext | None = Depends(_require_request_context_provider()),
) -> Neo4jTenantSessionSecured:
    """Alias for get_neo4j_secured - explicit validation naming.
    
    Use this dependency when you want to emphasize that query validation
    is being applied for security compliance.
    """
    return await get_neo4j_secured(request, context)


async def get_neo4j_with_optional_tenant(
    request: Request,
    context: RequestContext | None = Depends(_require_request_context_provider()),
) -> Neo4jTenantSessionSecured:
    """Compatibility dependency for privileged paths that may bypass tenant scope.

    New tenant-facing routes must use ``get_neo4j_with_tenant``. This helper is
    retained only for legacy admin routes and still requires a valid
    ``RequestContext``; non-super-admin callers must provide tenant context.
    """
    if context and context.tenant_id:
        return await get_neo4j_secured(request, context)
    if context and context.is_super_admin():
        raise AuthorizationError(message = "Super-admin Neo4j bypass must use an explicitly reviewed admin dependency.")
    raise ValidationError(message = "Tenant context required or explicitly reviewed super-admin dependency.")


def require_tenant_header_for_internal():
    """Compatibility factory that resolves tenant ID from RequestContext only."""

    async def _check_tenant_header(request: Request) -> str:
        if not IDENTITY_AVAILABLE:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Identity system unavailable. Ensure shared.identity is configured.",
            )
        provider = _require_request_context_provider()
        try:
            ctx = provider(request)
        except TypeError:
            ctx = provider()
        if inspect.isawaitable(ctx):
            ctx = await ctx
        if ctx and ctx.tenant_id:
            return str(ctx.tenant_id)
        raise AuthenticationError(message = "Tenant context required. Ensure request passed through GovernanceMiddleware.")

    return _check_tenant_header


def require_request_tenant_id(request: Request) -> str:
    """Extract tenant from request.state.governance_context and fail closed when absent."""
    ctx = getattr(request.state, "governance_context", None)
    tenant_id = getattr(ctx, "tenant_id", None) if ctx else None
    if not tenant_id:
        raise ValidationError(message = "tenant_id is required")
    return str(tenant_id)


# Backward-compatible aliases for route type hints
Neo4jTenantSession = Neo4jTenantSessionSecured
Neo4jTenantValidatedSession = Neo4jTenantSessionSecured
