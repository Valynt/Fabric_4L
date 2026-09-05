"""Principal context: a typed view of the acting identity.

Adapts the existing ``RequestContext`` / ``TokenClaims`` / ``AuthContext``
into a well-formed ``PrincipalContext`` that the policy engine can evaluate.
Per principle 3, roles and tenant supplied on the wire are normalized here
but every authoritative role assignment and tenant binding is VERIFIED
server-side by the attribute resolver before it influences a decision.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any, Iterable, Mapping

from .actions import PRINCIPAL_TYPES, PrincipalType


class PrincipalType_enum(str, enum.Enum):
    """Local mirror of principal types for self-contained construction."""

    HUMAN = PrincipalType.HUMAN.value
    AGENT = PrincipalType.AGENT.value
    SERVICE = PrincipalType.SERVICE.value
    SYSTEM = PrincipalType.SYSTEM.value
    EXTERNAL_VIEWER = PrincipalType.EXTERNAL_VIEWER.value


# The set of fields the policy engine may act on. Anything else supplied by a
# client (e.g. a spoofed ``roles`` claim) is ignored by the engine; the
# attribute resolver is the sole authority for role/tenant/resource facts.
_PRINCIPAL_FIELDS = frozenset(
    {
        "principal_type",
        "principal_id",
        "tenant_id",
        "user_id",
        "roles",
        "is_active",
        "is_system",
        "impersonator_id",
        "bound_tenant_ids",
    }
)


@dataclass(frozen=True)
class PrincipalContext:
    """Immutable, minimal principal projection safe to feed the PDP."""

    principal_type: str
    principal_id: str
    tenant_id: str | None = None
    user_id: str | None = None
    roles: frozenset[str] = frozenset()
    is_active: bool = True
    bound_tenant_ids: frozenset[str] = frozenset()
    impersonator_id: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "principal_type": self.principal_type,
            "principal_id": self.principal_id,
            "tenant_id": str(self.tenant_id) if self.tenant_id else None,
            "user_id": str(self.user_id) if self.user_id else None,
            "roles": sorted(self.roles),
            "is_active": self.is_active,
            "is_system": self.principal_type in {"system", "service"},
            "impersonator_id": self.impersonator_id,
            "bound_tenant_ids": sorted(self.bound_tenant_ids or ()),
        }

    @classmethod
    def build(
        cls,
        *,
        principal_type: str | PrincipalType | PrincipalType_enum,
        principal_id: str,
        tenant_id: str | None,
        roles: Iterable[str] = (),
        user_id: str | None = None,
        is_active: bool = True,
        bound_tenant_ids: Iterable[str] = (),
        impersonator_id: str | None = None,
    ) -> "PrincipalContext":
        """Construct with strict validation; fail closed on unknown types."""
        raw = (
            principal_type.value
            if hasattr(principal_type, "value")
            else str(principal_type)
        )
        if raw not in PRINCIPAL_TYPES:
            raise ValueError(f"unknown principal_type: {raw}")
        return cls(
            principal_type=raw,
            principal_id=str(principal_id),
            tenant_id=str(tenant_id) if tenant_id else None,
            user_id=str(user_id) if user_id else None,
            roles=frozenset(r for r in (roles or ())),
            is_active=bool(is_active),
            bound_tenant_ids=frozenset(str(t) for t in (bound_tenant_ids or ())),
            impersonator_id=str(impersonator_id) if impersonator_id else None,
        )


def _coerce_uuid(value: Any) -> str | None:
    if value is None:
        return None
    return str(value)


def principal_context_from_request(
    request_context: Mapping[str, Any] | Any,
) -> PrincipalContext:
    """Adapt the existing request identity into a ``PrincipalContext``.

    Accepts either:
      * a ``RequestContext``/``TokenClaims``-like object exposing
        ``tenant_id``, ``user_id``, ``roles``, auth-source attributes; or
      * a plain mapping.

    Roles are carried over verbatim here but MUST NOT be trusted — the
    attribute resolver re-derives authoritative role assignments from the
    ``authz_role_assignments`` table before a decision is made.
    """
    if not isinstance(request_context, Mapping):
        # Object-style access.
        def _get(name: str, default: Any = None) -> Any:
            value = getattr(request_context, name, default)
            if value is None:
                value = default
            return value

        raw = {
            "tenant_id": _coerce_uuid(_get("tenant_id")),
            "user_id": _coerce_uuid(_get("user_id")),
            "principal_id": _coerce_uuid(_get("user_id"))
            or _coerce_uuid(_get("service_account_id")),
            "roles": list(_get("roles", [])),
            "auth_source": _get("auth_source") or _get("source"),
            "org_id": _coerce_uuid(_get("org_id")),
            "impersonator_id": _coerce_uuid(_get("impersonator_id")),
        }
        obj = _SimpleNamespace(raw)
    else:
        obj = _SimpleNamespace(dict(request_context))

    # Infer principal type from auth source if not explicit.
    principal_type = _infer_principal_type(obj)

    return PrincipalContext.build(
        principal_type=principal_type,
        principal_id=obj.principal_id or obj.user_id or "anonymous",
        tenant_id=obj.tenant_id,
        user_id=obj.user_id,
        roles=list(obj.roles or ()),
        bound_tenant_ids=[obj.tenant_id] if obj.tenant_id else [],
        impersonator_id=obj.impersonator_id,
    )


def _infer_principal_type(ctx: "_SimpleNamespace") -> str:
    explicit = getattr(ctx, "principal_type", None)
    if explicit:
        return str(explicit)
    source = (getattr(ctx, "auth_source", None) or "").lower()
    principal_id = str(
        getattr(ctx, "principal_id", None) or getattr(ctx, "user_id", None) or ""
    ).lower()
    if "service" in source or getattr(ctx, "service_account_id", None):
        return PrincipalType.SERVICE.value
    if principal_id.startswith("service:"):
        return PrincipalType.SERVICE.value
    if "system" in source:
        return PrincipalType.SYSTEM.value
    if getattr(ctx, "is_agent", False) or getattr(ctx, "is_tool", False):
        return PrincipalType.AGENT.value
    if principal_id.startswith(("agent:", "tool:")):
        return PrincipalType.AGENT.value
    if "external" in source:
        return PrincipalType.EXTERNAL_VIEWER.value
    return PrincipalType.HUMAN.value


class _SimpleNamespace:
    """Tiny read-only attribute bag to normalize object/mapping access."""

    __slots__ = ("_data",)

    def __init__(self, data: dict[str, Any]) -> None:
        self._data = data

    def __getattr__(self, name: str) -> Any:
        value = self._data.get(name)
        # Expose lookup helpers used above.
        if name in {
            "principal_type",
            "auth_source",
            "service_account_id",
            "is_agent",
            "is_tool",
        }:
            return value
        return value
