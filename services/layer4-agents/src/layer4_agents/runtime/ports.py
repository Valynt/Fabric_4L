"""Agent Runtime ports (Protocols) defining stable boundaries."""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from typing import Any, Protocol, runtime_checkable

from .models import (
    AuthzDecision,
    Checkpoint,
    Message,
    ModelConfig,
    ModelResponse,
    ResumeRequest,
    RunEnvelope,
    RunRequest,
    RunResult,
    RunSummary,
    RuntimeContext,
    ToolDef,
    ToolResult,
    ToolSchema,
    WorkflowResult,
)


@runtime_checkable
class ToolRegistryPort(Protocol):
    """Contract for registering, discovering, and executing tools."""

    def register(self, tool: ToolDef) -> None:
        """Register a tool definition."""

    def get_schema(self, name: str, tenant_id: str) -> ToolSchema | None:
        """Return the public schema for a tenant-visible tool."""

    def list_tools(self, tenant_id: str) -> list[ToolSchema]:
        """Return all tools visible to the tenant."""

    async def execute(self, name: str, arguments: dict[str, Any], ctx: RuntimeContext) -> ToolResult:
        """Execute a tool, returning a canonical result."""


@runtime_checkable
class AuthzPort(Protocol):
    """Contract for authorizing runtime actions."""

    async def authorize_tool(self, tool_name: str, ctx: RuntimeContext) -> AuthzDecision:
        """Authorize a tool call in the current runtime context."""


@runtime_checkable
class ModelProviderPort(Protocol):
    """Contract for provider-specific LLM calls."""

    @property
    def provider_name(self) -> str:
        """Canonical provider name."""

    async def complete(self, messages: list[Message], config: ModelConfig, ctx: RuntimeContext) -> ModelResponse:
        """Generate a chat completion."""

    async def embed(self, texts: list[str], config: ModelConfig, ctx: RuntimeContext) -> list[list[float]]:
        """Return embeddings for the given texts."""


@runtime_checkable
class MemoryPort(Protocol):
    """Contract for thread memory and long-term retrieval."""

    async def get_thread_state(self, thread_id: str, tenant_id: str) -> dict[str, Any] | None:
        """Load the latest thread state for a tenant."""

    async def save_thread_state(self, thread_id: str, tenant_id: str, state: dict[str, Any]) -> None:
        """Persist thread state for a tenant."""

    async def search_long_term(self, query: str, tenant_id: str, *, limit: int = 10) -> list[dict[str, Any]]:
        """Search long-term memory for a tenant."""


@runtime_checkable
class CheckpointPort(Protocol):
    """Contract for durable checkpoint storage."""

    async def save(self, checkpoint: Checkpoint, state: dict[str, Any]) -> None:
        """Persist a checkpoint and its associated state."""

    async def load(self, run_id: str, thread_id: str, tenant_id: str, *, checkpoint_id: str | None = None) -> tuple[Checkpoint, dict[str, Any]] | None:
        """Load the latest or named checkpoint for a run/thread."""

    async def list(self, run_id: str, tenant_id: str) -> list[Checkpoint]:
        """List checkpoints for a run."""


@runtime_checkable
class WorkflowEnginePort(Protocol):
    """Contract for workflow execution adapters (LangGraph, custom, etc.)."""

    async def execute(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        ctx: RuntimeContext,
        checkpoint: Checkpoint | None = None,
    ) -> WorkflowResult:
        """Execute a workflow from input."""

    async def resume(
        self,
        workflow_type: str,
        run_id: str,
        resume_request: ResumeRequest,
        ctx: RuntimeContext,
    ) -> WorkflowResult:
        """Resume a paused/interrupted workflow."""

    def get_supported_types(self) -> set[str]:
        """Return the set of workflow types this engine supports."""


WorkflowFactory = Callable[[str, dict[str, Any], RuntimeContext], Awaitable[WorkflowResult]]


@runtime_checkable
class AgentRuntime(Protocol):
    """Primary Agent Runtime contract."""

    async def start(self) -> None:
        """Start background runtime processes."""

    async def stop(self) -> None:
        """Stop background runtime processes."""

    async def submit_run(self, request: RunRequest, ctx: RuntimeContext) -> RunEnvelope:
        """Submit a new workflow run."""

    async def get_run(self, run_id: str, tenant_id: str) -> RunResult | None:
        """Get a run by ID; returns None if not found or inaccessible."""

    async def cancel_run(self, run_id: str, tenant_id: str) -> RunResult:
        """Cancel a running/pending run."""

    async def list_runs(
        self,
        tenant_id: str,
        *,
        workflow_type: str | None = None,
        status: str | None = None,
    ) -> list[RunSummary]:
        """List runs scoped to a tenant."""

    async def resume_run(self, run_id: str, tenant_id: str, resume: ResumeRequest) -> RunResult:
        """Resume a paused run."""

    def register_tool(self, tool: ToolDef) -> None:
        """Register a tool globally."""

    def register_workflow_type(self, workflow_type: str, factory: WorkflowFactory) -> None:
        """Register a workflow type factory."""

    def register_model_provider(self, name: str, provider: ModelProviderPort) -> None:
        """Register a model provider adapter."""
