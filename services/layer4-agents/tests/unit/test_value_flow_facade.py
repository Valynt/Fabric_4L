from __future__ import annotations

"""
Unit tests for ValueFlowFacadeService.

Tests save/resume, idempotency, step transitions, and completion status
without requiring Redis or any external dependencies.
"""


import pytest
from unittest.mock import AsyncMock, MagicMock

from layer4_agents.api.schemas.value_flow import ValueFlowStep
from layer4_agents.services.value_flow_facade import ValueFlowFacadeService


class TestValueFlowFacadeInMemory:
    """Test facade behaviour using the in-memory (no-Redis) store."""

    def _svc(self) -> ValueFlowFacadeService:
        return ValueFlowFacadeService(redis_client=None)

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_and_load_step_state(self):
        """Saved step state can be loaded back unchanged."""
        svc = self._svc()
        flow_id = "flow-abc-001"
        state = {"target_arr": 1_000_000, "company": "Acme"}

        await svc.save_step_state(flow_id, ValueFlowStep.setup, state, idempotency_key=None)
        loaded = await svc.load_step_state(flow_id, ValueFlowStep.setup)

        assert loaded is not None
        assert loaded["state"]["payload"] == state

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_load_nonexistent_step_returns_none(self):
        """Loading a step that was never saved returns None."""
        svc = self._svc()
        result = await svc.load_step_state("flow-missing", ValueFlowStep.intelligence)
        assert result is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_idempotency_key_prevents_duplicate_save(self):
        """Second save with same idempotency key returns the first saved state."""
        svc = self._svc()
        flow_id = "flow-idempotent"
        key = "idem-key-001"

        first_state = {"value": "original"}
        second_state = {"value": "overwrite_attempt"}

        first_result = await svc.save_step_state(
            flow_id, ValueFlowStep.setup, first_state, idempotency_key=key
        )
        second_result = await svc.save_step_state(
            flow_id, ValueFlowStep.setup, second_state, idempotency_key=key
        )

        # Should return the cached first result without mutation
        assert first_result is second_result
        loaded = await svc.load_step_state(flow_id, ValueFlowStep.setup)
        assert loaded["state"]["payload"] == first_state

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_different_idempotency_keys_allow_overwrite(self):
        """A new idempotency key allows overwriting existing step state."""
        svc = self._svc()
        flow_id = "flow-new-key"

        await svc.save_step_state(flow_id, ValueFlowStep.setup, {"v": 1}, idempotency_key="key-a")
        await svc.save_step_state(flow_id, ValueFlowStep.setup, {"v": 2}, idempotency_key="key-b")

        loaded = await svc.load_step_state(flow_id, ValueFlowStep.setup)
        assert loaded["state"]["payload"] == {"v": 2}

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_current_step_is_updated(self):
        """current_step reflects the most recently saved step."""
        svc = self._svc()
        flow_id = "flow-step-track"

        await svc.save_step_state(flow_id, ValueFlowStep.setup, {}, idempotency_key=None)
        status = await svc.completion_status(flow_id)
        assert status["current_step"] == ValueFlowStep.setup

        await svc.save_step_state(flow_id, ValueFlowStep.intelligence, {}, idempotency_key=None)
        status = await svc.completion_status(flow_id)
        assert status["current_step"] == ValueFlowStep.intelligence

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_completion_status_not_complete_initially(self):
        """Flow is not complete when only early steps are saved."""
        svc = self._svc()
        flow_id = "flow-incomplete"

        await svc.save_step_state(flow_id, ValueFlowStep.setup, {}, idempotency_key=None)
        status = await svc.completion_status(flow_id)

        assert status["is_complete"] is False
        assert ValueFlowStep.setup in status["completed_steps"]

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_completion_status_complete_after_all_steps(self):
        """Flow is complete when the 'completion' step is saved."""
        svc = self._svc()
        flow_id = "flow-complete"

        for step in ValueFlowStep:
            await svc.save_step_state(flow_id, step, {}, idempotency_key=None)

        status = await svc.completion_status(flow_id)
        assert status["is_complete"] is True
        assert len(status["completed_steps"]) == len(list(ValueFlowStep))

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_apply_confirmation_confirm(self):
        """Confirm action returns accepted=True and advances to next step."""
        svc = self._svc()
        flow_id = "flow-confirm"

        await svc.save_step_state(flow_id, ValueFlowStep.setup, {}, idempotency_key=None)
        result = await svc.apply_confirmation(
            flow_id, ValueFlowStep.setup, "confirm", "Looks good", {}
        )

        assert result["accepted"] is True
        assert result["next_step"] == ValueFlowStep.intelligence

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_apply_confirmation_reject(self):
        """Reject action returns accepted=False with no next_step."""
        svc = self._svc()
        flow_id = "flow-reject"

        await svc.save_step_state(flow_id, ValueFlowStep.setup, {}, idempotency_key=None)
        result = await svc.apply_confirmation(
            flow_id, ValueFlowStep.setup, "reject", "Not ready", {}
        )

        assert result["accepted"] is False
        assert result["next_step"] is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_apply_confirmation_last_step_has_no_next(self):
        """Confirming the final step returns next_step=None."""
        svc = self._svc()
        flow_id = "flow-last-step"

        result = await svc.apply_confirmation(
            flow_id, ValueFlowStep.completion, "confirm", None, {}
        )

        assert result["accepted"] is True
        assert result["next_step"] is None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_adapt_step_data_intelligence_summary(self):
        """Intelligence step exposes 'summary' field in adapted state."""
        svc = self._svc()
        flow_id = "flow-intel"
        state = {"summary": "AI insights here", "raw": "data"}

        await svc.save_step_state(flow_id, ValueFlowStep.intelligence, state, idempotency_key=None)
        loaded = await svc.load_step_state(flow_id, ValueFlowStep.intelligence)

        assert loaded["state"]["summary"] == "AI insights here"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_adapt_step_data_model_card(self):
        """Model step exposes 'model_card' field in adapted state."""
        svc = self._svc()
        flow_id = "flow-model"
        model_card = {"name": "ROI Model v2", "accuracy": 0.95}
        state = {"model_card": model_card, "other": "data"}

        await svc.save_step_state(flow_id, ValueFlowStep.model, state, idempotency_key=None)
        loaded = await svc.load_step_state(flow_id, ValueFlowStep.model)

        assert loaded["state"]["model_card"] == model_card

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_multiple_flows_are_isolated(self):
        """State from one flow_instance_id does not leak into another."""
        svc = self._svc()

        await svc.save_step_state("flow-A", ValueFlowStep.setup, {"x": 1}, idempotency_key=None)
        await svc.save_step_state("flow-B", ValueFlowStep.setup, {"x": 99}, idempotency_key=None)

        loaded_a = await svc.load_step_state("flow-A", ValueFlowStep.setup)
        loaded_b = await svc.load_step_state("flow-B", ValueFlowStep.setup)

        assert loaded_a["state"]["payload"]["x"] == 1
        assert loaded_b["state"]["payload"]["x"] == 99


class TestValueFlowFacadeRedis:
    """Test facade behaviour with a mocked Redis client."""

    def _make_redis(self) -> MagicMock:
        redis = MagicMock()
        redis.get = AsyncMock(return_value=None)
        redis.setex = AsyncMock(return_value=True)
        return redis

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_save_calls_redis_setex(self):
        """save_step_state stores data in Redis via setex."""
        redis = self._make_redis()
        svc = ValueFlowFacadeService(redis_client=redis)

        await svc.save_step_state("flow-r1", ValueFlowStep.setup, {"k": "v"}, idempotency_key=None)

        redis.setex.assert_called_once()
        call_args = redis.setex.call_args
        key_arg = call_args[0][0]
        assert "flow-r1" in key_arg

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_load_from_redis_on_cache_miss(self):
        """load_step_state fetches from Redis when not in memory store."""
        import json

        stored_flow = {
            "steps": {
                "setup": {
                    "state": {"view": "setup", "payload": {"from_redis": True}},
                    "updated_at": "2025-01-01T00:00:00+00:00",
                    "idempotency_key": None,
                }
            },
            "current_step": "setup",
            "last_updated_at": "2025-01-01T00:00:00+00:00",
        }

        redis = self._make_redis()
        redis.get = AsyncMock(return_value=json.dumps(stored_flow))
        svc = ValueFlowFacadeService(redis_client=redis)

        loaded = await svc.load_step_state("flow-r2", ValueFlowStep.setup)

        assert loaded is not None
        assert loaded["state"]["payload"]["from_redis"] is True

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_redis_miss_returns_empty_flow(self):
        """When Redis returns None, service returns default empty flow data."""
        redis = self._make_redis()
        redis.get = AsyncMock(return_value=None)
        svc = ValueFlowFacadeService(redis_client=redis)

        loaded = await svc.load_step_state("flow-empty", ValueFlowStep.setup)
        assert loaded is None


class TestValueFlowFacadeNextStep:
    """Test the internal _next_step helper."""

    def _svc(self) -> ValueFlowFacadeService:
        return ValueFlowFacadeService(redis_client=None)

    @pytest.mark.unit
    def test_next_step_from_setup(self):
        svc = self._svc()
        assert svc._next_step(ValueFlowStep.setup) == ValueFlowStep.intelligence

    @pytest.mark.unit
    def test_next_step_from_intelligence(self):
        svc = self._svc()
        assert svc._next_step(ValueFlowStep.intelligence) == ValueFlowStep.model

    @pytest.mark.unit
    def test_next_step_from_model(self):
        svc = self._svc()
        assert svc._next_step(ValueFlowStep.model) == ValueFlowStep.validation

    @pytest.mark.unit
    def test_next_step_from_validation(self):
        svc = self._svc()
        assert svc._next_step(ValueFlowStep.validation) == ValueFlowStep.completion

    @pytest.mark.unit
    def test_next_step_from_completion_is_none(self):
        svc = self._svc()
        assert svc._next_step(ValueFlowStep.completion) is None
