"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Benchmark API routes for Layer 3.

Provides endpoints for benchmark CRUD and policy management.
Benchmarks are stored as Neo4j Benchmark nodes and may be linked to
ValuePacks via hasBenchmark relationships.

All Cypher queries are tenant-scoped via `create_neo4j_tenant_session`.
"""

from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field

from logging_config import get_logger

from ...api.dependencies_tenant_secured import create_neo4j_tenant_session
from ...api.routes._utils import get_tenant_id_from_api_key
from ...auth.api_keys import APIKey
from ...auth.middleware import get_current_api_key

logger = get_logger(__name__)

router = APIRouter()


def _get_authenticated_tenant_id(api_key: APIKey) -> str:
    """Resolve tenant ID from authenticated API-key context; fail closed if absent.

    Delegates to the shared get_tenant_id_from_api_key helper in _utils.
    """
    return get_tenant_id_from_api_key(api_key)


# Pagination limits
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 50


# ── Pydantic Models ──────────────────────────────────────────────────────────


class BenchmarkSummary(BaseModel):
    """Benchmark list item."""

    id: str
    benchmark_id: str
    name: str
    industry: str
    vertical: str | None = None
    value_range: str
    confidence: Literal["High", "Medium", "Low"]
    source: str
    source_url: str | None = None
    year: int
    status: Literal["active", "draft", "deprecated"]
    tags: list[str] = Field(default_factory=list)
    last_verified: str | None = None
    usage_count: int = 0
    description: str | None = None


class BenchmarkPolicy(BaseModel):
    """Benchmark policy configuration."""

    id: str
    policy_type: Literal["threshold", "cadence", "fallback", "override"]
    name: str
    description: str
    value: str
    is_enabled: bool = True
    scope: Literal["tenant", "pack", "formula"]


class BenchmarkPolicyUpdate(BaseModel):
    """Update payload for a benchmark policy (all fields optional)."""

    name: str | None = None
    description: str | None = None
    value: str | None = None
    is_enabled: bool | None = None
    scope: Literal["tenant", "pack", "formula"] | None = None


# ── Endpoints ────────────────────────────────────────────────────────────────


@router.get("/benchmarks", response_model=list[BenchmarkSummary])
async def list_benchmarks(
    industry: str | None = Query(None, description="Filter by industry"),
    status: str | None = Query(None, description="Filter by status"),
    confidence: str | None = Query(None, description="Filter by confidence level"),
    search: str | None = Query(None, description="Search benchmarks by name"),
    limit: int = Query(DEFAULT_PAGE_SIZE, ge=1, le=MAX_PAGE_SIZE, description="Maximum results to return"),
    api_key: APIKey = Depends(get_current_api_key),
):
    """List benchmarks with optional filters."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    where_conditions: list[str] = []
    params: dict[str, Any] = {"limit": limit, "tenant_id": tenant_id}

    if industry:
        where_conditions.append("b.industry = $industry")
        params["industry"] = industry

    if status:
        where_conditions.append("b.status = $status")
        params["status"] = status

    if confidence:
        where_conditions.append("b.confidence = $confidence")
        params["confidence"] = confidence

    if search:
        where_conditions.append("toLower(b.name) CONTAINS toLower($search)")
        params["search"] = search

    extra_where = ""
    if where_conditions:
        extra_where = "AND " + " AND ".join(where_conditions)

    query = f"""
    MATCH (b:Benchmark)
    WHERE b.tenant_id = $tenant_id
    {extra_where}
    OPTIONAL MATCH (vp:ValuePack)-[:hasBenchmark]->(b)
    RETURN b, count(DISTINCT vp) as usage_count
    ORDER BY b.name
    LIMIT $limit
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, **params)
        records = await result.data()

        current_year = datetime.now(UTC).year
        return [
            BenchmarkSummary(
                id=r["b"]["id"],
                benchmark_id=r["b"].get("benchmarkId", r["b"]["id"]),
                name=r["b"]["name"],
                industry=r["b"].get("industry", "General"),
                vertical=r["b"].get("vertical"),
                value_range=r["b"].get("valueRange", ""),
                confidence=r["b"].get("confidence", "Medium"),
                source=r["b"].get("source", ""),
                source_url=r["b"].get("sourceUrl"),
                year=r["b"].get("year", current_year),
                status=r["b"].get("status", "active"),
                tags=r["b"].get("tags", [])
                if isinstance(r["b"].get("tags"), list)
                else [],
                last_verified=r["b"].get("lastVerified"),
                usage_count=r.get("usage_count", 0),
                description=r["b"].get("description"),
            )
            for r in records
        ]


@router.get("/benchmarks/policies", response_model=list[BenchmarkPolicy])
async def list_benchmark_policies(
    api_key: APIKey = Depends(get_current_api_key),
):
    """List benchmark policy configurations."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    query = """
    MATCH (bp:BenchmarkPolicy)
    WHERE bp.tenant_id = $tenant_id
    RETURN bp
    ORDER BY bp.name
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, tenant_id=tenant_id)
        records = await result.data()

        return [
            BenchmarkPolicy(
                id=r["bp"]["id"],
                policy_type=r["bp"]["policyType"],
                name=r["bp"]["name"],
                description=r["bp"].get("description", ""),
                value=r["bp"].get("value", ""),
                is_enabled=r["bp"].get("isEnabled", True),
                scope=r["bp"].get("scope", "tenant"),
            )
            for r in records
        ]


@router.get("/benchmarks/{benchmark_id}", response_model=BenchmarkSummary)
async def get_benchmark(
    benchmark_id: str,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Get a single benchmark by ID."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    query = """
    MATCH (b:Benchmark {id: $benchmark_id})
    WHERE b.tenant_id = $tenant_id
    OPTIONAL MATCH (vp:ValuePack)-[:hasBenchmark]->(b)
    RETURN b, count(DISTINCT vp) as usage_count
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, benchmark_id=benchmark_id, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Benchmark not found")

        b = record["b"]
        current_year = datetime.now(UTC).year
        return BenchmarkSummary(
            id=b["id"],
            benchmark_id=b.get("benchmarkId", b["id"]),
            name=b["name"],
            industry=b.get("industry", "General"),
            vertical=b.get("vertical"),
            value_range=b.get("valueRange", ""),
            confidence=b.get("confidence", "Medium"),
            source=b.get("source", ""),
            source_url=b.get("sourceUrl"),
            year=b.get("year", current_year),
            status=b.get("status", "active"),
            tags=b.get("tags", []) if isinstance(b.get("tags"), list) else [],
            last_verified=b.get("lastVerified"),
            usage_count=record.get("usage_count", 0),
            description=b.get("description"),
        )


@router.put("/benchmarks/policies/{policy_id}", response_model=BenchmarkPolicy)
async def update_benchmark_policy(
    policy_id: str,
    update: BenchmarkPolicyUpdate,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Update a benchmark policy."""
    tenant_id = _get_authenticated_tenant_id(api_key)
    # Build SET clauses dynamically from provided fields
    set_parts: list[str] = []
    params: dict[str, Any] = {"policy_id": policy_id, "tenant_id": tenant_id}

    update_data = update.model_dump(exclude_none=True)
    field_map = {
        "name": "name",
        "description": "description",
        "value": "value",
        "is_enabled": "isEnabled",
        "scope": "scope",
    }

    for py_field, neo_field in field_map.items():
        if py_field in update_data:
            set_parts.append(f"bp.{neo_field} = ${py_field}")
            params[py_field] = update_data[py_field]

    if not set_parts:
        raise HTTPException(status_code=400, detail="No fields to update")

    now = datetime.now(UTC).isoformat()
    set_parts.append("bp.updatedAt = $updated_at")
    params["updated_at"] = now

    set_clause = ", ".join(set_parts)

    query = f"""
    MATCH (bp:BenchmarkPolicy {{id: $policy_id}})
    WHERE bp.tenant_id = $tenant_id
    SET {set_clause}
    RETURN bp
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, **params)
        record = await result.single()

        if not record:
            raise HTTPException(status_code=404, detail="Policy not found")

        bp = record["bp"]
        return BenchmarkPolicy(
            id=bp["id"],
            policy_type=bp["policyType"],
            name=bp["name"],
            description=bp.get("description", ""),
            value=bp.get("value", ""),
            is_enabled=bp.get("isEnabled", True),
            scope=bp.get("scope", "tenant"),
        )


# ── Default Policy Seeding ───────────────────────────────────────────────────


DEFAULT_BENCHMARK_POLICIES = [
    {
        "id": "bp-freshness-threshold",
        "policyType": "cadence",
        "name": "Freshness Threshold",
        "description": "Maximum age before a benchmark is considered stale",
        "value": "90",
        "isEnabled": True,
        "scope": "tenant",
    },
    {
        "id": "bp-confidence-floor",
        "policyType": "threshold",
        "name": "Confidence Floor",
        "description": "Minimum confidence level required for benchmark inclusion",
        "value": "Medium",
        "isEnabled": True,
        "scope": "tenant",
    },
    {
        "id": "bp-admin-override",
        "policyType": "override",
        "name": "Admin Override",
        "description": "Allows administrators to override benchmark values in formula evaluation",
        "value": "enabled",
        "isEnabled": True,
        "scope": "tenant",
    },
]


@router.post("/benchmarks/policies/seed", response_model=list[BenchmarkPolicy])
async def seed_benchmark_policies(
    api_key: APIKey = Depends(get_current_api_key),
):
    """Seed default benchmark policies if none exist. Idempotent."""
    tenant_id = _get_authenticated_tenant_id(api_key)

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        created: list[BenchmarkPolicy] = []
        for policy in DEFAULT_BENCHMARK_POLICIES:
            query = """
            MERGE (bp:BenchmarkPolicy {id: $id, tenant_id: $tenant_id})
            ON CREATE SET
                bp.policyType = $policyType,
                bp.name = $name,
                bp.description = $description,
                bp.value = $value,
                bp.isEnabled = $isEnabled,
                bp.scope = $scope,
                bp.createdAt = $now,
                bp.updatedAt = $now
            ON MATCH SET
                bp.updatedAt = $now
            RETURN bp
            """
            result = await neo4j.run(
                query,
                id=policy["id"],
                tenant_id=tenant_id,
                policyType=policy["policyType"],
                name=policy["name"],
                description=policy["description"],
                value=policy["value"],
                isEnabled=policy["isEnabled"],
                scope=policy["scope"],
                now=datetime.now(UTC).isoformat(),
            )
            record = await result.single()
            if record:
                bp = record["bp"]
                created.append(
                    BenchmarkPolicy(
                        id=bp["id"],
                        policy_type=bp["policyType"],
                        name=bp["name"],
                        description=bp.get("description", ""),
                        value=bp.get("value", ""),
                        is_enabled=bp.get("isEnabled", True),
                        scope=bp.get("scope", "tenant"),
                    )
                )
        return created
