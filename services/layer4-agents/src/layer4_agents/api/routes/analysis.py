from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import (
    NotFoundError,
    ServiceUnavailableError,
    ValidationError,
)

"""Analysis API routes for quick ROI and whitespace calculations."""


import logging
import os
from datetime import UTC, datetime
from typing import Any
from uuid import UUID, uuid4

from fastapi import (
    APIRouter,
    Body,
    Depends,
    Request,
)
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, emit_audit_event
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.policy_registry import authorize_action

from ...config.settings import get_settings

# Module-level settings reference. Tests monkeypatch `analysis.settings` to
# flip the environment flag; exposing the cached settings instance at module
# scope keeps that seam alive.
settings = get_settings()
from ...engine.executor import WorkflowExecutor
from ...models.agent_state import (
    ROIInputData,
    WhitespaceInputData,
)
from ...services.account_service import AccountService
from ...services.business_case_service import BusinessCaseService
from ...services.export_provenance import build_export_provenance_manifest
from ...services.export_storage import generate_download_url, upload_bytes
from ..common.audit import emit_and_persist_audit
from ..common.db import get_route_db
from ..common.errors import normalize_exception
from . import analysis_cases
from .analysis_schemas import (
    BusinessCaseRequest,
    BusinessCaseResponse,
    ROIAnalysisRequest,
    ROIAnalysisResponse,
    WhitespaceAnalysisRequest,
    WhitespaceAnalysisResponse,
)

get_db_from_context = get_route_db

router = APIRouter()
logger = logging.getLogger(__name__)

from ...test_support.seed_runtime_config import (  # noqa: F401
    SEED_PRIVILEGED_REASON,
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
        "backend_uuid": os.environ.get(
            "E2E_MERIDIAN_ACCOUNT_UUID", "00000000-0000-4000-e2e0-000000000101"
        ),
        "label": "Meridian Automotive",
    }
]


def _get_neo4j_driver(request: Request) -> Any:
    """Return the app-scoped Neo4j driver for routes that read graph context."""
    return request.app.state.neo4j_driver


# ROI Analysis Models
# (Models imported from analysis_schemas)


def get_executor() -> WorkflowExecutor:
    """Get workflow executor instance."""
    from ..startup import runtime_state

    if runtime_state.workflow_executor is None:
        raise ServiceUnavailableError(message="Workflow executor not initialized")
    return runtime_state.workflow_executor


def _is_smoke_mode(http_request: Request, *, body_mode: str | None = None) -> bool:
    """Return true only for explicit validation smoke-mode requests."""
    validation_mode = http_request.headers.get("X-Validation-Mode", "").strip().lower()
    smoke_header = http_request.headers.get("X-Fabric-Smoke-Test", "").strip().lower()
    body_mode_normalized = (body_mode or "").strip().lower()
    return (
        validation_mode == "smoke"
        or smoke_header in {"1", "true", "yes"}
        or body_mode_normalized == "smoke"
    )


def _validation_trace_id(http_request: Request) -> str:
    """Return a stable request trace identifier for validation responses."""
    return (
        http_request.headers.get("X-Validation-Run-ID")
        or http_request.headers.get("X-Request-ID")
        or str(uuid4())
    )


async def _smoke_roi_response(
    http_request: Request,
    prospect_id: str,
    account: Any,
    context: RequestContext,
) -> ROIAnalysisResponse:
    """Build deterministic smoke-mode ROI response without invoking the workflow executor."""
    trace_id = _validation_trace_id(http_request)
    audit_fn = globals().get("emit_audit_event", emit_audit_event)
    audit_res = audit_fn(
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
    if asyncio.iscoroutine(audit_res):
        await audit_res
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
    business_case_cls = globals().get("BusinessCaseService", BusinessCaseService)
    business_case_service = business_case_cls(db)
    res = business_case_service.upsert_case_record(
        case_id=case_id,
        workflow_id=case_id,
        account_id=request.account_id,
        opportunity_id=request.opportunity_id,
        status="draft",
        document_url=None,
        tenant_id=str(context.tenant_id),
    )
    if asyncio.iscoroutine(res):
        await res
    audit_fn = globals().get("emit_audit_event", emit_audit_event)
    audit_res = audit_fn(
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
    if asyncio.iscoroutine(audit_res):
        await audit_res
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


async def _require_tenant_account(
    db: AsyncSession, account_id: UUID, context: RequestContext
) -> Any:
    """Load an account through the authenticated tenant boundary or fail closed."""
    account = await AccountService(db).get_account(
        account_id, tenant_id=str(context.tenant_id)
    )
    if not account:
        raise NotFoundError(message=f"Account not found: {account_id}")
    return account


@router.post("/analysis/roi", response_model=ROIAnalysisResponse)
async def quick_roi_analysis(
    http_request: Request,
    request: ROIAnalysisRequest = Body(...),
    executor: WorkflowExecutor = Depends(get_executor),
    db: AsyncSession = Depends(get_route_db),
    context: RequestContext = Depends(require_authenticated),
) -> ROIAnalysisResponse:
    """Quick ROI analysis for a prospect."""
    try:
        prospect_id = request.prospect_id or request.account_id
        if not prospect_id:
            raise ValidationError(message="prospect_id or account_id is required")
        value_driver_ids = request.value_driver_ids or (
            [request.formula_id]
            if request.formula_id
            else list(request.variables.keys())
        )
        if not value_driver_ids:
            value_driver_ids = ["roi"]
        prospect_data = request.prospect_data or request.variables

        if _is_smoke_mode(http_request):
            if not request.account_id:
                raise ValidationError(
                    message="account_id is required for smoke-mode ROI validation"
                )
            try:
                account_uuid = UUID(request.account_id)
            except ValueError as exc:
                raise ValidationError(
                    message="account_id must be a UUID for smoke-mode ROI validation"
                ) from exc
            account = await _require_tenant_account(db, account_uuid, context)
            return await _smoke_roi_response(
                http_request, prospect_id, account, context
            )

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
            aggregated_roi=aggregate.get("aggregated")
            or {"calculation": "roi", "result": aggregate},
            detailed_results=aggregate.get("detailed_results") or [],
            benchmark_comparison=(result.output_data or {})
            .get("fetch_benchmarks", {})
            .get("benchmarks"),
        )

    except asyncio.CancelledError:
        raise
    except Exception as e:
        logger.exception("ROI analysis failed: %s", e)
        raise normalize_exception(
            e,
            status_code=500,
            message="ROI analysis failed",
            error_code="L4_ROI_ANALYSIS_FAILED",
            request_id=getattr(http_request.state, "request_id", None),
        )


@router.post("/analysis/whitespace", response_model=WhitespaceAnalysisResponse)
async def quick_whitespace_analysis(
    request: WhitespaceAnalysisRequest,
    executor: WorkflowExecutor = Depends(get_executor),
    context: RequestContext = Depends(require_authenticated),
) -> WhitespaceAnalysisResponse:
    """Quick whitespace analysis for a prospect."""
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
        raise normalize_exception(
            e,
            status_code=500,
            message="Whitespace analysis failed",
            error_code="L4_WHITESPACE_ANALYSIS_FAILED",
        )


# Import sub-routers
from .analysis_cases import (
    build_cases_router,
    require_approved_case as _require_approved_case,
)
from .analysis_scenarios import build_scenarios_router
from .analysis_validation import build_validation_seed_router
from .analysis_workspace import build_workspace_router

validation_router = build_validation_seed_router(
    get_executor=get_executor,
    require_tenant_account_fn=_require_tenant_account,
    get_settings_fn=lambda: settings,
)
cases_router = build_cases_router(
    get_executor=get_executor,
    require_tenant_account_fn=_require_tenant_account,
    is_smoke_mode_fn=_is_smoke_mode,
    smoke_business_case_response_fn=_smoke_business_case_response,
)
scenarios_router = build_scenarios_router()
workspace_router = build_workspace_router(
    get_executor=get_executor,
    get_neo4j_driver=_get_neo4j_driver,
)

router.include_router(validation_router)
router.include_router(cases_router)
router.include_router(scenarios_router)
router.include_router(workspace_router)
