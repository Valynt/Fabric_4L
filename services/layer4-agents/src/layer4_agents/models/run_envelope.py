from __future__ import annotations

"""Canonical run envelope for uniform run identity across Layer 4 surfaces.

Provides a single, explicit run-ID contract enforced across all workflow types,
logs, checkpoints, and output envelopes. run_id is distinct from workflow_id.
"""


from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RunEnvelope(BaseModel):
    """Canonical run envelope with distinct IDs for lifecycle tracking.

    Invariants:
      - run_id is distinct from workflow_id (they may coincidentally share
        a value for simple cases, but must be generated separately).
      - tenant_id is always present and non-empty.
      - trace_id is always present and non-empty.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    run_id: str = Field(..., description="Distinct UUID per workflow execution")
    workflow_id: str = Field(..., description="Stable workflow instance ID")
    trace_id: str = Field(..., description="Cross-layer audit trace ID")
    checkpoint_id: str | None = Field(
        default=None, description="Last known checkpoint identifier"
    )
    tenant_id: str = Field(..., description="Owning tenant")
    workflow_type: str = Field(..., description="Workflow type identifier")

    @field_validator("tenant_id")
    @classmethod
    def _tenant_id_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tenant_id is required and must be non-empty")
        return v

    @field_validator("run_id", "workflow_id", "trace_id")
    @classmethod
    def _id_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("run_id, workflow_id, and trace_id are required")
        return v

    def with_checkpoint(self, checkpoint_id: str | None) -> RunEnvelope:
        """Return a new envelope with updated checkpoint_id."""
        return self.model_copy(update={"checkpoint_id": checkpoint_id})

    def to_log_context(self) -> dict[str, Any]:
        """Flatten to dict for structured logging."""
        return {
            "run_id": self.run_id,
            "workflow_id": self.workflow_id,
            "trace_id": self.trace_id,
            "checkpoint_id": self.checkpoint_id,
            "tenant_id": self.tenant_id,
            "workflow_type": self.workflow_type,
        }
