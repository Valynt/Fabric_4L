from value_fabric.shared.error_handling.exceptions import NotFoundError, ValidationError
"""
FastAPI router for Layer 5 Governance APIs.

Endpoints:
  Formula Governance:
    POST   /governance/formulas                    — Create a new Formula
    GET    /governance/formulas                    — List Formulas (paginated, filterable)
    GET    /governance/formulas/{id}               — Get a single Formula
    PUT    /governance/formulas/{id}               — Update Formula metadata
    DELETE /governance/formulas/{id}               — Soft-delete/Archive Formula
    POST   /governance/formulas/{id}/versions      — Create new Formula version
    GET    /governance/formulas/{id}/versions      — List Formula versions
    GET    /governance/formulas/{id}/versions/{version} — Get specific version
    POST   /governance/formulas/{id}/versions/{version}/submit — Submit for approval
    POST   /governance/formulas/{id}/versions/{version}/approve — Approve version
    POST   /governance/formulas/{id}/versions/{version}/reject — Reject version
    POST   /governance/formulas/{id}/versions/{version}/request-changes — Request changes
    POST   /governance/formulas/{id}/deprecate     — Deprecate Formula
    POST   /governance/formulas/{id}/archive       — Archive Formula
    GET    /governance/formulas/{id}/audit         — Get audit trail

  Benchmark Governance:
    POST   /governance/benchmarks                  — Create a new Benchmark
    GET    /governance/benchmarks                  — List Benchmarks
    GET    /governance/benchmarks/{id}             — Get a single Benchmark
    POST   /governance/benchmarks/{id}/versions    — Create new Benchmark version
    POST   /governance/benchmarks/{id}/versions/{version}/submit — Submit for approval
    POST   /governance/benchmarks/{id}/versions/{version}/approve — Approve version
    POST   /governance/benchmarks/{id}/deprecate   — Deprecate Benchmark

  Policy Governance:
    POST   /governance/policies                   — Create a new Policy
    GET    /governance/policies                   — List Policies
    GET    /governance/policies/{id}              — Get a single Policy
    POST   /governance/policies/{id}/evaluate     — Evaluate policy against entity
    GET    /governance/policies/{id}/applications  — Get policy application history

  Assumption Governance:
    POST   /governance/assumptions                — Create a new Assumption
    GET    /governance/assumptions                — List Assumptions
    GET    /governance/assumptions/{id}           — Get a single Assumption
    POST   /governance/assumptions/{id}/evidence  — Add evidence
    POST   /governance/assumptions/{id}/submit    — Submit for approval (high-impact)
    POST   /governance/assumptions/{id}/approve   — Approve assumption
    POST   /governance/assumptions/{id}/reject    — Reject assumption

  Value Realization Ledger:
    POST   /governance/value-entries              — Create a value realization entry
    GET    /governance/value-entries              — List value entries
    GET    /governance/value-entries/{id}         — Get a single value entry
    POST   /governance/value-entries/{id}/updates  — Add value update
    GET    /governance/value-entries/{id}/updates  — Get update history

  Approval Workflow:
    GET    /governance/approvals                  — List approval requests
    GET    /governance/approvals/{id}             — Get approval request details
    POST   /governance/approvals/{id}/submit     — Submit for approval
    POST   /governance/approvals/{id}/approve     — Approve request
    POST   /governance/approvals/{id}/reject      — Reject request
    POST   /governance/approvals/{id}/request-changes — Request changes
"""

import logging
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling import sanitize_error_for_log, sanitize_public_error

from ..database import get_db_from_context
from ..services.formula_governance_service import (
    FormulaNotFoundError,
    FormulaService,
    FormulaSlugConflictError,
    FormulaVersionConflictError,
)
from ..services.benchmark_governance_service import (
    BenchmarkNotFoundError,
    BenchmarkService,
    BenchmarkSlugConflictError,
    BenchmarkVersionConflictError,
)
from ..services.policy_governance_service import (
    PolicyNotFoundError,
    PolicyService,
    PolicySlugConflictError,
)
from ..services.assumption_approval_service import (
    AssumptionApprovalService,
    AssumptionNotFoundError,
)
from ..services.value_realization_service import (
    ValueEntryNotFoundError,
    ValueRealizationService,
)
from ..services.approval_state_machine import (
    ApprovalStateMachine,
    ApprovalRequestNotFoundError,
)
from ..observability.governance_metrics import (
    get_metrics,
    record_governance_operation,
    record_governance_operation_duration,
)
from .auth import TokenClaims, authorize_action, get_current_user

logger = logging.getLogger(__name__)

governance_router = APIRouter(prefix="/api/v1/governance", tags=["governance"])


def _safe_http_detail(exc: Exception, *, status_code: int) -> str:
    logger.exception("governance_router_error", extra={"status_code": status_code, "error": sanitize_error_for_log(exc)})
    return sanitize_public_error(exc, status_code=status_code).message


# ---------------------------------------------------------------------------
# Metrics Endpoint
# ---------------------------------------------------------------------------


@governance_router.get(
    "/metrics",
    summary="Governance Metrics",
    description="Prometheus metrics for Layer 5 governance operations.",
    include_in_schema=False,
)
async def governance_metrics():
    """Return governance metrics in Prometheus format."""
    from fastapi.responses import Response

    return Response(content=get_metrics(), media_type="text/plain")


# ---------------------------------------------------------------------------
# Common Schemas
# ---------------------------------------------------------------------------


class ErrorEnvelope(BaseModel):
    """Standard error response envelope."""

    error: str = Field(..., description="Error type/category")
    message: str = Field(..., description="Human-readable error message")
    details: dict[str, Any] | None = Field(None, description="Additional error details")


class PaginatedResponse(BaseModel):
    """Standard paginated response envelope."""

    items: list[Any]
    total: int
    page: int
    page_size: int
    has_next: bool


# ---------------------------------------------------------------------------
# Formula Governance Schemas
# ---------------------------------------------------------------------------


class FormulaParameterCreate(BaseModel):
    """Schema for creating a formula parameter."""

    name: str = Field(..., max_length=128)
    display_name: str | None = Field(None, max_length=128)
    parameter_type: str = Field(..., description="number, string, boolean, currency, percentage, date, duration")
    description: str | None = None
    required: bool = True
    default_value: Any = None
    min_value: Any = None
    max_value: Any = None
    allowed_values: list[Any] | None = None


class FormulaCreate(BaseModel):
    """Schema for creating a formula."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    formula_type: str = Field(..., description="roi_calculation, cost_savings, revenue_impact, efficiency_gain, risk_reduction, custom")
    description: str | None = None
    expression: str = Field(..., description="Formula expression")
    expression_language: str = Field(default="python", description="python, javascript, etc.")
    input_schema: dict[str, Any] = Field(..., description="JSON Schema for input validation")
    output_schema: dict[str, Any] = Field(..., description="JSON Schema for output validation")
    parameters: list[FormulaParameterCreate] = Field(default_factory=list)


class FormulaResponse(BaseModel):
    """Schema for formula response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    formula_type: str
    description: str | None
    current_version: str
    latest_version: str
    input_schema: dict[str, Any]
    output_schema: dict[str, Any]
    is_active: bool
    deprecated_at: datetime | None
    deprecation_reason: str | None
    created_at: datetime
    updated_at: datetime


class FormulaVersionCreate(BaseModel):
    """Schema for creating a formula version."""

    version: str = Field(..., description="Semver version string")
    expression: str = Field(..., description="Formula expression")
    expression_language: str = Field(default="python")
    change_description: str | None = None


class FormulaVersionResponse(BaseModel):
    """Schema for formula version response."""

    id: UUID
    tenant_id: UUID
    formula_id: UUID
    version: str
    expression: str
    expression_language: str
    status: str
    validation_errors: dict[str, Any] | None
    test_results: dict[str, Any] | None
    change_description: str | None
    changed_by: str | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime


# ---------------------------------------------------------------------------
# Formula Governance Endpoints
# ---------------------------------------------------------------------------


@governance_router.post(
    "/formulas",
    response_model=FormulaResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Formula",
    description="Create a new value calculation formula with versioning and schema validation.",
    responses={
        201: {"description": "Formula created successfully"},
        400: {"description": "Invalid request data"},
        409: {"description": "Formula slug already exists"},
    },
)
async def create_formula(
    request: Request,
    payload: FormulaCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FormulaResponse:
    """Create a new Formula in DRAFT status."""
    import time

    authorize_action("layer5.governance.formulas.create", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()
    start_time = time.time()

    try:
        # Convert parameters to dict format
        parameters = [p.model_dump() for p in payload.parameters] if payload.parameters else None

        formula = await service.create_formula(
            db=db,
            tenant_id=tenant_id,
            name=payload.name,
            slug=payload.slug,
            formula_type=payload.formula_type,
            expression=payload.expression,
            expression_language=payload.expression_language,
            input_schema=payload.input_schema,
            output_schema=payload.output_schema,
            parameters=parameters,
            description=payload.description,
            created_by=caller.user_id,
        )

        duration = time.time() - start_time
        record_governance_operation_duration("create", "formula", duration)
        record_governance_operation("create", "formula", "success")

        return FormulaResponse(
            id=formula.id,
            tenant_id=formula.tenant_id,
            name=formula.name,
            slug=formula.slug,
            formula_type=formula.formula_type,
            description=formula.description,
            current_version=formula.current_version,
            latest_version=formula.latest_version,
            input_schema=formula.input_schema,
            output_schema=formula.output_schema,
            is_active=formula.is_active,
            deprecated_at=formula.deprecated_at,
            deprecation_reason=formula.deprecation_reason,
            created_at=formula.created_at,
            updated_at=formula.updated_at,
        )

    except FormulaSlugConflictError as e:
        duration = time.time() - start_time
        record_governance_operation_duration("create", "formula", duration)
        record_governance_operation("create", "formula", "conflict")
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_safe_http_detail(e, status_code=500),
        )
    except Exception as e:
        duration = time.time() - start_time
        record_governance_operation_duration("create", "formula", duration)
        record_governance_operation("create", "formula", "error")
        logger.error("Error creating formula: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create formula",
        )


@governance_router.get(
    "/formulas",
    response_model=PaginatedResponse,
    summary="List Formulas",
    description="List formulas with pagination and filtering.",
)
async def list_formulas(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    formula_type: str | None = Query(None),
    is_active: bool | None = Query(None),
) -> PaginatedResponse:
    """List formulas scoped to tenant."""
    authorize_action("layer5.governance.formulas.list", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()

    try:
        formulas, total = await service.list_formulas(
            db=db,
            tenant_id=tenant_id,
            formula_type=formula_type,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

        items = [
            FormulaResponse(
                id=f.id,
                tenant_id=f.tenant_id,
                name=f.name,
                slug=f.slug,
                formula_type=f.formula_type,
                description=f.description,
                current_version=f.current_version,
                latest_version=f.latest_version,
                input_schema=f.input_schema,
                output_schema=f.output_schema,
                is_active=f.is_active,
                deprecated_at=f.deprecated_at,
                deprecation_reason=f.deprecation_reason,
                created_at=f.created_at,
                updated_at=f.updated_at,
            )
            for f in formulas
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    except Exception as e:
        logger.error("Error listing formulas: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list formulas",
        )


@governance_router.get(
    "/formulas/{formula_id}",
    response_model=FormulaResponse,
    summary="Get a Formula",
    description="Get a single formula by ID.",
    responses={
        404: {"description": "Formula not found"},
    },
)
async def get_formula(
    formula_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FormulaResponse:
    """Get a formula by ID with tenant scoping."""
    authorize_action("layer5.governance.formulas.get", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()

    try:
        formula = await service.get_formula(db, tenant_id, formula_id)

        return FormulaResponse(
            id=formula.id,
            tenant_id=formula.tenant_id,
            name=formula.name,
            slug=formula.slug,
            formula_type=formula.formula_type,
            description=formula.description,
            current_version=formula.current_version,
            latest_version=formula.latest_version,
            input_schema=formula.input_schema,
            output_schema=formula.output_schema,
            is_active=formula.is_active,
            deprecated_at=formula.deprecated_at,
            deprecation_reason=formula.deprecation_reason,
            created_at=formula.created_at,
            updated_at=formula.updated_at,
        )

    except FormulaNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error getting formula: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get formula",
        )


@governance_router.post(
    "/formulas/{formula_id}/versions",
    response_model=FormulaVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Formula version",
    description="Create a new version of an existing formula.",
    responses={
        201: {"description": "Formula version created successfully"},
        404: {"description": "Formula not found"},
        400: {"description": "Invalid version or expression"},
    },
)
async def create_formula_version(
    formula_id: UUID,
    payload: FormulaVersionCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FormulaVersionResponse:
    """Create a new version of a formula."""
    authorize_action("layer5.governance.formulas.create_version", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()

    try:
        version = await service.create_formula_version(
            db=db,
            tenant_id=tenant_id,
            formula_id=formula_id,
            version=payload.version,
            expression=payload.expression,
            expression_language=payload.expression_language,
            change_description=payload.change_description,
            changed_by=caller.user_id,
        )

        return FormulaVersionResponse(
            id=version.id,
            tenant_id=version.tenant_id,
            formula_id=version.formula_id,
            version=version.version,
            expression=version.expression,
            expression_language=version.expression_language,
            status=version.status,
            validation_errors=version.validation_errors,
            test_results=version.test_results,
            change_description=version.change_description,
            changed_by=version.changed_by,
            approved_by=version.approved_by,
            approved_at=version.approved_at,
            created_at=version.created_at,
        )

    except FormulaNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except FormulaVersionConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_safe_http_detail(e, status_code=500),
        )
    except Exception as e:
        logger.error("Error creating formula version: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create formula version",
        )


@governance_router.post(
    "/formulas/{formula_id}/versions/{version}/submit",
    response_model=FormulaVersionResponse,
    summary="Submit Formula version for approval",
    description="Submit a formula version for approval (DRAFT → PENDING).",
    responses={
        200: {"description": "Version submitted successfully"},
        404: {"description": "Formula or version not found"},
        400: {"description": "Invalid status transition"},
    },
)
async def submit_formula_version(
    formula_id: UUID,
    version: str,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FormulaVersionResponse:
    """Submit a formula version for approval."""
    authorize_action("layer5.governance.formulas.submit", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()

    try:
        version_obj = await service.submit_formula_version(
            db=db,
            tenant_id=tenant_id,
            formula_id=formula_id,
            version=version,
            submitter=caller.user_id,
        )

        return FormulaVersionResponse(
            id=version_obj.id,
            tenant_id=version_obj.tenant_id,
            formula_id=version_obj.formula_id,
            version=version_obj.version,
            expression=version_obj.expression,
            expression_language=version_obj.expression_language,
            status=version_obj.status,
            validation_errors=version_obj.validation_errors,
            test_results=version_obj.test_results,
            change_description=version_obj.change_description,
            changed_by=version_obj.changed_by,
            approved_by=version_obj.approved_by,
            approved_at=version_obj.approved_at,
            created_at=version_obj.created_at,
        )

    except FormulaNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except ValueError as e:
        raise ValidationError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error submitting formula version: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit formula version",
        )


@governance_router.post(
    "/formulas/{formula_id}/versions/{version}/approve",
    response_model=FormulaVersionResponse,
    summary="Approve Formula version",
    description="Approve a formula version (PENDING → APPROVED).",
    responses={
        200: {"description": "Version approved successfully"},
        403: {"description": "Insufficient permissions"},
        400: {"description": "Invalid status transition"},
    },
)
async def approve_formula_version(
    formula_id: UUID,
    version: str,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FormulaVersionResponse:
    """Approve a formula version."""
    authorize_action("layer5.governance.formulas.approve", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()

    try:
        version_obj = await service.approve_formula_version(
            db=db,
            tenant_id=tenant_id,
            formula_id=formula_id,
            version=version,
            approver=caller.user_id,
        )

        return FormulaVersionResponse(
            id=version_obj.id,
            tenant_id=version_obj.tenant_id,
            formula_id=version_obj.formula_id,
            version=version_obj.version,
            expression=version_obj.expression,
            expression_language=version_obj.expression_language,
            status=version_obj.status,
            validation_errors=version_obj.validation_errors,
            test_results=version_obj.test_results,
            change_description=version_obj.change_description,
            changed_by=version_obj.changed_by,
            approved_by=version_obj.approved_by,
            approved_at=version_obj.approved_at,
            created_at=version_obj.created_at,
        )

    except FormulaNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error approving formula version: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve formula version",
        )


@governance_router.post(
    "/formulas/{formula_id}/versions/{version}/reject",
    response_model=FormulaVersionResponse,
    summary="Reject Formula version",
    description="Reject a formula version (PENDING → REJECTED).",
    responses={
        200: {"description": "Version rejected successfully"},
        403: {"description": "Insufficient permissions"},
        400: {"description": "Invalid status transition"},
    },
)
async def reject_formula_version(
    formula_id: UUID,
    version: str,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FormulaVersionResponse:
    """Reject a formula version."""
    authorize_action("layer5.governance.formulas.reject", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()

    try:
        version_obj = await service.reject_formula_version(
            db=db,
            tenant_id=tenant_id,
            formula_id=formula_id,
            version=version,
            reviewer=caller.user_id,
        )

        return FormulaVersionResponse(
            id=version_obj.id,
            tenant_id=version_obj.tenant_id,
            formula_id=version_obj.formula_id,
            version=version_obj.version,
            expression=version_obj.expression,
            expression_language=version_obj.expression_language,
            status=version_obj.status,
            validation_errors=version_obj.validation_errors,
            test_results=version_obj.test_results,
            change_description=version_obj.change_description,
            changed_by=version_obj.changed_by,
            approved_by=version_obj.approved_by,
            approved_at=version_obj.approved_at,
            created_at=version_obj.created_at,
        )

    except FormulaNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error rejecting formula version: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject formula version",
        )


@governance_router.post(
    "/formulas/{formula_id}/deprecate",
    response_model=FormulaResponse,
    summary="Deprecate a Formula",
    description="Deprecate a formula (APPROVED → DEPRECATED).",
    responses={
        200: {"description": "Formula deprecated successfully"},
        404: {"description": "Formula not found"},
        400: {"description": "Formula already deprecated"},
    },
)
async def deprecate_formula(
    formula_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    reason: str = Query(..., description="Reason for deprecation"),
) -> FormulaResponse:
    """Deprecate a formula."""
    authorize_action("layer5.governance.formulas.deprecate", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()

    try:
        formula = await service.deprecate_formula(
            db=db,
            tenant_id=tenant_id,
            formula_id=formula_id,
            reason=reason,
            deprecator=caller.user_id,
        )

        return FormulaResponse(
            id=formula.id,
            tenant_id=formula.tenant_id,
            name=formula.name,
            slug=formula.slug,
            formula_type=formula.formula_type,
            description=formula.description,
            current_version=formula.current_version,
            latest_version=formula.latest_version,
            input_schema=formula.input_schema,
            output_schema=formula.output_schema,
            is_active=formula.is_active,
            deprecated_at=formula.deprecated_at,
            deprecation_reason=formula.deprecation_reason,
            created_at=formula.created_at,
            updated_at=formula.updated_at,
        )

    except FormulaNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except ValueError as e:
        raise ValidationError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error deprecating formula: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to deprecate formula",
        )


@governance_router.post(
    "/formulas/{formula_id}/archive",
    response_model=FormulaResponse,
    summary="Archive a Formula",
    description="Archive a formula (DEPRECATED → ARCHIVED or DRAFT → ARCHIVED).",
    responses={
        200: {"description": "Formula archived successfully"},
        404: {"description": "Formula not found"},
    },
)
async def archive_formula(
    formula_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FormulaResponse:
    """Archive a formula."""
    authorize_action("layer5.governance.formulas.archive", caller)
    tenant_id = caller.tenant_id

    service = FormulaService()

    try:
        formula = await service.archive_formula(
            db=db,
            tenant_id=tenant_id,
            formula_id=formula_id,
            archiver=caller.user_id,
        )

        return FormulaResponse(
            id=formula.id,
            tenant_id=formula.tenant_id,
            name=formula.name,
            slug=formula.slug,
            formula_type=formula.formula_type,
            description=formula.description,
            current_version=formula.current_version,
            latest_version=formula.latest_version,
            input_schema=formula.input_schema,
            output_schema=formula.output_schema,
            is_active=formula.is_active,
            deprecated_at=formula.deprecated_at,
            deprecation_reason=formula.deprecation_reason,
            created_at=formula.created_at,
            updated_at=formula.updated_at,
        )

    except FormulaNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except ValueError as e:
        raise ValidationError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error archiving formula: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to archive formula",
        )


# ---------------------------------------------------------------------------
# Benchmark Governance Schemas
# ---------------------------------------------------------------------------


class BenchmarkCreate(BaseModel):
    """Schema for creating a benchmark."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    benchmark_type: str = Field(..., description="industry_standard, competitive, historical, customer_reference, internal, third_party")
    description: str | None = None
    source_name: str = Field(..., max_length=128)
    source_url: str | None = None
    source_type: str = Field(..., description="research, survey, internal, external")
    source_date: datetime | None = None
    collection_methodology: str | None = None
    confidence_level: str = Field(default="medium", description="high, medium, low")
    sample_size: int | None = None
    margin_of_error: dict[str, Any] | None = None
    data_quality_notes: str | None = None


class BenchmarkResponse(BaseModel):
    """Schema for benchmark response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    benchmark_type: str
    description: str | None
    current_version: str
    latest_version: str
    source_name: str
    source_url: str | None
    source_type: str
    source_date: datetime | None
    confidence_level: str
    sample_size: int | None
    is_active: bool
    deprecated_at: datetime | None
    created_at: datetime
    updated_at: datetime


class BenchmarkVersionCreate(BaseModel):
    """Schema for creating a benchmark version."""

    version: str = Field(..., description="Semver version string")
    data: dict[str, Any] = Field(..., description="Benchmark data")
    data_schema: dict[str, Any] = Field(..., description="JSON Schema for data structure")
    effective_from: datetime = Field(..., description="Effective start date")
    effective_until: datetime | None = None
    change_description: str | None = None


class BenchmarkCreateWithVersion(BaseModel):
    """Schema for creating a benchmark with initial version."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    benchmark_type: str = Field(..., description="industry_standard, competitive, historical, customer_reference, internal, third_party")
    description: str | None = None
    source_name: str = Field(..., max_length=128)
    source_url: str | None = None
    source_type: str = Field(..., description="research, survey, internal, external")
    source_date: datetime | None = None
    collection_methodology: str | None = None
    confidence_level: str = Field(default="medium", description="high, medium, low")
    sample_size: int | None = None
    margin_of_error: dict[str, Any] | None = None
    data_quality_notes: str | None = None
    # Initial version data
    data: dict[str, Any] = Field(..., description="Benchmark data")
    data_schema: dict[str, Any] = Field(..., description="JSON Schema for data structure")
    effective_from: datetime = Field(..., description="Effective start date")
    effective_until: datetime | None = None
    version: str = Field(default="1.0.0", description="Initial version")


# ---------------------------------------------------------------------------
# Benchmark Governance Endpoints
# ---------------------------------------------------------------------------


@governance_router.post(
    "/benchmarks",
    response_model=BenchmarkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Benchmark",
    description="Create a new benchmark dataset with versioning and metadata.",
)
async def create_benchmark(
    request: Request,
    payload: BenchmarkCreateWithVersion,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> BenchmarkResponse:
    """Create a new Benchmark in DRAFT status."""
    authorize_action("layer5.governance.benchmarks.create", caller)
    tenant_id = caller.tenant_id

    service = BenchmarkService()

    try:
        benchmark = await service.create_benchmark(
            db=db,
            tenant_id=tenant_id,
            name=payload.name,
            slug=payload.slug,
            benchmark_type=payload.benchmark_type,
            source_name=payload.source_name,
            source_type=payload.source_type,
            data=payload.data,
            data_schema=payload.data_schema,
            effective_from=payload.effective_from,
            version=payload.version,
            source_url=payload.source_url,
            source_date=payload.source_date,
            collection_methodology=payload.collection_methodology,
            confidence_level=payload.confidence_level,
            sample_size=payload.sample_size,
            margin_of_error=payload.margin_of_error,
            data_quality_notes=payload.data_quality_notes,
            description=payload.description,
            created_by=caller.user_id,
        )

        return BenchmarkResponse(
            id=benchmark.id,
            tenant_id=benchmark.tenant_id,
            name=benchmark.name,
            slug=benchmark.slug,
            benchmark_type=benchmark.benchmark_type,
            description=benchmark.description,
            current_version=benchmark.current_version,
            latest_version=benchmark.latest_version,
            source_name=benchmark.source_name,
            source_url=benchmark.source_url,
            source_type=benchmark.source_type,
            source_date=benchmark.source_date,
            confidence_level=benchmark.confidence_level,
            sample_size=benchmark.sample_size,
            is_active=benchmark.is_active,
            deprecated_at=benchmark.deprecated_at,
            created_at=benchmark.created_at,
            updated_at=benchmark.updated_at,
        )

    except BenchmarkSlugConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_safe_http_detail(e, status_code=500),
        )
    except Exception as e:
        logger.error("Error creating benchmark: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create benchmark",
        )


@governance_router.get(
    "/benchmarks",
    response_model=PaginatedResponse,
    summary="List Benchmarks",
    description="List benchmarks with pagination and filtering.",
)
async def list_benchmarks(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    benchmark_type: str | None = Query(None),
    is_active: bool | None = Query(None),
) -> PaginatedResponse:
    """List benchmarks scoped to tenant."""
    authorize_action("layer5.governance.benchmarks.list", caller)
    tenant_id = caller.tenant_id

    service = BenchmarkService()

    try:
        benchmarks, total = await service.list_benchmarks(
            db=db,
            tenant_id=tenant_id,
            benchmark_type=benchmark_type,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

        items = [
            BenchmarkResponse(
                id=b.id,
                tenant_id=b.tenant_id,
                name=b.name,
                slug=b.slug,
                benchmark_type=b.benchmark_type,
                description=b.description,
                current_version=b.current_version,
                latest_version=b.latest_version,
                source_name=b.source_name,
                source_url=b.source_url,
                source_type=b.source_type,
                source_date=b.source_date,
                confidence_level=b.confidence_level,
                sample_size=b.sample_size,
                is_active=b.is_active,
                deprecated_at=b.deprecated_at,
                created_at=b.created_at,
                updated_at=b.updated_at,
            )
            for b in benchmarks
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    except Exception as e:
        logger.error("Error listing benchmarks: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list benchmarks",
        )


@governance_router.post(
    "/benchmarks/{benchmark_id}/versions",
    response_model=FormulaVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Benchmark version",
    description="Create a new version of an existing benchmark.",
)
async def create_benchmark_version(
    benchmark_id: UUID,
    payload: BenchmarkVersionCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FormulaVersionResponse:
    """Create a new version of a benchmark."""
    authorize_action("layer5.governance.benchmarks.create_version", caller)
    tenant_id = caller.tenant_id

    service = BenchmarkService()

    try:
        version = await service.create_benchmark_version(
            db=db,
            tenant_id=tenant_id,
            benchmark_id=benchmark_id,
            version=payload.version,
            data=payload.data,
            data_schema=payload.data_schema,
            effective_from=payload.effective_from,
            effective_until=payload.effective_until,
            change_description=payload.change_description,
            changed_by=caller.user_id,
        )

        return FormulaVersionResponse(
            id=version.id,
            tenant_id=version.tenant_id,
            formula_id=benchmark_id,  # Reusing FormulaVersionResponse schema
            version=version.version,
            expression="",  # Not applicable for benchmarks
            expression_language="",
            status=version.status,
            validation_errors=None,
            test_results=None,
            change_description=version.change_description,
            changed_by=version.changed_by,
            approved_by=version.approved_by,
            approved_at=version.approved_at,
            created_at=version.created_at,
        )

    except BenchmarkNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except BenchmarkVersionConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_safe_http_detail(e, status_code=500),
        )
    except Exception as e:
        logger.error("Error creating benchmark version: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create benchmark version",
        )


# ---------------------------------------------------------------------------
# Policy Governance Schemas
# ---------------------------------------------------------------------------


class PolicyRuleCreate(BaseModel):
    """Schema for creating a policy rule."""

    rule_name: str = Field(..., max_length=128)
    rule_type: str = Field(..., description="validation, constraint, business_rule, security, compliance")
    condition: dict[str, Any] = Field(..., description="Rule condition")
    action: str = Field(..., description="Action to take if condition is met")
    severity: str = Field(default="medium", description="high, medium, low")
    description: str | None = None


class PolicyCreate(BaseModel):
    """Schema for creating a policy."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    policy_type: str = Field(..., description="validation, approval, access_control, data_quality, compliance, security, custom")
    description: str = Field(..., description="Policy description")
    rules: list[PolicyRuleCreate] = Field(..., description="List of policy rules")
    severity: str = Field(default="medium", description="high, medium, low")
    scope: dict[str, Any] | None = None


class PolicyResponse(BaseModel):
    """Schema for policy response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    policy_type: str
    description: str
    current_version: str | None
    latest_version: str
    severity: str
    scope: dict[str, Any] | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class PolicyEvaluationRequest(BaseModel):
    """Schema for policy evaluation request."""

    entity_id: UUID
    entity_type: str = Field(..., description="formula, benchmark, assumption, value_entry, etc.")
    context: dict[str, Any] = Field(..., description="Evaluation context")


class PolicyEvaluationResponse(BaseModel):
    """Schema for policy evaluation response."""

    policy_id: UUID
    entity_id: UUID
    entity_type: str
    is_compliant: bool
    passed_rules: list[dict[str, Any]]
    failed_rules: list[dict[str, Any]]
    evaluation_id: UUID
    evaluated_at: datetime


# ---------------------------------------------------------------------------
# Policy Governance Endpoints
# ---------------------------------------------------------------------------


@governance_router.post(
    "/policies",
    response_model=PolicyResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Policy",
    description="Create a new policy with rules and versioning.",
)
async def create_policy(
    request: Request,
    payload: PolicyCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> PolicyResponse:
    """Create a new Policy in DRAFT status."""
    authorize_action("layer5.governance.policies.create", caller)
    tenant_id = caller.tenant_id

    service = PolicyService()

    try:
        # Convert rules to dict format
        rules = [r.model_dump() for r in payload.rules]

        policy = await service.create_policy(
            db=db,
            tenant_id=tenant_id,
            name=payload.name,
            slug=payload.slug,
            policy_type=payload.policy_type,
            description=payload.description,
            rules=rules,
            severity=payload.severity,
            scope=payload.scope,
            created_by=caller.user_id,
        )

        return PolicyResponse(
            id=policy.id,
            tenant_id=policy.tenant_id,
            name=policy.name,
            slug=policy.slug,
            policy_type=policy.policy_type,
            description=policy.description,
            current_version=policy.current_version,
            latest_version=policy.latest_version,
            severity=policy.severity,
            scope=policy.scope,
            is_active=policy.is_active,
            created_at=policy.created_at,
            updated_at=policy.updated_at,
        )

    except PolicySlugConflictError as e:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=_safe_http_detail(e, status_code=500),
        )
    except Exception as e:
        logger.error("Error creating policy: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create policy",
        )


@governance_router.get(
    "/policies",
    response_model=PaginatedResponse,
    summary="List Policies",
    description="List policies with pagination and filtering.",
)
async def list_policies(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    policy_type: str | None = Query(None),
    is_active: bool | None = Query(None),
) -> PaginatedResponse:
    """List policies scoped to tenant."""
    authorize_action("layer5.governance.policies.list", caller)
    tenant_id = caller.tenant_id

    service = PolicyService()

    try:
        policies, total = await service.list_policies(
            db=db,
            tenant_id=tenant_id,
            policy_type=policy_type,
            is_active=is_active,
            page=page,
            page_size=page_size,
        )

        items = [
            PolicyResponse(
                id=p.id,
                tenant_id=p.tenant_id,
                name=p.name,
                slug=p.slug,
                policy_type=p.policy_type,
                description=p.description,
                current_version=p.current_version,
                latest_version=p.latest_version,
                severity=p.severity,
                scope=p.scope,
                is_active=p.is_active,
                created_at=p.created_at,
                updated_at=p.updated_at,
            )
            for p in policies
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    except Exception as e:
        logger.error("Error listing policies: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list policies",
        )


@governance_router.post(
    "/policies/{policy_id}/evaluate",
    response_model=PolicyEvaluationResponse,
    summary="Evaluate a Policy",
    description="Evaluate a policy against an entity.",
)
async def evaluate_policy(
    policy_id: UUID,
    payload: PolicyEvaluationRequest,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> PolicyEvaluationResponse:
    """Evaluate a policy against an entity."""
    authorize_action("layer5.governance.policies.evaluate", caller)
    tenant_id = caller.tenant_id

    service = PolicyService()

    try:
        result = await service.evaluate_policy(
            db=db,
            tenant_id=tenant_id,
            policy_id=policy_id,
            entity_id=payload.entity_id,
            entity_type=payload.entity_type,
            context=payload.context,
            evaluator=caller.user_id,
        )

        return PolicyEvaluationResponse(
            policy_id=UUID(result["policy_id"]),
            entity_id=UUID(result["entity_id"]),
            entity_type=result["entity_type"],
            is_compliant=result["is_compliant"],
            passed_rules=result["passed_rules"],
            failed_rules=result["failed_rules"],
            evaluation_id=UUID(result["evaluation_id"]),
            evaluated_at=result["evaluated_at"],
        )

    except PolicyNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except ValueError as e:
        raise ValidationError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error evaluating policy: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to evaluate policy",
        )


# ---------------------------------------------------------------------------
# Assumption Governance Schemas
# ---------------------------------------------------------------------------


class AssumptionCreate(BaseModel):
    """Schema for creating an assumption."""

    name: str = Field(..., max_length=128)
    slug: str = Field(..., max_length=128)
    assumption_type: str = Field(..., description="market_growth, pricing, cost_structure, timeline, resource_availability, competitive_response, customer_behavior, technical_feasibility, regulatory, custom")
    description: str = Field(..., description="Detailed description of the assumption")
    value: dict[str, Any] = Field(..., description="Assumption value")
    value_type: str = Field(..., description="number, percentage, currency, string, boolean, date, duration")
    impact_level: str = Field(..., description="low, medium, high, critical")
    truth_object_id: UUID | None = None
    applies_to_opportunity_id: UUID | None = None
    applies_to_formula_id: UUID | None = None


class AssumptionResponse(BaseModel):
    """Schema for assumption response."""

    id: UUID
    tenant_id: UUID
    name: str
    slug: str
    assumption_type: str
    description: str
    value: dict[str, Any]
    value_type: str
    impact_level: str
    sensitivity_analysis: dict[str, Any] | None
    truth_object_id: UUID | None
    evidence_count: int
    status: str
    is_active: bool
    approval_request_id: UUID | None
    approved_by: str | None
    approved_at: datetime | None
    created_at: datetime
    updated_at: datetime


class AssumptionEvidenceCreate(BaseModel):
    """Schema for adding evidence to an assumption."""

    evidence_type: str = Field(..., description="truth_object, external_source")
    truth_object_id: UUID | None = None
    source_url: str | None = None
    source_title: str | None = None
    excerpt: str | None = None
    confidence: str = Field(default="medium", description="high, medium, low")
    relevance: str = Field(default="medium", description="high, medium, low")
    notes: str | None = None


# ---------------------------------------------------------------------------
# Assumption Governance Endpoints
# ---------------------------------------------------------------------------


@governance_router.post(
    "/assumptions",
    response_model=AssumptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Assumption",
    description="Create a new assumption with evidence linkage.",
)
async def create_assumption(
    request: Request,
    payload: AssumptionCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> AssumptionResponse:
    """Create a new Assumption."""
    authorize_action("layer5.governance.assumptions.create", caller)
    tenant_id = caller.tenant_id

    service = AssumptionApprovalService()

    try:
        # Use the assumption approval service to create the assumption
        # This will handle high-impact approval gating automatically
        assumption = await service.create_assumption(
            db=db,
            tenant_id=tenant_id,
            name=payload.name,
            slug=payload.slug,
            assumption_type=payload.assumption_type,
            description=payload.description,
            value=payload.value,
            value_type=payload.value_type,
            impact_level=payload.impact_level,
            truth_object_id=payload.truth_object_id,
            applies_to_opportunity_id=payload.applies_to_opportunity_id,
            applies_to_formula_id=payload.applies_to_formula_id,
            created_by=caller.user_id,
        )

        return AssumptionResponse(
            id=assumption.id,
            tenant_id=assumption.tenant_id,
            name=assumption.name,
            slug=assumption.slug,
            assumption_type=assumption.assumption_type,
            description=assumption.description,
            value=assumption.value,
            value_type=assumption.value_type,
            impact_level=assumption.impact_level,
            sensitivity_analysis=assumption.sensitivity_analysis,
            truth_object_id=assumption.truth_object_id,
            evidence_count=assumption.evidence_count,
            status=assumption.status,
            is_active=assumption.is_active,
            approval_request_id=assumption.approval_request_id,
            approved_by=assumption.approved_by,
            approved_at=assumption.approved_at,
            created_at=assumption.created_at,
            updated_at=assumption.updated_at,
        )

    except Exception as e:
        logger.error("Error creating assumption: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create assumption",
        )


@governance_router.get(
    "/assumptions",
    response_model=PaginatedResponse,
    summary="List Assumptions",
    description="List assumptions with pagination and filtering.",
)
async def list_assumptions(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    assumption_type: str | None = Query(None),
    impact_level: str | None = Query(None),
    status: str | None = Query(None),
) -> PaginatedResponse:
    """List assumptions scoped to tenant."""
    authorize_action("layer5.governance.assumptions.list", caller)
    tenant_id = caller.tenant_id

    service = AssumptionApprovalService()

    try:
        assumptions, total = await service.list_assumptions(
            db=db,
            tenant_id=tenant_id,
            assumption_type=assumption_type,
            impact_level=impact_level,
            status=status,
            page=page,
            page_size=page_size,
        )

        items = [
            AssumptionResponse(
                id=a.id,
                tenant_id=a.tenant_id,
                name=a.name,
                slug=a.slug,
                assumption_type=a.assumption_type,
                description=a.description,
                value=a.value,
                value_type=a.value_type,
                impact_level=a.impact_level,
                sensitivity_analysis=a.sensitivity_analysis,
                truth_object_id=a.truth_object_id,
                evidence_count=a.evidence_count,
                status=a.status,
                is_active=a.is_active,
                approval_request_id=a.approval_request_id,
                approved_by=a.approved_by,
                approved_at=a.approved_at,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in assumptions
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    except Exception as e:
        logger.error("Error listing assumptions: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list assumptions",
        )


@governance_router.post(
    "/assumptions/{assumption_id}/evidence",
    response_model=AssumptionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add evidence to an Assumption",
    description="Add supporting evidence to an assumption.",
)
async def add_assumption_evidence(
    assumption_id: UUID,
    payload: AssumptionEvidenceCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> AssumptionResponse:
    """Add evidence to an assumption."""
    authorize_action("layer5.governance.assumptions.add_evidence", caller)
    tenant_id = caller.tenant_id

    service = AssumptionApprovalService()

    try:
        assumption = await service.add_evidence(
            db=db,
            tenant_id=tenant_id,
            assumption_id=assumption_id,
            evidence_type=payload.evidence_type,
            truth_object_id=payload.truth_object_id,
            source_url=payload.source_url,
            source_title=payload.source_title,
            excerpt=payload.excerpt,
            confidence=payload.confidence,
            relevance=payload.relevance,
            notes=payload.notes,
            added_by=caller.user_id,
        )

        return AssumptionResponse(
            id=assumption.id,
            tenant_id=assumption.tenant_id,
            name=assumption.name,
            slug=assumption.slug,
            assumption_type=assumption.assumption_type,
            description=assumption.description,
            value=assumption.value,
            value_type=assumption.value_type,
            impact_level=assumption.impact_level,
            sensitivity_analysis=assumption.sensitivity_analysis,
            truth_object_id=assumption.truth_object_id,
            evidence_count=assumption.evidence_count,
            status=assumption.status,
            is_active=assumption.is_active,
            approval_request_id=assumption.approval_request_id,
            approved_by=assumption.approved_by,
            approved_at=assumption.approved_at,
            created_at=assumption.created_at,
            updated_at=assumption.updated_at,
        )

    except AssumptionNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error adding assumption evidence: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add assumption evidence",
        )


@governance_router.post(
    "/assumptions/{assumption_id}/submit",
    response_model=AssumptionResponse,
    summary="Submit Assumption for approval",
    description="Submit a high-impact assumption for approval.",
)
async def submit_assumption(
    assumption_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> AssumptionResponse:
    """Submit an assumption for approval."""
    authorize_action("layer5.governance.assumptions.submit", caller)
    tenant_id = caller.tenant_id

    service = AssumptionApprovalService()

    try:
        assumption = await service.submit_for_approval(
            db=db,
            tenant_id=tenant_id,
            assumption_id=assumption_id,
            submitter=caller.user_id,
        )

        return AssumptionResponse(
            id=assumption.id,
            tenant_id=assumption.tenant_id,
            name=assumption.name,
            slug=assumption.slug,
            assumption_type=assumption.assumption_type,
            description=assumption.description,
            value=assumption.value,
            value_type=assumption.value_type,
            impact_level=assumption.impact_level,
            sensitivity_analysis=assumption.sensitivity_analysis,
            truth_object_id=assumption.truth_object_id,
            evidence_count=assumption.evidence_count,
            status=assumption.status,
            is_active=assumption.is_active,
            approval_request_id=assumption.approval_request_id,
            approved_by=assumption.approved_by,
            approved_at=assumption.approved_at,
            created_at=assumption.created_at,
            updated_at=assumption.updated_at,
        )

    except AssumptionNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error submitting assumption: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to submit assumption",
        )


# ---------------------------------------------------------------------------
# Value Realization Ledger Schemas
# ---------------------------------------------------------------------------


class ValueRealizationEntryCreate(BaseModel):
    """Schema for creating a value realization entry."""

    entry_type: str = Field(..., description="roi, cost_savings, revenue_impact, efficiency_gain, time_savings, risk_reduction, custom")
    entry_name: str = Field(..., max_length=128)
    description: str | None = None
    current_value: float = Field(..., description="Current value of the metric")
    value_unit: str | None = None
    value_currency: str | None = Field(max_length=3, description="ISO currency code")
    formula_id: UUID | None = None
    formula_version: str | None = None
    benchmark_id: UUID | None = None
    benchmark_version: str | None = None
    assumption_ids: list[UUID] | None = None
    opportunity_id: UUID | None = None
    account_id: UUID | None = None
    business_case_id: UUID | None = None


class ValueRealizationEntryResponse(BaseModel):
    """Schema for value realization entry response."""

    id: UUID
    tenant_id: UUID
    entry_type: str
    entry_name: str
    description: str | None
    current_value: float
    value_unit: str | None
    value_currency: str | None
    formula_id: UUID | None
    formula_version: str | None
    benchmark_id: UUID | None
    benchmark_version: str | None
    assumption_ids: list[UUID] | None
    opportunity_id: UUID | None
    account_id: UUID | None
    business_case_id: UUID | None
    is_active: bool
    created_at: datetime
    updated_at: datetime


class ValueRealizationUpdateCreate(BaseModel):
    """Schema for creating a value realization update."""

    new_value: float = Field(..., description="New value after update")
    update_reason: str = Field(..., description="new_calculation, data_refresh, formula_change, benchmark_update, assumption_change, correction, revalidation, manual_override, other")
    update_notes: str | None = None
    formula_id_at_update: UUID | None = None
    formula_version_at_update: str | None = None
    benchmark_id_at_update: UUID | None = None
    benchmark_version_at_update: str | None = None
    assumption_ids_at_update: list[UUID] | None = None
    calculation_metadata: dict[str, Any] | None = None


# ---------------------------------------------------------------------------
# Value Realization Ledger Endpoints
# ---------------------------------------------------------------------------


@governance_router.post(
    "/value-entries",
    response_model=ValueRealizationEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a Value Realization Entry",
    description="Create a new value realization entry with audit trail.",
)
async def create_value_entry(
    request: Request,
    payload: ValueRealizationEntryCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ValueRealizationEntryResponse:
    """Create a new value realization entry."""
    authorize_action("layer5.governance.value_entries.create", caller)
    tenant_id = caller.tenant_id

    service = ValueRealizationService()

    try:
        entry = await service.create_value_entry(
            db=db,
            tenant_id=tenant_id,
            entry_type=payload.entry_type,
            entry_name=payload.entry_name,
            current_value=payload.current_value,
            description=payload.description,
            value_unit=payload.value_unit,
            value_currency=payload.value_currency,
            formula_id=payload.formula_id,
            formula_version=payload.formula_version,
            benchmark_id=payload.benchmark_id,
            benchmark_version=payload.benchmark_version,
            assumption_ids=payload.assumption_ids,
            opportunity_id=payload.opportunity_id,
            account_id=payload.account_id,
            business_case_id=payload.business_case_id,
            created_by=caller.user_id,
        )

        return ValueRealizationEntryResponse(
            id=entry.id,
            tenant_id=entry.tenant_id,
            entry_type=entry.entry_type,
            entry_name=entry.entry_name,
            description=entry.description,
            current_value=entry.current_value,
            value_unit=entry.value_unit,
            value_currency=entry.value_currency,
            formula_id=entry.formula_id,
            formula_version=entry.formula_version,
            benchmark_id=entry.benchmark_id,
            benchmark_version=entry.benchmark_version,
            assumption_ids=entry.assumption_ids,
            opportunity_id=entry.opportunity_id,
            account_id=entry.account_id,
            business_case_id=entry.business_case_id,
            is_active=entry.is_active,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    except Exception as e:
        logger.error("Error creating value entry: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create value entry",
        )


@governance_router.get(
    "/value-entries",
    response_model=PaginatedResponse,
    summary="List Value Realization Entries",
    description="List value realization entries with pagination and filtering.",
)
async def list_value_entries(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    entry_type: str | None = Query(None),
    opportunity_id: UUID | None = Query(None),
    account_id: UUID | None = Query(None),
) -> PaginatedResponse:
    """List value entries scoped to tenant."""
    authorize_action("layer5.governance.value_entries.list", caller)
    tenant_id = caller.tenant_id

    service = ValueRealizationService()

    try:
        entries, total = await service.list_value_entries(
            db=db,
            tenant_id=tenant_id,
            entry_type=entry_type,
            opportunity_id=opportunity_id,
            account_id=account_id,
            page=page,
            page_size=page_size,
        )

        items = [
            ValueRealizationEntryResponse(
                id=e.id,
                tenant_id=e.tenant_id,
                entry_type=e.entry_type,
                entry_name=e.entry_name,
                description=e.description,
                current_value=e.current_value,
                value_unit=e.value_unit,
                value_currency=e.value_currency,
                formula_id=e.formula_id,
                formula_version=e.formula_version,
                benchmark_id=e.benchmark_id,
                benchmark_version=e.benchmark_version,
                assumption_ids=e.assumption_ids,
                opportunity_id=e.opportunity_id,
                account_id=e.account_id,
                business_case_id=e.business_case_id,
                is_active=e.is_active,
                created_at=e.created_at,
                updated_at=e.updated_at,
            )
            for e in entries
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    except Exception as e:
        logger.error("Error listing value entries: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list value entries",
        )


@governance_router.post(
    "/value-entries/{entry_id}/updates",
    response_model=ValueRealizationEntryResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Value Realization Update",
    description="Add an update to a value realization entry with audit trail.",
)
async def add_value_update(
    entry_id: UUID,
    payload: ValueRealizationUpdateCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ValueRealizationEntryResponse:
    """Add an update to a value realization entry."""
    authorize_action("layer5.governance.value_entries.update", caller)
    tenant_id = caller.tenant_id

    service = ValueRealizationService()

    try:
        entry = await service.add_value_update(
            db=db,
            tenant_id=tenant_id,
            entry_id=entry_id,
            new_value=payload.new_value,
            update_reason=payload.update_reason,
            update_notes=payload.update_notes,
            formula_id_at_update=payload.formula_id_at_update,
            formula_version_at_update=payload.formula_version_at_update,
            benchmark_id_at_update=payload.benchmark_id_at_update,
            benchmark_version_at_update=payload.benchmark_version_at_update,
            assumption_ids_at_update=payload.assumption_ids_at_update,
            calculation_metadata=payload.calculation_metadata,
            updated_by=caller.user_id,
        )

        return ValueRealizationEntryResponse(
            id=entry.id,
            tenant_id=entry.tenant_id,
            entry_type=entry.entry_type,
            entry_name=entry.entry_name,
            description=entry.description,
            current_value=entry.current_value,
            value_unit=entry.value_unit,
            value_currency=entry.value_currency,
            formula_id=entry.formula_id,
            formula_version=entry.formula_version,
            benchmark_id=entry.benchmark_id,
            benchmark_version=entry.benchmark_version,
            assumption_ids=entry.assumption_ids,
            opportunity_id=entry.opportunity_id,
            account_id=entry.account_id,
            business_case_id=entry.business_case_id,
            is_active=entry.is_active,
            created_at=entry.created_at,
            updated_at=entry.updated_at,
        )

    except ValueEntryNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error adding value update: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to add value update",
        )


# ---------------------------------------------------------------------------
# Approval Workflow Schemas
# ---------------------------------------------------------------------------


class ApprovalRequestResponse(BaseModel):
    """Schema for approval request response."""

    id: UUID
    tenant_id: UUID
    entity_type: str
    entity_id: UUID
    entity_version: str | None
    status: str
    requested_by: str
    requested_at: datetime
    request_reason: str | None
    request_metadata: dict[str, Any] | None
    reviewed_by: str | None
    reviewed_at: datetime | None
    review_notes: str | None
    approved_at: datetime | None
    rejected_at: datetime | None
    created_at: datetime
    updated_at: datetime


# ---------------------------------------------------------------------------
# Approval Workflow Endpoints
# ---------------------------------------------------------------------------


@governance_router.get(
    "/approvals",
    response_model=PaginatedResponse,
    summary="List Approval Requests",
    description="List approval requests with pagination and filtering.",
)
async def list_approvals(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100),
    entity_type: str | None = Query(None),
    status: str | None = Query(None),
) -> PaginatedResponse:
    """List approval requests scoped to tenant."""
    authorize_action("layer5.governance.approvals.list", caller)
    tenant_id = caller.tenant_id

    sm = ApprovalStateMachine()

    try:
        approvals, total = await sm.list_requests(
            db=db,
            tenant_id=tenant_id,
            entity_type=entity_type,
            status=status,
            page=page,
            page_size=page_size,
        )

        items = [
            ApprovalRequestResponse(
                id=a.id,
                tenant_id=a.tenant_id,
                entity_type=a.entity_type,
                entity_id=a.entity_id,
                entity_version=a.entity_version,
                status=a.status,
                requested_by=a.requested_by,
                requested_at=a.requested_at,
                request_reason=a.request_reason,
                request_metadata=a.request_metadata,
                reviewed_by=a.reviewed_by,
                reviewed_at=a.reviewed_at,
                review_notes=a.review_notes,
                approved_at=a.approved_at,
                rejected_at=a.rejected_at,
                created_at=a.created_at,
                updated_at=a.updated_at,
            )
            for a in approvals
        ]

        return PaginatedResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            has_next=(page * page_size) < total,
        )

    except Exception as e:
        logger.error("Error listing approval requests: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to list approval requests",
        )


@governance_router.get(
    "/approvals/{approval_id}",
    response_model=ApprovalRequestResponse,
    summary="Get Approval Request",
    description="Get a single approval request by ID.",
)
async def get_approval_request(
    approval_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ApprovalRequestResponse:
    """Get an approval request by ID with tenant scoping."""
    authorize_action("layer5.governance.approvals.get", caller)
    tenant_id = caller.tenant_id

    sm = ApprovalStateMachine()

    try:
        approval = await sm.get_request(db, tenant_id, approval_id)

        return ApprovalRequestResponse(
            id=approval.id,
            tenant_id=approval.tenant_id,
            entity_type=approval.entity_type,
            entity_id=approval.entity_id,
            entity_version=approval.entity_version,
            status=approval.status,
            requested_by=approval.requested_by,
            requested_at=approval.requested_at,
            request_reason=approval.request_reason,
            request_metadata=approval.request_metadata,
            reviewed_by=approval.reviewed_by,
            reviewed_at=approval.reviewed_at,
            review_notes=approval.review_notes,
            approved_at=approval.approved_at,
            rejected_at=approval.rejected_at,
            created_at=approval.created_at,
            updated_at=approval.updated_at,
        )

    except ApprovalRequestNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error getting approval request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to get approval request",
        )


@governance_router.post(
    "/approvals/{approval_id}/approve",
    response_model=ApprovalRequestResponse,
    summary="Approve an Approval Request",
    description="Approve a pending approval request.",
)
async def approve_request(
    approval_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    notes: str | None = None,
) -> ApprovalRequestResponse:
    """Approve an approval request."""
    authorize_action("layer5.governance.approvals.approve", caller)
    tenant_id = caller.tenant_id

    sm = ApprovalStateMachine()

    try:
        approval = await sm.get_request(db, tenant_id, approval_id)
        approved = await sm.approve(db, approval, caller.user_id, notes)

        return ApprovalRequestResponse(
            id=approved.id,
            tenant_id=approved.tenant_id,
            entity_type=approved.entity_type,
            entity_id=approved.entity_id,
            entity_version=approved.entity_version,
            status=approved.status,
            requested_by=approved.requested_by,
            requested_at=approved.requested_at,
            request_reason=approved.request_reason,
            request_metadata=approved.request_metadata,
            reviewed_by=approved.reviewed_by,
            reviewed_at=approved.reviewed_at,
            review_notes=approved.review_notes,
            approved_at=approved.approved_at,
            rejected_at=approved.rejected_at,
            created_at=approved.created_at,
            updated_at=approved.updated_at,
        )

    except ApprovalRequestNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error approving request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to approve request",
        )


@governance_router.post(
    "/approvals/{approval_id}/reject",
    response_model=ApprovalRequestResponse,
    summary="Reject an Approval Request",
    description="Reject a pending approval request.",
)
async def reject_request(
    approval_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    notes: str | None = None,
) -> ApprovalRequestResponse:
    """Reject an approval request."""
    authorize_action("layer5.governance.approvals.reject", caller)
    tenant_id = caller.tenant_id

    sm = ApprovalStateMachine()

    try:
        approval = await sm.get_request(db, tenant_id, approval_id)
        rejected = await sm.reject(db, approval, caller.user_id, notes)

        return ApprovalRequestResponse(
            id=rejected.id,
            tenant_id=rejected.tenant_id,
            entity_type=rejected.entity_type,
            entity_id=rejected.entity_id,
            entity_version=rejected.entity_version,
            status=rejected.status,
            requested_by=rejected.requested_by,
            requested_at=rejected.requested_at,
            request_reason=rejected.request_reason,
            request_metadata=rejected.request_metadata,
            reviewed_by=rejected.reviewed_by,
            reviewed_at=rejected.reviewed_at,
            review_notes=rejected.review_notes,
            approved_at=rejected.approved_at,
            rejected_at=rejected.rejected_at,
            created_at=rejected.created_at,
            updated_at=rejected.updated_at,
        )

    except ApprovalRequestNotFoundError as e:
        raise NotFoundError(message = str(_safe_http_detail(e, status_code=500)))
    except Exception as e:
        logger.error("Error rejecting request: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to reject request",
        )
