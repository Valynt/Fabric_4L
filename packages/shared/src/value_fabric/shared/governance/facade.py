from __future__ import annotations

import json
import uuid

from ..llm_safety.prompt_guard import PromptGuard
from .abom import AgentBillOfMaterials
from .decision import Decision, DecisionEffect, Obligation
from .policy_engine import PolicyEngineClient


def _serialize_input(input_data: dict[str, object] | None) -> str | None:
    """Serialize action input for prompt-injection scanning.

    Returns None when there is no input, so the safety guard treats the
    action as having no prompt text to inspect.
    """
    if not input_data:
        return None
    return json.dumps(input_data, default=str)


class PolicyDecisionFacade:
    """Thin transport-neutral coordinator over the existing governance evaluators."""

    def __init__(
        self,
        policy_client: PolicyEngineClient | None = None,
        abom: AgentBillOfMaterials | None = None,
        llm_safety: PromptGuard | None = None,
        allowed_actions: set[str] | frozenset[str] | None = None,
    ) -> None:
        self.policy_client = policy_client or PolicyEngineClient()
        self.abom = abom
        self.llm_safety = llm_safety
        # Non-tool actions are fail-closed by default: they must be explicitly
        # registered here to be authorized. Tool actions are instead evaluated
        # against the ABOM/policy engine.
        self._allowed_actions: frozenset[str] = frozenset(allowed_actions or ())

    def _deny(
        self,
        *,
        reason_code: str,
        reason: str,
        action: str | None = None,
        resource: str | None = None,
        tenant_id: str | None = None,
        actor_id: str | None = None,
        policy_ids: list[str] | None = None,
        obligations: list[str] | None = None,
        trace_id: str | None = None,
        policy_bundle_hash: str | None = None,
    ) -> Decision:
        return Decision(
            effect=DecisionEffect.DENY,
            reason_code=reason_code,
            reason=reason,
            obligations=list(obligations or []),
            policy_ids=list(policy_ids or []),
            policy_bundle_hash=policy_bundle_hash,
            decision_id=f"decision-{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource=resource,
            trace_id=trace_id,
        )

    async def evaluate_action(
        self,
        *,
        action: str,
        resource: str,
        tenant_id: str | None,
        actor_id: str | None = None,
        tool_name: str | None = None,
        input_data: dict[str, object] | None = None,
        policy_ids: list[str] | None = None,
        trace_id: str | None = None,
    ) -> Decision:
        """Compose the existing evaluators into a single decision result."""
        if not action:
            return self._deny(
                reason_code="missing_action",
                reason="Action identifier is required.",
                action=action,
                resource=resource,
                tenant_id=tenant_id,
                actor_id=actor_id,
                policy_ids=policy_ids,
                trace_id=trace_id,
            )
        if tenant_id is not None and isinstance(tenant_id, str):
            tenant_id = tenant_id.strip()
        if not tenant_id or tenant_id in {"unknown", "None", "null"}:
            return self._deny(
                reason_code="missing_tenant",
                reason="Tenant context is required for policy evaluation.",
                action=action,
                resource=resource,
                tenant_id=tenant_id,
                actor_id=actor_id,
                policy_ids=policy_ids,
                trace_id=trace_id,
            )
        decision_obligations: list[str] = [Obligation.AUDIT.value]
        decision_policy_bundle_hash: str | None = None

        if tool_name is not None:
            if self.abom is None:
                return self._deny(
                    reason_code="missing_abom",
                    reason="Agent Bill of Materials is required for tool policy evaluation.",
                    action=action,
                    resource=resource,
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    policy_ids=policy_ids,
                    trace_id=trace_id,
                )
            legacy_decision = await self.policy_client.evaluate(
                self.abom,
                tool_name,
                input_data or {},
                tenant_id=tenant_id,
            )
            decision_obligations = [str(item) for item in legacy_decision.obligations]
            if not decision_obligations:
                decision_obligations = [Obligation.AUDIT.value]
            decision_policy_bundle_hash = (
                legacy_decision.policy_bundle_hash or self.abom.manifest_hash()
            )
            if not legacy_decision.allowed:
                return Decision(
                    effect=DecisionEffect.DENY,
                    reason_code="policy_denied",
                    reason=legacy_decision.reason or "Policy denied.",
                    obligations=decision_obligations,
                    policy_ids=policy_ids or [],
                    policy_bundle_hash=decision_policy_bundle_hash,
                    decision_id=f"decision-{uuid.uuid4().hex[:12]}",
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    action=action,
                    resource=resource,
                    trace_id=trace_id,
                )
        else:
            if action not in self._allowed_actions:
                return self._deny(
                    reason_code="action_not_authorized",
                    reason=f"Action '{action}' is not authorized by any registered policy.",
                    action=action,
                    resource=resource,
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    policy_ids=policy_ids,
                    trace_id=trace_id,
                )

        if self.llm_safety is not None:
            safety = self.llm_safety.check(_serialize_input(input_data))
            if safety.is_injection:
                return self._deny(
                    reason_code="llm_safety_blocked",
                    reason="LLM safety policy blocked execution.",
                    action=action,
                    resource=resource,
                    tenant_id=tenant_id,
                    actor_id=actor_id,
                    policy_ids=policy_ids,
                    trace_id=trace_id,
                    obligations=[Obligation.MASK.value],
                )

        return Decision(
            effect=DecisionEffect.ALLOW,
            reason_code="allow",
            reason="Policy evaluation passed.",
            obligations=decision_obligations,
            policy_ids=policy_ids or [],
            policy_bundle_hash=(
                decision_policy_bundle_hash
                if decision_policy_bundle_hash is not None
                else getattr(self.abom, "manifest_hash", lambda: None)()
            ),
            decision_id=f"decision-{uuid.uuid4().hex[:12]}",
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource=resource,
            trace_id=trace_id,
        )


__all__ = ["PolicyDecisionFacade"]
