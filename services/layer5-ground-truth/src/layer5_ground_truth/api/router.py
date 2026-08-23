import asyncio

from value_fabric.shared.error_handling.exceptions import (
    BadRequestError,
    ConflictError,
    NotFoundError,
)

"""
FastAPI router for Layer 5 Ground Truth API.

Endpoints:
  POST   /truths                    — Create a new TruthObject
  GET    /truths                    — List TruthObjects (paginated, filterable)
  GET    /truths/{id}               — Get a single TruthObject with full detail
  POST   /truths/{id}/validate      — Apply a validation state transition
  POST   /truths/{id}/sources       — Add an evidence source
  DELETE /truths/{id}               — Soft-delete a TruthObject
  GET    /truths/{id}/audit         — Get full validation event log
  POST   /truths/sync-kg            — Trigger Layer 3 KG sync for validated objects
  GET    /maturity-ladder           — Reference: full maturity ladder definition
  GET    /health                    — Health check
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import emit_audit_event
from value_fabric.shared.audit.models import AuditAction, AuditOutcome

from ..cache import cached
from ..config import get_settings
from ..database import get_db_from_context
from ..integration.layer3_client import get_layer3_client
from ..models.truth_object import ClaimType, TruthStatus
from ..services.state_machine import (
    InsufficientEvidenceError,
    InvalidTransitionError,
    TransitionConflictError,
)
from ..services.truth_service import (
    add_source,
    create_truth_object,
    get_truth_object,
    list_truth_objects,
    soft_delete_truth_object,
    validate_truth_object,
)
from .auth import TokenClaims, authorize_action, get_current_user
from .schemas import (
    AddSourceRequest,
    FreshnessCheckResponse,
    FreshnessSummaryResponse,
    MaturityLadderResponse,
    MaturityLevelDetail,
    StaleTruthsResponse,
    SyncToKgResponse,
    TruthObjectCreate,
    TruthObjectListResponse,
    TruthObjectResponse,
    TruthObjectSummary,
    TruthSourceResponse,
    ValidateRequest,
    ValidateResponse,
    ValidationEventResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["ground-truth"])


# ---------------------------------------------------------------------------
# POST /truths
# ---------------------------------------------------------------------------


@router.post(
    "/truths",
    response_model=TruthObjectResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new TruthObject",
    description=(
        "Create a new evidence-backed factual claim in PROPOSED state. "
        "If sources are provided and confidence meets the threshold, the object "
        "will automatically advance to VALIDATED."
    ),
    responses={
        201: {"description": "TruthObject created successfully"},
        422: {"description": "Validation error in request body"},
    },
)
async def create_truth(
    request: Request,
    payload: TruthObjectCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> TruthObjectResponse:
    authorize_action("layer5.truths.create", caller)
    tenant_id = caller.tenant_id
    sources_data = (
        [s.model_dump() for s in payload.sources] if payload.sources else None
    )

    truth = await create_truth_object(
        db=db,
        tenant_id=tenant_id,  # resolved from JWT
        claim=payload.claim,
        claim_type=payload.claim_type,
        confidence=payload.confidence,
        extraction_job_id=payload.extraction_job_id,
        extraction_model=payload.extraction_model,
        value=payload.value.model_dump() if payload.value else None,
        applies_to=payload.applies_to.model_dump() if payload.applies_to else None,
        raw_extraction_data=payload.raw_extraction_data,
        sources=sources_data,
    )

    # Reload with eager-loaded relationships for the response
    truth = await get_truth_object(db, truth.id, tenant_id)
    if truth is None:
        raise NotFoundError(message="Truth object not found after creation")

    # Best-effort KG sync for high-confidence objects
    settings = get_settings()
    if truth.confidence >= settings.min_confidence_for_validated and truth.status in (
        "validated",
    ):
        try:
            client = get_layer3_client()
            request_id = getattr(request.state, "trace_id", None)
            node_id = await client.sync_truth_object(
                truth_object_id=truth.id,
                tenant_id=tenant_id,
                claim=truth.claim,
                claim_type=truth.claim_type,
                confidence=truth.confidence,
                status=truth.status,
                maturity_level=truth.maturity_level,
                value=truth.value,
                applies_to=truth.applies_to,
                source_count=len(truth.sources),
                request_id=str(request_id) if request_id else None,
            )
            if node_id:
                truth.kg_node_id = node_id
                truth.kg_synced_at = datetime.now(UTC)
        except Exception:
            logger.warning("create_truth_kg_sync_failed", exc_info=True)

    try:
        emit_audit_event(
            action=AuditAction.TRUTH_CREATED,
            outcome=AuditOutcome.SUCCESS,
            tenant_id=tenant_id,
            user_id=caller.user_id,
            resource_type="TruthObject",
            resource_id=str(truth.id),
            details={
                "claim": payload.claim,
                "claim_type": payload.claim_type,
                "confidence": payload.confidence,
                "status": truth.status,
            },
        )
    except Exception:
        logger.exception("truth_created_audit_failed")

    return TruthObjectResponse.model_validate(truth)


# ---------------------------------------------------------------------------
# GET /truths
# ---------------------------------------------------------------------------


@router.get(
    "/truths",
    response_model=TruthObjectListResponse,
    summary="List TruthObjects",
    description="Paginated, filterable list of TruthObjects for the organization.",
)
async def list_truths(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    status_filter: TruthStatus | None = Query(
        default=None,
        alias="status",
        description="Filter by validation status",
    ),
    claim_type: ClaimType | None = Query(
        default=None,
        description="Filter by claim type",
    ),
    min_maturity: int | None = Query(
        default=None,
        ge=0,
        le=5,
        description="Minimum maturity level (0–5)",
    ),
    min_confidence: float | None = Query(
        default=None,
        ge=0.0,
        le=1.0,
        description="Minimum confidence score",
    ),
    is_stale: bool | None = Query(
        default=None,
        description="Filter by staleness",
    ),
    applies_to_opportunity: str | None = Query(
        default=None,
        description="Filter by opportunity_id in applies_to",
    ),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> TruthObjectListResponse:
    authorize_action("layer5.truths.list", caller)
    tenant_id = caller.tenant_id
    items, total = await list_truth_objects(
        db=db,
        tenant_id=tenant_id,
        status=status_filter,
        claim_type=claim_type,
        min_maturity=min_maturity,
        min_confidence=min_confidence,
        is_stale=is_stale,
        applies_to_opportunity=applies_to_opportunity,
        limit=limit,
        offset=offset,
    )

    summaries = [
        TruthObjectSummary(
            id=t.id,
            claim=t.claim,
            claim_type=t.claim_type,
            confidence=t.confidence,
            status=t.status,
            maturity_level=t.maturity_level,
            is_stale=t.is_stale,
            source_count=len(t.sources),
            validated_by=t.validated_by,
            freshness=t.freshness,
            created_at=t.created_at,
        )
        for t in items
    ]

    return TruthObjectListResponse(
        items=summaries,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


# ---------------------------------------------------------------------------
# POST /truths/sync-kg
# ---------------------------------------------------------------------------


@router.post(
    "/truths/sync-kg",
    response_model=SyncToKgResponse,
    summary="Sync validated TruthObjects to Layer 3 Knowledge Graph",
    description=(
        "Triggers a bulk sync of all VALIDATED TruthObjects that have not yet "
        "been synced to the Layer 3 Knowledge Graph."
    ),
)
async def sync_to_kg(
    request: Request,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> SyncToKgResponse:
    authorize_action("layer5.truths.sync_kg", caller)
    tenant_id = caller.tenant_id
    from sqlalchemy import and_, select

    from ..models.truth_object import TruthObject

    result = await db.execute(
        select(TruthObject).where(
            and_(
                TruthObject.tenant_id == tenant_id,
                TruthObject.status == "validated",
                TruthObject.kg_node_id.is_(None),
                TruthObject.deleted_at.is_(None),
            )
        )
    )
    pending = result.scalars().all()

    client = get_layer3_client()
    request_id = getattr(request.state, "trace_id", None)

    async def _sync_single_truth(truth):
        node_id = await client.sync_truth_object(
            truth_object_id=truth.id,
            tenant_id=truth.tenant_id,
            claim=truth.claim,
            claim_type=truth.claim_type,
            confidence=truth.confidence,
            status=truth.status,
            maturity_level=truth.maturity_level,
            value=truth.value,
            applies_to=truth.applies_to,
            source_count=len(truth.sources),
            request_id=str(request_id) if request_id else None,
        )
        if node_id:
            truth.kg_node_id = node_id
            truth.kg_synced_at = datetime.now(UTC)
            return True
        return False

    results = await asyncio.gather(*(_sync_single_truth(t) for t in pending))
    synced = sum(1 for r in results if r)
    failed = len(results) - synced

    try:
        emit_audit_event(
            action=AuditAction.TRUTH_SYNCED,
            outcome=AuditOutcome.SUCCESS,
            tenant_id=tenant_id,
            user_id=caller.user_id,
            resource_type="TruthObject",
            resource_id="bulk",
            details={
                "synced": synced,
                "failed": failed,
                "total_pending": len(pending),
            },
        )
    except Exception:
        logger.exception("truth_synced_audit_failed")

    return SyncToKgResponse.model_validate(
        {
            "synced": synced,
            "failed": failed,
            "total_pending": len(pending),
        }
    )


# ---------------------------------------------------------------------------
# POST /truths/check-stale
# ---------------------------------------------------------------------------


@router.post(
    "/truths/check-stale",
    summary="Trigger freshness check for expired truths",
    description=(
        "Manually trigger the freshness monitor to check for and transition "
        "expired TruthObjects to EXPIRED status. Can be run in dry-run mode to preview."
    ),
    response_model=FreshnessCheckResponse,
    responses={
        200: {"description": "Freshness check completed"},
    },
)
async def check_stale(
    dry_run: bool = Query(default=False, description="Preview only, don't transition to expired"),
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FreshnessCheckResponse:
    authorize_action("layer5.truths.check_stale", caller)
    from ..services.freshness_monitor import check_freshness

    tenant_id = caller.tenant_id
    result = await check_freshness(
        db=db,
        tenant_id=tenant_id,
        dry_run=dry_run,
    )
    return result


# ---------------------------------------------------------------------------
# GET /truths/stale
# ---------------------------------------------------------------------------


@router.get(
    "/truths/stale",
    response_model=StaleTruthsResponse,
    summary="List expired TruthObjects",
    description="Returns all TruthObjects with EXPIRED status for the organization."
)
async def list_stale(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> StaleTruthsResponse:
    authorize_action("layer5.truths.list_stale", caller)
    from ..services.freshness_monitor import get_stale_truths
    from .schemas import TruthObjectSummary

    tenant_id = caller.tenant_id
    items, total = await get_stale_truths(
        db=db,
        tenant_id=tenant_id,
        limit=limit,
        offset=offset,
    )

    summaries = [
        TruthObjectSummary(
            id=t.id,
            claim=t.claim,
            claim_type=t.claim_type,
            confidence=t.confidence,
            status=t.status,
            maturity_level=t.maturity_level,
            is_stale=t.is_stale,
            source_count=len(t.sources),
            validated_by=t.validated_by,
            freshness=t.freshness,
            created_at=t.created_at,
        )
        for t in items
    ]

    return StaleTruthsResponse.model_validate(
        {
            "items": summaries,
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total,
        }
    )


# ---------------------------------------------------------------------------
# GET /truths/freshness-summary
# ---------------------------------------------------------------------------


@router.get(
    "/truths/freshness-summary",
    response_model=FreshnessSummaryResponse,
    summary="Get freshness status summary",
    description="Returns counts of stale, fresh, and expiring-soon TruthObjects.",
)
async def freshness_summary(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> FreshnessSummaryResponse:
    authorize_action("layer5.truths.freshness_summary", caller)
    from ..services.freshness_monitor import FreshnessMonitor

    tenant_id = caller.tenant_id
    monitor = FreshnessMonitor()
    result = await monitor.get_freshness_summary(db, tenant_id)
    return FreshnessSummaryResponse.model_validate(result)


# ---------------------------------------------------------------------------
# GET /truths/{id}
# ---------------------------------------------------------------------------


@router.get(
    "/truths/{truth_id}",
    response_model=TruthObjectResponse,
    summary="Get a TruthObject",
    description="Retrieve a single TruthObject with full detail, sources, and audit trail.",
    responses={
        200: {"description": "TruthObject found"},
        404: {"description": "TruthObject not found"},
    },
)
async def get_truth(
    truth_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> TruthObjectResponse:
    authorize_action("layer5.truths.read", caller)
    tenant_id = caller.tenant_id
    truth = await get_truth_object(db, truth_id, tenant_id)
    if not truth:
        raise NotFoundError(message=f"TruthObject {truth_id} not found")
    return TruthObjectResponse.model_validate(truth)


# ---------------------------------------------------------------------------
# POST /truths/{id}/validate
# ---------------------------------------------------------------------------


@router.post(
    "/truths/{truth_id}/validate",
    response_model=ValidateResponse,
    summary="Apply a validation state transition",
    description=(
        "Trigger a named validation action on a TruthObject. "
        "Actions: validate | dispute | resolve_dispute | reject | supersede | operationalize"
    ),
    responses={
        200: {"description": "Transition applied successfully"},
        400: {"description": "Invalid transition or insufficient evidence"},
        409: {"description": "Concurrent transition conflict"},
        404: {"description": "TruthObject not found"},
    },
)
async def validate_truth(
    request: Request,
    truth_id: UUID,
    payload: ValidateRequest,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ValidateResponse:
    authorize_action("layer5.truths.validate", caller)
    tenant_id = caller.tenant_id
    truth = await get_truth_object(db, truth_id, tenant_id)
    if not truth:
        raise NotFoundError(message=f"TruthObject {truth_id} not found")

    previous_status = truth.status
    previous_maturity = truth.maturity_level

    try:
        truth = await validate_truth_object(
            db=db,
            truth_object=truth,
            action=payload.action,
            actor=payload.actor,
            actor_type=payload.actor_type,
            notes=payload.notes,
            dispute_reason=(
                payload.dispute_reason.value if payload.dispute_reason else None
            ),
            rejection_reason=(
                payload.rejection_reason.value if payload.rejection_reason else None
            ),
            superseded_by_id=payload.superseded_by_id,
        )
    except InvalidTransitionError as exc:
        logger.warning("invalid_truth_transition: %s", exc)
        raise BadRequestError(message="Request failed", details={"code": "INVALID_TRANSITION", "message": "Invalid state transition for truth object"})
    except InsufficientEvidenceError as exc:
        logger.warning("insufficient_evidence: %s", exc)
        raise BadRequestError(message="Request failed", details={"code": "INSUFFICIENT_EVIDENCE", "message": "Insufficient evidence for requested operation"})
    except TransitionConflictError as exc:
        logger.warning("truth_transition_conflict: %s", exc)
        raise ConflictError(
            message="Conflict during state transition",
            details={
                "code": "TRANSITION_CONFLICT",
                "expected": previous_status,
                "actual": truth.status if truth else "unknown",
            },
        )
    except ValueError as exc:
        logger.warning("truth_value_error: %s", exc)
        raise BadRequestError(message="Request failed", details={"code": "INVALID_REQUEST", "message": "Invalid request parameters"})

    # Sync to Layer 3 after validation
    if truth.status == "validated":
        try:
            client = get_layer3_client()
            request_id = getattr(request.state, "trace_id", None)
            node_id = await client.sync_truth_object(
                truth_object_id=truth.id,
                tenant_id=tenant_id,
                claim=truth.claim,
                claim_type=truth.claim_type,
                confidence=truth.confidence,
                status=truth.status,
                maturity_level=truth.maturity_level,
                value=truth.value,
                applies_to=truth.applies_to,
                source_count=len(truth.sources),
                request_id=str(request_id) if request_id else None,
            )
            if node_id:
                truth.kg_node_id = node_id
                truth.kg_synced_at = datetime.now(UTC)
        except Exception:
            logger.warning("validate_truth_kg_sync_failed", exc_info=True)

    try:
        emit_audit_event(
            action=AuditAction.TRUTH_VALIDATED,
            outcome=AuditOutcome.SUCCESS,
            tenant_id=tenant_id,
            user_id=caller.user_id,
            resource_type="TruthObject",
            resource_id=str(truth.id),
            details={
                "action": payload.action,
                "previous_status": previous_status,
                "new_status": truth.status,
                "previous_maturity": previous_maturity,
                "new_maturity": truth.maturity_level,
                "actor": payload.actor,
            },
        )
    except Exception:
        logger.exception("truth_validated_audit_failed")

    return ValidateResponse(
        truth_object_id=truth.id,
        previous_status=previous_status,
        new_status=truth.status,
        previous_maturity=previous_maturity,
        new_maturity=truth.maturity_level,
        actor=payload.actor,
        message=(
            f"Successfully applied '{payload.action}': "
            f"{previous_status} → {truth.status}"
        ),
    )


# ---------------------------------------------------------------------------
# POST /truths/{id}/sources
# ---------------------------------------------------------------------------


@router.post(
    "/truths/{truth_id}/sources",
    response_model=TruthSourceResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add an evidence source",
    description=(
        "Attach a new evidence source to an existing TruthObject. "
        "Adding a source may trigger automatic status advancement."
    ),
    responses={
        201: {"description": "Source added successfully"},
        404: {"description": "TruthObject not found"},
    },
)
async def add_truth_source(
    truth_id: UUID,
    payload: AddSourceRequest,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> TruthSourceResponse:
    authorize_action("layer5.truths.add_source", caller)
    tenant_id = caller.tenant_id
    truth = await get_truth_object(db, truth_id, tenant_id)
    if not truth:
        raise NotFoundError(message=f"TruthObject {truth_id} not found")

    _, source = await add_source(
        db=db,
        truth_object=truth,
        tenant_id=tenant_id,
        source_data=payload.model_dump(),
    )

    return TruthSourceResponse.model_validate(source)


# ---------------------------------------------------------------------------
# GET /truths/{id}/audit
# ---------------------------------------------------------------------------


@router.get(
    "/truths/{truth_id}/audit",
    response_model=list[ValidationEventResponse],
    summary="Get validation audit trail",
    description="Returns the full immutable audit log of all state transitions for a TruthObject.",
)
async def get_audit_trail(
    truth_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> list[ValidationEventResponse]:
    authorize_action("layer5.truths.read_audit", caller)
    tenant_id = caller.tenant_id
    truth = await get_truth_object(db, truth_id, tenant_id)
    if not truth:
        raise NotFoundError(message=f"TruthObject {truth_id} not found")
    return [ValidationEventResponse.model_validate(e) for e in truth.validation_events]


# ---------------------------------------------------------------------------
# DELETE /truths/{id}
# ---------------------------------------------------------------------------


@router.delete(
    "/truths/{truth_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Soft-delete a TruthObject",
    description="Marks a TruthObject as deleted. Records are never hard-deleted.",
)
async def delete_truth(
    truth_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> None:
    authorize_action("layer5.truths.delete", caller)
    tenant_id = caller.tenant_id
    deleted_by = caller.user_id
    truth = await get_truth_object(db, truth_id, tenant_id)
    if not truth:
        raise NotFoundError(message=f"TruthObject {truth_id} not found")
    await soft_delete_truth_object(db, truth, deleted_by=deleted_by)

    try:
        emit_audit_event(
            action=AuditAction.TRUTH_DELETED,
            outcome=AuditOutcome.SUCCESS,
            tenant_id=tenant_id,
            user_id=caller.user_id,
            resource_type="TruthObject",
            resource_id=str(truth_id),
            details={"deleted_by": deleted_by},
        )
    except Exception:
        logger.exception("truth_deleted_audit_failed")


# ---------------------------------------------------------------------------
# GET /maturity-ladder
# ---------------------------------------------------------------------------


@router.get(
    "/maturity-ladder",
    response_model=MaturityLadderResponse,
    summary="Get maturity ladder definition",
    description="Returns the full 0–5 maturity ladder with descriptions and advancement criteria.",
)
@cached(ttl=3600, key_prefix="maturity_ladder")
async def get_maturity_ladder() -> MaturityLadderResponse:
    levels = [
        MaturityLevelDetail(
            level=0,
            name="Raw",
            description="Claim captured but not yet processed by any extraction model.",
            required_status="proposed",
            advancement_trigger="Extraction model processes the raw content",
        ),
        MaturityLevelDetail(
            level=1,
            name="Extracted",
            description="AI model has identified and structured the claim from source content.",
            required_status="proposed",
            advancement_trigger="At least 1 source attached AND confidence ≥ threshold",
        ),
        MaturityLevelDetail(
            level=2,
            name="Supported",
            description="Claim has at least one linked evidence source and meets confidence threshold.",
            required_status="proposed",
            advancement_trigger="≥ 2 distinct independent sources corroborate the claim",
        ),
        MaturityLevelDetail(
            level=3,
            name="Corroborated",
            description="Multiple independent sources confirm the claim from different angles.",
            required_status="proposed",
            advancement_trigger="Human reviewer explicitly validates the claim",
        ),
        MaturityLevelDetail(
            level=4,
            name="Validated",
            description="A qualified human reviewer has validated and approved the claim.",
            required_status="validated",
            advancement_trigger="Claim is referenced in an ROI model, board deck, or business case",
        ),
        MaturityLevelDetail(
            level=5,
            name="Operationalized",
            description=(
                "Claim has been used in board-level or CFO-facing decisions. "
                "This is the highest trust level — suitable for executive narratives."
            ),
            required_status="validated",
            advancement_trigger="Referenced in downstream business artefact (ROI model, deck, contract)",
        ),
    ]
    return MaturityLadderResponse(levels=levels)
