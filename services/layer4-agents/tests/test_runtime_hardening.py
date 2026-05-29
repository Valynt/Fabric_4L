from __future__ import annotations

"""Runtime hardening regressions for production blocker closure."""


import asyncio
from types import SimpleNamespace
from uuid import uuid4

import layer4_agents.services.llm_budget_guardrails as budget_module
from layer4_agents.services.llm_budget_guardrails import LLMBudgetGuardrails
from layer4_agents.workflows.whitespace import ExtractedNeedsResponse


class FakeRedisPipeline:
    def __init__(self, store: dict[str, float]):
        self.store = store
        self.ops = []

    def incrbyfloat(self, key: str, amount: float) -> None:
        self.ops.append(("incrbyfloat", key, amount))

    def expire(self, key: str, ttl: int) -> None:
        self.ops.append(("expire", key, ttl))

    async def execute(self) -> None:
        for op in self.ops:
            if op[0] == "incrbyfloat":
                _, key, amount = op
                self.store[key] = self.store.get(key, 0.0) + amount


class FakeRedis:
    def __init__(self):
        self.store: dict[str, float] = {}

    async def mget(self, *keys):
        return [self.store.get(key) for key in keys]

    def pipeline(self):
        return FakeRedisPipeline(self.store)


def test_llm_budget_guardrails_use_redis_backend(monkeypatch):
    async def scenario():
        tenant_id = uuid4()
        monkeypatch.setattr(budget_module, "require_context", lambda: SimpleNamespace(tenant_id=tenant_id))
        redis = FakeRedis()
        guardrails = LLMBudgetGuardrails(redis_client=redis)

        await guardrails.record_usage(1.25)
        decision = await guardrails.precheck_or_raise("gpt-4o")

        assert redis.store
        assert decision.model == "gpt-4o"
        assert decision.throttle_seconds == 0

    asyncio.run(scenario())


def test_whitespace_llm_output_requires_structured_needs_schema():
    parsed = ExtractedNeedsResponse.model_validate_json(
        '{"needs":["Reduce invoice processing time"]}'
    )

    assert parsed.needs == ["Reduce invoice processing time"]
