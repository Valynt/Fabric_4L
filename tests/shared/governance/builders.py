"""Shared test-data builders for the governance test suite.

These consolidate the ABOM, ToolRegistry, and policy-client constructions that
were previously duplicated across the governance test modules so that a change
to any collaborator's constructor is made in exactly one place.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from value_fabric.shared.governance.abom import ABOMInvariants, AgentBillOfMaterials
from value_fabric.shared.governance.policy_engine import PolicyDecision


def make_abom(**overrides) -> AgentBillOfMaterials:
    """Create a test ABOM with sensible defaults, overridable per-test."""
    defaults = {
        "agent_type": "TestAgent",
        "agent_id": "TestAgent-abcd1234",
        "privilege_tier": "standard",
        "allowed_tools": ["tool_a", "tool_b", "tool_c"],
        "denied_tools": [],
        "invariants": ABOMInvariants(
            max_tool_calls_per_run=5,
            budget_limit_usd=10.0,
        ),
    }
    defaults.update(overrides)
    return AgentBillOfMaterials(**defaults)


def make_mock_registry() -> MagicMock:
    """Create a mock ToolRegistry whose ``execute()`` succeeds."""
    registry = MagicMock()
    registry.execute = AsyncMock(return_value={"status": "ok"})
    return registry


def make_allowing_policy_client(abom: AgentBillOfMaterials) -> MagicMock:
    """Create a policy client whose ``evaluate()`` returns an ALLOW decision."""
    policy_client = MagicMock()
    policy_client.evaluate = AsyncMock(
        return_value=PolicyDecision(
            allowed=True,
            reason="allow",
            obligations=[],
            policy_bundle_hash=abom.manifest_hash(),
        )
    )
    return policy_client


__all__ = ["make_abom", "make_mock_registry", "make_allowing_policy_client"]
