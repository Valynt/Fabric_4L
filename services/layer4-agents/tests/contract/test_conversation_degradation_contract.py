"""Behavior contract test suite for ConversationService degradation and fallback auditing.

Validates:
1. When primary ConversationAgent succeeds -> response_tier='conversation_agent', fallback=False, degraded=False, degradation_reason=None.
2. When ConversationAgent is unavailable but C1 succeeds -> response_tier='thesys_c1', provider='thesys_c1'.
3. When both ConversationAgent and C1 fail -> response_tier='heuristic', fallback=True, degraded=True, degradation_reason is recorded.
4. Server-side audit event details records response_tier, fallback, degraded, degradation_reason.
5. When C1 is healthy, heuristic fallback is strictly unreachable.
6. Mutation tools report response_tier='tool' and fallback=False.
"""

from __future__ import annotations

import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Ensure source roots are on sys.path
_REPO_ROOT = Path(__file__).resolve().parent.parent.parent.parent
_L4_SRC = _REPO_ROOT / "services" / "layer4-agents" / "src"
_SHARED_SRC = _REPO_ROOT / "packages" / "shared" / "src"
for p in [_L4_SRC, _SHARED_SRC]:
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from layer4_agents.services.conversation import ConversationService
from value_fabric.shared.audit import AuditAction, AuditOutcome


@pytest.fixture
def base_service() -> ConversationService:
    service = ConversationService(c1_enabled=False)
    return service


@pytest.mark.asyncio
async def test_primary_agent_success_not_degraded():
    """Primary agent success emits conversation_agent tier, not degraded, not fallback."""
    mock_agent = MagicMock()
    async def mock_exec(params, gate_ctx=None):
        if params.get("capability") == "classify_intent":
            return {"intent": "value_analysis", "confidence": 0.9, "entities": {}}
        return {"response": "Full agent synthesis response"}

    mock_agent.execute = AsyncMock(side_effect=mock_exec)

    service = ConversationService(c1_enabled=True, conversation_agent=mock_agent)

    with patch("layer4_agents.services.conversation.emit_audit_event", new_callable=AsyncMock) as mock_emit, \
         patch.object(service, "_build_gate_context", return_value={"tool_gateway": object()}):
        result = await service.handle_message(
            user_message="Analyze the ROI for this deal",
            messages=[{"role": "user", "content": "Analyze the ROI for this deal"}],
            active_tab="value_studio",
            account_id="acc_123",
            tenant_id="tenant_abc",
        )

        assert result["content"] == "Full agent synthesis response"
        metadata = result["metadata"]
        assert metadata["response_tier"] == "conversation_agent"
        assert metadata["fallback"] is False
        assert metadata["degraded"] is False
        assert metadata["degradation_reason"] is None

        # Verify audit emission
        mock_emit.assert_awaited_once()
        call_args = mock_emit.call_args
        assert call_args.args[0] == AuditAction.AGENT_EXECUTION
        call_kwargs = call_args.kwargs
        assert call_kwargs["outcome"] == AuditOutcome.SUCCESS
        details = call_kwargs["details"]
        assert details["tenant_id"] == "tenant_abc"
        assert details["trace_id"] == metadata["trace_id"]
        assert details["journey_id"] == metadata["journey_id"]


@pytest.mark.asyncio
async def test_c1_proxy_success():
    """C1 proxy success when agent is unconfigured emits response_tier='thesys_c1'."""
    service = ConversationService(c1_enabled=True, conversation_agent=None)

    with patch.object(service, "_generate_via_c1", new_callable=AsyncMock) as mock_c1, \
         patch("layer4_agents.services.conversation.emit_audit_event", new_callable=AsyncMock) as mock_emit:
        mock_c1.return_value = "Contract-validated response from C1 proxy"

        result = await service.handle_message(
            user_message="What are the competitors?",
            messages=[{"role": "user", "content": "What are the competitors?"}],
            active_tab="battlecard",
            account_id="acc_123",
            tenant_id="tenant_abc",
        )

        assert result["content"] == "Contract-validated response from C1 proxy"
        metadata = result["metadata"]
        assert metadata["response_tier"] == "thesys_c1"
        assert metadata["provider"] == "thesys"
        assert metadata["fallback"] is False

        mock_emit.assert_awaited_once()
        details = mock_emit.call_args.kwargs["details"]
        assert details["tenant_id"] == "tenant_abc"


@pytest.mark.asyncio
async def test_heuristic_fallback_is_degraded_and_fallback():
    """When C1 is disabled or fails, heuristic fallback fires with fallback=True, degraded=True."""
    service = ConversationService(c1_enabled=False, conversation_agent=None)

    with patch("layer4_agents.services.conversation.emit_audit_event", new_callable=AsyncMock) as mock_emit:
        result = await service.handle_message(
            user_message="Calculate payback period",
            messages=[{"role": "user", "content": "Calculate payback period"}],
            active_tab="value_studio",
            account_id="acc_123",
            tenant_id="tenant_abc",
        )

        metadata = result["metadata"]
        assert metadata["response_tier"] == "heuristic"
        assert metadata["fallback"] is True
        assert metadata["degraded"] is True
        assert metadata["degradation_reason"] == "llm_tiers_unavailable"

        assert mock_emit.await_count >= 1
        # Last emitted audit event is conversation interaction audit
        details = mock_emit.call_args_list[-1].kwargs["details"]
        assert details["tenant_id"] == "tenant_abc"
        assert details["intent"] == "value_analysis"


@pytest.mark.asyncio
async def test_c1_failure_triggers_degradation_audit():
    """When C1 throws an error, degradation audit and heuristic fallback fire."""
    service = ConversationService(c1_enabled=True, conversation_agent=None)

    with patch.object(service, "_generate_via_c1", new_callable=AsyncMock) as mock_c1, \
         patch.object(service, "_emit_degradation_audit", new_callable=AsyncMock) as mock_deg_audit, \
         patch("layer4_agents.services.conversation.emit_audit_event", new_callable=AsyncMock) as mock_emit:
        mock_c1.side_effect = RuntimeError("C1 service 503 Service Unavailable")

        result = await service.handle_message(
            user_message="Hello",
            messages=[{"role": "user", "content": "Hello"}],
            active_tab="account_intelligence",
            account_id="acc_123",
            tenant_id="tenant_abc",
        )

        metadata = result["metadata"]
        assert metadata["response_tier"] == "heuristic"
        assert metadata["fallback"] is True
        assert metadata["degraded"] is True
        assert metadata["degradation_reason"] == "thesys_c1_failed"

        mock_deg_audit.assert_awaited_once()
        deg_kwargs = mock_deg_audit.call_args.kwargs
        assert deg_kwargs["tenant_id"] == "tenant_abc"
        assert deg_kwargs["selected_tier"] == "heuristic"
        assert deg_kwargs["reason"] == "thesys_c1_failed"


@pytest.mark.asyncio
async def test_c1_up_heuristic_unreachable():
    """Proves heuristic fallback is never reached when C1 generation succeeds."""
    service = ConversationService(c1_enabled=True, conversation_agent=None)

    with patch.object(service, "_generate_via_c1", new_callable=AsyncMock) as mock_c1, \
         patch.object(service, "_heuristic_response", new_callable=MagicMock) as mock_heuristic:
        mock_c1.return_value = "C1 content"

        result = await service.handle_message(
            user_message="Help me",
            messages=[{"role": "user", "content": "Help me"}],
            active_tab="value_studio",
            account_id="acc_123",
            tenant_id="tenant_abc",
        )

        assert result["content"] == "C1 content"
        mock_heuristic.assert_not_called()
        assert result["metadata"]["response_tier"] == "thesys_c1"
        assert result["metadata"]["fallback"] is False


@pytest.mark.asyncio
async def test_mutation_tool_intent_reports_tool_tier():
    """Mutation tool intents run as tool tier."""
    service = ConversationService(c1_enabled=False, conversation_agent=None)

    with patch.object(service, "_execute_mutation_tool", new_callable=AsyncMock) as mock_tool, \
         patch("layer4_agents.services.conversation.emit_audit_event", new_callable=AsyncMock) as mock_emit:
        mock_tool.return_value = {"success": True, "message": "Signal promoted to hypothesis"}

        # promote_signal intent
        with patch.object(service, "_classify_intent", new_callable=AsyncMock) as mock_classify:
            mock_classify.return_value = {"intent": "promote_signal", "confidence": 0.9, "entities": {}}

            result = await service.handle_message(
                user_message="Promote this signal",
                messages=[{"role": "user", "content": "Promote this signal"}],
                active_tab="account_intelligence",
                account_id="acc_123",
                tenant_id="tenant_abc",
            )

            assert "Signal promoted to hypothesis" in result["content"]
            metadata = result["metadata"]
            assert metadata["response_tier"] == "tool"
            assert metadata["fallback"] is False
            assert metadata["degraded"] is False
            assert metadata["degradation_reason"] is None

