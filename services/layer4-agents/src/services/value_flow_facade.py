from __future__ import annotations

"""UI-facing workflow facade service for value flow step endpoints."""


import json
from typing import Any

from ..api.schemas.value_flow import ValueFlowStep, now_iso


class ValueFlowFacadeService:
    """Coordinates save/resume and adapter payloads for UI workflow steps."""

    REDIS_PREFIX = "layer4:value_flow"

    def __init__(self, redis_client=None):
        self.redis = redis_client
        self._memory_store: dict[str, dict[str, Any]] = {}

    def _key(self, flow_instance_id: str) -> str:
        return f"{self.REDIS_PREFIX}:{flow_instance_id}"

    async def _load_flow(self, flow_instance_id: str) -> dict[str, Any]:
        key = self._key(flow_instance_id)
        if self.redis:
            data = await self.redis.get(key)
            if data:
                return json.loads(data)
        return self._memory_store.get(key, {"steps": {}, "current_step": ValueFlowStep.setup.value})

    async def _save_flow(self, flow_instance_id: str, payload: dict[str, Any]) -> None:
        key = self._key(flow_instance_id)
        if self.redis:
            await self.redis.setex(key, 604800, json.dumps(payload))
        self._memory_store[key] = payload

    async def save_step_state(
        self,
        flow_instance_id: str,
        step: ValueFlowStep,
        state: dict[str, Any],
        idempotency_key: str | None,
    ) -> dict[str, Any]:
        flow_data = await self._load_flow(flow_instance_id)
        steps = flow_data.setdefault("steps", {})
        existing = steps.get(step.value)
        if existing and idempotency_key and existing.get("idempotency_key") == idempotency_key:
            return existing

        steps[step.value] = {
            "state": self._adapt_step_data(step, state),
            "updated_at": now_iso(),
            "idempotency_key": idempotency_key,
        }
        flow_data["current_step"] = step.value
        flow_data["last_updated_at"] = steps[step.value]["updated_at"]
        await self._save_flow(flow_instance_id, flow_data)
        return steps[step.value]

    async def load_step_state(self, flow_instance_id: str, step: ValueFlowStep) -> dict[str, Any] | None:
        flow_data = await self._load_flow(flow_instance_id)
        return flow_data.get("steps", {}).get(step.value)

    async def apply_confirmation(
        self,
        flow_instance_id: str,
        step: ValueFlowStep,
        action: str,
        rationale: str | None,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        confirmation_state = {
            "action": action,
            "rationale": rationale,
            "metadata": metadata,
            "confirmed_at": now_iso(),
        }
        await self.save_step_state(flow_instance_id, step, {"confirmation": confirmation_state}, None)

        next_step = self._next_step(step) if action == "confirm" else None
        return {
            "accepted": action == "confirm",
            "message": "Step confirmed" if action == "confirm" else "Action recorded",
            "next_step": next_step,
        }

    async def completion_status(self, flow_instance_id: str) -> dict[str, Any]:
        flow_data = await self._load_flow(flow_instance_id)
        steps = flow_data.get("steps", {})
        completed_steps = [ValueFlowStep(name) for name in steps]
        current_step = ValueFlowStep(flow_data.get("current_step", ValueFlowStep.setup.value))
        return {
            "current_step": current_step,
            "completed_steps": completed_steps,
            "is_complete": ValueFlowStep.completion.value in steps,
            "last_updated_at": flow_data.get("last_updated_at", now_iso()),
        }

    def _adapt_step_data(self, step: ValueFlowStep, state: dict[str, Any]) -> dict[str, Any]:
        """Adapter layer to return UI-ready fields and hide low-level internals."""
        base = {"view": step.value, "payload": state}
        if step == ValueFlowStep.intelligence:
            base["summary"] = state.get("summary") or state.get("insights", [])
        elif step == ValueFlowStep.model:
            base["model_card"] = state.get("model_card", {})
        return base

    def _next_step(self, step: ValueFlowStep) -> ValueFlowStep | None:
        order = list(ValueFlowStep)
        idx = order.index(step)
        return order[idx + 1] if idx + 1 < len(order) else None
