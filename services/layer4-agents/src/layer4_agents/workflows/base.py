from __future__ import annotations

"""Base workflow class and LangGraph integration.

Provides the foundation for all workflow implementations with checkpointing,
state management, and node execution.
"""
import asyncio
import logging
from abc import ABC, abstractmethod
from collections.abc import Callable
from datetime import UTC, datetime
from typing import Any

from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.errors import GraphInterrupt, NodeInterrupt
from langgraph.graph import StateGraph
from langgraph.types import Command
from value_fabric.shared.governance.tool_gateway import ToolGateway
from value_fabric.shared.models.typed_dict import TypedDictModel

from ..models.agent_state import AgentState, BaseAgentState, WorkflowStatus
from ..models.reasoning_trace import ReasoningTrace, ToolCallTrace, validate_reasoning_trace
from ..models.workflow_config import EdgeConfig, NodeConfig, NodeType, WorkflowConfig
from ..tools.registry import ToolRegistry, ToolResult


class BaseWorkflow__execute_llmResult(TypedDictModel):
    status: str

class BaseWorkflow__execute_agentResult(TypedDictModel):
    status: str

# Default recursion limit for LangGraph workflows
# Prevents infinite loops in malformed workflows
DEFAULT_RECURSION_LIMIT = 100

logger = logging.getLogger(__name__)


class WorkflowError(Exception):
    """Raised when workflow execution fails."""

    pass


class NodeExecutionError(WorkflowError):
    """Raised when a node execution fails."""

    pass


class _WorkflowToolRegistryProxy:
    """Proxy all tool calls through the enforced gateway when available."""

    def __init__(self, registry: ToolRegistry, tool_gateway: ToolGateway | None = None):
        self._registry = registry
        self._tool_gateway = tool_gateway

    def __getattr__(self, name: str) -> object:
        return getattr(self._registry, name)

    async def execute(
        self, tool_name: str, input_data: dict[str, object]
    ) -> ToolResult | dict[str, object]:
        if self._tool_gateway is None:
            logger.warning(
                "No policy-enforced tool gateway configured for %s; falling back to the raw registry to preserve legacy workflow execution paths.",
                tool_name,
            )
            return await self._registry.execute(tool_name, input_data)
        return await self._tool_gateway.execute(tool_name, input_data)


class BaseWorkflow(ABC):
    """Base class for all LangGraph workflows.

    Provides common functionality for:
    - Graph construction from WorkflowConfig
    - State management and checkpointing
    - Node execution with error handling
    - Tool integration

    Example:
        class MyWorkflow(BaseWorkflow):
            def __init__(self, config: WorkflowConfig, tool_registry: ToolRegistry):
                super().__init__(config, tool_registry)

            def _build_graph(self) -> StateGraph:
                # Build and return LangGraph
                pass
    """

    def __init__(
        self,
        config: WorkflowConfig,
        tool_registry: ToolRegistry,
        checkpoint_saver: BaseCheckpointSaver | None = None,
        tool_gateway: ToolGateway | None = None,
    ):
        """Initialize workflow.

        Args:
            config: Workflow configuration
            tool_registry: Registry of available tools
            checkpoint_saver: Optional checkpoint saver for persistence
            tool_gateway: Optional policy-enforced gateway for tool execution
        """
        self.config = config
        self.tool_gateway = tool_gateway
        self.tool_registry = _WorkflowToolRegistryProxy(tool_registry, tool_gateway)
        self.checkpoint_saver = checkpoint_saver
        self._graph: StateGraph | None = None
        self._compiled_graph = None

    @property
    def name(self) -> str:
        """Get workflow name."""
        return self.config.name

    @property
    def workflow_type(self) -> str:
        """Get workflow type identifier."""
        return self.config.workflow_type

    def _build_graph(self) -> StateGraph:
        """Build the LangGraph from configuration.

        This base implementation constructs a basic graph from
        the WorkflowConfig. Subclasses can override for custom logic.

        Returns:
            Configured StateGraph
        """
        # Create state graph with our state type
        graph = StateGraph(self._get_state_type())

        # Add nodes
        for node_config in self.config.nodes:
            node_func = self._create_node_function(node_config)
            graph.add_node(node_config.id, node_func)

        # Add edges
        for edge_config in self.config.edges:
            if edge_config.edge_type.value == "conditional":
                # Conditional edge requires a router function
                graph.add_conditional_edges(
                    edge_config.source,
                    self._create_router(edge_config),
                    {"continue": edge_config.target, "retry": self.config.entry_point},
                )
            else:
                graph.add_edge(edge_config.source, edge_config.target)

        # Set entry point
        graph.set_entry_point(self.config.entry_point)

        return graph

    def _get_state_type(self) -> type:
        """Get the Pydantic state type for this workflow.

        Returns:
            Pydantic BaseModel class
        """
        return BaseAgentState

    def _create_node_function(self, node_config: NodeConfig) -> Callable:
        """Create a node execution function.

        Args:
            node_config: Node configuration

        Returns:
            Node function for LangGraph
        """

        async def node_function(state: AgentState) -> dict[str, Any]:
            """Execute node logic."""
            # Update state
            updates = {"current_node": node_config.id, "status": WorkflowStatus.RUNNING}

            try:
                if node_config.node_type == NodeType.TOOL and node_config.tool_name:
                    # Execute tool
                    result = await self._execute_tool(
                        node_config.tool_name, state, node_config.config
                    )
                    updates["output_data"] = {**state.output_data, node_config.id: result}
                    # Append to node trace log for reasoning trace construction
                    trace_log = list(state.metadata.get("node_trace_log", []))
                    trace_log.append({
                        "node_id": node_config.id,
                        "node_type": "tool",
                        "tool_name": node_config.tool_name,
                        "timestamp": self._now().isoformat(),
                    })
                    updates["metadata"] = {**state.metadata, "node_trace_log": trace_log}

                elif node_config.node_type == NodeType.LLM:
                    # LLM node - handled by subclass or agent node
                    result = await self._execute_llm(node_config, state)
                    updates["output_data"] = {**state.output_data, node_config.id: result}
                    trace_log = list(state.metadata.get("node_trace_log", []))
                    trace_log.append({
                        "node_id": node_config.id,
                        "node_type": "llm",
                        "timestamp": self._now().isoformat(),
                    })
                    updates["metadata"] = {**state.metadata, "node_trace_log": trace_log}

                elif node_config.node_type == NodeType.AGENT:
                    # Agent node - delegates to sub-workflow
                    result = await self._execute_agent(node_config, state)
                    updates["output_data"] = {**state.output_data, node_config.id: result}
                    trace_log = list(state.metadata.get("node_trace_log", []))
                    trace_log.append({
                        "node_id": node_config.id,
                        "node_type": "agent",
                        "timestamp": self._now().isoformat(),
                    })
                    updates["metadata"] = {**state.metadata, "node_trace_log": trace_log}

                elif node_config.node_type == NodeType.END:
                    # End node: construct and validate reasoning trace
                    updates["status"] = WorkflowStatus.COMPLETED
                    updates["completed_at"] = self._now()

                    trace_log = state.metadata.get("node_trace_log", [])
                    tools_called = [
                        ToolCallTrace(
                            tool_name=entry.get("tool_name", "unknown"),
                            invocation_id=f"{state.run_id or state.workflow_id}:{entry.get('node_id', 'unknown')}",
                            timestamp=entry.get("timestamp", self._now().isoformat()),
                        )
                        for entry in trace_log
                        if entry.get("node_type") == "tool"
                    ]

                    # Gather assumptions from metadata if present
                    assumptions = state.metadata.get("assumptions", [])
                    if not assumptions:
                        assumptions = ["No explicit assumptions recorded"]

                    # Gather evidence from metadata if present
                    evidence = state.metadata.get("evidence_considered", [])
                    if not evidence:
                        evidence = ["No explicit evidence recorded"]

                    # Gather output object IDs from output_data
                    output_object_ids: list[str] = []
                    for key, val in (state.output_data or {}).items():
                        if isinstance(val, dict) and "id" in val:
                            output_object_ids.append(str(val["id"]))
                        elif isinstance(val, list):
                            for item in val:
                                if isinstance(item, dict) and "id" in item:
                                    output_object_ids.append(str(item["id"]))
                    if not output_object_ids:
                        output_object_ids = [f"output:{state.workflow_id}"]

                    reasoning_trace = ReasoningTrace(
                        inputs_used=list(state.input_data.keys()),
                        tools_called=tools_called,
                        evidence_considered=evidence,
                        assumptions=assumptions,
                        confidence=state.metadata.get("confidence", 0.8),
                        output_object_ids=output_object_ids,
                        run_id=state.run_id or state.workflow_id,
                        trace_id=state.trace_id or state.workflow_id,
                    )

                    try:
                        validate_reasoning_trace(reasoning_trace, strict=False)
                        updates["reasoning_trace"] = reasoning_trace
                        updates["output_data"] = {
                            **state.output_data,
                            "reasoning_trace": reasoning_trace.model_dump(mode="json"),
                        }
                    except ValueError as ve:
                        updates["errors"] = state.errors + [f"REASONING_TRACE_INVALID: {ve}"]
                        updates["status"] = WorkflowStatus.FAILED

                return updates

            except (GraphInterrupt, NodeInterrupt):
                # Native LangGraph HITL interrupts must bubble up so the
                # checkpointer can persist state and the caller can handle it.
                raise
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                # Handle error
                error_msg = f"Node {node_config.id} failed (NODE_EXECUTION_ERROR): {exc}"
                updates["errors"] = state.errors + [error_msg]
                updates["status"] = WorkflowStatus.FAILED
                logger.exception(
                    "Node execution failed",
                    extra={
                        "node_id": node_config.id,
                        "workflow_id": getattr(state, "workflow_id", None),
                        "tenant_id": getattr(state, "tenant_id", None),
                        "run_id": getattr(state, "run_id", None),
                    },
                )

                # Check retry policy
                if self._should_retry(node_config, state):
                    # Return to same node for retry
                    return updates

                raise NodeExecutionError(error_msg) from exc

        return node_function

    async def _execute_tool(
        self, tool_name: str, state: AgentState, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Execute a tool from the registry.

        Args:
            tool_name: Name of tool to execute
            state: Current workflow state
            config: Tool configuration

        Returns:
            Tool execution result
        """
        tool_input = self._build_tool_input(tool_name, state, config)

        # Route through the policy-enforced proxy. When a ToolGateway is
        # injected it enforces policy before invoking the registry; otherwise
        # the proxy degrades to the raw registry to preserve legacy execution
        # paths (unit tests and config-driven workflows without an agent ABOM).
        return await self.tool_registry.execute(tool_name, tool_input)

    def _build_tool_input(
        self, tool_name: str, state: AgentState, config: dict[str, Any]
    ) -> dict[str, Any]:
        """Build tool input from state and config.

        Subclasses can override to customize input building.

        Args:
            tool_name: Tool being executed
            state: Current state
            config: Node config

        Returns:
            Tool input dictionary
        """
        # Default: merge input data with config
        tool_input = {**state.input_data, **config}

        # Add workflow-specific data
        if hasattr(state, "prospect_id"):
            tool_input["prospect_id"] = state.prospect_id

        # Propagate authenticated tenant context and correlation IDs so the
        # tool registry can authorize and attribute every tool call.
        tenant_id = getattr(state, "tenant_id", None)
        if tenant_id:
            tool_input.setdefault("tenant_id", tenant_id)
        trace_id = getattr(state, "trace_id", None)
        if trace_id:
            tool_input.setdefault("trace_id", trace_id)
        workflow_id = getattr(state, "workflow_id", None)
        if workflow_id:
            tool_input.setdefault("workflow_id", workflow_id)
        run_id = getattr(state, "run_id", None)
        if run_id:
            tool_input.setdefault("run_id", run_id)

        return tool_input

    async def _execute_llm(self, node_config: NodeConfig, state: AgentState) -> dict[str, Any]:
        """Execute LLM node.

        Subclasses should override for LLM-specific logic.
        """
        return BaseWorkflow__execute_llmResult.model_validate({"status": "llm_not_implemented"})

    async def _execute_agent(self, node_config: NodeConfig, state: AgentState) -> dict[str, Any]:
        """Execute agent node (sub-workflow).

        Subclasses should override for agent-specific logic.
        """
        return BaseWorkflow__execute_agentResult.model_validate({"status": "agent_not_implemented"})

    def _create_router(self, edge_config: EdgeConfig) -> Callable:
        """Create a router function for conditional edges."""

        def router(state: AgentState) -> str:
            """Route based on state.

            Returns string keys to avoid serialization issues with booleans
            in LangGraph conditional edges.
            """
            if edge_config.condition == "results_valid":
                return "continue" if len(state.errors) == 0 else "retry"
            elif edge_config.condition == "retry_needed":
                return "retry" if len(state.errors) > 0 else "continue"
            return "continue"

        return router

    def _should_retry(self, node_config: NodeConfig, state: AgentState) -> bool:
        """Check if node should be retried."""
        max_retries = node_config.retry_policy.get("max_retries", 0)
        # Count retries by checking errors containing node name
        retry_count = sum(1 for e in state.errors if node_config.id in e)
        return retry_count < max_retries

    def _now(self):
        """Get current timestamp."""
        return datetime.now(UTC)

    def compile(self) -> Any:
        """Compile the workflow graph.

        Returns:
            Compiled LangGraph runnable
        """
        if self._compiled_graph is None:
            if self._graph is None:
                self._graph = self._build_graph()

            compile_kwargs = {}
            if self.checkpoint_saver:
                compile_kwargs["checkpointer"] = self.checkpoint_saver
            if self.config.interrupt_before:
                compile_kwargs["interrupt_before"] = self.config.interrupt_before
            if self.config.interrupt_after:
                compile_kwargs["interrupt_after"] = self.config.interrupt_after

            self._compiled_graph = self._graph.compile(**compile_kwargs)

        return self._compiled_graph

    async def run(
        self,
        initial_state: AgentState,
        thread_id: str | None = None,
        recursion_limit: int | None = None,
        resume_data: Any = None,
        checkpoint_config: dict[str, Any] | None = None,
        **kwargs,
    ) -> AgentState:
        """Execute the workflow.

        Args:
            initial_state: Starting workflow state
            thread_id: Optional thread ID for checkpointing
            recursion_limit: Maximum recursion steps (default: DEFAULT_RECURSION_LIMIT)
            resume_data: Optional resume value for native LangGraph HITL resume
            checkpoint_config: Optional LangGraph checkpoint configurable fields
                such as ``checkpoint_id`` or ``checkpoint_ns``. Values are
                merged with ``thread_id`` and passed through to LangGraph.
            **kwargs: Additional run parameters

        Returns:
            Final workflow state

        Raises:
            ValueError: If recursion_limit is not a positive integer
        """
        # Validate recursion_limit
        if recursion_limit is not None:
            if not isinstance(recursion_limit, int) or recursion_limit <= 0:
                raise ValueError(
                    f"recursion_limit must be a positive integer, got {recursion_limit}"
                )
        else:
            recursion_limit = DEFAULT_RECURSION_LIMIT

        compiled = self.compile()

        config = {"configurable": {}, "recursion_limit": recursion_limit}
        if checkpoint_config:
            config["configurable"].update(checkpoint_config)
        if thread_id:
            config["configurable"]["thread_id"] = thread_id

        workflow_id = getattr(initial_state, "workflow_id", "unknown")
        run_id = getattr(initial_state, "run_id", workflow_id)
        trace_id = getattr(initial_state, "trace_id", workflow_id)
        tenant_id = getattr(initial_state, "tenant_id", "unknown")
        approval_decision = initial_state.metadata.get("approval_decision")

        # Build input: Command for resume, state dict for fresh run
        if resume_data is not None:
            input_val: Any = Command(resume=resume_data)
            logger.info(
                "Resuming workflow execution",
                extra={
                    "workflow_id": workflow_id,
                    "run_id": run_id,
                    "trace_id": trace_id,
                    "tenant_id": tenant_id,
                    "thread_id": thread_id,
                    "checkpoint_id": config["configurable"].get("checkpoint_id"),
                },
            )
        else:
            input_val = initial_state.model_dump()
            logger.info(
                "Starting workflow execution",
                extra={
                    "workflow_id": workflow_id,
                    "run_id": run_id,
                    "trace_id": trace_id,
                    "tenant_id": tenant_id,
                    "workflow_type": getattr(initial_state, "workflow_type", "unknown"),
                    "thread_id": thread_id,
                    "checkpoint_id": config["configurable"].get("checkpoint_id"),
                    "recursion_limit": recursion_limit,
                },
            )
            if approval_decision is not None:
                initial_state.metadata["approval_decision"] = approval_decision

        try:
            result = await compiled.ainvoke(input_val, config=config, **kwargs)

            # Detect native LangGraph interrupt (e.g. from interrupt() or interrupt_before/after)
            if isinstance(result, dict) and "__interrupt__" in result:
                logger.info("Workflow interrupted: %s", workflow_id)
                interrupted_state = self._state_from_dict(result)
                interrupted_state.status = WorkflowStatus.INTERRUPTED
                return interrupted_state

            logger.info("Workflow execution completed: %s", workflow_id)
            final_state = self._state_from_dict(result)
            # Ensure run_envelope is preserved if it was set on initial_state
            if initial_state.run_envelope is not None and final_state.run_envelope is None:
                final_state.run_envelope = initial_state.run_envelope
            if approval_decision is not None:
                final_state.metadata["approval_decision"] = approval_decision
            return final_state
        except NodeInterrupt:
            logger.info("Workflow interrupted by NodeInterrupt: %s", workflow_id)
            # Checkpoint already persisted by LangGraph; return structured INTERRUPTED state
            interrupted_state = initial_state.model_copy()
            interrupted_state.status = WorkflowStatus.INTERRUPTED
            return interrupted_state
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.error("Workflow execution failed: %s: %s", workflow_id, e, exc_info=True)
            raise

    def _state_from_dict(self, data: dict[str, Any]) -> AgentState:
        """Convert dict result back to state object."""
        state_type = self._get_state_type()
        return state_type(**data)

    def _make_harness_run(
        self,
        workflow_type_str: str,
        tenant_id: str,
        trace_id: str | None = None,
    ) -> Any:
        """Create an in-memory HarnessRun for GovernedLLMClient attribution.

        Returns a HarnessRun so that every LLM trace event carries run_id,
        workflow_type, and tenant_id.  Falls back to None (with a warning) if
        the harness models are unavailable, so callers degrade gracefully.

        Args:
            workflow_type_str: Canonical workflow type string (e.g. "business_case_generation").
            tenant_id: Authenticated tenant identifier.
            trace_id: Optional existing trace ID; a new one is generated if absent.
        """
        from ..harness.models import HarnessRun, HarnessWorkflowType, InitiatedBy

        try:
            kwargs: dict[str, Any] = {
                "tenant_id": tenant_id,
                "workflow_type": HarnessWorkflowType(workflow_type_str),
                "initiated_by": InitiatedBy.SYSTEM,
            }
            if trace_id:
                kwargs["trace_id"] = trace_id
            return HarnessRun(**kwargs)
        except ImportError as exc:
            # Harness models unavailable in this environment — degrade gracefully.
            logger.warning("Could not create HarnessRun for LLM attribution: %s", exc)
            return None
        # ValueError (unknown workflow_type_str) and all other exceptions propagate
        # so misconfigured callers are caught at development time rather than
        # silently producing ungoverned LLM calls with run=None.

    @abstractmethod
    def create_initial_state(
        self,
        input_data: dict[str, Any],
        *,
        tenant_id: str,
        run_id: str | None = None,
        trace_id: str | None = None,
        workflow_id: str | None = None,
    ) -> AgentState:
        """Create initial state from input data.

        Args:
            input_data: Workflow input parameters
            tenant_id: Required owning tenant identifier
            run_id: Optional distinct run identifier (generated if absent)
            trace_id: Optional cross-layer trace identifier (generated if absent)
            workflow_id: Optional stable workflow instance identifier (generated if absent)

        Returns:
            Initial workflow state

        Raises:
            TenantMissingError: If tenant_id is missing or empty
        """
        pass


class WorkflowBuilder:
    """Builder for constructing workflows programmatically.

    Example:
        builder = WorkflowBuilder("my_workflow", "My Workflow")
        builder.add_node(NodeConfig(id="step1", ...))
        builder.add_edge("step1", "step2")

        config = builder.build()
        workflow = BaseWorkflow(config, tool_registry)
    """

    def __init__(self, workflow_type: str, name: str, description: str = ""):
        """Initialize builder."""
        self.workflow_type = workflow_type
        self.name = name
        self.description = description
        self.nodes: list[NodeConfig] = []
        self.edges: list[EdgeConfig] = []
        self.entry_point: str | None = None
        self.global_config: dict[str, Any] = {}

    def add_node(self, node: NodeConfig) -> WorkflowBuilder:
        """Add a node to the workflow."""
        self.nodes.append(node)
        return self

    def add_edge(self, source: str, target: str, **kwargs) -> WorkflowBuilder:
        """Add an edge between nodes."""
        self.edges.append(EdgeConfig(source=source, target=target, **kwargs))
        return self

    def set_entry_point(self, node_id: str) -> WorkflowBuilder:
        """Set the workflow entry point."""
        self.entry_point = node_id
        return self

    def set_global_config(self, config: dict[str, Any]) -> WorkflowBuilder:
        """Set global workflow configuration."""
        self.global_config = config
        return self

    def build(self) -> WorkflowConfig:
        """Build the workflow configuration."""
        if not self.entry_point:
            raise WorkflowError("Entry point must be set")

        return WorkflowConfig(
            workflow_type=self.workflow_type,
            name=self.name,
            description=self.description,
            nodes=self.nodes,
            edges=self.edges,
            entry_point=self.entry_point,
            global_config=self.global_config,
        )
