"""Tests for validation aggregation, publish-gate enforcement, and human override auditing.

Covers:
  - aggregate_validation_results: all-passed → can_publish=True
  - aggregate_validation_results: any-failed → can_publish=False
  - aggregate_validation_results: any-needs_review → requires_human_review=True
  - aggregate_validation_results: any-insufficient_evidence → requires_human_review=True
  - aggregate_validation_results: empty → can_publish=False, requires_human_review=True
  - StateMachine: passed validation permits PUBLISH_OUTPUT
  - StateMachine: failed validation blocks PUBLISH_OUTPUT
  - LiveL5Validator: stale approved truth routes to NEEDS_REVIEW
  - LiveL5Validator: unavailable L5 does not approve (INSUFFICIENT_EVIDENCE)
  - HumanGate: human override is audited (decision_by is set)
"""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from harness.live_l5_validator import LiveL5Validator
from harness.models import (
    ClaimValidationResult,
    GateStatus,
    GateType,
    HarnessRunStatus,
    HarnessState,
    HarnessWorkflowType,
    InitiatedBy,
    ValidationState,
    ValidationSummary,
)
from harness.policies import aggregate_validation_results
from harness.state_machine import StateMachine, ValidationRequiredError
from harness.validation_hooks import ClaimValidationRequest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_result(
    claim_id: str,
    state: ValidationState,
    tenant_id: str = "t1",
) -> ClaimValidationResult:
    return ClaimValidationResult(
        tenant_id=tenant_id,
        claim_id=claim_id,
        validation_state=state,
        evidence_refs=[],
        confidence=1.0 if state == ValidationState.PASSED else 0.0,
        trust_score=1.0 if state == ValidationState.PASSED else 0.0,
        validator="agent",
        reason="test",
    )


def _make_mock_client(truths: list[dict]) -> MagicMock:
    client = MagicMock()
    client.list_truths = AsyncMock(return_value={"items": truths, "total": len(truths), "has_more": False})
    client.submit_truth = AsyncMock(return_value={"id": "new-truth"})
    client.get_freshness_summary = AsyncMock(return_value={})
    return client


# ---------------------------------------------------------------------------
# aggregate_validation_results
# ---------------------------------------------------------------------------


class TestAggregateValidationResults:
    def test_all_passed_can_publish(self):
        results = [
            _make_result("c1", ValidationState.PASSED),
            _make_result("c2", ValidationState.PASSED),
        ]
        summary = aggregate_validation_results(results)
        assert summary.can_publish is True
        assert summary.requires_human_review is False
        assert summary.passed == 2
        assert summary.total == 2

    def test_any_failed_blocks_publish(self):
        results = [
            _make_result("c1", ValidationState.PASSED),
            _make_result("c2", ValidationState.FAILED),
        ]
        summary = aggregate_validation_results(results)
        assert summary.can_publish is False
        assert summary.failed == 1

    def test_any_needs_review_requires_human_review(self):
        results = [
            _make_result("c1", ValidationState.PASSED),
            _make_result("c2", ValidationState.NEEDS_REVIEW),
        ]
        summary = aggregate_validation_results(results)
        assert summary.can_publish is False
        assert summary.requires_human_review is True
        assert summary.needs_review == 1

    def test_any_insufficient_evidence_requires_human_review(self):
        results = [
            _make_result("c1", ValidationState.PASSED),
            _make_result("c2", ValidationState.INSUFFICIENT_EVIDENCE),
        ]
        summary = aggregate_validation_results(results)
        assert summary.can_publish is False
        assert summary.requires_human_review is True
        assert summary.insufficient_evidence == 1

    def test_empty_results_blocks_publish_and_requires_review(self):
        summary = aggregate_validation_results([])
        assert summary.can_publish is False
        assert summary.requires_human_review is True
        assert summary.total == 0

    def test_mixed_states_counts_correctly(self):
        results = [
            _make_result("c1", ValidationState.PASSED),
            _make_result("c2", ValidationState.FAILED),
            _make_result("c3", ValidationState.NEEDS_REVIEW),
            _make_result("c4", ValidationState.INSUFFICIENT_EVIDENCE),
        ]
        summary = aggregate_validation_results(results)
        assert summary.total == 4
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.needs_review == 1
        assert summary.insufficient_evidence == 1
        assert summary.can_publish is False

    def test_returns_validation_summary_type(self):
        summary = aggregate_validation_results([_make_result("c1", ValidationState.PASSED)])
        assert isinstance(summary, ValidationSummary)


# ---------------------------------------------------------------------------
# StateMachine publish gate
# ---------------------------------------------------------------------------


class TestStateMachinePublishGate:
    def _make_run(self, current_state: HarnessState = HarnessState.VALIDATE_CLAIMS):
        from harness.models import HarnessRun
        return HarnessRun(
            tenant_id="t1",
            workflow_type=HarnessWorkflowType.BUSINESS_CASE_GENERATION,
            initiated_by=InitiatedBy.USER,
            current_state=current_state,
            status=HarnessRunStatus.RUNNING,
        )

    def test_passed_validation_permits_publish(self):
        sm = StateMachine()
        run = self._make_run(HarnessState.VALIDATE_CLAIMS)
        updated, _ = sm.transition(
            run=run,
            to_state=HarnessState.PUBLISH_OUTPUT,
            validation_state=ValidationState.PASSED,
            human_override=False,
        )
        assert updated.current_state == HarnessState.PUBLISH_OUTPUT

    def test_failed_validation_blocks_publish(self):
        sm = StateMachine()
        run = self._make_run(HarnessState.VALIDATE_CLAIMS)
        with pytest.raises(ValidationRequiredError):
            sm.transition(
                run=run,
                to_state=HarnessState.PUBLISH_OUTPUT,
                validation_state=ValidationState.FAILED,
                human_override=False,
            )

    def test_needs_review_blocks_publish_without_override(self):
        sm = StateMachine()
        run = self._make_run(HarnessState.VALIDATE_CLAIMS)
        with pytest.raises(ValidationRequiredError):
            sm.transition(
                run=run,
                to_state=HarnessState.PUBLISH_OUTPUT,
                validation_state=ValidationState.NEEDS_REVIEW,
                human_override=False,
            )

    def test_insufficient_evidence_blocks_publish(self):
        sm = StateMachine()
        run = self._make_run(HarnessState.VALIDATE_CLAIMS)
        with pytest.raises(ValidationRequiredError):
            sm.transition(
                run=run,
                to_state=HarnessState.PUBLISH_OUTPUT,
                validation_state=ValidationState.INSUFFICIENT_EVIDENCE,
                human_override=False,
            )

    def test_human_override_permits_publish_from_human_review(self):
        sm = StateMachine()
        run = self._make_run(HarnessState.HUMAN_REVIEW)
        updated, _ = sm.transition(
            run=run,
            to_state=HarnessState.PUBLISH_OUTPUT,
            validation_state=ValidationState.NEEDS_REVIEW,
            human_override=True,
        )
        assert updated.current_state == HarnessState.PUBLISH_OUTPUT


# ---------------------------------------------------------------------------
# LiveL5Validator: stale approved truth → NEEDS_REVIEW
# ---------------------------------------------------------------------------


class TestLiveL5ValidatorStaleApproved:
    @pytest.mark.asyncio
    async def test_stale_approved_truth_routes_to_needs_review(self):
        """An approved TruthObject older than stale_threshold_hours → NEEDS_REVIEW."""
        stale_time = (datetime.now(UTC) - timedelta(hours=48)).isoformat()
        truths = [
            {
                "claim": "roi claim text",
                "status": "approved",
                "confidence": 0.9,
                "updated_at": stale_time,
            }
        ]
        client = _make_mock_client(truths)
        validator = LiveL5Validator(client=client, stale_threshold_hours=24)

        req = ClaimValidationRequest(
            tenant_id="t1",
            claim_id="c1",
            claim_text="roi claim text",
            evidence_refs=[],
        )
        result = await validator.validate(req)
        assert result.validation_state == ValidationState.NEEDS_REVIEW

    @pytest.mark.asyncio
    async def test_fresh_approved_truth_passes(self):
        """A recently approved TruthObject → PASSED."""
        fresh_time = (datetime.now(UTC) - timedelta(hours=1)).isoformat()
        truths = [
            {
                "claim": "roi claim text",
                "status": "approved",
                "confidence": 0.9,
                "updated_at": fresh_time,
            }
        ]
        client = _make_mock_client(truths)
        validator = LiveL5Validator(client=client, stale_threshold_hours=24)

        req = ClaimValidationRequest(
            tenant_id="t1",
            claim_id="c1",
            claim_text="roi claim text",
            evidence_refs=[],
        )
        result = await validator.validate(req)
        assert result.validation_state == ValidationState.PASSED


# ---------------------------------------------------------------------------
# LiveL5Validator: unavailable L5 does not approve
# ---------------------------------------------------------------------------


class TestLiveL5ValidatorUnavailable:
    @pytest.mark.asyncio
    async def test_list_truths_failure_returns_insufficient_evidence(self):
        """list_truths network failure → INSUFFICIENT_EVIDENCE, never PASSED."""
        client = MagicMock()
        client.list_truths = AsyncMock(side_effect=ConnectionError("L5 unreachable"))
        client.get_freshness_summary = AsyncMock(side_effect=ConnectionError("L5 unreachable"))

        validator = LiveL5Validator(client=client)
        req = ClaimValidationRequest(
            tenant_id="t1",
            claim_id="c1",
            claim_text="any claim",
            evidence_refs=[],
        )
        result = await validator.validate(req)
        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE
        assert result.validation_state != ValidationState.PASSED

    @pytest.mark.asyncio
    async def test_health_returns_false_when_l5_unreachable(self):
        """health() returns False when L5 is unreachable."""
        client = MagicMock()
        client.get_freshness_summary = AsyncMock(side_effect=ConnectionError("L5 unreachable"))

        validator = LiveL5Validator(client=client)
        assert await validator.health() is False

    @pytest.mark.asyncio
    async def test_unhandled_exception_returns_insufficient_evidence(self):
        """Any unhandled exception in validate() → INSUFFICIENT_EVIDENCE, never raises."""
        client = MagicMock()
        client.list_truths = AsyncMock(side_effect=RuntimeError("unexpected"))
        client.get_freshness_summary = AsyncMock(return_value={})

        validator = LiveL5Validator(client=client)
        req = ClaimValidationRequest(
            tenant_id="t1",
            claim_id="c1",
            claim_text="any claim",
            evidence_refs=[],
        )
        # Must not raise
        result = await validator.validate(req)
        assert result.validation_state == ValidationState.INSUFFICIENT_EVIDENCE


# ---------------------------------------------------------------------------
# Human override is audited (decision_by is set)
# ---------------------------------------------------------------------------


class TestHumanOverrideAudited:
    @pytest.mark.asyncio
    async def test_gate_decision_by_is_recorded(self):
        """Approving a gate records decision_by on the gate object."""
        from harness.factory import make_in_memory_registry
        from harness.models import HarnessWorkflowType, InitiatedBy

        registry = make_in_memory_registry()
        run = registry.create_run(
            tenant_id="t1",
            workflow_type=HarnessWorkflowType.BUSINESS_CASE_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        gate = registry.create_human_gate(run.id, "t1", GateType.APPROVE_CLAIMS)
        assert gate.status == GateStatus.PENDING

        decided = registry.decide_gate(
            gate_id=gate.id,
            tenant_id="t1",
            decision=GateStatus.APPROVED,
            decision_by="reviewer@example.com",
            decision_reason="All claims verified manually",
        )
        assert decided.status == GateStatus.APPROVED
        assert decided.decision_by == "reviewer@example.com"
        assert decided.decision_reason == "All claims verified manually"
        assert decided.decided_at is not None

    @pytest.mark.asyncio
    async def test_rejected_gate_records_decision_by(self):
        """Rejecting a gate also records decision_by."""
        from harness.factory import make_in_memory_registry
        from harness.models import HarnessWorkflowType, InitiatedBy

        registry = make_in_memory_registry()
        run = registry.create_run(
            tenant_id="t1",
            workflow_type=HarnessWorkflowType.BUSINESS_CASE_GENERATION,
            initiated_by=InitiatedBy.USER,
        )
        gate = registry.create_human_gate(run.id, "t1", GateType.APPROVE_CLAIMS)
        decided = registry.decide_gate(
            gate_id=gate.id,
            tenant_id="t1",
            decision=GateStatus.REJECTED,
            decision_by="reviewer@example.com",
            decision_reason="Claim lacks evidence",
        )
        assert decided.status == GateStatus.REJECTED
        assert decided.decision_by == "reviewer@example.com"
