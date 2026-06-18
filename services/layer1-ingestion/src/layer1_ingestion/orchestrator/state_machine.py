"""Deterministic state machine for source ingestion pipeline runs.

Enforces the stage transitions from the Fabric_4L design brief and maps every
run state to a terminal or non-terminal disposition.
"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Final

from layer1_ingestion.shared.models import IngestionRunStatus


class TransitionError(ValueError):
    """Raised when a pipeline stage transition is invalid."""

    pass


class TerminalStateError(TransitionError):
    """Raised when a transition is requested from a terminal state."""

    pass


class PipelineStateMachine:
    """Deterministic state machine for SourceIngestionRun lifecycle.

    Valid transitions follow the canonical pipeline:
    ACCEPTED → VALIDATING → STORED → NORMALIZING → CHUNKING
    → READY_FOR_EXTRACTION → EXTRACTING → REFINING → GRAPH_COMMITTING
    → SYNTHESIZING → VALIDATING_CLAIMS → APPLYING_POLICY → READY

    Any non-terminal state may transition to NEEDS_INPUT, NEEDS_REVIEW,
    FAILED_RETRYABLE, FAILED_PERMANENT, or CANCELLED.
    """

    _TRANSITIONS: Final[dict[str, set[str]]] = {
        IngestionRunStatus.ACCEPTED.value: {
            IngestionRunStatus.VALIDATING.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.VALIDATING.value: {
            IngestionRunStatus.STORED.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.STORED.value: {
            IngestionRunStatus.NORMALIZING.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.NORMALIZING.value: {
            IngestionRunStatus.CHUNKING.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.CHUNKING.value: {
            IngestionRunStatus.READY_FOR_EXTRACTION.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.READY_FOR_EXTRACTION.value: {
            IngestionRunStatus.EXTRACTING.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.EXTRACTING.value: {
            IngestionRunStatus.REFINING.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.REFINING.value: {
            IngestionRunStatus.GRAPH_COMMITTING.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.GRAPH_COMMITTING.value: {
            IngestionRunStatus.SYNTHESIZING.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.SYNTHESIZING.value: {
            IngestionRunStatus.VALIDATING_CLAIMS.value,
            IngestionRunStatus.NEEDS_REVIEW.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.VALIDATING_CLAIMS.value: {
            IngestionRunStatus.APPLYING_POLICY.value,
            IngestionRunStatus.NEEDS_REVIEW.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.APPLYING_POLICY.value: {
            IngestionRunStatus.READY.value,
            IngestionRunStatus.NEEDS_REVIEW.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.NEEDS_INPUT.value: {
            IngestionRunStatus.NORMALIZING.value,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.NEEDS_REVIEW.value: {
            IngestionRunStatus.APPLYING_POLICY.value,
            IngestionRunStatus.SYNTHESIZING.value,
            IngestionRunStatus.FAILED_PERMANENT.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.FAILED_RETRYABLE.value: {
            IngestionRunStatus.NORMALIZING.value,
            IngestionRunStatus.READY_FOR_EXTRACTION.value,
            IngestionRunStatus.EXTRACTING.value,
            IngestionRunStatus.REFINING.value,
            IngestionRunStatus.GRAPH_COMMITTING.value,
            IngestionRunStatus.SYNTHESIZING.value,
            IngestionRunStatus.VALIDATING_CLAIMS.value,
            IngestionRunStatus.APPLYING_POLICY.value,
            IngestionRunStatus.CANCELLED.value,
        },
        IngestionRunStatus.READY.value: set(),
        IngestionRunStatus.FAILED_PERMANENT.value: set(),
        IngestionRunStatus.CANCELLED.value: set(),
        IngestionRunStatus.SUPERSEDED.value: set(),
    }

    _TERMINAL_STATES: Final[set[str]] = {
        IngestionRunStatus.READY.value,
        IngestionRunStatus.FAILED_PERMANENT.value,
        IngestionRunStatus.CANCELLED.value,
        IngestionRunStatus.SUPERSEDED.value,
    }

    _HAPPY_PATH: Final[Sequence[str]] = (
        IngestionRunStatus.ACCEPTED.value,
        IngestionRunStatus.VALIDATING.value,
        IngestionRunStatus.STORED.value,
        IngestionRunStatus.NORMALIZING.value,
        IngestionRunStatus.CHUNKING.value,
        IngestionRunStatus.READY_FOR_EXTRACTION.value,
        IngestionRunStatus.EXTRACTING.value,
        IngestionRunStatus.REFINING.value,
        IngestionRunStatus.GRAPH_COMMITTING.value,
        IngestionRunStatus.SYNTHESIZING.value,
        IngestionRunStatus.VALIDATING_CLAIMS.value,
        IngestionRunStatus.APPLYING_POLICY.value,
        IngestionRunStatus.READY.value,
    )

    @classmethod
    def allowed_transitions(cls, state: str) -> set[str]:
        """Return the set of states reachable from ``state``."""
        return set(cls._TRANSITIONS.get(state, set()))

    @classmethod
    def is_valid_transition(cls, from_state: str, to_state: str) -> bool:
        """Return True if ``from_state`` may transition to ``to_state``."""
        return to_state in cls._TRANSITIONS.get(from_state, set())

    @classmethod
    def is_terminal(cls, state: str) -> bool:
        """Return True if ``state`` is terminal."""
        return state in cls._TERMINAL_STATES

    @classmethod
    def next_happy_state(cls, state: str) -> str | None:
        """Return the next happy-path state after ``state``.

        Returns None if ``state`` is the final happy state or not recognized.
        """
        if state not in cls._HAPPY_PATH:
            return None
        idx = cls._HAPPY_PATH.index(state)
        if idx + 1 >= len(cls._HAPPY_PATH):
            return None
        return cls._HAPPY_PATH[idx + 1]

    def transition(self, from_state: str, to_state: str) -> None:
        """Validate a transition and raise on violation.

        This method is pure; callers update the database row.
        """
        if self.is_terminal(from_state):
            raise TerminalStateError(
                f"Cannot transition from terminal state {from_state!r}"
            )
        allowed = self.allowed_transitions(from_state)
        if to_state not in allowed:
            raise TransitionError(
                f"Invalid transition from {from_state!r} to {to_state!r}. "
                f"Allowed: {sorted(allowed)}"
            )
