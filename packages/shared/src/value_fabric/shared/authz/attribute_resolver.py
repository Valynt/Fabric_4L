"""Policy Information Point (PIP): resolves server-side facts for a request.

Per principle 3, the PDP may NEVER trust tenant IDs, roles, resource
attributes, or approval state supplied by the client. This resolver is the
sole authority that reads authoritative role assignments (authz_role_assignments),
resource/opportunity bindings, approval ceilings, delegation/external/break-glass
grants, and current resource state from server-owned storage, and injects them
into the request environment as ``resource_attributes`` and ``relationships``.
"""

from __future__ import annotations

from typing import Any, Awaitable, Callable

from .models import AuthzEnvironment, AuthzRequest


class AttributeResolver:
    """Enriches an AuthzRequest with server-side facts.

    Subclasses/instances implement ``resolve`` returning ``(attrs, relationships)``.
    The default no-op resolver leaves facts as-is for pure-engine tests.
    """

    def __init__(self, *, fetcher: Callable[[AuthzRequest], Awaitable[dict]] | None = None) -> None:
        # ``fetcher`` returns a dict with keys 'attributes' and 'relationships'.
        self._fetcher = fetcher

    async def resolve(self, request: AuthzRequest) -> tuple[dict, dict]:
        internal = _as_authz_request(request)
        if self._fetcher is not None:
            result = await self._fetcher(internal)
            attrs = result.get("attributes", {}) if isinstance(result, dict) else {}
            rel = result.get("relationships", {}) if isinstance(result, dict) else {}
            return attrs, rel
        attrs = dict(internal.environment.resource_attributes or {})
        rel = dict(internal.environment.relationships or {})
        return attrs, rel


def _as_authz_request(request: Any) -> AuthzRequest:
    """Coerce a request-like object to AuthzRequest (tolerant of plain dicts)."""
    if isinstance(request, AuthzRequest):
        return request
    if hasattr(request, "action") and hasattr(request, "resource"):
        # Duck-typed request carrying the expected fields.
        return AuthzRequest(
            action=request.action,
            principal=request.principal,
            resource=dict(request.resource or {}),
            environment=getattr(request, "environment", None) or AuthzEnvironment(),
            requested_resource_revision=getattr(request, "requested_resource_revision", None),
        )
    raise TypeError("expected AuthzRequest or request-like object")


class StaticAttributeResolver(AttributeResolver):
    """Test/onboarding-resolver that answers from a provided map of
    resource_id -> {attributes, relationships} without any I/O."""

    def __init__(self, *, facts: dict[str, dict] | None = None, current_revision: str | None = None, **kwargs) -> None:
        super().__init__(**kwargs)
        self._facts = facts or {}
        self._current_revision = current_revision

    async def resolve(self, request: AuthzRequest) -> tuple[dict, dict]:
        internal = _as_authz_request(request)
        resource_id = internal.resource.get("id") if isinstance(internal.resource, dict) else None
        entry = self._facts.get(str(resource_id), {}) if resource_id else {}
        attrs = dict(entry.get("attributes", {}))
        rel = dict(entry.get("relationships", {}))
        if self._current_revision:
            attrs.setdefault("revision", self._current_revision)
        return attrs, rel