"""
Typed domain models for the Fabric_4L Harness.

All models are immutable Pydantic v2 models. Timestamps use UTC.
IDs are generated deterministically where possible.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, datetime
from enum import Enum
from typing import Any, Literal, Self

from pydantic import BaseModel, ConfigDict, Field, field_validator


class HarnessWorkflowType(str, Enum):
    """Canonical workflow types."""

    SIGNAL_EXTRACTION = "signal_extraction"
    ACCOUNT_INTELLIGENCE = "account_intelligence"
    VALUE_MODEL_GENERATION = "value_model_generation"
    EVIDENCE_MATCHING = "evidence_matching"
    VALUE_TREE_GENERATION = "value_tree_generation"
    ROI_CALCULATOR_GENERATION = "roi_calculator_generation"
    BUSINESS_CASE_GENERATION = "business_case_generation"
    RENEWAL_RISK_ANALYSIS = "renewal_risk_analysis"
    EXPANSION_OPPORTUNITY_ANALYSIS = "expansion_opportunity_analysis"


class HarnessRunStatus(str, Enum):
    """Run status reflects execution disposition."""

    QUEUED = "queued"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    FAILED = "failed"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


class HarnessState(str, Enum):
    """
    Canonical workflow states.

    State flow (happy path):
      INIT → RESOLVE_CONTEXT → LOAD_VALUE_PACK → RETRIEVE_KNOWLEDGE
      → GENERATE_HYPOTHESES → MATCH_EVIDENCE → QUANTIFY_IMPACT
      → VALIDATE_CLAIMS → HUMAN_REVIEW → PUBLISH_OUTPUT → DONE

    Terminal states: DONE, FAILED, CANCELLED.
    """

    INIT = "INIT"
    RESOLVE_CONTEXT = "RESOLVE_CONTEXT"
    LOAD_VALUE_PACK = "LOAD_VALUE_PACK"
    RETRIEVE_KNOWLEDGE = "RETRIEVE_KNOWLEDGE"
    GENERATE_HYPOTHESES = "GENERATE_HYPOTHESES"
    MATCH_EVIDENCE = "MATCH_EVIDENCE"
    QUANTIFY_IMPACT = "QUANTIFY_IMPACT"
    VALIDATE_CLAIMS = "VALIDATE_CLAIMS"
    HUMAN_REVIEW = "HUMAN_REVIEW"
    PUBLISH_OUTPUT = "PUBLISH_OUTPUT"
    DONE = "DONE"
    FAILED = "FAILED"
    CANCELLED = "CANCELLED"

    @classmethod
    def terminal_states(cls) -> set[HarnessState]:
        return {cls.DONE, cls.FAILED, cls.CANCELLED}

    @classmethod
    def non_terminal_states(cls) -> set[HarnessState]:
        return set(cls) - cls.terminal_states()

    @property
    def is_terminal(self) -> bool:
        return self in self.terminal_states()


class InitiatedBy(str, Enum):
    """Who or what initiated the run."""

    USER = "user"
    SYSTEM = "system"
    AGENT = "agent"
    SCHEDULED_JOB = "scheduled_job"


class ToolLayer(str, Enum):
    """Fabric layer where the tool executes."""

    L1 = "L1"
    L2 = "L2"
    L3 = "L3"
    L4 = "L4"
    L5 = "L5"
    L6 = "L6"
    PRESENTATION = "presentation"
    EXTERNAL = "external"


class ToolSideEffectClass(str, Enum):
    """Classification of tool side effects."""

    READ = "read"
    INTERNAL_WRITE = "internal_write"
    EXTERNAL_WRITE = "external_write"
    CUSTOMER_FACING_OUTPUT = "customer_facing_output"


class ToolRiskLevel(str, Enum):
    """Risk level of tool invocation."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class GateType(str, Enum):
    """Type of human gate."""

    APPROVE_CLAIMS = "approve_claims"
    APPROVE_ASSUMPTIONS = "approve_assumptions"
    APPROVE_CUSTOMER_OUTPUT = "approve_customer_output"
    RESOLVE_CONFLICT = "resolve_conflict"


class ActionClass(str, Enum):
    """Canonical high-impact action classes requiring human approval."""

    APPROVE_HYPOTHESES = "approve_hypotheses"
    PUBLISH_BUSINESS_CASE = "publish_business_case"
    APPLY_BENCHMARK_ASSUMPTIONS = "apply_benchmark_assumptions"
    GENERATE_CUSTOMER_FACING_DELIVERABLE = "generate_customer_facing_deliverable"
    CHANGE_ACCOUNT_VALUE_MODEL = "change_account_value_model"


class GateStatus(str, Enum):
    """Human gate status."""

    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"
    MODIFIED = "modified"
    EXPIRED = "expired"


class ValidationState(str, Enum):
    """Result of claim validation."""

    PASSED = "passed"
    FAILED = "failed"
    NEEDS_REVIEW = "needs_review"
    INSUFFICIENT_EVIDENCE = "insufficient_evidence"


class HarnessRun(BaseModel):
    """
    A single harness workflow execution.

    Invariants:
      - tenant_id is always present.
      - trace_id is always present.
      - status and current_state are kept consistent by the state machine.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: f"run_{uuid.uuid4().hex[:16]}")
    tenant_id: str
    account_id: str | None = None
    workflow_type: HarnessWorkflowType
    initiated_by: InitiatedBy
    status: HarnessRunStatus = HarnessRunStatus.QUEUED
    current_state: HarnessState = HarnessState.INIT
    value_pack_id: str | None = None
    trace_id: str = Field(default_factory=lambda: f"trace_{uuid.uuid4().hex[:16]}")
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    def with_state(
        self,
        state: HarnessState,
        status: HarnessRunStatus | None = None,
    ) -> Self:
        """Return a new run with updated state and timestamp."""
        update: dict[str, Any] = {
            "current_state": state,
            "updated_at": datetime.now(UTC),
        }
        if status is not None:
            update["status"] = status
        elif state.is_terminal:
            if state == HarnessState.DONE:
                update["status"] = HarnessRunStatus.COMPLETED
            elif state == HarnessState.FAILED:
                update["status"] = HarnessRunStatus.FAILED
            elif state == HarnessState.CANCELLED:
                update["status"] = HarnessRunStatus.CANCELLED
        return self.model_copy(update=update)

    @field_validator("tenant_id")
    @classmethod
    def _tenant_id_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tenant_id is required and must be non-empty")
        return v


class ToolCallRef(BaseModel):
    """Reference to a tool invocation within a checkpoint."""

    model_config = ConfigDict(frozen=True)

    tool_contract_id: str
    invocation_id: str
    input_hash: str
    output_hash: str | None = None


class HarnessCheckpoint(BaseModel):
    """
    Immutable snapshot of workflow state at a point in time.

    Deterministic hashing: the same payload + state always produces the same hash.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: f"chk_{uuid.uuid4().hex[:16]}")
    run_id: str
    tenant_id: str
    state_name: HarnessState
    state_payload: dict[str, Any] = Field(default_factory=dict)
    input_hash: str
    output_hash: str | None = None
    tool_calls: list[ToolCallRef] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @field_validator("run_id", "tenant_id")
    @classmethod
    def _required_refs(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("run_id and tenant_id are required")
        return v

    @classmethod
    def compute_input_hash(
        cls,
        run_id: str,
        tenant_id: str,
        state_name: HarnessState,
        state_payload: dict[str, Any],
        tool_calls: list[ToolCallRef],
    ) -> str:
        """Deterministic hash over checkpoint contents."""
        canonical = json.dumps(
            {
                "run_id": run_id,
                "tenant_id": tenant_id,
                "state_name": state_name.value,
                "state_payload": _canonical_json(state_payload),
                "tool_calls": [
                    {
                        "tool_contract_id": tc.tool_contract_id,
                        "invocation_id": tc.invocation_id,
                        "input_hash": tc.input_hash,
                        "output_hash": tc.output_hash,
                    }
                    for tc in sorted(tool_calls, key=lambda t: t.invocation_id)
                ],
            },
            sort_keys=True,
            separators=(",", ":"),
            default=str,
        )
        return hashlib.sha256(canonical.encode("utf-8")).hexdigest()


class ToolContract(BaseModel):
    """
    Typed contract for a tool that the harness can invoke.

    Invariants:
      - side_effect_class == customer_facing_output → risk_level >= high.
      - requires_tenant_context implies tenant_id must be present at invocation.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: f"tc_{uuid.uuid4().hex[:16]}")
    tool_id: str
    layer: ToolLayer
    version: str = "v1"
    input_schema_ref: str
    output_schema_ref: str
    side_effect_class: ToolSideEffectClass
    risk_level: ToolRiskLevel
    requires_tenant_context: bool = True
    requires_account_context: bool = False
    approval_policy_id: str | None = None
    action_class: ActionClass | None = Field(
        default=None,
        description="High-impact action class requiring explicit human approval",
    )

    @field_validator("tool_id")
    @classmethod
    def _tool_id_required(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tool_id is required")
        return v

    def requires_approval(self) -> bool:
        """Return True if this tool requires explicit approval before invocation."""
        return self.risk_level in (ToolRiskLevel.HIGH, ToolRiskLevel.CRITICAL) or (
            self.side_effect_class == ToolSideEffectClass.CUSTOMER_FACING_OUTPUT
        )


class HumanGate(BaseModel):
    """
    A gate that requires human approval before a workflow can proceed.

    Invariants:
      - Once decided (approved/rejected), the decision is final.
      - expired gates cannot be decided.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: f"gate_{uuid.uuid4().hex[:16]}")
    run_id: str
    tenant_id: str
    gate_type: GateType
    action_class: ActionClass | None = None
    status: GateStatus = GateStatus.PENDING
    decision_by: str | None = None
    decision_reason: str | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))
    decided_at: datetime | None = None

    @property
    def is_terminal(self) -> bool:
        return self.status in (
            GateStatus.APPROVED,
            GateStatus.REJECTED,
            GateStatus.EXPIRED,
        )

    def decide(
        self,
        new_status: GateStatus,
        decision_by: str,
        decision_reason: str | None = None,
    ) -> Self:
        """Return a new gate with the decision applied."""
        if self.is_terminal and self.status != GateStatus.MODIFIED:
            raise ValueError(f"Gate {self.id} already decided with status {self.status}")
        if new_status == GateStatus.EXPIRED and self.status != GateStatus.PENDING:
            raise ValueError("Only pending gates can be expired")
        if new_status not in (
            GateStatus.APPROVED,
            GateStatus.REJECTED,
            GateStatus.MODIFIED,
            GateStatus.EXPIRED,
        ):
            raise ValueError(f"Invalid gate decision status: {new_status}")
        update: dict[str, Any] = {
            "status": new_status,
            "decision_by": decision_by,
            "decided_at": datetime.now(UTC),
        }
        if decision_reason is not None:
            update["decision_reason"] = decision_reason
        return self.model_copy(update=update)


class ClaimValidationResult(BaseModel):
    """Result of validating a single claim through L5 or fallback."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    id: str = Field(default_factory=lambda: f"cvr_{uuid.uuid4().hex[:16]}")
    tenant_id: str
    claim_id: str
    validation_state: ValidationState
    evidence_refs: list[str] = Field(default_factory=list)
    confidence: float = Field(ge=0.0, le=1.0)
    trust_score: float = Field(ge=0.0, le=1.0)
    validator: Literal["agent", "human", "policy", "benchmark", "unavailable"]
    reason: str = ""
    created_at: datetime = Field(default_factory=lambda: datetime.now(UTC))


class ValidationSummary(BaseModel):
    """Aggregate result across all claims validated in a single run.

    Rules:
      - can_publish=True only when all claims passed.
      - requires_human_review=True when any claim is needs_review or insufficient_evidence.
      - Empty results → can_publish=False, requires_human_review=True.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    total: int = 0
    passed: int = 0
    failed: int = 0
    needs_review: int = 0
    insufficient_evidence: int = 0
    can_publish: bool = False
    requires_human_review: bool = True


class EvidenceChain(BaseModel):
    """Full evidence provenance for a single validated claim.

    Captures the claim ID, all source/evidence/benchmark references, the
    validation result from L5, and any human gate decision that overrode
    or confirmed the automated result.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    claim_id: str
    source_refs: list[str] = Field(default_factory=list)
    evidence_refs: list[str] = Field(default_factory=list)
    benchmark_refs: list[str] = Field(default_factory=list)
    validation_result: ClaimValidationResult
    confidence: float = Field(ge=0.0, le=1.0)
    trust_score: float = Field(ge=0.0, le=1.0)
    human_decision: HumanGate | None = None


class HarnessTraceEvent(BaseModel):
    """
    Structured trace event emitted on every significant harness action.

    Invariant: tenant_id and trace_id are always present.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")

    trace_id: str
    run_id: str
    tenant_id: str
    account_id: str | None = None
    workflow_type: HarnessWorkflowType
    from_state: HarnessState | None = None
    to_state: HarnessState | None = None
    status: HarnessRunStatus | None = None
    value_pack_id: str | None = None
    validation_state: ValidationState | None = None
    human_gate_id: str | None = None
    tool_contract_id: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
    event_type: str = "transition"
    metadata: dict[str, Any] = Field(default_factory=dict)

    @field_validator("tenant_id", "trace_id", "run_id")
    @classmethod
    def _required_ids(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("tenant_id, trace_id, and run_id are required")
        return v


def _canonical_json(value: Any) -> Any:
    """Recursively sort dict keys for canonical JSON serialization."""
    if isinstance(value, dict):
        return {k: _canonical_json(v) for k, v in sorted(value.items())}
    if isinstance(value, list):
        return [_canonical_json(v) for v in value]
    if isinstance(value, Enum):
        return value.value
    return value
