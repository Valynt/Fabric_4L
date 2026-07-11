from __future__ import annotations

"""OSS-0 tests for legacy-backed ports used by future substitution pilots."""


from datetime import UTC, datetime

import pytest

from layer4_agents.adapters.task_execution import (
    LegacyTaskExecutionAdapter,
    as_task_execution_port,
)
from layer4_agents.engine.ports import TaskExecutionPort
from layer4_agents.engine.scheduler import TaskScheduler
from layer4_agents.engine.types import ScheduledTask, TaskPriority
from layer4_agents.resilience import CircuitBreaker, TenantRateLimiter
from layer4_agents.resilience_ports import (
    DependencyCircuitBreakerPort,
    LegacyCircuitBreakerAdapter,
    LegacyTenantRateLimitAdapter,
    TenantRateLimitPort,
    as_dependency_circuit_breaker_port,
    as_tenant_rate_limit_port,
)


def _task(task_id: str = "port-task", tenant_id: str = "tenant-port") -> ScheduledTask:
    return ScheduledTask(
        priority=TaskPriority.NORMAL.value,
        scheduled_time=datetime.now(UTC),
        task_id=task_id,
        workflow_instance_id="wf-port",
        capability="capability",
        agent_type="Agent",
        tenant_id=tenant_id,
        context={"tenant_id": tenant_id},
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_tenant_rate_limit_port_delegates_to_legacy_limiter() -> None:
    limiter = TenantRateLimiter()
    adapter = LegacyTenantRateLimitAdapter(limiter)

    assert isinstance(adapter, TenantRateLimitPort)
    assert await adapter.check_rate_limit("tenant-a") is True
    assert adapter.get_bucket_state("tenant-a") is not None
    assert await adapter.get_retry_after("tenant-a") >= 0
    assert isinstance(as_tenant_rate_limit_port(limiter), LegacyTenantRateLimitAdapter)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_dependency_circuit_breaker_port_delegates_call_and_state() -> None:
    breaker = CircuitBreaker("service-a", failure_threshold=2, recovery_timeout=10)
    adapter = LegacyCircuitBreakerAdapter(breaker)

    async def dependency(value: str) -> dict[str, str]:
        return {"value": value}

    assert isinstance(adapter, DependencyCircuitBreakerPort)
    assert await adapter.call(dependency, "ok") == {"value": "ok"}
    assert adapter.get_state()["service"] == "service-a"
    assert isinstance(as_dependency_circuit_breaker_port(breaker), LegacyCircuitBreakerAdapter)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_execution_port_delegates_scheduler_status_contract() -> None:
    scheduler = TaskScheduler()
    adapter = LegacyTaskExecutionAdapter(scheduler)
    task = _task()

    assert isinstance(adapter, TaskExecutionPort)
    assert await adapter.submit(task) == "port-task"

    pending = await adapter.list_pending(tenant_id="tenant-port")
    assert [item["task_id"] for item in pending] == ["port-task"]

    status = await adapter.get_status("port-task")
    assert status is not None
    assert status["tenant_id"] == "tenant-port"

    assert await adapter.list_running() == []
    assert adapter.get_stats()["pending_tasks"] == 1
    assert await adapter.cancel("port-task") is True
    assert isinstance(as_task_execution_port(scheduler), LegacyTaskExecutionAdapter)


@pytest.mark.unit
@pytest.mark.asyncio
async def test_task_execution_port_preserves_capability_filtering() -> None:
    scheduler = TaskScheduler()
    adapter = as_task_execution_port(scheduler)
    first = _task(task_id="first")
    second = _task(task_id="second")
    second.capability = "other_capability"

    await adapter.submit(first)
    await adapter.submit(second)

    filtered = await adapter.list_pending(capability="capability")

    assert [item["task_id"] for item in filtered] == ["first"]
