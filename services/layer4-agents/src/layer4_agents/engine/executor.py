from __future__ import annotations

"""Orchestration Controller - Enhanced workflow execution engine.

Provides comprehensive workflow orchestration with:
- Multi-agent coordination
- Task scheduling with priorities
- Backpressure handling
- Message-based agent communication
- Failure recovery

This implements the OrchestrationController agent type from the specification.
"""


import asyncio
import logging
from collections.abc import Callable
from contextvars import Token
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import NodeInterrupt
from opentelemetry import trace
from value_fabric.shared.identity.context import (
    RequestContext,
    _current_context,
    set_request_context,
)

from ..models.agent_state import AgentState, WorkflowStatus
from .ports import TaskSchedulerPort
from .scheduler import TaskScheduler
from .types import ScheduledTask, TaskPriority


class WorkflowExecutionError(Exception):
    """Raised when workflow execution fails."""

    pass


class WorkflowPauseValidationError(WorkflowExecutionError, ValueError):
    """Raised when workflow pause request violates status or existence invariants."""

    pass


class CheckpointConflictError(WorkflowExecutionError):
    """Raised when checkpoint hash from caller is stale versus persisted latest state."""

    def __init__(self, message: str, metadata: dict[str, Any]):
        super().__init__(message)
        self.metadata = metadata


from value_fabric.shared.models.typed_dict import TypedDictModel

from ..agents.base import BaseAgent
from ..messaging.bus import InMemoryMessageBus, MessageBus
from ..messaging.router import MessageRouter
from ..messaging.types import MessageType
from ..observability import Layer4EventContext, Layer4LifecycleLogger
from ..registry.service import FALLBACK_LLM_MODEL, resolve_llm_model
from ..tools.registry import ToolRegistry
from ..workflows import WORKFLOW_TYPES, create_workflow
from .checkpoint_replay import (
    compute_state_hash,
    get_latest_persisted_checkpoint_hash,
    resolve_resume_policy,
)
from .execution_checkpointing import persist_interruption_if_needed
from .execution_dispatch import build_workflow_task, initialize_workflow_run_context
from .execution_persistence import (
    archive_workflow_state,
    mark_workflow_running,
    persist_workflow_failure,
    recover_orphaned_workflow_states,
)
from .execution_validation import (
    ensure_controller_accepts_execution,
    parse_and_enforce_approval_gate,
    validate_workflow_start_invariants,
)
from .output_contract import validate_final_output
from .state_manager import StateManager


class OrchestrationController_get_resultResult(TypedDictModel):
    completed_at: Any
    created_at: Any
    metadata: Any
    output: dict[str, Any]
    started_at: Any
    status: Any
    workflow_id: Any


class OrchestrationController_get_workflow_statusResult(TypedDictModel):
    completed_at: Any
    current_node: Any
    error_count: Any
    estimated_duration_seconds: Any
    has_output: Any
    priority: Any
    progress_percentage: Any
    scheduler_status: Any
    started_at: Any
    status: Any
    tenant_id: Any
    user_id: Any
    workflow_id: Any
    workflow_type: Any


class OrchestrationController_get_cluster_healthResult(TypedDictModel):
    active_workflows: Any
    avg_load: Any
    pending_tasks: Any
    registered_agents: Any
    running_tasks: Any
    status: Any
    utilization: Any


logger = logging.getLogger(__name__)
lifecycle_logger = Layer4LifecycleLogger(logger)
_tracer = trace.get_tracer(__name__)


TENANT_WORKFLOW_TIMEOUT_SETTINGS_PATHS: tuple[tuple[str, ...], ...] = (
    ("layer4", "workflow", "timeout_seconds"),
    ("layer4", "workflow_timeout_seconds"),
    ("workflow", "timeout_seconds"),
    ("workflow_timeout_seconds",),
)


# ---------------------------------------------------------------------------
# LLM Cost Metrics Integration Snippet
# ---------------------------------------------------------------------------
# When making LLM calls in tools (e.g., generation_tools.py), record cost
# and token usage via the Prometheus metrics helper:
#
#     from ..metrics import get_metrics
#     from ..metrics.llm_cost_calculator import LLMCostCalculator
#
#     calculator = LLMCostCalculator()
#     cost = calculator.calculate_cost(
#         provider="openai",
#         model="gpt-4o",
#         prompt_tokens=response.usage.prompt_tokens,
#         completion_tokens=response.usage.completion_tokens,
#     )
#     metrics = get_metrics()
#     if metrics:
#         metrics.record_llm_cost(
#             provider="openai",
#             model="gpt-4o",
#             tenant_id=str(tenant_id),
#             cost=cost,
#             prompt_tokens=response.usage.prompt_tokens,
#             completion_tokens=response.usage.completion_tokens,
#             status="success",
#         )
# ---------------------------------------------------------------------------


class OrchestrationController:
    """Enhanced workflow executor with multi-agent orchestration.

    Implements the OrchestrationController from the specification:
    - workflow_scheduling: Schedule workflows with priority
    - task_distribution: Distribute tasks to agents
    - failure_recovery: Handle failures with retry
    - resource_management: Manage agent pool scaling

    Scaling Policy: min_instances=2, max_instances=50

    Example:
        controller = OrchestrationController(
            tool_registry=tool_registry,
            message_bus=message_bus,
        )
        await controller.start()

        # Execute workflow
        result = await controller.execute_workflow(
            workflow_type="roi_calculator",
            input_data={"prospect_id": "123", ...},
            priority=TaskPriority.HIGH,
        )
    """

    @staticmethod
    def _fmt_enum(value: Any) -> str:
        """Serialize an enum-like value consistently."""
        return value.value if hasattr(value, "value") else str(value)

    @staticmethod
    def _fmt_dt(dt: datetime | None) -> str | None:
        """Serialize a datetime to ISO format."""
        return dt.isoformat() if dt else None

    def _lifecycle_context(
        self,
        workflow_id: str,
        *,
        tenant_id: str | None = None,
        checkpoint_id: str | None = None,
    ) -> Layer4EventContext:
        """Build a Layer4EventContext for lifecycle logging.

        Falls back to workflow metadata when no explicit tenant_id is provided.
        Uses distinct run_id and trace_id from the canonical run envelope when available.
        """
        meta = self._workflow_metadata.get(workflow_id, {})
        envelope_data = meta.get("run_envelope", {})

        kwargs: dict[str, Any] = {
            "request_id": workflow_id,
            "trace_id": envelope_data.get("trace_id") or workflow_id,
            "tenant_id": tenant_id or str(meta.get("tenant_id") or "unknown"),
            "workflow_id": workflow_id,
            "run_id": envelope_data.get("run_id") or workflow_id,
            "provider_name": "langgraph",
        }
        if checkpoint_id is not None:
            kwargs["checkpoint_id"] = checkpoint_id
        return Layer4EventContext(**kwargs)

    @staticmethod
    def _compute_state_hash(state: AgentState) -> str:
        """Compute a deterministic hash for checkpoint conflict detection."""
        return compute_state_hash(state)

    async def _resolve_resume_policy(
        self,
        *,
        workflow_id: str,
        state: AgentState,
        target_checkpoint_id: str | None = None,
    ) -> None:
        """Validate a resume attempt against the canonical ReplayConflictPolicy."""
        await resolve_resume_policy(
            self,
            workflow_id=workflow_id,
            state=state,
            target_checkpoint_id=target_checkpoint_id,
            workflow_execution_error_type=WorkflowExecutionError,
            checkpoint_conflict_error_type=CheckpointConflictError,
        )

    async def _get_latest_persisted_checkpoint_hash(
        self,
        *,
        tenant_id: str,
        workflow_id: str,
        run_id: str,
        checkpoint_id: str,
    ) -> str:
        """Load the latest persisted checkpoint hash from durable state."""
        return await get_latest_persisted_checkpoint_hash(
            self,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            run_id=run_id,
            checkpoint_id=checkpoint_id,
            workflow_execution_error_type=WorkflowExecutionError,
        )

    def __init__(
        self,
        tool_registry: ToolRegistry | None = None,
        state_manager: StateManager | None = None,
        message_bus: MessageBus | None = None,
        max_concurrent: int = 100,
        scaling_config: dict[str, Any] | None = None,
        checkpoint_saver: BaseCheckpointSaver | None = None,
        task_scheduler: TaskSchedulerPort | None = None,
    ):
        """Initialize orchestration controller.

        Args:
            tool_registry: Registry of available tools (optional, defaults to empty ToolRegistry)
            state_manager: State persistence manager
            message_bus: Message bus for agent communication
            max_concurrent: Maximum concurrent tasks
            scaling_config: Scaling policy configuration
            checkpoint_saver: LangGraph checkpoint saver for workflow persistence
            task_scheduler: Optional scheduler implementation for dependency injection
        """
        self.tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
        self.state_manager = state_manager or StateManager()
        self.message_bus = message_bus or InMemoryMessageBus()
        self.checkpoint_saver = checkpoint_saver
        self.max_concurrent = max_concurrent

        # Scaling configuration per spec
        self.scaling_config = scaling_config or {
            "min_instances": 2,
            "max_instances": 50,
            "scale_trigger": "queue_depth > 100",
        }

        # Task scheduling
        self.scheduler = task_scheduler or TaskScheduler(max_concurrent_tasks=max_concurrent)
        self.scheduler.set_callbacks(
            on_complete=self._on_task_complete,
            on_fail=self._on_task_fail,
        )
        self.scheduler.register_handler("workflow_execution", self._run_workflow_task)

        # Message routing
        self.message_router = MessageRouter(self.message_bus)

        # Agent management
        self._registered_agents: dict[str, BaseAgent] = {}
        self._agent_pool: dict[str, dict[str, Any]] = {}

        # Workflow tracking
        self._active_workflows: dict[str, asyncio.Task] = {}
        self._workflow_metadata: dict[str, dict[str, Any]] = {}

        # Replay-conflict deduplication tracking
        self._seen_replay_fingerprints: set[str] = set()

        # Lifecycle
        self._started = False
        self._shutdown = False

    async def start(self) -> None:
        """Start the orchestration controller."""
        if self._started:
            return

        await self.scheduler.start()
        self._started = True
        logger.info("OrchestrationController started")

    async def stop(self) -> None:
        """Stop the orchestration controller."""
        if not self._started:
            return

        self._shutdown = True
        await self._mark_active_workflows_interrupted("controller shutdown")

        # Cancel active workflows
        for workflow_id, task in list(self._active_workflows.items()):
            task.cancel()

        # Stop scheduler
        await self.scheduler.stop()

        # Close message bus
        await self.message_bus.close()

        self._started = False
        logger.info("OrchestrationController stopped")

    async def _mark_active_workflows_interrupted(self, reason: str) -> None:
        """Persist active workflow state before pod shutdown cancels tasks."""
        interrupted_at = datetime.now(UTC)
        for workflow_id in list(self._active_workflows):
            state = await self.state_manager.load_state(workflow_id)
            if not state or state.status in {
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
            }:
                continue
            state.status = WorkflowStatus.INTERRUPTED
            state.metadata["interrupted_at"] = interrupted_at.isoformat()
            state.metadata["interruption_reason"] = reason
            state.errors.append(f"Workflow interrupted by {reason} at {interrupted_at.isoformat()}")
            await self.state_manager.save_state(workflow_id, state)

    async def resolve_model(self, tenant_id: UUID, provider: str = "openai") -> str:
        """Resolve the active production LLM model for a tenant.

        Falls back to :data:`~registry.service.FALLBACK_LLM_MODEL` if no
        production model is registered or the lookup fails.
        """
        try:
            from value_fabric.shared.identity.context import RequestContext

            from ..database import db_session_for_context

            context = RequestContext(tenant_id=tenant_id)
            async with db_session_for_context(context) as db:
                return await resolve_llm_model(db, tenant_id, provider)
        except (ImportError, ConnectionError) as exc:
            logger.warning(
                "Failed to resolve LLM model for tenant %s (%s: %s), using fallback",
                tenant_id,
                type(exc).__name__,
                exc,
            )
            return FALLBACK_LLM_MODEL
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception(
                "Unexpected error resolving LLM model for tenant %s (type: %s), using fallback",
                tenant_id,
                type(exc).__name__,
            )
            return FALLBACK_LLM_MODEL

    async def register_agent(self, agent: BaseAgent) -> None:
        """Register an agent with the controller.

        Args:
            agent: Agent instance to register
        """
        await agent.initialize()

        self._registered_agents[agent.agent_id] = agent

        # Register with message router
        capabilities = agent.get_capabilities()
        capability_names = [c.name for c in capabilities]

        self.message_router.register_agent(
            agent_id=agent.agent_id,
            capabilities=capability_names,
            metadata={"agent_type": agent.agent_type},
        )

        # Subscribe to task assignments
        await self.message_bus.subscribe(
            subscriber_id=agent.agent_id,
            message_type=MessageType.TASK_ASSIGNMENT,
            handler=self._create_agent_handler(agent),
        )

        logger.info(f"Registered agent {agent.agent_id} ({agent.agent_type})")

    def unregister_agent(self, agent_id: str) -> None:
        """Unregister an agent.

        Args:
            agent_id: Agent to unregister
        """
        if agent_id in self._registered_agents:
            del self._registered_agents[agent_id]
            self.message_router.unregister_agent(agent_id)
            logger.info(f"Unregistered agent {agent_id}")

    async def execute_workflow(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        workflow_id: str | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        tenant_id: str | None = None,
        user_id: str | None = None,
        checkpoint_interval: int = 5,
    ) -> AgentState:
        """Execute a workflow with orchestration.

        Args:
            workflow_type: Type of workflow to run
            input_data: Workflow input parameters
            workflow_id: Optional workflow ID
            priority: Execution priority
            tenant_id: Tenant context
            user_id: User context
            checkpoint_interval: Save state every N nodes

        Returns:
            Final workflow state

        Raises:
            ConcurrencyLimitExceeded: If max concurrent workflows reached (P1-42)
            WorkflowTimeoutError: If workflow exceeds global timeout (P1-25)
            WorkflowExecutionError: If tenant_id is missing or empty
        """
        ensure_controller_accepts_execution(
            is_shutdown=self._shutdown,
            error_cls=WorkflowExecutionError,
        )

        validate_workflow_start_invariants(
            workflow_type=workflow_type,
            supported_types=WORKFLOW_TYPES,
            tenant_id=tenant_id,
            checkpoint_saver=self.checkpoint_saver,
            error_cls=WorkflowExecutionError,
        )

        approval_evidence = parse_and_enforce_approval_gate(
            workflow_id=workflow_id,
            input_data=input_data,
            tenant_id=tenant_id,
            error_cls=WorkflowExecutionError,
        )

        # P1-42: Check concurrent workflow limit
        active_count = len(self._active_workflows)
        if active_count >= self.max_concurrent:
            from ..exceptions import ConcurrencyLimitExceeded

            raise ConcurrencyLimitExceeded(
                f"Maximum concurrent workflows ({self.max_concurrent}) exceeded. "
                f"Current active: {active_count}. Retry after existing workflows complete."
            )

        # Resolve tenant-aware timeout and store metadata with timeout tracking
        resolved_timeout_seconds, timeout_source = await self._resolve_workflow_timeout_seconds(
            tenant_id
        )

        # Atomic deduplication: check if workflow_id already exists or is running
        if workflow_id:
            if workflow_id in self._active_workflows:
                logger.info(
                    "Workflow %s is currently active; awaiting completion for deduplication",
                    workflow_id,
                )
                return await self._wait_for_workflow_with_timeout(
                    workflow_id, timeout_seconds=resolved_timeout_seconds
                )
            existing_state = await self.state_manager.load_state(workflow_id)
            if existing_state is not None:
                if existing_state.tenant_id and existing_state.tenant_id != str(tenant_id):
                    raise WorkflowExecutionError("tenant_id mismatch: workflow access forbidden")
                logger.info(
                    "Workflow %s already exists with status %s; returning existing execution",
                    workflow_id,
                    existing_state.status,
                )
                if existing_state.status in (
                    WorkflowStatus.PENDING,
                    WorkflowStatus.RUNNING,
                ):
                    return await self._wait_for_workflow_with_timeout(
                        workflow_id, timeout_seconds=resolved_timeout_seconds
                    )
                return existing_state

        (
            wf_id,
            run_id,
            trace_id,
            workflow,
            initial_state,
            workflow_metadata,
        ) = initialize_workflow_run_context(
            workflow_type=workflow_type,
            input_data=input_data,
            tool_registry=self.tool_registry,
            checkpoint_saver=self.checkpoint_saver,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            priority_value=priority.value,
            approval_evidence=approval_evidence,
            resolved_timeout_seconds=resolved_timeout_seconds,
            timeout_source=timeout_source,
        )
        workflow_id = wf_id
        self._workflow_metadata[workflow_id] = workflow_metadata

        # Schedule workflow execution (Task 2.1: Capture tenant context)
        lifecycle_logger.emit(
            stage="start",
            context=Layer4EventContext(
                request_id=workflow_id,
                trace_id=trace_id,
                tenant_id=tenant_id,
                workflow_id=workflow_id,
                run_id=run_id,
                provider_name="langgraph",
            ),
            workflow_type=workflow_type,
        )

        initial_state.status = WorkflowStatus.PENDING
        initial_state.started_at = datetime.now(UTC)
        await self.state_manager.save_state(workflow_id, initial_state)

        task = build_workflow_task(  # type: ignore[call-arg]
            priority=priority.value,
            workflow_id=workflow_id,
            tenant_id=tenant_id,
            user_id=user_id,
            workflow_type=workflow_type,
            workflow=workflow,
            initial_state=initial_state,
            checkpoint_interval=checkpoint_interval,
            handler=self._run_workflow_task,
        )

        await self.scheduler.schedule_task(task)

        # P1-25: Wait for completion with global timeout
        result = await self._wait_for_workflow_with_timeout(
            workflow_id, timeout_seconds=resolved_timeout_seconds
        )

        # Hardening: validate reasoning trace with strict schema enforcement
        if result.status not in {
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        }:
            try:
                from ..models.reasoning_trace import validate_reasoning_trace

                validate_reasoning_trace(result.reasoning_trace, strict=True)
            except ValueError as exc:
                result.status = WorkflowStatus.FAILED
                result.errors.append(f"{type(exc).__name__}: reasoning_trace_invalid")
                lifecycle_logger.emit(
                    stage="reasoning_trace_invalid",
                    context=self._lifecycle_context(workflow_id),
                    workflow_type=workflow_type,
                    error_class="ValueError",
                    error_code="REASONING_TRACE_INVALID",
                )
                await self.state_manager.save_state(workflow_id, result)

        return result

    async def run(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        workflow_id: str | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        tenant_id: str | None = None,
        user_id: str | None = None,
        checkpoint_interval: int = 5,
    ) -> AgentState:
        """Backward-compatible workflow entrypoint.

        Routes and older callers historically used ``run(...)``. This method
        delegates to ``execute_workflow(...)`` so all call sites share the
        same durable orchestration path.
        """
        return await self.execute_workflow(
            workflow_type=workflow_type,
            input_data=input_data,
            workflow_id=workflow_id,
            priority=priority,
            tenant_id=tenant_id,
            user_id=user_id,
            checkpoint_interval=checkpoint_interval,
        )

    async def get_result(self, workflow_id: str) -> dict[str, Any] | None:
        """Get a durable workflow result by workflow ID.

        Reads persisted workflow state via ``StateManager`` and returns a
        route-friendly shape used by analysis/tools endpoints.
        """
        state = await self.state_manager.load_state(workflow_id)
        if not state:
            return None

        persisted_metadata = dict(state.metadata or {})
        if "workflow_id" not in persisted_metadata:
            persisted_metadata["workflow_id"] = state.workflow_id
        if "workflow_type" not in persisted_metadata:
            persisted_metadata["workflow_type"] = self._fmt_enum(state.workflow_type)

        output = dict(state.output_data or {})
        if state.reasoning_trace is not None:
            output["reasoning_trace"] = state.reasoning_trace.model_dump(mode="json")

        result_metadata = persisted_metadata
        if state.run_envelope is not None:
            result_metadata["run_envelope"] = state.run_envelope.model_dump()

        # Prefer canonical run envelope for identity fields when available
        envelope = state.run_envelope
        return OrchestrationController_get_resultResult.model_validate(
            {  # type: ignore[no-any-return]
                "workflow_id": envelope.workflow_id if envelope else state.workflow_id,
                "run_id": envelope.run_id if envelope else state.run_id,
                "trace_id": envelope.trace_id if envelope else state.trace_id,
                "output": output,
                "metadata": result_metadata,
                "status": self._fmt_enum(state.status),
                "created_at": self._fmt_dt(state.started_at),
                "started_at": self._fmt_dt(state.started_at),
                "completed_at": self._fmt_dt(state.completed_at),
            }
        )

    async def schedule_workflow(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        scheduled_time: datetime | None = None,
        priority: TaskPriority = TaskPriority.NORMAL,
        tenant_id: str | None = None,
        user_id: str | None = None,
    ) -> str:
        """Schedule workflow for future execution.

        Args:
            workflow_type: Type of workflow
            input_data: Input parameters
            scheduled_time: When to execute (default: now)
            priority: Execution priority
            tenant_id: Tenant context
            user_id: User context

        Returns:
            schedule_id: ID for tracking

        Raises:
            WorkflowExecutionError: If tenant_id is missing or empty
        """
        # HARDENING: Tenant scope is a mandatory workflow-start invariant
        if not tenant_id or not tenant_id.strip():
            raise WorkflowExecutionError("tenant_id is required: scheduled workflow start rejected")

        schedule_id = f"sched-{datetime.now(UTC).timestamp()}"

        execute_time = scheduled_time or datetime.now(UTC)
        workflow = create_workflow(workflow_type, self.tool_registry, self.checkpoint_saver)
        initial_state = workflow.create_initial_state(
            input_data,
            tenant_id=tenant_id,
        )
        initial_state.workflow_id = schedule_id
        initial_state.status = WorkflowStatus.PENDING
        initial_state.started_at = execute_time

        # Generate canonical run envelope for scheduled workflows
        from uuid import uuid4

        from ..models.run_envelope import RunEnvelope

        run_id = str(uuid4())
        trace_id = str(uuid4())
        envelope = RunEnvelope(
            run_id=run_id,
            workflow_id=schedule_id,
            trace_id=trace_id,
            tenant_id=str(tenant_id) if tenant_id else "",
            workflow_type=workflow_type,
        )
        initial_state.run_envelope = envelope
        initial_state.run_id = run_id
        initial_state.trace_id = trace_id

        self._workflow_metadata[schedule_id] = {
            "workflow_type": workflow_type,
            "tenant_id": tenant_id,
            "user_id": user_id,
            "priority": priority.value,
            "scheduled_at": execute_time.isoformat(),
            "run_envelope": envelope.model_dump(),
        }
        await self.state_manager.save_state(schedule_id, initial_state)

        # Create scheduled task
        task = ScheduledTask(
            priority=priority.value,
            scheduled_time=execute_time,
            task_id=schedule_id,
            workflow_instance_id=schedule_id,
            capability="workflow_execution",
            agent_type="OrchestrationController",
            context={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "workflow_type": workflow_type,
            },
            parameters={
                "workflow": workflow,
                "initial_state": initial_state,
                "workflow_id": schedule_id,
                "workflow_type": workflow_type,
                "input_data": input_data,
                "tenant_id": tenant_id,
                "user_id": user_id,
                "handler": self._run_workflow_task,
            },
            tenant_id=tenant_id,
            tenant_context={
                "tenant_id": tenant_id,
                "user_id": user_id,
                "workflow_type": workflow_type,
                "auth_source": "scheduled_workflow",
            },
        )

        await self.scheduler.schedule_task(task)

        logger.info(f"Scheduled workflow {schedule_id} for {execute_time}")
        return schedule_id

    async def distribute_task(
        self,
        capability: str,
        parameters: dict[str, Any],
        priority: TaskPriority = TaskPriority.NORMAL,
        tenant_id: str | None = None,
        timeout_seconds: int = 300,
    ) -> str | None:
        """Distribute task to appropriate agent.

        Args:
            capability: Required capability
            parameters: Task parameters
            priority: Task priority
            tenant_id: Tenant context
            timeout_seconds: Task timeout

        Returns:
            task_id: ID of scheduled task, or None if no agent available
        """
        # Route to agent
        agent_id = self.message_router.route_task(capability)

        if not agent_id:
            logger.warning(f"No agent available for capability: {capability}")
            return None

        # Create and schedule task
        task_id = f"task-{datetime.now(UTC).timestamp()}"

        task = ScheduledTask(
            priority=priority.value,
            scheduled_time=datetime.now(UTC),
            task_id=task_id,
            workflow_instance_id=task_id,
            capability=capability,
            agent_type=getattr(self._registered_agents.get(agent_id), "agent_type", "Unknown"),
            context={"tenant_id": tenant_id},
            parameters=parameters,
            timeout_seconds=timeout_seconds,
        )

        await self.scheduler.schedule_task(task)

        # Send task assignment via message bus
        await self.message_bus.publish(
            agent_id="orchestrator",
            event_type=MessageType.TASK_ASSIGNMENT,
            payload={
                "task_id": task_id,
                "capability": capability,
                "parameters": parameters,
            },
            recipient_id=agent_id,
        )

        return task_id

    async def get_workflow_status(self, workflow_id: str) -> dict[str, Any] | None:
        """Get workflow status with orchestration context.

        Args:
            workflow_id: Workflow identifier

        Returns:
            Status dict with progress information
        """
        # Get base state
        state = await self.state_manager.load_state(workflow_id)
        if not state:
            return None

        # Get scheduler status
        scheduler_status = await self.scheduler.get_task_status(f"wf-{workflow_id}")

        # Prefer in-memory metadata when present, but fall back to persisted
        # state metadata so completed workflows remain tenant-scoped after
        # process restarts and deterministic seed runs.
        metadata = dict(state.metadata or {})
        metadata.update(self._workflow_metadata.get(workflow_id, {}))

        # Prefer canonical run envelope for identity fields when available
        envelope = state.run_envelope
        if envelope is None:
            envelope_data = metadata.get("run_envelope", {})
        else:
            envelope_data = envelope.model_dump()

        return OrchestrationController_get_workflow_statusResult.model_validate(
            {  # type: ignore[no-any-return]
                "workflow_id": workflow_id,
                "workflow_type": self._fmt_enum(state.workflow_type),
                "status": self._fmt_enum(state.status),
                "current_node": state.current_node,
                "progress_percentage": self._calculate_progress(state),
                "started_at": self._fmt_dt(state.started_at),
                "completed_at": self._fmt_dt(state.completed_at),
                "estimated_duration_seconds": metadata.get("estimated_duration"),
                "error_count": len(state.errors),
                "has_output": bool(state.output_data),
                "tenant_id": (envelope.tenant_id if envelope else metadata.get("tenant_id")),
                "user_id": metadata.get("user_id"),
                "priority": metadata.get("priority"),
                "scheduler_status": (scheduler_status.get("status") if scheduler_status else None),
                "run_id": (
                    envelope.run_id if envelope else envelope_data.get("run_id") or state.run_id
                ),
                "trace_id": (
                    envelope.trace_id
                    if envelope
                    else envelope_data.get("trace_id") or state.trace_id
                ),
                "checkpoint_id": envelope.checkpoint_id if envelope else None,
            }
        )

    async def cancel_workflow(self, workflow_id: str, reason: str | None = None) -> bool:
        """Cancel a workflow.

        Args:
            workflow_id: Workflow to cancel
            reason: Optional reason for cancellation (logged for audit)

        Returns:
            True if cancelled
        """
        # Log cancellation reason for audit trail
        if reason:
            logger.info(f"Cancelling workflow {workflow_id}: {reason}")

        # Cancel in scheduler
        cancelled = await self.scheduler.cancel_task(f"wf-{workflow_id}")

        # Cancel active task
        if workflow_id in self._active_workflows:
            task = self._active_workflows[workflow_id]
            if not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Update state
        state = await self.state_manager.load_state(workflow_id)
        if state:
            state.status = WorkflowStatus.CANCELLED
            state.completed_at = datetime.now(UTC)
            await self.state_manager.save_state(workflow_id, state)

        lifecycle_logger.emit(
            stage="cancel",
            context=self._lifecycle_context(workflow_id),
            cancel_reason=reason,
        )
        return cancelled

    async def pause_workflow(
        self,
        workflow_id: str,
        user_id: str,
        reason: str | None = None,
    ) -> bool:
        """Pause a running or queued workflow and persist a resumable state.

        Uses WorkflowStatus.INTERRUPTED (native LangGraph HITL semantics) instead
        of the legacy PAUSED status. The checkpoint is persisted by the
        checkpointer; StateManager holds a mirror for API compatibility.
        """
        state = await self.state_manager.load_state(workflow_id)
        if not state:
            raise WorkflowPauseValidationError(f"Workflow {workflow_id} not found")

        if state.status in [
            WorkflowStatus.COMPLETED,
            WorkflowStatus.FAILED,
            WorkflowStatus.CANCELLED,
        ]:
            raise WorkflowPauseValidationError(
                f"Workflow {workflow_id} is {state.status.value} and cannot be paused"
            )

        if state.status == WorkflowStatus.INTERRUPTED:
            raise WorkflowPauseValidationError(f"Workflow {workflow_id} is already interrupted")

        await self.scheduler.cancel_task(f"wf-{workflow_id}")
        await self.scheduler.cancel_task(workflow_id)

        if workflow_id in self._active_workflows:
            running = self._active_workflows[workflow_id]
            if not running.done():
                running.cancel()

        paused_at = datetime.now(UTC)
        state.status = WorkflowStatus.INTERRUPTED
        state.paused_at = paused_at
        state.paused_by = user_id
        state.pause_count = (state.pause_count or 0) + 1
        state.pause_point = {
            "title": "Workflow interrupted",
            "reason": reason or "Manual pause requested",
            "severity": "info",
            "node": state.current_node,
            "required_inputs": [],
            "paused_at": paused_at.isoformat(),
        }
        state.metadata["pause_reason"] = reason
        state.metadata["paused_by"] = user_id
        state.metadata["paused_at"] = paused_at.isoformat()
        state.metadata["checkpoint_hash"] = self._compute_state_hash(state)
        await self.state_manager.save_state(workflow_id, state)
        logger.info("Interrupted workflow %s at node %s", workflow_id, state.current_node)
        tenant_id = str(
            (state.metadata or {}).get("tenant_id")
            or self._workflow_metadata.get(workflow_id, {}).get("tenant_id")
            or "unknown"
        )
        lifecycle_logger.emit(
            stage="checkpoint",
            context=self._lifecycle_context(
                workflow_id,
                tenant_id=tenant_id,
                checkpoint_id=str(state.current_node or "interrupted"),
            ),
        )
        return True

    async def archive_workflow(
        self, workflow_id: str, tenant_id: str | None = None
    ) -> dict[str, Any] | None:
        """Archive a workflow.

        Args:
            workflow_id: Workflow to archive
            tenant_id: Optional tenant for ownership verification

        Returns:
            Dict with archived_at timestamp if archived, None if not found,
            or raises PermissionError if tenant mismatch.
        """
        logger.info(f"Archiving workflow {workflow_id}")
        return await archive_workflow_state(
            state_manager=self.state_manager,
            workflow_id=workflow_id,
            workflow_metadata=self._workflow_metadata,
            tenant_id=tenant_id,
        )

    async def resume_workflow(
        self,
        workflow_id: str,
        user_id: str,
        resume_data: dict[str, Any] | None = None,
    ) -> AgentState:
        """Resume a workflow from its last checkpoint.

        Reloads workflow state from checkpoint storage and continues execution
        from the last completed node. Supports human-in-the-loop workflows where
        execution pauses for user input/decisions.

        Validates against the canonical ReplayConflictPolicy with real hashes.

        Args:
            workflow_id: Workflow to resume
            user_id: User initiating resume
            resume_data: Optional user input/decision data to merge into state

        Returns:
            Final or updated workflow state

        Raises:
            WorkflowExecutionError: If workflow not found, completed, or resume fails
        """
        # Load existing state
        state = await self.state_manager.load_state(workflow_id)
        if not state:
            raise WorkflowExecutionError(f"No state found for workflow {workflow_id}")

        # Check if workflow is in a resumable state
        if state.status not in [
            WorkflowStatus.PAUSED,
            WorkflowStatus.RUNNING,
            WorkflowStatus.PENDING,
            WorkflowStatus.INTERRUPTED,
        ]:
            raise WorkflowExecutionError(
                f"Workflow {workflow_id} is {state.status.value} and cannot be resumed. "
                f"Only PAUSED, RUNNING, PENDING, or INTERRUPTED workflows can be resumed."
            )

        # Validate workflow_id matches state
        if state.workflow_id != workflow_id:
            raise WorkflowExecutionError(
                f"Workflow ID mismatch: requested {workflow_id} but state has {state.workflow_id}"
            )

        # Validate against replay-conflict policy with real hashes
        await self._resolve_resume_policy(workflow_id=workflow_id, state=state)

        # Merge resume data into state if provided
        if resume_data:
            if state.output_data is None:
                state.output_data = {}
            state.output_data["resume_decision"] = resume_data
            state.output_data["resumed_by"] = user_id
            state.output_data["resumed_at"] = datetime.now(UTC).isoformat()

        # Get workflow type from metadata
        metadata = self._workflow_metadata.get(workflow_id, {})
        workflow_type = metadata.get("workflow_type")

        if not workflow_type:
            raise WorkflowExecutionError(f"No workflow type found for {workflow_id}")

        # Re-create workflow with checkpoint saver.
        workflow = create_workflow(workflow_type, self.tool_registry, self.checkpoint_saver)

        # Update metadata
        metadata["resumed_at"] = datetime.now(UTC).isoformat()
        metadata["resumed_by"] = user_id

        # Resume execution
        try:
            result = await workflow.run(state, thread_id=workflow_id, resume_data=resume_data)
        except WorkflowExecutionError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise WorkflowExecutionError(f"Failed to resume workflow {workflow_id}: {e}") from e

        # Update run envelope with latest checkpoint reference
        if result.run_envelope is not None:
            result.run_envelope = result.run_envelope.with_checkpoint(
                checkpoint_id=str(result.current_node or "resume")
            )
            await self.state_manager.save_state(workflow_id, result)

        lifecycle_logger.emit(
            stage="resume",
            context=self._lifecycle_context(
                workflow_id,
                tenant_id=str(metadata.get("tenant_id") or "unknown"),
                checkpoint_id=str(result.current_node or "resume"),
            ),
            resumed_by=user_id,
        )
        return result

    async def resume_from_checkpoint(
        self,
        workflow_id: str,
        checkpoint_id: str,
        user_id: str,
        resume_data: dict[str, Any] | None = None,
        skip_nodes: list[str] | None = None,
    ) -> dict[str, Any]:
        """Resume a workflow from a specific checkpoint.

        Loads the workflow state, validates against the replay-conflict policy
        with real hashes, updates the run envelope, and continues execution.

        Args:
            workflow_id: Workflow to resume
            checkpoint_id: Specific checkpoint identifier to resume from
            user_id: User initiating resume
            resume_data: Optional user input/decision data
            skip_nodes: Optional node IDs to skip (not yet implemented)

        Returns:
            Dict with status and result metadata

        Raises:
            WorkflowExecutionError: If workflow not found, checkpoint invalid,
                or resume fails policy validation.
        """
        # Load existing state
        state = await self.state_manager.load_state(workflow_id)
        if not state:
            raise WorkflowExecutionError(f"No state found for workflow {workflow_id}")

        if state.status not in [
            WorkflowStatus.PAUSED,
            WorkflowStatus.RUNNING,
            WorkflowStatus.PENDING,
            WorkflowStatus.INTERRUPTED,
        ]:
            raise WorkflowExecutionError(
                f"Workflow {workflow_id} is {state.status.value} and cannot be resumed."
            )

        if state.workflow_id != workflow_id:
            raise WorkflowExecutionError(
                f"Workflow ID mismatch: requested {workflow_id} but state has {state.workflow_id}"
            )

        # Validate against replay-conflict policy with real hashes
        await self._resolve_resume_policy(
            workflow_id=workflow_id,
            state=state,
            target_checkpoint_id=checkpoint_id,
        )

        # Merge resume data
        if resume_data:
            if state.output_data is None:
                state.output_data = {}
            state.output_data["resume_decision"] = resume_data
            state.output_data["resumed_by"] = user_id
            state.output_data["resumed_at"] = datetime.now(UTC).isoformat()

        # Update envelope with target checkpoint
        if state.run_envelope is not None:
            state.run_envelope = state.run_envelope.with_checkpoint(checkpoint_id)

        # Get workflow type
        metadata = self._workflow_metadata.get(workflow_id, {})
        workflow_type = metadata.get("workflow_type")
        if not workflow_type:
            raise WorkflowExecutionError(f"No workflow type found for {workflow_id}")

        workflow = create_workflow(workflow_type, self.tool_registry, self.checkpoint_saver)

        metadata["resumed_at"] = datetime.now(UTC).isoformat()
        metadata["resumed_by"] = user_id
        metadata["resumed_from_checkpoint"] = checkpoint_id

        try:
            result = await workflow.run(
                state,
                thread_id=workflow_id,
                checkpoint_config={"checkpoint_id": checkpoint_id},
                resume_data=resume_data,
            )
        except WorkflowExecutionError:
            raise
        except asyncio.CancelledError:
            raise
        except Exception as e:
            raise WorkflowExecutionError(
                f"Failed to resume workflow {workflow_id} from checkpoint {checkpoint_id}: {e}"
            ) from e

        # Update envelope with post-resume checkpoint reference
        if result.run_envelope is not None:
            result.run_envelope = result.run_envelope.with_checkpoint(
                checkpoint_id=str(result.current_node or checkpoint_id)
            )
            await self.state_manager.save_state(workflow_id, result)

        lifecycle_logger.emit(
            stage="resume_from_checkpoint",
            context=self._lifecycle_context(
                workflow_id,
                tenant_id=str(metadata.get("tenant_id") or "unknown"),
                checkpoint_id=checkpoint_id,
            ),
            resumed_by=user_id,
            checkpoint_id=checkpoint_id,
        )

        return {
            "status": self._fmt_enum(result.status),
            "workflow_id": workflow_id,
            "checkpoint_id": checkpoint_id,
            "current_node": result.current_node,
        }

    async def list_active_workflows(
        self,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List active workflows.

        Excludes archived workflows regardless of status.

        Args:
            tenant_id: Filter by tenant

        Returns:
            List of workflow status dicts
        """
        active = []

        for workflow_id, metadata in self._workflow_metadata.items():
            if tenant_id and metadata.get("tenant_id") != tenant_id:
                continue

            # Skip archived workflows
            state = await self.state_manager.load_state(workflow_id)
            if state and state.metadata.get("archived"):
                continue

            status = await self.get_workflow_status(workflow_id)
            if status and status.get("status") in ["pending", "running", "retrying"]:
                active.append(status)

        return active

    async def list_workflows(
        self,
        tenant_id: str | None = None,
    ) -> list[dict[str, Any]]:
        """List persisted workflows for API consumers, including completed ones.

        This does not replace ``list_active_workflows`` because recovery should
        continue to scan only active workflow states.
        """
        workflows: list[dict[str, Any]] = []
        workflow_ids = await self.state_manager.list_workflows()

        for workflow_id in workflow_ids:
            state = await self.state_manager.load_state(workflow_id)
            if not state or state.metadata.get("archived"):
                continue

            status = await self.get_workflow_status(workflow_id)
            if not status:
                continue

            workflow_tenant = status.get("tenant_id")
            if tenant_id and str(workflow_tenant) != str(tenant_id):
                continue

            workflows.append(status)

        return sorted(
            workflows,
            key=lambda item: str(item.get("completed_at") or item.get("started_at") or ""),
            reverse=True,
        )

    def get_cluster_health(self) -> dict[str, Any]:
        """Get orchestration cluster health.

        Returns:
            Health metrics
        """
        router_health = self.message_router.get_cluster_health()
        scheduler_stats = self.scheduler.get_stats()

        return OrchestrationController_get_cluster_healthResult.model_validate(
            {  # type: ignore[no-any-return]
                "status": router_health.get("status", "unknown"),
                "registered_agents": len(self._registered_agents),
                "active_workflows": len(self._active_workflows),
                "pending_tasks": scheduler_stats.get("pending_tasks", 0),
                "running_tasks": scheduler_stats.get("running_tasks", 0),
                "avg_load": router_health.get("avg_load", 0),
                "utilization": scheduler_stats.get("utilization", 0),
            }
        )

    async def recover_workflows(self) -> list[dict[str, Any]]:
        """On startup, identify and handle orphaned workflows from previous pod.

        Called during application startup to find workflows that were RUNNING/PENDING
        in Redis but not in this pod's memory. Marks them as INTERRUPTED for
        manual review or auto-resume.

        Returns:
            List of recovered workflow IDs with status
        """
        logger.info("Scanning for orphaned workflows to recover...")
        return await recover_orphaned_workflow_states(
            state_manager=self.state_manager,
            active_workflow_ids=set(self._active_workflows.keys()),
            format_enum=self._fmt_enum,
        )

    def _create_agent_handler(
        self,
        agent: BaseAgent,
    ) -> Callable:
        """Create message handler for an agent.

        Args:
            agent: Agent to handle messages

        Returns:
            Handler function
        """

        async def handler(message):
            if message.message_type == MessageType.TASK_ASSIGNMENT:
                payload = message.payload
                task = {
                    "capability": payload.get("capability"),
                    "parameters": payload.get("parameters"),
                }
                context = {
                    "tenant_id": payload.get("tenant_id", None),
                    "correlation_id": message.correlation_id,
                }

                try:
                    result = await agent.run(task, context)

                    # Send result back
                    await self.message_bus.publish(
                        agent_id=agent.agent_id,
                        event_type=MessageType.TASK_RESULT,
                        payload={
                            "task_id": payload.get("task_id"),
                            "success": True,
                            "result": result,
                        },
                        recipient_id=message.sender_id,
                        correlation_id=message.correlation_id,
                    )
                except (ValueError, RuntimeError, TimeoutError):
                    # Send error
                    await self.message_bus.publish(
                        agent_id=agent.agent_id,
                        event_type=MessageType.ERROR_NOTIFICATION,
                        payload={
                            "task_id": payload.get("task_id"),
                            "success": False,
                            "error": "Task execution failed",
                            "error_code": "TASK_EXECUTION_ERROR",
                        },
                        recipient_id=message.sender_id,
                        correlation_id=message.correlation_id,
                    )

        return handler

    @staticmethod
    def _set_workflow_request_context(
        *,
        task: ScheduledTask,
        workflow_id: str,
        tenant_id: str,
    ) -> Token | None:
        """Propagate authenticated workflow context into background execution."""
        try:
            workflow_ctx = RequestContext(
                tenant_id=tenant_id,
                user_id=task.context.get("user_id") or "workflow_executor",
                roles=["tenant_admin"],
                auth_source="workflow_execution",
                request_id=workflow_id,
                trace_id=task.context.get("trace_id") or workflow_id,
            )
            return set_request_context(workflow_ctx)
        except Exception as ctx_exc:
            logger.warning("Failed to set workflow RequestContext: %s", ctx_exc)
            return None

    @staticmethod
    def _reset_workflow_request_context(ctx_token: Token | None) -> None:
        """Reset a workflow RequestContext token created for background execution."""
        if ctx_token is not None:
            _current_context.reset(ctx_token)

    async def _run_workflow_task(self, task: ScheduledTask) -> AgentState:
        """Execute a scheduled workflow task and persist state transitions."""
        workflow = task.parameters.get("workflow")
        initial_state = task.parameters.get("initial_state")
        workflow_id = task.parameters.get("workflow_id") or task.workflow_instance_id

        if workflow is None or initial_state is None:
            raise WorkflowExecutionError(
                f"Workflow task {task.task_id} missing workflow or initial_state"
            )

        # KILL-SWITCH: Block workflow execution for suspended tenants
        tenant_id = task.get_tenant_id()
        if tenant_id:
            try:
                from value_fabric.shared.tenant_kill_switch import TenantKillSwitch

                kill_switch = TenantKillSwitch()
                if await kill_switch.is_suspended(tenant_id):
                    raise WorkflowExecutionError(
                        f"Tenant {tenant_id} is suspended: workflow execution blocked"
                    )
            except WorkflowExecutionError:
                raise
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "tenant_kill_switch_check_failed",
                    extra={"tenant_id": tenant_id, "error": str(exc)},
                )
                raise WorkflowExecutionError(
                    f"Tenant kill-switch check failed for {tenant_id}; "
                    "blocking workflow execution as a fail-closed safety measure."
                ) from exc

        await mark_workflow_running(
            state_manager=self.state_manager,
            workflow_id=workflow_id,
            initial_state=initial_state,
        )
        current_task = asyncio.current_task()
        if current_task is None:
            raise RuntimeError("No current task available")
        self._active_workflows[workflow_id] = current_task

        try:
            from ..config.settings import get_settings

            timeout_seconds = float(
                task.parameters.get("timeout_seconds", get_settings().workflow_timeout_seconds)
            )
            wf_type = task.parameters.get("workflow_type", "unknown")
            tenant_id_for_trace = task.get_tenant_id() or "unknown"

            ctx_token = self._set_workflow_request_context(
                task=task,
                workflow_id=workflow_id,
                tenant_id=tenant_id_for_trace,
            )

            try:
                with _tracer.start_as_current_span(
                    "layer4.workflow.execute",
                    attributes={
                        "workflow.id": workflow_id,
                        "workflow.type": wf_type,
                        "tenant.id": tenant_id_for_trace,
                    },
                ) as span:
                    result = await asyncio.wait_for(
                        workflow.run(initial_state, thread_id=workflow_id),
                        timeout=timeout_seconds,
                    )
                    span.set_attribute("workflow.status", self._fmt_enum(result.status))
            finally:
                self._reset_workflow_request_context(ctx_token)

            if result.status == WorkflowStatus.COMPLETED:
                validation = validate_final_output(result)
                result.metadata["output_validation"] = validation.model_dump(mode="json")
                if not validation.valid:
                    result.status = WorkflowStatus.FAILED
                    result.metadata["needs_review"] = True
                    result.metadata["recoverable_failure"] = True
                    result.output_data = {
                        **(result.output_data or {}),
                        "error": {
                            "code": "WORKFLOW_OUTPUT_SCHEMA_VALIDATION_FAILED",
                            "message": "Workflow output failed contract validation and requires review.",
                            "recoverable": True,
                            "details": validation.errors,
                        },
                    }
                    result.errors.extend(
                        [f"OUTPUT_SCHEMA_VALIDATION_FAILED: {err}" for err in validation.errors]
                    )

            await self.state_manager.save_state(workflow_id, result)

            # Native LangGraph HITL interrupt: checkpoint already persisted
            if result.status == WorkflowStatus.INTERRUPTED:
                lifecycle_logger.emit(
                    stage="checkpoint",
                    context=self._lifecycle_context(workflow_id),
                    checkpoint_id=str(result.current_node or "interrupted"),
                )
                return result  # type: ignore[no-any-return]

            lifecycle_logger.emit(
                stage="completion",
                context=self._lifecycle_context(workflow_id),
            )
            return result  # type: ignore[no-any-return]
        except TimeoutError as exc:
            await persist_workflow_failure(
                state_manager=self.state_manager,
                workflow_id=workflow_id,
                initial_state=initial_state,
                exc=exc,
            )
            lifecycle_logger.emit(
                stage="failure",
                context=self._lifecycle_context(workflow_id),
                error_class="TimeoutError",
                error_code="WORKFLOW_TIMEOUT",
            )
            raise WorkflowExecutionError(
                f"Workflow {workflow_id} exceeded global timeout of {timeout_seconds}s"
            ) from exc
        except NodeInterrupt:
            # Native LangGraph HITL - checkpoint already persisted by checkpointer
            paused = await self.state_manager.load_state(workflow_id)
            if paused:
                paused.status = WorkflowStatus.INTERRUPTED
                await self.state_manager.save_state(workflow_id, paused)
            raise
        except asyncio.CancelledError:
            await persist_interruption_if_needed(
                state_manager=self.state_manager,
                workflow_id=workflow_id,
            )
            paused = await self.state_manager.load_state(workflow_id)
            if paused and paused.status in {
                WorkflowStatus.PAUSED,
                WorkflowStatus.INTERRUPTED,
            }:
                raise
            raise
        except (RuntimeError, ValueError) as exc:
            await persist_workflow_failure(
                state_manager=self.state_manager,
                workflow_id=workflow_id,
                initial_state=initial_state,
                exc=exc,
            )
            lifecycle_logger.emit(
                stage="failure",
                context=self._lifecycle_context(workflow_id),
                error_class=type(exc).__name__,
                error_code="WORKFLOW_EXECUTION_ERROR",
            )
            raise
        except Exception as exc:
            # Catch-all for LangGraph errors (InvalidUpdateError, etc.) and
            # any other unexpected exceptions so the state manager is always
            # updated and the HTTP client receives a timely response.
            await persist_workflow_failure(
                state_manager=self.state_manager,
                workflow_id=workflow_id,
                initial_state=initial_state,
                exc=exc,
            )
            lifecycle_logger.emit(
                stage="failure",
                context=self._lifecycle_context(workflow_id),
                error_class=type(exc).__name__,
                error_code="WORKFLOW_EXECUTION_ERROR",
            )
            raise
        finally:
            self._active_workflows.pop(workflow_id, None)

    async def _wait_for_workflow_with_timeout(
        self, workflow_id: str, timeout_seconds: int
    ) -> AgentState:
        """Wait for workflow completion with global timeout (P1-25).

        Args:
            workflow_id: Workflow to wait for
            timeout_seconds: Maximum time to wait before failing

        Returns:
            Final workflow state

        Raises:
            WorkflowTimeoutError: If workflow exceeds timeout
        """
        from ..exceptions import WorkflowTimeoutError

        start_time = datetime.now(UTC)

        # Fast path: if this pod owns the live task, await the asyncio task
        # directly instead of polling the state store every 500ms.
        # _run_workflow_task persists the final state before returning (and
        # persists failures), so awaiting the task yields the identical state
        # the polling loop would read back — no save_state semantics change.
        task = self._active_workflows.get(workflow_id)
        if task is not None and timeout_seconds > 0:
            try:
                await asyncio.wait_for(asyncio.shield(task), timeout=timeout_seconds)
            except TimeoutError:
                # Preserve the existing global-timeout behavior: cancel the
                # workflow, then raise WorkflowTimeoutError.
                await self.cancel_workflow(
                    workflow_id,
                    reason=f"Global timeout exceeded ({timeout_seconds}s)",
                )
                raise WorkflowTimeoutError(
                    f"Workflow {workflow_id} timed out after {timeout_seconds} seconds"
                )
            except asyncio.CancelledError:
                raise
            except Exception:
                # _run_workflow_task persists failures before re-raising; the
                # terminal FAILED state is already in the store. Fall through
                # to the polling loop to read it.
                pass

            state = await self.state_manager.load_state(workflow_id)
            if state and state.status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
                WorkflowStatus.INTERRUPTED,
            ]:
                return state

        while True:
            # Check for timeout
            elapsed = (datetime.now(UTC) - start_time).total_seconds()
            if elapsed > timeout_seconds:
                # Cancel the workflow
                await self.cancel_workflow(
                    workflow_id, reason=f"Global timeout exceeded ({timeout_seconds}s)"
                )
                raise WorkflowTimeoutError(
                    f"Workflow {workflow_id} timed out after {timeout_seconds} seconds"
                )

            state = await self.state_manager.load_state(workflow_id)

            if state and state.status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
                WorkflowStatus.INTERRUPTED,
            ]:
                return state

            await asyncio.sleep(0.5)

    def _extract_tenant_timeout(self, tenant_settings: dict[str, Any] | None) -> int | None:
        if not tenant_settings:
            return None
        cursor: Any
        for path in TENANT_WORKFLOW_TIMEOUT_SETTINGS_PATHS:
            cursor = tenant_settings
            for key in path:
                if not isinstance(cursor, dict) or key not in cursor:
                    cursor = None
                    break
                cursor = cursor[key]
            if isinstance(cursor, int):
                return cursor
        return None

    async def _resolve_workflow_timeout_seconds(self, tenant_id: str | None) -> tuple[int, str]:
        from ..config.settings import get_settings

        source = "service_default"
        selected = get_settings().workflow_timeout_seconds

        if tenant_id:
            try:
                from value_fabric.shared.identity.context import RequestContext

                from ..database import db_session_for_context
                from ..tenants.service import get_tenant_settings

                tenant_uuid = UUID(str(tenant_id))
                async with db_session_for_context(RequestContext(tenant_id=tenant_uuid)) as db:
                    tenant_settings = await get_tenant_settings(db, tenant_uuid)
                tenant_timeout = self._extract_tenant_timeout(tenant_settings)
                if tenant_timeout is not None:
                    selected = tenant_timeout
                    source = "tenant_settings"
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug(
                    "Tenant timeout override resolution failed for tenant_id=%s",
                    tenant_id,
                    exc_info=True,
                )

        min_timeout = get_settings().workflow_timeout_min_seconds
        max_timeout = get_settings().workflow_timeout_max_seconds
        if not isinstance(selected, int) or selected < min_timeout or selected > max_timeout:
            source = "safe_fallback"
            selected = get_settings().workflow_timeout_fallback_seconds

        if selected < min_timeout:
            selected = min_timeout
        if selected > max_timeout:
            selected = max_timeout
        return selected, source

    async def _wait_for_workflow(self, workflow_id: str) -> AgentState:
        """Wait for workflow completion (legacy, no timeout).

        Args:
            workflow_id: Workflow to wait for

        Returns:
            Final workflow state
        """
        # Poll until complete
        while True:
            state = await self.state_manager.load_state(workflow_id)

            if state and state.status in [
                WorkflowStatus.COMPLETED,
                WorkflowStatus.FAILED,
                WorkflowStatus.CANCELLED,
                WorkflowStatus.INTERRUPTED,
            ]:
                return state

            await asyncio.sleep(0.5)

    def _calculate_progress(self, state: AgentState) -> int:
        """Calculate workflow progress percentage.

        Args:
            state: Current workflow state

        Returns:
            Progress percentage (0-100)
        """
        # Simple heuristic based on status
        status_progress = {
            WorkflowStatus.PENDING: 0,
            WorkflowStatus.RUNNING: 50,
            WorkflowStatus.PAUSED: 50,
            WorkflowStatus.INTERRUPTED: 25,
            WorkflowStatus.COMPLETED: 100,
            WorkflowStatus.FAILED: 100,
            WorkflowStatus.CANCELLED: 100,
        }

        return status_progress.get(state.status, 0)

    async def _on_task_complete(self, task: ScheduledTask) -> None:
        """Callback for task completion.

        Args:
            task: Completed task
        """
        logger.info(f"Task {task.task_id} completed")

    async def _on_task_fail(self, task: ScheduledTask, exception: Exception) -> None:
        """Callback for task failure.

        Args:
            task: Failed task
            exception: Exception that caused failure
        """
        logger.error(f"Task {task.task_id} failed: {exception}")

        # Hardening: emit repeated failure metric
        try:
            from ..metrics.prometheus_metrics import get_metrics

            metrics = get_metrics()
            if metrics:
                workflow_type = (
                    task.parameters.get("workflow_type", "unknown")
                    if hasattr(task, "parameters")
                    else "unknown"
                )
                tenant_id = task.tenant_id if hasattr(task, "tenant_id") else "unknown"
                failure_class = type(exception).__name__
                metrics.increment_repeated_failure(
                    workflow_type=workflow_type,
                    failure_class=failure_class,
                    tenant_id=tenant_id or "unknown",
                )
        except asyncio.CancelledError:
            raise
        except Exception:
            pass

    async def detect_and_record_stuck_workflows(self, threshold_seconds: int = 600) -> None:
        """Detect workflows stuck longer than threshold and emit metric.

        Args:
            threshold_seconds: Time in seconds after which a workflow is considered stuck.
        """
        try:
            from ..metrics.prometheus_metrics import get_metrics

            metrics = get_metrics()
            if not metrics:
                return
        except asyncio.CancelledError:
            raise
        except Exception:
            return

        stuck_counts: dict[tuple[str, str], int] = {}
        for workflow_id, meta in self._workflow_metadata.items():
            state = await self.state_manager.load_state(workflow_id)
            if not state:
                continue
            if state.status not in {
                WorkflowStatus.RUNNING,
                WorkflowStatus.PAUSED,
                WorkflowStatus.INTERRUPTED,
            }:
                continue
            started_at = state.started_at or state.metadata.get("started_at")
            if not started_at:
                continue
            if isinstance(started_at, str):
                from datetime import datetime as _dt

                started_at = _dt.fromisoformat(started_at.replace("Z", "+00:00"))
            elapsed = (datetime.now(UTC) - started_at).total_seconds()
            if elapsed > threshold_seconds:
                wf_type = meta.get("workflow_type", "unknown")
                tenant_id = meta.get("tenant_id", "unknown")
                key = (wf_type, tenant_id)
                stuck_counts[key] = stuck_counts.get(key, 0) + 1

        for (wf_type, tenant_id), count in stuck_counts.items():
            metrics.set_stuck_workflows(
                count=count,
                workflow_type=wf_type,
                tenant_id=tenant_id,
            )


# Backward compatibility alias for route dependency typing.
WorkflowExecutor = OrchestrationController
