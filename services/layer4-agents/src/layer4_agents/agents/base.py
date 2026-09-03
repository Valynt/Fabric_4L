from __future__ import annotations

"""Base agent class and state definitions.

Provides the foundation for all 9 canonical agent types in the Value Fabric
Layer 4 system.  See taxonomy.py for the full roster.
"""


import asyncio
import logging
import os
import sys
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum, auto
from pathlib import Path
from typing import TYPE_CHECKING, Any

from value_fabric.shared.governance.abom import AgentBillOfMaterials
from value_fabric.shared.models.typed_dict import TypedDictModel

_PLATFORM_CONTRACT_PYTHON = next(
    (parent / "packages" / "platform-contract" / "src" / "python" for parent in Path(__file__).resolve().parents if (parent / "packages" / "platform-contract" / "src" / "python").exists()),
    None,
)
if _PLATFORM_CONTRACT_PYTHON and str(_PLATFORM_CONTRACT_PYTHON) not in sys.path:
    sys.path.append(str(_PLATFORM_CONTRACT_PYTHON))

try:  # pragma: no cover - contract tests configure this path explicitly
    from agent_contracts import build_agent_output_envelope, validate_agent_output
except asyncio.CancelledError:
    raise
except Exception:  # pragma: no cover - runtime remains warning-only if package import fails
    build_agent_output_envelope = None  # type: ignore[assignment]
    validate_agent_output = None  # type: ignore[assignment]

if TYPE_CHECKING:
    from .operating_contract import AgentOperatingContract

logger = logging.getLogger(__name__)
SEMANTIC_CONTRACT_VERSION = "2.0.0"


class AgentState_to_dictResult(TypedDictModel):
    agent_id: Any
    agent_type: Any
    completed_at: Any
    context: Any
    current_task: Any
    errors: Any
    metadata: Any
    started_at: Any
    status: Any

try:
    from value_fabric.shared.testability import Clock, IDGenerator, SystemClock, UUIDGenerator
except ImportError:
    # Fallback implementations when shared package unavailable
    class Clock:  # type: ignore[no-redef]
        @staticmethod
        def now() -> datetime:
            return datetime.now()
    
    class SystemClock(Clock):  # type: ignore[no-redef]
        pass
    
    class IDGenerator:  # type: ignore[no-redef]
        @staticmethod
        def generate() -> str:
            import uuid
            return str(uuid.uuid4())
    
    class UUIDGenerator(IDGenerator):  # type: ignore[no-redef]
        pass


class AgentStatus(Enum):
    """Agent execution status."""

    IDLE = auto()
    INITIALIZING = auto()
    RUNNING = auto()
    PAUSED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()


@dataclass
class AgentCapability:
    """Capability that an agent can perform.

    Attributes:
        name: Capability identifier
        description: Human-readable description
        input_schema: Expected input structure
        output_schema: Expected output structure
        timeout_seconds: Maximum execution time
    """

    name: str
    description: str
    input_schema: dict[str, Any] = field(default_factory=dict)
    output_schema: dict[str, Any] = field(default_factory=dict)
    timeout_seconds: int = 300


@dataclass
class AgentState:
    """Current state of an agent instance.

    Attributes:
        agent_id: Unique identifier
        agent_type: Type of agent
        status: Current status
        current_task: What the agent is currently doing
        context: Execution context (tenant_id, user_id, etc.)
        started_at: When agent started
        completed_at: When agent finished
        errors: List of errors encountered
        metadata: Additional runtime data
    """

    agent_id: str
    agent_type: str
    status: AgentStatus = AgentStatus.IDLE
    current_task: str | None = None
    context: dict[str, Any] = field(default_factory=dict)
    started_at: datetime | None = None
    completed_at: datetime | None = None
    errors: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary."""
        return dict(AgentState_to_dictResult.model_validate({
            "agent_id": self.agent_id,
            "agent_type": self.agent_type,
            "status": self.status.name,
            "current_task": self.current_task,
            "context": self.context,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "errors": self.errors,
            "metadata": self.metadata,
        }).model_dump())


class BaseAgent(ABC):
    """Base class for all Value Fabric agents.

    All agents must inherit from this class and implement:
    - execute(): The main agent execution logic
    - get_capabilities(): Return list of supported capabilities

    Example:
        class MyAgent(BaseAgent):
            agent_type = "MY_AGENT"

            def get_capabilities(self) -> List[AgentCapability]:
                return [AgentCapability(name="do_something", ...)]

            async def execute(self, task: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
                # Implementation here
                return dict(result="success")
    """

    agent_type: str = "BASE"
    capabilities: list[AgentCapability] = []

    def __init__(
        self,
        agent_id: str | None = None,
        config: dict[str, Any] | None = None,
        message_bus: Any | None = None,
        clock: Clock | None = None,
        id_generator: IDGenerator | None = None,
    ):
        """Initialize agent.

        Args:
            agent_id: Unique identifier (generated if not provided)
            config: Agent-specific configuration
            message_bus: Message bus for inter-agent communication
            clock: Injectable clock for time operations.  Defaults to
                ``SystemClock``.
            id_generator: Injectable ID generator.  Defaults to ``UUIDGenerator``.
        """
        self._clock: Clock = clock or SystemClock()
        self._id_gen: IDGenerator = id_generator or UUIDGenerator()
        self.agent_id = agent_id or f"{self.agent_type.lower()}-{self._id_gen.generate()[:8]}"
        self.config = config or {}
        self.message_bus = message_bus
        self.abom: AgentBillOfMaterials | None = None
        self.contract: AgentOperatingContract | None = None
        self.state = AgentState(
            agent_id=self.agent_id,
            agent_type=self.agent_type,
            context={"config": self.config},
        )
        self._initialized = False
        self._execution_lock = asyncio.Lock()

    @staticmethod
    def _default_manifest_dir() -> Path:
        # base.py: agents -> layer4_agents -> src -> layer4-agents -> manifests
        return Path(__file__).resolve().parents[3] / "manifests"

    def _load_operating_contract(self) -> None:
        """Load the declarative operating contract for this agent type.

        The contract is loaded in warning mode by default; set
        ``AGENT_OPERATING_CONTRACT_MODE=strict`` to fail closed when no valid
        contract is present.
        """
        try:
            # Imported lazily to avoid a circular import: base.py is also
            # loaded directly by the harness (registered as ``agents.base``),
            # and a top-of-file ``from .operating_contract import ...`` would
            # re-trigger ``agents/__init__.py`` while this module is still
            # partially initialized.
            from .operating_contract import load_operating_contract

            self.contract = load_operating_contract(self.agent_type)
        except Exception as exc:
            mode = os.getenv("AGENT_OPERATING_CONTRACT_MODE", "warn").strip().lower()
            if mode == "strict":
                raise AgentExecutionError(
                    f"Agent {self.agent_id} failed to load operating contract: {exc}"
                ) from exc
            logger.warning(
                "Agent %s could not load operating contract (warning mode): %s",
                self.agent_id,
                exc,
            )
            self.contract = None

        if self.contract is not None:
            self.state.metadata["operating_contract"] = {
                "id": self.contract.id,
                "version": self.contract.version,
                "agent_type": self.contract.agent_type,
                "tools": self.contract.tools,
                "memory_scopes": self.contract.memory_scopes,
                "eval_target": {
                    "suite_id": self.contract.eval_target.suite_id,
                    "min_score": self.contract.eval_target.min_score,
                },
            }

    async def initialize(self) -> None:
        """Initialize agent resources and load the GATE ABOM manifest."""
        if self._initialized:
            return

        self.state.status = AgentStatus.INITIALIZING

        # GATE Phase 2: load agent bill of materials
        manifest_path = self.config.get("manifest_path")
        if manifest_path:
            from value_fabric.shared.governance.abom import load_abom

            self.abom = load_abom(manifest_path)
        else:
            self.abom = AgentBillOfMaterials.from_manifest_dir(
                self._default_manifest_dir(),
                self.agent_type,
                override_agent_id=self.agent_id,
            )
        self.state.metadata["abom_hash"] = self.abom.manifest_hash()

        self._load_operating_contract()

        await self._initialize_resources()
        self._initialized = True
        self.state.status = AgentStatus.IDLE

    async def _initialize_resources(self) -> None:
        """Override to initialize agent-specific resources."""
        pass

    @abstractmethod
    def get_capabilities(self) -> list[AgentCapability]:
        """Return list of capabilities this agent supports."""
        pass

    @abstractmethod
    async def execute(
        self,
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Execute a task.

        Args:
            task: Task specification with 'capability' and 'parameters'
            context: Execution context (tenant_id, user_id, workflow_id, etc.)

        Returns:
            Task execution result
        """
        pass

    def _semantic_contract_mode(self) -> str:
        """Resolve Phase 2 semantic-contract enforcement mode."""

        mode = os.getenv("AGENT_SEMANTIC_CONTRACT_MODE", "warn").strip().lower()
        return "strict" if mode == "strict" else "warn"

    def _replay_enabled(self) -> bool:
        """Resolve GATE Phase 3 replay snapshot commit mode."""

        return os.getenv("AGENT_REPLAY_MODE", "enabled").lower() != "disabled"

    def _validate_agent_output_contract(
        self,
        result: dict[str, Any],
        task: dict[str, Any],
        context: dict[str, Any],
    ) -> dict[str, Any]:
        """Validate an agent result against the shared semantic output envelope."""

        mode = self._semantic_contract_mode()
        if build_agent_output_envelope is None or validate_agent_output is None:
            validation_metadata = {
                "version": SEMANTIC_CONTRACT_VERSION,
                "mode": mode,
                "valid": False,
                "violations": [
                    {
                        "code": "semantic_contract_validator_unavailable",
                        "message": "agent_contracts package is unavailable in this runtime",
                        "severity": "warning",
                        "path": "$",
                    }
                ],
            }
            self.state.metadata["semantic_contract"] = validation_metadata
            return validation_metadata

        tenant_id = str(context.get("tenant_id") or context.get("tenantId") or "unknown")
        trace_id = str(context.get("trace_id") or context.get("traceId") or self.agent_id)
        workflow_id = context.get("workflow_id") or context.get("workflowId")
        audit_event_id = context.get("audit_event_id") or context.get("auditEventId")
        capability = str(task.get("capability", "unknown"))

        envelope = build_agent_output_envelope(
            agent_type=self.agent_type,
            output=result,
            tenant_id=tenant_id,
            trace_id=trace_id,
            workflow_id=str(workflow_id) if workflow_id else None,
            audit_event_id=str(audit_event_id) if audit_event_id else None,
            source_node=f"{self.agent_type}.{capability}",
            confidence=result.get("confidence") if isinstance(result.get("confidence"), (int, float)) else None,
            explainability={"capability": capability},
            contract_versions={
                "semantic_contract": SEMANTIC_CONTRACT_VERSION,
                "agent_registry": "1.0.0",
            },
        )
        validation = validate_agent_output(envelope, mode=mode)
        violations = [
            violation.model_dump() if hasattr(violation, "model_dump") else violation
            for violation in validation.violations
        ]
        validation_metadata = {
            "version": SEMANTIC_CONTRACT_VERSION,
            "mode": validation.mode.value if hasattr(validation.mode, "value") else str(validation.mode),
            "valid": validation.valid,
            "violations": violations,
        }
        self.state.metadata["semantic_contract"] = validation_metadata
        if validation.blocking:
            raise AgentExecutionError(
                f"Agent {self.agent_id} produced output that violates semantic contract: {violations}"
            )
        if violations:
            logger.warning(
                "Agent %s semantic-contract warnings: %s",
                self.agent_id,
                violations,
            )
        return validation_metadata

    async def run(
        self,
        task: dict[str, Any],
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Run the agent with a task (handles lifecycle).

        GATE integration: If a ``tool_registry`` and ``abom`` are present in
        context, a ``ToolGateway`` is created and injected into ``ctx`` so that
        ``execute()`` implementations can call ``ctx['tool_gateway'].execute()``
        instead of using the registry directly.  A ``ReplayRecorder`` is also
        attached when available.

        Args:
            task: Task to execute
            context: Execution context

        Returns:
            Execution result
        """
        await self.initialize()

        ctx = context or {}
        self.state.context.update(ctx)
        self.state.started_at = self._clock.now()
        self.state.status = AgentStatus.RUNNING
        self.state.current_task = task.get("capability", "unknown")

        # ── GATE Phase 2: ToolGateway injection ──
        tool_gateway = None
        if "tool_registry" in ctx and self.abom is not None:
            try:
                from value_fabric.shared.governance.tool_gateway import ToolGateway

                tool_gateway = ToolGateway(
                    registry=ctx["tool_registry"],
                    abom=self.abom,
                    tenant_id=ctx.get("tenant_id"),
                    trace_id=ctx.get("trace_id"),
                )
                ctx["tool_gateway"] = tool_gateway
            except ImportError:
                pass  # GATE not installed — graceful degradation

        # ── GATE Phase 3: MemoryGateway injection ──
        memory_gateway = None
        if "memory_gateway" in ctx:
            memory_gateway = ctx["memory_gateway"]
        elif "retrieval_engine" in ctx and self.abom is not None:
            try:
                from value_fabric.shared.governance.memory_gateway import MemoryGateway

                memory_gateway = MemoryGateway(
                    retrieval_engine=ctx["retrieval_engine"],
                    tenant_id=ctx.get("tenant_id"),
                    agent_id=self.agent_id,
                    trace_id=ctx.get("trace_id"),
                    source_blocklist=ctx.get("memory_source_blocklist"),
                )
                ctx["memory_gateway"] = memory_gateway
            except ImportError:
                pass

        if memory_gateway is not None:
            # ctx was already snapshotted into state.context, so mirror the
            # injected gateway back so that persisted state reflects it.
            self.state.context["memory_gateway"] = memory_gateway

        # ── GATE Phase 3: ReplayRecorder injection ──
        replay_recorder = None
        if tool_gateway is not None:
            try:
                from value_fabric.shared.governance.replay import ReplayRecorder

                replay_recorder = ReplayRecorder(
                    agent_id=self.agent_id,
                    agent_type=self.agent_type,
                    abom=self.abom,
                    tenant_id=ctx.get("tenant_id"),
                    trace_id=ctx.get("trace_id"),
                )
                ctx["replay_recorder"] = replay_recorder
            except ImportError:
                pass  # Replay not installed — graceful degradation

        try:
            # Send status update via message bus if available
            if self.message_bus:
                await self.message_bus.publish(
                    agent_id=self.agent_id,
                    event_type="AGENT_STARTED",
                    payload={"task": task, "context": ctx},
                )

            # Execute the task
            async with self._execution_lock:
                result = await self.execute(task, ctx)

            semantic_contract = self._validate_agent_output_contract(result, task, ctx)

            # Mark completion
            self.state.status = AgentStatus.COMPLETED
            self.state.completed_at = self._clock.now()

            # ── GATE Phase 3: Commit replay snapshot ──
            if self._replay_enabled() and replay_recorder is not None and tool_gateway is not None:
                replay_recorder.record_tool_invocations(tool_gateway.invocation_log)
                if memory_gateway is not None:
                    replay_recorder.record_memory_accesses(memory_gateway.access_log)
                await replay_recorder.commit()
                self.state.metadata["replay_committed"] = True

            # Send completion event
            if self.message_bus:
                await self.message_bus.publish(
                    agent_id=self.agent_id,
                    event_type="AGENT_COMPLETED",
                    payload={"result": result, "semantic_contract": semantic_contract},
                )

            return result

        except asyncio.CancelledError:
            raise
        except Exception as e:
            self.state.status = AgentStatus.FAILED
            self.state.errors.append(f"{type(e).__name__}: agent_execution_failed")
            self.state.completed_at = self._clock.now()

            # Send failure event
            if self.message_bus:
                await self.message_bus.publish(
                    agent_id=self.agent_id,
                    event_type="AGENT_FAILED",
                    payload={"error": "Agent execution failed", "error_code": "AGENT_EXECUTION_ERROR"},
                )

            raise AgentExecutionError(f"Agent {self.agent_id} failed") from e

    async def pause(self) -> None:
        """Pause agent execution (if supported)."""
        if self.state.status == AgentStatus.RUNNING:
            self.state.status = AgentStatus.PAUSED

    async def resume(self) -> None:
        """Resume paused execution."""
        if self.state.status == AgentStatus.PAUSED:
            self.state.status = AgentStatus.RUNNING

    async def cancel(self) -> None:
        """Cancel current execution."""
        self.state.status = AgentStatus.CANCELLED
        self.state.completed_at = self._clock.now()

    def get_state(self) -> AgentState:
        """Get current agent state."""
        return self.state

    def has_capability(self, capability_name: str) -> bool:
        """Check if agent supports a capability."""
        return any(c.name == capability_name for c in self.get_capabilities())


class AgentExecutionError(Exception):
    """Raised when agent execution fails."""

    pass


class AgentNotFoundError(Exception):
    """Raised when requested agent type is not found."""

    pass


# ---------------------------------------------------------------------------
# Degraded output contract
# ---------------------------------------------------------------------------


@dataclass
class AgentResult:
    """Typed output envelope for all Layer 4 agent workflows.

    Carries the structured payload alongside governance flags that downstream
    consumers (UI, Layer 5, Narrative Builder) must respect before surfacing
    results to end users.

    Governance rules (enforced by ``__post_init__``):
    - ``llm_enrichment=False`` always forces ``customer_facing_allowed=False``
      and ``human_review_required=True``.
    - ``confidence < 0.4`` forces ``human_review_required=True``.
    - ``human_review_required=True`` forces ``customer_facing_allowed=False``.

    Attributes:
        payload:                 The structured agent output (workflow-specific).
        workflow_type:           Canonical workflow identifier (e.g. "roi_calculator").
        tenant_id:               Owning tenant — must be set before persistence.
        llm_enrichment:          True when the payload was produced with LLM assistance.
        confidence:              Aggregate confidence score [0.0, 1.0].
        customer_facing_allowed: Safe to surface directly to end users.
        human_review_required:   Must be reviewed by a human before use.
        degraded_reason:         Human-readable explanation when degraded.
        trace_id:                Harness run or request trace identifier.
        model_used:              LLM model identifier, if applicable.
        prompt_tokens:           Input token count for cost tracking.
        completion_tokens:       Output token count for cost tracking.
        metadata:                Arbitrary additional context.
    """

    payload: dict[str, Any]
    workflow_type: str
    tenant_id: str = ""
    llm_enrichment: bool = False
    confidence: float = 0.0
    customer_facing_allowed: bool = False
    human_review_required: bool = True
    degraded_reason: str | None = None
    trace_id: str | None = None
    model_used: str | None = None
    prompt_tokens: int = 0
    completion_tokens: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        self._apply_governance_rules()

    def _apply_governance_rules(self) -> None:
        """Enforce degraded-output invariants."""
        # Clamp confidence to valid range before any governance decisions.
        self.confidence = max(0.0, min(1.0, self.confidence))
        reasons: list[str] = []

        if not self.llm_enrichment:
            self.customer_facing_allowed = False
            self.human_review_required = True
            reasons.append("no_llm_enrichment")

        if self.confidence < 0.4:
            self.human_review_required = True
            reasons.append(f"low_confidence:{self.confidence:.2f}")

        if self.human_review_required:
            self.customer_facing_allowed = False

        if reasons and self.degraded_reason is None:
            self.degraded_reason = "; ".join(reasons)

    def mark_llm_enriched(
        self,
        model: str,
        prompt_tokens: int,
        completion_tokens: int,
        confidence: float,
    ) -> None:
        """Update enrichment fields after a successful LLM call.

        Resets governance flags to their optimistic defaults before
        re-applying rules, so a high-confidence enrichment can promote
        a previously degraded result to customer-facing.
        """
        self.llm_enrichment = True
        self.model_used = model
        self.prompt_tokens = prompt_tokens
        self.completion_tokens = completion_tokens
        self.confidence = confidence
        self.degraded_reason = None
        # Reset to optimistic defaults before re-evaluation
        self.customer_facing_allowed = True
        self.human_review_required = False
        self._apply_governance_rules()

    def to_dict(self) -> dict[str, Any]:
        """Serialise to a plain dict suitable for API responses."""
        return {
            "payload": self.payload,
            "workflow_type": self.workflow_type,
            "tenant_id": self.tenant_id,
            "llm_enrichment": self.llm_enrichment,
            "confidence": self.confidence,
            "customer_facing_allowed": self.customer_facing_allowed,
            "human_review_required": self.human_review_required,
            "degraded_reason": self.degraded_reason,
            "trace_id": self.trace_id,
            "model_used": self.model_used,
            "prompt_tokens": self.prompt_tokens,
            "completion_tokens": self.completion_tokens,
            "metadata": self.metadata,
        }
