"""FastAPI router for ValueClaim API."""

from __future__ import annotations

import logging
from uuid import UUID

from fastapi import APIRouter, Depends, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.error_handling.exceptions import (
    BadRequestError,
    NotFoundError,
)
from value_fabric.shared.error_handling.models import ErrorCode

from ..database import get_db_from_context
from ..models.value_evidence_graph_enums import ClaimStatus
from ..services.value_claim_service import (
    InvalidTransitionError,
    ValueClaimError,
    ValueClaimService,
    ValueNotOrderedError,
)
from .auth import TokenClaims, authorize_action, get_current_user
from .authz_enforcement import (
    build_principal,
    guard_protected_command,
    make_claim_approval_environment,
    resolve_claim_approval_facts,
)

# Claim lifecycle states that legally reach APPROVED (approval is a protected
# domain command — enforcement is layered on before the write). Only MODELED
# may transition to APPROVED; other-current-state APPROVED targets are invalid
# lifecycle transitions and are rejected as 400 by the service.
_APPROVAL_SOURCE_STATES = {ClaimStatus.MODELED}
from .value_claim_schemas import (
    ValueClaimCreate,
    ValueClaimListResponse,
    ValueClaimResponse,
    ValueClaimStatusTransition,
    ValueClaimSummary,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["value-claims"])


def _handle_service_error(exc: ValueClaimError) -> None:
    """Map domain errors to canonical HTTP exceptions."""
    if exc.code == "NOT_FOUND":
        raise NotFoundError(message=exc.message)
    if exc.code == "INVALID_TRANSITION":
        raise BadRequestError(
            message=exc.message,
            error_code=ErrorCode.CLAIM_VALIDATION_ERROR,
            details={"domain_code": exc.code},
        )
    if exc.code == "VALUE_NOT_ORDERED":
        raise BadRequestError(
            message=exc.message,
            error_code=ErrorCode.CLAIM_VALIDATION_ERROR,
            details={"domain_code": exc.code},
        )
    raise BadRequestError(
        message=exc.message,
        error_code=ErrorCode.CLAIM_VALIDATION_ERROR,
        details={"domain_code": exc.code},
    )


@router.post(
    "/value-claims",
    response_model=ValueClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a ValueClaim",
)
async def create_value_claim(
    request: Request,
    payload: ValueClaimCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ValueClaimResponse:
    authorize_action("layer5.value_claims.create", caller)
    svc = ValueClaimService(db)
    try:
        claim = await svc.create_claim(
            tenant_id=caller.tenant_id,
            account_id=payload.account_id,
            statement=payload.statement,
            claim_type=payload.claim_type.value,
            value_unit=payload.value_unit,
            conservative_value=payload.conservative_value,
            expected_value=payload.expected_value,
            aggressive_value=payload.aggressive_value,
            confidence=payload.confidence.value,
            status=payload.status,
            created_by_user_id=caller.user_id,
            case_id=payload.case_id,
            truth_object_id=payload.truth_object_id,
        )
    except ValueNotOrderedError as exc:
        _handle_service_error(exc)
    except ValueClaimError as exc:
        _handle_service_error(exc)
    return ValueClaimResponse.model_validate(claim)


@router.get(
    "/value-claims",
    response_model=ValueClaimListResponse,
    summary="List ValueClaims for an account",
)
async def list_value_claims(
    account_id: UUID,
    status: ClaimStatus | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ValueClaimListResponse:
    authorize_action("layer5.value_claims.list", caller)
    svc = ValueClaimService(db)
    items = await svc.list_claims(
        tenant_id=caller.tenant_id,
        account_id=account_id,
        status=status,
    )
    total = len(items)
    summaries = [ValueClaimSummary.model_validate(c) for c in items]
    return ValueClaimListResponse(
        items=summaries,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/value-claims/{claim_id}",
    response_model=ValueClaimResponse,
    summary="Get a ValueClaim",
)
async def get_value_claim(
    claim_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ValueClaimResponse:
    authorize_action("layer5.value_claims.read", caller)
    svc = ValueClaimService(db)
    claim = await svc.get_claim(caller.tenant_id, claim_id)
    if claim is None:
        raise NotFoundError(message=f"ValueClaim {claim_id} not found")
    return ValueClaimResponse.model_validate(claim)


@router.post(
    "/value-claims/{claim_id}/status",
    response_model=ValueClaimResponse,
    summary="Transition a ValueClaim status",
)
async def transition_value_claim_status(
    claim_id: UUID,
    payload: ValueClaimStatusTransition,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ValueClaimResponse:
    authorize_action("layer5.value_claims.transition", caller)
    svc = ValueClaimService(db)

    # Approving a claim is a protected domain command. Gate it with the shared
    # PBAC facade (RBAC + ReBAC + ABAC + SoD) BEFORE the write. Only an
    # already-MODELED claim may be approved; other APPROVED targets remain an
    # invalid 400 lifecycle transition handled by the service below.
    if payload.status == ClaimStatus.APPROVED:
        claim_for_guard = await svc.get_claim(caller.tenant_id, claim_id)
        if claim_for_guard is None:
            raise NotFoundError(message=f"ValueClaim {claim_id} not found")
        if ClaimStatus(claim_for_guard.status) in _APPROVAL_SOURCE_STATES:
            principal = await build_principal(caller, db)
            facts = await resolve_claim_approval_facts(claim_for_guard, caller, db)
            env = make_claim_approval_environment(facts)
            await guard_protected_command(
                action="claim.approve",
                principal=principal,
                resource={
                    "type": "value_claim",
                    "id": str(claim_id),
                    "tenant_id": str(caller.tenant_id),
                },
                requested_resource_revision=str(claim_for_guard.version or 1),
                environment=env,
                request_context={"caller": caller, "claim_id": str(claim_id)},
            )

    try:
        claim = await svc.transition_status(
            caller.tenant_id, claim_id, payload.status
        )
    except InvalidTransitionError as exc:
        _handle_service_error(exc)
    except ValueClaimError as exc:
        _handle_service_error(exc)
    return ValueClaimResponse.model_validate(claim)


@router.delete(
    "/value-claims/{claim_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Archive a ValueClaim",
)
async def archive_value_claim(
    claim_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> None:
    authorize_action("layer5.value_claims.archive", caller)
    svc = ValueClaimService(db)
    try:
        await svc.archive(caller.tenant_id, claim_id)
    except ValueClaimError as exc:
        _handle_service_error(exc)
