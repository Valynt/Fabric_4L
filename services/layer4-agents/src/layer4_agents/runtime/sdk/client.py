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

import httpx

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

__all__ = [
    "AgentRuntimeClient",
    "RemoteAgentRuntimeClient",
    "RunsNamespace",
    "SDKTimeoutError",
]

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
        runtime: AgentRuntime | None = None,
        *,
        default_tenant_id: str | None = None,
        poll_interval: float = 0.05,
        base_url: str | None = None,
        http_client: httpx.AsyncClient | None = None,
        auth_token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        if poll_interval <= 0:
            raise ValueError("poll_interval must be greater than zero")
        if runtime is None and not base_url and http_client is None:
            raise ValueError("runtime, base_url, or http_client is required")
        if timeout_seconds <= 0:
            raise ValueError("timeout_seconds must be greater than zero")
        self._runtime = runtime
        self._default_tenant_id = default_tenant_id
        self._poll_interval = poll_interval
        inferred_base_url = str(http_client.base_url) if http_client is not None else ""
        self._base_url = (base_url or inferred_base_url).rstrip("/")
        self._http_client = http_client
        self._owns_http_client = http_client is None and runtime is None
        self._auth_token = auth_token
        self._timeout_seconds = timeout_seconds
        self.runs = RunsNamespace(self)

    async def __aenter__(self) -> AgentRuntimeClient:
        if self._runtime is not None:
            await self._runtime.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        traceback: TracebackType | None,
    ) -> None:
        if self._runtime is not None:
            await self._runtime.stop()
        if self._owns_http_client and self._http_client is not None:
            await self._http_client.aclose()

    @property
    def is_remote(self) -> bool:
        """Whether this client uses the HTTP transport."""
        return self._runtime is None

    async def aclose(self) -> None:
        """Close an owned HTTP transport."""
        await self.__aexit__(None, None, None)

    def _http_url(self, path: str) -> str:
        base = self._base_url
        if not base:
            raise ValueError("base_url is required for the HTTP transport")
        if base.endswith("/v1/runtime"):
            return f"{base}/{path.lstrip('/')}"
        return f"{base}/v1/runtime/{path.lstrip('/')}"

    async def _get_http_client(self) -> httpx.AsyncClient:
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=self._timeout_seconds)
        return self._http_client

    async def _remote_request(
        self,
        method: str,
        path: str,
        *,
        tenant_id: str,
        json: dict[str, Any] | None = None,
        params: dict[str, str] | None = None,
        run_id: str | None = None,
    ) -> Any:
        client = await self._get_http_client()
        headers = {"X-Tenant-ID": tenant_id}
        if self._auth_token:
            headers["Authorization"] = "Bearer " + self._auth_token
        try:
            response = await client.request(
                method,
                self._http_url(path),
                headers=headers,
                json=json,
                params=params,
                timeout=self._timeout_seconds,
            )
        except httpx.TimeoutException as exc:
            raise SDKTimeoutError(run_id or path, self._timeout_seconds) from exc
        except httpx.HTTPError as exc:
            raise AgentRuntimeError(
                f"Runtime transport failed: {type(exc).__name__}",
                code="SDK_TRANSPORT_ERROR",
                details={"operation": path},
            ) from exc

        if response.status_code >= 400:
            try:
                payload = response.json()
            except ValueError:
                payload = {}
            detail = payload.get("detail", payload) if isinstance(payload, dict) else {}
            if not isinstance(detail, dict):
                detail = {"message": str(detail)}
            code = str(detail.get("code") or f"HTTP_{response.status_code}")
            message = str(detail.get("message") or response.reason_phrase or "Runtime request failed")
            details = detail.get("details")
            if not isinstance(details, dict):
                details = {"status_code": response.status_code}
            if response.status_code in (408, 504):
                raise SDKTimeoutError(run_id or path, self._timeout_seconds)
            if code == "TENANT_REQUIRED":
                raise TenantRequiredError(details=details)
            if code == "RUN_NOT_FOUND" or response.status_code == 404:
                raise RunNotFoundError(run_id or str(details.get("run_id", "")))
            raise AgentRuntimeError(message, code=code, details=details)
        if response.status_code == 204 or not response.content:
            return None
        return response.json()

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
        if self.is_remote:
            return RunEnvelope.model_validate(
                await self._remote_request(
                    "POST",
                    "runs",
                    tenant_id=tenant,
                    json=request.model_dump(mode="json"),
                    run_id=run_id,
                )
            )
        assert self._runtime is not None
        return await self._runtime.submit_run(request, ctx)

    async def get_run(self, run_id: str, *, tenant_id: str | None = None) -> RunResult | None:
        """Tenant-scoped run lookup; None for missing or inaccessible runs."""
        tenant = self._resolve_tenant(tenant_id, operation="get_run")
        if self.is_remote:
            try:
                payload = await self._remote_request(
                    "GET", f"runs/{run_id}", tenant_id=tenant, run_id=run_id
                )
            except RunNotFoundError:
                return None
            return RunResult.model_validate(payload)
        assert self._runtime is not None
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
        if self.is_remote:
            params = {
                key: value
                for key, value in {
                    "workflow_type": workflow_type,
                    "status": status,
                }.items()
                if value is not None
            }
            payload = await self._remote_request(
                "GET", "runs", tenant_id=tenant, params=params
            )
            raw_runs = payload.get("runs", payload) if isinstance(payload, dict) else payload
            return [RunSummary.model_validate(item) for item in raw_runs]
        assert self._runtime is not None
        return await self._runtime.list_runs(tenant, workflow_type=workflow_type, status=status)

    async def cancel_run(self, run_id: str, *, tenant_id: str | None = None) -> RunResult:
        """Cancel a run belonging to the resolved tenant."""
        tenant = self._resolve_tenant(tenant_id, operation="cancel_run")
        if self.is_remote:
            return RunResult.model_validate(
                await self._remote_request(
                    "POST", f"runs/{run_id}/cancel", tenant_id=tenant, run_id=run_id
                )
            )
        assert self._runtime is not None
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
        if self.is_remote:
            return RunResult.model_validate(
                await self._remote_request(
                    "POST",
                    f"runs/{run_id}/resume",
                    tenant_id=tenant,
                    json=resume.model_dump(mode="json"),
                    run_id=run_id,
                )
            )
        assert self._runtime is not None
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
            result = await self.get_run(run_id, tenant_id=tenant)
            if result is None:
                raise RunNotFoundError(run_id)
            if result.status not in _ACTIVE_STATUSES:
                return result
            if loop.time() >= deadline:
                raise SDKTimeoutError(run_id, timeout_seconds)
            await asyncio.sleep(interval)


class RemoteAgentRuntimeClient(AgentRuntimeClient):
    """Named convenience wrapper for the HTTP-backed runtime client."""

    def __init__(
        self,
        base_url: str,
        *,
        default_tenant_id: str | None = None,
        poll_interval: float = 0.05,
        http_client: httpx.AsyncClient | None = None,
        auth_token: str | None = None,
        timeout_seconds: float = 30.0,
    ) -> None:
        super().__init__(
            None,
            default_tenant_id=default_tenant_id,
            poll_interval=poll_interval,
            base_url=base_url,
            http_client=http_client,
            auth_token=auth_token,
            timeout_seconds=timeout_seconds,
        )
