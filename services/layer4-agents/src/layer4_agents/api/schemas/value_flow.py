from __future__ import annotations

"""Schemas for the UI-oriented value flow facade API."""


from datetime import UTC, datetime
from enum import Enum
from typing import Any

from pydantic import BaseModel, Field


class ValueFlowStep(str, Enum):
    """Supported UI workflow steps."""

    setup = "setup"
    intelligence = "intelligence"
    model = "model"
    validation = "validation"
    completion = "completion"


class StepStatePayload(BaseModel):
    """Opaque step state payload stored for save/resume."""

    data: dict[str, Any] = Field(default_factory=dict)


class StepStateRequest(BaseModel):
    """Request to save or update a step state."""

    flow_instance_id: str = Field(..., min_length=3)
    step: ValueFlowStep
    state: StepStatePayload
    idempotency_key: str | None = Field(
        default=None,
        description="Optional client key for retry-safe state saves",
    )


class StepStateResponse(BaseModel):
    """Response for saved or loaded step state."""

    flow_instance_id: str
    step: ValueFlowStep
    saved: bool
    resumed: bool
    state: StepStatePayload
    updated_at: str


class ConfirmationActionRequest(BaseModel):
    """Action payload for explicit user confirmations."""

    flow_instance_id: str = Field(..., min_length=3)
    step: ValueFlowStep
    action: str = Field(..., description="confirm, reject, or request_changes")
    rationale: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ConfirmationActionResponse(BaseModel):
    """Response after processing a confirmation action."""

    flow_instance_id: str
    step: ValueFlowStep
    action: str
    accepted: bool
    message: str
    next_step: ValueFlowStep | None = None


class CompletionStatusResponse(BaseModel):
    """Top-level completion status for durable UI navigation."""

    flow_instance_id: str
    current_step: ValueFlowStep
    completed_steps: list[ValueFlowStep]
    is_complete: bool
    last_updated_at: str


def now_iso() -> str:
    """Current UTC time in ISO format."""
    return datetime.now(UTC).isoformat()
