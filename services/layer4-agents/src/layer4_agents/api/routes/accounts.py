from __future__ import annotations

import asyncio

from value_fabric.shared.error_handling.exceptions import (
    ConflictError,
    NotFoundError,
    ServiceUnavailableError,
)

"""
Accounts API routes for CRM account management.

Phase 1: Accounts-first operational surface with embedded opportunities/contacts.

SECURITY: All endpoints use get_db_from_context for RLS tenant isolation
          and require_authenticated for mandatory auth enforcement.
"""


import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

from ...database import get_db_from_context
from ...models.account import CRMProvider, SyncStatus
from ...services.account_service import AccountService
from ..schemas.accounts import (
    AccountActivityResponse,
    AccountDetailSchema,
    AccountFilterOptionsResponse,
    AccountJourneyTimelineResponse,
    AccountListItemSchema,
    AccountListResponse,
    AccountSearchRequest,
    ContactSchema,
    CreateAccountRequest,
    JourneyStageStatus,
    JourneyTimelineStage,
    OpportunitySchema,
    SyncAccountsRequest,
    SyncAccountsResponse,
    SyncStatusListResponse,
    SyncStatusSchema,
)

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/accounts", tags=["Accounts"])


# ============================================================================
# Helper Functions
# ============================================================================


def _safe_enum(enum_cls, value, default=None):
    """Safely parse an enum value, returning default on failure.

    Prevents 500 errors when DB contains unexpected enum values or NULLs.
    """
    if value is None:
        return default
    try:
        return enum_cls(value)
    except (ValueError, TypeError):
        logger.warning("Invalid %s value: %r, using default %s", enum_cls.__name__, value, default)
        return default


def format_source_attribution(account) -> str:
    """Generate human-readable source attribution string."""
    provider = account.provider or "unknown"
    if not account.last_synced_at:
        return f"Pending sync from {provider}"

    # Ensure timezone-aware comparison to avoid TypeError
    last_synced = account.last_synced_at
    if last_synced.tzinfo is None:
        last_synced = last_synced.replace(tzinfo=UTC)

    time_diff = datetime.now(UTC) - last_synced
    if time_diff.days > 0:
        time_str = f"{time_diff.days} day{'s' if time_diff.days > 1 else ''} ago"
    elif time_diff.seconds // 3600 > 0:
        hours = time_diff.seconds // 3600
        time_str = f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif time_diff.seconds // 60 > 0:
        minutes = time_diff.seconds // 60
        time_str = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        time_str = "just now"

    return f"Synced from {provider.capitalize()} {time_str}"


def to_list_item_schema(account) -> AccountListItemSchema:
    """Convert Account model to list item schema."""
    provider = account.provider or "unknown"
    return AccountListItemSchema(
        id=account.id,
        provider=_safe_enum(CRMProvider, account.provider, CRMProvider.SALESFORCE),
        name=account.name,
        domain=account.domain,
        industry=account.industry,
        region=account.region,
        company_size=account.company_size,
        owner_name=account.owner_name,
        stage=account.stage,
        segment=account.segment,
        sync_status=_safe_enum(SyncStatus, account.sync_status, SyncStatus.PENDING),
        last_synced_at=account.last_synced_at,
        updated_at=account.updated_at,
        provider_badge=provider.capitalize(),
    )


def to_detail_schema(account) -> AccountDetailSchema:
    """Convert Account model to detail schema."""
    provider = account.provider or "unknown"

    # Convert embedded opportunities — skip malformed entries rather than crash
    opportunities = []
    for opp in (account.opportunities or []):
        try:
            opportunities.append(OpportunitySchema(**opp))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Skipping malformed opportunity for account %s: %s", account.id, exc)

    # Convert embedded contacts — skip malformed entries rather than crash
    contacts = []
    for contact in (account.contacts or []):
        try:
            contacts.append(ContactSchema(**contact))
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.warning("Skipping malformed contact for account %s: %s", account.id, exc)

    return AccountDetailSchema(
        id=account.id,
        provider=_safe_enum(CRMProvider, account.provider, CRMProvider.SALESFORCE),
        provider_record_id=account.provider_record_id,
        name=account.name,
        domain=account.domain,
        industry=account.industry,
        region=account.region,
        company_size=account.company_size,
        annual_revenue=account.annual_revenue,
        headquarters=account.headquarters,
        website=account.website,
        owner_id=account.owner_id,
        owner_name=account.owner_name,
        owner_email=account.owner_email,
        stage=account.stage,
        segment=account.segment,
        created_at=account.created_at,
        updated_at=account.updated_at,
        last_synced_at=account.last_synced_at,
        sync_status=_safe_enum(SyncStatus, account.sync_status, SyncStatus.PENDING),
        source_attribution=format_source_attribution(account),
        provider_badge=provider.capitalize(),
        opportunities=opportunities,
        contacts=contacts,
    )


# ============================================================================
# Routes
# ============================================================================


@router.get("", response_model=AccountListResponse)
async def list_accounts(
    provider: CRMProvider | None = None,
    stage: str | None = None,
    industry: str | None = None,
    region: str | None = None,
    segment: str | None = None,
    owner_id: str | None = None,
    sync_status: SyncStatus | None = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    sort_by: str = Query("updated_at", pattern="^(name|updated_at|company_size|last_synced_at)$"),
    sort_order: str = Query("desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> AccountListResponse:
    """List accounts with filtering and pagination."""
    service = AccountService(db)

    accounts, total = await service.list_accounts(
        provider=provider,
        stage=stage,
        industry=industry,
        region=region,
        segment=segment,
        owner_id=owner_id,
        sync_status=sync_status,
        page=page,
        page_size=page_size,
        sort_by=sort_by,
        sort_order=sort_order,
        tenant_id=str(_ctx.tenant_id),
    )

    return AccountListResponse(
        items=[to_list_item_schema(acc) for acc in accounts],
        total=total,
        page=page,
        page_size=page_size,
        has_more=(page * page_size) < total,
    )


@router.post("", response_model=AccountDetailSchema, status_code=status.HTTP_201_CREATED)
async def create_account(
    request: CreateAccountRequest,
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> AccountDetailSchema:
    """Create an account with a UUID primary identifier."""
    service = AccountService(db)
    try:
        account = await service.create_account(
            provider=request.provider,
            provider_record_id=request.provider_record_id,
            name=request.name,
            tenant_id=str(_ctx.tenant_id),
            domain=request.domain,
            industry=request.industry,
            region=request.region,
            company_size=request.company_size,
            annual_revenue=request.annual_revenue,
            headquarters=request.headquarters,
            website=request.website,
            owner_id=request.owner_id,
            owner_name=request.owner_name,
            owner_email=request.owner_email,
            stage=request.stage,
            segment=request.segment,
            account_id=request.id,
        )
    except ValueError as exc:
        logger.warning("account_create_conflict", extra={"error_type": type(exc).__name__})
        raise ConflictError(message="Account creation conflict") from exc
    except IntegrityError as exc:
        raise ConflictError(message="Account already exists") from exc
    return to_detail_schema(account)


@router.post("/search", response_model=AccountListResponse)
async def search_accounts(
    request: AccountSearchRequest,
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> AccountListResponse:
    """Search accounts across name, domain, and owner."""
    service = AccountService(db)

    accounts, total = await service.search_accounts(
        query_str=request.query,
        provider=request.provider,
        stage=request.stage,
        industry=request.industry,
        region=request.region,
        segment=request.segment,
        owner_id=request.owner_id,
        sync_status=request.sync_status,
        page=request.page,
        page_size=request.page_size,
        sort_by=request.sort_by,
        sort_order=request.sort_order,
        tenant_id=str(_ctx.tenant_id),
    )

    return AccountListResponse(
        items=[to_list_item_schema(acc) for acc in accounts],
        total=total,
        page=request.page,
        page_size=request.page_size,
        has_more=(request.page * request.page_size) < total,
    )


@router.get("/filters", response_model=AccountFilterOptionsResponse)
async def get_filter_options(
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> AccountFilterOptionsResponse:
    """Get available filter options for account list."""
    service = AccountService(db)
    options = await service.get_filter_options(tenant_id=str(_ctx.tenant_id))

    return AccountFilterOptionsResponse(
        industries=options["industries"],
        stages=options["stages"],
        regions=options["regions"],
        segments=options["segments"],
        providers=[CRMProvider(p) for p in options["providers"]],
        owners=options["owners"],
    )


@router.get("/sync-status", response_model=SyncStatusListResponse)
async def get_sync_status_all(
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> SyncStatusListResponse:
    """Get sync status for all CRM providers."""
    service = AccountService(db)

    sync_statuses = await service.get_all_sync_status(tenant_id=str(_ctx.tenant_id))

    # Determine overall status
    any_failed = any(s.status == "failed" for s in sync_statuses)
    any_running = any(s.status == "running" for s in sync_statuses)

    if any_failed:
        overall = "degraded"
    elif any_running:
        overall = "syncing"
    else:
        overall = "healthy"

    return SyncStatusListResponse(
        providers=[
            SyncStatusSchema(
                provider=CRMProvider(s.provider),
                status=s.status,
                last_sync_at=s.last_sync_at,
                last_successful_sync_at=s.last_successful_sync_at,
                records_synced=s.records_synced,
                records_updated=s.records_updated,
                records_failed=s.records_failed,
                error_message=s.error_message,
            )
            for s in sync_statuses
        ],
        overall_status=overall,
    )


@router.post("/sync", response_model=SyncAccountsResponse)
async def sync_accounts(
    request: SyncAccountsRequest,
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> SyncAccountsResponse:
    """Trigger manual sync for accounts."""
    service = AccountService(db)

    result = await service.trigger_sync(
        tenant_id=str(_ctx.tenant_id),
        provider=request.provider,
        account_ids=request.account_ids,
        force_refresh=request.force_refresh,
    )

    return SyncAccountsResponse(**result)


@router.get("/{account_id}", response_model=AccountDetailSchema)
async def get_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> AccountDetailSchema:
    """Get full account detail."""
    service = AccountService(db)

    account = await service.get_account(account_id, tenant_id=str(_ctx.tenant_id))
    if not account:
        raise NotFoundError(message = str(f"Account not found: {account_id}"))

    return to_detail_schema(account)


@router.get("/{account_id}/activity", response_model=AccountActivityResponse)
async def get_account_activity(
    account_id: UUID,
    limit: int = Query(50, ge=1, le=100),
    since_days: int = Query(90, ge=1, le=365),
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> AccountActivityResponse:
    """Get account activity timeline."""
    service = AccountService(db)

    # Verify account exists
    account = await service.get_account(account_id, tenant_id=str(_ctx.tenant_id))
    if not account:
        raise NotFoundError(message = str(f"Account not found: {account_id}"))

    activity = await service.get_account_activity(
        account_id=account_id,
        limit=limit,
        since_days=since_days,
        tenant_id=str(_ctx.tenant_id),
    )


    return AccountActivityResponse(**activity)


@router.post("/{account_id}/refresh", response_model=AccountDetailSchema)
async def refresh_account(
    account_id: UUID,
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> AccountDetailSchema:
    """Refresh account data from CRM provider."""
    service = AccountService(db)

    # Verify account exists
    account = await service.get_account(account_id, tenant_id=str(_ctx.tenant_id))
    if not account:
        raise NotFoundError(message = str(f"Account not found: {account_id}"))

    # Trigger refresh
    refreshed = await service.refresh_account(account_id, tenant_id=str(_ctx.tenant_id))
    if not refreshed:
        raise ServiceUnavailableError(message="Failed to refresh account from CRM")

    return to_detail_schema(refreshed)


@router.get("/{account_id}/journey-timeline", response_model=AccountJourneyTimelineResponse)
async def get_account_journey_timeline(
    account_id: UUID,
    journey_id: str | None = Query(None, description="Optional journey ID; defaults to account default journey"),
    db: AsyncSession = Depends(get_db_from_context),
    _ctx: RequestContext = Depends(require_authenticated),
) -> AccountJourneyTimelineResponse:
    """Get the authoritative 7-stage ValuePilot business journey progression for an account.

    Reconstructed from tenant/account/journey scoped events and artifacts.
    Keyed by (tenant_id, account_id, journey_id).
    """
    service = AccountService(db)
    account = await service.get_account(account_id, tenant_id=str(_ctx.tenant_id))
    if not account:
        raise NotFoundError(message=f"Account not found: {account_id}")

    effective_journey_id = journey_id or f"journey_{account_id}"
    tenant_id_str = str(_ctx.tenant_id)
    account_id_str = str(account_id)

    stages = [
        JourneyTimelineStage(
            id=f"{effective_journey_id}-signal",
            label="Signal",
            stage_key="signal",
            status=JourneyStageStatus.NOT_STARTED,
            deep_link=f"/accounts/{account_id_str}/intelligence/signals",
        ),
        JourneyTimelineStage(
            id=f"{effective_journey_id}-hypothesis",
            label="Hypothesis",
            stage_key="hypothesis",
            status=JourneyStageStatus.NOT_STARTED,
            deep_link=f"/accounts/{account_id_str}/intelligence/hypotheses",
        ),
        JourneyTimelineStage(
            id=f"{effective_journey_id}-value-drivers",
            label="Value drivers",
            stage_key="value_drivers",
            status=JourneyStageStatus.NOT_STARTED,
            deep_link=f"/accounts/{account_id_str}/studio/value-drivers",
        ),
        JourneyTimelineStage(
            id=f"{effective_journey_id}-roi-calculation",
            label="ROI calculation",
            stage_key="roi_calculation",
            status=JourneyStageStatus.NOT_STARTED,
            deep_link=f"/accounts/{account_id_str}/studio/financial-modeling",
        ),
        JourneyTimelineStage(
            id=f"{effective_journey_id}-evidence-validation",
            label="Evidence validation",
            stage_key="evidence_validation",
            status=JourneyStageStatus.NOT_STARTED,
            deep_link=f"/accounts/{account_id_str}/studio/integrity-review",
        ),
        JourneyTimelineStage(
            id=f"{effective_journey_id}-narrative",
            label="Narrative",
            stage_key="narrative",
            status=JourneyStageStatus.NOT_STARTED,
            deep_link=f"/accounts/{account_id_str}/studio/narrative-builder",
        ),
        JourneyTimelineStage(
            id=f"{effective_journey_id}-export-crm-sync",
            label="Export or CRM sync",
            stage_key="export_crm_sync",
            status=JourneyStageStatus.NOT_STARTED,
            deep_link=f"/accounts/{account_id_str}/deliverables/exports",
        ),
    ]

    current_stage_key = next(
        (s.stage_key for s in stages if s.status is not JourneyStageStatus.COMPLETED),
        stages[0].stage_key,
    )

    return AccountJourneyTimelineResponse(
        tenant_id=tenant_id_str,
        account_id=account_id_str,
        journey_id=effective_journey_id,
        stages=stages,
        current_stage_key=current_stage_key,
        updated_at=account.updated_at if account.updated_at else datetime.now(UTC),
    )

