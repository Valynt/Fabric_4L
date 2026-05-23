"""Tests for canonical replay-conflict policy enforcement."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest

from value_fabric.layer4.models.agent_state import WorkflowStatus
from value_fabric.layer4.policies.replay_conflict import (
    CollisionAction,
    ReplayConflictError,
    ReplayConflictPolicy,
    ReplayConflictResolver,
    ReplayStrategy,
)


class TestReplayConflictPolicy:
    def test_default_policy_values(self) -> None:
        policy = ReplayConflictPolicy()
        assert policy.strategy == ReplayStrategy.REJECT
        assert policy.max_replay_age_seconds == 86400
        assert policy.require_exact_checkpoint_match is True
        assert policy.on_collision == CollisionAction.FAIL
        assert WorkflowStatus.INTERRUPTED in policy.allowed_statuses_for_resume

    def test_allowed_statuses_non_empty_validation(self) -> None:
        with pytest.raises(ValueError, match="allowed_statuses_for_resume must not be empty"):
            ReplayConflictPolicy(allowed_statuses_for_resume=set())

    def test_custom_policy(self) -> None:
        policy = ReplayConflictPolicy(
            strategy=ReplayStrategy.MERGE,
            max_replay_age_seconds=3600,
            require_exact_checkpoint_match=False,
            on_collision=CollisionAction.OVERWRITE,
        )
        assert policy.strategy == ReplayStrategy.MERGE
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

    def test_validate_resume_attempt_rejects_collision_when_fail(self) -> None:
        resolver = ReplayConflictResolver()
        with pytest.raises(ReplayConflictError, match="diverges from latest checkpoint"):
            resolver.validate_resume_attempt(
                workflow_status=WorkflowStatus.INTERRUPTED,
                checkpoint_created_at=datetime.now(UTC) - timedelta(hours=1),
                checkpoint_hash="abc",
                expected_hash="abc",
                latest_checkpoint_hash="def",
            )

    def test_check_duplicate_replay_rejects_on_reject_strategy(self) -> None:
        resolver = ReplayConflictResolver()
        seen = {resolver.compute_replay_fingerprint("run_123", "tenant_a", "chk_456")}
        with pytest.raises(ReplayConflictError, match="duplicate replay detected"):
            resolver.check_duplicate_replay(
                run_id="run_123",
                tenant_id="tenant_a",
                checkpoint_id="chk_456",
                seen_fingerprints=seen,
            )

    def test_check_duplicate_replay_allows_new(self) -> None:
        resolver = ReplayConflictResolver()
        seen = set()
        is_dup = resolver.check_duplicate_replay(
            run_id="run_123",
            tenant_id="tenant_a",
            checkpoint_id="chk_456",
            seen_fingerprints=seen,
        )
        assert is_dup is False
