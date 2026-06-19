"""No-op stage handler for the initial pipeline skeleton.

Marks the step running, immediately completes it, and advances the run to the
next happy-path state.  Concrete handlers will replace this registration.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from ..coordinator import PipelineCoordinator
from ..state_machine import PipelineStateMachine
from .base import StageHandler


class NoopStageHandler(StageHandler):
    """No-op handler that walks the happy path without doing real work."""

    def execute(
        self,
        db: Session,
        coordinator: PipelineCoordinator,
        run: Any,
        step: Any,
    ) -> None:
        coordinator.mark_step_running(step)
        output_artifacts = {"noop": True, "stage": step.stage_name}
        coordinator.mark_step_completed(step, output_artifacts)

        next_state = PipelineStateMachine.next_happy_state(step.stage_name)
        if next_state is None:
            # Terminal state reached (should not happen with current happy path).
            return

        coordinator.advance(
            run,
            next_state,
            output_artifact_ids={step.stage_name: output_artifacts},
        )
