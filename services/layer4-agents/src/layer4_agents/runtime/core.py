"""Thin Agent Runtime orchestration spine."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .context import with_context
from .errors import ProviderNotFoundError, ToolForbiddenError, WorkflowTypeNotFoundError
from .models import (
    RunEnvelope,
    RunRequest,
    RunResult,
    RunStatus,
    RunSummary,
    RuntimeContext,
    ToolDef,
    ToolResult,
)
from .ports import (
    AuthzPort,
    CheckpointPort,
    MemoryPort,
    ModelProviderPort,
    ToolRegistryPort,
    WorkflowEnginePort,
    WorkflowFactory,
)


class AgentRuntimeImpl:
    """Provider-agnostic agent runtime implementation.

    This is the execution spine: it validates runtime context, delegates to
    registered ports, and persists run metadata. It intentionally contains no
    provider-specific logic.
    """

    def __init__(
        self,
        *,
        workflow_engine: WorkflowEnginePort | None = None,
        tool_registry: ToolRegistryPort | None = None,
        authz: AuthzPort | None = None,
        memory: MemoryPort | None = None,
        checkpoint: CheckpointPort | None = None,
    ):
        self._workflow_engine = workflow_engine
        self._tool_registry = tool_registry
        self._authz = authz
        self._memory = memory
        self._checkpoint = checkpoint
        self._model_providers: dict[str, ModelProviderPort] = {}
        self._workflow_factories: dict[str, WorkflowFactory] = {}
        self._tools: dict[str, ToolDef] = {}
        self._runs: dict[str, RunResult] = {}

    async def start(self) -> None:
        """No-op for the skeleton; adapters may implement startup here."""

    async def stop(self) -> None:
        """No-op for the skeleton; adapters may implement shutdown here."""

    def register_tool(self, tool: ToolDef) -> None:
        """Register a tool globally in the runtime."""
        self._tools[tool.name] = tool
        if self._tool_registry is not None:
            self._tool_registry.register(tool)

    def register_workflow_type(self, workflow_type: str, factory: WorkflowFactory) -> None:
        """Register a factory for a workflow type."""
        self._workflow_factories[workflow_type] = factory

    def register_model_provider(self, name: str, provider: ModelProviderPort) -> None:
        """Register a model provider adapter."""
        self._model_providers[name] = provider

    async def submit_run(self, request: RunRequest, ctx: RuntimeContext) -> RunEnvelope:
        """Submit a new run after validating tenant context."""
        if not ctx.tenant_id:
            from .errors import TenantRequiredError

            raise TenantRequiredError()

        run_id = str(uuid4())
        workflow_id = request.workflow_id or run_id
        envelope = RunEnvelope(
            run_id=run_id,
            workflow_id=workflow_id,
            trace_id=ctx.trace_id,
            tenant_id=ctx.tenant_id,
            workflow_type=request.workflow_type,
            status=RunStatus.PENDING,
        )
        self._runs[run_id] = RunResult(
            run_id=run_id,
            workflow_id=workflow_id,
            trace_id=ctx.trace_id,
            tenant_id=ctx.tenant_id,
            workflow_type=request.workflow_type,
            status=RunStatus.PENDING,
            created_at=envelope.created_at,
        )

        with with_context(ctx):
            await self._dispatch_run(envelope, request, ctx)

        return envelope

    async def _dispatch_run(
        self,
        envelope: RunEnvelope,
        request: RunRequest,
        ctx: RuntimeContext,
    ) -> None:
        """Internal dispatch: choose engine or factory, execute, persist result."""
        if self._workflow_engine is not None:
            result = await self._workflow_engine.execute(
                request.workflow_type,
                request.input_data,
                ctx,
                checkpoint=None,
            )
        elif request.workflow_type in self._workflow_factories:
            factory = self._workflow_factories[request.workflow_type]
            result = await factory(request.workflow_type, request.input_data, ctx)
        else:
            raise WorkflowTypeNotFoundError(request.workflow_type)

        existing = self._runs.get(envelope.run_id)
        if existing is not None:
            self._runs[envelope.run_id] = RunResult(
                run_id=envelope.run_id,
                workflow_id=envelope.workflow_id,
                trace_id=ctx.trace_id,
                tenant_id=ctx.tenant_id,
                workflow_type=request.workflow_type,
                status=result.status,
                output=result.output,
                error=result.error,
                created_at=existing.created_at,
                started_at=existing.started_at,
                completed_at=datetime.now(UTC).isoformat(),
            )

    async def get_run(self, run_id: str, tenant_id: str) -> RunResult | None:
        """Tenant-scoped run lookup; returns None for missing or inaccessible runs."""
        result = self._runs.get(run_id)
        if result is None or result.tenant_id != tenant_id:
            return None
        return result

    async def cancel_run(self, run_id: str, tenant_id: str) -> RunResult:
        """Cancel a run if it belongs to the tenant."""
        result = await self.get_run(run_id, tenant_id)
        if result is None:
            from .errors import RunNotFoundError

            raise RunNotFoundError(run_id)
        self._runs[run_id] = result.model_copy(update={"status": RunStatus.CANCELLED})
        return self._runs[run_id]

    async def list_runs(
        self,
        tenant_id: str,
        *,
        workflow_type: str | None = None,
        status: str | None = None,
    ) -> list[RunSummary]:
        """List runs scoped to tenant with optional filters."""
        summaries: list[RunSummary] = []
        for run in self._runs.values():
            if run.tenant_id != tenant_id:
                continue
            if workflow_type and run.workflow_type != workflow_type:
                continue
            if status and run.status.value != status:
                continue
            summaries.append(
                RunSummary(
                    run_id=run.run_id,
                    workflow_id=run.workflow_id,
                    workflow_type=run.workflow_type,
                    status=run.status,
                    created_at=run.created_at,
                )
            )
        return summaries

    async def resume_run(self, run_id: str, tenant_id: str, resume: Any) -> RunResult:
        """Resume a paused run; stubbed for Phase 0."""
        raise NotImplementedError("resume_run is stubbed for Phase 0")

    async def authorize_tool(self, tool_name: str, ctx: RuntimeContext) -> bool:
        """Helper to authorize a tool call through the configured AuthzPort."""
        if self._authz is None:
            return True
        decision = await self._authz.authorize_tool(tool_name, ctx)
        if not decision.allowed:
            raise ToolForbiddenError(tool_name, reason=decision.reason or None)
        return True

    async def call_tool(self, name: str, arguments: dict[str, Any], ctx: RuntimeContext) -> ToolResult:
        """Execute a tool through the registry, enforcing authz and tenant context."""
        await self.authorize_tool(name, ctx)
        if self._tool_registry is None:
            raise ProviderNotFoundError("tool_registry")
        return await self._tool_registry.execute(name, arguments, ctx)
