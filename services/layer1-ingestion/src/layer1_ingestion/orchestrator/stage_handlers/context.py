"""Execution context for a single pipeline stage.

Bridges the handler's test-friendly ``handle(ctx)`` interface with the
pipeline's ``execute(db, coordinator, run, step)`` interface.
"""

from __future__ import annotations

from typing import Any

from sqlalchemy.orm import Session

from layer1_ingestion.domain.stages import IngestionStage
from layer1_ingestion.orchestrator.coordinator import PipelineCoordinator
from layer1_ingestion.shared.models import (
    IngestionRunStatus,
    IngestionRunStep,
    SourceIngestionRun,
)


class StageResult:
    """Outcome of a single stage execution."""

    def __init__(
        self,
        status: str,
        next_stage: str | None = None,
        error_code: str | None = None,
        error_detail_safe: str | None = None,
    ) -> None:
        self.status = status
        self.next_stage = next_stage
        self.error_code = error_code
        self.error_detail_safe = error_detail_safe


class StageContext:
    """Wraps a stage execution with a uniform, auditable, tenant-scoped interface."""

    def __init__(
        self,
        *,
        tenant_id: Any,
        account_id: Any,
        source: Any,
        source_version: Any,
        step: IngestionRunStep,
        run: SourceIngestionRun,
        coordinator: PipelineCoordinator,
        db: Session,
        artifacts: dict[str, Any] | None = None,
    ) -> None:
        self.tenant_id = tenant_id
        self.account_id = account_id
        self.source = source
        self.source_version = source_version
        self.step = step
        self.run = run
        self.coordinator = coordinator
        self.db = db
        self._artifacts: dict[str, Any] = artifacts or {}
        self._output_artifacts: dict[str, Any] = {}
        self.scratchpad: dict[str, Any] = {}
        self.permanent_store: str | None = None

    def get_step_artifact(self, name: str) -> Any | None:
        """Return an input artifact by name."""
        return self._artifacts.get(name)

    def persist_step_artifact(self, name: str, payload: Any) -> None:
        """Persist an output artifact for the current stage."""
        self._output_artifacts[name] = payload

    def set_scratchpad(self, key: str, value: Any) -> None:
        """Store transient worker-local data."""
        self.scratchpad[key] = value

    def get_scratchpad(self, key: str) -> Any | None:
        """Retrieve transient worker-local data."""
        return self.scratchpad.get(key)

    def clear_scratchpad(self, key: str | None = None) -> None:
        """Clear a single scratchpad key, or the entire scratchpad."""
        if key:
            self.scratchpad.pop(key, None)
        else:
            self.scratchpad.clear()

    def save_permanent_document(self, text: str) -> None:
        """Record that the processed text has been written to permanent storage.

        For full-custody sources, the downstream normalizer/persistence layer
        is responsible for durable storage; the context keeps the reference
        artifact so the audit trail is complete.
        """
        self.permanent_store = text
        self._output_artifacts["permanent_document"] = text

    def fail_permanent(self, error_code: str, error_detail_safe: str) -> str:
        """Fail the current step permanently and advance to FAILED_PERMANENT."""
        self.coordinator.mark_step_failed(self.step, error_code, error_detail_safe)
        self.coordinator.advance(
            self.run,
            IngestionRunStatus.FAILED_PERMANENT.value,
            error_code=error_code,
            error_detail_safe=error_detail_safe,
        )
        return "FAILED_PERMANENT"

    def fail_transient(self, error_code: str, error_detail_safe: str) -> str:
        """Fail the current step transiently and advance to FAILED_RETRYABLE."""
        self.coordinator.mark_step_failed(self.step, error_code, error_detail_safe)
        self.coordinator.advance(
            self.run,
            IngestionRunStatus.FAILED_RETRYABLE.value,
            error_code=error_code,
            error_detail_safe=error_detail_safe,
        )
        return "FAILED_TRANSIENT"

    def advance(self, target_status: IngestionStage | str) -> str:
        """Complete the current step and advance the run to the target stage."""
        target = target_status.value if isinstance(target_status, IngestionStage) else target_status
        self.coordinator.advance(
            self.run,
            target,
            output_artifact_ids=self._output_artifacts,
        )
        return "ADVANCED"


def _flatten_artifact_ids(nested: dict[str, Any] | None) -> dict[str, Any]:
    """Flatten the nested input artifact map into a single artifact dictionary.

    The coordinator stores previous-step output as either ``{stage_name: {...}}``
    (a stage-output group) or ``{artifact_name: {...}}`` (a direct artifact). This
    helper normalizes both shapes without stripping direct artifact payloads.
    """
    if not nested:
        return {}
    flat: dict[str, Any] = {}
    for key, value in nested.items():
        if isinstance(value, dict) and value and all(isinstance(v, dict) for v in value.values()):
            # Stage-output group: flatten the inner artifact names up one level.
            for inner_key, inner_value in value.items():
                flat[inner_key] = inner_value
        else:
            # Direct artifact payload (leaf data, string, or empty dict).
            flat[key] = value
    return flat
