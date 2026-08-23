from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Value Pack API routes for Layer 3.

Provides endpoints for Value Pack CRUD and execution.
"""

import re
import uuid
from datetime import UTC, datetime
from typing import Any, Literal, TypedDict

from fastapi import APIRouter, Depends, Query, Request
from neo4j import AsyncDriver
from pydantic import BaseModel, Field
from value_fabric.shared.models.typed_dict import TypedDictModel

from src.logging_config import get_logger

from ...api.routes._utils import get_tenant_id_from_api_key, increment_patch_version
from ...api.routes.formulas import evaluate_expression
from ...auth.api_keys import APIKey
from ...auth.middleware import get_current_api_key
from ...db.audited_mutation import AuditedGraphMutation
from ...db.driver import get_driver
from ...db.query_execution import run_validated_query
from ...models.valuepack import (
    DEFAULT_VALUEPACKS,
    ComposableTemplateLibraryResponse,
    OntologyMapResponse,
    ValuePackComparisonRequest,
    ValuePackComparisonResponse,
    ValuePackCreate,
    ValuePackListResponse,
    ValuePackUpdate,
)
from ...utils.cypher_security import (
    ALLOWED_REL_TYPES,
    ALLOWED_TARGET_LABELS,
    validate_cypher_identifier,
)
from .value_packs_mapping import build_pack_detail_from_record, build_valuepack_response


class _build_fork_paramsResult(TypedDictModel):
    created_at: Any
    created_by: Any
    description: Any
    industry: Any
    name: Any
    new_pack_id: Any
    old_pack_id: Any
    segment: Any
    status: Any
    version: Any
    workspace_id: Any


class seed_valuepack_dataResult(TypedDictModel):
    industry_id: Any
    status: str


logger = get_logger(__name__)


# SECURITY: Tenant context extraction for multi-tenant isolation
def _extract_tenant_id(request: Request | None) -> str | None:
    """Extract tenant_id from request context for multi-tenant security.

    Returns None if tenant context is unavailable.

    Args:
        request: FastAPI Request object with optional state.context

    Returns:
        Normalized tenant_id string or None
    """
    if not request:
        return None
    ctx = getattr(request.state, "context", None)
    if ctx and ctx.tenant_id:
        return str(ctx.tenant_id)
    return None


def _tenant_id_from_api_key(api_key: APIKey) -> str:
    """Resolve tenant ID from authenticated API-key metadata; fail closed if absent.

    Delegates to the shared get_tenant_id_from_api_key helper in _utils.

    Contract note: previously raised 403 ("Tenant context is required"). Changed to
    401 in round-2 hardening to align with benchmarks.py and formula_governance.py,
    which treat a missing/invalid tenant as an authentication failure (the API key
    does not carry a valid identity) rather than an authorization failure.
    Callers that previously distinguished 403 from 401 should be updated accordingly.
    """
    return get_tenant_id_from_api_key(api_key)


# Status constants for Value Packs
STATUS_DRAFT = "draft"
STATUS_PUBLISHED = "published"
STATUS_DEPRECATED = "deprecated"
STATUS_ARCHIVED = "archived"

# Relationship type constants for Neo4j
REL_HAS_DRIVER = "hasDriver"
REL_HAS_FORMULA = "hasFormula"
REL_HAS_BENCHMARK = "hasBenchmark"
REL_HAS_WORKFLOW = "hasWorkflow"
REL_SUPERSEDES = "SUPERSEDES"
REL_HAS_EXECUTION = "HAS_EXECUTION"
REL_SEED_HAS_DRIVER = "HAS_DRIVER"
REL_SEED_HAS_USE_CASE = "HAS_USE_CASE"
REL_SEED_HAS_MODEL_TYPE = "HAS_MODEL_TYPE"

# Default version for new packs
DEFAULT_VERSION = "1.0.0"

# Pagination limits
MAX_PAGE_SIZE = 100
DEFAULT_PAGE_SIZE = 50


# Pack ID validation regex: allows UUIDs OR slug-style IDs (alphanumeric, hyphens, underscores)
# Examples: "manufacturing-v1", "life-sciences-v1", "550e8400-e29b-41d4-a716-446655440000"
VALID_PACK_ID_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")
MAX_PACK_ID_LENGTH = 128


def _validate_pack_id(pack_id: str) -> None:
    """Validate pack_id format.

    Accepts both UUID format (for dynamic packs) and slug-style IDs
    (for manifest packs like "manufacturing-v1").

    Raises:
        HTTPException: 400 if pack_id format is invalid or too long.
    """
    if not pack_id:
        raise ValidationError(message="pack_id is required")

    if len(pack_id) > MAX_PACK_ID_LENGTH:
        raise ValidationError(
            message=str(
                f"pack_id exceeds maximum length ({MAX_PACK_ID_LENGTH} chars): {pack_id[:50]}..."
            )
        )

    # Check if it's a valid UUID
    try:
        uuid.UUID(pack_id)
        return  # Valid UUID
    except ValueError:
        pass  # Not a UUID, check slug format

    # Check slug format (alphanumeric, hyphens, underscores)
    if not VALID_PACK_ID_PATTERN.match(pack_id):
        raise ValidationError(
            message=str(
                f"Invalid pack_id format: {pack_id}. Must be UUID or slug-style (alphanumeric, hyphens, underscores)."
            )
        )


router = APIRouter()


# Pydantic Models


class ValueDriverSummary(BaseModel):
    """Summary of value driver in pack."""

    driver_id: str
    name: str
    category: str
    weight: float = 1.0


class FormulaSummary(BaseModel):
    """Summary of formula in pack."""

    formula_id: str
    name: str
    version: str
    variables: list[str]


class BenchmarkSummary(BaseModel):
    """Summary of benchmark in pack."""

    dataset_id: str
    metric: str
    industry: str


class PackSummary(BaseModel):
    """Summary of Value Pack."""

    pack_id: str
    id: str | None = None  # Alias for pack_id (frontend compatibility)
    name: str
    description: str | None = None
    industry: str
    segment: str | None
    status: str
    version: str
    driver_count: int
    formula_count: int
    benchmark_count: int
    workflow_count: int = 0
    scope: str | None = "global"
    category: str | None = None
    updated_at: str | None = None
    created_by: str | None = None


class PackDetail(BaseModel):
    """Full Value Pack detail."""

    pack_id: str
    name: str
    description: str
    industry: str
    segment: str | None
    status: str
    version: str
    drivers: list[ValueDriverSummary]
    formulas: list[FormulaSummary]
    benchmarks: list[BenchmarkSummary]
    created_at: str
    updated_at: str | None = None
    created_by: str | None = None
    workspace_id: str | None = None
    is_loaded: bool = False
    workflow_count: int = 0
    scope: str | None = "global"
    category: str | None = None


VALID_PACK_STATUSES = [
    STATUS_DRAFT,
    STATUS_PUBLISHED,
    STATUS_DEPRECATED,
    STATUS_ARCHIVED,
]


class PackCreateRequest(BaseModel):
    """Request to create a Value Pack."""

    name: str
    description: str
    industry: str
    segment: str | None = None
    status: Literal["draft", "published", "deprecated", "archived"] = STATUS_DRAFT
    driver_ids: list[str] = Field(default_factory=list)
    formula_ids: list[str] = Field(default_factory=list)
    benchmark_ids: list[str] = Field(default_factory=list)
    created_by: str | None = None


class PackUpdateRequest(BaseModel):
    """Request to update a Value Pack."""

    name: str | None = None
    description: str | None = None
    industry: str | None = None
    segment: str | None = None
    status: Literal["draft", "published", "deprecated", "archived"] | None = None
    driver_ids: list[str] | None = None
    formula_ids: list[str] | None = None
    benchmark_ids: list[str] | None = None


class PackExecuteRequest(BaseModel):
    """Request to execute a pack."""

    workspace_id: str
    variables: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None


class PackExecuteResponse(BaseModel):
    """Response from pack execution."""

    execution_id: str
    pack_id: str
    status: str
    outputs: dict[str, Any]
    errors: list[str]
    warnings: list[str] = Field(
        default_factory=list,
        description="Warning messages about partial implementation",
    )


class PackForkRequest(BaseModel):
    """Request to fork a pack."""

    workspace_id: str
    name: str | None = None
    modifications: dict[str, Any] = Field(default_factory=dict)
    user_id: str | None = None


class PackForkResponse(BaseModel):
    """Response from pack fork."""

    pack_id: str
    name: str
    version: str
    status: str


# Helper functions

# SEC-L3-CYPHER-003 / GOV-L3-006: Allowlists for dynamic Cypher label and
# relationship-type interpolation are now the canonical source of truth in
# utils.cypher_security (ALLOWED_REL_TYPES, ALLOWED_TARGET_LABELS).
# Imported above — do not redefine locally.


async def _update_relationships(
    tx,
    pack_id: str,
    rel_type: str,
    target_label: str,
    target_ids: list[str],
    tenant_id: str | None = None,
    request_id: str | None = None,
    account_id: str | None = None,
) -> None:
    """Update pack relationships, validating target entities exist.

    SECURITY: All queries include tenant_id filtering to prevent cross-tenant access.
    SECURITY: rel_type and target_label are validated against allowlists before
    interpolation to prevent Cypher injection (SEC-L3-CYPHER-003).
    SECURITY: All relationship writes go through AuditedGraphMutation for audit trail (Phase 1 hardening).

    Raises HTTPException if any target_id doesn't exist.
    Raises ValueError if rel_type or target_label are not in the allowlist.
    """
    # SEC-L3-CYPHER-003 / GOV-L3-006: Validate interpolated identifiers against
    # the canonical allowlists in utils.cypher_security before building the query.
    validate_cypher_identifier(rel_type, ALLOWED_REL_TYPES, kind="rel_type")
    validate_cypher_identifier(target_label, ALLOWED_TARGET_LABELS, kind="target_label")

    # Validate all targets exist with tenant scoping
    if target_ids:
        # SECURITY: Add tenant_id filter if available
        # Query is split so the validated label interpolation lives on a line
        # carrying the cypher-dynamic-safe provenance marker (outside the
        # query text, so Neo4j never sees the `#` token).
        check_query = (
            "UNWIND $target_ids as target_id\n"
            f"        MATCH (t:{target_label} {{id: target_id, tenant_id: $tenant_id}})\n"  # cypher-dynamic-safe: validated against ALLOWED_TARGET_LABELS allowlist
            "        RETURN collect(t.id) as found_ids\n"
            "        "
        )
        params = {"target_ids": target_ids}
        if tenant_id:
            params["tenant_id"] = tenant_id
        # strict-scoped-query-execution: helper requires tenant_id on every target node match
        result = await run_validated_query(
            tx,
            check_query,
            params,
            tenant_id=tenant_id,
            require_explicit_tenant_id=True,
            query_name="value_packs.validate_relationship_targets",
        )
        record = await result.single()
        found_ids = set(record["found_ids"]) if record else set()
        missing = set(target_ids) - found_ids
        if missing:
            raise ValidationError(
                message=str(f"{target_label} IDs not found: {sorted(missing)}")
            )

    # Phase 1 hardening: Use AuditedGraphMutation for all relationship writes
    if not tenant_id:
        raise AuthorizationError(
            message="Tenant context is required for relationship mutations"
        )
    mutation = AuditedGraphMutation(
        tenant_id=tenant_id,
        session=tx,
        request_id=request_id,
        account_id=account_id,
        operation_source="value_packs._update_relationships",
    )

    # Delete existing relationships of this type from the pack through the
    # audited gateway — one batch round trip. First scan for the existing
    # targets (single round trip, read-only) so the audited helper knows
    # which triples to remove.
    existing_query = (
        "MATCH (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id})\n"
        f"MATCH (vp)-[r:{rel_type}]->(t)\n"  # cypher-dynamic-safe: validated against ALLOWED_REL_TYPES allowlist
        "RETURN t.id as target_id\n"
        ""
    )
    existing_result = await run_validated_query(
        tx,
        existing_query,
        {"pack_id": pack_id, "tenant_id": tenant_id},
        tenant_id=tenant_id,
        require_explicit_tenant_id=True,
        query_name="value_packs.list_existing_relationship_targets",
    )
    existing_records = await existing_result.data()
    removed_targets = [record["target_id"] for record in existing_records]
    if removed_targets:
        await mutation.delete_relationships_batch(
            rel_type,
            [
                {"src_id": pack_id, "tgt_id": target_id}
                for target_id in removed_targets
            ],
        )

    # Create new relationships through the gateway in one round-trip batch.
    # versioned=True mirrors the original per-record write_relationship path
    # (which defaults to versioned=True), so RelationshipVersion provenance
    # is preserved identically.
    if target_ids:
        await mutation.write_relationships_batch(
            rel_type,
            [{"src_id": pack_id, "tgt_id": target_id} for target_id in target_ids],
            versioned=True,
        )


async def _get_pack_detail(
    driver: AsyncDriver, pack_id: str, tenant_id: str | None = None
) -> PackDetail | None:
    """Get full pack detail from Neo4j.

    SECURITY: Query includes tenant_id filtering to prevent cross-tenant access.

    Returns None if pack not found, PackDetail with related entities otherwise.
    """
    # SECURITY: Tenant-scoped query to prevent cross-tenant data leakage
    query = """
    MATCH (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id})
    OPTIONAL MATCH (vp)-[:hasDriver]->(vd:ValueDriver {tenant_id: $tenant_id})
    OPTIONAL MATCH (vp)-[:hasFormula]->(f:Formula {tenant_id: $tenant_id})
    OPTIONAL MATCH (vp)-[:hasBenchmark]->(b:BenchmarkDataset {tenant_id: $tenant_id})
    OPTIONAL MATCH (vp)-[:hasWorkflow]->(w:Workflow {tenant_id: $tenant_id})
    RETURN vp,
           collect(DISTINCT vd) as drivers,
           collect(DISTINCT f) as formulas,
           collect(DISTINCT b) as benchmarks,
           count(DISTINCT w) as workflow_count
    """

    async with driver.session() as session:
        result = await run_validated_query(
            session,
            query,
            {"pack_id": pack_id, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            require_explicit_tenant_id=True,
            query_name="value_packs.get_pack_detail",
        )
        record = await result.single()

        if not record:
            return None

        return build_pack_detail_from_record(record)


# API Endpoints


async def list_packs(
    industry: str | None = None,
    status: str | None = None,
    category: str | None = None,
    search: str | None = None,
    limit: int = Query(default=50, ge=1, le=100),
    driver: AsyncDriver = Depends(get_driver),
    fastapi_request: Request = None,  # SECURITY: For tenant context extraction
):
    """List Value Packs with optional filtering."""
    # SECURITY: Extract tenant context for multi-tenant isolation
    tenant_id = _extract_tenant_id(fastapi_request)

    # Build query dynamically with tenant scoping
    where_clauses = ["vp.tenant_id = $tenant_id"]  # SECURITY: Mandatory tenant filter
    params: dict[str, Any] = {"limit": limit, "tenant_id": tenant_id}

    if industry:
        where_clauses.append("vp.industry = $industry")
        params["industry"] = industry
    if status:
        where_clauses.append("vp.status = $status")
        params["status"] = status
    if category:
        where_clauses.append("vp.category = $category")
        params["category"] = category
    if search:
        where_clauses.append(
            "(vp.name CONTAINS $search OR vp.description CONTAINS $search)"
        )
        params["search"] = search

    where_clause = " AND ".join(
        where_clauses
    )  # cypher-dynamic-safe: where_clauses are hardcoded literals

    # SECURITY: All related nodes filtered by tenant_id
    query = f"""
    MATCH (vp:ValuePack)
    WHERE {where_clause}  
    OPTIONAL MATCH (vp)-[:hasDriver]->(vd:ValueDriver {{tenant_id: $tenant_id}})
    OPTIONAL MATCH (vp)-[:hasFormula]->(f:Formula {{tenant_id: $tenant_id}})
    OPTIONAL MATCH (vp)-[:hasBenchmark]->(b:BenchmarkDataset {{tenant_id: $tenant_id}})
    OPTIONAL MATCH (vp)-[:hasWorkflow]->(w:Workflow {{tenant_id: $tenant_id}})
    RETURN vp,
           count(DISTINCT vd) as driver_count,
           count(DISTINCT f) as formula_count,
           count(DISTINCT b) as benchmark_count,
           count(DISTINCT w) as workflow_count
    ORDER BY vp.name
    LIMIT $limit
    """

    async with driver.session() as session:
        result = await run_validated_query(
            session,
            query,
            params,
            tenant_id=tenant_id,
            require_explicit_tenant_id=True,
            query_name="value_packs.list_packs",
        )
        records = await result.data()

        return [
            PackSummary(
                pack_id=r["vp"]["id"],
                id=r["vp"]["id"],
                name=r["vp"].get("name", ""),
                description=r["vp"].get("description"),
                industry=r["vp"].get("industry", ""),
                segment=r["vp"].get("segment"),
                status=r["vp"].get("status", "draft"),
                version=r["vp"].get("version", DEFAULT_VERSION),
                driver_count=r["driver_count"],
                formula_count=r["formula_count"],
                benchmark_count=r["benchmark_count"],
                workflow_count=r["workflow_count"],
                scope=r["vp"].get("scope", "global"),
                category=r["vp"].get("category"),
                updated_at=r["vp"].get("updatedAt"),
                created_by=r["vp"].get("createdBy"),
            )
            for r in records
        ]


async def get_pack(
    pack_id: str,
    driver: AsyncDriver = Depends(get_driver),
    fastapi_request: Request = None,  # SECURITY: For tenant context extraction
):
    """Get Value Pack by ID."""
    _validate_pack_id(pack_id)

    # SECURITY: Extract tenant context for multi-tenant isolation
    tenant_id = _extract_tenant_id(fastapi_request)

    pack = await _get_pack_detail(driver, pack_id, tenant_id)
    if not pack:
        raise NotFoundError(message="Pack not found")
    return pack


async def create_pack(
    request: PackCreateRequest,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(get_current_api_key),
):
    """Create a new Value Pack. Requires authentication."""
    tenant_id = _tenant_id_from_api_key(api_key)
    pack_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    async with driver.session() as session:
        async with session.begin_transaction() as tx:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=tx,
                operation_source="value_packs.create_pack",
            )
            await mutation.write_node(
                "ValuePack",
                pack_id,
                {
                    "name": request.name,
                    "description": request.description,
                    "industry": request.industry,
                    "segment": request.segment,
                    "status": request.status,
                    "version": DEFAULT_VERSION,
                    "createdAt": now,
                    "createdBy": request.created_by,
                },
            )
            await _update_pack_relationships(tx, pack_id, request, tenant_id)

    pack = await _get_pack_detail(driver, pack_id, tenant_id)
    if not pack:
        raise ServiceUnavailableError(message="Failed to create pack")
    return pack


def _build_update_params(
    request: PackUpdateRequest, pack_id: str
) -> tuple[list[str], dict[str, Any]]:
    """Build SET clauses and params for pack update query.

    Returns:
        Tuple of (set_clauses list, params dict)
    """
    set_clauses = ["vp.updatedAt = $updated_at"]
    params: dict[str, Any] = {
        "pack_id": pack_id,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    if request.name is not None:
        set_clauses.append("vp.name = $name")
        params["name"] = request.name
    if request.description is not None:
        set_clauses.append("vp.description = $description")
        params["description"] = request.description
    if request.industry is not None:
        set_clauses.append("vp.industry = $industry")
        params["industry"] = request.industry
    if request.segment is not None:
        set_clauses.append("vp.segment = $segment")
        params["segment"] = request.segment
    if request.status is not None:
        set_clauses.append("vp.status = $status")
        params["status"] = request.status

    return set_clauses, params


async def _update_pack_relationships(
    tx,
    pack_id: str,
    request: PackCreateRequest | PackUpdateRequest,
    tenant_id: str | None = None,
    request_id: str | None = None,
    account_id: str | None = None,
) -> None:
    """Helper to update pack relationships during create/update.

    Validates target entities exist before creating relationships.
    SECURITY: All relationship operations are tenant-scoped.
    SECURITY: All relationship writes go through AuditedGraphMutation (Phase 1 hardening).
    """
    if request.driver_ids is not None:
        await _update_relationships(
            tx,
            pack_id,
            "hasDriver",
            "ValueDriver",
            request.driver_ids,
            tenant_id,
            request_id=request_id,
            account_id=account_id,
        )
    if request.formula_ids is not None:
        await _update_relationships(
            tx,
            pack_id,
            "hasFormula",
            "Formula",
            request.formula_ids,
            tenant_id,
            request_id=request_id,
            account_id=account_id,
        )
    if request.benchmark_ids is not None:
        await _update_relationships(
            tx,
            pack_id,
            "hasBenchmark",
            "BenchmarkDataset",
            request.benchmark_ids,
            tenant_id,
            request_id=request_id,
            account_id=account_id,
        )


async def update_pack(
    pack_id: str,
    request: PackUpdateRequest,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(get_current_api_key),
    fastapi_request: Request = None,  # SECURITY: For tenant context extraction
):
    """Update a Value Pack. Requires authentication."""
    _validate_pack_id(pack_id)

    # SECURITY: Extract tenant context for multi-tenant isolation
    tenant_id = _extract_tenant_id(fastapi_request)

    # SECURITY: Verify pack exists with tenant scoping
    check_query = "MATCH (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id}) RETURN vp"
    async with driver.session() as session:
        result = await run_validated_query(
            session,
            check_query,
            {"pack_id": pack_id, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            require_explicit_tenant_id=True,
            query_name="value_packs.update_pack.exists",
        )
        if not await result.single():
            raise NotFoundError(message="Pack not found")

    # Build and execute update
    _, params = _build_update_params(request, pack_id)
    update_props = {
        "updatedAt": params["updated_at"],
        **{
            key: params[key]
            for key in ("name", "description", "industry", "segment", "status")
            if key in params
        },
    }

    async with driver.session() as session:
        async with session.begin_transaction() as tx:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=tx,
                operation_source="value_packs.update_pack",
            )
            await mutation.write_node("ValuePack", pack_id, update_props)
            # Phase 1 hardening: Pass request context for audit trail
            request_id = (
                getattr(fastapi_request.state, "request_id", None)
                if fastapi_request
                else None
            )
            account_id = (
                getattr(fastapi_request.state, "account_id", None)
                if fastapi_request
                else None
            )
            await _update_pack_relationships(
                tx,
                pack_id,
                request,
                tenant_id,
                request_id=request_id,
                account_id=account_id,
            )

        # Re-query for consistent view with relationships
        pack = await _get_pack_detail(driver, pack_id, tenant_id)
        if not pack:
            raise ServiceUnavailableError(message="Failed to update pack")
        return pack


async def _get_pack_formulas(
    driver: AsyncDriver, pack_id: str, tenant_id: str
) -> list[dict[str, Any]]:
    """Get all formulas associated with a pack from Neo4j.

    Returns list of formula dicts with id, expression, variables, name.
    """
    query = """
    // strict-scoped-query-execution: execution reads only formulas owned by the same tenant
    MATCH (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id})-[:hasFormula]->(f:Formula {tenant_id: $tenant_id})
    RETURN f.id as formula_id,
           f.expression as expression,
           f.variables as variables,
           f.name as name
    """
    async with driver.session() as session:
        result = await run_validated_query(
            session,
            query,
            {"pack_id": pack_id, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            require_explicit_tenant_id=True,
            query_name="value_packs.get_pack_formulas",
        )
        records = await result.data()
        return records


class VariableDefault(TypedDict, total=False):
    """Schema for formula variable defaults from Neo4j."""

    name: str
    default_value: float


def _merge_variables(
    formula_defaults: list[VariableDefault], user_variables: dict[str, Any]
) -> dict[str, float]:
    """Merge user-provided variables with formula defaults.

    Args:
        formula_defaults: List of variable dicts with 'name' and 'default_value'
        user_variables: Dict of user-provided variable values

    Returns:
        Merged dict with all required variables as floats
    """
    merged: dict[str, float] = {}

    # Add formula defaults first
    for var in formula_defaults:
        var_name = var.get("name")
        default = var.get("default_value")
        if var_name and default is not None:
            try:
                merged[var_name] = float(default)
            except (ValueError, TypeError):
                logger.warning(
                    "Invalid default value",
                    extra={"variable": var_name, "value": default},
                )

    # Override with user-provided values
    for var_name, var_value in user_variables.items():
        try:
            merged[var_name] = float(var_value)
        except (ValueError, TypeError):
            if var_name in merged:
                logger.warning(
                    "Invalid user value, keeping default",
                    extra={
                        "variable": var_name,
                        "user_value": var_value,
                        "default_value": merged[var_name],
                    },
                )
            else:
                logger.warning(
                    "Invalid user value, no default available",
                    extra={"variable": var_name, "user_value": var_value},
                )

    return merged


async def execute_pack(
    pack_id: str,
    request: PackExecuteRequest,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(get_current_api_key),
):
    """Execute a Value Pack workflow. Requires authentication.

    Evaluates all formulas associated with the pack using provided variables
    merged with formula defaults. Returns calculated values for each formula.
    """
    _validate_pack_id(pack_id)
    tenant_id = _tenant_id_from_api_key(api_key)
    execution_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()

    # Get pack formulas
    pack_formulas = await _get_pack_formulas(driver, pack_id, tenant_id)

    if not pack_formulas:
        raise ValidationError(message=str(f"Pack {pack_id} has no formulas to execute"))

    async with driver.session() as session:
        mutation = AuditedGraphMutation(
            tenant_id=tenant_id,
            session=session,
            operation_source="value_packs.execute_pack.start",
        )
        await mutation.write_node(
            "PackExecution",
            execution_id,
            {
                "packId": pack_id,
                "workspaceId": request.workspace_id,
                "status": "running",
                "variables": request.variables,
                "userId": request.user_id,
                "startedAt": now,
            },
        )
        await mutation.write_relationship(
            pack_id,
            REL_HAS_EXECUTION,
            execution_id,
            versioned=False,
        )

    # Execute formulas
    outputs: dict[str, Any] = {"pack_id": pack_id, "formulas_evaluated": 0}
    errors: list[str] = []
    warnings: list[str] = []
    execution_status = "success"

    for formula in pack_formulas:
        formula_id = formula.get("formula_id", "unknown")
        expression = formula.get("expression", "")
        variables_spec = formula.get("variables", []) or []
        formula_name = formula.get("name", formula_id)

        if not expression:
            errors.append(f"Formula '{formula_name}' has no expression")
            continue

        # Build variable context: merge user inputs with formula defaults
        variable_context = _merge_variables(
            variables_spec,  # type: ignore[arg-type]
            request.variables,
        )

        try:
            result_value = evaluate_expression(expression, variable_context)
            outputs[formula_id] = {
                "name": formula_name,
                "result": result_value,
                "expression": expression,
                "variables_used": variable_context,
            }
            outputs["formulas_evaluated"] += 1
        except ValueError as e:
            errors.append(f"Formula '{formula_name}' evaluation failed: {e}")
            execution_status = "partial"
        except Exception as e:
            errors.append(f"Formula '{formula_name}' unexpected error: {e}")
            execution_status = "partial"

    # Determine final status
    if outputs["formulas_evaluated"] == 0 and errors:
        execution_status = "failed"
    elif errors:
        execution_status = "partial"

    async with driver.session() as session:
        async with session.begin_transaction() as tx:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=tx,
                operation_source="value_packs.execute_pack.complete",
            )
            await mutation.write_node(
                "PackExecution",
                execution_id,
                {
                    "status": execution_status,
                    "outputs": outputs,
                    "errors": errors,
                    "completedAt": datetime.now(UTC).isoformat(),
                },
            )

    return PackExecuteResponse(
        execution_id=execution_id,
        pack_id=pack_id,
        status=execution_status,
        outputs=outputs,
        errors=errors,
        warnings=warnings,
    )


async def _get_original_pack(
    driver: AsyncDriver, pack_id: str, tenant_id: str
) -> dict[str, Any]:
    """Get original pack data for forking.

    Raises HTTPException if pack not found.
    """
    query = "// strict-scoped-query-execution: fork source pack is tenant-scoped\nMATCH (vp:ValuePack {id: $pack_id, tenant_id: $tenant_id}) RETURN vp"
    async with driver.session() as session:
        result = await run_validated_query(
            session,
            query,
            {"pack_id": pack_id, "tenant_id": tenant_id},
            tenant_id=tenant_id,
            require_explicit_tenant_id=True,
            query_name="value_packs.get_original_pack",
        )
        record = await result.single()
        if not record:
            raise NotFoundError(message="Pack not found")
        return record["vp"]


def _build_fork_params(
    orig: dict[str, Any], request: PackForkRequest, new_pack_id: str
) -> dict[str, Any]:
    """Build parameters for fork creation query.

    Returns dict with all parameters for the fork Cypher query.
    """
    original_version = orig.get("version", DEFAULT_VERSION)
    new_version = increment_patch_version(original_version)
    name = request.name or f"{orig.get('name', 'Unnamed')} (Fork)"
    now = datetime.now(UTC).isoformat()

    return _build_fork_paramsResult.model_validate(
        {
            "old_pack_id": orig["id"],
            "new_pack_id": new_pack_id,
            "name": name,
            "description": orig.get("description", ""),
            "industry": orig.get("industry", ""),
            "segment": orig.get("segment"),
            "version": new_version,
            "status": STATUS_DRAFT,
            "workspace_id": request.workspace_id,
            "created_at": now,
            "created_by": request.user_id,
        }
    )


async def _execute_fork(driver: AsyncDriver, params: dict[str, Any]) -> dict[str, Any]:
    """Execute fork creation in Neo4j.

    Creates new pack with relationships copied from original.
    Returns the new pack node properties.

    Raises HTTPException on failure.
    """
    relationship_query = """
    // strict-scoped-query-execution: fork relationship targets are copied only within tenant boundary
    MATCH (old:ValuePack {id: $old_pack_id, tenant_id: $tenant_id})
    OPTIONAL MATCH (old)-[:hasDriver]->(vd:ValueDriver {tenant_id: $tenant_id})
    OPTIONAL MATCH (old)-[:hasFormula]->(f:Formula {tenant_id: $tenant_id})
    OPTIONAL MATCH (old)-[:hasBenchmark]->(b:BenchmarkDataset {tenant_id: $tenant_id})
    RETURN collect(DISTINCT vd.id) as driver_ids,
           collect(DISTINCT f.id) as formula_ids,
           collect(DISTINCT b.id) as benchmark_ids
    """

    async with driver.session() as session:
        relationship_result = await run_validated_query(
            session,
            relationship_query,
            {"old_pack_id": params["old_pack_id"], "tenant_id": params["tenant_id"]},
            tenant_id=params["tenant_id"],
            require_explicit_tenant_id=True,
            query_name="value_packs.fork.relationship_targets",
        )
        relationship_record = await relationship_result.single()
        if not relationship_record:
            raise ServiceUnavailableError(message="Failed to fork pack")

        async with session.begin_transaction() as tx:
            mutation = AuditedGraphMutation(
                tenant_id=params["tenant_id"],
                session=tx,
                operation_source="value_packs.fork_pack",
            )
            await mutation.write_node(
                "ValuePack",
                params["new_pack_id"],
                {
                    "name": params["name"],
                    "description": params["description"],
                    "industry": params["industry"],
                    "segment": params["segment"],
                    "status": params["status"],
                    "version": params["version"],
                    "workspaceId": params["workspace_id"],
                    "isLoaded": True,
                    "createdAt": params["created_at"],
                    "createdBy": params["created_by"],
                    "forkedFrom": params["old_pack_id"],
                },
            )
            await mutation.write_relationship(
                params["new_pack_id"],
                REL_SUPERSEDES,
                params["old_pack_id"],
                {"type": "fork"},
                versioned=False,
            )
            for target_id in relationship_record["driver_ids"]:
                if target_id:
                    await mutation.write_relationship(
                        params["new_pack_id"], REL_HAS_DRIVER, target_id
                    )
            for target_id in relationship_record["formula_ids"]:
                if target_id:
                    await mutation.write_relationship(
                        params["new_pack_id"], REL_HAS_FORMULA, target_id
                    )
            for target_id in relationship_record["benchmark_ids"]:
                if target_id:
                    await mutation.write_relationship(
                        params["new_pack_id"], REL_HAS_BENCHMARK, target_id
                    )

        return {
            "id": params["new_pack_id"],
            "name": params["name"],
            "description": params["description"],
            "industry": params["industry"],
            "segment": params["segment"],
            "status": params["status"],
            "version": params["version"],
            "workspaceId": params["workspace_id"],
            "isLoaded": True,
            "createdAt": params["created_at"],
            "createdBy": params["created_by"],
            "forkedFrom": params["old_pack_id"],
        }


async def fork_pack(
    pack_id: str,
    request: PackForkRequest,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(get_current_api_key),
):
    """Fork a Value Pack for customization. Requires authentication."""
    _validate_pack_id(pack_id)

    # Get original pack properties
    tenant_id = _tenant_id_from_api_key(api_key)
    orig = await _get_original_pack(driver, pack_id, tenant_id)

    # Create forked pack with copied relationships
    new_pack_id = str(uuid.uuid4())
    fork_params = _build_fork_params(orig, request, new_pack_id)
    fork_params["tenant_id"] = tenant_id
    new_pack = await _execute_fork(driver, fork_params)

    return PackForkResponse(
        pack_id=new_pack["id"],
        name=new_pack["name"],
        version=new_pack["version"],
        status=STATUS_DRAFT,
    )


async def apply_pack(
    pack_id: str,
    request: PackExecuteRequest,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(get_current_api_key),
):
    """Apply/Deploy a Value Pack (alias for execute endpoint). Requires authentication."""
    _validate_pack_id(pack_id)
    # NOTE: apply_pack is currently an alias for execute_pack.
    # When execution logic diverges (e.g., deployment vs preview), refactor.
    return await execute_pack(pack_id, request, driver)


# ═══════════════════════════════════════════════════════════════════════════════
# ValuePack Framework v1.0 - Industry-Specific Value Model Templates
# ═══════════════════════════════════════════════════════════════════════════════

# In-memory store for now (to be replaced with Neo4j)
_valuepack_db: dict[str, ValuePackCreate] = {}


def _init_default_valuepacks():
    """Initialize default ValuePacks if not already loaded."""
    if not _valuepack_db:
        for vp in DEFAULT_VALUEPACKS:
            if vp:
                _valuepack_db[vp.industry_id] = vp


async def list_valuepacks(
    tier: int | None = Query(None, description="Filter by tier (1, 2, or 3)"),
    search: str | None = Query(None, description="Search in name/description"),
    is_active: bool = Query(True, description="Only active ValuePacks"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    api_key: APIKey = Depends(get_current_api_key),
):
    """List all ValuePacks with optional filtering.

    Returns paginated list of ValuePack summaries.
    """
    _init_default_valuepacks()

    # Filter ValuePacks
    filtered = list(_valuepack_db.values())

    if tier:
        filtered = [vp for vp in filtered if vp.tier.value == tier]

    if is_active is not None:
        filtered = [vp for vp in filtered if vp.is_active == is_active]

    if search:
        search_lower = search.lower()
        filtered = [
            vp
            for vp in filtered
            if (
                search_lower in vp.display_name.lower()
                or search_lower in vp.description.lower()
            )
        ]

    # Pagination
    total = len(filtered)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = filtered[start:end]

    # Convert to response format
    items = [build_valuepack_response(vp) for vp in paginated]

    return ValuePackListResponse(
        items=items, total=total, page=page, page_size=page_size, has_more=end < total
    )


async def get_valuepack(
    industry_id: str,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Get a specific ValuePack by industry_id.

    Returns complete ValuePack schema v1.0 data.
    """
    _init_default_valuepacks()

    if industry_id not in _valuepack_db:
        raise NotFoundError(message=str(f"ValuePack not found: {industry_id}"))

    vp = _valuepack_db[industry_id]
    return build_valuepack_response(vp)


async def create_valuepack(
    request: ValuePackCreate,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Create a new ValuePack.

    All fields must conform to ValuePack Schema v1.0.
    """
    _init_default_valuepacks()

    if request.industry_id in _valuepack_db:
        raise ConflictError(message=f"ValuePack already exists: {request.industry_id}")

    _valuepack_db[request.industry_id] = request
    logger.info(f"Created ValuePack: {request.industry_id}")

    return build_valuepack_response(request)


async def update_valuepack(
    industry_id: str,
    request: ValuePackUpdate,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Update an existing ValuePack.

    Only provided fields are updated; others remain unchanged.
    """
    _init_default_valuepacks()

    if industry_id not in _valuepack_db:
        raise NotFoundError(message=str(f"ValuePack not found: {industry_id}"))

    existing = _valuepack_db[industry_id]
    update_data = request.model_dump(exclude_unset=True)

    # Merge update into existing
    merged = existing.model_copy(update=update_data)
    _valuepack_db[industry_id] = merged

    logger.info(f"Updated ValuePack: {industry_id}")
    return build_valuepack_response(merged)


async def delete_valuepack(
    industry_id: str,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Soft-delete a ValuePack (marks as inactive)."""
    _init_default_valuepacks()

    if industry_id not in _valuepack_db:
        raise NotFoundError(message=str(f"ValuePack not found: {industry_id}"))

    _valuepack_db[industry_id].is_active = False
    logger.info(f"Soft-deleted ValuePack: {industry_id}")


async def get_ontology_map(
    api_key: APIKey = Depends(get_current_api_key),
):
    """Get cross-industry ontology map.

    Returns shared drivers, model types, and proof patterns across all industries.
    """
    _init_default_valuepacks()

    # Collect all tags and categorize
    all_drivers = {}
    all_models = {}
    all_proofs = {}

    for vp in _valuepack_db.values():
        # Drivers
        for driver in vp.primary_value_drivers:
            if driver.id not in all_drivers:
                all_drivers[driver.id] = {
                    "id": driver.id,
                    "name": driver.name,
                    "industries": [],
                    "count": 0,
                }
            all_drivers[driver.id]["industries"].append(vp.industry_id)
            all_drivers[driver.id]["count"] += 1

        # Models
        for model in vp.economic_model_types:
            if model.id not in all_models:
                all_models[model.id] = {
                    "id": model.id,
                    "name": model.name,
                    "industries": [],
                    "count": 0,
                }
            all_models[model.id]["industries"].append(vp.industry_id)
            all_models[model.id]["count"] += 1

        # Proof patterns
        for proof in vp.proof_requirements:
            if proof.id not in all_proofs:
                all_proofs[proof.id] = {
                    "id": proof.id,
                    "requirement": proof.requirement,
                    "industries": [],
                    "count": 0,
                }
            all_proofs[proof.id]["industries"].append(vp.industry_id)
            all_proofs[proof.id]["count"] += 1

    # Filter to those appearing in 2+ industries
    shared_drivers = [d for d in all_drivers.values() if d["count"] >= 2]
    shared_models = [m for m in all_models.values() if m["count"] >= 2]
    shared_proofs = [p for p in all_proofs.values() if p["count"] >= 2]

    # Build cross-reference matrix
    industry_ids = list(_valuepack_db.keys())
    matrix = {}
    for driver_id, driver_data in all_drivers.items():
        matrix[driver_id] = {}
        for ind_id in industry_ids:
            matrix[driver_id][ind_id] = 1 if ind_id in driver_data["industries"] else 0

    return OntologyMapResponse(
        shared_drivers=shared_drivers,
        shared_model_types=shared_models,
        shared_proof_patterns=shared_proofs,
        cross_reference_matrix=matrix,
    )


async def get_composable_templates(
    api_key: APIKey = Depends(get_current_api_key),
):
    """Get the composable template library.

    Returns reusable calculation patterns and their industry usage.
    """
    _init_default_valuepacks()

    # Collect all templates
    all_templates = {}
    template_usage: dict[str, list[str]] = {}

    for vp in _valuepack_db.values():
        for template in vp.composable_model_templates:
            all_templates[template.template_id] = template
            if template.template_id not in template_usage:
                template_usage[template.template_id] = []
            template_usage[template.template_id].extend(template.applicable_industries)

    return ComposableTemplateLibraryResponse(
        templates=list(all_templates.values()), template_usage=template_usage
    )


async def compare_valuepacks(
    request: ValuePackComparisonRequest,
    api_key: APIKey = Depends(get_current_api_key),
):
    """Compare multiple ValuePacks side-by-side.

    Returns detailed comparison across all schema dimensions.
    """
    _init_default_valuepacks()

    # Validate all IDs exist
    for ind_id in request.industry_ids:
        if ind_id not in _valuepack_db:
            raise NotFoundError(message=str(f"ValuePack not found: {ind_id}"))

    # Get full ValuePacks
    valuepacks = [
        build_valuepack_response(_valuepack_db[ind_id])
        for ind_id in request.industry_ids
    ]

    # Build comparison matrix
    comparison = {}

    # Compare drivers
    comparison["value_drivers"] = {
        ind_id: [d.name for d in _valuepack_db[ind_id].primary_value_drivers]
        for ind_id in request.industry_ids
    }

    # Compare use cases
    comparison["use_cases"] = {
        ind_id: [uc.name for uc in _valuepack_db[ind_id].core_use_cases]
        for ind_id in request.industry_ids
    }

    # Compare tiers
    comparison["tiers"] = {
        ind_id: _valuepack_db[ind_id].tier.name for ind_id in request.industry_ids
    }

    # Find shared templates
    shared_templates = set()
    for vp in valuepacks:
        for template in vp.composable_model_templates:
            if len(template.applicable_industries) >= 2:
                shared_templates.add(template.template_id)

    # Differentiation analysis
    differentiation = {}
    for ind_id in request.industry_ids:
        vp = _valuepack_db[ind_id]
        wins = [w.statement for w in vp.why_it_wins]
        differentiation[ind_id] = f"Differentiated by: {', '.join(wins[:2])}"

    return ValuePackComparisonResponse(
        valuepacks=valuepacks,
        comparison_matrix=comparison,
        shared_templates=list(shared_templates),
        differentiation_analysis=differentiation,
    )


async def seed_valuepack_data(
    industry_id: str,
    driver: AsyncDriver = Depends(get_driver),
    api_key: APIKey = Depends(get_current_api_key),
):
    """Seed ValuePack data into Neo4j knowledge graph.

    Creates nodes and relationships for the ValuePack's economic graph,
    value drivers, use cases, and ontology tags.
    """
    _init_default_valuepacks()

    if industry_id not in _valuepack_db:
        raise NotFoundError(message=str(f"ValuePack not found: {industry_id}"))

    vp = _valuepack_db[industry_id]
    tenant_id = _tenant_id_from_api_key(api_key)

    async with driver.session() as session:
        async with session.begin_transaction() as tx:
            mutation = AuditedGraphMutation(
                tenant_id=tenant_id,
                session=tx,
                operation_source="value_packs.seed_valuepack_data",
            )
            await mutation.write_node(
                "ValuePack",
                vp.industry_id,
                {
                    "industry_id": vp.industry_id,
                    "display_name": vp.display_name,
                    "tier": vp.tier.value,
                    "description": vp.description,
                    "version": vp.version,
                    "is_active": vp.is_active,
                },
            )
            for driver_node in vp.primary_value_drivers:
                await mutation.write_node(
                    "ValueDriver",
                    driver_node.id,
                    driver_node.model_dump(),
                )
                await mutation.write_relationship(
                    vp.industry_id,
                    REL_SEED_HAS_DRIVER,
                    driver_node.id,
                    versioned=False,
                )
            for use_case in vp.core_use_cases:
                await mutation.write_node(
                    "UseCase",
                    use_case.id,
                    use_case.model_dump(),
                )
                await mutation.write_relationship(
                    vp.industry_id,
                    REL_SEED_HAS_USE_CASE,
                    use_case.id,
                    versioned=False,
                )
            for model_type in vp.economic_model_types:
                await mutation.write_node(
                    "EconomicModel",
                    model_type.id,
                    model_type.model_dump(),
                )
                await mutation.write_relationship(
                    vp.industry_id,
                    REL_SEED_HAS_MODEL_TYPE,
                    model_type.id,
                    versioned=False,
                )

    logger.info(f"Seeded ValuePack data to Neo4j: {industry_id}")
    return seed_valuepack_dataResult.model_validate(
        {"status": "seeded", "industry_id": industry_id}
    )


# Local route modules register cohesive Value Pack route groups without changing public paths.
from .value_packs_framework_routes import router as valuepack_framework_router
from .value_packs_pack_routes import router as pack_router

router.include_router(pack_router)
router.include_router(valuepack_framework_router)
