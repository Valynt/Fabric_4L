from __future__ import annotations

"""Shared Neo4j query helpers with tenant-context validation for Layer 4.

DEPRECATED: This module is kept for backward compatibility. New code should
use ``layer4_agents.services.tenant_cypher`` directly.
"""


from typing import Any

from layer4_agents.services.tenant_cypher import (
    TenantCypherValidationError,
    fetch_tenant_validated_records,
)

__all__ = ["run_tenant_validated_query", "TenantCypherValidationError"]


async def run_tenant_validated_query(
    *,
    driver: Any | None,
    query: str,
    tenant_id: str,
    params: dict[str, Any] | None = None,
) -> list[Any]:
    """Deprecated: use tenant_cypher.fetch_tenant_validated_records directly.

    Preserves the legacy behavior of rejecting an explicit tenant_id parameter
    that does not match the authenticated tenant context.
    """
    params = params or {}
    supplied_tenant_id = params.get("tenant_id")
    if supplied_tenant_id is not None and supplied_tenant_id != tenant_id:
        raise ValueError("Tenant context mismatch")
    return await fetch_tenant_validated_records(
        driver=driver,
        query=query,
        params=params,
        tenant_id=tenant_id,
        operation="run_tenant_validated_query",
    )
