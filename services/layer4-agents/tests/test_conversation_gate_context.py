from __future__ import annotations

from unittest.mock import MagicMock

from layer4_agents.services.conversation import ConversationService


def test_build_gate_context_includes_tool_registry_and_tenant() -> None:
    registry = MagicMock()
    service = ConversationService(tool_registry=registry)
    ctx = service._build_gate_context(
        tenant_id="tenant-123",
        trace_id="trace-abc",
        workflow_id="wf-1",
        audit_event_id="audit-1",
    )
    assert ctx["tool_registry"] is registry
    assert ctx["tenant_id"] == "tenant-123"
    assert ctx["trace_id"] == "trace-abc"
    assert ctx["workflow_id"] == "wf-1"
    assert ctx["audit_event_id"] == "audit-1"


def test_build_gate_context_includes_retrieval_engine() -> None:
    registry = MagicMock()
    engine = MagicMock()
    service = ConversationService(tool_registry=registry, retrieval_engine=engine)
    ctx = service._build_gate_context(
        tenant_id="tenant-123",
        trace_id="trace-abc",
        workflow_id="wf-1",
        audit_event_id="audit-1",
    )
    assert ctx["retrieval_engine"] is engine


def test_build_gate_context_omits_optional_ids_when_none() -> None:
    registry = MagicMock()
    service = ConversationService(tool_registry=registry)
    ctx = service._build_gate_context()
    assert "tenant_id" not in ctx
    assert "trace_id" not in ctx
    assert "workflow_id" not in ctx
    assert "audit_event_id" not in ctx
    assert ctx["tool_registry"] is registry


def test_build_gate_context_returns_empty_with_no_deps() -> None:
    service = ConversationService()
    ctx = service._build_gate_context()
    assert ctx == {}
