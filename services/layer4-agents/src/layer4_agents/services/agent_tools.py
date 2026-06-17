from __future__ import annotations

"""AgentToolRegistry — Mutation tools for ValuePilot agent actions.

Allows the agent to trigger real side-effects (promote signal, validate
hypothesis) rather than just generating text. Each tool validates tenant
scope before executing and returns structured results for LLM consumption.

Tools:
  - promote_signal: Create a ValueHypothesis from a PainSignal
  - validate_hypothesis: Update hypothesis status based on user feedback
"""
import asyncio
import logging
from typing import Any

from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.policy_registry import authorize_action

logger = logging.getLogger(__name__)


class AgentToolRegistry:
    """Registry of agent-callable mutation tools."""

    def __init__(
        self,
        *,
        neo4j_driver: Any | None = None,
        db: Any | None = None,
    ) -> None:
        self._driver = neo4j_driver
        self._db = db

    async def promote_signal(
        self,
        *,
        tenant_id: str,
        account_id: str,
        signal_id: str,
        value_path_category: str | None = None,
        context: RequestContext | None = None,
    ) -> dict[str, Any]:
        """Promote a pain signal to a value hypothesis."""
        authorize_action(
            "layer4.agent_tool.promote_signal",
            context,
            target_tenant_id=tenant_id,
        )
        if not self._driver:
            return {"success": False, "error": "Neo4j driver not available"}

        try:
            from ..services.value_hypothesis_engine import ValueHypothesisEngine

            engine = ValueHypothesisEngine(self._driver)
            result = await engine.promote_signal(
                tenant_id=tenant_id,
                account_id=account_id,
                signal_id=signal_id,
                value_path_category=value_path_category,
            )
            return {
                "success": True,
                "hypothesis_id": result.get("hypothesis_id"),
                "message": f"Signal {signal_id} promoted to hypothesis.",
            }
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("promote_signal tool failed: %s", e)
            return {"success": False, "error": "Signal promotion failed", "error_code": "SIGNAL_PROMOTION_ERROR"}

    async def validate_hypothesis(
        self,
        *,
        tenant_id: str,
        hypothesis_id: str,
        new_status: str,
        feedback: str = "",
        context: RequestContext | None = None,
    ) -> dict[str, Any]:
        """Validate or reject a value hypothesis."""
        authorize_action(
            "layer4.agent_tool.validate_hypothesis",
            context,
            target_tenant_id=tenant_id,
        )
        if not self._driver:
            return {"success": False, "error": "Neo4j driver not available"}

        try:
            from ..services.value_hypothesis_engine import ValueHypothesisEngine

            engine = ValueHypothesisEngine(self._driver)
            result = await engine.validate_hypothesis(
                tenant_id=tenant_id,
                hypothesis_id=hypothesis_id,
                feedback=feedback,
                new_status=new_status,
            )
            if result is None:
                return {"success": False, "error": "Hypothesis not found"}
            return {
                "success": True,
                "hypothesis_id": hypothesis_id,
                "new_status": result.get("status"),
                "message": f"Hypothesis {hypothesis_id} updated to {new_status}.",
            }
        except asyncio.CancelledError:
            raise
        except Exception as e:
            logger.warning("validate_hypothesis tool failed: %s", e)
            return {"success": False, "error": "Hypothesis validation failed", "error_code": "HYPOTHESIS_VALIDATION_ERROR"}

    def get_tool_schemas(self) -> list[dict[str, Any]]:
        """Return OpenAI-compatible function schemas."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "promote_signal",
                    "description": "Promote a pain signal to a value hypothesis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "account_id": {"type": "string", "description": "Account identifier"},
                            "signal_id": {"type": "string", "description": "Signal to promote"},
                            "value_path_category": {
                                "type": "string",
                                "enum": ["revenue_uplift", "cost_savings", "risk_reduction", "blended"],
                                "description": "Value path classification",
                            },
                        },
                        "required": ["account_id", "signal_id"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_hypothesis",
                    "description": "Validate or reject a value hypothesis.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "hypothesis_id": {"type": "string", "description": "Hypothesis identifier"},
                            "new_status": {
                                "type": "string",
                                "enum": ["validated", "rejected"],
                                "description": "New status for the hypothesis",
                            },
                            "feedback": {"type": "string", "description": "Optional feedback notes"},
                        },
                        "required": ["hypothesis_id", "new_status"],
                    },
                },
            },
        ]
