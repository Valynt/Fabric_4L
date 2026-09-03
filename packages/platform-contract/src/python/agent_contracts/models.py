"""Executable semantic-contract models for Layer 4 agents.

These models intentionally live in ``packages/platform-contract`` so Layer 4
runtime code, CI checks, and contract tests validate the same semantic envelope.
The first rollout is warning-oriented: callers may collect findings without
blocking production execution, then opt into strict enforcement when the registry
coverage is complete.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Mapping, Optional, Sequence

from pydantic import BaseModel, Field, ValidationError, field_validator, model_validator


SEMANTIC_CONTRACT_VERSION = "2.0.0"


class ContractViolationSeverity(str, Enum):
    """Severity emitted by semantic-contract validators."""

    ERROR = "error"
    WARNING = "warning"


class ContractViolation(BaseModel):
    """A single semantic-contract validation finding."""

    code: str
    message: str
    severity: ContractViolationSeverity = ContractViolationSeverity.WARNING
    path: str = "$"


class ValidationMode(str, Enum):
    """Validation mode used by runtime and CI integrations."""

    WARN = "warn"
    STRICT = "strict"


class ContractValidationResult(BaseModel):
    """Structured result returned by all semantic-contract validators."""

    valid: bool
    mode: ValidationMode = ValidationMode.WARN
    violations: List[ContractViolation] = Field(default_factory=list)
    normalized: Optional[Dict[str, Any]] = None

    @property
    def blocking(self) -> bool:
        """Return true when the result should block execution."""

        return self.mode == ValidationMode.STRICT and any(
            violation.severity == ContractViolationSeverity.ERROR
            for violation in self.violations
        )


class ContractVersionRef(BaseModel):
    """Version identifiers for the semantic contract surfaces used by an event."""

    semantic_contract: str = SEMANTIC_CONTRACT_VERSION
    agent_registry: Optional[str] = None
    prompt: Optional[str] = None
    tool: Optional[str] = None
    workflow: Optional[str] = None
    memory: Optional[str] = None


class ProvenanceRef(BaseModel):
    """Traceability fields required for auditable agent outputs."""

    tenant_id: str
    trace_id: str
    workflow_id: Optional[str] = None
    audit_event_id: Optional[str] = None
    source_node: Optional[str] = None
    source_layer: str = "layer4-agents"


class PromptRef(BaseModel):
    """Reference to the prompt contract that shaped an agent decision."""

    prompt_id: str
    version: str
    reasoning_policy_id: Optional[str] = None
    content_hash: Optional[str] = None


class AgentPermission(BaseModel):
    """Declarative capability boundary for an agent operating contract."""

    read_paths: List[str] = Field(default_factory=list)
    write_paths: List[str] = Field(default_factory=list)
    network: List[Literal["none", "internal_only", "restricted_external", "external"]] = Field(
        default_factory=list
    )
    isolation_level: Literal["tenant_strict", "tenant_preferred", "shared_read_only", "shared"]


class EvalTarget(BaseModel):
    """Eval target that an agent operating contract must meet."""

    suite_id: str
    min_score: float = Field(..., ge=0.0, le=1.0)
    required_capabilities: List[str] = Field(default_factory=list)


class AgentOperatingContract(BaseModel):
    """Declarative per-agent operating contract (tools, memory, permissions, eval)."""

    id: str
    version: str
    kind: Literal["agent_contract"]
    owner: Optional[str] = None
    risk_class: Optional[str] = None
    description: Optional[str] = None
    agent_type: str
    tools: List[str] = Field(default_factory=list)
    memory_scopes: List[str] = Field(default_factory=list)
    permissions: AgentPermission
    eval_target: EvalTarget
    compatibility: Optional[Dict[str, Any]] = None
    observability: Optional[Dict[str, Any]] = None
    governance: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}


class AgentOutputEnvelope(BaseModel):
    """Canonical semantic envelope for Layer 4 agent decision outputs."""

    agent_type: str
    output: Any = None
    provenance: ProvenanceRef
    contract_versions: ContractVersionRef = Field(default_factory=ContractVersionRef)
    prompt: Optional[PromptRef] = None
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)
    explainability: Dict[str, Any] = Field(default_factory=dict)
    evidence: List[Dict[str, Any]] = Field(default_factory=list)
    emitted_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("agent_type")
    @classmethod
    def agent_type_must_be_present(cls, value: str) -> str:
        if not value:
            raise ValueError("agent_type is required")
        return value


class ToolInvocationEnvelope(BaseModel):
    """Canonical semantic envelope for tool invocations and tool results."""

    tool_name: str
    tool_version: str
    caller_agent_type: str
    input: Dict[str, Any] = Field(default_factory=dict)
    output: Optional[Any] = None
    provenance: ProvenanceRef
    contract_versions: ContractVersionRef = Field(default_factory=ContractVersionRef)
    success: bool = True
    error: Optional[Dict[str, Any]] = None

    @model_validator(mode="after")
    def error_required_when_failed(self) -> "ToolInvocationEnvelope":
        if self.success is False and not self.error:
            raise ValueError("failed tool invocations must include an error envelope")
        return self


class WorkflowTransitionEnvelope(BaseModel):
    """Canonical semantic envelope for workflow state transitions."""

    workflow_type: str
    workflow_id: str
    source_state: str
    target_state: str
    triggering_agent_type: str
    provenance: ProvenanceRef
    contract_versions: ContractVersionRef = Field(default_factory=ContractVersionRef)
    transition_reason: Optional[str] = None


class MemoryReference(BaseModel):
    """Canonical semantic reference to persisted memory used by an agent."""

    memory_id: str
    memory_type: str
    tenant_id: str
    trace_id: str
    contract_versions: ContractVersionRef = Field(default_factory=ContractVersionRef)
    provenance: Optional[ProvenanceRef] = None


class CompatibilityMatrix(BaseModel):
    """Version compatibility matrix for Phase 2 semantic contracts."""

    id: str = "fabric4l-agent-semantic-compatibility"
    version: str = SEMANTIC_CONTRACT_VERSION
    agent_registry_version: str
    min_runtime_version: str = "0.1.0"
    enforcement_default: ValidationMode = ValidationMode.WARN
    compatible_event_versions: Dict[str, str] = Field(default_factory=dict)
    agent_contracts: Dict[str, str] = Field(default_factory=dict)
    prompt_contracts: Dict[str, str] = Field(default_factory=dict)
    tool_contracts: Dict[str, str] = Field(default_factory=dict)
    workflow_contracts: Dict[str, str] = Field(default_factory=dict)
    memory_contracts: Dict[str, str] = Field(default_factory=dict)
    deprecated_contracts: List[str] = Field(default_factory=list)


def _model_validate(model_cls: type[BaseModel], value: Mapping[str, Any]) -> BaseModel:
    """Call the Pydantic v2 API when available, otherwise fall back to v1."""

    model_validate = getattr(model_cls, "model_validate", None)
    if callable(model_validate):
        return model_validate(value)  # type: ignore[no-any-return]
    return model_cls.parse_obj(value)


def _model_dump(model: BaseModel) -> Dict[str, Any]:
    """Call the Pydantic v2 dump API when available, otherwise fall back to v1."""

    model_dump = getattr(model, "model_dump", None)
    if callable(model_dump):
        return model_dump(mode="json")  # type: ignore[no-any-return]
    return model.dict()


def _validation_errors(exc: ValidationError) -> List[ContractViolation]:
    violations: List[ContractViolation] = []
    for error in exc.errors():
        location = ".".join(str(part) for part in error.get("loc", ())) or "$"
        violations.append(
            ContractViolation(
                code="semantic_contract_validation_error",
                message=str(error.get("msg", "validation error")),
                severity=ContractViolationSeverity.ERROR,
                path=location,
            )
        )
    return violations


def validate_envelope(
    payload: Mapping[str, Any],
    model_cls: type[BaseModel],
    *,
    mode: ValidationMode | str = ValidationMode.WARN,
) -> ContractValidationResult:
    """Validate a payload against a semantic-contract model."""

    resolved_mode = ValidationMode(mode)
    try:
        model = _model_validate(model_cls, payload)
    except ValidationError as exc:
        return ContractValidationResult(
            valid=False,
            mode=resolved_mode,
            violations=_validation_errors(exc),
            normalized=None,
        )
    except Exception:
        return ContractValidationResult(
            valid=False,
            mode=resolved_mode,
            violations=[
                ContractViolation(
                    code="semantic_contract_validation_error",
                    message="contract_validation_error",
                    severity=ContractViolationSeverity.ERROR,
                )
            ],
            normalized=None,
        )

    return ContractValidationResult(
        valid=True,
        mode=resolved_mode,
        violations=[],
        normalized=_model_dump(model),
    )


def validate_agent_output(
    payload: Mapping[str, Any], *, mode: ValidationMode | str = ValidationMode.WARN
) -> ContractValidationResult:
    """Validate an agent output semantic envelope."""

    return validate_envelope(payload, AgentOutputEnvelope, mode=mode)


def validate_tool_invocation(
    payload: Mapping[str, Any], *, mode: ValidationMode | str = ValidationMode.WARN
) -> ContractValidationResult:
    """Validate a tool invocation semantic envelope."""

    return validate_envelope(payload, ToolInvocationEnvelope, mode=mode)


def validate_workflow_transition(
    payload: Mapping[str, Any], *, mode: ValidationMode | str = ValidationMode.WARN
) -> ContractValidationResult:
    """Validate a workflow transition semantic envelope."""

    return validate_envelope(payload, WorkflowTransitionEnvelope, mode=mode)


def validate_memory_reference(
    payload: Mapping[str, Any], *, mode: ValidationMode | str = ValidationMode.WARN
) -> ContractValidationResult:
    """Validate a memory reference semantic envelope."""

    return validate_envelope(payload, MemoryReference, mode=mode)


def build_agent_output_envelope(
    *,
    agent_type: str,
    output: Any,
    tenant_id: str,
    trace_id: str,
    workflow_id: Optional[str] = None,
    audit_event_id: Optional[str] = None,
    source_node: Optional[str] = None,
    prompt_id: Optional[str] = None,
    prompt_version: Optional[str] = None,
    reasoning_policy_id: Optional[str] = None,
    prompt_content_hash: Optional[str] = None,
    confidence: Optional[float] = None,
    explainability: Optional[Mapping[str, Any]] = None,
    evidence: Optional[Sequence[Mapping[str, Any]]] = None,
    contract_versions: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Construct a normalized agent-output envelope from runtime metadata."""

    prompt = None
    if prompt_id and prompt_version:
        prompt = PromptRef(
            prompt_id=prompt_id,
            version=prompt_version,
            reasoning_policy_id=reasoning_policy_id,
            content_hash=prompt_content_hash,
        )

    envelope = AgentOutputEnvelope(
        agent_type=agent_type,
        output=output,
        provenance=ProvenanceRef(
            tenant_id=tenant_id,
            trace_id=trace_id,
            workflow_id=workflow_id,
            audit_event_id=audit_event_id,
            source_node=source_node,
        ),
        prompt=prompt,
        confidence=confidence,
        explainability=dict(explainability or {}),
        evidence=[dict(item) for item in (evidence or [])],
        contract_versions=ContractVersionRef(**dict(contract_versions or {})),
    )
    return _model_dump(envelope)
