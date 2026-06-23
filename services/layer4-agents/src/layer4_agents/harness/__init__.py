"""
Fabric_4L Harness — Governed Execution Spine for Agentic Value Workflows.

The harness coordinates:
  - HarnessRun lifecycle
  - Deterministic workflow state transitions
  - Checkpoints
  - Tool contracts
  - Approval policies
  - Human gates
  - L5 claim validation hooks
  - Tenant/account/value-pack context
  - Structured trace emission
  - Customer-facing output controls
  - Auditability and replayability

Invariants:
  - Every HarnessRun has tenant_id and trace_id.
  - Every state transition is validated.
  - Terminal runs cannot continue.
  - Every checkpoint is tied to run_id and tenant_id with deterministic hashing.
  - Every high-risk tool action requires an approval policy.
  - Every customer-facing output requires L5 validation or explicit human override.
  - Unavailable L5 validation routes to needs_review — never silently approves.
"""

from .checkpoints import CheckpointError, CheckpointManager
from .human_gates import (
    GateDecisionError,
    GateExpiredError,
    GateNotFoundError,
    HumanGateManager,
)
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
    ToolContract,
    ToolLayer,
    ToolRiskLevel,
    ToolSideEffectClass,
    ValidationState,
)
from .policies import (
    ApprovalRequiredError,
    PublicationBlockedError,
    can_publish_output,
    evaluate_tool_invocation_policy,
    evaluate_transition_policy,
    requires_approval,
)
from .registry import HarnessRegistry, HarnessRegistryError, RunNotFoundError
from .state_machine import (
    StateMachine,
    TerminalStateError,
    TransitionError,
    ValidationRequiredError,
)
from .telemetry import TelemetryEmitter
from .tool_contracts import (
    ToolContractRegistry,
    ToolNotFoundError,
    ToolRegistrationError,
)
from .validation_hooks import (
    ClaimValidationRequest,
    ClaimValidator,
    MockValidator,
    UnavailableValidator,
    ValidationHook,
    ValidationUnavailableError,
)


def __getattr__(name: str):  # noqa: N807
    """Lazy imports for SQL-backed stores and factory — avoids pulling in
    SQLAlchemy ORM models at harness import time (keeps standalone tests fast)."""
    _sql = {
        "SqlCheckpointManager",
        "SqlHarnessRegistry",
        "SqlHumanGateManager",
        "SqlTelemetryEmitter",
        "SqlToolContractRegistry",
    }
    _factory = {"make_in_memory_registry", "make_sql_registry", "make_live_l5_registry"}
    _l5 = {"LiveL5Validator"}
    if name in _sql:
        from . import sql_stores as _m
        return getattr(_m, name)
    if name in _factory:
        from . import factory as _m
        return getattr(_m, name)
    if name in _l5:
        from . import live_l5_validator as _m
        return getattr(_m, name)
    raise AttributeError(f"module 'harness' has no attribute {name!r}")

__all__ = [
    # Models
    "HarnessRun",
    "HarnessCheckpoint",
    "ToolContract",
    "HumanGate",
    "ClaimValidationResult",
    "HarnessTraceEvent",
    "HarnessWorkflowType",
    "HarnessRunStatus",
    "HarnessState",
    "ToolLayer",
    "ToolSideEffectClass",
    "ToolRiskLevel",
    "GateType",
    "GateStatus",
    "ValidationState",
    "InitiatedBy",
    "ActionClass",
    # State machine
    "StateMachine",
    "TransitionError",
    "TerminalStateError",
    "ValidationRequiredError",
    # Policies
    "requires_approval",
    "can_publish_output",
    "evaluate_transition_policy",
    "evaluate_tool_invocation_policy",
    "ApprovalRequiredError",
    "PublicationBlockedError",
    # Tool contracts
    "ToolContractRegistry",
    "ToolRegistrationError",
    "ToolNotFoundError",
    # Human gates
    "HumanGateManager",
    "GateDecisionError",
    "GateExpiredError",
    "GateNotFoundError",
    # Checkpoints
    "CheckpointManager",
    "CheckpointError",
    # Telemetry
    "TelemetryEmitter",
    # Validation hooks
    "ClaimValidationRequest",
    "ClaimValidator",
    "MockValidator",
    "UnavailableValidator",
    "ValidationHook",
    "ValidationUnavailableError",
    # Registry
    "HarnessRegistry",
    "HarnessRegistryError",
    "RunNotFoundError",
    # SQL-backed stores
    "SqlCheckpointManager",
    "SqlHarnessRegistry",
    "SqlHumanGateManager",
    "SqlTelemetryEmitter",
    "SqlToolContractRegistry",
    # Factory
    "make_in_memory_registry",
    "make_sql_registry",
    "make_live_l5_registry",
    # Live L5 validator
    "LiveL5Validator",
]
