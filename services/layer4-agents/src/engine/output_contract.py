"""Canonical output-envelope contract validation for workflow finalization."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field, ValidationError

from ..models.agent_state import AgentState


class OutputEnvelopeValidationResult(BaseModel):
    schema_name: str
    schema_version: str
    valid: bool
    errors: list[str] = Field(default_factory=list)


class CanonicalOutputEnvelopeV1(BaseModel):
    """Canonical executor-level output envelope."""

    schema_ref: str
    schema_version: str
    workflow_type: str
    reasoning_trace: dict[str, Any]
    payload: dict[str, Any]


_SCHEMA_MAP: dict[str, tuple[str, str]] = {
    "roi_calculator": ("roi_calculator_output_envelope", "1.0.0"),
    "whitespace_analysis": ("whitespace_analysis_output_envelope", "1.0.0"),
    "business_case": ("business_case_output_envelope", "1.0.0"),
}


def resolve_output_schema(workflow_type: str) -> tuple[str, str]:
    return _SCHEMA_MAP.get(workflow_type, (f"{workflow_type}_output_envelope", "1.0.0"))


def validate_final_output(state: AgentState) -> OutputEnvelopeValidationResult:
    schema_name, schema_version = resolve_output_schema(state.workflow_type.value)
    envelope = {
        "schema_ref": schema_name,
        "schema_version": schema_version,
        "workflow_type": state.workflow_type.value,
        "reasoning_trace": state.reasoning_trace.model_dump(mode="json") if state.reasoning_trace else None,
        "payload": state.output_data or {},
    }
    try:
        CanonicalOutputEnvelopeV1.model_validate(envelope)
        return OutputEnvelopeValidationResult(
            schema_name=schema_name,
            schema_version=schema_version,
            valid=True,
            errors=[],
        )
    except ValidationError as exc:
        return OutputEnvelopeValidationResult(
            schema_name=schema_name,
            schema_version=schema_version,
            valid=False,
            errors=[f"{'.'.join(str(x) for x in err['loc'])}: {err['msg']}" for err in exc.errors()],
        )

