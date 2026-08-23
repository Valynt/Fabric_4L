from __future__ import annotations

"""Unit tests for degradation policy parsing, ladder evaluation, and execution tracking (Pass 1)."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from layer4_agents.models.degradation_policy import (
    DegradationLadderStep,
    DegradationPoliciesConfig,
    DegradationPolicy,
    DegradationRungKind,
    FailoverRungConfig,
    HeuristicRungConfig,
    OutputMarking,
    RetryRungConfig,
)
from layer4_agents.services.degradation_evaluator import (
    DegradationEvaluator,
    DegradationExecutionTracker,
    DegradationPolicyError,
    validate_degradation_runtime_config,
)
from layer4_agents.services.governed_llm_client import GovernedLLMClient


def test_load_default_degradation_policies_from_runtime_yaml() -> None:
    """Test loading and validating the canonical harness.runtime.yaml configuration."""
    config = validate_degradation_runtime_config()
    assert isinstance(config, DegradationPoliciesConfig)
    assert "conversation" in config.policies
    assert "narrative" in config.policies
    assert "reasoning" in config.policies

    conv_policy = config.get_policy("conversation")
    assert conv_policy is not None
    assert conv_policy.output_marking == OutputMarking.REQUIRED
    assert conv_policy.max_retries == 1
    assert conv_policy.has_failover is True
    assert conv_policy.has_heuristic is True
    assert conv_policy.heuristic_id == "chat_deterministic_v1"
    assert len(conv_policy.ladder) == 3


def test_custom_degradation_policy_validation() -> None:
    """Test building and validating a custom DegradationPolicy model."""
    policy = DegradationPolicy(
        ladder=[
            DegradationLadderStep(retry=RetryRungConfig(same_model=2)),
            DegradationLadderStep(failover=FailoverRungConfig(tier="secondary_provider")),
            DegradationLadderStep(heuristic=HeuristicRungConfig(id="custom_heuristic")),
        ],
        output_marking=OutputMarking.OPTIONAL,
    )
    assert policy.max_retries == 2
    assert policy.has_failover is True
    assert policy.has_heuristic is True
    assert policy.heuristic_id == "custom_heuristic"
    assert policy.output_marking == OutputMarking.OPTIONAL


def test_degradation_tracker_primary_success() -> None:
    """Test DegradationExecutionTracker when primary tier succeeds on first attempt."""
    policy = DegradationPolicy(
        ladder=[
            DegradationLadderStep(retry=RetryRungConfig(same_model=1)),
            DegradationLadderStep(heuristic=HeuristicRungConfig(id="heuristic_handler")),
        ],
        output_marking=OutputMarking.REQUIRED,
    )
    tracker = DegradationExecutionTracker(
        task_name="conversation",
        policy=policy,
        tenant_id="tenant-alpha",
        trace_id="trace-123",
        workflow_id="wf-456",
    )

    tracker.record_attempt()
    tracker.record_success(tier="primary", provider="anthropic", model="claude-3-5-sonnet")

    assert tracker.is_degraded is False
    assert tracker.degradation_reason is None
    assert tracker.failed_tiers == []

    metadata = tracker.build_generation_metadata()
    assert metadata["response_tier"] == "primary"
    assert metadata["provider"] == "anthropic"
    assert metadata["fallback"] is False
    assert metadata["degraded"] is False
    assert metadata["degradation_reason"] is None


def test_degradation_tracker_fallback_applied() -> None:
    """Test DegradationExecutionTracker when primary fails and heuristic fallback is recorded."""
    policy = DegradationPolicy(
        ladder=[
            DegradationLadderStep(retry=RetryRungConfig(same_model=1)),
            DegradationLadderStep(heuristic=HeuristicRungConfig(id="heuristic_handler")),
        ],
        output_marking=OutputMarking.REQUIRED,
    )
    tracker = DegradationExecutionTracker(
        task_name="conversation",
        policy=policy,
        tenant_id="tenant-alpha",
        trace_id="trace-123",
        workflow_id="wf-456",
    )

    tracker.record_attempt()
    tracker.record_failure(
        rung_kind=DegradationRungKind.RETRY,
        tier="primary",
        reason="rate_limit_exceeded",
        exc=RuntimeError("HTTP 429"),
    )
    tracker.record_failure(
        rung_kind=DegradationRungKind.FAILOVER,
        tier="thesys_c1",
        reason="thesys_c1_failed",
    )
    tracker.record_success(tier="heuristic")

    assert tracker.is_degraded is True
    assert "rate_limit_exceeded" in tracker.degradation_reason
    assert "thesys_c1_failed" in tracker.degradation_reason
    assert tracker.failed_tiers == ["primary", "thesys_c1"]

    metadata = tracker.build_generation_metadata()
    assert metadata["response_tier"] == "heuristic"
    assert metadata["fallback"] is True
    assert metadata["degraded"] is True
    assert metadata["degradation_reason"] == "rate_limit_exceeded,thesys_c1_failed"

    audit_details = tracker.build_audit_details()
    assert audit_details["event_type"] == "llm_degradation_applied"
    assert audit_details["tenant_id"] == "tenant-alpha"
    assert audit_details["trace_id"] == "trace-123"
    assert audit_details["run_id"] == "wf-456"
    assert audit_details["selected_tier"] == "heuristic"
    assert audit_details["degraded"] is True


@pytest.mark.asyncio
async def test_evaluator_executes_primary_action_successfully() -> None:
    """Test that DegradationEvaluator executes primary action without invoking fallbacks."""
    evaluator = DegradationEvaluator(task_name="conversation")
    primary_mock = AsyncMock(return_value="primary_success")
    fallback_mock = AsyncMock(return_value="fallback_result")

    result, tracker = await evaluator.execute_cascade(
        primary_fn=primary_mock,
        heuristic_fn=fallback_mock,
        tenant_id="tenant-1",
    )

    assert result == "primary_success"
    assert primary_mock.await_count == 1
    assert fallback_mock.await_count == 0
    assert tracker.is_degraded is False
    assert tracker.selected_tier == "primary"


@pytest.mark.asyncio
async def test_evaluator_retries_and_falls_back_on_failure() -> None:
    """Test that DegradationEvaluator retries primary and invokes fallback upon exhaustion."""
    evaluator = DegradationEvaluator(task_name="conversation")
    primary_mock = AsyncMock(side_effect=RuntimeError("Upstream timeout"))
    fallback_mock = AsyncMock(return_value="safe_fallback_content")

    result, tracker = await evaluator.execute_cascade(
        primary_fn=primary_mock,
        heuristic_fn=fallback_mock,
        tenant_id="tenant-1",
    )

    assert result == "safe_fallback_content"
    # conversation configured with same_model: 1 in harness.runtime.yaml -> 1 retry attempt
    assert primary_mock.await_count == 1
    assert fallback_mock.await_count == 1
    assert tracker.is_degraded is True
    assert tracker.selected_tier == "heuristic"


@pytest.mark.asyncio
async def test_evaluator_raises_when_no_fallback_allowed() -> None:
    """Test that DegradationEvaluator raises DegradationPolicyError if fallback is not available."""
    policy = DegradationPolicy(
        ladder=[
            DegradationLadderStep(retry=RetryRungConfig(same_model=1)),
        ],
        output_marking=OutputMarking.NONE,
    )
    evaluator = DegradationEvaluator(policy=policy, task_name="strict_task")

    primary_mock = AsyncMock(side_effect=ValueError("Invalid output"))

    with pytest.raises(DegradationPolicyError) as exc_info:
        await evaluator.execute_cascade(
            primary_fn=primary_mock,
            tenant_id="tenant-1",
        )

    assert "strict_task" in str(exc_info.value)


def test_governed_llm_client_resolves_policy_and_retries() -> None:
    """Test GovernedLLMClient initializes degradation config and respects policy retry and attempt counts."""
    mock_provider = MagicMock()
    client = GovernedLLMClient(provider=mock_provider, provider_name="together")
    assert client.degradation_policies is not None

    policy = client.degradation_policies.get_policy("reasoning")
    assert policy is not None
    assert policy.output_marking == OutputMarking.REQUIRED

    max_retries = client.get_max_retries_for_task("reasoning")
    assert max_retries == 3
    max_attempts = client.get_max_attempts_for_task("reasoning")
    assert max_attempts == 4

    # Conversation has 1 retry -> 2 total attempts (initial + 1 retry)
    assert client.get_max_retries_for_task("conversation") == 1
    assert client.get_max_attempts_for_task("conversation") == 2

    # Unknown task returns default max retries of 2 (max_attempts 3 - 1) from llm.retry.max_attempts
    default_retries = client.get_max_retries_for_task("nonexistent_task")
    assert default_retries == 2
    default_attempts = client.get_max_attempts_for_task("nonexistent_task")
    assert default_attempts == 3

