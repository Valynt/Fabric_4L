from __future__ import annotations

"""Centralised tenant-spoofing guard for layer4 agents.

Deduplicates the tenant_id mismatch checks that previously existed as inline
blocks in each knowledge tool. All six knowledge tools now route their raise
path through :func:`enforce_tenant_context` so they share one
``TenantSpoofingError`` exit shape and one message.

The exception type is imported lazily to avoid a hard import cycle at module
load time: ``tools/registry`` has no dependency on this module, and
``tools/knowledge_tools`` imports both, so a top-level import here would be
safe in practice, but we keep it deferred to remain robust to future import
reordering.
"""

from uuid import UUID


def enforce_tenant_context(
    payload_tenant_id: str | UUID | None,
    authenticated_tenant_id: str | UUID | None,
) -> None:
    """Raise ``TenantSpoofingError`` if a supplied tenant_id mismatches context.

    Args:
        payload_tenant_id: The tenant_id supplied on the tool input/payload,
            or ``None`` if the caller did not supply one. A ``None`` value is
            treated as "not supplied" and does not raise (the caller already
            scopes the query with the authenticated tenant).
        authenticated_tenant_id: The tenant_id from the authenticated context.

    Raises:
        TenantSpoofingError: If ``payload_tenant_id`` is not ``None`` and does
            not equal ``authenticated_tenant_id`` (string-compared).
    """
    if payload_tenant_id is None:
        return
    if str(payload_tenant_id) != str(authenticated_tenant_id):
        from layer4_agents.tools.registry import TenantSpoofingError

        raise TenantSpoofingError(
            "Tenant spoofing detected: payload tenant_id does not match authenticated context"
        )
