"""Tests for ValueClaimService lifecycle and validation."""

import uuid

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from layer5_ground_truth.models.value_evidence_graph_enums import (
    ClaimStatus,
    ClaimType,
    Confidence,
)
from layer5_ground_truth.services.value_claim_service import (
    InvalidTransitionError,
    ValueClaimService,
    ValueNotOrderedError,
)


@pytest.mark.asyncio
async def test_create_claim_defaults_to_draft(db: AsyncSession):
    svc = ValueClaimService(db)
    claim = await svc.create_claim(
        tenant_id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        statement="Reduce churn by 5%",
        claim_type=ClaimType.REVENUE_GROWTH.value,
        value_unit="USD/year",
        conservative_value=100_000,
        expected_value=250_000,
        aggressive_value=500_000,
        confidence=Confidence.MEDIUM.value,
    )
    assert claim.status == ClaimStatus.DRAFT.value
    assert claim.maturity_level == 0


@pytest.mark.asyncio
async def test_create_claim_enforces_value_order(db: AsyncSession):
    svc = ValueClaimService(db)
    with pytest.raises(ValueNotOrderedError):
        await svc.create_claim(
            tenant_id=uuid.uuid4(),
            account_id=uuid.uuid4(),
            statement="Bad ordering",
            claim_type=ClaimType.COST_SAVINGS.value,
            value_unit="USD",
            conservative_value=200,
            expected_value=100,
            aggressive_value=300,
            confidence=Confidence.HIGH.value,
        )


@pytest.mark.asyncio
async def test_lifecycle_transition_allowed(db: AsyncSession):
    svc = ValueClaimService(db)
    tenant_id = uuid.uuid4()
    account_id = uuid.uuid4()
    claim = await svc.create_claim(
        tenant_id=tenant_id,
        account_id=account_id,
        statement="Cycle time reduction",
        claim_type=ClaimType.CYCLE_TIME_REDUCTION.value,
        value_unit="hours/year",
        conservative_value=100,
        expected_value=200,
        aggressive_value=400,
        confidence=Confidence.MEDIUM.value,
    )

    await svc.transition_status(tenant_id, claim.id, ClaimStatus.SUPPORTED)
    await svc.transition_status(tenant_id, claim.id, ClaimStatus.MODELED)
    await svc.transition_status(tenant_id, claim.id, ClaimStatus.APPROVED)
    await svc.transition_status(tenant_id, claim.id, ClaimStatus.COMMITTED)
    updated = await svc.transition_status(tenant_id, claim.id, ClaimStatus.VALIDATED)

    assert updated.status == ClaimStatus.VALIDATED.value
    assert updated.maturity_level == 5


@pytest.mark.asyncio
async def test_invalid_transition_rejected(db: AsyncSession):
    svc = ValueClaimService(db)
    tenant_id = uuid.uuid4()
    account_id = uuid.uuid4()
    claim = await svc.create_claim(
        tenant_id=tenant_id,
        account_id=account_id,
        statement="x",
        claim_type=ClaimType.COST_SAVINGS.value,
        value_unit="USD",
        conservative_value=1,
        expected_value=2,
        aggressive_value=3,
        confidence=Confidence.LOW.value,
    )

    with pytest.raises(InvalidTransitionError):
        await svc.transition_status(tenant_id, claim.id, ClaimStatus.VALIDATED)


@pytest.mark.asyncio
async def test_cross_tenant_isolation(db: AsyncSession):
    svc = ValueClaimService(db)
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    account_id = uuid.uuid4()
    claim = await svc.create_claim(
        tenant_id=tenant_a,
        account_id=account_id,
        statement="x",
        claim_type=ClaimType.COST_SAVINGS.value,
        value_unit="USD",
        conservative_value=1,
        expected_value=2,
        aggressive_value=3,
        confidence=Confidence.LOW.value,
    )

    fetched = await svc.get_claim(tenant_b, claim.id)
    assert fetched is None
