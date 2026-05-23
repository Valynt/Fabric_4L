"""
Unit tests for the ValidationStateMachine.

Tests are designed to FAIL initially if the state machine is not implemented
correctly. Each test verifies a specific invariant of the state machine.

Coverage:
  - All valid forward transitions
  - All invalid transitions (must raise InvalidTransitionError)
  - Insufficient evidence guard (InsufficientEvidenceError)
  - Dispute and resolve_dispute flow
  - Reject flow
  - Supersede flow
  - Expire flow
  - Auto-advance behaviour
  - Maturity level advancement
  - Immutable audit event creation
"""

import uuid
from datetime import UTC, datetime

import pytest

from layer5_ground_truth.models.truth_object import (
    DisputeReason,
    MaturityLevel,
    RejectionReason,
    TruthObject,
    TruthSource,
    TruthStatus,
    ValidationEvent,
)
from layer5_ground_truth.services.state_machine import (
    InsufficientEvidenceError,
    InvalidTransitionError,
    ValidationStateMachine,
)
from tests.conftest import TEST_ORG_ID

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def make_truth(
    status: TruthStatus = TruthStatus.PROPOSED,
    confidence: float = 0.85,
    maturity: int = MaturityLevel.EXTRACTED.value,
) -> TruthObject:
    return TruthObject(
        id=uuid.uuid4(),
        tenant_id=TEST_ORG_ID,
        claim="Test claim for unit testing",
        claim_type="efficiency_gain",
        confidence=confidence,
        status=status.value,
        maturity_level=maturity,
        freshness=datetime.now(UTC),
        created_at=datetime.now(UTC),
        updated_at=datetime.now(UTC),
    )


def make_source(
    truth_id: uuid.UUID,
    source_type: str = "call_transcript",
) -> TruthSource:
    return TruthSource(
        id=uuid.uuid4(),
        truth_object_id=truth_id,
        tenant_id=TEST_ORG_ID,
        source_type=source_type,
        confidence_contribution=0.8,
        created_at=datetime.now(UTC),
    )


# ---------------------------------------------------------------------------
# PROPOSED → VALIDATED
# ---------------------------------------------------------------------------


class TestValidate:
    @pytest.mark.asyncio
    async def test_validates_when_conditions_met(self, db):
        """Should advance PROPOSED → VALIDATED when confidence ≥ 0.5 and 2+ distinct sources."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, confidence=0.85)
        db.add(truth)
        db.add(make_source(truth.id, source_type="call_transcript"))
        db.add(make_source(truth.id, source_type="crm_field"))
        await db.flush()

        result = await sm.validate(db, truth, validated_by="test_user")

        assert result.status == TruthStatus.VALIDATED.value
        assert result.maturity_level >= MaturityLevel.APPROVED.value
        assert result.validated_by == "test_user"
        assert result.validated_at is not None

    @pytest.mark.asyncio
    async def test_fails_without_enough_sources(self, db):
        """Should raise InsufficientEvidenceError when fewer than 2 distinct sources."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, confidence=0.85)
        db.add(truth)
        db.add(make_source(truth.id))
        await db.flush()

        with pytest.raises(InsufficientEvidenceError, match="2 distinct sources"):
            await sm.validate(db, truth, validated_by="test_user")

    @pytest.mark.asyncio
    async def test_fails_with_low_confidence(self, db):
        """Should raise InsufficientEvidenceError when confidence < threshold."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, confidence=0.3)
        db.add(truth)
        db.add(make_source(truth.id, source_type="a"))
        db.add(make_source(truth.id, source_type="b"))
        await db.flush()

        with pytest.raises(InsufficientEvidenceError, match="confidence"):
            await sm.validate(db, truth, validated_by="test_user")

    @pytest.mark.asyncio
    async def test_invalid_from_validated(self, db):
        """Cannot validate a truth that is already VALIDATED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.VALIDATED, maturity=MaturityLevel.APPROVED.value)
        db.add(truth)
        await db.flush()

        with pytest.raises(InvalidTransitionError):
            await sm.validate(db, truth, validated_by="test_user")

    @pytest.mark.asyncio
    async def test_creates_validation_event(self, db):
        """Transition must create an immutable ValidationEvent record."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, confidence=0.9)
        db.add(truth)
        db.add(make_source(truth.id, source_type="a"))
        db.add(make_source(truth.id, source_type="b"))
        await db.flush()

        await sm.validate(db, truth, validated_by="auditor")
        await db.flush()

        from sqlalchemy import select

        events = (
            await db.execute(
                select(ValidationEvent).where(
                    ValidationEvent.truth_object_id == truth.id,
                    ValidationEvent.to_status == TruthStatus.VALIDATED.value,
                )
            )
        ).scalars().all()

        assert len(events) == 1
        assert events[0].actor == "auditor"
        assert events[0].from_status == TruthStatus.PROPOSED.value


# ---------------------------------------------------------------------------
# Dispute flow
# ---------------------------------------------------------------------------


class TestDisputeFlow:
    @pytest.mark.asyncio
    async def test_dispute_from_proposed(self, db):
        """Should mark PROPOSED → DISPUTED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, maturity=MaturityLevel.EXTRACTED.value)
        db.add(truth)
        await db.flush()

        result = await sm.dispute(
            db,
            truth,
            reason=DisputeReason.CONFLICTING_SOURCES,
            disputed_by="reviewer@company.com",
        )

        assert result.status == TruthStatus.DISPUTED.value
        assert result.dispute_reason == DisputeReason.CONFLICTING_SOURCES.value
        assert result.disputed_by == "reviewer@company.com"

    @pytest.mark.asyncio
    async def test_dispute_from_validated(self, db):
        """Should allow disputing a VALIDATED truth object."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.VALIDATED, maturity=MaturityLevel.APPROVED.value)
        db.add(truth)
        await db.flush()

        result = await sm.dispute(
            db,
            truth,
            reason=DisputeReason.STALE_DATA,
            disputed_by="analyst@company.com",
        )

        assert result.status == TruthStatus.DISPUTED.value

    @pytest.mark.asyncio
    async def test_cannot_dispute_already_disputed(self, db):
        """Cannot dispute a truth object that is already DISPUTED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.DISPUTED)
        db.add(truth)
        await db.flush()

        with pytest.raises(InvalidTransitionError):
            await sm.dispute(
                db,
                truth,
                reason=DisputeReason.OTHER,
                disputed_by="reviewer@company.com",
            )

    @pytest.mark.asyncio
    async def test_resolve_dispute_reverts_to_validated(self, db):
        """Resolving a dispute should revert to VALIDATED and clear dispute fields."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.DISPUTED, maturity=MaturityLevel.APPROVED.value)
        truth.dispute_reason = DisputeReason.CONFLICTING_SOURCES.value
        truth.disputed_by = "analyst@company.com"
        db.add(truth)
        await db.flush()

        result = await sm.resolve_dispute(db, truth, resolved_by="cfo@company.com")

        assert result.status == TruthStatus.VALIDATED.value
        assert result.dispute_reason is None
        assert result.disputed_by is None


# ---------------------------------------------------------------------------
# Reject flow
# ---------------------------------------------------------------------------


class TestReject:
    @pytest.mark.asyncio
    async def test_reject_from_proposed(self, db):
        """Should mark PROPOSED → REJECTED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED)
        db.add(truth)
        await db.flush()

        result = await sm.reject(
            db,
            truth,
            reason=RejectionReason.INSUFFICIENT_EVIDENCE,
            rejected_by="reviewer@company.com",
        )

        assert result.status == TruthStatus.REJECTED.value
        assert result.rejection_reason == RejectionReason.INSUFFICIENT_EVIDENCE.value
        assert result.rejected_by == "reviewer@company.com"
        assert result.rejected_at is not None

    @pytest.mark.asyncio
    async def test_reject_from_disputed(self, db):
        """Should mark DISPUTED → REJECTED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.DISPUTED)
        db.add(truth)
        await db.flush()

        result = await sm.reject(
            db,
            truth,
            reason=RejectionReason.FACTUALLY_INCORRECT,
            rejected_by="reviewer@company.com",
        )

        assert result.status == TruthStatus.REJECTED.value

    @pytest.mark.asyncio
    async def test_cannot_reject_already_rejected(self, db):
        """Cannot reject a truth object that is already REJECTED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.REJECTED)
        db.add(truth)
        await db.flush()

        with pytest.raises(InvalidTransitionError):
            await sm.reject(
                db,
                truth,
                reason=RejectionReason.OTHER,
                rejected_by="reviewer@company.com",
            )

    @pytest.mark.asyncio
    async def test_cannot_reject_validated(self, db):
        """Cannot reject a VALIDATED truth directly (must dispute first)."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.VALIDATED)
        db.add(truth)
        await db.flush()

        with pytest.raises(InvalidTransitionError):
            await sm.reject(
                db,
                truth,
                reason=RejectionReason.OTHER,
                rejected_by="reviewer@company.com",
            )


# ---------------------------------------------------------------------------
# Supersede flow
# ---------------------------------------------------------------------------


class TestSupersede:
    @pytest.mark.asyncio
    async def test_supersede_from_validated(self, db):
        """Should mark VALIDATED → SUPERSEDED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.VALIDATED, maturity=MaturityLevel.APPROVED.value)
        db.add(truth)
        # Create a newer truth object to supersede by
        newer_truth = make_truth(TruthStatus.VALIDATED, maturity=MaturityLevel.APPROVED.value)
        db.add(newer_truth)
        await db.flush()

        result = await sm.supersede(
            db,
            truth,
            superseded_by_id=newer_truth.id,
            superseded_by="system",
        )

        assert result.status == TruthStatus.SUPERSEDED.value
        assert result.superseded_by_id == newer_truth.id
        assert result.superseded_at is not None

    @pytest.mark.asyncio
    async def test_cannot_supersede_proposed(self, db):
        """Cannot supersede a PROPOSED truth."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED)
        db.add(truth)
        await db.flush()

        with pytest.raises(InvalidTransitionError):
            await sm.supersede(
                db,
                truth,
                superseded_by_id=uuid.uuid4(),
                superseded_by="system",
            )


# ---------------------------------------------------------------------------
# Expire flow
# ---------------------------------------------------------------------------


class TestExpire:
    @pytest.mark.asyncio
    async def test_expire_from_validated(self, db):
        """Should mark VALIDATED → EXPIRED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.VALIDATED, maturity=MaturityLevel.APPROVED.value)
        db.add(truth)
        await db.flush()

        result = await sm.expire(db, truth)

        assert result.status == TruthStatus.EXPIRED.value
        assert result.is_stale is True

    @pytest.mark.asyncio
    async def test_expire_from_disputed(self, db):
        """Should mark DISPUTED → EXPIRED."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.DISPUTED)
        db.add(truth)
        await db.flush()

        result = await sm.expire(db, truth)

        assert result.status == TruthStatus.EXPIRED.value

    @pytest.mark.asyncio
    async def test_cannot_expire_proposed(self, db):
        """Cannot expire a PROPOSED truth."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED)
        db.add(truth)
        await db.flush()

        with pytest.raises(InvalidTransitionError):
            await sm.expire(db, truth)


# ---------------------------------------------------------------------------
# Operationalize
# ---------------------------------------------------------------------------


class TestOperationalize:
    @pytest.mark.asyncio
    async def test_advances_maturity_to_5(self, db):
        """Should advance maturity to OPERATIONALIZED (5) for VALIDATED objects."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.VALIDATED, maturity=MaturityLevel.APPROVED.value)
        db.add(truth)
        await db.flush()

        result = await sm.mark_operationalized(
            db,
            truth,
            trigger="used_in_roi_model",
            triggered_by="system",
            context={"roi_model_id": "roi-001"},
        )

        assert result.maturity_level == MaturityLevel.OPERATIONALIZED.value
        assert result.status == TruthStatus.VALIDATED.value  # status unchanged

    @pytest.mark.asyncio
    async def test_fails_for_non_validated(self, db):
        """Should raise InvalidTransitionError for non-VALIDATED objects."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, maturity=MaturityLevel.EXTRACTED.value)
        db.add(truth)
        await db.flush()

        with pytest.raises(InvalidTransitionError, match="Only VALIDATED"):
            await sm.mark_operationalized(db, truth, trigger="test")

    @pytest.mark.asyncio
    async def test_idempotent_if_already_operationalized(self, db):
        """Should not raise if already at OPERATIONALIZED maturity."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.VALIDATED, maturity=MaturityLevel.OPERATIONALIZED.value)
        db.add(truth)
        await db.flush()

        result = await sm.mark_operationalized(db, truth, trigger="test")
        assert result.maturity_level == MaturityLevel.OPERATIONALIZED.value


# ---------------------------------------------------------------------------
# Auto-advance
# ---------------------------------------------------------------------------


class TestAutoAdvance:
    @pytest.mark.asyncio
    async def test_auto_advances_to_validated_with_two_sources(self, db):
        """Auto-advance should reach VALIDATED with 2 sources + high confidence."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, confidence=0.9)
        db.add(truth)
        db.add(make_source(truth.id, source_type="call_transcript"))
        db.add(make_source(truth.id, source_type="crm_field"))
        await db.flush()

        result = await sm.auto_advance(db, truth)

        assert result.status == TruthStatus.VALIDATED.value

    @pytest.mark.asyncio
    async def test_does_not_auto_validate_with_one_source(self, db):
        """Auto-advance should not reach VALIDATED with only 1 source."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, confidence=0.9)
        db.add(truth)
        db.add(make_source(truth.id))
        await db.flush()

        result = await sm.auto_advance(db, truth)

        assert result.status == TruthStatus.PROPOSED.value

    @pytest.mark.asyncio
    async def test_stays_proposed_with_low_confidence(self, db):
        """Auto-advance should not advance if confidence is below threshold."""
        sm = ValidationStateMachine()
        truth = make_truth(TruthStatus.PROPOSED, confidence=0.2)
        db.add(truth)
        db.add(make_source(truth.id, source_type="a"))
        db.add(make_source(truth.id, source_type="b"))
        await db.flush()

        result = await sm.auto_advance(db, truth)

        assert result.status == TruthStatus.PROPOSED.value
