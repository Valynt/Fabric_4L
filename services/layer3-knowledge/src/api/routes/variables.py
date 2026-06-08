from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
)

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Variable Registry API routes for Layer 3.

Provides endpoints for variable definitions, search, and resolution.

All Cypher queries are tenant-scoped via `create_neo4j_tenant_session`.
"""

import os
from datetime import UTC, datetime
from typing import Any, Literal

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_tenant_context

from src.logging_config import get_logger

from ...api.dependencies_tenant_secured import create_neo4j_tenant_session

logger = get_logger(__name__)

# Error messages for fail-closed scenarios
_ERROR_BENCHMARK_NOT_CONFIGURED = (
    "Benchmark integration not configured. Configure BENCHMARK_API_URL and "
    "BENCHMARK_API_KEY for production-like environments."
)
_ERROR_FORMULA_NOT_CONFIGURED = (
    "Formula calculation service not configured. Configure FORMULA_SERVICE_URL "
    "for production-like environments."
)


def _is_production_like() -> bool:
    """Return True only for the exact 'production' environment.

    This changes the previous fail-safe policy to an explicit allowlist.
    Staging and unknown/custom environments are NOT treated as production-like.
    For safety-critical checks that must run in both production and staging,
    use is_strict_environment() from value_fabric.shared.security.config instead.
    """
    env = (os.getenv("ENVIRONMENT") or os.getenv("APP_ENV") or "development").strip().lower()
    return env == "production"

router = APIRouter()

# Pydantic Models


class SourceBinding(BaseModel):
    """Source binding configuration."""

    source_type: Literal[
        "user_input",
        "crm_field",
        "erp_field",
        "benchmark_lookup",
        "formula_calculation",
        "database_query",
        "api_call",
        "ground_truth",
    ]
    source_location: str
    extraction_query: str | None = None
    transformation: str | None = None
    fallback_value: Any | None = None
    is_required: bool = True


class ValidationRule(BaseModel):
    """Validation rule for variable."""

    rule_type: str
    parameters: dict[str, Any]
    error_message: str


class VariableSummary(BaseModel):
    """Summary of variable definition."""

    variable_id: str
    name: str
    description: str
    data_type: str
    industry: str | None
    source_type: str | None
    is_active: bool
    version: str


class VariableDetail(BaseModel):
    """Full variable definition."""

    variable_id: str
    name: str
    description: str
    data_type: str
    industry: str | None
    applicable_formulas: list[str]
    applicable_packs: list[str]
    source_binding: SourceBinding | None
    validation_rules: list[ValidationRule]
    created_at: str
    updated_at: str | None
    version: str
    is_active: bool


VALID_DATA_TYPES = ["string", "integer", "decimal", "boolean", "date", "enum", "json"]
VALID_SOURCE_TYPES = [
    "user_input",
    "crm_field",
    "erp_field",
    "benchmark_lookup",
    "formula_calculation",
    "database_query",
    "api_call",
    "ground_truth",
]


class VariableCreateRequest(BaseModel):
    """Request to create a variable."""

    name: str
    description: str
    data_type: Literal[
        "string", "integer", "decimal", "boolean", "date", "enum", "json"
    ]
    industry: str | None = None
    applicable_formulas: list[str] = Field(default_factory=list)
    applicable_packs: list[str] = Field(default_factory=list)
    source_binding: SourceBinding | None = None
    validation_rules: list[ValidationRule] = Field(default_factory=list)


class VariableUpdateRequest(BaseModel):
    """Request to update a variable."""

    name: str | None = None
    description: str | None = None
    data_type: str | None = None
    industry: str | None = None
    applicable_formulas: list[str] | None = None
    applicable_packs: list[str] | None = None
    source_binding: SourceBinding | None = None
    validation_rules: list[ValidationRule] | None = None
    is_active: bool | None = None


class VariableSearchRequest(BaseModel):
    """Request to search variables."""

    industry: str | None = None
    pack_id: str | None = None
    formula_id: str | None = None
    data_type: str | None = None
    source_type: str | None = None
    is_active: bool = True


class ResolveRequest(BaseModel):
    """Request to resolve variable value."""

    workspace_id: str
    entity_id: str | None = None
    user_id: str | None = None
    pack_id: str | None = None
    industry: str | None = None


class ResolveResponse(BaseModel):
    """Response from variable resolution."""

    variable_id: str
    value: Any
    data_type: str
    source_type: str
    source_location: str | None
    confidence: float
    extracted_at: str


class ValidateRequest(BaseModel):
    """Request to validate variable value."""

    value: Any


class ValidateResponse(BaseModel):
    """Response from validation."""

    is_valid: bool
    error: str | None


# API Endpoints


@router.get("/variables", response_model=list[VariableSummary])
async def search_variables(
    industry: str | None = Query(None, description="Filter by industry"),
    pack_id: str | None = Query(None, description="Filter by pack ID"),
    formula_id: str | None = Query(None, description="Filter by formula ID"),
    data_type: str | None = Query(None, description="Filter by data type"),
    source_type: str | None = Query(None, description="Filter by source type"),
    is_active: bool = Query(True, description="Only active variables"),
    tenant: RequestContext = Depends(require_tenant_context),
):
    """Search variables by context."""
    tenant_id = str(tenant.tenant_id)
    # Build safe query with parameterized WHERE conditions only
    # NEVER use string interpolation (f-strings or .format()) for Cypher queries
    where_conditions = ["v.isActive = $is_active", "v.tenant_id = $tenant_id"]
    params: dict[str, Any] = {"is_active": is_active, "tenant_id": tenant_id}

    if industry:
        where_conditions.append("v.industry = $industry")
        params["industry"] = industry

    if data_type:
        where_conditions.append("v.dataType = $data_type")
        params["data_type"] = data_type

    if source_type:
        where_conditions.append("v.sourceType = $source_type")
        params["source_type"] = source_type

    # pack_id and formula_id filters use relationship patterns - safely built
    match_pattern = "(v:Variable)"
    if pack_id:
        match_pattern = "(v:Variable)-[:USED_IN_PACK]->(p:ValuePack)"
        where_conditions.append("p.id = $pack_id")
        params["pack_id"] = pack_id

    if formula_id:
        match_pattern = "(v:Variable)-[:USED_IN_FORMULA]->(f:Formula)"
        where_conditions.append("f.id = $formula_id")
        params["formula_id"] = formula_id

    # Static query structure - no user input in query text
    query_parts = [
        "MATCH",
        match_pattern,
        "WHERE",
        " AND ".join(where_conditions),
        "RETURN v ORDER BY v.name",
    ]
    query = " ".join(query_parts)

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, **params)
        records = await result.data()

        return [
            VariableSummary(
                variable_id=r["v"]["id"],
                name=r["v"]["name"],
                description=r["v"].get("description", ""),
                data_type=r["v"]["dataType"],
                industry=r["v"].get("industry"),
                source_type=r["v"].get("sourceType"),
                is_active=r["v"].get("isActive", True),
                version=r["v"].get("version", "1.0.0"),
            )
            for r in records
        ]


@router.get("/variables/{variable_id}", response_model=VariableDetail)
async def get_variable(
    variable_id: str,
    tenant: RequestContext = Depends(require_tenant_context),
):
    """Get variable definition by ID."""
    tenant_id = str(tenant.tenant_id)
    query = """
    MATCH (v:Variable {id: $variable_id})
    WHERE v.tenant_id = $tenant_id
    RETURN v
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, variable_id=variable_id, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            raise NotFoundError(message = "Variable not found")

        v = record["v"]

        # Reconstruct source binding
        source_binding = None
        if v.get("sourceType"):
            source_binding = SourceBinding(
                source_type=v["sourceType"],
                source_location=v.get("sourceLocation", ""),
                extraction_query=v.get("extractionQuery"),
                transformation=v.get("transformation"),
                fallback_value=v.get("fallbackValue"),
                is_required=v.get("isRequired", True),
            )

        # Reconstruct validation rules
        validation_rules = []
        for rule_data in v.get("validationRules", []):
            validation_rules.append(
                ValidationRule(
                    rule_type=rule_data["ruleType"],
                    parameters=rule_data["parameters"],
                    error_message=rule_data["errorMessage"],
                )
            )

        return VariableDetail(
            variable_id=v["id"],
            name=v["name"],
            description=v.get("description", ""),
            data_type=v["dataType"],
            industry=v.get("industry"),
            applicable_formulas=v.get("applicableFormulas", []),
            applicable_packs=v.get("applicablePacks", []),
            source_binding=source_binding,
            validation_rules=validation_rules,
            created_at=v.get("createdAt", datetime.now(UTC).isoformat()),
            updated_at=v.get("updatedAt"),
            version=v.get("version", "1.0.0"),
            is_active=v.get("isActive", True),
        )


@router.post("/variables", response_model=VariableDetail, status_code=201)
async def create_variable(
    request: VariableCreateRequest,
    tenant: RequestContext = Depends(require_tenant_context),
):
    """Register a new variable definition. Requires authentication."""
    import uuid

    variable_id = str(uuid.uuid4())
    now = datetime.now(UTC).isoformat()
    tenant_id = str(tenant.tenant_id)

    # Build validation rules
    validation_rules = []
    for rule in request.validation_rules:
        validation_rules.append(
            {
                "ruleType": rule.rule_type,
                "parameters": rule.parameters,
                "errorMessage": rule.error_message,
            }
        )

    query = """
    CREATE (v:Variable {
        id: $variable_id,
        name: $name,
        description: $description,
        dataType: $data_type,
        industry: $industry,
        applicableFormulas: $applicable_formulas,
        applicablePacks: $applicable_packs,
        validationRules: $validation_rules,
        createdAt: $created_at,
        version: "1.0.0",
        isActive: true,
        tenant_id: $tenant_id
    })
    SET v.sourceType = $source_type,
        v.sourceLocation = $source_location,
        v.extractionQuery = $extraction_query,
        v.transformation = $transformation,
        v.fallbackValue = $fallback_value,
        v.isRequired = $is_required
    RETURN v
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(
            query,
            variable_id=variable_id,
            name=request.name,
            description=request.description,
            data_type=request.data_type,
            industry=request.industry,
            applicable_formulas=request.applicable_formulas,
            applicable_packs=request.applicable_packs,
            validation_rules=validation_rules,
            created_at=now,
            tenant_id=tenant_id,
            source_type=request.source_binding.source_type
            if request.source_binding
            else None,
            source_location=request.source_binding.source_location
            if request.source_binding
            else None,
            extraction_query=request.source_binding.extraction_query
            if request.source_binding
            else None,
            transformation=request.source_binding.transformation
            if request.source_binding
            else None,
            fallback_value=request.source_binding.fallback_value
            if request.source_binding
            else None,
            is_required=request.source_binding.is_required
            if request.source_binding
            else True,
        )
        record = await result.single()

        if not record:
            raise ServiceUnavailableError(message="Failed to create variable")

        v = record["v"]

        return VariableDetail(
            variable_id=v["id"],
            name=v["name"],
            description=v.get("description", ""),
            data_type=v["dataType"],
            industry=v.get("industry"),
            applicable_formulas=v.get("applicableFormulas", []),
            applicable_packs=v.get("applicablePacks", []),
            source_binding=request.source_binding,
            validation_rules=request.validation_rules,
            created_at=v["createdAt"],
            version=v["version"],
            is_active=True,
        )


@router.put("/variables/{variable_id}", response_model=VariableDetail)
async def update_variable(
    variable_id: str,
    request: VariableUpdateRequest,
    tenant: RequestContext = Depends(require_tenant_context),
):
    """Update variable definition. Requires authentication."""
    tenant_id = str(tenant.tenant_id)
    # Check variable exists
    check_query = "MATCH (v:Variable {id: $variable_id}) WHERE v.tenant_id = $tenant_id RETURN v"
    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(check_query, variable_id=variable_id, tenant_id=tenant_id)
        if not await result.single():
            raise NotFoundError(message = "Variable not found")

    # Build update query
    set_clauses = ["v.updatedAt = $updated_at"]
    params = {
        "variable_id": variable_id,
        "updated_at": datetime.now(UTC).isoformat(),
    }

    if request.name is not None:
        set_clauses.append("v.name = $name")
        params["name"] = request.name
    if request.description is not None:
        set_clauses.append("v.description = $description")
        params["description"] = request.description
    if request.data_type is not None:
        set_clauses.append("v.dataType = $data_type")
        params["data_type"] = request.data_type
    if request.industry is not None:
        set_clauses.append("v.industry = $industry")
        params["industry"] = request.industry
    if request.applicable_formulas is not None:
        set_clauses.append("v.applicableFormulas = $applicable_formulas")
        params["applicable_formulas"] = request.applicable_formulas
    if request.applicable_packs is not None:
        set_clauses.append("v.applicablePacks = $applicable_packs")
        params["applicable_packs"] = request.applicable_packs
    if request.is_active is not None:
        set_clauses.append("v.isActive = $is_active")
        params["is_active"] = request.is_active

    if request.source_binding is not None:
        set_clauses.extend(
            [
                "v.sourceType = $source_type",
                "v.sourceLocation = $source_location",
            ]
        )
        params["source_type"] = request.source_binding.source_type
        params["source_location"] = request.source_binding.source_location

    if request.validation_rules is not None:
        set_clauses.append("v.validationRules = $validation_rules")
        validation_rules = []
        for rule in request.validation_rules:
            validation_rules.append(
                {
                    "ruleType": rule.rule_type,
                    "parameters": rule.parameters,
                    "errorMessage": rule.error_message,
                }
            )
        params["validation_rules"] = validation_rules

    query = f"""
    MATCH (v:Variable {{id: $variable_id}})
    WHERE v.tenant_id = $tenant_id
    SET {", ".join(set_clauses)}
    RETURN v
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, **params)
        record = await result.single()

        if not record:
            raise ServiceUnavailableError(message="Failed to update variable")

    # Return updated variable
    return await get_variable(variable_id, tenant=tenant)


@router.post("/variables/{variable_id}/resolve", response_model=ResolveResponse)
async def resolve_variable(
    variable_id: str,
    request: ResolveRequest,
    tenant: RequestContext = Depends(require_tenant_context),
):
    """Resolve variable value for given context."""
    tenant_id = str(tenant.tenant_id)
    # Get variable definition
    var_query = """
    MATCH (v:Variable {id: $variable_id})
    WHERE v.tenant_id = $tenant_id
    RETURN v
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(var_query, variable_id=variable_id, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            raise NotFoundError(message = "Variable not found")

        v = record["v"]
        data_type = v["dataType"]
        source_type = v.get("sourceType", "user_input")
        source_location = v.get("sourceLocation")

    # Resolve variable value based on source type.
    # Never fabricate synthetic values. Fail closed for unimplemented integrations.
    value = None
    if source_type == "user_input":
        # User input must be provided by the caller; do not fabricate.
        value = v.get("fallbackValue")
    elif source_type == "crm_field":
        raise ServiceUnavailableError(message = "CRM integration not configured. Set CRM_API_URL and CRM_API_KEY.")
    elif source_type == "benchmark_lookup":
        raise ServiceUnavailableError(message = str(_ERROR_BENCHMARK_NOT_CONFIGURED))
    elif source_type == "formula_calculation":
        raise ServiceUnavailableError(message = str(_ERROR_FORMULA_NOT_CONFIGURED))
    elif source_type == "ground_truth":
        raise ServiceUnavailableError(message = "Ground-truth integration not configured. Set LAYER5_BASE_URL.")
    else:
        value = v.get("fallbackValue")

    # Cast to appropriate type
    if data_type == "integer":
        value = int(value) if value else 0
    elif data_type == "decimal":
        from decimal import Decimal

        value = float(Decimal(str(value))) if value else 0.0
    elif data_type == "boolean":
        value = bool(value)

    return ResolveResponse(
        variable_id=variable_id,
        value=value,
        data_type=data_type,
        source_type=source_type,
        source_location=source_location,
        confidence=1.0 if value is not None else 0.0,
        extracted_at=datetime.now(UTC).isoformat(),
    )


@router.post("/variables/{variable_id}/validate", response_model=ValidateResponse)
async def validate_value(
    variable_id: str,
    request: ValidateRequest,
    tenant: RequestContext = Depends(require_tenant_context),
):
    """Validate value against variable rules."""
    tenant_id = str(tenant.tenant_id)
    # Get variable validation rules
    query = """
    MATCH (v:Variable {id: $variable_id})
    WHERE v.tenant_id = $tenant_id
    RETURN v.dataType as data_type, v.validationRules as validation_rules
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, variable_id=variable_id, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            raise NotFoundError(message = "Variable not found")

        data_type = record["data_type"]
        validation_rules = record["validation_rules"] or []

    # Check data type
    try:
        if data_type == "integer":
            int(request.value)
        elif data_type == "decimal":
            float(request.value)
        elif data_type == "boolean":
            if isinstance(request.value, str):
                request.value.lower() in ("true", "false", "1", "0", "yes", "no")
        elif data_type == "date":
            datetime.fromisoformat(str(request.value))
    except (ValueError, TypeError):
        return ValidateResponse(
            is_valid=False,
            error=f"Invalid data type: expected {data_type}",
        )

    # Run validation rules
    for rule in validation_rules:
        params = rule.get("parameters", {})

        if rule["ruleType"] == "range":
            try:
                val = float(request.value)
                if "min" in params and val < params["min"]:
                    return ValidateResponse(
                        is_valid=False,
                        error=rule.get(
                            "errorMessage", f"Value below minimum {params['min']}"
                        ),
                    )
                if "max" in params and val > params["max"]:
                    return ValidateResponse(
                        is_valid=False,
                        error=rule.get(
                            "errorMessage", f"Value above maximum {params['max']}"
                        ),
                    )
            except (ValueError, TypeError):
                return ValidateResponse(
                    is_valid=False,
                    error=rule.get("errorMessage", "Value must be numeric for range validation"),
                )

        elif rule["ruleType"] == "regex":
            import re

            pattern = params.get("pattern", ".*")
            if not re.match(pattern, str(request.value)):
                return ValidateResponse(
                    is_valid=False,
                    error=rule.get("errorMessage", "Value does not match pattern"),
                )

        elif rule["ruleType"] == "enum":
            allowed = params.get("values", [])
            if request.value not in allowed:
                return ValidateResponse(
                    is_valid=False,
                    error=rule.get(
                        "errorMessage", f"Value not in allowed values: {allowed}"
                    ),
                )

    return ValidateResponse(is_valid=True, error=None)


# ── Aggregate Endpoints ──────────────────────────────────────────────────────


class VariableStatsResponse(BaseModel):
    """Aggregate statistics for the variable registry."""

    total: int = 0
    validated: int = 0
    pending: int = 0
    failed: int = 0
    manual_sources: int = 0
    avg_usage: float = 0.0


class SourceBindingResponse(BaseModel):
    """Source binding connection metadata."""

    id: str
    name: str
    source_type: str
    connection_string: str | None = None
    status: Literal["connected", "disconnected", "error"]
    last_sync: str | None = None
    variables_bound: int = 0
    error_message: str | None = None


@router.get("/variables/stats", response_model=VariableStatsResponse)
async def get_variable_stats(
    tenant: RequestContext = Depends(require_tenant_context),
):
    """Return aggregate statistics for the variable registry."""
    tenant_id = str(tenant.tenant_id)
    query = """
    MATCH (v:Variable)
    WHERE v.tenant_id = $tenant_id
    WITH count(v) AS total,
         count(CASE WHEN v.validationStatus = 'validated' THEN 1 END) AS validated,
         count(CASE WHEN v.validationStatus = 'pending' THEN 1 END) AS pending,
         count(CASE WHEN v.validationStatus = 'failed' THEN 1 END) AS failed,
         count(CASE WHEN v.sourceType IN ['user_input', 'Manual'] THEN 1 END) AS manual_sources,
         avg(COALESCE(v.usedInCount, 0)) AS avg_usage
    RETURN total, validated, pending, failed, manual_sources, avg_usage
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, tenant_id=tenant_id)
        record = await result.single()

        if not record:
            return VariableStatsResponse()

        return VariableStatsResponse(
            total=record["total"],
            validated=record["validated"],
            pending=record["pending"],
            failed=record["failed"],
            manual_sources=record["manual_sources"],
            avg_usage=round(record["avg_usage"] or 0, 1),
        )


@router.get("/variables/bindings", response_model=list[SourceBindingResponse])
async def list_source_bindings(
    tenant: RequestContext = Depends(require_tenant_context),
):
    """List data source binding configurations and their health status."""
    tenant_id = str(tenant.tenant_id)
    query = """
    MATCH (sb:SourceBinding)
    WHERE sb.tenant_id = $tenant_id
    OPTIONAL MATCH (v:Variable)-[:BOUND_TO]->(sb)
    RETURN sb, count(v) AS variables_bound
    ORDER BY sb.name
    """

    async with await create_neo4j_tenant_session(tenant_id) as neo4j:
        result = await neo4j.run(query, tenant_id=tenant_id)
        records = await result.data()

        return [
            SourceBindingResponse(
                id=r["sb"]["id"],
                name=r["sb"]["name"],
                source_type=r["sb"].get("sourceType", "unknown"),
                connection_string=r["sb"].get("connectionString"),
                status=r["sb"].get("status", "disconnected"),
                last_sync=r["sb"].get("lastSync"),
                variables_bound=r.get("variables_bound", 0),
                error_message=r["sb"].get("errorMessage"),
            )
            for r in records
        ]
