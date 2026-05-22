"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Layer 3 knowledge subgraph endpoints consumed by Layer 4 agents.

Provides two read-only endpoints that replace the Cypher-in-L4 arch debt
tracked in ``services/layer4-agents/src/workflows/queries.py``:

- ``GET /v1/knowledge/benchmarks/variables``
  Returns benchmark variables and defaults for an industry vertical.
  Replaces ``get_benchmark_variables_query()`` in L4.

- ``GET /v1/knowledge/value-drivers/formulas``
  Returns value driver formulas by ID list.
  Replaces ``get_value_driver_formulas_query()`` in L4.

All queries are tenant-scoped via ``create_neo4j_tenant_session``.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from logging_config import get_logger

from ...api.dependencies_tenant_secured import create_neo4j_tenant_session
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_context

logger = get_logger(__name__)

router = APIRouter()


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class BenchmarkVariablesResponse(BaseModel):
    """Benchmark variables and defaults for an industry vertical."""

    industry: str
    variables: dict[str, Any] = Field(
        default_factory=dict,
        description="Variable definitions keyed by variable name",
    )
    defaults: dict[str, Any] = Field(
        default_factory=dict,
        description="Default values keyed by variable name",
    )
    benchmark_id: str | None = Field(
        None, description="ID of the most-recently-updated matching Benchmark node"
    )


class ValueDriverFormula(BaseModel):
    """Formula definition for a single value driver."""

    id: str
    name: str
    category: str | None = None
    formula: str | None = None
    unit: str | None = None


class ValueDriverFormulasResponse(BaseModel):
    """Value driver formulas for a list of driver IDs."""

    drivers: list[ValueDriverFormula]
    missing_ids: list[str] = Field(
        default_factory=list,
        description="Requested IDs that were not found in the graph",
    )


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.get(
    "/knowledge/benchmarks/variables",
    response_model=BenchmarkVariablesResponse,
    summary="Get benchmark variables for an industry",
    tags=["knowledge"],
)
async def get_benchmark_variables(
    industry: str = Query(..., description="Industry vertical to look up"),
    tenant: RequestContext = Depends(require_tenant_context),
) -> BenchmarkVariablesResponse:
    """Return benchmark variables and defaults for the given industry.

    Queries the most-recently-updated ``Benchmark`` node linked to a
    ``ValueDriver`` for the requested industry, scoped to the caller's tenant.

    Used by Layer 4 agents to resolve benchmark context without embedding
    Cypher in the agent layer.
    """
    tenant_id = str(tenant.tenant_id)

    query = """
        MATCH (v:ValueDriver)-[:HAS_BENCHMARK]->(b:Benchmark)
        WHERE b.industry = $industry
          AND b.tenant_id = $tenant_id
          AND v.tenant_id = $tenant_id
        RETURN b.id AS benchmark_id,
               b.variables AS variables,
               b.defaults AS defaults
        ORDER BY b.updated_at DESC
        LIMIT 1
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, industry=industry, tenant_id=tenant_id)
        records = await result.data()

    if not records:
        # Return an empty-but-valid response rather than 404 — callers should
        # treat missing benchmark data as "no data available" and fall back to
        # pack defaults, not as an error.
        logger.info(
            "no benchmark variables found",
            extra={"industry": industry, "tenant_id": tenant_id},
        )
        return BenchmarkVariablesResponse(industry=industry)

    row = records[0]
    return BenchmarkVariablesResponse(
        industry=industry,
        benchmark_id=row.get("benchmark_id"),
        variables=row.get("variables") or {},
        defaults=row.get("defaults") or {},
    )


@router.get(
    "/knowledge/value-drivers/formulas",
    response_model=ValueDriverFormulasResponse,
    summary="Get value driver formulas by ID list",
    tags=["knowledge"],
)
async def get_value_driver_formulas(
    driver_ids: list[str] = Query(
        ...,
        description="Value driver IDs to look up (repeat parameter for multiple)",
    ),
    tenant: RequestContext = Depends(require_tenant_context),
) -> ValueDriverFormulasResponse:
    """Return formula definitions for the requested value driver IDs.

    Queries ``ValueDriver`` nodes by ID, scoped to the caller's tenant.
    IDs not found in the graph are reported in ``missing_ids`` rather than
    raising an error, so callers can handle partial results gracefully.

    Used by Layer 4 agents to resolve formula context without embedding
    Cypher in the agent layer.
    """
    tenant_id = str(tenant.tenant_id)

    if not driver_ids:
        raise HTTPException(status_code=422, detail="driver_ids must not be empty")

    # Deduplicate while preserving order for deterministic missing_ids reporting
    seen: set[str] = set()
    unique_ids: list[str] = []
    for d in driver_ids:
        if d and d not in seen:
            seen.add(d)
            unique_ids.append(d)

    if not unique_ids:
        raise HTTPException(status_code=422, detail="driver_ids must contain non-empty strings")

    query = """
        MATCH (v:ValueDriver)
        WHERE v.id IN $driver_ids
          AND v.tenant_id = $tenant_id
        RETURN v.id AS id,
               v.name AS name,
               v.category AS category,
               v.formula AS formula,
               v.unit AS unit
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, driver_ids=unique_ids, tenant_id=tenant_id)
        records = await result.data()

    found_ids = {r["id"] for r in records}
    missing_ids = [d for d in unique_ids if d not in found_ids]

    if missing_ids:
        logger.info(
            "value driver IDs not found in graph",
            extra={"missing_ids": missing_ids, "tenant_id": tenant_id},
        )

    return ValueDriverFormulasResponse(
        drivers=[
            ValueDriverFormula(
                id=r["id"],
                name=r["name"],
                category=r.get("category"),
                formula=r.get("formula"),
                unit=r.get("unit"),
            )
            for r in records
        ],
        missing_ids=missing_ids,
    )
