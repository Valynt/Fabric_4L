from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import AuthorizationError, ValidationError

INTENTIONAL_DB_ADAPTER_BYPASS = True

"""
Async SQLAlchemy engine and session management for Layer 4.

Extends the checkpoint database configuration to support operational data storage
for accounts, CRM sync metadata, and workflow state.

P0-08: Supports PostgreSQL Row-Level Security via SET LOCAL app.tenant_id
SECURITY: Fail-safe tenant isolation - tenant context is mandatory
"""

import logging
import os
import time
import warnings
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager
from urllib.parse import urlparse
from uuid import UUID

# Import settings at module level for early validation and clarity
from .config.settings import get_settings

# Task 4.1: Default isolation tier constant
DEFAULT_ISOLATION_TIER = "shared"

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import event, text
from sqlalchemy.exc import TimeoutError as SATimeoutError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

# P1: Module-level logger for audit emission errors
logger = logging.getLogger(__name__)

# Task 1.6: Tenant context validation metrics
_tenant_validation_metrics = {
    "validations_total": 0,
    "validation_failures": 0,
    "uuid_format_errors": 0,
    "missing_context_errors": 0,
    "empty_tenant_errors": 0,
}
_privileged_db_session_metrics = {
    "activations_total": 0,
    "denials_total": 0,
    "missing_reason_total": 0,
}


def get_tenant_validation_metrics() -> dict[str, int]:
    """Get tenant validation metrics for monitoring.

    Returns:
        Dictionary of validation metric counters
    """
    return _tenant_validation_metrics.copy()


def reset_tenant_validation_metrics() -> None:
    """Reset tenant validation metrics. Used for testing."""
    _tenant_validation_metrics.update(
        {
            "validations_total": 0,
            "validation_failures": 0,
            "uuid_format_errors": 0,
            "missing_context_errors": 0,
            "empty_tenant_errors": 0,
        }
    )


def get_privileged_db_session_metrics() -> dict[str, int]:
    return _privileged_db_session_metrics.copy()


def reset_privileged_db_session_metrics() -> None:
    _privileged_db_session_metrics.update(
        {
            "activations_total": 0,
            "denials_total": 0,
            "missing_reason_total": 0,
        }
    )


try:
    from value_fabric.shared.identity.context import RequestContext
    from value_fabric.shared.identity.dependencies import get_current_context as get_request_context

    SHARED_IDENTITY_AVAILABLE = True
except ImportError:
    SHARED_IDENTITY_AVAILABLE = False
    RequestContext = None  # type: ignore
    get_request_context = None  # type: ignore

# Task 3.1: Tenant resolution audit logging
try:
    from value_fabric.shared.audit import (
        AuditAction,
        AuditOutcome,
        TenantContextSetDetails,
        emit_audit_event,
    )

    AUDIT_AVAILABLE = True
except ImportError:
    AUDIT_AVAILABLE = False
    emit_audit_event = None  # type: ignore
    AuditAction = None  # type: ignore
    AuditOutcome = None  # type: ignore
    TenantContextSetDetails = None  # type: ignore


async def _emit_tenant_context_set_audit(
    context: RequestContext,
    tenant_id: str | None,
    *,
    is_bypass: bool = False,
    bypass_reason: str | None = None,
) -> None:
    """P1: Helper to emit TENANT_CONTEXT_SET audit event.

    Centralizes the audit emission logic to avoid duplication between
    get_db_from_context and get_db_with_optional_tenant.
    """
    if not AUDIT_AVAILABLE:
        return

    try:
        details = TenantContextSetDetails(
            tenant_id=tenant_id,
            isolation_tier=context.isolation_tier,
            bypass=is_bypass,
            bypass_reason=bypass_reason,
            context_source="request_context",
        )
        await emit_audit_event(
            action=AuditAction.TENANT_CONTEXT_SET,
            outcome=AuditOutcome.SUCCESS,
            resource_type="database_session",
            resource_id=tenant_id,
            actor_id=context.user_id or context.api_key_id or context.service_account_id,
            tenant_id=context.tenant_id,
            request_id=context.request_id,
            details=details.model_dump(exclude_none=True),
        )
    except asyncio.CancelledError:
        raise
    except Exception as exc:
        # Audit emission must never break request flow — log and continue.
        logger.debug("Tenant context audit emission failed (non-critical): %s", exc)


# ---------------------------------------------------------------------------
# Declarative Base
# ---------------------------------------------------------------------------


class Base(DeclarativeBase):
    """Shared declarative base for all Layer 4 models."""

    pass


# ---------------------------------------------------------------------------
# Engine — created once at import time, reused across requests
# ---------------------------------------------------------------------------

_engine: AsyncEngine | None = None
_session_factory: async_sessionmaker[TenantEnforcedAsyncSession] | None = None

_TENANT_CONTEXT_STATE_KEY = "tenant_context_state"
_TENANT_CONTEXT_VALUE_KEY = "tenant_context_value"
_TENANT_BYPASS_REASON_KEY = "tenant_context_bypass_reason"
_PRIVILEGED_REASON_HEADER = "X-Privileged-Reason"
_RLS_SUPPORTED_SCHEMES = frozenset(
    {"postgresql", "postgres", "postgresql+asyncpg", "postgresql+psycopg"}
)
_RLS_SUPERUSER_NAMES = frozenset({"postgres", "rdsadmin", "cloudsqladmin", "azure_superuser"})


def _record_pool_state(engine: AsyncEngine) -> None:
    try:
        from .metrics import get_metrics

        metrics = get_metrics()
        if metrics is None:
            return
        pool = engine.sync_engine.pool
        active = int(pool.checkedout())
        size = int(pool.size())
        idle = max(size - active, 0)
        metrics.set_db_pool_state(pool_size=size, active=active, idle=idle)
    except asyncio.CancelledError:
        raise
    except Exception:
        logger.debug("DB pool state metric emission failed", exc_info=True)


def get_database_url() -> str:
    """Get database URL from environment.

    Falls back to checkpoint database URL for compatibility,
    but allows separate configuration for operational data.

    In production-like environments, fails fast if neither URL is configured.
    """
    database_url = (
        os.getenv("LAYER4_DATABASE_URL")
        or os.getenv("DATABASE_URL")
        or os.getenv("CHECKPOINT_DATABASE_URL")
    )

    if not database_url:
        if _is_production_like_runtime():
            raise RuntimeError(
                "LAYER4_DATABASE_URL or CHECKPOINT_DATABASE_URL must be set in production-like environments. "
                "Configure these environment variables via Kubernetes secrets."
            )
        # Allow local development with SQLite or other local databases
        return "sqlite+aiosqlite:///:memory:"

    return database_url


def _is_production_like_runtime() -> bool:
    env = os.getenv("ENVIRONMENT", "").strip().lower()
    app_env = os.getenv("APP_ENV", "").strip().lower()
    value = env or app_env
    return value == "production"


def _assert_rls_safe_database_url(database_url: str, *, source: str) -> None:
    if not _is_production_like_runtime():
        return

    parsed = urlparse(database_url)
    scheme = (parsed.scheme or "").lower()
    username = (parsed.username or "").lower()

    if scheme not in _RLS_SUPPORTED_SCHEMES:
        raise RuntimeError(
            f"{source} must use PostgreSQL with RLS-capable tenant isolation in protected environments."
        )

    if username in _RLS_SUPERUSER_NAMES:
        raise RuntimeError(
            f"{source} must not use PostgreSQL superuser role '{username}' in protected environments."
        )


def _statement_sets_tenant_context(statement: object) -> bool:
    sql = str(statement).lower()
    return "app.tenant_id" in sql and ("set_config" in sql or "set local" in sql)


def _mark_session_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    session.info[_TENANT_CONTEXT_STATE_KEY] = "set"
    session.info[_TENANT_CONTEXT_VALUE_KEY] = tenant_id
    object.__setattr__(session, "_tenant_id", tenant_id)
    session.info.pop(_TENANT_BYPASS_REASON_KEY, None)


def _mark_session_tenant_bypass(session: AsyncSession, *, reason: str) -> None:
    session.info[_TENANT_CONTEXT_STATE_KEY] = "bypass"
    session.info[_TENANT_CONTEXT_VALUE_KEY] = None
    session.info[_TENANT_BYPASS_REASON_KEY] = reason


def _assert_session_has_tenant_context(session: AsyncSession, *, operation: str) -> None:
    state = session.info.get(_TENANT_CONTEXT_STATE_KEY)
    if state in {"set", "bypass"}:
        return
    raise TenantContextError(
        f"Tenant database session context must be established before {operation}."
    )


class TenantEnforcedAsyncSession(AsyncSession):
    """AsyncSession that fails closed if SQL executes before tenant context is set."""

    async def execute(self, statement, params=None, /, **kwargs):  # type: ignore[override]
        if not _statement_sets_tenant_context(statement):
            _assert_session_has_tenant_context(self, operation="statement execution")
        try:
            return await super().execute(statement, params, **kwargs)
        except SATimeoutError:
            try:
                from .metrics import get_metrics

                metrics = get_metrics()
                if metrics is not None:
                    metrics.increment_db_pool_timeout()
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("DB pool timeout metric emission failed", exc_info=True)
            raise


@event.listens_for(TenantEnforcedAsyncSession.sync_session_class, "before_flush")
def _enforce_tenant_context_before_flush(session, flush_context, instances) -> None:
    _assert_session_has_tenant_context(session, operation="flush")


def get_engine() -> AsyncEngine:
    """Return (or lazily create) the shared async engine."""
    global _engine
    if _engine is None:
        database_url = get_database_url()
        _assert_rls_safe_database_url(database_url, source="Layer 4 database URL")
        _is_sqlite = database_url.startswith("sqlite")
        _engine_kwargs: dict = {
            "pool_pre_ping": not _is_sqlite,
            "echo": False,
            "future": True,
        }
        if not _is_sqlite:
            # SQLite uses StaticPool and does not accept pool_size/max_overflow/pool_timeout
            _engine_kwargs["pool_size"] = get_settings().database_pool_size
            _engine_kwargs["max_overflow"] = get_settings().database_max_overflow
            _engine_kwargs["pool_timeout"] = 30.0
        _engine = create_async_engine(database_url, **_engine_kwargs)
        _record_pool_state(_engine)

        @event.listens_for(_engine.sync_engine.pool, "checkout")
        def _on_pool_checkout(dbapi_conn, connection_record, connection_proxy) -> None:
            connection_record.info["pool_checkout_start"] = time.perf_counter()
            _record_pool_state(_engine)

        @event.listens_for(_engine.sync_engine.pool, "checkin")
        def _on_pool_checkin(dbapi_conn, connection_record) -> None:
            start = connection_record.info.pop("pool_checkout_start", None)
            if start is not None:
                try:
                    from .metrics import get_metrics

                    metrics = get_metrics()
                    if metrics is not None:
                        metrics.observe_db_pool_wait(time.perf_counter() - start)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.debug("DB pool wait metric emission failed", exc_info=True)
            _record_pool_state(_engine)

    return _engine


def get_session_factory() -> async_sessionmaker[TenantEnforcedAsyncSession]:
    """Return (or lazily create) the shared session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = async_sessionmaker(
            bind=get_engine(),
            class_=TenantEnforcedAsyncSession,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,
        )
    return _session_factory


async def close_db() -> None:
    """Dispose of the database engine and connection pool.

    Should be called during application shutdown to ensure clean connection cleanup.
    """
    global _engine, _session_factory
    if _engine is not None:
        await _engine.dispose()
        _engine = None
        logger.info("Layer 4 database engine disposed")
    _session_factory = None


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------


class TenantContextError(Exception):
    """Raised when tenant context is missing or invalid in fail-safe mode."""

    pass


# SECURITY: Fail-safe mode - require explicit tenant context
# Set to False only for admin/system operations with proper role validation
FAIL_SAFE_MODE = True

# Reserved tenant keywords for system/admin operations
RESERVED_TENANT_KEYWORDS = frozenset({"system", "admin", "internal"})


def _is_test_environment() -> bool:
    """Return True when deprecated DB dependencies are executed under tests."""
    env = os.getenv("ENVIRONMENT", "").strip().lower()
    app_env = os.getenv("APP_ENV", "").strip().lower()
    return (
        os.getenv("PYTEST_CURRENT_TEST") is not None
        or env in {"test", "testing"}
        or app_env in {"test", "testing"}
    )


def _allow_compat_only_db_dependency(dep_name: str) -> None:
    """Compatibility-only gate for deprecated DB dependencies.

    Deprecated dependencies remain for legacy integration points and tests,
    but new route usage is forbidden. Runtime blocks production usage unless
    explicit compatibility override is configured.
    """
    if _is_test_environment():
        return

    allow_compat = os.getenv("L4_ALLOW_DEPRECATED_DB_DEPENDENCIES", "").strip().lower()
    if allow_compat in {"1", "true", "yes"}:
        return

    raise RuntimeError(
        f"Deprecated compatibility dependency {dep_name}() is disabled. "
        "Use get_db_from_context() for tenant-scoped routes. "
        "Set L4_ALLOW_DEPRECATED_DB_DEPENDENCIES=true only for temporary compatibility migration."
    )


# Try to import shared tenant validation
try:
    from value_fabric.shared.database import TenantContextError as SharedTenantContextError
    from value_fabric.shared.database import validate_tenant_id as shared_validate_tenant_id

    SHARED_TENANT_VALIDATION_AVAILABLE = True
except ImportError:
    SHARED_TENANT_VALIDATION_AVAILABLE = False
    SharedTenantContextError = None  # type: ignore
    shared_validate_tenant_id = None  # type: ignore


def _record_tenant_validation_failure(
    *,
    tenant_id: UUID | str | None,
    error_type: str | None = None,
) -> None:
    """Record validation failure counters based on tenant_id value or explicit type."""
    if error_type == "missing" or tenant_id is None:
        _tenant_validation_metrics["missing_context_errors"] += 1
    elif error_type == "empty" or str(tenant_id).strip() == "":
        _tenant_validation_metrics["empty_tenant_errors"] += 1
    else:
        _tenant_validation_metrics["uuid_format_errors"] += 1
    _tenant_validation_metrics["validation_failures"] += 1


def _validate_tenant_id_via_shared(tenant_id: UUID | str | None) -> str:
    """Delegate tenant ID validation to shared library when available."""
    try:
        return shared_validate_tenant_id(
            tenant_id,
            fail_safe_mode=FAIL_SAFE_MODE,
            reserved_keywords=RESERVED_TENANT_KEYWORDS,
        )
    except (ValueError, TypeError, SharedTenantContextError) as exc:
        # Increment per-error-type counters so metrics stay accurate
        # regardless of which validation path executes.
        _record_tenant_validation_failure(tenant_id=tenant_id)
        # Re-raise as local TenantContextError for a stable exception contract.
        if not isinstance(exc, TenantContextError):
            raise TenantContextError(
                f"tenant_context_invalid ({type(exc).__name__}: tenant_context_failed)"
            ) from exc
        raise


def _validate_tenant_id_fallback(tenant_id: UUID | str | None) -> str:
    """Local fallback validation when shared validation is unavailable."""
    if tenant_id is None:
        _record_tenant_validation_failure(tenant_id=None, error_type="missing")
        if FAIL_SAFE_MODE:
            raise TenantContextError(
                "Tenant context is mandatory. Ensure request includes valid tenant_id "
                "in JWT token or X-Tenant-ID header. For admin operations, use "
                "get_db_with_optional_tenant() with require_super_admin() dependency."
            )
        return ""

    # Convert to string and normalize
    normalized = str(tenant_id).strip()

    # Fail-safe: empty tenant_id is not allowed
    if not normalized:
        _record_tenant_validation_failure(tenant_id="", error_type="empty")
        raise TenantContextError("Empty tenant_id is not allowed. Provide a valid tenant context.")

    # Validate UUID format for strict tenant isolation
    if normalized.lower() not in RESERVED_TENANT_KEYWORDS:
        try:
            UUID(normalized)
        except ValueError:
            _record_tenant_validation_failure(tenant_id=normalized, error_type="uuid_format")
            raise TenantContextError(
                f"Invalid tenant_id format: '{normalized}'. Expected valid UUID or "
                f"reserved keyword ({', '.join(sorted(RESERVED_TENANT_KEYWORDS))})."
            )

    return normalized


def validate_tenant_id(tenant_id: UUID | str | None) -> str:
    """Validate tenant_id format and return normalized string.

    SECURITY: Strict validation to prevent tenant confusion attacks.
    Tracks metrics for validation monitoring.

    Args:
        tenant_id: Tenant identifier to validate (UUID object, UUID string, or None)

    Returns:
        Normalized tenant ID string (lowercase UUID format or reserved keyword)

    Raises:
        TenantContextError: If tenant_id is invalid or missing in fail-safe mode

    Examples:
        >>> validate_tenant_id(UUID('550e8400-e29b-41d4-a716-446655440000'))
        '550e8400-e29b-41d4-a716-446655440000'
        >>> validate_tenant_id('system')
        'system'
    """
    _tenant_validation_metrics["validations_total"] += 1

    # Use shared validation if available
    if SHARED_TENANT_VALIDATION_AVAILABLE and shared_validate_tenant_id:
        return _validate_tenant_id_via_shared(tenant_id)

    # Fallback to local implementation
    return _validate_tenant_id_fallback(tenant_id)


async def _set_local_tenant_context(session: AsyncSession, tenant_id: str) -> None:
    """Set tenant context, using PostgreSQL RLS when the dialect supports it.

    ``set_config`` is a PostgreSQL-only function. Unit tests exercise this path
    against SQLite (which has no equivalent transaction-local variable
    mechanism), so we skip the SQL statement for non-PostgreSQL dialects and
    only record the tenant mark on the session object. Production always runs
    against PostgreSQL and is additionally protected by
    ``_is_production_like_runtime``, which refuses to boot on a non-PostgreSQL
    dialect.
    """
    bind = session.get_bind() if hasattr(session, "get_bind") else getattr(session, "bind", None)
    dialect_name = getattr(getattr(bind, "dialect", None), "name", "") if bind is not None else ""
    if dialect_name != "postgresql":
        if _is_production_like_runtime():
            raise RuntimeError("Tenant RLS context requires PostgreSQL in protected environments.")
        _mark_session_tenant_context(session, tenant_id)
        return

    await session.execute(
        text("SELECT set_config('app.tenant_id', :tenant_id, true)"),
        {"tenant_id": tenant_id},
    )
    _mark_session_tenant_context(session, tenant_id)


async def _clear_local_tenant_context(session: AsyncSession) -> None:
    """Clear the transaction-local tenant context for explicit admin/system bypass."""
    _mark_session_tenant_bypass(session, reason="system_operation")


def _record_privileged_db_session_activation(
    context: RequestContext,
    *,
    mode: str,
    reason: str,
) -> None:
    """Record privileged cross-tenant activation in logs and metrics."""
    _privileged_db_session_metrics["activations_total"] += 1
    logger.warning(
        "Privileged cross-tenant DB session activated",
        extra={
            "request_id": context.request_id,
            "actor_id": context.user_id or context.api_key_id or context.service_account_id,
            "tenant_id": str(context.tenant_id) if context.tenant_id is not None else None,
            "mode": mode,
            "reason": reason,
        },
    )
    try:
        from .metrics import get_metrics

        metrics = get_metrics()
        if metrics is not None:
            metrics.increment_privileged_db_session_activation(
                str(context.tenant_id) if context.tenant_id is not None else None,
                mode,
            )
    except asyncio.CancelledError:
        raise
    except Exception as exc:  # pragma: no cover - metrics must not block authz
        logger.debug("Privileged DB activation metric emission failed: %s", exc)


def _require_privileged_cross_tenant_reason(
    request: Request,
    context: RequestContext,
) -> str:
    """Require explicit super-admin context plus an audited reason for cross-tenant DB access."""
    if not context.is_super_admin():
        _privileged_db_session_metrics["denials_total"] += 1
        raise AuthorizationError(message="Cross-tenant database access requires super admin role.")

    reason = (request.headers.get(_PRIVILEGED_REASON_HEADER) or "").strip()
    if not reason:
        _privileged_db_session_metrics["missing_reason_total"] += 1
        raise ValidationError(
            message=str(
                f"Cross-tenant database access requires {_PRIVILEGED_REASON_HEADER} header."
            )
        )
    return reason


async def set_tenant_context(session: AsyncSession, tenant_id: UUID | str | None) -> None:
    """P0-08: Set PostgreSQL app.tenant_id for RLS policies.

    SECURITY: Fail-safe semantics - tenant context is mandatory unless
    explicitly using admin bypass with proper role authentication.

    Executes SET LOCAL app.tenant_id = '...' which applies for the
    duration of the current transaction. RLS policies in PostgreSQL
    can reference current_setting('app.tenant_id') to filter rows.

    Args:
        session: SQLAlchemy async session
        tenant_id: Tenant UUID or string identifier (whitespace is stripped)

    Raises:
        TenantContextError: If tenant_id is missing/invalid in fail-safe mode
    """
    # SECURITY: Validate tenant context with fail-safe semantics
    normalized_id = validate_tenant_id(tenant_id)

    # Set tenant context for RLS policies
    # Empty string only allowed for admin roles (enforced by RLS policy TO clause)
    await _set_local_tenant_context(session, normalized_id)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for database sessions (without RLS).

    DEPRECATED: Use get_db_from_context() for all new endpoints.
    This function is kept only for health checks and will be removed.

    SECURITY: Use only for health checks or admin operations with proper
    role authentication. All production endpoints should use get_db_from_context.
    """
    _allow_compat_only_db_dependency("get_db")
    warnings.warn(
        "get_db() is deprecated. Use get_db_from_context() for proper tenant isolation.",
        DeprecationWarning,
        stacklevel=2,
    )
    # SECURITY: Bypass tenant validation for health checks (admin role required in DB)
    factory = get_session_factory()
    async with factory() as session:
        # Clear tenant context - RLS bypass only works for admin/system roles
        await _clear_local_tenant_context(session)
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            await session.rollback()
            raise


async def get_db_with_tenant(
    request: Request,
    context: RequestContext = Depends(get_request_context),  # type: ignore
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for DB sessions with required tenant context.

    DEPRECATED: Use get_db_from_context() for all new endpoints. This stub
    exists only to satisfy the compatibility-guard contract and emit a
    deprecation warning when legacy callers are present.
    """
    _allow_compat_only_db_dependency("get_db_with_tenant")
    warnings.warn(
        "get_db_with_tenant() is deprecated. Use get_db_from_context() for proper tenant isolation.",
        DeprecationWarning,
        stacklevel=2,
    )
    async for session in get_db_from_context(context):
        yield session


def _extract_and_validate_context_tenant(
    context: RequestContext | None,
    *,
    error_message: str = "Tenant context required. Ensure request has passed through GovernanceMiddleware.",
) -> str:
    """Extract and validate tenant_id from RequestContext with fail-closed semantics."""
    if not context or not context.tenant_id:
        raise ValidationError(message=error_message)

    try:
        return validate_tenant_id(context.tenant_id)
    except TenantContextError as e:
        logger.warning("tenant_context_error", extra={"error_code": "TENANT_CONTEXT_ERROR"})
        raise ValidationError(message="Invalid tenant context") from e


async def _enforce_session_isolation_tier(
    session: AsyncSession,
    context: RequestContext,
    tenant_id: str,
    *,
    error_detail_verb: str = "supported",
) -> None:
    """Set local tenant context or reject unsupported isolation tiers."""
    if context.isolation_tier == "shared":
        await _set_local_tenant_context(session, tenant_id)
    else:
        # Only 'shared' (PostgreSQL RLS) is supported in v1.
        # 'schema' and 'database' tiers are rejected at provisioning time
        # (see tenant_provisioning.py). This branch is a defensive fallback
        # for tenants that were provisioned before that guard was added.
        # 422 is correct: the request is structurally valid but the tier
        # value is not accepted by this server.
        verb = error_detail_verb
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Isolation tier '{context.isolation_tier}' is not {verb}. "
                "Only 'shared' (PostgreSQL RLS) is available in v1. "
                "Contact support to migrate this tenant."
                if verb == "supported"
                else (
                    f"Isolation tier '{context.isolation_tier}' is not {verb}. "
                    "Only 'shared' (PostgreSQL RLS) is supported in v1. "
                    "Re-provision this tenant with isolation_tier='shared'."
                )
            ),
        )


async def get_db_from_context(
    context: RequestContext = Depends(get_request_context),  # type: ignore
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency that yields DB session with tenant context from RequestContext (Task 1.2).

    This is the recommended dependency for new endpoints. It extracts tenant_id
    from the RequestContext (set by GovernanceMiddleware) rather than directly
    from headers, ensuring consistent tenant resolution.

    Usage::

        @router.get("/items")
        async def list_items(
            db: AsyncSession = Depends(get_db_from_context),
            context: RequestContext = Depends(get_request_context)
        ):
            ...

    Raises:
        HTTPException: 400 if tenant context is missing in RequestContext
    """
    if not SHARED_IDENTITY_AVAILABLE:
        raise RuntimeError("shared.identity package required for get_db_from_context")

    tenant_id = _extract_and_validate_context_tenant(context)

    factory = get_session_factory()
    async with factory() as session:
        # P0-08: Set tenant context for RLS with isolation tier awareness
        await _enforce_session_isolation_tier(
            session, context, tenant_id, error_detail_verb="supported"
        )

        # Task 3.1: Emit tenant context set audit event
        await _emit_tenant_context_set_audit(context, str(tenant_id), is_bypass=False)

        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            await session.rollback()
            raise


async def get_db_with_optional_tenant(
    request: Request,
    context: RequestContext = Depends(get_request_context),  # type: ignore
) -> AsyncGenerator[AsyncSession, None]:
    """FastAPI dependency for DB sessions with optional tenant context (Task 1.3).

    DEPRECATED: Use get_db_from_context() combined with require_super_admin() for
    admin operations. This separate function creates inconsistency in tenant handling.

    This is for super-admin operations that may cross tenant boundaries.
    For regular endpoints, use get_db_from_context() which enforces tenant context.

    Security: Must be combined with require_privileged_access() or require_super_admin()
    dependencies to ensure only authorized users can bypass tenant isolation.

    Usage::

        @router.get("/admin/all-tenants")
        async def get_all_tenants(
            db: AsyncSession = Depends(get_db_with_optional_tenant),
            context: RequestContext = Depends(require_privileged_access()),
        ):
            ...

    Raises:
        HTTPException: 400 if non-super-admin tries to use without tenant context
    """
    _allow_compat_only_db_dependency("get_db_with_optional_tenant")
    warnings.warn(
        "get_db_with_optional_tenant() is deprecated. Use get_db_from_context() for consistency.",
        DeprecationWarning,
        stacklevel=2,
    )
    if not SHARED_IDENTITY_AVAILABLE:
        raise RuntimeError("shared.identity package required for get_db_with_optional_tenant")

    factory = get_session_factory()
    async with factory() as session:
        is_bypass = False
        bypass_reason = None
        effective_tenant_id = None

        if context.tenant_id:
            # Regular users must have tenant context
            try:
                effective_tenant_id = validate_tenant_id(context.tenant_id)
            except TenantContextError as e:
                logger.warning("tenant_context_error", extra={"error_code": "TENANT_CONTEXT_ERROR"})
                raise ValidationError(message="Invalid tenant context") from e
            await _set_local_tenant_context(session, effective_tenant_id)
        elif context.is_super_admin():
            bypass_reason = _require_privileged_cross_tenant_reason(request, context)
            is_bypass = True
            _mark_session_tenant_bypass(session, reason=f"privileged_cross_tenant:{bypass_reason}")
            _record_privileged_db_session_activation(
                context,
                mode="cross_tenant_admin",
                reason=bypass_reason,
            )
        else:
            _privileged_db_session_metrics["denials_total"] += 1
            raise AuthorizationError(
                message="Cross-tenant database access requires super admin role."
            )

        # Task 3.1: Emit tenant context set audit event (with bypass flag for super-admin)
        await _emit_tenant_context_set_audit(
            context,
            effective_tenant_id if effective_tenant_id else None,
            is_bypass=is_bypass,
            bypass_reason=bypass_reason,
        )

        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Tier-aware database session factory (Task 4.1)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def get_tiered_db_session(
    tenant_id: UUID | str,
    isolation_tier: str = DEFAULT_ISOLATION_TIER,
    *,
    request_context: RequestContext | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Get database session with appropriate isolation based on tenant tier.

    DEPRECATED: Use get_db_from_context() which handles tier awareness internally.
    This separate factory is redundant and creates confusion about which to use.

    This factory routes to the correct session implementation based on
    the tenant's isolation tier:
    - "shared": Uses RLS with SET LOCAL app.tenant_id
    - "schema": Reserved for future implementation (dedicated schema)
    - "database": Reserved for future implementation (dedicated database)

    Args:
        tenant_id: The tenant UUID
        isolation_tier: One of "shared", "schema", "database"
        request_context: Optional RequestContext for audit logging

    Raises:
        HTTPException: 422 if an unsupported isolation tier is requested
        TenantContextError: If tenant_id is invalid
    """
    _allow_compat_only_db_dependency("get_tiered_db_session")
    warnings.warn(
        "get_tiered_db_session() is deprecated. Use get_db_from_context() for consistency.",
        DeprecationWarning,
        stacklevel=2,
    )
    # Validate tenant ID
    validated_id = validate_tenant_id(tenant_id)

    # Route to appropriate session implementation
    if isolation_tier == "shared":
        factory = get_session_factory()
        async with factory() as session:
            await _set_local_tenant_context(session, validated_id)

            # Emit audit event if context provided
            if request_context and AUDIT_AVAILABLE:
                await _emit_tenant_context_set_audit(
                    request_context,
                    validated_id,
                    is_bypass=False,
                    bypass_reason=None,
                )

            try:
                yield session
                await session.commit()
            except asyncio.CancelledError:
                raise
            except Exception:
                await session.rollback()
                raise

    elif isolation_tier in ("schema", "database"):
        # "schema" and "database" tiers are not implemented in v1.
        # Tenants must be provisioned with isolation_tier="shared".
        # If this path is reached, the tenant was provisioned with an unsupported
        # tier — reject immediately rather than silently failing mid-workflow.
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=(
                f"Isolation tier {isolation_tier!r} is not implemented. "
                "Only 'shared' (PostgreSQL RLS) is supported in v1. "
                "Re-provision this tenant with isolation_tier='shared'."
            ),
        )

    else:
        raise ValidationError(
            message=str(f"Unknown isolation tier: {isolation_tier!r}. Supported: 'shared'.")
        )


# ---------------------------------------------------------------------------
# Context manager for non-FastAPI usage (services, background tasks)
# ---------------------------------------------------------------------------


@asynccontextmanager
async def db_session(
    tenant_id: UUID | str | None = None, *, require_tenant: bool = True
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for use outside of FastAPI request lifecycle.

    DEPRECATED: Use get_db_from_context() with FastAPI's Depends() for all
    endpoint handlers. For background tasks, inject RequestContext explicitly.

    SECURITY: Fail-safe by default - tenant context is mandatory.

    Args:
        tenant_id: Tenant ID to set for RLS context (P0-08)
        require_tenant: If True (default), enforce mandatory tenant context.
                       Set to False only for admin/system operations with
                       proper role authentication.

    Raises:
        TenantContextError: If tenant_id is missing/invalid and require_tenant=True
    """
    _allow_compat_only_db_dependency("db_session")
    warnings.warn(
        "db_session() is deprecated. Use get_db_from_context() for consistency.",
        DeprecationWarning,
        stacklevel=2,
    )
    # SECURITY: Enforce mandatory tenant context by default
    if require_tenant:
        # This will raise TenantContextError in fail-safe mode if tenant_id is invalid
        tenant_id = validate_tenant_id(tenant_id)
    elif tenant_id is not None:
        # Validate even when require_tenant=False, if a tenant_id was provided
        tenant_id = validate_tenant_id(tenant_id)
    # If require_tenant=False and tenant_id is None, we permit only system-level bypass.

    factory = get_session_factory()
    async with factory() as session:
        if tenant_id is None:
            _mark_session_tenant_bypass(session, reason="system_operation")
        else:
            await _set_local_tenant_context(session, str(tenant_id))
        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            await session.rollback()
            raise


@asynccontextmanager
async def db_session_for_context(
    context: RequestContext,
) -> AsyncGenerator[AsyncSession, None]:
    """Context manager for DB sessions outside FastAPI request lifecycle.

    Uses RequestContext (set by GovernanceMiddleware) to extract tenant_id,
    validate it, and set PostgreSQL RLS context.  Commits on success and
    rolls back on exception — callers MUST NOT call commit/rollback manually.

    Args:
        context: The RequestContext containing tenant_id and isolation_tier.

    Raises:
        TenantContextError: If tenant_id is missing or invalid.
        HTTPException: 422 if an unsupported isolation tier is requested.
    """
    if not SHARED_IDENTITY_AVAILABLE:
        raise RuntimeError("shared.identity package required for db_session_for_context")

    if not context or not context.tenant_id:
        raise TenantContextError(
            "Tenant context required. Ensure request has passed through GovernanceMiddleware."
        )

    try:
        tenant_id = validate_tenant_id(context.tenant_id)
    except TenantContextError:
        raise

    factory = get_session_factory()
    async with factory() as session:
        await _enforce_session_isolation_tier(
            session, context, tenant_id, error_detail_verb="implemented"
        )

        await _emit_tenant_context_set_audit(context, str(tenant_id), is_bypass=False)

        try:
            yield session
            await session.commit()
        except asyncio.CancelledError:
            raise
        except Exception:
            await session.rollback()
            raise


# ---------------------------------------------------------------------------
# Lifecycle helpers (called from FastAPI lifespan)
# ---------------------------------------------------------------------------


async def init_db() -> None:
    """Create all tables if they do not exist (dev/test convenience)."""
    # Ensure all ORM models are registered with Base.metadata before create_all.
    # Side-effect imports are required so that SQLAlchemy discovers tables such
    # as tenants, users, and registry/harness models alongside layer4 models.
    from . import models  # noqa: F401
    from .harness import db_models  # noqa: F401
    from .registry import models as _registry_models  # noqa: F401
    from .runtime import orm as _runtime_orm  # noqa: F401
    from .tenants import models as _tenant_models  # noqa: F401

    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
