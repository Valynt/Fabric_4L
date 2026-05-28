from __future__ import annotations

"""Shared Neo4j query helpers with tenant-context validation for Layer 4."""


from typing import Any


async def run_tenant_validated_query(
    *,
    driver: Any | None,
    query: str,
    tenant_id: str,
    params: dict[str, Any] | None = None,
) -> list[Any]:
    """Execute a Neo4j query while enforcing tenant parameter consistency.

    - Fails closed when no driver is provided.
    - Rejects mismatched tenant IDs from call-site parameters.
    - Always sends authenticated tenant_id value to Neo4j.
    """
    if not driver:
        return []

    scoped_params = dict(params or {})
    provided_tenant = scoped_params.get("tenant_id")
    if provided_tenant is not None and provided_tenant != tenant_id:
        raise ValueError("Tenant context mismatch for Neo4j query")
    scoped_params["tenant_id"] = tenant_id

    async with driver.session() as session:
        result = await session.run(query, scoped_params)
        return [record async for record in result]
