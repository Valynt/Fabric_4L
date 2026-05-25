"""Thread-safe request context for tenant/user identity.

A single ``RequestContext`` is populated by ``GovernanceMiddleware`` at the
start of every request and stored in a ``ContextVar`` so any code that runs
within the same async task can retrieve it without threading it through
function signatures.

This module is the canonical shared identity contract used by all Fabric_4L
layers.  It intentionally carries the tenant, auth-source, trace, isolation,
and privileged-access fields required by governance middleware and security
checks so layer implementations do not create ad-hoc cross-layer shortcuts.
"""

from __future__ import annotations

from contextvars import ContextVar, Token
from dataclasses import dataclass, field
from typing import Any, Dict, FrozenSet, Iterable, List, Optional, Set
from uuid import UUID

from .permissions import Permission, Role
from value_fabric.shared.models.typed_dict import TypedDictModel

# Auth source constants
AUTH_SOURCE_JWT = "jwt_claim"
AUTH_SOURCE_API_KEY = "api_key"
AUTH_SOURCE_SERVICE_ACCOUNT = "service_account"
AUTH_SOURCE_UNKNOWN = "unknown"
VALID_AUTH_SOURCES = {
    AUTH_SOURCE_JWT,
    AUTH_SOURCE_API_KEY,
    AUTH_SOURCE_SERVICE_ACCOUNT,
}
_LEGACY_AUTH_SOURCE_ALIASES = {
    "jwt": AUTH_SOURCE_JWT,
    "bearer": AUTH_SOURCE_JWT,
    "api-key": AUTH_SOURCE_API_KEY,
    "api_key": AUTH_SOURCE_API_KEY,
    "service-account": AUTH_SOURCE_SERVICE_ACCOUNT,
    "service_account": AUTH_SOURCE_SERVICE_ACCOUNT,
}

# Tenant isolation tier constants
ISOLATION_TIER_SHARED = "shared"
ISOLATION_TIER_SCHEMA = "schema"
ISOLATION_TIER_DATABASE = "database"
VALID_ISOLATION_TIERS = {ISOLATION_TIER_SHARED, ISOLATION_TIER_SCHEMA, ISOLATION_TIER_DATABASE}


class RequestContext_to_log_dictResult(TypedDictModel):
    api_key_id: Any
    auth_source: Any
    roles: Any
    source: Any
    tenant_id: Any
    user_id: Any
    request_id: Any


def _normalise_auth_source(value: Optional[str]) -> str:
    if not value:
        return AUTH_SOURCE_UNKNOWN
    return _LEGACY_AUTH_SOURCE_ALIASES.get(value, value)


def _coerce_str_list(values: Optional[Iterable[Any]]) -> List[str]:
    if values is None:
        return []
    return [str(value) for value in values]


@dataclass
class RequestContext:
    """Identity context carried by a single request.

    ``RequestContext`` is deliberately shared by L1-L5 governance code.  It
    preserves tenant scoping and trace propagation while supporting legacy
    callers that still pass ``source`` and newer middleware that passes the
    explicit ``auth_source`` field.
    """

    tenant_id: Optional[UUID | str] = None
    user_id: Optional[Any] = None
    roles: List[str] = field(default_factory=list)
    api_key_id: Optional[str] = None
    permissions: FrozenSet[Permission | str] | Iterable[Permission | str] = field(default_factory=frozenset)
    source: str = AUTH_SOURCE_JWT
    raw: Dict[str, Any] = field(default_factory=dict)
    auth_source: Optional[str] = None
    request_id: Optional[str] = None
    org_id: Optional[Any] = None
    workspace_id: Optional[Any] = None
    tenant_role: Optional[str] = None
    trace_id: Optional[str] = None
    isolation_tier: str = ISOLATION_TIER_SHARED
    service_account_id: Optional[str] = None
    service_account_scopes: List[str] = field(default_factory=list)
    accessed_tenant_ids: Set[str] = field(default_factory=set)
    privileged_session_start: Optional[float] = None
    impersonator_id: Optional[str] = None
    _locked: bool = field(default=False, init=False, repr=False, compare=False)

    def __post_init__(self) -> None:
        object.__setattr__(self, "roles", _coerce_str_list(self.roles))
        object.__setattr__(self, "permissions", frozenset(self.permissions or []))
        object.__setattr__(self, "service_account_scopes", _coerce_str_list(self.service_account_scopes))
        object.__setattr__(
            self,
            "accessed_tenant_ids",
            {str(tenant_id) for tenant_id in (self.accessed_tenant_ids or set())},
        )

        source_for_auth = self.source if self.auth_source is None else self.auth_source
        normalised_auth_source = _normalise_auth_source(source_for_auth)
        object.__setattr__(self, "auth_source", normalised_auth_source)
        if self.source == AUTH_SOURCE_UNKNOWN and normalised_auth_source != AUTH_SOURCE_UNKNOWN:
            object.__setattr__(self, "source", normalised_auth_source)
        else:
            object.__setattr__(self, "source", _normalise_auth_source(self.source))
        object.__setattr__(self, "_locked", True)

    def __setattr__(self, name: str, value: Any) -> None:
        """Protect escalation-sensitive identity fields after construction.

        Tenant identity, workspace scope, and permission assignments remain
        immutable for the cross-layer security contract, while privileged-audit
        bookkeeping fields such as ``accessed_tenant_ids`` and
        ``privileged_session_start`` remain mutable so audit instrumentation
        can record runtime session details.
        """
        if getattr(self, "_locked", False) and name in {"tenant_id", "permissions", "workspace_id"}:
            raise AttributeError(f"cannot assign to immutable RequestContext field '{name}'")
        super().__setattr__(name, value)

    # ------------------------------------------------------------------
    # Role / permission helpers
    # ------------------------------------------------------------------

    def has_role(self, role: Role | str) -> bool:
        """Return True if this context carries the given role."""
        role_val = role.value if isinstance(role, Role) else role
        return role_val in self.roles

    def has_any_role(self, *roles: Role | str) -> bool:
        return any(self.has_role(r) for r in roles)

    def is_super_admin(self) -> bool:
        """Return True only for explicit super-admin role membership."""
        return self.has_role(Role.SUPER_ADMIN) or self.has_role("super_admin")

    def has_permission(self, permission: Permission | str) -> bool:
        """Return True if the effective permission set includes *permission*.

        Only known ``Permission`` enum values are matched. Raw strings that are
        not valid enum members (including wildcards like ``"*"`` or ``"all"``)
        are never treated as granting access — the check fails closed.
        """
        # Resolve the requested permission to its canonical enum value string.
        # Unknown strings are rejected immediately (fail closed).
        if isinstance(permission, Permission):
            permission_val = permission.value
        else:
            try:
                permission_val = Permission(permission).value
            except ValueError:
                return False

        # Build the set of known permission values in a single pass.
        # Permission enum instances are resolved directly; raw strings are
        # coerced through the enum and discarded if unrecognised (including
        # wildcards like "*" or "all" that may have slipped through from a
        # JWT claim before extract_context_from_jwt filtering was in place).
        known_values: set[str] = set()
        for p in self.permissions:
            if isinstance(p, Permission):
                known_values.add(p.value)
            else:
                try:
                    known_values.add(Permission(str(p)).value)
                except ValueError:
                    pass  # unknown string — discard silently

        return permission_val in known_values

    def has_any_permission(self, *permissions: Permission | str) -> bool:
        return any(self.has_permission(p) for p in permissions)

    def has_all_permissions(self, *permissions: Permission | str) -> bool:
        return all(self.has_permission(p) for p in permissions)

    # ------------------------------------------------------------------
    # Validation / serialisation helpers
    # ------------------------------------------------------------------

    def is_auth_source_valid(self) -> bool:
        """Return True when the context was resolved by an approved auth source."""
        return self.auth_source in VALID_AUTH_SOURCES

    def is_service_account(self) -> bool:
        """Return True when this context represents a service account."""
        return self.service_account_id is not None

    def is_isolation_tier_valid(self) -> bool:
        """Return True when the isolation tier is a valid value."""
        return self.isolation_tier in VALID_ISOLATION_TIERS

    def validate(self) -> List[str]:
        """Return fail-closed validation errors for identity/governance checks."""
        errors: List[str] = []

        if not self.tenant_id:
            errors.append("tenant_id is required")

        if not self.auth_source or not self.is_auth_source_valid():
            errors.append(f"auth_source must be one of {sorted(VALID_AUTH_SOURCES)}")

        if self.isolation_tier not in VALID_ISOLATION_TIERS:
            errors.append(f"isolation_tier must be one of {sorted(VALID_ISOLATION_TIERS)}")

        if self.auth_source == AUTH_SOURCE_SERVICE_ACCOUNT:
            if not self.service_account_id:
                errors.append("service account auth_source requires service_account_id")
            if not self.service_account_scopes:
                errors.append("service account auth_source requires non-empty service_account_scopes")

        return errors

    def to_dict(self) -> Dict[str, Any]:
        """Serialise the non-secret request context for cross-layer contracts."""
        return {
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id) if self.user_id is not None else None,
            "api_key_id": self.api_key_id,
            "org_id": str(self.org_id) if self.org_id is not None else None,
            "workspace_id": str(self.workspace_id) if self.workspace_id is not None else None,
            "service_account_id": self.service_account_id,
            "roles": list(self.roles),
            "permissions": [
                value.value if isinstance(value, Permission) else str(value)
                for value in self.permissions
            ],
            "tenant_role": self.tenant_role,
            "isolation_tier": self.isolation_tier,
            "auth_source": self.auth_source,
            "source": self.source,
            "service_account_scopes": list(self.service_account_scopes),
            "request_id": self.request_id,
            "impersonator_id": self.impersonator_id,
        }

    def to_log_dict(self) -> Dict[str, Any]:
        """Serialise for structured logging without sensitive data."""
        return RequestContext_to_log_dictResult.model_validate({
            "tenant_id": str(self.tenant_id),
            "user_id": str(self.user_id) if self.user_id is not None else None,
            "roles": list(self.roles),
            "api_key_id": self.api_key_id,
            "source": self.source,
            "auth_source": self.auth_source,
            "request_id": self.request_id,
        })


# ---------------------------------------------------------------------------
# ContextVar storage
# ---------------------------------------------------------------------------

_current_context: ContextVar[Optional[RequestContext]] = ContextVar(
    "vf_request_context",
    default=None,
)


def get_request_context() -> Optional[RequestContext]:
    """Return the current request context, or ``None`` if not set."""
    return _current_context.get()


def get_current_context() -> Optional[RequestContext]:
    """Legacy alias for ``get_request_context`` used by older tests and routes."""
    return get_request_context()


def set_request_context(ctx: Optional[RequestContext]) -> Token:
    """Set the request context and return the reset token."""
    return _current_context.set(ctx)


def set_current_context(ctx: Optional[RequestContext]) -> Token:
    """Legacy alias for ``set_request_context`` used by older tests and routes."""
    return set_request_context(ctx)


def clear_current_context() -> None:
    """Clear the current request context for request-end or test isolation."""
    _current_context.set(None)


def require_context() -> RequestContext:
    """Return the current context or raise ``RuntimeError``.

    Use this in code paths that *must* run within an authenticated request.
    """
    ctx = _current_context.get()
    if ctx is None:
        raise RuntimeError(
            "No RequestContext is set — ensure GovernanceMiddleware is installed "
            "and the endpoint is not bypassing authentication."
        )
    return ctx


class RequestContextManager:
    """Sync context manager for setting the request context.

    Useful in tests and background tasks where there is no HTTP middleware.
    """

    def __init__(self, ctx: RequestContext) -> None:
        self._ctx = ctx
        self._token: Optional[Token] = None

    def __enter__(self) -> "RequestContextManager":
        self._token = set_request_context(self._ctx)
        return self

    def __exit__(self, *args: Any) -> None:
        if self._token is not None:
            _current_context.reset(self._token)
