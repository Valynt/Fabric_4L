"""Thin Agent Runtime orchestration spine."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

from .context import with_context
from .errors import (
    AgentRuntimeError,
    ProviderNotFoundError,
    RunNotFoundError,
    TenantRequiredError,
    ToolForbiddenError,
    ToolRegistryUnavailableError,
    WorkflowTypeNotFoundError,
)
from .events import (
    RUN_CANCELLED,
    RUN_COMPLETED,
    RUN_FAILED,
    RUN_PAUSED,
    RUN_RESUMED,
    RUN_STARTED,
    TOOL_CALLED,
    TOOL_DENIED,
    EventSink,
    RuntimeEvent,
)
from .models import (
    ResumeRequest,
    RunEnvelope,
    RunRequest,
    RunResult,
    RunStatus,
    RunSummary,
    RuntimeContext,
    ToolDef,
    ToolResult,
    ToolSchema,
    WorkflowResult,
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

# Statuses in which a run may still be cancelled. Terminal runs are immutable:
# cancelling a completed/failed/cancelled run would rewrite its history.
_CANCELLABLE_STATUSES = frozenset(
    {RunStatus.PENDING, RunStatus.RUNNING, RunStatus.RETRYING, RunStatus.PAUSED}
)

# Terminal statuses: only these stamp completed_at. A paused (resumable) run
# must keep completed_at null so stale-run detection and timelines treat it
# as in-flight.
_TERMINAL_RUN_STATUSES = frozenset(
    {RunStatus.COMPLETED, RunStatus.FAILED, RunStatus.CANCELLED}
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
        event_bus: EventSink | None = None,
    ):
        self._workflow_engine = workflow_engine
        self._tool_registry = tool_registry
        self._authz = authz
        self._memory = memory
        self._checkpoint = checkpoint
        self._event_bus = event_bus
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

    def list_workflow_types(self) -> list[str]:
        """Return the workflow types exposed by the configured runtime."""
        types = set(self._workflow_factories)
        if self._workflow_engine is not None:
            types.update(self._workflow_engine.get_supported_types())
        return sorted(types)

    def list_model_providers(self) -> list[str]:
        """Return provider names without exposing provider implementation details."""
        return sorted(self._model_providers)

    def list_tools(self, tenant_id: str) -> list[ToolSchema]:
        """Return tenant-visible tool schemas through the configured registry."""
        if not tenant_id:
            raise TenantRequiredError()
        if self._tool_registry is not None:
            return self._tool_registry.list_tools(tenant_id)
        return [
            ToolSchema(
                name=tool.name,
                description=tool.description,
                category=tool.category,
                tenant_scoped=tool.tenant_scoped,
                parameters=dict(tool.parameters),
                required=list(tool.required),
                version=tool.version,
            )
            for tool in self._tools.values()
        ]

    def get_model_provider(self, name: str) -> ModelProviderPort:
        """Resolve a registered model provider, failing closed when absent.

        This is the consumption seam for the execution spine and downstream
        wiring: engine adapters and tools resolve inference providers by name
        rather than constructing them directly, keeping orchestration
        provider-agnostic.
        """
        try:
            return self._model_providers[name]
        except KeyError:
            raise ProviderNotFoundError(name) from None

    async def submit_run(self, request: RunRequest, ctx: RuntimeContext) -> RunEnvelope:
        """Submit a new run after validating tenant context."""
        if not ctx.tenant_id:
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

        await self._emit(
            RuntimeEvent(
                kind=RUN_STARTED,
                run_id=run_id,
                tenant_id=ctx.tenant_id,
                workflow_type=request.workflow_type,
                status=RunStatus.PENDING.value,
                payload={"workflow_id": workflow_id},
            )
        )
        try:
            # The envelope's run/workflow ids are authoritative for execution:
            # the engine must observe the same run identity the runtime records
            # and persists, never a caller-supplied context's.
            dispatch_ctx = ctx.model_copy(update={"run_id": run_id, "workflow_id": workflow_id})
            with with_context(dispatch_ctx):
                if request.timeout_seconds is None:
                    await self._dispatch_run(envelope, request, dispatch_ctx)
                else:
                    # Enforce the run's timeout budget: a dispatch exceeding it
                    # is cancelled and folded into a terminal failed record.
                    await asyncio.wait_for(
                        self._dispatch_run(envelope, request, dispatch_ctx),
                        timeout=request.timeout_seconds,
                    )
        except AgentRuntimeError as exc:
            await self._fail_run(run_id, ctx, request, code=exc.code, message=str(exc))
            raise
        except TimeoutError:
            await self._fail_run(
                run_id,
                ctx,
                request,
                code="RUN_TIMEOUT",
                message=f"Run exceeded its timeout budget of {request.timeout_seconds}s",
            )
            raise

        stored = self._runs.get(run_id)
        if stored is not None:
            await self._emit_status_event(stored)
        return envelope

    async def _fail_run(
        self, run_id: str, ctx: RuntimeContext, request: RunRequest, *, code: str, message: str
    ) -> None:
        """Fold a dispatch failure into a terminal failed record and emit RUN_FAILED.

        A dispatch failure must leave a terminal (failed) record behind, not a
        zombie pending run, and must surface as a failed event.
        """
        failed = self._runs[run_id].model_copy(
            update={
                "status": RunStatus.FAILED,
                "error": {"code": code, "message": message},
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
        self._runs[run_id] = failed
        await self._persist_run_memory(failed)
        await self._emit(
            RuntimeEvent(
                kind=RUN_FAILED,
                run_id=run_id,
                tenant_id=ctx.tenant_id,
                workflow_type=request.workflow_type,
                status=RunStatus.FAILED.value,
                payload={"error_code": code},
            )
        )

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
            updated = self._finalize_run(existing, result)
            self._runs[envelope.run_id] = updated
            await self._persist_run_memory(updated)

    def _finalize_run(self, existing: RunResult, result: WorkflowResult) -> RunResult:
        """Fold a dispatch/resume ``WorkflowResult`` into the stored run record."""
        update: dict[str, object] = {
            "status": result.status,
            "output": result.output,
            "error": result.error,
        }
        if result.status in _TERMINAL_RUN_STATUSES:
            update["completed_at"] = datetime.now(UTC).isoformat()
        return existing.model_copy(update=update)

    async def _persist_run_memory(self, result: RunResult) -> None:
        """Persist a run-envelope snapshot through the configured ``MemoryPort``.

        The thread handle defaults to the run id, matching the workflow engine
        adapter's thread derivation for resumable runs. No-op when no memory
        port is configured; long-term indexing is the adapter's concern.
        """
        if self._memory is None:
            return
        await self._memory.save_thread_state(
            result.run_id,
            result.tenant_id,
            {
                "run_id": result.run_id,
                "workflow_id": result.workflow_id,
                "trace_id": result.trace_id,
                "tenant_id": result.tenant_id,
                "workflow_type": result.workflow_type,
                "status": result.status.value,
                "created_at": result.created_at,
                "started_at": result.started_at,
                "completed_at": result.completed_at,
                "error_code": (result.error or {}).get("code"),
            },
        )

    async def _restore_run_from_memory(
        self, run_id: str, tenant_id: str
    ) -> RunResult | None:
        """Rebuild a run record from its persisted snapshot on a local miss.

        Read-through for multi-worker deployments and process restarts: a run
        submitted, resumed, or cancelled on another worker stays visible here
        for get/cancel/resume. The snapshot is a reduced envelope (no output
        or error body), so restored records are degraded: output is None and
        only the structured error code survives. Malformed or tenant-mismatched
        snapshots fail closed to None.
        """
        if self._memory is None:
            return None
        snapshot = await self._memory.get_thread_state(run_id, tenant_id)
        if not isinstance(snapshot, dict):
            return None
        required = (
            "run_id",
            "workflow_id",
            "trace_id",
            "tenant_id",
            "workflow_type",
            "status",
            "created_at",
        )
        if any(key not in snapshot for key in required):
            return None
        if snapshot["tenant_id"] != tenant_id or snapshot["run_id"] != run_id:
            return None
        try:
            status = RunStatus(snapshot["status"])
        except ValueError:
            return None
        error_code = snapshot.get("error_code")
        restored = RunResult(
            run_id=run_id,
            workflow_id=str(snapshot["workflow_id"]),
            trace_id=str(snapshot["trace_id"]),
            tenant_id=tenant_id,
            workflow_type=str(snapshot["workflow_type"]),
            status=status,
            output=None,
            error={"code": error_code} if error_code else None,
            created_at=str(snapshot["created_at"]),
            started_at=snapshot.get("started_at"),
            completed_at=snapshot.get("completed_at"),
        )
        self._runs[run_id] = restored
        return restored

    async def _emit(self, event: RuntimeEvent) -> None:
        """Publish an event through the configured event bus (no-op if none)."""
        if self._event_bus is not None:
            await self._event_bus.publish(event)

    async def _emit_status_event(self, result: RunResult) -> None:
        """Publish the lifecycle event matching a stored run's current status.

        Maps terminal statuses (completed/failed/cancelled) and the resumable
        pause/interrupt state onto their event kinds. Unknown kinds are skipped.
        """
        kind_by_status = {
            RunStatus.COMPLETED: RUN_COMPLETED,
            RunStatus.FAILED: RUN_FAILED,
            RunStatus.PAUSED: RUN_PAUSED,
            RunStatus.CANCELLED: RUN_CANCELLED,
        }
        kind = kind_by_status.get(result.status)
        if kind is None:
            return
        payload = {"error_code": (result.error or {}).get("code")} if result.error else {}
        await self._emit(
            RuntimeEvent(
                kind=kind,
                run_id=result.run_id,
                tenant_id=result.tenant_id,
                workflow_type=result.workflow_type,
                status=result.status.value,
                payload=payload,
            )
        )

    async def get_run(self, run_id: str, tenant_id: str) -> RunResult | None:
        """Tenant-scoped run lookup; returns None for missing or inaccessible runs.

        On a local miss, reads through to the configured MemoryPort so runs
        persisted by another worker (or before a process restart) stay
        visible. The restored record is degraded: the persisted snapshot
        carries no output or error body, only the structured error code.
        """
        if not tenant_id:
            raise TenantRequiredError(details={"run_id": run_id})
        result = self._runs.get(run_id)
        if result is not None:
            return result if result.tenant_id == tenant_id else None
        return await self._restore_run_from_memory(run_id, tenant_id)

    async def cancel_run(self, run_id: str, tenant_id: str) -> RunResult:
        """Cancel a run if it belongs to the tenant."""
        if not tenant_id:
            raise TenantRequiredError(details={"run_id": run_id})
        result = await self.get_run(run_id, tenant_id)
        if result is None:
            raise RunNotFoundError(run_id)
        if result.status not in _CANCELLABLE_STATUSES:
            # Terminal runs are immutable: cancelling a completed/failed/
            # cancelled run would rewrite its historical outcome.
            raise AgentRuntimeError(
                f"Run {run_id} is already terminal ({result.status.value}); cannot cancel",
                code="RUN_NOT_CANCELLABLE",
                details={"run_id": run_id, "status": result.status.value},
            )
        cancelled = result.model_copy(
            update={
                "status": RunStatus.CANCELLED,
                "completed_at": datetime.now(UTC).isoformat(),
            }
        )
        self._runs[run_id] = cancelled
        # Mirror the cancellation through memory so other workers (and a
        # restarted process) observe the terminal state instead of a stale
        # in-flight record.
        await self._persist_run_memory(cancelled)
        await self._emit_status_event(cancelled)
        return self._runs[run_id]

    async def list_runs(
        self,
        tenant_id: str,
        *,
        workflow_type: str | None = None,
        status: str | None = None,
    ) -> list[RunSummary]:
        """List runs scoped to tenant with optional filters.

        Worker-local: this iterates the in-process run store only. Runs
        persisted by other workers stay visible via ``get_run``'s memory
        read-through, but cross-worker listing needs a MemoryPort list
        operation (deferred to the durable run-store phase).
        """
        if not tenant_id:
            raise TenantRequiredError()
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

    async def resume_run(
        self, run_id: str, tenant_id: str, resume: ResumeRequest
    ) -> RunResult:
        """Resume a paused run through the configured workflow engine.

        Fails closed when tenant context is absent, no workflow engine is
        configured, or the run is not visible to the requesting tenant. The
        engine's own resume path owns checkpoint lookup and conflict policy;
        on success the resumed result replaces the stored run record.
        """
        if not tenant_id:
            raise TenantRequiredError()
        if self._workflow_engine is None:
            raise AgentRuntimeError(
                "Resume unavailable: no workflow engine is configured",
                code="RESUME_UNAVAILABLE",
                details={"run_id": run_id},
            )
        existing = await self.get_run(run_id, tenant_id)
        if existing is None:
            raise RunNotFoundError(run_id)

        resume_ctx = RuntimeContext(
            tenant_id=existing.tenant_id,
            trace_id=existing.trace_id,
            run_id=existing.run_id,
            workflow_id=existing.workflow_id,
            workflow_type=existing.workflow_type,
        )
        with with_context(resume_ctx):
            result = await self._workflow_engine.resume(
                existing.workflow_type, run_id, resume, resume_ctx
            )

        updated = self._finalize_run(existing, result)
        self._runs[run_id] = updated
        await self._persist_run_memory(updated)
        await self._emit(
            RuntimeEvent(
                kind=RUN_RESUMED,
                run_id=run_id,
                tenant_id=updated.tenant_id,
                workflow_type=updated.workflow_type,
                status=updated.status.value,
            )
        )
        await self._emit_status_event(updated)
        return updated

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
        if not ctx.tenant_id:
            raise TenantRequiredError(details={"tool_name": name})
        try:
            await self.authorize_tool(name, ctx)
        except ToolForbiddenError:
            # A denial is a first-class observability event: emit it before
            # surfacing the structured error to the caller.
            await self._emit(
                RuntimeEvent(
                    kind=TOOL_DENIED,
                    run_id=ctx.run_id,
                    tenant_id=ctx.tenant_id,
                    workflow_type=ctx.workflow_type,
                    tool_name=name,
                )
            )
            raise
        if self._tool_registry is None:
            raise ToolRegistryUnavailableError(name)
        result = await self._tool_registry.execute(name, arguments, ctx)
        await self._emit(
            RuntimeEvent(
                kind=TOOL_CALLED,
                run_id=ctx.run_id,
                tenant_id=ctx.tenant_id,
                workflow_type=ctx.workflow_type,
                tool_name=name,
            )
        )
        return result
