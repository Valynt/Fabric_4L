"""Structured reasoning trace schema for Layer 4 workflow outputs.

Enforces a guaranteed, schema-validated reasoning trace with required fields
(inputs/tools/evidence/assumptions/confidence/output object IDs) for every
agent output.
"""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ToolCallTrace(BaseModel):
    """Record of a single tool invocation within a workflow."""

    model_config = ConfigDict(frozen=True)

    tool_name: str
    invocation_id: str
    timestamp: str = Field(default_factory=lambda: datetime.now(UTC).isoformat())
    input_summary: dict[str, Any] = Field(default_factory=dict)
    output_summary: dict[str, Any] = Field(default_factory=dict)


class ReasoningTrace(BaseModel):
    """Canonical reasoning trace attached to every workflow output.

    Invariants:
      - All required list fields must be non-empty for a completed workflow.
      - confidence must be in [0.0, 1.0].
      - run_id and trace_id must match the parent workflow's envelope.
    """

    model_config = ConfigDict(frozen=False, extra="forbid")

    inputs_used: list[str] = Field(
        default_factory=list,
        description="Keys from input_data that were consumed by the workflow",
    )
    tools_called: list[ToolCallTrace] = Field(
        default_factory=list,
        description="Tool invocations executed during the workflow",
    )
    evidence_considered: list[str] = Field(
        default_factory=list,
        description="Evidence IDs or references considered during reasoning",
    )
    assumptions: list[str] = Field(
        default_factory=list,
        description="Explicit assumptions made during reasoning",
    )
    confidence: float = Field(
        default=0.0,
        ge=0.0,
        le=1.0,
        description="Confidence score for the output (0.0–1.0)",
    )
    output_object_ids: list[str] = Field(
        default_factory=list,
        description="IDs of generated artifacts / output objects",
    )
    run_id: str = Field(..., description="Parent workflow run_id")
    trace_id: str = Field(..., description="Cross-layer audit trace_id")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("confidence")
    @classmethod
    def _confidence_in_range(cls, v: float) -> float:
        if not 0.0 <= v <= 1.0:
            raise ValueError("confidence must be between 0.0 and 1.0")
        return v

    @field_validator("inputs_used", "evidence_considered", "assumptions", "output_object_ids")
    @classmethod
    def _lists_are_strings(cls, v: list[Any]) -> list[Any]:
        return v


def validate_reasoning_trace(trace: ReasoningTrace | None, *, strict: bool = True) -> None:
    """Validate that a reasoning trace meets the hardened contract.

    Args:
        trace: The reasoning trace to validate.
        strict: If True, requires all list fields to be non-empty.

    Raises:
        ValueError: If the trace is missing or violates contract invariants.
    """
    if trace is None:
        raise ValueError("REASONING_TRACE_MISSING: reasoning trace is required")

    if strict:
        missing_fields: list[str] = []
        if not trace.inputs_used:
            missing_fields.append("inputs_used")
        if not trace.tools_called:
            missing_fields.append("tools_called")
        if not trace.evidence_considered:
            missing_fields.append("evidence_considered")
        if not trace.assumptions:
            missing_fields.append("assumptions")
        if not trace.output_object_ids:
            missing_fields.append("output_object_ids")

        if missing_fields:
            raise ValueError(
                f"REASONING_TRACE_INVALID: missing required fields: {', '.join(missing_fields)}"
            )

    if trace.confidence < 0.0 or trace.confidence > 1.0:
        raise ValueError(
            f"REASONING_TRACE_INVALID: confidence {trace.confidence} out of range [0.0, 1.0]"
        )
