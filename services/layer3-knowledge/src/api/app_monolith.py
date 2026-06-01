from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import AuthenticationError

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Compatibility shim exposing _resolve_ingest_tenant_id under the
legacy app_monolith namespace. Tests and callers should migrate to
services/layer3-knowledge/src/api/services/tenant_resolution.py
(``api.services.tenant_resolution.resolve_ingest_tenant_id``).
"""


from .services.tenant_resolution import resolve_ingest_tenant_id as _canonical


def _resolve_ingest_tenant_id(
    authenticated_tenant_id: str,
    header_tenant_id: str | None,
    body_tenant_id: str | None,
    *,
    allow_tenant_hints: bool,
) -> str:
    """Compatibility wrapper — delegates to tenant_resolution.resolve_ingest_tenant_id.

    Raises(401) when authenticated_tenant_id is empty (legacy
    behaviour expected by test_ingest_tenant_fail_closed.py).
    """
    if not (authenticated_tenant_id or "").strip():
        raise AuthenticationError(message = "Authentication context is required")
    return _canonical(
        authenticated_tenant_id,
        header_tenant_id,
        body_tenant_id,
        allow_tenant_hints=allow_tenant_hints,
    )


__all__ = ["_resolve_ingest_tenant_id"]
