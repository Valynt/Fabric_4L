from __future__ import annotations

from unittest.mock import MagicMock

import pytest

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
