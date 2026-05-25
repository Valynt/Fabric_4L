"""Tests for tenant LLM budget guardrails."""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from value_fabric.layer4.services.llm_budget_guardrails import LLMBudgetExceededError, LLMBudgetGuardrails


def test_precheck_blocks_when_hard_cap_exceeded(mock_tenant_context):
    guardrails = LLMBudgetGuardrails()
    guardrails.hourly_cap_usd = 1.0
    guardrails.daily_cap_usd = 10.0
    tenant_id = "test-tenant-001"
    guardrails._usage_events[tenant_id] = [(datetime.now(UTC), 1.1)]

    with pytest.raises(LLMBudgetExceededError):
        asyncio.run(guardrails.precheck_or_raise(model="gpt-4o"))


def test_precheck_returns_throttle_near_soft_cap(mock_tenant_context):
    guardrails = LLMBudgetGuardrails()
    guardrails.hourly_cap_usd = 100.0
    guardrails.daily_cap_usd = 1000.0
    guardrails.soft_threshold_ratio = 0.8
    guardrails.throttle_seconds = 3
    guardrails.fallback_model = "gpt-4o-mini"
    tenant_id = "test-tenant-001"
    guardrails._usage_events[tenant_id] = [(datetime.now(UTC), 85.0)]

    decision = asyncio.run(guardrails.precheck_or_raise(model="gpt-4o"))

    assert decision.model == "gpt-4o-mini"
    assert decision.throttle_seconds == 3
    assert decision.escalation_required is True


def test_record_usage_and_prune_old_events(mock_tenant_context):
    guardrails = LLMBudgetGuardrails()
    tenant_id = "test-tenant-001"
    guardrails._usage_events[tenant_id] = [
        (datetime.now(UTC) - timedelta(days=2), 5.0),
    ]

    asyncio.run(guardrails.record_usage(cost_usd=2.5))

    assert len(guardrails._usage_events[tenant_id]) == 1
    assert guardrails._usage_events[tenant_id][0][1] == 2.5
