from __future__ import annotations

"""Tests for canonical replay-conflict policy enforcement."""


from datetime import UTC, datetime, timedelta

import pytest

from value_fabric.layer4.models.agent_state import WorkflowStatus
from value_fabric.layer4.policies.replay_conflict import (
    CollisionAction,
    ReplayDecision,
    ReplayConflictError,
    ReplayConflictPolicy,
    ReplayConflictResolver,
)


class TestReplayConflictPolicy:
    def test_default_policy_values(self) -> None:
        policy = ReplayConflictPolicy()
        assert policy.default_decision == ReplayDecision.REJECT
        assert policy.max_replay_age_seconds == 86400
        assert policy.require_exact_checkpoint_match is True
        assert policy.on_collision == CollisionAction.FAIL
        assert WorkflowStatus.INTERRUPTED in policy.allowed_statuses_for_resume

    def test_allowed_statuses_non_empty_validation(self) -> None:
        with pytest.raises(ValueError, match="allowed_statuses_for_resume must not be empty"):
            ReplayConflictPolicy(allowed_statuses_for_resume=set())

    def test_custom_policy(self) -> None:
        policy = ReplayConflictPolicy(
            default_decision=ReplayDecision.MERGE_SAFE,
            max_replay_age_seconds=3600,
            require_exact_checkpoint_match=False,
            on_collision=CollisionAction.OVERWRITE,
        )
        assert policy.default_decision == ReplayDecision.MERGE_SAFE
        assert policy.max_replay_age_seconds == 3600
        assert policy.require_exact_checkpoint_match is False
        assert policy.on_collision == CollisionAction.OVERWRITE


class TestReplayConflictResolver:
    def test_compute_replay_fingerprint_deterministic(self) -> None:
        resolver = ReplayConflictResolver()
        fp1 = resolver.compute_replay_fingerprint("run_123", "tenant_a", "chk_456")
        fp2 = resolver.compute_replay_fingerprint("run_123", "tenant_a", "chk_456")
        assert fp1 == fp2
        assert len(fp1) == 64  # SHA-256 hex

    def test_compute_replay_fingerprint_different_inputs(self) -> None:
        resolver = ReplayConflictResolver()
        fp1 = resolver.compute_replay_fingerprint("run_123", "tenant_a", "chk_456")
        fp2 = resolver.compute_replay_fingerprint("run_123", "tenant_a", "chk_457")
        assert fp1 != fp2

    def test_validate_resume_attempt_allowed_status(self) -> None:
        resolver = ReplayConflictResolver()
        resolver.validate_resume_attempt(
            workflow_status=WorkflowStatus.INTERRUPTED,
            checkpoint_created_at=datetime.now(UTC) - timedelta(hours=1),
            checkpoint_hash="abc",
            expected_hash="abc",
            latest_checkpoint_hash="abc",
        )

    def test_validate_resume_attempt_rejects_disallowed_status(self) -> None:
        resolver = ReplayConflictResolver()
        with pytest.raises(ReplayConflictError, match="not eligible for resume"):
            resolver.validate_resume_attempt(
                workflow_status=WorkflowStatus.COMPLETED,
                checkpoint_created_at=datetime.now(UTC) - timedelta(hours=1),
                checkpoint_hash="abc",
                expected_hash="abc",
                latest_checkpoint_hash="abc",
            )

    def test_validate_resume_attempt_rejects_old_checkpoint(self) -> None:
        resolver = ReplayConflictResolver()
        with pytest.raises(ReplayConflictError, match="age .* exceeds"):
            resolver.validate_resume_attempt(
                workflow_status=WorkflowStatus.INTERRUPTED,
                checkpoint_created_at=datetime.now(UTC) - timedelta(days=2),
                checkpoint_hash="abc",
                expected_hash="abc",
                latest_checkpoint_hash="abc",
            )

    def test_validate_resume_attempt_rejects_hash_mismatch(self) -> None:
        resolver = ReplayConflictResolver()
        with pytest.raises(ReplayConflictError, match="checkpoint hash mismatch"):
            resolver.validate_resume_attempt(
                workflow_status=WorkflowStatus.INTERRUPTED,
                checkpoint_created_at=datetime.now(UTC) - timedelta(hours=1),
                checkpoint_hash="abc",
                expected_hash="def",
                latest_checkpoint_hash="abc",
            )

    def test_validate_resume_attempt_accepts_equal_canonical_hash_variants(self) -> None:
        resolver = ReplayConflictResolver()
        digest = "a" * 64
        resolver.validate_resume_attempt(
            workflow_status=WorkflowStatus.INTERRUPTED,
            checkpoint_created_at=datetime.now(UTC) - timedelta(hours=1),
            checkpoint_hash=f"SHA256:{digest.upper()}",
            expected_hash=f"0x{digest}",
            latest_checkpoint_hash=digest,
        )

    def test_validate_resume_attempt_rejects_encoding_variant_safely(self) -> None:
        resolver = ReplayConflictResolver()
        with pytest.raises(ReplayConflictError, match="hash normalization failed"):
            resolver.validate_resume_attempt(
                workflow_status=WorkflowStatus.INTERRUPTED,
                checkpoint_created_at=datetime.now(UTC) - timedelta(hours=1),
                checkpoint_hash="not-hex-encoded",
                expected_hash="a" * 64,
                latest_checkpoint_hash="a" * 64,
            )

    def test_validate_resume_attempt_rejects_collision_when_fail(self) -> None:
        resolver = ReplayConflictResolver()
        with pytest.raises(ReplayConflictError, match="checkpoint collision/mismatch"):
            resolver.validate_resume_attempt(
                workflow_status=WorkflowStatus.INTERRUPTED,
                checkpoint_created_at=datetime.now(UTC) - timedelta(hours=1),
                checkpoint_hash="a" * 64,
                expected_hash="a" * 64,
                latest_checkpoint_hash="b" * 64,
            )

    def test_evaluate_duplicate_replay_rejects_without_audit_justification(self) -> None:
        resolver = ReplayConflictResolver()
        seen = {resolver.compute_replay_fingerprint("run_123", "tenant_a", "chk_456")}
        decision = resolver.evaluate_duplicate_replay(
            run_id="run_123",
            tenant_id="tenant_a",
            checkpoint_id="chk_456",
            seen_fingerprints=seen,
        )
        assert decision == ReplayDecision.REJECT

    def test_evaluate_duplicate_replay_allows_new(self) -> None:
        resolver = ReplayConflictResolver()
        seen = set()
        decision = resolver.evaluate_duplicate_replay(
            run_id="run_123",
            tenant_id="tenant_a",
            checkpoint_id="chk_456",
            seen_fingerprints=seen,
        )
        assert decision == ReplayDecision.MERGE_SAFE

    def test_evaluate_duplicate_replay_force_replay_with_audit_justification(self) -> None:
        resolver = ReplayConflictResolver()
        seen = {resolver.compute_replay_fingerprint("run_123", "tenant_a", "chk_456")}
        decision = resolver.evaluate_duplicate_replay(
            run_id="run_123",
            tenant_id="tenant_a",
            checkpoint_id="chk_456",
            seen_fingerprints=seen,
            audit_justification="Incident 42 approved by on-call",
        )
        assert decision == ReplayDecision.FORCE_REPLAY
