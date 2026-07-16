from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import (
    AuthorizationError,
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
    ValueFabricException,
)

"""Analysis API routes for quick ROI and whitespace calculations."""


import json
import logging
import os
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Body,
    Depends,
    Request,
    Response,
    status,
)
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, emit_audit_event
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.jwt import encode_jwt
from value_fabric.shared.identity.policy_registry import authorize_action

from ...config.settings import get_settings
from ...engine.executor import WorkflowExecutor
from ...models.agent_state import (
    BusinessCaseAgentState,
    BusinessCaseInputData,
    ROIInputData,
    WhitespaceInputData,
    WorkflowStatus,
)
from ...models.business_case_record import BusinessCaseRecord
from ...models.saved_scenario import SavedBusinessCaseScenario
from ...services.account_service import AccountService
from ...services.business_case_service import BusinessCaseService
from ...services.export_provenance import build_export_provenance_manifest
from ...services.export_storage import generate_download_url, upload_bytes
from ...tenants.models.api_key import APIKey
from ...tenants.models.tenant import IsolationTier, Tenant, TenantStatus
from ...tenants.models.user import User
from ..common.audit import emit_and_persist_audit
from ..common.db import get_route_db
from ..common.errors import normalize_exception
from ..security.csrf import CSRF_COOKIE_NAME, SESSION_COOKIE_NAME, issue_csrf_token
from .analysis_schemas import (
    BusinessCaseLifecycleSeedRequest,
    BusinessCaseRequest,
    BusinessCaseResponse,
    CaseListItem,
    CaseListResponse,
    CreateCaseRequest,
    CreateCaseResponse,
    RegenerateBusinessCaseRequest,
    ROIAnalysisRequest,
    ROIAnalysisResponse,
    SavedScenarioDetail,
    SavedScenarioSummary,
    SaveScenarioRequest,
    ValidationAuthContextSeedRequest,
    ValidationSeededApiKey,
    ValidationSessionRequest,
    WhitespaceAnalysisRequest,
    WhitespaceAnalysisResponse,
    export_business_caseResult,
)
from .analysis_workspace import build_workspace_router

get_db_from_context = get_route_db

router = APIRouter()
logger = logging.getLogger(__name__)
settings = get_settings()

from ...test_support.seed_runtime_config import (
    SEED_AUTH_SOURCE,
    SEED_PRIVILEGED_REASON,
    SEED_SERVICE_ACCOUNT_ID,
    SEED_VALIDATION_USER_IDS,
)

VALIDATION_USERS = [
    {
        "id": SEED_VALIDATION_USER_IDS["admin"],
        "email": "validation-admin@valuefabric.test",
        "display_name": "Validation Admin",
        "role": "super_admin",
    },
    {
        "id": SEED_VALIDATION_USER_IDS["reviewer"],
        "email": "validation-reviewer@valuefabric.test",
        "display_name": "Validation Reviewer",
        "role": "analyst",
    },
    {
        "id": SEED_VALIDATION_USER_IDS["read_only"],
        "email": "validation-readonly@valuefabric.test",
        "display_name": "Validation Read Only",
        "role": "read_only",
    },
    {
        "id": SEED_VALIDATION_USER_IDS["sales"],
        "email": "validation-sales@valuefabric.test",
        "display_name": "Validation Sales",
        "role": "analyst",
    },
]
VALIDATION_ACCOUNT_MAPPINGS = [
    {
        "provider_record_id": "acct-meridian-001",
        "backend_uuid": os.environ.get("E2E_MERIDIAN_ACCOUNT_UUID", "00000000-0000-4000-e2e0-000000000101"),
        "label": "Meridian Automotive",
    }
]


def _get_neo4j_driver(request: Request) -> Any:
    """Return the app-scoped Neo4j driver for routes that read graph context."""
    return request.app.state.neo4j_driver


# ROI Analysis Models




# Whitespace Analysis Models




# Business Case Models













def _compute_case_diff(previous: dict[str, Any], current: dict[str, Any]) -> dict[str, Any]:
    prev_total = float(previous.get("total_estimated_value", 0.0) or 0.0)
    curr_total = float(current.get("total_estimated_value", 0.0) or 0.0)
    prev_narrative = str(previous.get("executive_summary", "") or "")
    curr_narrative = str(current.get("executive_summary", "") or "")
    return {
        "totals": {
            "previous_total_value": prev_total,
            "current_total_value": curr_total,
            "delta": curr_total - prev_total,
        },
        "narrative_sections_changed": {
            "executive_summary": prev_narrative != curr_narrative,
        },
    }


def get_executor() -> WorkflowExecutor:
    """Get workflow executor instance."""
    from ..startup import runtime_state

    if runtime_state.workflow_executor is None:
        raise ServiceUnavailableError(message = "Workflow executor not initialized")
    return runtime_state.workflow_executor


def _is_smoke_mode(http_request: Request, *, body_mode: str | None = None) -> bool:
    """Return true only for explicit validation smoke-mode requests."""
    validation_mode = http_request.headers.get("X-Validation-Mode", "").strip().lower()
    smoke_header = http_request.headers.get("X-Fabric-Smoke-Test", "").strip().lower()
    body_mode_normalized = (body_mode or "").strip().lower()
    return validation_mode == "smoke" or smoke_header in {"1", "true", "yes"} or body_mode_normalized == "smoke"


def _validation_trace_id(http_request: Request) -> str:
    """Return a stable request trace identifier for validation responses."""
    return http_request.headers.get("X-Validation-Run-ID") or http_request.headers.get("X-Request-ID") or str(uuid4())


async def _smoke_roi_response(
    http_request: Request,
    prospect_id: str,
    account: Any,
    context: RequestContext,
) -> ROIAnalysisResponse:
    """Build deterministic smoke-mode ROI response without invoking the workflow executor."""
    trace_id = _validation_trace_id(http_request)
    emit_audit_event(
        AuditAction.ROI_CALCULATED,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        api_key_id=context.api_key_id,
        resource_type="ROIAnalysis",
        resource_id=str(account.id),
        request_id=trace_id,
        details={
            "mode": "smoke",
            "status": "draft",
            "account_id": str(account.id),
            "requires_full_analysis": True,
        },
    )
    return ROIAnalysisResponse(
        prospect_id=prospect_id,
        aggregated_roi={
            "status": "draft",
            "mode": "smoke",
            "calculation": "roi",
            "result": {
                "total_value": 0,
                "roi": None,
                "payback_months": None,
            },
            "requires_full_analysis": True,
            "trace_id": trace_id,
            "tenant_id": str(context.tenant_id),
            "account_id": str(account.id),
        },
        detailed_results=[],
        benchmark_comparison={"mode": "smoke", "status": "not_evaluated"},
    )


async def _smoke_business_case_response(
    http_request: Request,
    request: BusinessCaseRequest,
    account: Any,
    db: AsyncSession,
    context: RequestContext,
) -> BusinessCaseResponse:
    """Build deterministic smoke-mode business case response without invoking the workflow executor."""
    trace_id = _validation_trace_id(http_request)
    case_id = f"smoke-case-{uuid4()}"
    business_case_service = BusinessCaseService(db)
    await business_case_service.upsert_case_record(
        case_id=case_id,
        workflow_id=case_id,
        account_id=request.account_id,
        opportunity_id=request.opportunity_id,
        status="draft",
        document_url=None,
        tenant_id=str(context.tenant_id),
    )
    emit_audit_event(
        AuditAction.BUSINESS_CASE_GENERATED,
        tenant_id=context.tenant_id,
        user_id=context.user_id,
        api_key_id=context.api_key_id,
        resource_type="BusinessCase",
        resource_id=case_id,
        request_id=trace_id,
        details={
            "mode": "smoke",
            "status": "draft",
            "account_id": str(account.id),
            "approval_required": True,
            "export_allowed": False,
            "requires_full_generation": True,
        },
    )
    return BusinessCaseResponse(
        case_id=case_id,
        title="Business Case Draft",
        summary="Draft smoke-mode business case; full generation is still required.",
        status="draft",
        created_at=datetime.now(UTC).isoformat(),
        remediation_items=[
            {
                "code": "FULL_GENERATION_REQUIRED",
                "message": "Run full business-case generation before approval or export.",
            }
        ],
        case_metadata={
            "mode": "smoke",
            "trace_id": trace_id,
            "tenant_id": str(context.tenant_id),
            "account_id": str(account.id),
            "approval_required": True,
            "export_allowed": False,
            "requires_full_generation": True,
        },
    )


async def _require_tenant_account(db: AsyncSession, account_id: UUID, context: RequestContext) -> Any:
    """Load an account through the authenticated tenant boundary or fail closed."""
    account = await AccountService(db).get_account(account_id, tenant_id=str(context.tenant_id))
    if not account:
        raise NotFoundError(message = str(f"Account not found: {account_id}"))
    return account


def _require_validation_seed_allowed(http_request: Request, context: RequestContext) -> None:
    """Fail closed unless this is an authenticated, non-production seed request."""
    if settings.environment == "production":
        raise AuthorizationError(message = "Validation seeding is disabled in production")
    if not context.tenant_id:
        raise AuthorizationError(message = "Validation seeding requires tenant context")
    reason = http_request.headers.get("X-Privileged-Reason", "").strip()
    if reason != SEED_PRIVILEGED_REASON:
        raise AuthorizationError(message = "Validation seeding requires privileged reason")


def _context_tenant_uuid(context: RequestContext) -> UUID:
    """Return the authenticated tenant UUID or fail closed."""
    authorize_action("layer4.analysis.roi", context)
    try:
        return UUID(str(context.tenant_id))
    except (TypeError, ValueError) as exc:
        raise ValidationError(message = "Validation seeding requires UUID tenant context") from exc


async def _upsert_validation_tenant(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    tenant_name: str,
    tenant_slug: str,
    actor: str | None,
) -> Tenant:
    tenant = await db.get(Tenant, tenant_id)
    now = datetime.now(UTC)
    settings_payload = {
        "isolation_tier": IsolationTier.SHARED.value,
        "seeded": True,
        "seed_source": SEED_AUTH_SOURCE,
        "backend_integrated_validation": True,
    }
    if tenant is None:
        tenant = Tenant(
            id=tenant_id,
            name=tenant_name,
            slug=tenant_slug,
            status=TenantStatus.ACTIVE.value,
            settings=settings_payload,
            status_changed_at=now,
            status_reason="backend-integrated validation seed",
            status_changed_by=actor or SEED_SERVICE_ACCOUNT_ID,
        )
        db.add(tenant)
    else:
        tenant.name = tenant_name
        tenant.slug = tenant_slug
        tenant.status = TenantStatus.ACTIVE.value
        tenant.settings = {**(tenant.settings or {}), **settings_payload}
        tenant.updated_at = now
    return tenant


async def _upsert_validation_users(db: AsyncSession, *, tenant_id: UUID) -> list[dict[str, str]]:
    seeded: list[dict[str, str]] = []
    now = datetime.now(UTC)
    for user_data in VALIDATION_USERS:
        user_id = user_data["id"]
        user = await db.get(User, user_id)
        if user is None:
            user = User(
                id=user_id,
                tenant_id=tenant_id,
                email=str(user_data["email"]),
                display_name=str(user_data["display_name"]),
                role=str(user_data["role"]),
                status="active",
            )
            db.add(user)
        else:
            if user.tenant_id != tenant_id:
                raise ConflictError(message=f"Seeded user tenant mismatch: {user_id}")
            user.email = str(user_data["email"])
            user.display_name = str(user_data["display_name"])
            user.role = str(user_data["role"])
            user.status = "active"
            user.updated_at = now
        seeded.append(
            {
                "id": str(user_id),
                "email": str(user_data["email"]),
                "role": str(user_data["role"]),
                "status": "active",
            }
        )
    return seeded


async def _upsert_validation_api_key(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    service_account_id: str,
    api_key_payload: ValidationSeededApiKey,
) -> dict[str, Any]:
    if not re.fullmatch(r"[a-f0-9]{64}", api_key_payload.key_hash):
        raise ValidationError(message="Seeded API key hash must be HMAC-SHA256 hex")

    metadata = {
        **api_key_payload.metadata,
        "seeded": True,
        "seed_source": SEED_AUTH_SOURCE,
        "service_account_id": service_account_id,
        "raw_secret_persisted": False,
    }
    key = await db.get(APIKey, api_key_payload.key_id)
    if key is None:
        key = APIKey(
            key_id=api_key_payload.key_id,
            tenant_id=tenant_id,
            user_id=None,
            name=api_key_payload.name,
            key_hash=api_key_payload.key_hash,
            prefix=api_key_payload.prefix,
            role=api_key_payload.role,
            permissions=api_key_payload.permissions or None,
            enabled=True,
            metadata_=metadata,
        )
        db.add(key)
    else:
        if key.tenant_id != tenant_id:
            raise ConflictError(message=f"Seeded API key tenant mismatch: {key.key_id}")
        key.name = api_key_payload.name
        key.key_hash = api_key_payload.key_hash
        key.prefix = api_key_payload.prefix
        key.role = api_key_payload.role
        key.permissions = api_key_payload.permissions or None
        key.enabled = True
        key.metadata_ = metadata

    return {
        "key_id": key.key_id,
        "prefix": key.prefix,
        "role": key.role,
        "permissions": key.permissions or [],
        "raw_secret_persisted": False,
    }


@router.post("/validation/seed/auth-context")
async def seed_validation_auth_context(
    payload: ValidationAuthContextSeedRequest,
    http_request: Request,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Seed deterministic auth context for backend-integrated validation.

    This endpoint is non-production only and persists no raw secrets. It is
    designed to make local/CI backend-integrated tests reproducible while
    keeping runtime secrets sourced exclusively from environment or a secret
    manager.
    """
    authorize_action("layer4.analysis.seed_auth_context", context)
    _require_validation_seed_allowed(http_request, context)
    tenant_id = _context_tenant_uuid(context)
    if payload.tenant_id is not None and payload.tenant_id != tenant_id:
        raise AuthorizationError(message = "Validation seed tenant mismatch")

    await _upsert_validation_tenant(
        db,
        tenant_id=tenant_id,
        tenant_name=payload.tenant_name,
        tenant_slug=payload.tenant_slug,
        actor=context.service_account_id or str(context.user_id or SEED_SERVICE_ACCOUNT_ID),
    )
    seeded_users = await _upsert_validation_users(db, tenant_id=tenant_id)
    seeded_api_key = None
    if payload.api_key is not None:
        seeded_api_key = await _upsert_validation_api_key(
            db,
            tenant_id=tenant_id,
            service_account_id=payload.service_account_id,
            api_key_payload=payload.api_key,
        )

    await db.flush()
    return {
        "seeded": True,
        "tenant": {
            "id": str(tenant_id),
            "slug": payload.tenant_slug,
            "name": payload.tenant_name,
            "status": TenantStatus.ACTIVE.value,
        },
        "users": seeded_users,
        "role_bindings": [
            {"user_id": user["id"], "role": user["role"], "tenant_id": str(tenant_id)}
            for user in seeded_users
        ],
        "service_account": {
            "id": payload.service_account_id,
            "tenant_id": str(tenant_id),
            "auth_source": "service_account",
            "metadata_seeded": True,
        },
        "api_key": seeded_api_key,
        "account_mappings": payload.account_mappings,
        "raw_secret_persisted": False,
    }


@router.post("/validation/session")
async def issue_validation_session(
    payload: ValidationSessionRequest,
    response: Response,
    http_request: Request,
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Issue a non-production browser session for backend-integrated Playwright validation.

    The endpoint is deliberately gated by the same service-authenticated,
    privileged, non-production boundary as deterministic seed data. It uses the
    canonical JWT and CSRF cookie mechanics, and returns only non-secret UI
    metadata.
    """
    authorize_action("layer4.analysis.create_validation_session", context)
    _require_validation_seed_allowed(http_request, context)

    token = encode_jwt(
        tenant_id=context.tenant_id,
        user_id=payload.user_id,
        roles=[payload.role],
        expires_in_seconds=payload.expires_in_seconds,
    )
    csrf_token = issue_csrf_token()
    secure_cookie = http_request.url.scheme == "https"

    response.set_cookie(
        key=SESSION_COOKIE_NAME,
        value=token,
        httponly=True,
        secure=secure_cookie,
        samesite="strict",
        max_age=payload.expires_in_seconds,
        path="/",
    )
    response.set_cookie(
        key=CSRF_COOKIE_NAME,
        value=csrf_token,
        httponly=False,
        secure=secure_cookie,
        samesite="strict",
        max_age=payload.expires_in_seconds,
        path="/",
    )

    return {
        "authenticated": True,
        "expires_in": payload.expires_in_seconds,
        "user": {
            "id": payload.user_id,
            "email": payload.email,
            "role": payload.role,
            "tenantId": str(context.tenant_id),
            "tenantSlug": payload.tenant_slug,
        },
        "tenant_id": str(context.tenant_id),
    }


def _seeded_business_case_output(
    *,
    case_id: str,
    account_id: UUID,
    tenant_id: str,
    lifecycle_status: str,
    document_url: str | None,
) -> dict[str, Any]:
    """Build canonical workflow output for deterministic business-case lifecycle evidence."""
    approved = lifecycle_status == "approved"
    title = (
        "Meridian Automation Business Case"
        if approved
        else "Draft Meridian Business Case"
    )
    approval_history = [
        {
            "event": "submitted",
            "actor": "e2e-admin-user",
            "timestamp": datetime.now(UTC).isoformat(),
            "outcome": "pending_approval",
        }
    ]
    if approved:
        approval_history.append(
            {
                "event": "approved",
                "actor": "e2e-reviewer-user",
                "timestamp": datetime.now(UTC).isoformat(),
                "outcome": "approved",
            }
        )

    recommendations = [
        "Approve phased automation rollout for Meridian Automotive with ROI governance checkpoints.",
        "Use traceable claims and linked evidence before executive export.",
        "Push approved ROI summary to CRM for sales follow-up.",
        "Convert approved business case into post-sale realization action plan and track outcomes.",
    ]

    return {
        "assemble_document": {
            "title": title,
            "executive_summary": (
                "Executive summary: Meridian Automotive can capture validated automation value "
                "through a governed rollout with evidence-backed claims, approval history, "
                "CRM follow-up, and post-sale realization tracking."
            ),
            "total_estimated_value": 1_850_000.0 if approved else 0.0,
            "implementation_cost_estimate": 420_000.0 if approved else 0.0,
            "roi_ratio": 4.4 if approved else 0.0,
            "payback_months": 9 if approved else 0,
            "confidence_score": 0.86 if approved else 0.42,
            "recommendations": recommendations if approved else recommendations[:2],
            "status": lifecycle_status,
            "document_url": document_url,
            "page_count": 12 if approved else 0,
            "file_size_bytes": 245_760 if approved else 0,
            "truth_references": [
                {
                    "truth_object_id": "truth-meridian-automation-001",
                    "claim": "Automation reduces quote-to-cash cycle time",
                    "source": "Meridian validation workspace evidence",
                    "confidence": 0.88,
                }
            ],
            "remediation_items": []
            if approved
            else [{"code": "APPROVAL_REQUIRED", "message": "Draft must be approved before export"}],
            "case_metadata": {
                "tenant_id": tenant_id,
                "account_id": str(account_id),
                "approval_history": approval_history,
                "export_allowed": approved,
                "crm_push_available": approved,
                "realization_conversion_available": approved,
                "seed_source": SEED_PRIVILEGED_REASON,
            },
        },
        "verify_truth_requirements": {
            "passed": approved,
            "truth_references": [
                {
                    "truth_object_id": "truth-meridian-automation-001",
                    "claim": "Automation reduces quote-to-cash cycle time",
                }
            ],
            "remediation_items": []
            if approved
            else [{"code": "APPROVAL_REQUIRED", "message": "Approval is required"}],
        },
        "generate_sdes": {
            "status": "seeded",
            "lineage": {
                "case_id": case_id,
                "account_id": str(account_id),
                "tenant_id": tenant_id,
            },
        },
        "synthesize_narrative": {
            "narrative": "Approved value case with renewal narrative and realization action plan."
        },
    }


@router.post("/analysis/roi", response_model=ROIAnalysisResponse)
async def quick_roi_analysis(
    http_request: Request,
    request: ROIAnalysisRequest = Body(...),
    executor: WorkflowExecutor = Depends(get_executor),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> ROIAnalysisResponse:
    """Quick ROI analysis for a prospect.

    Calculates ROI for specified value drivers using prospect data.

    Example:
        POST /v1/analysis/roi
        {
            "prospect_id": "prospect-001",
            "value_driver_ids": ["vd-001", "vd-002"],
            "industry_vertical": "manufacturing"
        }
    """
    try:
        prospect_id = request.prospect_id or request.account_id
        if not prospect_id:
            raise ValidationError(message="prospect_id or account_id is required")
        value_driver_ids = request.value_driver_ids or ([request.formula_id] if request.formula_id else list(request.variables.keys()))
        if not value_driver_ids:
            value_driver_ids = ["roi"]
        prospect_data = request.prospect_data or request.variables

        if _is_smoke_mode(http_request):
            if not request.account_id:
                raise ValidationError(message="account_id is required for smoke-mode ROI validation")
            try:
                account_uuid = UUID(request.account_id)
            except ValueError as exc:
                raise ValidationError(message="account_id must be a UUID for smoke-mode ROI validation") from exc
            account = await _require_tenant_account(db, account_uuid, context)
            return await _smoke_roi_response(http_request, prospect_id, account, context)

        input_data = ROIInputData(
            prospect_id=prospect_id,
            value_driver_ids=value_driver_ids,
            prospect_data=prospect_data,
            industry_vertical=request.industry_vertical,
            company_size=request.company_size,
        )

        result = await executor.run(
            workflow_type="roi_calculator",
            input_data=input_data.model_dump(),
            tenant_id=str(context.tenant_id),
            user_id=context.user_id,
        )

        raw_aggregate = (result.output_data or {}).get("aggregate") or {}
        aggregate = raw_aggregate if isinstance(raw_aggregate, dict) else {}

        return ROIAnalysisResponse(
            prospect_id=prospect_id,
            aggregated_roi=aggregate.get("aggregated") or {"calculation": "roi", "result": aggregate},
            detailed_results=aggregate.get("detailed_results") or [],
            benchmark_comparison=(result.output_data or {}).get("fetch_benchmarks", {}).get("benchmarks"),
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("ROI analysis failed: %s", e)
        raise normalize_exception(e, status_code=500, message="ROI analysis failed", error_code="L4_ROI_ANALYSIS_FAILED", request_id=getattr(http_request.state, "request_id", None))


@router.post("/analysis/whitespace", response_model=WhitespaceAnalysisResponse)
async def quick_whitespace_analysis(
    request: WhitespaceAnalysisRequest,
    executor: WorkflowExecutor = Depends(get_executor),
    context: RequestContext = Depends(require_authenticated),
) -> WhitespaceAnalysisResponse:
    """Quick whitespace analysis for a prospect.

    Identifies gaps between prospect needs and solution capabilities.

    Example:
        POST /v1/analysis/whitespace
        {
            "prospect_id": "prospect-001",
            "prospect_needs": "We need to automate invoice processing and get real-time visibility into cash flow"
        }
    """
    authorize_action("layer4.analysis.whitespace", context)
    try:
        input_data = WhitespaceInputData(
            prospect_id=request.prospect_id,
            prospect_needs=request.prospect_needs,
            analysis_depth=request.analysis_depth,
        )

        result = await executor.run(
            workflow_type="whitespace_analysis",
            input_data=input_data.model_dump(),
            tenant_id=str(context.tenant_id),
            user_id=context.user_id,
        )

        score_data = result.output_data.get("score_opportunity", {})

        return WhitespaceAnalysisResponse(
            prospect_id=request.prospect_id,
            extracted_needs=result.output_data.get("analyze_prospect", {}).get(
                "extracted_needs", []
            ),
            gap_analysis=result.output_data.get("identify_gaps", {}).get("gaps", []),
            opportunity_score=score_data.get("opportunity_score", 0),
            recommendations=score_data.get("recommendations", []),
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        raise normalize_exception(e, status_code=500, message="Whitespace analysis failed", error_code="L4_WHITESPACE_ANALYSIS_FAILED")


@router.post("/cases", response_model=BusinessCaseResponse)
async def generate_business_case(
    request: BusinessCaseRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> BusinessCaseResponse:
    """Generate a business case document.

    Creates a comprehensive business case with ROI analysis and narrative sections.

    Example:
        POST /v1/cases
        {
            "account_id": "550e8400-e29b-41d4-a716-446655440000",
            "sections": ["executive_summary", "roi_analysis"],
            "output_format": "pdf"
        }
    """
    authorize_action("layer4.analysis.generate_case", context)
    try:
        try:
            raw_body = await http_request.json()
        except asyncio.CancelledError:
            raise
        except Exception:
            raw_body = {}
        if _is_workspace_case_create_body(raw_body):
            workspace_case = await _create_workspace_case_record(
                CreateCaseRequest.model_validate(raw_body),
                db,
                context,
            )
            return BusinessCaseResponse(
                case_id=workspace_case.case_id,
                title=workspace_case.title or "Case Workspace",
                status=workspace_case.status,
                created_at=workspace_case.created_at,
                case_metadata={
                    "account_id": workspace_case.account_id,
                    "workspace_case": True,
                },
            )

        executor = get_executor()
        account_service = AccountService(db)
        account = await account_service.get_account(request.account_id, tenant_id=str(context.tenant_id))
        if not account:
            raise NotFoundError(message = str(f"Account not found: {request.account_id}"))

        custom_inputs = dict(request.custom_inputs)
        custom_inputs["provider_record_id"] = account.provider_record_id

        if _is_smoke_mode(http_request, body_mode=str(custom_inputs.get("mode", ""))):
            return await _smoke_business_case_response(http_request, request, account, db, context)

        input_data = BusinessCaseInputData(
            account_id=request.account_id,
            opportunity_id=request.opportunity_id,
            sections_requested=request.sections,
            output_format=request.output_format,
            custom_inputs=custom_inputs,
        )

        result = await executor.run(
            workflow_type="business_case",
            input_data=input_data.model_dump(),
            tenant_id=str(context.tenant_id),
            user_id=context.user_id,
        )

        assemble_data = result.output_data.get("assemble", {})
        truth_gate = result.output_data.get("verify_truth_requirements", {})
        sdes_bundle = result.output_data.get("generate_sdes", {})

        case_metadata = dict(assemble_data.get("case_metadata", {}))
        case_metadata["account_id"] = str(request.account_id)

        business_case_service = BusinessCaseService(db)
        await business_case_service.upsert_case_record(
            case_id=result.workflow_id,
            workflow_id=result.workflow_id,
            account_id=request.account_id,
            opportunity_id=request.opportunity_id,
            status=result.status.value,
            document_url=assemble_data.get("document_url"),
            tenant_id=str(context.tenant_id),
        )

        return BusinessCaseResponse(
            case_id=result.workflow_id,
            status=result.status.value,
            title=assemble_data.get("title", "Business Case"),
            summary=assemble_data.get("summary", ""),
            total_value=assemble_data.get("total_value", 0.0),
            implementation_cost=assemble_data.get("implementation_cost", 0.0),
            roi_ratio=assemble_data.get("roi_ratio", 0.0),
            payback_months=assemble_data.get("payback_months", 0),
            confidence_score=assemble_data.get("confidence_score", 0.0),
            recommendations=assemble_data.get("recommendations", []),
            created_at=assemble_data.get("created_at"),
            document_url=assemble_data.get("document_url"),
            page_count=assemble_data.get("page_count", 0),
            file_size_bytes=assemble_data.get("file_size_bytes", 0),
            truth_references=assemble_data.get("truth_references", truth_gate.get("truth_references", [])),
            remediation_items=assemble_data.get("remediation_items", truth_gate.get("remediation_items", [])),
            sdes=sdes_bundle,
            case_metadata=case_metadata,
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("Business case generation failed: %s", e)
        raise normalize_exception(e, status_code=500, message="Business case generation failed", error_code="L4_BUSINESS_CASE_GENERATION_FAILED", request_id=getattr(http_request.state, "request_id", None))


@router.post("/cases/{case_id}/regenerate", response_model=BusinessCaseResponse)
async def regenerate_business_case(
    case_id: str,
    request: RegenerateBusinessCaseRequest,
    background_tasks: BackgroundTasks,
    http_request: Request,
    executor: WorkflowExecutor = Depends(get_executor),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> BusinessCaseResponse:
    """Regenerate a business case with latest inputs and preserve revision lineage."""
    authorize_action("layer4.analysis.regenerate_case", context)
    if request.previous_case_id != case_id:
        raise ValidationError(message = "previous_case_id must match route case_id")
    previous_result = await executor.get_result(case_id)
    previous_assemble = (previous_result or {}).get("output", {}).get("assemble_document", {})
    response = await generate_business_case(request, background_tasks, http_request, executor, db, context)
    current_result = await executor.get_result(response.case_id)
    current_assemble = (current_result or {}).get("output", {}).get("assemble_document", {})
    diff_summary = _compute_case_diff(previous_assemble, current_assemble)
    source_version = str(request.custom_inputs.get("value_case_version", "latest"))
    source_hash = str(request.custom_inputs.get("value_case_hash", "unknown"))
    response.case_metadata.update({
        "source_value_case_version": source_version,
        "source_value_case_hash": source_hash,
        "regenerated_from_case_id": case_id,
    })
    response.revision_history = [
        {"case_id": case_id, "created_at": (previous_result or {}).get("created_at")},
        {"case_id": response.case_id, "created_at": current_result.get("created_at") if current_result else None},
    ]
    response.diff_summary = diff_summary
    return response


@router.get("/cases/{case_id}", response_model=BusinessCaseResponse)
async def get_business_case(
    case_id: str,
    executor: WorkflowExecutor = Depends(get_executor),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> BusinessCaseResponse:
    """Get a generated business case by ID."""
    authorize_action("layer4.analysis.read_case", context)
    result = await executor.get_result(case_id)

    if not result:
        raise NotFoundError(message = str(f"Business case {case_id} not found"))

    record = await db.get(BusinessCaseRecord, case_id)
    if record and record.account_id:
        await _require_tenant_account(db, record.account_id, context)
    else:
        result_tenant = result.get("metadata", {}).get("tenant_id")
        if result_tenant and str(result_tenant) != str(context.tenant_id):
            raise AuthorizationError(message = str(f"Business case {case_id} does not belong to the current tenant"))

    output = result.get("output", {})
    assemble_data = output.get("assemble_document", {})
    truth_gate = output.get("verify_truth_requirements", {})
    sdes_bundle = output.get("generate_sdes", {})
    narrative_data = output.get("synthesize_narrative", {})
    case_metadata = dict(assemble_data.get("case_metadata", {}))
    if record and record.account_id:
        case_metadata["account_id"] = str(record.account_id)

    return BusinessCaseResponse(
        case_id=case_id,
        title=assemble_data.get("title", "Business Case"),
        summary=assemble_data.get("executive_summary", narrative_data.get("narrative", "")),
        total_value=assemble_data.get("total_estimated_value", 0.0),
        implementation_cost=assemble_data.get("implementation_cost_estimate", 0.0),
        roi_ratio=assemble_data.get("roi_ratio", 0.0),
        payback_months=assemble_data.get("payback_months", 0),
        confidence_score=assemble_data.get("confidence_score", 0.0),
        recommendations=assemble_data.get("recommendations", []),
        created_at=result.get("created_at"),
        status=assemble_data.get("status", record.status if record else result.get("status", "unknown")),
        document_url=assemble_data.get("document_url", record.document_url if record else None),
        page_count=assemble_data.get("page_count", 0),
        file_size_bytes=assemble_data.get("file_size_bytes", 0),
        truth_references=assemble_data.get("truth_references", truth_gate.get("truth_references", [])),
        remediation_items=assemble_data.get("remediation_items", truth_gate.get("remediation_items", [])),
        sdes=sdes_bundle,
        case_metadata=case_metadata,
    )


@router.post("/validation/seed/business-case-lifecycle")
async def seed_business_case_lifecycle(
    payload: BusinessCaseLifecycleSeedRequest,
    http_request: Request,
    executor: WorkflowExecutor = Depends(get_executor),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Seed deterministic business-case lifecycle state for non-production E2E validation."""
    authorize_action("layer4.analysis.seed_case_lifecycle", context)
    _require_validation_seed_allowed(http_request, context)
    await _require_tenant_account(db, payload.account_id, context)

    tenant_id = str(context.tenant_id)
    now = datetime.now(UTC)
    cases = [
        {
            "case_id": payload.draft_case_id,
            "status": "draft",
            "document_url": None,
        },
        {
            "case_id": payload.approved_case_id,
            "status": "approved",
            "document_url": "/exports/meridian-business-case.pdf",
        },
    ]
    for alias_case_id in payload.approved_case_aliases:
        if alias_case_id and alias_case_id not in {str(case["case_id"]) for case in cases}:
            cases.append(
                {
                    "case_id": alias_case_id,
                    "status": "approved",
                    "document_url": "/exports/meridian-business-case.pdf",
                }
            )

    business_case_service = BusinessCaseService(db)
    seeded_cases: list[dict[str, Any]] = []
    audit_events_requested = 0

    for case in cases:
        case_id = str(case["case_id"])
        lifecycle_status = str(case["status"])
        document_url = case["document_url"]
        output_data = _seeded_business_case_output(
            case_id=case_id,
            account_id=payload.account_id,
            tenant_id=tenant_id,
            lifecycle_status=lifecycle_status,
            document_url=document_url,
        )
        metadata = {
            "workflow_id": case_id,
            "workflow_type": "business_case",
            "tenant_id": tenant_id,
            "user_id": context.user_id,
            "account_id": str(payload.account_id),
            "seeded": True,
            "seed_source": SEED_PRIVILEGED_REASON,
            "lifecycle_status": lifecycle_status,
        }

        await business_case_service.upsert_case_record(
            case_id=case_id,
            workflow_id=case_id,
            account_id=payload.account_id,
            opportunity_id=None,
            status=lifecycle_status,
            document_url=document_url,
            tenant_id=tenant_id,
        )

        state = BusinessCaseAgentState(
            workflow_id=case_id,
            tenant_id=tenant_id,
            status=WorkflowStatus.COMPLETED,
            current_node="seeded_validation_lifecycle",
            input_data={"account_id": str(payload.account_id)},
            output_data=output_data,
            metadata=metadata,
            started_at=now,
            completed_at=now,
            document_url=document_url,
        )
        await executor.state_manager.save_state(case_id, state)
        if hasattr(executor, "_workflow_metadata"):
            executor._workflow_metadata[case_id] = metadata

        audit_actions = [AuditAction.BUSINESS_CASE_GENERATED, AuditAction.WORKFLOW_COMPLETED]
        if lifecycle_status == "approved":
            audit_actions.append(AuditAction.BUSINESS_CASE_APPROVED)

        for audit_action in audit_actions:
            try:
                await emit_and_persist_audit(
                    action=audit_action,
                    context=context,
                    resource_type="BusinessCase",
                    resource_id=case_id,
                    details={
                        "case_id": case_id,
                        "account_id": str(payload.account_id),
                        "lifecycle_status": lifecycle_status,
                        "seed_source": SEED_PRIVILEGED_REASON,
                    },
                )
                audit_events_requested += 1
            except asyncio.CancelledError:
                raise
            except Exception:
                # Audit persistence must be visible in logs but must not create
                # a fail-open auth path or leave partial lifecycle state hidden.
                logger.exception("Seed lifecycle audit emission failed for case %s", case_id)

        seeded_cases.append(
            {
                "case_id": case_id,
                "workflow_id": case_id,
                "status": lifecycle_status,
                "document_url": document_url,
                "account_id": str(payload.account_id),
            }
        )

    return {
        "seeded": True,
        "tenant_id": tenant_id,
        "cases": seeded_cases,
        "audit_events_requested": audit_events_requested,
        "required_seed_rows_blocked": [],
    }

async def _require_approved_case(
    record: Any,
    context: RequestContext,
    account: Any,
    format: str = "pdf",
) -> None:
    """Raise if the business case is not in an export-allowed status."""
    if str(record.status).lower() not in {"approved", "exported", "delivered"}:
        await emit_and_persist_audit(
            action=AuditAction.EXPORT_REQUESTED,
            context=context,
            resource_type="BusinessCaseExport",
            resource_id=str(record.case_id),
            details={
                "case_id": str(record.case_id),
                "format": format,
                "outcome": "denied",
                "denied_reason": "approval_required",
                "tenant_id": str(context.tenant_id),
                "account_id": str(account.id),
                "case_status": str(record.status),
            },
        )
        raise ConflictError(message="Business case must be approved before export")


@router.get("/cases/{case_id}/export")
async def export_business_case(
    case_id: str,
    format: str = "pdf",
    executor: WorkflowExecutor = Depends(get_executor),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> dict[str, Any]:
    """Export a generated business case.

    This version resolves the merge conflict by preserving both:
    1. Truth-gating / blocking behavior
    2. Provenance manifest generation, storage upload, and audit events
    """
    authorize_action("layer4.analysis.export_case", context)
    record = await db.get(BusinessCaseRecord, case_id)
    if not record or str(getattr(record, "tenant_id", None)) != str(context.tenant_id):
        raise NotFoundError(message = str(f"Business case {case_id} not found"))

    try:
        account = await _require_tenant_account(db, record.account_id, context)
    except ValueFabricException as exc:
        await emit_and_persist_audit(
            action=AuditAction.EXPORT_REQUESTED,
            context=context,
            resource_type="BusinessCaseExport",
            resource_id=case_id,
            details={
                "case_id": case_id,
                "format": format,
                "outcome": "denied",
                "denied_reason": "tenant_access_denied",
                "tenant_id": str(context.tenant_id),
                "record_account_id": str(record.account_id),
            },
        )
        raise exc

    await _require_approved_case(record, context, account, format)

    result = await executor.get_result(case_id)
    if not result:
        raise ConflictError(message="Business case draft is not approved or document bytes unavailable")

    output = result.get("output", {})
    assemble_data = output.get("assemble_document", {})
    truth_gate = output.get("verify_truth_requirements", {})

    blocked = bool(assemble_data.get("blocked")) or not truth_gate.get("passed", True)
    truth_references = assemble_data.get(
        "truth_references", truth_gate.get("truth_references", [])
    )
    remediation_items = assemble_data.get(
        "remediation_items", truth_gate.get("remediation_items", [])
    )

    document_bytes = assemble_data.get("document_bytes")
    export_id = str(uuid4())

    if blocked:
        await emit_and_persist_audit(
            action=AuditAction.EXPORT_REQUESTED,
            context=context,
            resource_type="BusinessCaseExport",
            resource_id=case_id,
            details={
                "case_id": case_id,
                "format": format,
                "outcome": "denied",
                "denied_reason": "truth_gate_blocked",
                "tenant_id": str(context.tenant_id),
                "account_id": str(account.id),
                "blocked": True,
                "truth_gate_passed": truth_gate.get("passed", False),
            },
        )
        return export_business_caseResult.model_validate({
            "case_id": case_id,
            "export_id": export_id,
            "format": format,
            "document_url": assemble_data.get("document_url"),
            "download_ready": False,
            "blocked": True,
            "remediation_items": remediation_items,
            "truth_references": truth_references,
            "manifest": {
                "case_id": case_id,
                "format": format,
                "blocked": True,
                "truth_references": truth_references,
                "remediation_items": remediation_items,
                "truth_gate": {
                    "passed": truth_gate.get("passed", False),
                    "requirements": truth_gate.get("requirements", []),
                },
            },
        }).model_dump()


    if not document_bytes:
        raise ConflictError(message="Business case document bytes unavailable")

    if not isinstance(document_bytes, bytes):
        document_bytes = bytes(document_bytes)

    if not get_settings().export_storage_endpoint:
        raise ServiceUnavailableError(message = "Export storage endpoint is not configured")

    workflow_id = (
        result.get("workflow_id")
        or result.get("metadata", {}).get("workflow_id")
        or case_id
    )
    filename = f"business_case_{case_id}.{format}"
    manifest_filename = f"business_case_{case_id}.provenance.json"

    manifest = build_export_provenance_manifest(
        case_id=case_id,
        workflow_result=result,
        actor_context=context,
        export_id=export_id,
    )
    manifest_bytes = json.dumps(manifest, indent=2).encode("utf-8")

    base_prefix = f"{case_id}/{export_id}"
    object_key = f"{base_prefix}/{filename}"
    manifest_key = f"{base_prefix}/{manifest_filename}"
    metadata = {
        "case-id": case_id,
        "workflow-id": workflow_id,
        "export-id": export_id,
        "tenant-id": str(context.tenant_id),
        "tenant_id": str(context.tenant_id),
        "actor-user-id": str(context.user_id or ""),
        "actor-subject": str(getattr(context, "subject", "") or ""),
        "account-id": str(account.id),
    }

    content_type = "application/pdf" if format == "pdf" else "application/octet-stream"

    await upload_bytes(
        tenant_id=str(context.tenant_id),
        object_key=object_key,
        content=document_bytes,
        content_type=content_type,
        metadata=metadata,
    )
    await upload_bytes(
        tenant_id=str(context.tenant_id),
        object_key=manifest_key,
        content=manifest_bytes,
        content_type="application/json",
        metadata=metadata,
    )

    document_url = await generate_download_url(tenant_id=str(context.tenant_id), object_key=object_key)
    manifest_url = await generate_download_url(tenant_id=str(context.tenant_id), object_key=manifest_key)
    expires_at = datetime.fromtimestamp(
        datetime.now(UTC).timestamp() + get_settings().export_signed_url_ttl_seconds,
        tz=UTC,
    ).isoformat()

    await emit_and_persist_audit(
        action=AuditAction.EXPORT_REQUESTED,
        context=context,
        resource_type="BusinessCaseExport",
        resource_id=case_id,
        details={
            "case_id": case_id,
            "workflow_id": workflow_id,
            "export_id": export_id,
            "format": format,
            "account_id": str(account.id),
        },
    )

    await emit_and_persist_audit(
        action=AuditAction.EXPORT_PACKAGE_GENERATED,
        context=context,
        resource_type="BusinessCaseExport",
        resource_id=case_id,
        details={
            "case_id": case_id,
            "workflow_id": workflow_id,
            "export_id": export_id,
            "pdf_object_key": object_key,
            "manifest_object_key": manifest_key,
            "account_id": str(account.id),
            "truth_object_ids": manifest.get("truth_object_ids", []),
            "source_references": manifest.get("source_references", []),
        },
    )

    await emit_and_persist_audit(
        action=AuditAction.EXPORT_DOWNLOAD_ACCESSED,
        context=context,
        resource_type="BusinessCaseExport",
        resource_id=case_id,
        details={
            "case_id": case_id,
            "workflow_id": workflow_id,
            "export_id": export_id,
            "pdf_object_key": object_key,
            "account_id": str(account.id),
        },
    )

    return export_business_caseResult.model_validate({
        "case_id": case_id,
        "export_id": export_id,
        "format": format,
        "document_url": document_url,
        "manifest_url": manifest_url,
        "download_ready": True,
        "blocked": False,
        "manifest": manifest,
        "remediation_items": remediation_items,
        "truth_references": truth_references,
        "url_expires_at": expires_at,
    }).model_dump()


# ═══════════════════════════════════════════════════════════════════════════════
# WORKSPACE ENDPOINTS — Intelligence tab data for account cases
# ═══════════════════════════════════════════════════════════════════════════════









def _parse_case_account_uuid(account_id: str) -> UUID:
    """Parse account identifiers used by case workspace routes."""
    try:
        return UUID(account_id)
    except ValueError as exc:
        raise ValidationError(message="account_id must be a UUID") from exc


def _isoformat_or_none(value: datetime | str | None) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.isoformat()
    return str(value)


def _is_workspace_case_create_body(body: object) -> bool:
    """Disambiguate the legacy workspace create payload from business-case generation."""
    if not isinstance(body, dict):
        return False
    generation_keys = {"sections", "output_format", "custom_inputs", "opportunity_id"}
    return "account_id" in body and "title" in body and not generation_keys.intersection(body)


async def _create_workspace_case_record(
    request: CreateCaseRequest,
    db: AsyncSession,
    context: RequestContext,
) -> CreateCaseResponse:
    account_uuid = _parse_case_account_uuid(request.account_id)
    tenant_id = str(context.tenant_id)
    account = await AccountService(db).get_account(account_uuid, tenant_id=tenant_id)
    if account is None:
        raise NotFoundError(message = str(f"Account not found: {request.account_id}"))

    case_id = request.case_id or str(uuid4())
    now = datetime.now(UTC).isoformat()
    record = BusinessCaseRecord(
        case_id=case_id,
        account_id=account_uuid,
        workflow_id=case_id,
        status="created",
        tenant_id=tenant_id,
    )
    db.add(record)

    return CreateCaseResponse(
        case_id=case_id,
        account_id=request.account_id,
        title=request.title,
        status="created",
        created_at=now,
    )












@router.get("/cases", response_model=CaseListResponse)
async def list_cases(
    account_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> CaseListResponse:
    """List cases for an account.

    Returns all cases associated with the specified account.
    """
    authorize_action("layer4.analysis.list_cases", context)
    account_uuid = _parse_case_account_uuid(account_id)
    tenant_id = str(context.tenant_id)

    account = await AccountService(db).get_account(account_uuid, tenant_id=tenant_id)
    if account is None:
        return CaseListResponse(items=[], total=0)

    result = await db.execute(
        select(BusinessCaseRecord).where(
            BusinessCaseRecord.account_id == account_uuid,
            BusinessCaseRecord.tenant_id == tenant_id,
        )
    )
    records = result.scalars().all()

    items = [
        CaseListItem(
            case_id=str(r.case_id),
            account_id=str(r.account_id) if r.account_id else None,
            title=getattr(r, 'title', None),
            status=r.status,
            created_at=_isoformat_or_none(getattr(r, 'created_at', None)),
            updated_at=_isoformat_or_none(getattr(r, 'updated_at', None)),
        )
        for r in records
    ]

    return CaseListResponse(items=items, total=len(items))


@router.post("/cases", response_model=CreateCaseResponse)
async def create_case(
    request: CreateCaseRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> CreateCaseResponse:
    """Create a new case for an account.

    Creates a case workspace for the specified account.
    """
    authorize_action("layer4.analysis.write_case", context)
    return await _create_workspace_case_record(request, db, context)


@router.get("/cases/{case_id}/scenarios", response_model=list[SavedScenarioSummary])
async def list_saved_scenarios(
    case_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> list[SavedScenarioSummary]:
    """List saved scenario metadata for a business case."""
    authorize_action("layer4.analysis.read_case", context)
    tenant_id = str(context.tenant_id)
    result = await db.execute(
        select(SavedBusinessCaseScenario)
        .where(
            SavedBusinessCaseScenario.case_id == case_id,
            SavedBusinessCaseScenario.tenant_id == tenant_id,
        )
        .order_by(SavedBusinessCaseScenario.created_at.desc())
    )
    records = result.scalars().all()
    return [
        SavedScenarioSummary(
            id=record.scenario_id,
            name=record.name,
            created_at=record.created_at.isoformat(),
        )
        for record in records
    ]


@router.post(
    "/cases/{case_id}/scenarios",
    response_model=SavedScenarioDetail,
    status_code=status.HTTP_201_CREATED,
)
async def save_scenario(
    case_id: str,
    request: SaveScenarioRequest,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> SavedScenarioDetail:
    """Persist a business-case what-if scenario server-side."""
    authorize_action("layer4.analysis.write_case", context)
    now = datetime.now(UTC)
    record = SavedBusinessCaseScenario(
        scenario_id=f"scenario_{uuid4().hex}",
        case_id=case_id,
        tenant_id=str(context.tenant_id),
        name=request.name,
        adjustments=request.adjustments,
        created_at=now,
    )
    db.add(record)
    return SavedScenarioDetail(
        id=record.scenario_id,
        name=record.name,
        adjustments=record.adjustments,
        created_at=now.isoformat(),
    )


@router.get("/cases/{case_id}/scenarios/{scenario_id}", response_model=SavedScenarioDetail)
async def get_saved_scenario(
    case_id: str,
    scenario_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> SavedScenarioDetail:
    """Fetch a saved scenario with sensitive adjustments from server storage."""
    authorize_action("layer4.analysis.read_case", context)
    result = await db.execute(
        select(SavedBusinessCaseScenario).where(
            SavedBusinessCaseScenario.case_id == case_id,
            SavedBusinessCaseScenario.scenario_id == scenario_id,
            SavedBusinessCaseScenario.tenant_id == str(context.tenant_id),
        )
    )
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundError(message = "Saved scenario not found")
    return SavedScenarioDetail(
        id=record.scenario_id,
        name=record.name,
        adjustments=record.adjustments,
        created_at=record.created_at.isoformat(),
    )


@router.delete("/cases/{case_id}/scenarios/{scenario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_saved_scenario(
    case_id: str,
    scenario_id: str,
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> None:
    """Delete a saved scenario only within the authenticated tenant scope."""
    authorize_action("layer4.analysis.write_case", context)
    result = await db.execute(
        delete(SavedBusinessCaseScenario).where(
            SavedBusinessCaseScenario.case_id == case_id,
            SavedBusinessCaseScenario.scenario_id == scenario_id,
            SavedBusinessCaseScenario.tenant_id == str(context.tenant_id),
        )
    )
    if result.rowcount == 0:
        raise NotFoundError(message = "Saved scenario not found")


router.include_router(
    build_workspace_router(
        get_executor=get_executor,
        get_neo4j_driver=_get_neo4j_driver,
    )
)
