"""Agent builder helpers for the Agent Runtime Python SDK."""

from __future__ import annotations

from typing import Any

from ..models import RunEnvelope, RunResult
from .client import AgentRuntimeClient
from .types import AgentSpec

__all__ = ["Agent", "create_agent"]


class Agent:
    """Bound agent handle: submits a workflow run and optionally waits on it."""

    def __init__(self, spec: AgentSpec, client: AgentRuntimeClient) -> None:
        self._spec = spec
        self._client = client

    @property
    def name(self) -> str:
        return self._spec.name

    @property
    def workflow_type(self) -> str:
        return self._spec.workflow_type

    def _resolve_tenant(self, tenant_id: str | None) -> str | None:
        return tenant_id or self._spec.default_tenant_id

    async def run(
        self,
        input_data: dict[str, Any] | None = None,
        *,
        tenant_id: str | None = None,
        wait: bool = True,
        timeout_seconds: float = 30.0,
        trace_id: str | None = None,
        user_id: str | None = None,
        metadata: dict[str, Any] | None = None,
    ) -> RunEnvelope | RunResult:
        """Submit the agent's workflow; when ``wait`` is true also await the result."""
        merged_metadata = {**(self._spec.metadata or {}), **(metadata or {})}
        tenant = self._resolve_tenant(tenant_id)
        envelope = await self._client.submit_run(
            self._spec.workflow_type,
            input_data=input_data,
            tenant_id=tenant,
            priority=self._spec.default_priority,
            metadata=merged_metadata,
            trace_id=trace_id,
            user_id=user_id,
        )
        if not wait:
            return envelope
        return await self._client.wait_for_run(
            envelope.run_id,
            tenant_id=tenant,
            timeout_seconds=timeout_seconds,
        )

    async def resume(
        self,
        run_id: str,
        *,
        tenant_id: str | None = None,
        resume_data: dict[str, Any] | None = None,
        checkpoint_id: str | None = None,
        checkpoint_hash: str | None = None,
    ) -> RunResult:
        """Resume a previously paused run for the agent's workflow."""
        return await self._client.resume_run(
            run_id,
            tenant_id=self._resolve_tenant(tenant_id),
            resume_data=resume_data,
            checkpoint_id=checkpoint_id,
            checkpoint_hash=checkpoint_hash,
        )


def create_agent(
    client: AgentRuntimeClient,
    *,
    name: str,
    workflow_type: str,
    description: str = "",
    tools: tuple[str, ...] = (),
    default_tenant_id: str | None = None,
    default_priority: int = 3,
    metadata: dict[str, Any] | None = None,
) -> Agent:
    """Build an ``Agent`` bound to ``client`` from explicit fields."""
    spec = AgentSpec(
        name=name,
        workflow_type=workflow_type,
        description=description,
        tools=tools,
        default_tenant_id=default_tenant_id,
        default_priority=default_priority,
        metadata=metadata or {},
    )
    return Agent(spec, client)
