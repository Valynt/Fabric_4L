"""Base class for pipeline stage handlers."""

from __future__ import annotations

import uuid
from abc import ABC, abstractmethod
from typing import Any

from sqlalchemy.orm import Session

from layer1_ingestion.shared.models import (
    IngestionRunStep,
    IngestionRunStepStatus,
    SourceIngestionRun,
)

from ..coordinator import PipelineCoordinator


class StageHandler(ABC):
    """Abstract base for a single pipeline stage handler.

    Subclasses must implement ``execute``.  The base class provides helpers for
    loading the run and current step, verifying state, and advancing.
    """

    def run(
        self,
        db: Session,
        coordinator: PipelineCoordinator,
        run_id: uuid.UUID,
        tenant_id: uuid.UUID,
        stage_name: str,
    ) -> None:
        """Execute the stage for ``run_id``.

        This method is the entry point called by Celery workers.
        """
        run = self._load_run(db, run_id, tenant_id)
        step = self._load_step(db, run.current_step_id)
        if step.stage_name != stage_name:
            raise ValueError(
                f"Run {run_id} current step is not {stage_name!r}, got "
                f"{step.stage_name!r}"
            )
        if step.status != IngestionRunStepStatus.PENDING.value:
            raise ValueError(
                f"Step {step.id} is not PENDING, got {step.status}"
            )
        self.execute(db, coordinator, run, step)

    @abstractmethod
    def execute(
        self,
        db: Session,
        coordinator: PipelineCoordinator,
        run: SourceIngestionRun,
        step: IngestionRunStep,
    ) -> None:
        """Perform the stage-specific work and advance the run."""
        raise NotImplementedError

    def _load_run(
        self, db: Session, run_id: uuid.UUID, tenant_id: uuid.UUID
    ) -> SourceIngestionRun:
        run = (
            db.query(SourceIngestionRun)
            .filter(
                SourceIngestionRun.id == run_id,
                SourceIngestionRun.tenant_id == tenant_id,
            )
            .first()
        )
        if run is None:
            raise ValueError(f"Run {run_id} not found for tenant {tenant_id}")
        return run

    def _load_step(
        self, db: Session, step_id: uuid.UUID | None
    ) -> IngestionRunStep:
        if step_id is None:
            raise ValueError("Run has no current step")
        step = db.query(IngestionRunStep).filter(IngestionRunStep.id == step_id).first()
        if step is None:
            raise ValueError(f"Step {step_id} not found")
        return step
