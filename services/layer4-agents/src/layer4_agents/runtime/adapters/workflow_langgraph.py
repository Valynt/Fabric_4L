"""WorkflowEnginePort adapter bridging the legacy LangGraph workflow layer.

The Layer 4 Agent Runtime exposes a provider-agnostic ``WorkflowEnginePort``.
This adapter implements that port over the existing LangGraph-backed workflow
layer (``layer4_agents.workflows``): it dispatches through the canonical
``create_workflow`` factory, seeds initial state through each workflow's
``create_initial_state``, executes through ``BaseWorkflow.run``, and maps the
resulting legacy ``AgentState`` back onto the canonical runtime
``WorkflowResult``.

Resume is supported when a ``CheckpointPort`` is configured: the adapter
persists a tenant-scoped, JSON-safe snapshot whenever a run stops in a
resumable state (PAUSED/INTERRUPTED) and re-hydrates the typed state from that
snapshot on ``resume`` — mirroring the legacy OrchestrationController resume
semantics without reaching into the engine's state manager.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
from collections.abc import Callable
from contextvars import Token
from datetime import UTC, datetime
from enum import Enum
from inspect import signature
from typing import Any
from uuid import uuid4

from pydantic import BaseModel
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_SERVICE_ACCOUNT,
    RequestContext,
    _current_context,
    get_request_context,
    set_request_context,
)

from ...models.agent_state import WorkflowStatus
from ...tools.registry import ToolRegistry
from ...workflows import WORKFLOW_TYPES, create_workflow
from ..errors import (
    AgentRuntimeError,
    CheckpointConflictError,
    RunNotFoundError,
    TenantRequiredError,
    WorkflowTypeNotFoundError,
)
from ..models import Checkpoint, ResumeRequest, RunStatus, RuntimeContext, WorkflowResult
from ..ports import CheckpointPort

#: Legacy statuses that leave a run resumable (mirrors the legacy executor set).
_RESUMABLE_STATUSES: frozenset[WorkflowStatus] = frozenset(
    {
        WorkflowStatus.PENDING,
        WorkflowStatus.RUNNING,
        WorkflowStatus.PAUSED,
        WorkflowStatus.INTERRUPTED,
    }
)


def _to_run_status(legacy_status: Any) -> RunStatus:
    """Map a legacy ``WorkflowStatus`` onto the canonical runtime ``RunStatus``.

    The runtime contract has no ``interrupted`` value, so legacy INTERRUPTED
    runs surface as ``RunStatus.PAUSED`` (resumable). The original status is
    preserved in the result error/output metadata by the caller when relevant.
    """
    try:
        status = WorkflowStatus(legacy_status)
    except (TypeError, ValueError):
        status = WorkflowStatus.PENDING
    if status == WorkflowStatus.COMPLETED:
        return RunStatus.COMPLETED
    if status == WorkflowStatus.FAILED:
        return RunStatus.FAILED
    if status == WorkflowStatus.CANCELLED:
        return RunStatus.CANCELLED
    if status in (WorkflowStatus.PAUSED, WorkflowStatus.INTERRUPTED):
        return RunStatus.PAUSED
    if status == WorkflowStatus.RUNNING:
        return RunStatus.RUNNING
    return RunStatus.PENDING


def _json_safe(value: Any) -> Any:
    """Recursively normalize a value into a JSON-safe structure.

    Handles pydantic models, enums, datetimes, and bytes so snapshots can be
    persisted and hashed deterministically without leaking unserializable
    artifacts into the checkpoint store.
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value
    if isinstance(value, Enum):
        inner = value.value
        return inner if isinstance(inner, (str, int, float, bool)) else str(inner)
    if isinstance(value, BaseModel):
        return _json_safe(value.model_dump(mode="python"))
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, bytes):
        return {"__bytes_length__": len(value)}
    if isinstance(value, dict):
        return {str(key): _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set, frozenset)):
        return [_json_safe(item) for item in value]
    try:
        json.dumps(value)
        return value
    except (TypeError, ValueError):
        return str(value)


def _state_payload(state: Any) -> dict[str, Any]:
    """Return a JSON-safe, portable snapshot of a typed workflow state."""
    if isinstance(state, BaseModel):
        dumped: dict[str, Any] = state.model_dump(mode="python")
    elif hasattr(state, "model_dump"):
        dumped = state.model_dump(mode="python")  # type: ignore[no-any-return]
    else:
        dumped = dict(state)
    normalized = _json_safe(dumped)
    assert isinstance(normalized, dict)
    return normalized


def _state_hash(payload: dict[str, Any]) -> str:
    """Compute a stable content hash over a JSON-safe state snapshot."""
    encoded = json.dumps(payload, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


class LangGraphWorkflowEngineAdapter:
    """WorkflowEnginePort implemented over the legacy LangGraph workflow layer."""

    def __init__(
        self,
        *,
        tool_registry: Any | None = None,
        checkpoint_saver: Any | None = None,
        checkpoint_port: CheckpointPort | None = None,
        create_workflow_fn: Callable[..., Any] | None = None,
        workflow_types: set[str] | None = None,
    ) -> None:
        """Wrap the legacy workflow layer behind the runtime port.

        Args:
            tool_registry: Legacy registry the workflows execute tools through.
                Defaults to a fresh ``ToolRegistry()`` (keeps tests hermetic).
            checkpoint_saver: Optional LangGraph ``BaseCheckpointSaver`` passed
                to ``create_workflow`` for native thread checkpointing.
            checkpoint_port: Optional ``CheckpointPort`` used to persist and
                reload resume snapshots. Required for ``resume`` to work.
            create_workflow_fn: Factory with the ``create_workflow`` signature.
                Defaults to the canonical legacy factory; override in tests.
            workflow_types: Supported workflow type names. Defaults to the keys
                of the legacy ``WORKFLOW_TYPES`` registry.
        """
        self._tool_registry = tool_registry if tool_registry is not None else ToolRegistry()
        self._checkpoint_saver = checkpoint_saver
        self._checkpoint_port = checkpoint_port
        self._create_workflow: Callable[..., Any] = create_workflow_fn or create_workflow
        self._workflow_types = (
            set(workflow_types) if workflow_types is not None else set(WORKFLOW_TYPES)
        )

    # ------------------------------------------------------------------
    # WorkflowEnginePort
    # ------------------------------------------------------------------

    def get_supported_types(self) -> set[str]:
        """Return the set of workflow types this engine supports."""
        return set(self._workflow_types)

    async def execute(
        self,
        workflow_type: str,
        input_data: dict[str, Any],
        ctx: RuntimeContext,
        checkpoint: Checkpoint | None = None,
    ) -> WorkflowResult:
        """Execute a workflow from input data through the legacy LangGraph layer.

        Fails closed on missing tenant context or an unknown workflow type.
        A fresh run never starts from an existing ``Checkpoint`` — replaying a
        checkpointed run is the job of ``resume``.
        """
        self._require_tenant(ctx)
        if workflow_type not in self._workflow_types:
            raise WorkflowTypeNotFoundError(workflow_type)
        if checkpoint is not None:
            raise AgentRuntimeError(
                "Fresh runs cannot start from an existing checkpoint; use resume()",
                code="EXECUTE_WITH_CHECKPOINT_UNSUPPORTED",
                details={"workflow_type": workflow_type, "run_id": ctx.run_id},
            )

        workflow = self._build_workflow(workflow_type)
        initial_state = self._create_initial_state(workflow, input_data, ctx)
        thread_id = ctx.run_id or ctx.workflow_id or str(uuid4())

        token = self._enter_execution_context(ctx)
        try:
            final_state = await workflow.run(initial_state, thread_id=thread_id)
        except asyncio.CancelledError:
            raise
        except AgentRuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001 - adapter boundary maps to a result
            return WorkflowResult(
                status=RunStatus.FAILED,
                output=None,
                error={
                    "code": "WORKFLOW_EXECUTION_ERROR",
                    "message": f"Workflow {workflow_type} raised {type(exc).__name__}: {exc}",
                    "error_type": type(exc).__name__,
                    "workflow_type": workflow_type,
                    "run_id": ctx.run_id,
                },
                checkpoint=None,
            )
        finally:
            if token is not None:
                _current_context.reset(token)

        return await self._map_result(workflow_type, final_state, ctx, thread_id)

    async def resume(
        self,
        workflow_type: str,
        run_id: str,
        resume_request: ResumeRequest,
        ctx: RuntimeContext,
    ) -> WorkflowResult:
        """Resume a paused/interrupted run from its persisted snapshot.

        The snapshot is located tenant-scoped via the configured
        ``CheckpointPort``; a run that does not exist for the requesting tenant
        fails closed with ``RunNotFoundError``. Stale checkpoint references are
        rejected per the canonical replay-conflict policy.
        """
        self._require_tenant(ctx)
        if workflow_type not in self._workflow_types:
            raise WorkflowTypeNotFoundError(workflow_type)
        if self._checkpoint_port is None:
            raise AgentRuntimeError(
                "Resume unavailable: no checkpoint store is configured",
                code="RESUME_UNAVAILABLE",
                details={"run_id": run_id, "workflow_type": workflow_type},
            )

        checkpoints = await self._checkpoint_port.list(run_id, ctx.tenant_id)
        if not checkpoints:
            raise RunNotFoundError(run_id)

        latest = checkpoints[-1]
        if resume_request.checkpoint_id and latest.checkpoint_id != resume_request.checkpoint_id:
            raise CheckpointConflictError(
                f"Checkpoint mismatch for run {run_id}: requested "
                f"{resume_request.checkpoint_id}, latest is {latest.checkpoint_id}",
                details={"run_id": run_id, "checkpoint_id": latest.checkpoint_id},
            )

        loaded = await self._checkpoint_port.load(
            run_id,
            latest.thread_id,
            ctx.tenant_id,
            checkpoint_id=latest.checkpoint_id,
        )
        if loaded is None:
            raise RunNotFoundError(run_id)
        checkpoint, payload = loaded

        if resume_request.checkpoint_hash and checkpoint.state_hash != resume_request.checkpoint_hash:
            raise CheckpointConflictError(
                f"State hash mismatch for run {run_id}: refusing to resume a stale snapshot",
                details={"run_id": run_id, "checkpoint_id": checkpoint.checkpoint_id},
            )

        workflow = self._build_workflow(workflow_type)
        state = self._reconstruct_state(workflow, payload, workflow_type, run_id)
        if state.status not in _RESUMABLE_STATUSES:
            raise AgentRuntimeError(
                f"Run {run_id} is {state.status.value} and cannot be resumed",
                code="RUN_NOT_RESUMABLE",
                details={"run_id": run_id, "status": state.status.value},
            )

        # Mirror the legacy executor: record the resume decision in output_data.
        if resume_request.resume_data:
            output_data = dict(state.output_data or {})
            output_data["resume_decision"] = resume_request.resume_data
            output_data["resumed_at"] = datetime.now(UTC).isoformat()
            state.output_data = output_data

        token = self._enter_execution_context(ctx)
        try:
            final_state = await workflow.run(
                state,
                thread_id=checkpoint.thread_id,
                resume_data=resume_request.resume_data or None,
            )
        except asyncio.CancelledError:
            raise
        except AgentRuntimeError:
            raise
        except Exception as exc:  # noqa: BLE001 - adapter boundary maps to a result
            return WorkflowResult(
                status=RunStatus.FAILED,
                output=None,
                error={
                    "code": "WORKFLOW_EXECUTION_ERROR",
                    "message": (
                        f"Resume of {workflow_type} (run {run_id}) raised "
                        f"{type(exc).__name__}: {exc}"
                    ),
                    "error_type": type(exc).__name__,
                    "workflow_type": workflow_type,
                    "run_id": run_id,
                },
                checkpoint=None,
            )
        finally:
            if token is not None:
                _current_context.reset(token)

        return await self._map_result(workflow_type, final_state, ctx, checkpoint.thread_id)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _require_tenant(ctx: RuntimeContext) -> None:
        """Fail closed when tenant context is absent."""
        if not ctx.tenant_id:
            raise TenantRequiredError()

    def _build_workflow(self, workflow_type: str) -> Any:
        """Construct a workflow instance through the configured factory."""
        try:
            return self._create_workflow(workflow_type, self._tool_registry, self._checkpoint_saver)
        except ValueError as exc:
            if workflow_type not in self._workflow_types:
                raise WorkflowTypeNotFoundError(workflow_type) from exc
            raise AgentRuntimeError(
                f"Could not construct workflow '{workflow_type}': {exc}",
                code="WORKFLOW_CONSTRUCTION_ERROR",
                details={"workflow_type": workflow_type},
            ) from exc

    @classmethod
    def _create_initial_state(
        cls,
        workflow: Any,
        input_data: dict[str, Any],
        ctx: RuntimeContext,
    ) -> Any:
        """Seed initial state, passing only the correlation kwargs the workflow accepts."""
        try:
            param_names: set[str] = set(signature(workflow.create_initial_state).parameters)
        except (TypeError, ValueError):
            param_names = set()
        kwargs: dict[str, Any] = {}
        if "tenant_id" in param_names:
            kwargs["tenant_id"] = ctx.tenant_id
        for key in ("run_id", "trace_id", "workflow_id"):
            value = getattr(ctx, key, None)
            if key in param_names and value:
                kwargs[key] = value
        return workflow.create_initial_state(input_data, **kwargs)

    @staticmethod
    def _reconstruct_state(
        workflow: Any,
        payload: dict[str, Any],
        workflow_type: str,
        run_id: str,
    ) -> Any:
        """Re-hydrate the typed state from a stored snapshot payload."""
        state_type = workflow._get_state_type()
        try:
            return state_type(**payload)
        except Exception as exc:  # noqa: BLE001 - report structured reconstruction failure
            raise AgentRuntimeError(
                f"Could not reconstruct state for run {run_id}: {exc}",
                code="STATE_RECONSTRUCTION_FAILED",
                details={"run_id": run_id, "workflow_type": workflow_type},
            ) from exc

    async def _map_result(
        self,
        workflow_type: str,
        final_state: Any,
        ctx: RuntimeContext,
        thread_id: str,
    ) -> WorkflowResult:
        """Map a legacy terminal ``AgentState`` onto the canonical ``WorkflowResult``."""
        legacy_status = getattr(final_state, "status", WorkflowStatus.PENDING)
        status = _to_run_status(legacy_status)

        output: dict[str, Any] | None = None
        if status in (RunStatus.COMPLETED, RunStatus.PAUSED):
            output_data = getattr(final_state, "output_data", None)
            if output_data:
                output = _json_safe(output_data)

        error: dict[str, Any] | None = None
        if status in (RunStatus.FAILED, RunStatus.CANCELLED):
            errors = list(getattr(final_state, "errors", None) or [])
            error = {
                "code": "WORKFLOW_EXECUTION_FAILED",
                "message": errors[0] if errors else f"Workflow ended in {legacy_status.value}",
                "errors": errors,
                "workflow_type": workflow_type,
                "run_id": ctx.run_id,
            }

        checkpoint: Checkpoint | None = None
        if self._checkpoint_port is not None and legacy_status in _RESUMABLE_STATUSES:
            checkpoint = await self._persist_checkpoint(
                workflow_type, final_state, ctx, thread_id, status
            )

        return WorkflowResult(status=status, output=output, error=error, checkpoint=checkpoint)

    async def _persist_checkpoint(
        self,
        workflow_type: str,
        final_state: Any,
        ctx: RuntimeContext,
        thread_id: str,
        run_status: RunStatus,
    ) -> Checkpoint:
        """Persist a resume snapshot and return its portable checkpoint metadata."""
        port = self._checkpoint_port
        if port is None:
            # Callers guard on _checkpoint_port; fail closed defensively.
            raise AgentRuntimeError(
                "Cannot persist checkpoint: no checkpoint store is configured",
                code="CHECKPOINT_PERSIST_UNAVAILABLE",
                details={"run_id": ctx.run_id, "workflow_type": workflow_type},
            )
        payload = _state_payload(final_state)
        state_hash = _state_hash(payload)
        node = getattr(final_state, "current_node", None) or "state"
        checkpoint = Checkpoint(
            checkpoint_id=f"{ctx.run_id}:{node}:{state_hash[:8]}",
            run_id=ctx.run_id,
            thread_id=thread_id,
            tenant_id=ctx.tenant_id,
            state_hash=state_hash,
            created_at=datetime.now(UTC).isoformat(),
            metadata={
                "workflow_type": workflow_type,
                "status": run_status.value,
                "current_node": node,
            },
        )
        await port.save(checkpoint, payload)
        return checkpoint

    @staticmethod
    def _enter_execution_context(ctx: RuntimeContext) -> Token | None:
        """Synthesize ambient workflow RequestContext when none is present.

        Mirrors the legacy OrchestrationController: tools executed inside
        workflow nodes resolve their execution tenant from the ambient
        ``RequestContext`` when one exists. Returns the reset token or None.

        The synthesized context carries a non-bypass ``service`` role:
        ``authorize_action`` short-circuits for ``system``/``super_admin``,
        so elevating the ambient executor to ``system`` would bypass every
        gated tool action. Grants flow only from trusted runtime metadata
        (populated by the HTTP layer from the authenticated request), so
        missing grants still fail closed.
        """
        token: Token | None = None
        try:
            if ctx.tenant_id and get_request_context() is None:
                metadata = ctx.metadata or {}
                scopes = [
                    str(scope)
                    for scope in metadata.get("service_account_scopes") or []
                    if isinstance(scope, str)
                ]
                permissions = [
                    str(permission)
                    for permission in metadata.get("permissions") or []
                    if isinstance(permission, str)
                ]
                token = set_request_context(
                    RequestContext(
                        tenant_id=ctx.tenant_id,
                        user_id=ctx.user_id or "workflow_executor",
                        roles=["service"],
                        source=AUTH_SOURCE_SERVICE_ACCOUNT,
                        auth_source=AUTH_SOURCE_SERVICE_ACCOUNT,
                        request_id=ctx.workflow_id or ctx.run_id,
                        trace_id=ctx.trace_id or ctx.run_id,
                        permissions=permissions,
                        service_account_id="layer4-workflow-executor",
                        service_account_scopes=scopes,
                    )
                )
        except Exception:  # noqa: BLE001 - ambient context is best-effort
            return None
        return token
