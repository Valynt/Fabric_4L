"""Pydantic request/response models for the Harness FastAPI routes.

These models are the API contract layer — they are separate from the domain
models in harness.models so that API shape changes don't require domain model
changes and vice versa.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

from .models import (
    ActionClass,
    ClaimValidationResult,
    GateStatus,
    GateType,
    HarnessCheckpoint,
    HarnessRun,
    HarnessRunStatus,
    HarnessState,
    HarnessTraceEvent,
    HarnessWorkflowType,
    HumanGate,
    InitiatedBy,
    ValidationState,
    ValidationSummary,
)

# ---------------------------------------------------------------------------
# Run management
# ---------------------------------------------------------------------------


class CreateRunRequest(BaseModel):
    """Request body for POST /v1/harness/runs."""

    model_config = ConfigDict(extra="forbid")

    workflow_type: HarnessWorkflowType
    initiated_by: InitiatedBy = InitiatedBy.USER
    account_id: str | None = None
    value_pack_id: str | None = None


class RunResponse(BaseModel):
    """Single run in API responses."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    account_id: str | None
    workflow_type: HarnessWorkflowType
    initiated_by: InitiatedBy
    status: HarnessRunStatus
    current_state: HarnessState
    value_pack_id: str | None
    trace_id: str
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_domain(cls, run: HarnessRun) -> RunResponse:
        return cls(**run.model_dump())


class RunListResponse(BaseModel):
    """Paginated list of runs."""

    model_config = ConfigDict(extra="forbid")

    items: list[RunResponse]
    total: int
    limit: int
    offset: int
    has_more: bool


class TransitionRequest(BaseModel):
    """Request body for POST /v1/harness/runs/{run_id}/transition."""

    model_config = ConfigDict(extra="forbid")

    to_state: HarnessState
    human_override: bool = False
    state_payload: dict[str, Any] = Field(default_factory=dict)
    validation_results: list[ClaimValidationResult] | None = None


class TransitionResponse(BaseModel):
    """Response for a successful state transition."""

    model_config = ConfigDict(extra="forbid")

    run: RunResponse
    trace_event: TraceEventResponse | None = None


# ---------------------------------------------------------------------------
# Checkpoints
# ---------------------------------------------------------------------------


class CheckpointResponse(BaseModel):
    """Single checkpoint in API responses."""

    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    tenant_id: str
    state_name: HarnessState
    input_hash: str
    output_hash: str | None
    created_at: datetime

    @classmethod
    def from_domain(cls, chk: HarnessCheckpoint) -> CheckpointResponse:
        return cls(
            id=chk.id,
            run_id=chk.run_id,
            tenant_id=chk.tenant_id,
            state_name=chk.state_name,
            input_hash=chk.input_hash,
            output_hash=chk.output_hash,
            created_at=chk.created_at,
        )


class CheckpointListResponse(BaseModel):
    """List of checkpoints for a run."""

    model_config = ConfigDict(extra="forbid")

    items: list[CheckpointResponse]
    total: int


# ---------------------------------------------------------------------------
# Human gates
# ---------------------------------------------------------------------------


class CreateGateRequest(BaseModel):
    """Request body for POST /v1/harness/runs/{run_id}/gates."""

    model_config = ConfigDict(extra="forbid")

    gate_type: GateType
    action_class: ActionClass | None = None


class GateResponse(BaseModel):
    """Single gate in API responses."""

    model_config = ConfigDict(extra="forbid")

    id: str
    run_id: str
    tenant_id: str
    gate_type: GateType
    status: GateStatus
    decision_by: str | None
    decision_reason: str | None
    created_at: datetime
    decided_at: datetime | None

    @classmethod
    def from_domain(cls, gate: HumanGate) -> GateResponse:
        return cls(**gate.model_dump())


class GateListResponse(BaseModel):
    """List of gates for a run."""

    model_config = ConfigDict(extra="forbid")

    items: list[GateResponse]
    total: int


class GateDecisionRequest(BaseModel):
    """Request body for POST /v1/harness/gates/{gate_id}/decide."""

    model_config = ConfigDict(extra="forbid")

    decision: Literal["approved", "rejected", "modified", "expired"]
    decision_reason: str | None = None


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class ClaimValidationRequest(BaseModel):
    """A single claim to validate."""

    model_config = ConfigDict(extra="forbid")

    claim_id: str
    claim_text: str
    evidence_refs: list[str] = Field(default_factory=list)
    value_pack_id: str | None = None
    account_id: str | None = None


class ValidateClaimsRequest(BaseModel):
    """Request body for POST /v1/harness/runs/{run_id}/validate."""

    model_config = ConfigDict(extra="forbid")

    claims: list[ClaimValidationRequest]


class ValidationResultResponse(BaseModel):
    """Single validation result in API responses."""

    model_config = ConfigDict(extra="forbid")

    id: str
    tenant_id: str
    claim_id: str
    validation_state: ValidationState
    evidence_refs: list[str]
    confidence: float
    trust_score: float
    validator: str
    reason: str
    created_at: datetime

    @classmethod
    def from_domain(cls, result: ClaimValidationResult) -> ValidationResultResponse:
        return cls(**result.model_dump())


class ValidationSummaryResponse(BaseModel):
    """Aggregate publish decision across all validated claims."""

    model_config = ConfigDict(extra="forbid")

    total: int
    passed: int
    failed: int
    needs_review: int
    insufficient_evidence: int
    can_publish: bool
    requires_human_review: bool

    @classmethod
    def from_domain(cls, summary: ValidationSummary) -> ValidationSummaryResponse:
        return cls(**summary.model_dump())


class ValidateClaimsResponse(BaseModel):
    """Response for POST /v1/harness/runs/{run_id}/validate
    and GET /v1/harness/runs/{run_id}/validation."""

    model_config = ConfigDict(extra="forbid")

    results: list[ValidationResultResponse]
    total: int
    passed: int
    failed: int
    needs_review: int
    insufficient_evidence: int
    summary: ValidationSummaryResponse | None = None


# ---------------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------------


class HarnessHealthResponse(BaseModel):
    """Response for GET /v1/harness/health."""

    model_config = ConfigDict(extra="forbid")

    status: Literal["ok", "degraded"]
    validation_available: bool
    l5_healthy: bool
    db_healthy: bool


# ---------------------------------------------------------------------------
# Trace events
# ---------------------------------------------------------------------------


class TraceEventResponse(BaseModel):
    """Trace event emitted on state transitions."""

    model_config = ConfigDict(extra="forbid")

    trace_id: str
    run_id: str
    tenant_id: str
    from_state: HarnessState | None
    to_state: HarnessState | None
    event_type: str
    timestamp: datetime

    @classmethod
    def from_domain(cls, event: HarnessTraceEvent) -> TraceEventResponse:
        return cls(
            trace_id=event.trace_id,
            run_id=event.run_id,
            tenant_id=event.tenant_id,
            from_state=event.from_state,
            to_state=event.to_state,
            event_type=event.event_type,
            timestamp=event.timestamp,
        )


# Resolve forward reference
TransitionResponse.model_rebuild()
