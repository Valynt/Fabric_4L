from __future__ import annotations

"""Focused Layer 4 agent tenant-isolation tests."""


from typing import Any
from uuid import UUID

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel
from value_fabric.shared.error_handling import register_exception_handlers

from layer4_agents.api.routes import agent_stream
from layer4_agents.services.conversation import (
    ConversationService,
    ConversationTenantValidationError,
)
from layer4_agents.tools.registry import TenantAwareTool, ToolResult
from value_fabric.shared.identity.context import RequestContext, RequestContextManager
from value_fabric.shared.identity.dependencies import require_authenticated
from sqlalchemy.ext.asyncio import AsyncSession
from unittest.mock import AsyncMock


@pytest.fixture
def app() -> FastAPI:
    app = FastAPI()
    register_exception_handlers(app)
    app.include_router(agent_stream.router, prefix="/v1")
    
    # Mock database dependency to avoid PostgreSQL connection
    async def mock_get_db():
        return AsyncMock(spec=AsyncSession)
    
    app.dependency_overrides[agent_stream.get_route_db] = mock_get_db
    return app


class CapturingService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def handle_message(self, **kwargs: Any) -> dict[str, Any]:
        self.calls.append(kwargs)
        return {
            "content": "tenant scoped response",
            "metadata": {
                "trace_id": kwargs["trace_id"],
                "workflow_id": "wf-tenant",
                "tenant_id": kwargs["tenant_id"],
                "tool_name": "valuepilot_conversation",
                "audit_event_id": "audit-tenant",
                "emitted_at": "2026-05-05T00:00:00+00:00",
                "intent": "general_question",
                "confidence": 0.5,
                "workflow_triggered": False,
            },
        }


@pytest.mark.asyncio
async def test_agent_missing_tenant_context_fails_closed(app: FastAPI) -> None:
    async def missing_tenant_context() -> RequestContext:
        return RequestContext(user_id="user-without-tenant")

    app.dependency_overrides[require_authenticated] = missing_tenant_context

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/agent-stream/chat",
            json={
                "messages": [{"role": "user", "content": "Summarize evidence."}],
                "activeTab": "evidence",
            },
        )

    assert response.status_code == 422
    assert "tenant context" in response.json()["error"]["message"].lower()


@pytest.mark.asyncio
async def test_agent_malformed_tenant_context_fails_closed() -> None:
    class Input(BaseModel):
        value: int

    class Tool(TenantAwareTool):
        name = "tenant_required_tool"
        input_schema = Input
        output_schema = BaseModel

        async def execute(self, input_data: Input) -> dict[str, Any]:
            return {"tenant_id": self.get_tenant_id()}

    result = await Tool(config={"tenant_id": ""}).run({"value": 1})

    assert result.status == "error"
    assert result.error["code"] == "TENANT_CONTEXT_MISSING"
    assert "requires tenant context" in result.error["message"]


@pytest.mark.asyncio
async def test_forged_tenant_header_cannot_override_validated_context(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CapturingService()
    validated_tenant = UUID("12345678-1234-1234-1234-123456789abc")

    async def valid_context() -> RequestContext:
        return RequestContext(tenant_id=validated_tenant, user_id="user-a")

    app.dependency_overrides[require_authenticated] = valid_context
    monkeypatch.setattr(agent_stream, "_get_conversation_service", lambda **kwargs: service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/agent-stream/chat",
            headers={"X-Tenant-ID": "00000000-0000-0000-0000-000000000999"},
            json={
                "messages": [{"role": "user", "content": "Summarize evidence."}],
                "activeTab": "evidence",
                "account": {"accountId": "account-a", "accountName": "Acme"},
            },
        )

    assert response.status_code == 200, response.text
    assert service.calls[0]["tenant_id"] == str(validated_tenant)
    assert response.json()["metadata"]["tenant_id"] == str(validated_tenant)


@pytest.mark.asyncio
async def test_agent_stream_passes_entity_context_to_conversation_service(
    app: FastAPI,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = CapturingService()
    validated_tenant = UUID("12345678-1234-1234-1234-123456789abc")

    async def valid_context() -> RequestContext:
        return RequestContext(tenant_id=validated_tenant, user_id="user-a")

    app.dependency_overrides[require_authenticated] = valid_context
    monkeypatch.setattr(agent_stream, "_get_conversation_service", lambda **kwargs: service)

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.post(
            "/v1/agent-stream/chat",
            json={
                "messages": [{"role": "user", "content": "What changed?"}],
                "activeTab": "roi",
                "account": {"accountId": "account-a", "accountName": "Acme"},
                "selectedSignalId": "signal-a",
                "entityContext": {
                    "workspaceCaseId": "case-a",
                    "selectedDriverId": "driver-a",
                    "valueCaseId": "value-case-a",
                },
            },
        )

    assert response.status_code == 200, response.text
    entity_context = service.calls[0]["entity_context"]
    assert entity_context["accountId"] == "account-a"
    assert entity_context["activeTab"] == "roi"
    assert entity_context["selectedSignalId"] == "signal-a"
    assert entity_context["selectedDriverId"] == "driver-a"
    assert entity_context["workspaceCaseId"] == "case-a"
    assert entity_context["valueCaseId"] == "value-case-a"


@pytest.mark.asyncio
async def test_agent_tool_receives_validated_tenant_context() -> None:
    class Input(BaseModel):
        value: int

    class Tool(TenantAwareTool):
        name = "tenant_context_echo"
        input_schema = Input
        output_schema = BaseModel

        async def execute(self, input_data: Input) -> dict[str, Any]:
            return {"tenant_id": self.get_tenant_id(), "value": input_data.value}

    result = await Tool(config={"tenant_id": "tenant-a"}).run(
        {"value": 7, "trace_id": "trace-tenant"}
    )

    assert isinstance(result, ToolResult)
    assert result.status == "success"
    assert result.data["tenant_id"] == "tenant-a"
    assert result.metadata["tenant_id"] == "tenant-a"


@pytest.mark.asyncio
async def test_agent_retrieval_excludes_foreign_tenant_evidence() -> None:
    service = ConversationService(
        conversation_agent=None,
    )
    result = await service._generate_response(
        user_message="Cite evidence for this value claim.",
        messages=[{"role": "user", "content": "Cite evidence for this value claim."}],
        active_tab="evidence",
        intent="value_analysis",
        context_data={
            "tenant_id": "tenant-a",
            "evidence_records": [
                {"id": "ev-a", "tenant_id": "tenant-a"},
                {"id": "ev-b", "tenant_id": "tenant-b"},
            ],
        },
        workflow_result=None,
        account_name="Acme",
        gate_context={},
        tenant_id="tenant-a",
    )

    assert "ev-a" in result
    assert "ev-b" not in result


@pytest.mark.asyncio
async def test_agent_output_contains_no_foreign_tenant_data() -> None:
    service = ConversationService()
    result = await service._generate_response(
        user_message="Cite evidence for this value claim.",
        messages=[{"role": "user", "content": "Cite evidence for this value claim."}],
        active_tab="evidence",
        intent="value_analysis",
        context_data={
            "tenant_id": "tenant-a",
            "evidence_records": [
                {"id": "foreign-account-secret", "tenant_id": "tenant-b"},
            ],
        },
        workflow_result=None,
        account_name="Acme",
        gate_context={},
        tenant_id="tenant-a",
    )

    assert "foreign-account-secret" not in result
    assert "cannot present it as verified" in result.lower()


@pytest.mark.asyncio
async def test_conversation_service_fails_closed_on_blank_tenant() -> None:
    with pytest.raises(ConversationTenantValidationError):
        await ConversationService().handle_message(
            user_message="Summarize this account.",
            messages=[{"role": "user", "content": "Summarize this account."}],
            active_tab="evidence",
            account_id="account-a",
            account_name="Acme",
            tenant_id="",
            trace_id="trace-blank-tenant",
        )


@pytest.mark.asyncio
async def test_mutation_tool_rejects_empty_tenant_id() -> None:
    class StubToolRegistry:
        async def promote_signal(self, **kwargs: Any) -> dict[str, Any]:
            raise AssertionError("tool should not execute when tenant_id is blank")

    service = ConversationService(tool_registry=StubToolRegistry())

    with pytest.raises(ConversationTenantValidationError):
        await service._generate_response(
            user_message="Promote this signal.",
            messages=[{"role": "user", "content": "Promote this signal."}],
            active_tab="signals",
            intent="promote_signal",
            context_data={"account": {"id": "account-a"}},
            workflow_result=None,
            account_name="Acme",
            gate_context={},
            tenant_id="   ",
            entities={"signal_id": "signal-a"},
        )
