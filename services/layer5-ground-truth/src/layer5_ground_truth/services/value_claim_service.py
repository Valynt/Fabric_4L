"""Service layer for ValueClaim lifecycle management."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from layer5_ground_truth.models.value_evidence_graph import ValueClaim
from layer5_ground_truth.models.value_evidence_graph_enums import ClaimStatus
from layer5_ground_truth.repositories.value_claim_repository import (
    ValueClaimRepository,
)


class ValueClaimError(Exception):
    """Base error for ValueClaim domain operations."""

    def __init__(self, message: str, code: str | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.code = code or "VALUE_CLAIM_ERROR"


class InvalidTransitionError(ValueClaimError):
    """Raised when a status transition is not allowed by the claim lifecycle."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="INVALID_TRANSITION")


class ValueNotOrderedError(ValueClaimError):
    """Raised when conservative ≤ expected ≤ aggressive is violated."""

    def __init__(self, message: str) -> None:
        super().__init__(message, code="VALUE_NOT_ORDERED")


# Ordered lifecycle transitions. Terminal states (VALIDATED, INVALIDATED,
# ARCHIVED) only allow ARCHIVED from terminal states.
_ALLOWED_TRANSITIONS: dict[ClaimStatus, set[ClaimStatus]] = {
    ClaimStatus.DRAFT: {ClaimStatus.SUPPORTED, ClaimStatus.ARCHIVED},
    ClaimStatus.SUPPORTED: {ClaimStatus.MODELED, ClaimStatus.ARCHIVED},
    ClaimStatus.MODELED: {
        ClaimStatus.APPROVED,
        ClaimStatus.CHALLENGED,
        ClaimStatus.ARCHIVED,
    },
    ClaimStatus.APPROVED: {
        ClaimStatus.PUBLISHED,
        ClaimStatus.COMMITTED,
        ClaimStatus.ARCHIVED,
    },
    ClaimStatus.PUBLISHED: {
        ClaimStatus.CHALLENGED,
        ClaimStatus.COMMITTED,
        ClaimStatus.ARCHIVED,
    },
    ClaimStatus.CHALLENGED: {
        ClaimStatus.COMMITTED,
        ClaimStatus.INVALIDATED,
        ClaimStatus.ARCHIVED,
    },
    ClaimStatus.COMMITTED: {
        ClaimStatus.VALIDATED,
        ClaimStatus.INVALIDATED,
        ClaimStatus.ARCHIVED,
    },
    ClaimStatus.VALIDATED: {ClaimStatus.ARCHIVED},
    ClaimStatus.INVALIDATED: {ClaimStatus.ARCHIVED},
    ClaimStatus.ARCHIVED: set(),
}

# Maturity ladder stage tied to status for new claims.
_STATUS_MATURITY: dict[ClaimStatus, int] = {
    ClaimStatus.DRAFT: 0,
    ClaimStatus.SUPPORTED: 1,
    ClaimStatus.MODELED: 2,
    ClaimStatus.APPROVED: 3,
    ClaimStatus.PUBLISHED: 3,
    ClaimStatus.CHALLENGED: 3,
    ClaimStatus.COMMITTED: 4,
    ClaimStatus.VALIDATED: 5,
    ClaimStatus.INVALIDATED: 5,
    ClaimStatus.ARCHIVED: 5,
}


def _validate_value_order(
    conservative: Decimal, expected: Decimal, aggressive: Decimal
) -> None:
    if not (conservative <= expected <= aggressive):
        raise ValueNotOrderedError(
            "conservative_value must be <= expected_value <= aggressive_value"
        )


def _validate_status(status: ClaimStatus) -> ClaimStatus:
    if not isinstance(status, ClaimStatus):
        try:
            return ClaimStatus(status)
        except ValueError as exc:
            raise ValueClaimError(
                f"Invalid claim status: {status}", code="INVALID_STATUS"
            ) from exc
    return status


class ValueClaimService:
    """Application service for ValueClaim CRUD and lifecycle transitions."""

    def __init__(self, db: AsyncSession) -> None:
        self._repo = ValueClaimRepository(db)

    async def create_claim(
        self,
        *,
        tenant_id: UUID,
        account_id: UUID,
        statement: str,
        claim_type: str,
        value_unit: str,
        conservative_value: Decimal | float | str,
        expected_value: Decimal | float | str,
        aggressive_value: Decimal | float | str,
        confidence: str,
        status: str | ClaimStatus | None = None,
        created_by_user_id: str | None = None,
        case_id: UUID | None = None,
        truth_object_id: UUID | None = None,
    ) -> ValueClaim:
        resolved_status = (
            _validate_status(status) if status is not None else ClaimStatus.DRAFT
        )
        conservative = Decimal(conservative_value)
        expected = Decimal(expected_value)
        aggressive = Decimal(aggressive_value)
        _validate_value_order(conservative, expected, aggressive)

        now = datetime.now(UTC)
        claim = ValueClaim(
            id=uuid.uuid4(),
            tenant_id=tenant_id,
            account_id=account_id,
            case_id=case_id,
            statement=statement,
            claim_type=claim_type,
            value_unit=value_unit,
            conservative_value=conservative,
            expected_value=expected,
            aggressive_value=aggressive,
            confidence=confidence,
            status=resolved_status.value,
            maturity_level=_STATUS_MATURITY[resolved_status],
            created_by_user_id=created_by_user_id,
            created_at=now,
            updated_at=now,
            truth_object_id=truth_object_id,
        )
        return await self._repo.create(claim)

    async def get_claim(
        self, tenant_id: UUID, claim_id: UUID
    ) -> ValueClaim | None:
        return await self._repo.get_by_id(tenant_id, claim_id)

    async def list_claims(
        self,
        tenant_id: UUID,
        account_id: UUID,
        status: str | ClaimStatus | None = None,
    ) -> list[ValueClaim]:
        status_value: str | None = None
        if status is not None:
            status_value = _validate_status(status).value
        result: list[ValueClaim] = await self._repo.list_by_account(
            tenant_id, account_id, status=status_value
        )
        return result

    async def transition_status(
        self,
        tenant_id: UUID,
        claim_id: UUID,
        new_status: str | ClaimStatus,
    ) -> ValueClaim:
        target = _validate_status(new_status)
        claim = await self._repo.get_by_id(tenant_id, claim_id)
        if claim is None:
            raise ValueClaimError(
                f"ValueClaim {claim_id} not found", code="NOT_FOUND"
            )

        current = ClaimStatus(claim.status)
        allowed = _ALLOWED_TRANSITIONS.get(current, set())
        if target not in allowed:
            raise InvalidTransitionError(
                f"Cannot transition claim from {current.value} to {target.value}"
            )

        claim.status = target.value
        claim.maturity_level = max(
            claim.maturity_level, _STATUS_MATURITY[target]
        )
        claim.updated_at = datetime.now(UTC)
        await self._repo._db.flush()
        await self._repo._db.refresh(claim)
        return claim

    async def archive(
        self, tenant_id: UUID, claim_id: UUID
    ) -> ValueClaim:
        return await self.transition_status(
            tenant_id, claim_id, ClaimStatus.ARCHIVED
        )
