import uuid
from datetime import datetime

import pytest
from sqlalchemy.ext.asyncio import AsyncSession

from layer5_ground_truth.models.value_evidence_graph import ValueClaim
from layer5_ground_truth.models.value_evidence_graph_enums import (
    ClaimStatus,
    ClaimType,
    Confidence,
)
from layer5_ground_truth.repositories.value_claim_repository import ValueClaimRepository


@pytest.mark.asyncio
async def test_create_and_get_claim(db: AsyncSession):
    tenant_id = uuid.uuid4()
    account_id = uuid.uuid4()
    repo = ValueClaimRepository(db)
    claim = ValueClaim(
        tenant_id=tenant_id,
        account_id=account_id,
        statement="Reduce onboarding cycle time by 25%",
        claim_type=ClaimType.CYCLE_TIME_REDUCTION,
        value_unit="USD/year",
        conservative_value=700_000,
        expected_value=1_200_000,
        aggressive_value=1_800_000,
        confidence=Confidence.MEDIUM,
        status=ClaimStatus.DRAFT,
        maturity_level=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    created = await repo.create(claim)
    fetched = await repo.get_by_id(tenant_id, created.id)
    assert fetched is not None
    assert fetched.expected_value == 1_200_000


@pytest.mark.asyncio
async def test_cross_tenant_isolation(db: AsyncSession):
    tenant_a = uuid.uuid4()
    tenant_b = uuid.uuid4()
    account_id = uuid.uuid4()
    repo = ValueClaimRepository(db)
    claim = ValueClaim(
        tenant_id=tenant_a,
        account_id=account_id,
        statement="test",
        claim_type=ClaimType.COST_SAVINGS,
        value_unit="USD",
        conservative_value=1,
        expected_value=2,
        aggressive_value=3,
        confidence=Confidence.LOW,
        status=ClaimStatus.DRAFT,
        maturity_level=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    created = await repo.create(claim)
    assert await repo.get_by_id(tenant_b, created.id) is None


@pytest.mark.asyncio
async def test_list_by_account_filters_by_status(db: AsyncSession):
    tenant_id = uuid.uuid4()
    account_id = uuid.uuid4()
    repo = ValueClaimRepository(db)

    draft = ValueClaim(
        tenant_id=tenant_id,
        account_id=account_id,
        statement="draft claim",
        claim_type=ClaimType.COST_SAVINGS,
        value_unit="USD",
        conservative_value=1,
        expected_value=2,
        aggressive_value=3,
        confidence=Confidence.MEDIUM,
        status=ClaimStatus.DRAFT,
        maturity_level=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    supported = ValueClaim(
        tenant_id=tenant_id,
        account_id=account_id,
        statement="supported claim",
        claim_type=ClaimType.COST_SAVINGS,
        value_unit="USD",
        conservative_value=1,
        expected_value=2,
        aggressive_value=3,
        confidence=Confidence.MEDIUM,
        status=ClaimStatus.SUPPORTED,
        maturity_level=0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    await repo.create(draft)
    await repo.create(supported)

    all_claims = await repo.list_by_account(tenant_id, account_id)
    assert len(all_claims) == 2

    supported_claims = await repo.list_by_account(
        tenant_id, account_id, status=ClaimStatus.SUPPORTED.value
    )
    assert len(supported_claims) == 1
    assert supported_claims[0].status == ClaimStatus.SUPPORTED
