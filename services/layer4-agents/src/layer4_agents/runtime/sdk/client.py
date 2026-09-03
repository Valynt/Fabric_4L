"""High-level async Python SDK client for the Agent Runtime.

Phases 0-3 shipped the in-process ``AgentRuntimeImpl`` spine but no HTTP
surface (``/v1/runtime`` introspection routes are Phase 5 work), so
``AgentRuntimeClient`` binds to any object satisfying the ``AgentRuntime``
port and treats that binding as the injectable transport seam. When the HTTP
routes exist, a remote binding can be supplied behind the same client surface
without changing callers.
"""

from __future__ import annotations

import asyncio
from types import TracebackType
from typing import Any
from uuid import uuid4

from ..errors import AgentRuntimeError, RunNotFoundError, TenantRequiredError
from ..models import (
    ResumeRequest,
    RunEnvelope,
    RunRequest,
    RunResult,
    RunStatus,
    RunSummary,
    RuntimeContext,
)
from ..ports import AgentRuntime

__all__ = ["AgentRuntimeClient", "RunsNamespace", "SDKTimeoutError"]

_ACTIVE_STATUSES = frozenset({RunStatus.PENDING, RunStatus.RUNNING, RunStatus.RETRYING})


class SDKTimeoutError(AgentRuntimeError):
    """Raised when ``wait_for_run`` exceeds its deadline on an active run."""

    def __init__(self, run_id: str, timeout_seconds: float) -> None:
        super().__init__(
            f"Run {run_id} did not reach a terminal state within {timeout_seconds:g}s",
            code="SDK_WAIT_TIMEOUT",
            details={"run_id": run_id, "timeout_seconds": timeout_seconds},
        )


class RunsNamespace:
    """Convenience ``client.runs.*`` surface mirroring the SDK example shape."""

    def __init__(self, client: AgentRuntimeClient) -> None:
        self._client = client

    async def submit(
        self,
        workflow_type: str,
        input_data: dict[str, Any] | None = None,
        *,
        tenant_id: str | None = None,
        workflow_id: str | None = None,
        priority: int = 3,
        timeout_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
        user_id: str | None = None,
    ) -> RunEnvelope:
        return await self._client.submit_run(
            workflow_type,
            input_data=input_data,
            tenant_id=tenant_id,
            workflow_id=workflow_id,
            priority=priority,
            timeout_seconds=timeout_seconds,
            metadata=metadata,
            trace_id=trace_id,
            user_id=user_id,
        )

    async def wait(
        self,
        run_id: str,
        *,
        tenant_id: str | None = None,
        timeout_seconds: float = 30.0,
        poll_interval: float | None = None,
    ) -> RunResult:
        return await self._client.wait_for_run(
            run_id,
            tenant_id=tenant_id,
            timeout_seconds=timeout_seconds,
            poll_interval=poll_interval,
        )

    async def get(self, run_id: str, *, tenant_id: str | None = None) -> RunResult | None:
        return await self._client.get_run(run_id, tenant_id=tenant_id)

    async def list(
        self,
        *,
        tenant_id: str | None = None,
        workflow_type: str | None = None,
        status: str | None = None,
    ) -> list[RunSummary]:
        return await self._client.list_runs(
            tenant_id=tenant_id,
            workflow_type=workflow_type,
            status=status,
        )

    async def cancel(self, run_id: str, *, tenant_id: str | None = None) -> RunResult:
        return await self._client.cancel_run(run_id, tenant_id=tenant_id)

    async def resume(
        self,
        run_id: str,
        *,
        tenant_id: str | None = None,
        resume_data: dict[str, Any] | None = None,
        checkpoint_id: str | None = None,
        checkpoint_hash: str | None = None,
    ) -> RunResult:
        return await self._client.resume_run(
            run_id,
            tenant_id=tenant_id,
            resume_data=resume_data,
            checkpoint_id=checkpoint_id,
            checkpoint_hash=checkpoint_hash,
        )


class AgentRuntimeClient:
    """Async facade over an ``AgentRuntime`` for services and tests.

    Run identity is owned by the runtime: the returned envelope's ``run_id``
    is authoritative for ``get_run``/``wait_for_run``/``cancel_run``/``resume``.
    """

    def __init__(
        self,
        runtime: AgentRuntime,
        *,
        default_tenant_id: str | None = None,
        poll_interval: float = 0.05,
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than zero")
        self._runtime = runtime
        self._default_tenant_id = default_tenant_id
        self._poll_interval = poll_interval
        self.runs = RunsNamespace(self)

    async def __aenter__(self) -> AgentRuntimeClient:
        await self._runtime.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        await self._runtime.stop()

    def _resolve_tenant(self, tenant_id: str | None, *, operation: str) -> str:
        resolved = (tenant_id or self._default_tenant_id or "").strip()
        if not resolved:
            raise TenantRequiredError(details={"operation": operation})
        return resolved

    def _build_context(
        self,
        *,
        tenant_id: str,
        workflow_type: str,
        run_id: str,
        workflow_id: str | None,
        priority: int,
        trace_id: str | None,
        user_id: str | None,
        metadata: dict[str, Any],
    ) -> RuntimeContext:
        return RuntimeContext(
            tenant_id=tenant_id,
            user_id=user_id,
            trace_id=trace_id or str(uuid4()),
            run_id=run_id,
            workflow_id=workflow_id or run_id,
            workflow_type=workflow_type,
            priority=priority,
            metadata=dict(metadata),
        )

    async def submit_run(
        self,
        workflow_type: str,
        input_data: dict[str, Any] | None = None,
        *,
        tenant_id: str | None = None,
        workflow_id: str | None = None,
        priority: int = 3,
        timeout_seconds: int | None = None,
        metadata: dict[str, Any] | None = None,
        trace_id: str | None = None,
        user_id: str | None = None,
    ) -> RunEnvelope:
        """Submit a workflow run; returns the identity envelope (PENDING)."""
        tenant = self._resolve_tenant(tenant_id, operation="submit_run")
        run_id = str(uuid4())
        request = RunRequest(
            workflow_type=workflow_type,
            input_data=input_data or {},
            workflow_id=workflow_id,
            priority=priority,
            timeout_seconds=timeout_seconds,
            metadata=metadata or {},
        )
        ctx = self._build_context(
            tenant_id=tenant,
            workflow_type=workflow_type,
            run_id=run_id,
            workflow_id=workflow_id,
            priority=priority,
            trace_id=trace_id,
            user_id=user_id,
            metadata=request.metadata,
        )
        return await self._runtime.submit_run(request, ctx)

    async def get_run(self, run_id: str, *, tenant_id: str | None = None) -> RunResult | None:
        """Tenant-scoped run lookup; None for missing or inaccessible runs."""
        tenant = self._resolve_tenant(tenant_id, operation="get_run")
        return await self._runtime.get_run(run_id, tenant)

    async def list_runs(
        self,
        *,
        tenant_id: str | None = None,
        workflow_type: str | None = None,
        status: str | None = None,
    ) -> list[RunSummary]:
        """List runs scoped to a tenant with optional type/status filters."""
        tenant = self._resolve_tenant(tenant_id, operation="list_runs")
        return await self._runtime.list_runs(tenant, workflow_type=workflow_type, status=status)

    async def cancel_run(self, run_id: str, *, tenant_id: str | None = None) -> RunResult:
        """Cancel a run belonging to the resolved tenant."""
        tenant = self._resolve_tenant(tenant_id, operation="cancel_run")
        return await self._runtime.cancel_run(run_id, tenant)

    async def resume_run(
        self,
        run_id: str,
        *,
        tenant_id: str | None = None,
        resume_data: dict[str, Any] | None = None,
        checkpoint_id: str | None = None,
        checkpoint_hash: str | None = None,
    ) -> RunResult:
        """Resume a paused/interrupted run for the resolved tenant."""
        tenant = self._resolve_tenant(tenant_id, operation="resume_run")
        resume = ResumeRequest(
            resume_data=resume_data or {},
            checkpoint_id=checkpoint_id,
            checkpoint_hash=checkpoint_hash,
        )
        return await self._runtime.resume_run(run_id, tenant, resume)

    async def wait_for_run(
        self,
        run_id: str,
        *,
        tenant_id: str | None = None,
        timeout_seconds: float = 30.0,
        poll_interval: float | None = None,
    ) -> RunResult:
        """Poll until the run leaves the active set (or raise on timeout).

        A ``get_run`` miss fails closed as ``RunNotFoundError``; a run still
        active when the deadline passes raises ``SDKTimeoutError``.
        """
        tenant = self._resolve_tenant(tenant_id, operation="wait_for_run")
        interval = self._poll_interval if poll_interval is None else poll_interval
        loop = asyncio.get_running_loop()
        deadline = loop.time() + timeout_seconds
        while True:
            result = await self._runtime.get_run(run_id, tenant)
            if result is None:
                raise RunNotFoundError(run_id)
            if result.status not in _ACTIVE_STATUSES:
                return result
            if loop.time() >= deadline:
                raise SDKTimeoutError(run_id, timeout_seconds)
            await asyncio.sleep(interval)
