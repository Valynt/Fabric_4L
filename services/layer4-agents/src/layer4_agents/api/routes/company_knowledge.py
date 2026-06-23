from __future__ import annotations

from value_fabric.shared.error_handling.exceptions import NotFoundError

"""Company Knowledge Onboarding API routes.

Endpoints for managing company knowledge profiles, sources, extractions,
and ICP profiles during tenant onboarding.

SECURITY: All endpoints use get_db_from_context for RLS tenant isolation
          and require_authenticated for mandatory auth enforcement.
"""


import logging
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ...interfaces.company_knowledge_pipeline import CompanyKnowledgePipelinePort
from ...models.company_knowledge import (
    ReviewStatus,
    SourceType,
)
from ...services.company_knowledge_service import CompanyKnowledgeService
from ...startup.agent_composition import create_company_knowledge_pipeline_client
from ..schemas.company_knowledge import (
    CompanyKnowledgeProfileCreateRequest,
    CompanyKnowledgeProfileResponse,
    CompanyKnowledgeProfileUpdateRequest,
    ICPProfileCreateRequest,
    ICPProfileResponse,
    ICPProfileUpdateRequest,
    KnowledgeSourceCreateRequest,
    KnowledgeSourceListResponse,
    KnowledgeSourceResponse,
    OnboardingStatusResponse,
    ProfileApproveRequest,
    ValueExtractionRecordListResponse,
    ValueExtractionRecordResponse,
    ValueExtractionReviewRequest,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/company-knowledge", tags=["Company Knowledge"])


# ============================================================================
# Helper Functions
# ============================================================================


def get_company_knowledge_pipeline_client() -> CompanyKnowledgePipelinePort:
    """Return the company knowledge pipeline adapter for route operations."""
    return create_company_knowledge_pipeline_client()


def _require_profile(
    service: CompanyKnowledgeService,
    profile_id: UUID,
    tenant_id: str,
) -> CompanyKnowledgeProfileResponse:
    """Fetch profile or raise 404."""
    profile = service.get_profile(profile_id, tenant_id)
    if not profile:
        raise NotFoundError(message = str(f"Company knowledge profile {profile_id} not found"))
    return profile


# ============================================================================
# Profile Routes
# ============================================================================


@router.post(
    "/profiles",
    response_model=CompanyKnowledgeProfileResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_profile(
    request: CompanyKnowledgeProfileCreateRequest,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> CompanyKnowledgeProfileResponse:
    """Create a new draft company knowledge profile."""
    service = CompanyKnowledgeService(db)
    profile = await service.create_profile(
        tenant_id=str(ctx.tenant_id),
        company_name=request.company_name,
        website=request.website,
    )
    return CompanyKnowledgeProfileResponse.model_validate(profile)


@router.get("/profiles/current", response_model=CompanyKnowledgeProfileResponse)
async def get_current_profile(
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> CompanyKnowledgeProfileResponse:
    """Get the current tenant's active or latest draft profile."""
    service = CompanyKnowledgeService(db)
    profile = await service.get_active_profile(str(ctx.tenant_id))
    if not profile:
        raise NotFoundError(message = "No company knowledge profile found for this tenant")
    return CompanyKnowledgeProfileResponse.model_validate(profile)


@router.get("/profiles/{profile_id}", response_model=CompanyKnowledgeProfileResponse)
async def get_profile(
    profile_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> CompanyKnowledgeProfileResponse:
    """Get a company knowledge profile by ID."""
    service = CompanyKnowledgeService(db)
    profile = await service.get_profile(profile_id, str(ctx.tenant_id))
    if not profile:
        raise NotFoundError(message = str(f"Profile {profile_id} not found"))
    return CompanyKnowledgeProfileResponse.model_validate(profile)


@router.patch("/profiles/{profile_id}", response_model=CompanyKnowledgeProfileResponse)
async def update_profile(
    profile_id: UUID,
    request: CompanyKnowledgeProfileUpdateRequest,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> CompanyKnowledgeProfileResponse:
    """Update sections of a company knowledge profile."""
    service = CompanyKnowledgeService(db)
    updates = request.model_dump(exclude_unset=True)
    profile = await service.update_profile(profile_id, str(ctx.tenant_id), updates)
    if not profile:
        raise NotFoundError(message = str(f"Profile {profile_id} not found"))
    return CompanyKnowledgeProfileResponse.model_validate(profile)


@router.post(
    "/profiles/{profile_id}/approve",
    response_model=CompanyKnowledgeProfileResponse,
)
async def approve_profile(
    profile_id: UUID,
    request: ProfileApproveRequest,
    http_request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
    pipeline_client: CompanyKnowledgePipelinePort = Depends(get_company_knowledge_pipeline_client),
) -> CompanyKnowledgeProfileResponse:
    """Approve a draft company knowledge profile.

    After approval, syncs the profile entities to Layer 3 Knowledge Graph
    as a background task.
    """
    service = CompanyKnowledgeService(db, pipeline_client=pipeline_client)
    profile = await service.approve_profile(
        profile_id, str(ctx.tenant_id), request.approved_by
    )
    if not profile:
        raise NotFoundError(message = str(f"Profile {profile_id} not found"))

    # Sync approved profile to Layer 3 in the background
    background_tasks.add_task(
        service.sync_profile_to_layer3,
        profile_id=profile_id,
        tenant_id=str(ctx.tenant_id),
        auth_headers={
            key: value for key, value in http_request.headers.items()
            if key.lower() in {"authorization", "x-service-auth", "x-tenant-id"}
        },
    )
    logger.info(
        "Queued Layer 3 sync for approved profile %s (tenant=%s)",
        profile_id,
        ctx.tenant_id,
    )

    return CompanyKnowledgeProfileResponse.model_validate(profile)


# ============================================================================
# Knowledge Source Routes
# ============================================================================


@router.post("/sources", response_model=KnowledgeSourceResponse, status_code=status.HTTP_201_CREATED)
async def add_knowledge_source(
    request: KnowledgeSourceCreateRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
    pipeline_client: CompanyKnowledgePipelinePort = Depends(get_company_knowledge_pipeline_client),
) -> KnowledgeSourceResponse:
    """Add a knowledge source to a profile.

    For website sources, triggers a background crawl via Layer 1.
    """
    service = CompanyKnowledgeService(db, pipeline_client=pipeline_client)
    source = await service.add_knowledge_source(
        tenant_id=str(ctx.tenant_id),
        profile_id=request.profile_id,
        source_type=request.source_type,
        source_url=request.source_url,
        document_name=request.document_name,
        content_hash=request.content_hash,
        raw_storage_path=request.raw_storage_path,
        authority_weight=request.authority_weight.value,
        page_type=request.page_type.value if request.page_type else None,
        extra_metadata=request.extra_metadata,
    )

    # Trigger background crawl for website sources
    if request.source_type == SourceType.WEBSITE and request.source_url:
        background_tasks.add_task(
            service.trigger_layer1_crawl,
            source_id=source.id,
            tenant_id=str(ctx.tenant_id),
        )
        logger.info(
            "Queued background crawl for source %s (tenant=%s)",
            source.id,
            ctx.tenant_id,
        )

    return KnowledgeSourceResponse.model_validate(source)


@router.get("/sources", response_model=KnowledgeSourceListResponse)
async def list_knowledge_sources(
    profile_id: UUID | None = None,
    source_type: SourceType | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> KnowledgeSourceListResponse:
    """List knowledge sources for the tenant."""
    service = CompanyKnowledgeService(db)
    sources, total = await service.list_knowledge_sources(
        tenant_id=str(ctx.tenant_id),
        profile_id=profile_id,
        source_type=source_type,
        page=page,
        page_size=page_size,
    )
    return KnowledgeSourceListResponse(
        items=[KnowledgeSourceResponse.model_validate(s) for s in sources],
        total=total,
        page=page,
        page_size=page_size,
        has_more=total > page * page_size,
    )


# ============================================================================
# Extraction Record Routes
# ============================================================================


@router.get("/extractions", response_model=ValueExtractionRecordListResponse)
async def list_extraction_records(
    profile_id: UUID | None = None,
    source_id: UUID | None = None,
    min_confidence: float | None = Query(None, ge=0.0, le=1.0),
    requires_review: bool | None = None,
    review_status: ReviewStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> ValueExtractionRecordListResponse:
    """List value extraction records with filtering."""
    service = CompanyKnowledgeService(db)
    records, total = await service.list_extraction_records(
        tenant_id=str(ctx.tenant_id),
        profile_id=profile_id,
        source_id=source_id,
        min_confidence=min_confidence,
        requires_review=requires_review,
        review_status=review_status,
        page=page,
        page_size=page_size,
    )
    return ValueExtractionRecordListResponse(
        items=[ValueExtractionRecordResponse.model_validate(r) for r in records],
        total=total,
        page=page,
        page_size=page_size,
        has_more=total > page * page_size,
    )


@router.post("/extractions/{record_id}/review", response_model=ValueExtractionRecordResponse)
async def review_extraction_record(
    record_id: UUID,
    request: ValueExtractionReviewRequest,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> ValueExtractionRecordResponse:
    """Review an extraction record: accept, reject, or modify."""
    service = CompanyKnowledgeService(db)
    # Use current user as reviewer if available
    reviewed_by = getattr(ctx, "user_id", None)
    if reviewed_by is None:
        reviewed_by = UUID("00000000-0000-0000-0000-000000000000")

    record = await service.review_extraction_record(
        record_id=record_id,
        tenant_id=str(ctx.tenant_id),
        action=request.action,
        reviewed_by=reviewed_by,
        user_edits=request.user_edits,
    )
    if not record:
        raise NotFoundError(message = str(f"Extraction record {record_id} not found"))
    return ValueExtractionRecordResponse.model_validate(record)


# ============================================================================
# ICP Profile Routes
# ============================================================================


@router.post("/icp", response_model=ICPProfileResponse, status_code=status.HTTP_201_CREATED)
async def create_icp_profile(
    request: ICPProfileCreateRequest,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> ICPProfileResponse:
    """Create an ICP profile linked to a company knowledge profile."""
    service = CompanyKnowledgeService(db)
    icp = await service.create_icp_profile(
        tenant_id=str(ctx.tenant_id),
        profile_id=request.profile_id,
        industries=request.industries,
        company_size=request.company_size,
        buyer_personas=request.buyer_personas,
        user_personas=request.user_personas,
        pain_points=request.pain_points,
        trigger_events=request.trigger_events,
        qualification_criteria=request.qualification_criteria,
        disqualification_criteria=request.disqualification_criteria,
        competitive_context=request.competitive_context,
        buying_committee_structure=request.buying_committee_structure,
        typical_sales_motion=request.typical_sales_motion,
        confidence=request.confidence,
        source_type=request.source_type.value,
    )
    return ICPProfileResponse.model_validate(icp)


@router.get("/icp", response_model=ICPProfileResponse)
async def get_icp_for_current_profile(
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> ICPProfileResponse:
    """Get the ICP profile for the current tenant's active knowledge profile."""
    service = CompanyKnowledgeService(db)
    profile = await service.get_active_profile(str(ctx.tenant_id))
    if not profile:
        raise NotFoundError(message = "No company knowledge profile found for this tenant")

    icp = await service.get_icp_for_profile(profile.id, str(ctx.tenant_id))
    if not icp:
        raise NotFoundError(message = "No ICP profile found for the current knowledge profile")
    return ICPProfileResponse.model_validate(icp)


@router.patch("/icp/{icp_id}", response_model=ICPProfileResponse)
async def update_icp_profile(
    icp_id: UUID,
    request: ICPProfileUpdateRequest,
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> ICPProfileResponse:
    """Update an ICP profile."""
    service = CompanyKnowledgeService(db)
    updates = request.model_dump(exclude_unset=True)
    icp = await service.update_icp_profile(icp_id, str(ctx.tenant_id), updates)
    if not icp:
        raise NotFoundError(message = str(f"ICP profile {icp_id} not found"))
    return ICPProfileResponse.model_validate(icp)


# ============================================================================
# Onboarding Status Route
# ============================================================================


@router.get("/onboarding-status", response_model=OnboardingStatusResponse)
async def get_onboarding_status(
    db: AsyncSession = Depends(get_db_from_context),
    ctx: RequestContext = Depends(require_authenticated),
) -> OnboardingStatusResponse:
    """Get aggregated onboarding progress for the current tenant."""
    service = CompanyKnowledgeService(db)
    status_data = await service.get_onboarding_status(str(ctx.tenant_id))
    return OnboardingStatusResponse.model_validate(status_data)
