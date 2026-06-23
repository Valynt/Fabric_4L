"""Tests for the v3.0 source ingestion state machine."""

from __future__ import annotations

import pytest

from layer1_ingestion.orchestrator.state_machine import PipelineStateMachine
from layer1_ingestion.shared.models import IngestionRunStatus


class TestV3_0HappyPath:
    """Verify the canonical v3.0 happy path."""

    def test_happy_path_sequence(self) -> None:
        expected = [
            IngestionRunStatus.ACCEPTED.value,
            IngestionRunStatus.VALIDATING_ACCESS.value,
            IngestionRunStatus.RESOLVING_CONNECTOR.value,
            IngestionRunStatus.FETCHING_SOURCE.value,
            IngestionRunStatus.APPLYING_POLICY.value,
            IngestionRunStatus.NORMALIZING.value,
            IngestionRunStatus.CHUNKING.value,
            IngestionRunStatus.EXTRACTING.value,
            IngestionRunStatus.BUILDING_CLAIMS.value,
            IngestionRunStatus.VALIDATING_CLAIMS.value,
            IngestionRunStatus.PROJECTING_SUMMARY.value,
            IngestionRunStatus.READY.value,
        ]

        assert PipelineStateMachine._HAPPY_PATH == tuple(expected)

        for current, next_state in zip(expected, expected[1:]):
            assert PipelineStateMachine.is_valid_transition(current, next_state)

    def test_next_happy_state(self) -> None:
        assert PipelineStateMachine.next_happy_state(IngestionRunStatus.ACCEPTED.value) == IngestionRunStatus.VALIDATING_ACCESS.value
        assert PipelineStateMachine.next_happy_state(IngestionRunStatus.PROJECTING_SUMMARY.value) == IngestionRunStatus.READY.value
        assert PipelineStateMachine.next_happy_state(IngestionRunStatus.READY.value) is None


class TestV3_0FailureAndUserAction:
    """Verify failure, cancellation, and user-action transitions."""

    def test_any_non_terminal_may_fail_or_cancel(self) -> None:
        non_terminal = (
            set(PipelineStateMachine._TRANSITIONS)
            - PipelineStateMachine._TERMINAL_STATES
            - {IngestionRunStatus.FAILED_RETRYABLE.value, IngestionRunStatus.CANCELLED.value}
        )
        for state in non_terminal:
            assert PipelineStateMachine.is_valid_transition(state, IngestionRunStatus.FAILED_RETRYABLE.value)
            assert PipelineStateMachine.is_valid_transition(state, IngestionRunStatus.FAILED_PERMANENT.value)
            assert PipelineStateMachine.is_valid_transition(state, IngestionRunStatus.CANCELLED.value)

    def test_building_claims_and_validating_claims_may_need_user_action(self) -> None:
        for state in (
            IngestionRunStatus.BUILDING_CLAIMS.value,
            IngestionRunStatus.VALIDATING_CLAIMS.value,
            IngestionRunStatus.PROJECTING_SUMMARY.value,
        ):
            assert PipelineStateMachine.is_valid_transition(state, IngestionRunStatus.NEEDS_USER_ACTION.value)

    def test_needs_user_action_can_resume(self) -> None:
        assert PipelineStateMachine.is_valid_transition(
            IngestionRunStatus.NEEDS_USER_ACTION.value,
            IngestionRunStatus.APPLYING_POLICY.value,
        )
        assert PipelineStateMachine.is_valid_transition(
            IngestionRunStatus.NEEDS_USER_ACTION.value,
            IngestionRunStatus.BUILDING_CLAIMS.value,
        )

    def test_failed_retryable_can_resume_from_any_stage(self) -> None:
        allowed = PipelineStateMachine.allowed_transitions(IngestionRunStatus.FAILED_RETRYABLE.value)
        for state in PipelineStateMachine._HAPPY_PATH:
            if state not in {IngestionRunStatus.ACCEPTED.value, IngestionRunStatus.READY.value}:
                assert state in allowed, f"FAILED_RETRYABLE should be able to resume to {state}"

    def test_terminal_states_are_terminal(self) -> None:
        for state in PipelineStateMachine._TERMINAL_STATES:
            assert PipelineStateMachine.is_terminal(state)
            assert PipelineStateMachine.allowed_transitions(state) == set()

    def test_no_terminal_to_any_transition(self) -> None:
        with pytest.raises(Exception):
            PipelineStateMachine().transition(
                IngestionRunStatus.READY.value,
                IngestionRunStatus.VALIDATING_ACCESS.value,
            )


class TestV3_0RemovedOldStates:
    """Verify old v2.x states are no longer valid."""

    def test_old_states_not_in_happy_path(self) -> None:
        old_states = {
            "VALIDATING",
            "STORED",
            "READY_FOR_EXTRACTION",
            "REFINING",
            "GRAPH_COMMITTING",
            "SYNTHESIZING",
            "NEEDS_INPUT",
            "NEEDS_REVIEW",
        }
        for state in old_states:
            assert state not in PipelineStateMachine._TRANSITIONS
            assert state not in PipelineStateMachine._HAPPY_PATH
            assert not PipelineStateMachine.is_terminal(state)
