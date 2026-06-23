from __future__ import annotations

"""
Tests for ValueFlowFacadeService.

Covers:
- save_step_state (normal and idempotent)
- load_step_state (hit and miss)
- apply_confirmation (confirm / reject)
- completion_status
- _adapt_step_data adapter layer
- _next_step progression
- In-memory fallback (no Redis)
"""


import pytest

from layer4_agents.api.schemas.value_flow import ValueFlowStep
from layer4_agents.services.value_flow_facade import ValueFlowFacadeService


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def facade() -> ValueFlowFacadeService:
    """Return a ValueFlowFacadeService backed by in-memory store (no Redis)."""
    return ValueFlowFacadeService(redis_client=None)


FLOW_ID = "test-flow-001"


# ---------------------------------------------------------------------------
# save_step_state
# ---------------------------------------------------------------------------

class TestSaveStepState:
    """Tests for save_step_state."""

    @pytest.mark.asyncio
    async def test_save_returns_saved_record(self, facade):
        """save_step_state returns a dict with state and updated_at."""
        result = await facade.save_step_state(
            FLOW_ID,
            ValueFlowStep.setup,
            {"name": "Acme"},
            idempotency_key=None,
        )
        assert result["state"]["payload"] == {"name": "Acme"}
        assert "updated_at" in result

    @pytest.mark.asyncio
    async def test_idempotent_save_returns_existing(self, facade):
        """Duplicate save with same idempotency_key returns cached record unchanged."""
        first = await facade.save_step_state(
            FLOW_ID,
            ValueFlowStep.setup,
            {"name": "Acme"},
            idempotency_key="idem-001",
        )
        second = await facade.save_step_state(
            FLOW_ID,
            ValueFlowStep.setup,
            {"name": "Overwrite attempt"},
            idempotency_key="idem-001",
        )
        # Should return the first saved record unchanged
        assert second["state"]["payload"] == {"name": "Acme"}
        assert second["updated_at"] == first["updated_at"]

    @pytest.mark.asyncio
    async def test_different_idempotency_key_overwrites(self, facade):
        """Different idempotency keys allow overwriting step state."""
        await facade.save_step_state(
            FLOW_ID,
            ValueFlowStep.setup,
            {"name": "First"},
            idempotency_key="idem-001",
        )
        result = await facade.save_step_state(
            FLOW_ID,
            ValueFlowStep.setup,
            {"name": "Second"},
            idempotency_key="idem-002",
        )
        assert result["state"]["payload"] == {"name": "Second"}

    @pytest.mark.asyncio
    async def test_current_step_updated(self, facade):
        """After saving intelligence step, completion_status reflects it."""
        await facade.save_step_state(
            FLOW_ID,
            ValueFlowStep.intelligence,
            {"summary": "great insights"},
            idempotency_key=None,
        )
        status = await facade.completion_status(FLOW_ID)
        assert status["current_step"] == ValueFlowStep.intelligence


# ---------------------------------------------------------------------------
# load_step_state
# ---------------------------------------------------------------------------

class TestLoadStepState:
    """Tests for load_step_state."""

    @pytest.mark.asyncio
    async def test_load_returns_none_when_missing(self, facade):
        """Loading a step that hasn't been saved returns None."""
        result = await facade.load_step_state(FLOW_ID, ValueFlowStep.validation)
        assert result is None

    @pytest.mark.asyncio
    async def test_load_returns_saved_data(self, facade):
        """Loading a saved step returns the correct data."""
        await facade.save_step_state(
            FLOW_ID,
            ValueFlowStep.model,
            {"model_card": {"version": "1.0"}},
            idempotency_key=None,
        )
        result = await facade.load_step_state(FLOW_ID, ValueFlowStep.model)
        assert result is not None
        assert result["state"]["payload"] == {"model_card": {"version": "1.0"}}


# ---------------------------------------------------------------------------
# apply_confirmation
# ---------------------------------------------------------------------------

class TestApplyConfirmation:
    """Tests for apply_confirmation."""

    @pytest.mark.asyncio
    async def test_confirm_returns_accepted_true(self, facade):
        """Confirming a step returns accepted=True and advances to next step."""
        result = await facade.apply_confirmation(
            FLOW_ID,
            ValueFlowStep.setup,
            action="confirm",
            rationale="Looks good",
            metadata={"reviewer": "alice"},
        )
        assert result["accepted"] is True
        assert result["message"] == "Step confirmed"
        assert result["next_step"] is not None

    @pytest.mark.asyncio
    async def test_reject_returns_accepted_false(self, facade):
        """Rejecting a step returns accepted=False."""
        result = await facade.apply_confirmation(
            FLOW_ID,
            ValueFlowStep.setup,
            action="reject",
            rationale="Needs revision",
            metadata={},
        )
        assert result["accepted"] is False
        assert result["next_step"] is None

    @pytest.mark.asyncio
    async def test_completion_step_confirm_has_no_next_step(self, facade):
        """Confirming the final step returns next_step=None."""
        result = await facade.apply_confirmation(
            FLOW_ID,
            ValueFlowStep.completion,
            action="confirm",
            rationale=None,
            metadata={},
        )
        assert result["accepted"] is True
        assert result["next_step"] is None


# ---------------------------------------------------------------------------
# completion_status
# ---------------------------------------------------------------------------

class TestCompletionStatus:
    """Tests for completion_status."""

    @pytest.mark.asyncio
    async def test_empty_flow_is_not_complete(self, facade):
        """A flow with no steps saved is not complete."""
        status = await facade.completion_status("new-flow-xyz")
        assert status["is_complete"] is False
        assert status["completed_steps"] == []

    @pytest.mark.asyncio
    async def test_is_complete_when_completion_step_saved(self, facade):
        """Flow is complete only when ValueFlowStep.completion is saved."""
        for step in ValueFlowStep:
            await facade.save_step_state(FLOW_ID, step, {}, idempotency_key=None)

        status = await facade.completion_status(FLOW_ID)
        assert status["is_complete"] is True

    @pytest.mark.asyncio
    async def test_completed_steps_listed(self, facade):
        """completed_steps includes all steps that have been saved."""
        await facade.save_step_state(FLOW_ID, ValueFlowStep.setup, {}, idempotency_key=None)
        await facade.save_step_state(FLOW_ID, ValueFlowStep.model, {}, idempotency_key=None)

        status = await facade.completion_status(FLOW_ID)
        step_values = [s.value for s in status["completed_steps"]]
        assert "setup" in step_values
        assert "model" in step_values


# ---------------------------------------------------------------------------
# _adapt_step_data
# ---------------------------------------------------------------------------

class TestAdaptStepData:
    """Tests for _adapt_step_data internal method."""

    def test_intelligence_step_exposes_summary(self, facade):
        """Intelligence step adapter exposes 'summary' key."""
        adapted = facade._adapt_step_data(
            ValueFlowStep.intelligence,
            {"summary": "key insight", "other": "data"},
        )
        assert adapted["summary"] == "key insight"

    def test_intelligence_step_falls_back_to_insights(self, facade):
        """If summary absent, 'insights' list is used."""
        adapted = facade._adapt_step_data(
            ValueFlowStep.intelligence,
            {"insights": ["a", "b"]},
        )
        assert adapted["summary"] == ["a", "b"]

    def test_model_step_exposes_model_card(self, facade):
        """Model step adapter exposes 'model_card' key."""
        adapted = facade._adapt_step_data(
            ValueFlowStep.model,
            {"model_card": {"name": "roi-v1"}},
        )
        assert adapted["model_card"] == {"name": "roi-v1"}

    def test_base_fields_always_present(self, facade):
        """All adapted results include 'view' and 'payload'."""
        adapted = facade._adapt_step_data(ValueFlowStep.setup, {"k": "v"})
        assert adapted["view"] == "setup"
        assert adapted["payload"] == {"k": "v"}


# ---------------------------------------------------------------------------
# _next_step
# ---------------------------------------------------------------------------

class TestNextStep:
    """Tests for _next_step progression."""

    def test_setup_next_is_intelligence(self, facade):
        assert facade._next_step(ValueFlowStep.setup) == ValueFlowStep.intelligence

    def test_intelligence_next_is_model(self, facade):
        assert facade._next_step(ValueFlowStep.intelligence) == ValueFlowStep.model

    def test_completion_next_is_none(self, facade):
        """Final step has no successor."""
        assert facade._next_step(ValueFlowStep.completion) is None
