from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock
from uuid import UUID

import pytest
from value_fabric.shared.audit import models as audit_models

import layer4_agents.tenants.usage as module
from layer4_agents.tenants.usage import UsageMetrics, UsageTrackingService

TENANT = UUID("550e8400-e29b-41d4-a716-446655440000")


@pytest.mark.asyncio
async def test_usage_events_preserve_tenant_and_safe_details(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    emit = AsyncMock()
    monkeypatch.setattr("value_fabric.shared.audit.emit_audit_event", emit)
    service = UsageTrackingService(SimpleNamespace())

    await service.record_api_call(TENANT, "/v1/workflows", 201, 15)
    await service.record_llm_usage(TENANT, "model", 10, 5, 20)
    await service.record_agent_execution(TENANT, "business_case", 30, False)

    assert emit.await_count == 3
    for call in emit.await_args_list:
        assert call.kwargs["tenant_id"] == TENANT
        assert call.kwargs["actor_type"] == "system"
    assert emit.await_args_list[0].kwargs["details"]["status_code"] == 201
    assert emit.await_args_list[1].kwargs["details"]["tokens_output"] == 5
    assert emit.await_args_list[2].kwargs["outcome"] == audit_models.AuditOutcome.FAILURE


@pytest.mark.asyncio
async def test_usage_event_transport_failure_is_non_fatal(monkeypatch: pytest.MonkeyPatch) -> None:
    emit = AsyncMock(side_effect=RuntimeError("audit unavailable"))
    monkeypatch.setattr("value_fabric.shared.audit.emit_audit_event", emit)
    service = UsageTrackingService(SimpleNamespace())
    await service.record_api_call(TENANT, "/health", 200, 1)
    await service.record_llm_usage(TENANT, "model", 1, 1, 1)
    await service.record_agent_execution(TENANT, "agent", 1, True)


class Result:
    def all(self):
        return [
            SimpleNamespace(action=audit_models.AuditAction.API_CALL.value, count=8),
            SimpleNamespace(action=audit_models.AuditAction.AGENT_EXECUTION.value, count=3),
            SimpleNamespace(action=audit_models.AuditAction.LLM_USAGE.value, count=2),
        ]


@pytest.mark.asyncio
async def test_usage_summary_aggregates_tenant_scoped_counts() -> None:
    db = SimpleNamespace(execute=AsyncMock(return_value=Result()))
    service = UsageTrackingService(db)
    summary = await service.get_usage_summary(TENANT, days=7)
    assert (summary.api_calls_total, summary.agent_executions, summary.llm_requests) == (8, 3, 2)
    statement, parameters = db.execute.await_args.args
    assert "WHERE tenant_id = :tenant_id" in str(statement)
    assert parameters["tenant_id"] == str(TENANT)

    current = await service.get_current_month_usage(TENANT)
    assert current["api_calls"] == 8
    assert current["agent_executions"] == 3
    assert current["period"] == "current_month"


@pytest.mark.asyncio
async def test_usage_summary_validates_window_and_fails_safe_on_query_error() -> None:
    service = UsageTrackingService(
        SimpleNamespace(execute=AsyncMock(side_effect=RuntimeError("db")))
    )
    with pytest.raises(ValueError, match="between 1 and 365"):
        await service.get_usage_summary(TENANT, days=0)
    with pytest.raises(ValueError, match="between 1 and 365"):
        await service.get_usage_summary(TENANT, days=366)
    summary = await service.get_usage_summary(TENANT)
    assert isinstance(summary, UsageMetrics)
    assert summary.api_calls_total == summary.agent_executions == summary.llm_requests == 0


@pytest.mark.asyncio
async def test_usage_convenience_functions_delegate(monkeypatch: pytest.MonkeyPatch) -> None:
    service = SimpleNamespace(
        record_api_call=AsyncMock(),
        record_llm_usage=AsyncMock(),
        record_agent_execution=AsyncMock(),
    )

    class Context:
        async def __aenter__(self):
            return service

        async def __aexit__(self, *_args):
            return False

    monkeypatch.setattr(module, "UsageTrackingService", Context)
    await module.record_api_call(TENANT, "/v1", 200, 1)
    await module.record_llm_usage(TENANT, "model", 2, 3, 4)
    await module.record_agent_execution(TENANT, "agent", 5, True)
    service.record_api_call.assert_awaited_once_with(TENANT, "/v1", 200, 1)
    service.record_llm_usage.assert_awaited_once_with(TENANT, "model", 2, 3, 4)
    service.record_agent_execution.assert_awaited_once_with(TENANT, "agent", 5, True)
