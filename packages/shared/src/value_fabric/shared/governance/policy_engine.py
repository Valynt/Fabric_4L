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
    """Result of a policy evaluation.

    This is the legacy gateway result retained for compatibility with the
    existing ToolGateway pipeline; the canonical transport-neutral contract is
    ``Decision`` in ``shared.governance.decision``.
    """

    allowed: bool
    reason: str | None = None
    obligations: list[str] = field(default_factory=list)
    policy_bundle_hash: str | None = None
    decision_id: str | None = None
    tenant_id: str | None = None
    actor_id: str | None = None
    action: str | None = None
    resource: str | None = None


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
        if not tool_name or not isinstance(tool_name, str):
            return PolicyDecision(
                allowed=False,
                reason="Tool name is required for policy evaluation.",
                obligations=["AUDIT"],
                policy_bundle_hash=abom.manifest_hash(),
            )
        if not tenant_id or tenant_id in {"unknown", "None", "null", ""}:
            return PolicyDecision(
                allowed=False,
                reason="Tenant context is required for policy evaluation.",
                obligations=["AUDIT"],
                policy_bundle_hash=abom.manifest_hash(),
            )

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
            decision = await self._evaluate_opa(opa_input)
            if not isinstance(decision, PolicyDecision):
                raise ValueError("OPA returned a non-policy decision")
            if decision.reason is None and not decision.allowed:
                decision.reason = "Policy denied by OPA."
            if not decision.policy_bundle_hash:
                decision.policy_bundle_hash = abom.manifest_hash()
            if decision.allowed is False and decision.reason is None:
                decision.reason = "Policy denied."
            return decision
        except Exception as e:
            logger.warning("OPA unavailable (%s): fail-closed deny", e)
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
        """Fail-closed local fallback. OPA outages must deny by default.

        The legacy ABOM-only fallback is intentionally not privileged to permit
        tool execution after an outage; missing or malformed OPA responses always
        result in a deny decision.
        """
        if abom.privilege_tier == "high_privilege":
            return PolicyDecision(
                allowed=False,
                reason=(
                    f"OPA unavailable: deny-all for high_privilege agent "
                    f"'{abom.agent_type}' — tool '{tool_name}' blocked"
                ),
                obligations=["AUDIT"],
                policy_bundle_hash=abom.manifest_hash(),
            )

        if tool_name in abom.denied_tools:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_name}' is in denied_tools for {abom.agent_type}",
                obligations=["AUDIT"],
                policy_bundle_hash=abom.manifest_hash(),
            )

        if tool_name not in abom.allowed_tools:
            return PolicyDecision(
                allowed=False,
                reason=f"Tool '{tool_name}' is not in allowed_tools for {abom.agent_type}",
                obligations=["AUDIT"],
                policy_bundle_hash=abom.manifest_hash(),
            )

        return PolicyDecision(
            allowed=False,
            reason=(
                "OPA unavailable: fail-closed deny for standard agent "
                f"'{abom.agent_type}' while evaluating '{tool_name}'"
            ),
            obligations=["AUDIT"],
            policy_bundle_hash=abom.manifest_hash(),
        )
