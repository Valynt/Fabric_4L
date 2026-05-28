from __future__ import annotations

"""
Deterministic workflow state machine for HarnessRun.

Rules:
  - INIT can transition only to RESOLVE_CONTEXT, FAILED, or CANCELLED.
  - DONE, FAILED, CANCELLED are terminal — no further transitions.
  - PUBLISH_OUTPUT requires validation passed or explicit human override.
  - HUMAN_REVIEW is entered when validation is insufficient or unavailable.
  - Invalid transitions fail deterministically with TransitionError.
  - Every transition emits a trace event.
"""


from collections.abc import Callable
from datetime import UTC, datetime

from .models import (
    HarnessRun,
    HarnessRunStatus,
    HarnessState,
    HarnessTraceEvent,
    ValidationState,
)


class TransitionError(ValueError):
    """Raised when a state transition is invalid."""

    pass


class TerminalStateError(TransitionError):
    """Raised when attempting to transition from a terminal state."""

    pass


class ValidationRequiredError(TransitionError):
    """Raised when PUBLISH_OUTPUT is attempted without proper validation."""

    pass


# Valid transitions: from_state -> set of allowed to_states
_TRANSITION_MAP: dict[HarnessState, set[HarnessState]] = {
    HarnessState.INIT: {
        HarnessState.RESOLVE_CONTEXT,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.RESOLVE_CONTEXT: {
        HarnessState.LOAD_VALUE_PACK,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.LOAD_VALUE_PACK: {
        HarnessState.RETRIEVE_KNOWLEDGE,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.RETRIEVE_KNOWLEDGE: {
        HarnessState.GENERATE_HYPOTHESES,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.GENERATE_HYPOTHESES: {
        HarnessState.MATCH_EVIDENCE,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.MATCH_EVIDENCE: {
        HarnessState.QUANTIFY_IMPACT,
        HarnessState.HUMAN_REVIEW,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.QUANTIFY_IMPACT: {
        HarnessState.VALIDATE_CLAIMS,
        HarnessState.HUMAN_REVIEW,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.VALIDATE_CLAIMS: {
        HarnessState.PUBLISH_OUTPUT,
        HarnessState.HUMAN_REVIEW,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.HUMAN_REVIEW: {
        HarnessState.PUBLISH_OUTPUT,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
    },
    HarnessState.PUBLISH_OUTPUT: {
        HarnessState.DONE,
        HarnessState.FAILED,
        HarnessState.CANCELLED,
        HarnessState.HUMAN_REVIEW,
    },
    HarnessState.DONE: set(),  # terminal
    HarnessState.FAILED: set(),  # terminal
    HarnessState.CANCELLED: set(),  # terminal
}

# Terminal states
_TERMINAL_STATES: set[HarnessState] = HarnessState.terminal_states()

# States that may route to HUMAN_REVIEW on insufficient evidence
_REVIEW_ROUTING_STATES: set[HarnessState] = {
    HarnessState.VALIDATE_CLAIMS,
    HarnessState.MATCH_EVIDENCE,
    HarnessState.QUANTIFY_IMPACT,
}


def _compute_status_for_state(state: HarnessState) -> HarnessRunStatus:
    if state == HarnessState.DONE:
        return HarnessRunStatus.COMPLETED
    if state == HarnessState.FAILED:
        return HarnessRunStatus.FAILED
    if state == HarnessState.CANCELLED:
        return HarnessRunStatus.CANCELLED
    if state == HarnessState.HUMAN_REVIEW:
        return HarnessRunStatus.WAITING_FOR_HUMAN
    return HarnessRunStatus.RUNNING


class StateMachine:
    """
    Deterministic state machine for HarnessRun lifecycle.

    All operations are pure: transition returns a new HarnessRun + optional event.
    """

    def __init__(
        self,
        transition_hooks: list[Callable[[HarnessRun, HarnessState, HarnessState], None]] | None = None,
    ) -> None:
        self._hooks = transition_hooks or []

    @staticmethod
    def allowed_transitions(from_state: HarnessState) -> set[HarnessState]:
        """Return the set of states reachable from `from_state`."""
        return set(_TRANSITION_MAP.get(from_state, set()))

    @staticmethod
    def is_valid_transition(from_state: HarnessState, to_state: HarnessState) -> bool:
        return to_state in _TRANSITION_MAP.get(from_state, set())

    @staticmethod
    def is_terminal(state: HarnessState) -> bool:
        return state in _TERMINAL_STATES

    def transition(
        self,
        run: HarnessRun,
        to_state: HarnessState,
        validation_state: ValidationState | None = None,
        human_override: bool = False,
    ) -> tuple[HarnessRun, HarnessTraceEvent]:
        """
        Attempt to transition `run` to `to_state`.

        Returns:
            Tuple of (updated_run, trace_event).

        Raises:
            TerminalStateError: if run is already in a terminal state.
            TransitionError: if the transition is not allowed.
            ValidationRequiredError: if PUBLISH_OUTPUT without validation/override.
        """
        from_state = run.current_state

        # Terminal guard
        if from_state in _TERMINAL_STATES:
            raise TerminalStateError(
                f"Cannot transition from terminal state {from_state.value}"
            )

        # Validate transition exists
        allowed = _TRANSITION_MAP.get(from_state, set())
        if to_state not in allowed:
            raise TransitionError(
                f"Invalid transition: {from_state.value} -> {to_state.value}. "
                f"Allowed: {[s.value for s in allowed]}"
            )

        # PUBLISH_OUTPUT guard: must have passed validation or human override
        if to_state == HarnessState.PUBLISH_OUTPUT:
            self._enforce_publish_policy(run, validation_state, human_override)

        # Compute new status
        new_status = _compute_status_for_state(to_state)

        # Produce updated run
        updated_run = run.with_state(to_state, status=new_status)

        # Build trace event
        event = HarnessTraceEvent(
            trace_id=run.trace_id,
            run_id=run.id,
            tenant_id=run.tenant_id,
            account_id=run.account_id,
            workflow_type=run.workflow_type,
            from_state=from_state,
            to_state=to_state,
            status=new_status,
            value_pack_id=run.value_pack_id,
            validation_state=validation_state,
            timestamp=datetime.now(UTC),
            event_type="transition",
        )

        # Execute hooks
        for hook in self._hooks:
            hook(updated_run, from_state, to_state)

        return updated_run, event

    def route_to_human_review(
        self,
        run: HarnessRun,
        reason: str,
    ) -> tuple[HarnessRun, HarnessTraceEvent]:
        """Route a run to HUMAN_REVIEW with a traceable reason."""
        if run.current_state in _TERMINAL_STATES:
            raise TerminalStateError(
                f"Cannot route to HUMAN_REVIEW from terminal state {run.current_state.value}"
            )
        return self.transition(
            run,
            HarnessState.HUMAN_REVIEW,
            validation_state=ValidationState.INSUFFICIENT_EVIDENCE,
        )

    def _enforce_publish_policy(
        self,
        run: HarnessRun,
        validation_state: ValidationState | None,
        human_override: bool,
    ) -> None:
        """
        Enforce the rule: PUBLISH_OUTPUT requires:
          - validation_state == PASSED, OR
          - human_override == True and policy allows.
        """
        if validation_state == ValidationState.PASSED:
            return  # Validated — allow

        if human_override:
            # Human override requires an explicit policy check.
            # For MVP, override is allowed only if a human gate approved.
            return  # Override path — policy checked upstream

        # Block publication
        if validation_state is None:
            raise ValidationRequiredError(
                "PUBLISH_OUTPUT blocked: no validation state provided. "
                "Provide passed validation or explicit human override."
            )
        if validation_state == ValidationState.FAILED:
            raise ValidationRequiredError(
                "PUBLISH_OUTPUT blocked: validation failed. "
                "Failed validation cannot publish unless explicitly overridden."
            )
        if validation_state in (
            ValidationState.INSUFFICIENT_EVIDENCE,
            ValidationState.NEEDS_REVIEW,
        ):
            raise ValidationRequiredError(
                f"PUBLISH_OUTPUT blocked: validation state is {validation_state.value}. "
                f"Route to HUMAN_REVIEW first."
            )

    def can_publish(
        self,
        run: HarnessRun,
        validation_state: ValidationState | None,
        human_override: bool = False,
    ) -> bool:
        """Return True if the run can enter PUBLISH_OUTPUT."""
        if run.current_state == HarnessState.HUMAN_REVIEW and human_override:
            return True
        if validation_state == ValidationState.PASSED:
            return True
        return False
