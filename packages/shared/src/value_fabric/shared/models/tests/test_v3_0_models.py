"""Unit tests for v3.0 shared models."""

from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from value_fabric.shared.models.claim import (
    Claim,
    ClaimCreate,
    ClaimProvenance,
    ClaimStatus,
    EvidenceStrength,
)
from value_fabric.shared.models.fabric_found_summary import (
    FabricFoundSummary,
    SummaryItem,
    SummaryItemStatus,
    SummarySection,
)
from value_fabric.shared.models.parameter_manifest import (
    ParameterManifest,
    ParameterStatus,
    ParameterType,
    ParameterValue,
    ParameterValidationRule,
)


@pytest.fixture
def tenant_id():
    return uuid4()


@pytest.fixture
def account_id():
    return uuid4()


@pytest.fixture
def now():
    return datetime.now(UTC)


@pytest.fixture
def claim_provenance(now):
    return ClaimProvenance(
        extractor="ai",
        method="llm_extraction",
        model="gpt-4",
        run_id="run-123",
        source_refs=["source://1"],
        extracted_at=now,
        normalizer_version="v3.0",
        extractor_version="v3.0",
    )


class TestClaim:
    def test_claim_requires_evidence_chunk(self, tenant_id, account_id, now, claim_provenance) -> None:
        with pytest.raises(ValueError):
            Claim(
                id=uuid4(),
                tenant_id=tenant_id,
                account_id=account_id,
                claim_text="Test claim",
                confidence=0.9,
                trust_score=0.8,
                provenance=claim_provenance,
                created_at=now,
                updated_at=now,
                evidence_chunk_ids=[],
            )

    def test_claim_valid_with_evidence_chunk(self, tenant_id, account_id, now, claim_provenance) -> None:
        chunk_id = uuid4()
        claim = Claim(
            id=uuid4(),
            tenant_id=tenant_id,
            account_id=account_id,
            claim_text="Test claim",
            confidence=0.9,
            trust_score=0.8,
            evidence_strength=EvidenceStrength.STRONG,
            evidence_strength_score=0.85,
            provenance=claim_provenance,
            created_at=now,
            updated_at=now,
            evidence_chunk_ids=[chunk_id],
        )
        assert claim.status == ClaimStatus.EXTRACTED
        assert claim.evidence_chunk_ids == [chunk_id]

    def test_claim_create_requires_evidence_chunk(self, account_id, claim_provenance) -> None:
        with pytest.raises(ValueError):
            ClaimCreate(
                account_id=account_id,
                claim_text="Test claim",
                confidence=0.9,
                provenance=claim_provenance,
                evidence_chunk_ids=[],
            )


class TestParameterManifest:
    def test_parameter_manifest_create(self, tenant_id, account_id, now) -> None:
        manifest = ParameterManifest(
            id=uuid4(),
            tenant_id=tenant_id,
            account_id=account_id,
            name="annual_contract_value",
            display_name="Annual Contract Value",
            parameter_type=ParameterType.CURRENCY,
            required=True,
            validation_rules=[
                ParameterValidationRule(rule_type="range", config={"min": 0, "max": 1000000000})
            ],
            created_at=now,
            updated_at=now,
        )
        assert manifest.override_allowed is True

    def test_parameter_value_status(self, tenant_id, account_id, now) -> None:
        value = ParameterValue(
            id=uuid4(),
            tenant_id=tenant_id,
            account_id=account_id,
            parameter_id=uuid4(),
            value={"amount": 100000, "currency": "USD"},
            status=ParameterStatus.VALIDATED,
            confidence=0.95,
            created_at=now,
            updated_at=now,
        )
        assert value.status == ParameterStatus.VALIDATED


class TestFabricFoundSummary:
    def test_summary_requires_revision(self, tenant_id, account_id, now) -> None:
        item = SummaryItem(
            id=uuid4(),
            section=SummarySection.FACTS,
            title="Annual contract value",
            body="The customer spends $100k annually.",
            status=SummaryItemStatus.FACT,
            confidence=0.95,
            trust_score=0.9,
            claim_ids=[uuid4()],
            evidence_chunk_ids=[uuid4()],
        )
        summary = FabricFoundSummary(
            id=uuid4(),
            tenant_id=tenant_id,
            account_id=account_id,
            revision=1,
            title="Account Summary",
            items=[item],
            created_at=now,
        )
        assert summary.revision == 1
        assert summary.items[0].status == SummaryItemStatus.FACT

    def test_summary_revision_must_be_positive(self, tenant_id, account_id, now) -> None:
        with pytest.raises(ValueError):
            FabricFoundSummary(
                id=uuid4(),
                tenant_id=tenant_id,
                account_id=account_id,
                revision=0,
                title="Account Summary",
                created_at=now,
            )
