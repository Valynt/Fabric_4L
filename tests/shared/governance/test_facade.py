"""Tests for the fail-closed PolicyDecisionFacade.

Covers the enforcement contract:
- Whitespace-only tenant IDs are rejected.
- Non-tool actions are denied unless explicitly authorized.
- Tool actions are denied when no ABOM is present.
- Missing action/tenant are denied.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, Mock

import pytest

from tests.shared.governance.builders import make_abom
from value_fabric.shared.governance.decision import DecisionEffect
from value_fabric.shared.governance.facade import PolicyDecisionFacade
from value_fabric.shared.governance.policy_engine import PolicyDecision


@pytest.mark.asyncio
async def test_rejects_whitespace_only_tenant_id() -> None:
    """Whitespace-only tenant IDs must not satisfy tenant validation."""
    facade = PolicyDecisionFacade(allowed_actions={"memory.query"})
    decision = await facade.evaluate_action(
        action="memory.query",
        resource="memory",
        tenant_id="   ",
    )
    assert decision.effect == DecisionEffect.DENY
    assert decision.reason_code == "missing_tenant"


@pytest.mark.asyncio
async def test_denies_non_tool_action_not_in_allowlist() -> None:
    """A non-tool action with no registered authorization must fail closed."""
    facade = PolicyDecisionFacade()
    decision = await facade.evaluate_action(
        action="memory.query",
        resource="memory",
        tenant_id="tenant-123",
    )
    assert decision.effect == DecisionEffect.DENY
    assert decision.reason_code == "action_not_authorized"


@pytest.mark.asyncio
async def test_allows_non_tool_action_in_allowlist() -> None:
    """A non-tool action explicitly registered is allowed through."""
    facade = PolicyDecisionFacade(allowed_actions={"memory.query"})
    decision = await facade.evaluate_action(
        action="memory.query",
        resource="memory",
        tenant_id="tenant-123",
    )
    assert decision.effect == DecisionEffect.ALLOW


@pytest.mark.asyncio
async def test_denies_tool_action_without_abom() -> None:
    """A tool action with no ABOM to evaluate against must fail closed."""
    facade = PolicyDecisionFacade(allowed_actions={"memory.query"})
    decision = await facade.evaluate_action(
        action="memory.query",
        resource="memory",
        tenant_id="tenant-123",
        tool_name="some_tool",
    )
    assert decision.effect == DecisionEffect.DENY
    assert decision.reason_code == "missing_abom"


@pytest.mark.asyncio
async def test_denies_missing_action() -> None:
    """An empty action identifier must be denied."""
    facade = PolicyDecisionFacade()
    decision = await facade.evaluate_action(
        action="",
        resource="memory",
        tenant_id="tenant-123",
    )
    assert decision.effect == DecisionEffect.DENY
    assert decision.reason_code == "missing_action"


@pytest.mark.asyncio
async def test_denies_missing_tenant() -> None:
    """A missing tenant context must be denied."""
    facade = PolicyDecisionFacade(allowed_actions={"memory.query"})
    decision = await facade.evaluate_action(
        action="memory.query",
        resource="memory",
        tenant_id=None,
    )
    assert decision.effect == DecisionEffect.DENY
    assert decision.reason_code == "missing_tenant"


@pytest.mark.asyncio
async def test_tool_allow_preserves_opa_obligations_and_bundle_hash() -> None:
    """A tool-action ALLOW must carry OPA allow-side obligations and hash."""
    abom = make_abom()
    policy_client = Mock()
    policy_client.evaluate = AsyncMock(
        return_value=PolicyDecision(
            allowed=True,
            obligations=["MASK", "RATE"],
            policy_bundle_hash="bundle-abc123",
        )
    )

    facade = PolicyDecisionFacade(policy_client=policy_client, abom=abom)

    decision = await facade.evaluate_action(
        action="tool.call",
        resource="tool",
        tenant_id="tenant-123",
        tool_name="some_tool",
        input_data={"q": "x"},
    )

    assert decision.effect == DecisionEffect.ALLOW
    assert decision.obligations == ["MASK", "RATE"]
    assert decision.policy_bundle_hash == "bundle-abc123"


@pytest.mark.asyncio
async def test_tool_allow_defaults_obligation_to_audit_when_opa_returns_none() -> None:
    """An ALLOW with no OPA obligations must still default to AUDIT."""
    abom = make_abom()
    policy_client = Mock()
    policy_client.evaluate = AsyncMock(
        return_value=PolicyDecision(allowed=True, obligations=[], policy_bundle_hash=None)
    )

    facade = PolicyDecisionFacade(policy_client=policy_client, abom=abom)

    decision = await facade.evaluate_action(
        action="tool.call",
        resource="tool",
        tenant_id="tenant-123",
        tool_name="some_tool",
    )

    assert decision.effect == DecisionEffect.ALLOW
    assert decision.obligations == ["AUDIT"]
    assert decision.policy_bundle_hash == abom.manifest_hash()


@pytest.mark.asyncio
async def test_tool_deny_preserves_opa_obligations_and_bundle_hash() -> None:
    """A tool-action DENY must carry OPA deny-side obligations and hash."""
    abom = make_abom()
    policy_client = Mock()
    policy_client.evaluate = AsyncMock(
        return_value=PolicyDecision(
            allowed=False,
            reason="OPA denied",
            obligations=["manual_review"],
            policy_bundle_hash="bundle-denied-xyz",
        )
    )

    facade = PolicyDecisionFacade(policy_client=policy_client, abom=abom)

    decision = await facade.evaluate_action(
        action="tool.call",
        resource="tool",
        tenant_id="tenant-123",
        tool_name="some_tool",
        input_data={"q": "x"},
    )

    assert decision.effect == DecisionEffect.DENY
    assert decision.reason_code == "policy_denied"
    assert decision.obligations == ["manual_review"]
    assert decision.policy_bundle_hash == "bundle-denied-xyz"
