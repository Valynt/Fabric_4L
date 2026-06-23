from __future__ import annotations

"""Cypher query templates used by Layer 4 workflows.

.. deprecated::
    These query builders are superseded by the Layer 3 subgraph API:

    - ``Layer3Client.get_benchmark_variables(industry)``
      → ``GET /v1/knowledge/benchmarks/variables``
    - ``Layer3Client.get_value_driver_formulas(driver_ids)``
      → ``GET /v1/knowledge/value-drivers/formulas``

    New workflows should call the Layer 3 client methods directly.
    Existing callers of these helpers should be migrated; this module
    will be removed once all callers are updated.
"""


from typing import Any


def get_benchmark_variables_query(industry: str, tenant_id: str | None = None) -> dict[str, Any]:
    """Return query to fetch benchmark variables and defaults for an industry.

    Args:
        industry: Industry vertical to filter benchmarks.
        tenant_id: Optional tenant scope. When provided the query is
            narrowed to nodes owned by that tenant.

    Returns:
        Dict with ``cypher_query`` and ``parameters`` ready for the
        ``query_graph`` tool.
    """
    if not industry or not isinstance(industry, str):
        raise ValueError("industry must be a non-empty string")

    cypher = """
        MATCH (v:ValueDriver)-[:HAS_BENCHMARK]->(b:Benchmark)
        WHERE b.industry = $industry
    """
    params: dict[str, Any] = {"industry": industry}

    if tenant_id:
        cypher += " AND b.tenant_id = $tenant_id"
        params["tenant_id"] = tenant_id

    cypher += """
        RETURN b.variables AS variables, b.defaults AS defaults
        ORDER BY b.updated_at DESC
        LIMIT 1
    """

    return {"cypher_query": cypher, "parameters": params}


def get_value_driver_formulas_query(
    driver_ids: list[str], tenant_id: str | None = None
) -> dict[str, Any]:
    """Return query to fetch value driver formulas by ID list.

    Args:
        driver_ids: List of value-driver identifiers. Must be non-empty.
        tenant_id: Optional tenant scope.

    Returns:
        Dict with ``cypher_query`` and ``parameters`` ready for the
        ``query_graph`` tool.
    """
    if not driver_ids:
        raise ValueError("driver_ids must be a non-empty list")
    if not all(isinstance(d, str) and d for d in driver_ids):
        raise ValueError("all driver_ids must be non-empty strings")

    cypher = """
        MATCH (v:ValueDriver)
        WHERE v.id IN $driver_ids
    """
    params: dict[str, Any] = {"driver_ids": driver_ids}

    if tenant_id:
        cypher += " AND v.tenant_id = $tenant_id"
        params["tenant_id"] = tenant_id

    cypher += """
        RETURN v.id AS id, v.name AS name, v.category AS category,
               v.formula AS formula, v.unit AS unit
    """

    return {"cypher_query": cypher, "parameters": params}
