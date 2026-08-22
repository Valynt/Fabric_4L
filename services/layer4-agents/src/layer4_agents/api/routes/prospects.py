from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import (
    AuthenticationError,
    ServiceUnavailableError,
    ValueFabricException,
)

"""Prospect API routes — Composite context and analysis workflow initiation.

Provides endpoints for:
- Cross-layer context aggregation (Layer1/2/3/5 + CRM)
- Prospect analysis workflow initiation with real backend integration
- Explicit degraded/pending state handling (no fabricated data)
"""


import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.security.dil_auth import get_verified_tenant_id

from ...config.settings import get_settings
from ...database import get_db_from_context
from ...interfaces.prospect_context import ProspectContextPort
from ...models.account import Account
from ...startup.agent_composition import create_prospect_context_client
from .prospects_helpers import (
    create_or_update_prospect_account,
    infer_buyer_role_from_title,
    resolve_enrichment_and_crm_status,
    trigger_prospect_workflow,
)

router = APIRouter(prefix="/prospects", tags=["prospects"])


def get_prospect_context_client() -> ProspectContextPort:
    """Return the prospect context adapter for route operations."""

    settings = get_settings()
    return create_prospect_context_client(
        layer1_url=str(settings.layer1_api_url),
        layer2_url=str(settings.layer2_api_url),
        layer3_url=str(settings.layer3_api_url),
        layer5_url=str(settings.layer5_api_url),
    )


# =============================================================================
# Enumerations
# =============================================================================


class EnrichmentStatus(str, Enum):
    """Status of enrichment data availability."""

    QUEUED = "queued"
    COMPLETE = "complete"
    UNAVAILABLE = "unavailable"
    PENDING = "pending"
    DEGRADED = "degraded"


class BuyerRoleInferenceStatus(str, Enum):
    """Status of buyer role inference."""

    COMPLETE = "complete"
    PENDING = "pending"
    UNAVAILABLE = "unavailable"


class CrmMatchStatus(str, Enum):
    """Status of CRM opportunity matching."""

    MATCHED = "matched"
    NOT_FOUND = "not_found"
    UNAVAILABLE = "unavailable"


class WorkflowStartStatus(str, Enum):
    """Status of workflow start operation."""

    STARTED = "started"
    PENDING = "pending"
    DEGRADED = "degraded"
    FAILED = "failed"


# =============================================================================
# Request/Response Models
# =============================================================================


class ProspectSetupData(BaseModel):
    """Prospect setup data from frontend form.

    Mirrors the fields collected in ProspectSetup.tsx.
    """

    company_name: str = Field(..., description="Company name", min_length=1, max_length=255)
    contact_name: str = Field(..., description="Primary contact name", min_length=1, max_length=255)
    contact_title: str | None = Field(None, description="Contact job title", max_length=255)
    primary_objective: str | None = Field(
        None,
        description="Primary business objective",
        examples=["reduce_costs", "increase_revenue", "improve_efficiency", "mitigate_risk"],
    )
    buyer_role_confirmed: bool = Field(default=False, description="Whether buyer role is confirmed")
    company_confirmed: bool = Field(default=False, description="Whether company profile is confirmed")
    crm_reviewed: bool = Field(default=False, description="Whether CRM match is reviewed")


class StartAnalysisRequest(BaseModel):
    """Request to start prospect analysis workflow.

    Creates or updates prospect record and triggers intelligence workflow.
    """

    prospect_id: str | None = Field(None, description="Existing prospect ID (if updating)")
    setup_data: ProspectSetupData = Field(..., description="Prospect setup form data")
    workflow_type: str = Field(
        default="prospect_analysis",
        description="Type of workflow to trigger",
        examples=["prospect_analysis", "whitespace_analysis", "business_case"],
    )
    priority: str = Field(default="NORMAL", description="Workflow priority")


class BuyerRoleInferenceResult(BaseModel):
    """Result of buyer role inference (never fabricated)."""

    status: BuyerRoleInferenceStatus
    role: str | None = None
    confidence: float | None = None
    source: str | None = None


class CrmMatchResult(BaseModel):
    """Result of CRM opportunity matching (never fabricated)."""

    status: CrmMatchStatus
    opportunity_id: str | None = None
    confidence: float | None = None
    source: str | None = None


class StartAnalysisResponse(BaseModel):
    """Response from starting prospect analysis.

    Never returns hardcoded demo data. All enrichment/matching data
    explicitly reports its availability status.
    """

    prospect_id: str = Field(..., description="Canonical prospect/account ID")
    workflow_id: str | None = Field(None, description="Created workflow instance ID")
    status: WorkflowStartStatus = Field(..., description="Overall start operation status")
    enrichment_status: EnrichmentStatus = Field(
        default=EnrichmentStatus.UNAVAILABLE,
        description="Company enrichment data availability",
    )
    buyer_role_inference: BuyerRoleInferenceResult = Field(
        default_factory=lambda: BuyerRoleInferenceResult(status=BuyerRoleInferenceStatus.UNAVAILABLE),
        description="Buyer role inference result (never fabricated)",
    )
    crm_match: CrmMatchResult = Field(
        default_factory=lambda: CrmMatchResult(status=CrmMatchStatus.UNAVAILABLE),
        description="CRM opportunity match result (never fabricated)",
    )
    next_route_state: str = Field(
        default="workflow-intelligence",
        description="Recommended frontend route state",
    )
    message: str | None = Field(None, description="Human-readable status message")


class ContextField(BaseModel):
    """Single context field with provenance metadata."""

    value: Any = None
    inferred: bool = False
    needs_confirmation: bool = False
    source: str


class ProspectContextResponse(BaseModel):
    """Composite prospect context (legacy endpoint, kept for compatibility)."""

    prospect_id: str
    company_profile: ContextField
    contact_role: ContextField
    crm_match: ContextField
    confidence_flags: list[dict[str, Any]] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=lambda: ["confirm", "adjust", "edit"])


@router.get("/{prospect_id}/context", response_model=ProspectContextResponse)
async def get_prospect_context(
    prospect_id: str,
    tenant_id: str = Depends(get_verified_tenant_id),
    context_client: ProspectContextPort = Depends(get_prospect_context_client),
) -> ProspectContextResponse:
    """Assemble a composite context payload for a prospect.

    Explicitly returns inferred/needs_confirmation/source per UI expectations.
    """
    sources = await context_client.load_context_sources(
        prospect_id=prospect_id,
        tenant_id=tenant_id,
    )
    profile_data = sources.profile_data

    company_profile = ContextField(
        value=profile_data or {},
        inferred=profile_data is None,
        needs_confirmation=profile_data is None,
        source="layer3_knowledge_graph" if profile_data else "layer3_unavailable",
    )

    role_value = "unknown"
    role_inferred = True
    role_needs_confirmation = True

    role_hint = (profile_data or {}).get("title") or (profile_data or {}).get("role")
    if role_hint:
        role_value = role_hint
        role_needs_confirmation = False
    elif sources.role_value:
        role_value = sources.role_value

    contact_role = ContextField(
        value=role_value,
        inferred=role_inferred,
        needs_confirmation=role_needs_confirmation,
        source="layer2_extraction" if role_needs_confirmation else "layer3_knowledge_graph",
    )

    truth_items = sources.truth_items

    # Layer 1 client is included by the adapter for completeness; if no ingestion metadata exists,
    # keep an explicit inferred match state.
    crm_ingestion_source = "layer1_ingestion"
    if profile_data and profile_data.get("crm_id"):
        crm_value: dict[str, Any] = {"matched": True, "record_id": profile_data.get("crm_id")}
        crm_inferred = False
        crm_needs_confirmation = False
        crm_ingestion_source = "layer3_knowledge_graph"
    else:
        crm_value = {"matched": False, "record_id": None}
        crm_inferred = True
        crm_needs_confirmation = True

    crm_match = ContextField(
        value=crm_value,
        inferred=crm_inferred,
        needs_confirmation=crm_needs_confirmation,
        source=crm_ingestion_source,
    )

    confidence_flags = [
        {
            "name": "company_profile_completeness",
            "inferred": company_profile.inferred,
            "needs_confirmation": company_profile.needs_confirmation,
            "source": company_profile.source,
        },
        {
            "name": "contact_role_confidence",
            "inferred": contact_role.inferred,
            "needs_confirmation": contact_role.needs_confirmation,
            "source": contact_role.source,
        },
        {
            "name": "crm_match_confidence",
            "inferred": crm_match.inferred,
            "needs_confirmation": crm_match.needs_confirmation,
            "source": crm_match.source,
        },
        {
            "name": "ground_truth_available",
            "inferred": len(truth_items) == 0,
            "needs_confirmation": len(truth_items) == 0,
            "source": "layer5_ground_truth",
        },
    ]

    return ProspectContextResponse(
        prospect_id=prospect_id,
        company_profile=company_profile,
        contact_role=contact_role,
        crm_match=crm_match,
        confidence_flags=confidence_flags,
    )


# =============================================================================
# Start Analysis Endpoint (Replaces Mock Navigation)
# =============================================================================


def get_executor():
    """Get workflow executor instance from Layer 4 runtime state."""
    from ..startup import runtime_state

    return runtime_state.workflow_executor


@router.post("/{prospect_id}/start-analysis", response_model=StartAnalysisResponse, status_code=status.HTTP_201_CREATED)
async def start_prospect_analysis(
    prospect_id: str,
    request: StartAnalysisRequest,
    tenant_id: str = Depends(get_verified_tenant_id),
    ctx: RequestContext = Depends(require_authenticated),
    db: AsyncSession = Depends(get_db_from_context),
    executor: Any | None = Depends(get_executor),
) -> StartAnalysisResponse:
    """Start prospect analysis workflow — real backend implementation.

    This endpoint replaces the mock "Continue to Intelligence" navigation:
    1. Validates tenant context (fails closed if missing)
    2. Creates/updates prospect record with setup data
    3. Triggers intelligence workflow via orchestration layer
    4. Returns explicit status (never hardcoded demo data)

    Enrichment/CRM/buyer role data explicitly reports availability:
    - UNAVAILABLE: Service not wired/accessible
    - PENDING: Async enrichment queued
    - DEGRADED: Partial data available with caveats
    - COMPLETE/MATCHED: Real data confirmed

    Args:
        prospect_id: Prospect identifier (UUID or external ID)
        request: Setup data and workflow configuration
        tenant_id: Validated tenant from auth context
        ctx: Request context for audit logging
        db: Database session for persistence

    Returns:
        StartAnalysisResponse with real status and next route state

    Raises:
        HTTPException 401: Missing/invalid tenant context
        HTTPException 404: Prospect not found and creation failed
        HTTPException 503: Workflow executor unavailable
    """
    workflow_id: str | None = None
    overall_status = WorkflowStartStatus.PENDING
    enrichment_status = EnrichmentStatus.UNAVAILABLE
    buyer_inference = BuyerRoleInferenceResult(status=BuyerRoleInferenceStatus.UNAVAILABLE)
    crm_match = CrmMatchResult(status=CrmMatchStatus.UNAVAILABLE)
    message = None

    try:
        # -------------------------------------------------------------------
        # 1. Validate tenant context (fail closed)
        # -------------------------------------------------------------------
        if not tenant_id:
            await emit_audit_event(
                action=AuditAction.CREATE,
                outcome=AuditOutcome.FAILURE,
                resource_type="prospect_analysis",
                resource_id=prospect_id,
                details={"reason": "missing_tenant_context"},
                tenant_id=None,
                user_id=ctx.user_id if ctx else None,
            )
            raise AuthenticationError(message = "Tenant context required for prospect analysis")

        # -------------------------------------------------------------------
        # 2. Create or update prospect record
        # -------------------------------------------------------------------
        prospect_uuid = uuid.UUID(prospect_id) if prospect_id else uuid.uuid4()
        setup_data = request.setup_data
        await create_or_update_prospect_account(db, prospect_uuid, setup_data)

        # -------------------------------------------------------------------
        # 3. Attempt workflow trigger (if executor available)
        # -------------------------------------------------------------------
        workflow_id, overall_status_val, message = await trigger_prospect_workflow(
            executor=executor,
            prospect_uuid=prospect_uuid,
            setup_data=setup_data,
            workflow_type=request.workflow_type,
            priority_str=request.priority,
            tenant_id=tenant_id,
            user_id=ctx.user_id if ctx else None,
        )
        overall_status = WorkflowStartStatus(overall_status_val)

        # -------------------------------------------------------------------
        # 4 & 5. Attempt enrichment and CRM status resolution
        # -------------------------------------------------------------------
        enrichment_val, crm_val, crm_source, message = resolve_enrichment_and_crm_status(
            company_name=setup_data.company_name,
            initial_message=message,
        )
        enrichment_status = EnrichmentStatus(enrichment_val)
        crm_match = CrmMatchResult(status=CrmMatchStatus(crm_val), source=crm_source)

        # -------------------------------------------------------------------
        # 6. Buyer role inference (from title if available)
        # -------------------------------------------------------------------
        if setup_data.contact_title:
            buyer_st_val, buyer_role, buyer_conf, buyer_src = infer_buyer_role_from_title(
                setup_data.contact_title
            )
            buyer_inference = BuyerRoleInferenceResult(
                status=BuyerRoleInferenceStatus(buyer_st_val),
                role=buyer_role,
                confidence=buyer_conf,
                source=buyer_src,
            )

        # -------------------------------------------------------------------
        # 7. Emit audit event
        # -------------------------------------------------------------------
        await emit_audit_event(
            action=AuditAction.CREATE,
            outcome=AuditOutcome.SUCCESS if overall_status != WorkflowStartStatus.FAILED else AuditOutcome.FAILURE,
            resource_type="prospect_analysis",
            resource_id=str(prospect_uuid),
            details={
                "workflow_id": workflow_id,
                "status": overall_status.value,
                "enrichment_status": enrichment_status.value,
                "company_name": setup_data.company_name,
            },
            tenant_id=tenant_id,
            user_id=ctx.user_id if ctx else None,
        )

        return StartAnalysisResponse(
            prospect_id=str(prospect_uuid),
            workflow_id=workflow_id,
            status=overall_status,
            enrichment_status=enrichment_status,
            buyer_role_inference=buyer_inference,
            crm_match=crm_match,
            next_route_state="workflow-intelligence",
            message=message,
        )

    except (HTTPException, ValueFabricException):
        raise
    except asyncio.CancelledError:
        raise
    except Exception:
        # Emit failure audit
        await emit_audit_event(
            action=AuditAction.CREATE,
            outcome=AuditOutcome.FAILURE,
            resource_type="prospect_analysis",
            resource_id=prospect_id,
            details={"error": "Prospect analysis failed", "error_code": "PROSPECT_ANALYSIS_ERROR", "reason": "unexpected_error"},
            tenant_id=tenant_id if tenant_id else None,
            user_id=ctx.user_id if ctx else None,
        )
        raise ServiceUnavailableError(message="Failed to start prospect analysis")
