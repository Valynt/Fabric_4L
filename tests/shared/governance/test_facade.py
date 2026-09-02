"""Tests for the fail-closed PolicyDecisionFacade.

Covers the enforcement contract:
- Whitespace-only tenant IDs are rejected.
- Non-tool actions are denied unless explicitly authorized.
- Tool actions are denied when no ABOM is present.
- Missing action/tenant are denied.
"""

from __future__ import annotations

import pytest

from value_fabric.shared.governance.decision import DecisionEffect
from value_fabric.shared.governance.facade import PolicyDecisionFacade


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
