"""OPA Policy Engine client for GATE framework.

Provides async HTTP integration with Open Policy Agent (OPA) for
tool-invocation authorization decisions.  Falls back to local
evaluation when OPA is unavailable.

GATE Framework §2.2 — PolicyEngineClient
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Any

from value_fabric.shared.crypto.canonical import canonical_hash

from .abom import AgentBillOfMaterials

logger = logging.getLogger(__name__)


@dataclass
class PolicyDecision:
    """Result of a policy evaluation."""

    allowed: bool
    reason: str | None = None
    obligations: list[str] = field(default_factory=list)
    policy_bundle_hash: str | None = None


class PolicyEngineClient:
    """Async client for OPA policy evaluation.

    Evaluates tool-invocation requests against the agent's ABOM and
    the deployed Rego policy bundle.  When OPA is unreachable, falls
    back to ``_evaluate_local()`` which enforces ABOM allow/deny lists
    and applies deny-all for ``high_privilege`` agents.

    Args:
        opa_url: OPA server URL (default: ``OPA_URL`` env var).
        timeout: HTTP timeout in seconds.
    """

    def __init__(
        self,
        opa_url: str | None = None,
        timeout: int = 3,
    ) -> None:
        self._opa_url = opa_url or os.getenv("OPA_URL", "http://localhost:8181")
        self._timeout = timeout

    async def evaluate(
        self,
        abom: AgentBillOfMaterials,
        tool_name: str,
        input_data: dict[str, Any],
        tenant_id: str | None = None,
    ) -> PolicyDecision:
        """Evaluate a tool invocation against OPA policy.

        Args:
            abom: Agent's ABOM manifest.
            tool_name: Name of the tool being invoked.
            input_data: Tool input parameters.
            tenant_id: Tenant context for multi-tenant policies.

        Returns:
            PolicyDecision with allowed/denied status and obligations.
        """
        opa_input = {
            "agent_type": abom.agent_type,
            "agent_id": abom.agent_id,
            "privilege_tier": abom.privilege_tier,
            "tool_name": tool_name,
            "allowed_tools": abom.allowed_tools,
            "denied_tools": abom.denied_tools,
            "invariants": abom.invariants.model_dump(),
            "tenant_id": tenant_id,
            "input_hash": canonical_hash(input_data),
        }

        try:
            return await self._evaluate_opa(opa_input)
        except Exception as e:
            logger.warning("OPA unavailable (%s), falling back to local evaluation", e)
            return self._evaluate_local(abom, tool_name)

    async def _evaluate_opa(self, opa_input: dict[str, Any]) -> PolicyDecision:
        """Send evaluation request to OPA server."""
        import httpx

        url = f"{self._opa_url}/v1/data/gate/tool_access"
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            response = await client.post(url, json={"input": opa_input})
            response.raise_for_status()

        result = response.json().get("result", {})
        return PolicyDecision(
            allowed=result.get("allow", False),
            reason=result.get("reason"),
            obligations=result.get("obligations", []),
            policy_bundle_hash=result.get("bundle_hash"),
        )

    @staticmethod
    def _evaluate_local(
        abom: AgentBillOfMaterials,
        tool_name: str,
    ) -> PolicyDecision:
        """Local fallback evaluation using ABOM allow/deny lists.

        CRITICAL: When OPA is unavailable, high_privilege agents are
        denied ALL tool access to prevent privilege escalation without
        policy enforcement.  Standard and elevated agents fall back to
        ABOM-only evaluation.
        """
        # Deny-all for high_privilege when OPA is down
        if abom.privilege_tier == "high_privilege":
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"OPA unavailable: deny-all for high_privilege agent "
                    f"'{abom.agent_type}' — tool '{tool_name}' blocked"
                ),
            )

        if tool_name in abom.denied_tools:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_name}' is in denied_tools for {abom.agent_type}",
            )

        if tool_name not in abom.allowed_tools:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_name}' is not in allowed_tools for {abom.agent_type}",
            )

        return PolicyDecision(
            allowed=True,
            reason="Local ABOM evaluation: tool allowed (OPA fallback)",
            obligations=[],
        )
