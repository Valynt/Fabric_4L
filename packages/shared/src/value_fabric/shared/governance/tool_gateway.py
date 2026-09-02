"""ToolGateway — policy-enforced tool invocation proxy.

Wraps ``ToolRegistry.execute()`` with:
1. ABOM allow/deny list check
2. OPA policy evaluation (or local fallback)
3. Invariant pre-checks (budget, call count, human approval)
4. Post-invocation invariant recording
5. Audit event emission with full chain_id tracking

Agents MUST invoke tools through ``ToolGateway.execute()`` instead of
calling ``ToolRegistry.execute()`` directly.

GATE Framework §2.4 — ToolGateway
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any
from uuid import UUID

from value_fabric.shared.audit.emitter import emit_audit_event
from value_fabric.shared.audit.models import (
    AuditAction,
    AuditOutcome,
    PolicyDecisionRecord,
    ToolInvocationRecord,
)
from value_fabric.shared.crypto.canonical import canonical_hash

from .abom import AgentBillOfMaterials
from .invariants import InvariantEvaluator
from .policy_engine import PolicyDecision, PolicyEngineClient

logger = logging.getLogger(__name__)


class ToolGatewayDenied(Exception):
    """Raised when ToolGateway denies a tool invocation."""

    def __init__(self, tool_name: str, reason: str) -> None:
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"ToolGateway denied '{tool_name}': {reason}")


class ToolError(Exception):
    """Raised when the underlying tool execution reports a structured failure."""

    pass


class InvariantViolation(Exception):
    """Raised when an invariant check fails."""

    def __init__(self, violations: list[str]) -> None:
        self.violations = violations
        super().__init__(f"Invariant violations: {violations}")


class ToolGateway:
    """Policy-enforced tool invocation gateway.

    Args:
        registry: ToolRegistry instance for actual tool execution.
        abom: Agent's ABOM manifest.
        policy_client: OPA policy engine client (optional).
        tenant_id: Tenant context for multi-tenant policies.
        trace_id: Trace ID for audit correlation.
    """

    def __init__(
        self,
        registry: Any,  # ToolRegistry — avoid circular import
        abom: AgentBillOfMaterials,
        policy_client: PolicyEngineClient | None = None,
        tenant_id: str | None = None,
        trace_id: str | None = None,
    ) -> None:
        self._registry = registry
        self._abom = abom
        self._policy_client = policy_client or PolicyEngineClient()
        self._invariant_evaluator = InvariantEvaluator(abom)
        self._tenant_id = tenant_id
        self._trace_id = trace_id
        self._invocation_log: list[dict[str, Any]] = []

    @property
    def invariant_evaluator(self) -> InvariantEvaluator:
        """Access the invariant evaluator for state inspection."""
        return self._invariant_evaluator

    @property
    def invocation_log(self) -> list[dict[str, Any]]:
        """Read-only access to the invocation log for replay recording."""
        return list(self._invocation_log)

    async def execute(
        self,
        tool_name: str,
        input_data: dict[str, Any],
        estimated_cost_usd: float = 0.0,
    ) -> dict[str, Any]:
        """Execute a tool through the GATE policy pipeline.

        Pipeline:
        1. ABOM allow/deny check
        2. OPA policy evaluation
        3. Invariant pre-check
        4. Tool execution (via ToolRegistry)
        5. Post-invocation recording
        6. Audit event emission

        Args:
            tool_name: Registered tool name.
            input_data: Tool input parameters.
            estimated_cost_usd: Estimated cost for budget invariant.

        Returns:
            Tool output as dictionary.

        Raises:
            ToolGatewayDenied: If policy or ABOM denies the invocation.
            InvariantViolation: If invariant checks fail.
        """
        request_hash = canonical_hash({"tool_name": tool_name, "input": input_data})

        # ── Step 1: ABOM allow/deny ──
        if not self._abom.is_tool_allowed(tool_name):
            reason = f"ABOM denies tool '{tool_name}' for {self._abom.agent_type}"
            await self._emit_policy_decision_audit(
                tool_name=tool_name,
                allowed=False,
                reason=reason,
                obligations=["abom_denied"],
                policy_bundle_hash=self._abom.manifest_hash(),
            )
            await self._emit_denied_audit(tool_name, request_hash, reason, "denied")
            raise ToolGatewayDenied(tool_name, reason)

        # ── Step 2: OPA policy evaluation ──
        tenant_id = self._tenant_id
        if not tenant_id or tenant_id in {"unknown", "None", "null", ""}:
            reason = "Tenant context is required for policy evaluation."
            await self._emit_policy_decision_audit(
                tool_name=tool_name,
                allowed=False,
                reason=reason,
                obligations=["AUDIT"],
                policy_bundle_hash=self._abom.manifest_hash(),
            )
            await self._emit_denied_audit(tool_name, request_hash, reason, "missing_tenant")
            raise ToolGatewayDenied(tool_name, reason)

        policy_decision = await self._policy_client.evaluate(
            abom=self._abom,
            tool_name=tool_name,
            input_data=input_data,
            tenant_id=tenant_id,
        )
        await self._emit_policy_decision_audit(
            tool_name=tool_name,
            allowed=policy_decision.allowed,
            reason=policy_decision.reason,
            obligations=policy_decision.obligations,
            policy_bundle_hash=policy_decision.policy_bundle_hash or self._abom.manifest_hash(),
        )
        if not policy_decision.allowed:
            reason = policy_decision.reason or "Policy denied"
            await self._emit_denied_audit(tool_name, request_hash, reason, "denied")
            raise ToolGatewayDenied(tool_name, reason)

        # ── Step 3: Invariant pre-check ──
        inv_result = self._invariant_evaluator.check_pre_invocation(
            tool_name=tool_name,
            input_data=input_data,
            estimated_cost_usd=estimated_cost_usd,
        )
        invariant_bundle_hash = canonical_hash({
            "abom_manifest_hash": self._abom.manifest_hash(),
            "invariants": self._abom.invariants.model_dump(),
        })
        if not inv_result.passed:
            reason = "; ".join(inv_result.violations)
            await self._emit_policy_decision_audit(
                tool_name=tool_name,
                allowed=False,
                reason=reason,
                obligations=["invariant_blocked", *inv_result.violations],
                policy_bundle_hash=invariant_bundle_hash,
            )
            await self._emit_denied_audit(
                tool_name,
                request_hash,
                reason,
                "invariant_blocked",
                invariant_checks=inv_result.violations,
            )
            raise InvariantViolation(inv_result.violations)

        for warning in inv_result.warnings:
            logger.warning("Invariant warning for %s: %s", tool_name, warning)

        # ── Step 4: Execute tool ──
        start_time = asyncio.get_running_loop().time()
        try:
            raw_result = await self._registry.execute(tool_name, input_data)
        except Exception:
            self._invariant_evaluator.record_invocation(
                tool_name, cost_usd=0.0, success=False
            )
            raise

        # Normalize structured ToolResult (Layer 4 registry) to a plain dict.
        if hasattr(raw_result, "model_dump"):
            result_dict = raw_result.model_dump()
            if hasattr(raw_result, "is_success") and not raw_result.is_success():
                error = result_dict.get("error") or {}
                raise ToolError(
                    f"Tool '{tool_name}' execution failed: {error.get('message', 'unknown')}"
                )
        elif isinstance(raw_result, dict):
            result_dict = raw_result
        else:
            result_dict = {"result": raw_result}

        elapsed_ms = int((asyncio.get_running_loop().time() - start_time) * 1000)

        # ── Step 5: Post-invocation recording ──
        self._invariant_evaluator.record_invocation(
            tool_name, cost_usd=estimated_cost_usd, success=True
        )

        response_hash = canonical_hash(result_dict)
        log_entry = {
            "tool_name": tool_name,
            "request_hash": request_hash,
            "response_hash": response_hash,
            "execution_time_ms": elapsed_ms,
            "policy_decision": "allowed",
            "policy_bundle_hash": policy_decision.policy_bundle_hash or self._abom.manifest_hash(),
            "invariant_checks": inv_result.warnings,
        }
        self._invocation_log.append(log_entry)

        # ── Step 6: Audit emission ──
        await self._emit_success_audit(
            tool_name=tool_name,
            request_hash=request_hash,
            response_hash=response_hash,
            elapsed_ms=elapsed_ms,
            policy_decision=policy_decision,
            invariant_checks=inv_result.warnings,
        )

        return result_dict

    async def _emit_success_audit(
        self,
        tool_name: str,
        request_hash: str,
        response_hash: str,
        elapsed_ms: int,
        policy_decision: PolicyDecision,
        invariant_checks: list[str] | None = None,
    ) -> None:
        """Emit TOOL_INVOCATION audit event for successful execution."""
        record = ToolInvocationRecord(
            tool_name=tool_name,
            tool_manifest_hash=self._abom.manifest_hash(),
            request_hash=request_hash,
            response_hash=response_hash,
            policy_decision="allowed",
            invariant_checks=invariant_checks or [],
            execution_time_ms=elapsed_ms,
            tenant_id=self._tenant_id,
            trace_id=self._trace_id,
        )
        await emit_audit_event(
            action=AuditAction.TOOL_INVOCATION,
            outcome=AuditOutcome.SUCCESS,
            resource_type="tool",
            resource_id=tool_name,
            tenant_id=self._tenant_uuid(),
            request_id=self._trace_id,
            details=record.model_dump(),
            chain_id=f"{self._tenant_id or 'global'}:{tool_name}",
        )

    async def _emit_denied_audit(
        self,
        tool_name: str,
        request_hash: str,
        reason: str,
        decision_type: str,
        invariant_checks: list[str] | None = None,
    ) -> None:
        """Emit TOOL_INVOCATION audit event for denied execution."""
        record = ToolInvocationRecord(
            tool_name=tool_name,
            tool_manifest_hash=self._abom.manifest_hash(),
            request_hash=request_hash,
            policy_decision=decision_type,
            invariant_checks=invariant_checks or [],
            tenant_id=self._tenant_id,
            trace_id=self._trace_id,
        )
        await emit_audit_event(
            action=AuditAction.TOOL_INVOCATION,
            outcome=AuditOutcome.DENIED,
            resource_type="tool",
            resource_id=tool_name,
            tenant_id=self._tenant_uuid(),
            request_id=self._trace_id,
            details={**record.model_dump(), "denial_reason": reason},
            chain_id=f"{self._tenant_id or 'global'}:{tool_name}",
        )

    async def _emit_policy_decision_audit(
        self,
        tool_name: str,
        allowed: bool,
        reason: str | None,
        obligations: list[str] | None,
        policy_bundle_hash: str | None,
    ) -> None:
        """Emit the stage-1/stage-2 runtime policy decision for audit replay."""
        record = PolicyDecisionRecord(
            decision=allowed,
            reason=reason,
            obligations=obligations or [],
            policy_bundle_hash=policy_bundle_hash,
        )
        await emit_audit_event(
            action=AuditAction.POLICY_DECISION,
            outcome=AuditOutcome.SUCCESS if allowed else AuditOutcome.DENIED,
            resource_type="tool",
            resource_id=tool_name,
            tenant_id=self._tenant_uuid(),
            request_id=self._trace_id,
            details=record.model_dump(),
            chain_id=f"{self._tenant_id or 'global'}:policy:{tool_name}",
        )

    def _tenant_uuid(self) -> UUID | None:
        """Return a UUID tenant for audit storage when the tenant ID is canonical."""
        if not self._tenant_id:
            return None
        try:
            return UUID(self._tenant_id)
        except (TypeError, ValueError):
            return None

    def reset_for_new_run(self) -> None:
        """Reset gateway state for a new agent run."""
        self._invariant_evaluator.reset()
        self._invocation_log.clear()
