from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID

import pytest

from layer4_agents.tenants.email_verification import EmailConfig, EmailVerificationService
from layer4_agents.tools.registry import ToolResult
from layer4_agents.workflows.whitespace import WhitespaceAnalysisWorkflow, _unwrap_tool_data

TENANT = UUID("550e8400-e29b-41d4-a716-446655440000")


class Registry:
    def __init__(self, outcomes=()):
        self.outcomes = list(outcomes)
        self.calls = []

    async def execute(self, name, payload):
        self.calls.append((name, payload))
        value = self.outcomes.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value


def workflow(registry=None):
    value = object.__new__(WhitespaceAnalysisWorkflow)
    value.tool_registry = registry or Registry()
    value.config = {}
    return value


def state(output_data=None):
    return SimpleNamespace(
        output_data=output_data or {}, whitespace_input=None, input_data={}, metadata={}
    )


def test_unwrap_basic_needs_similarity_and_provider(monkeypatch) -> None:
    assert _unwrap_tool_data(ToolResult.success({"value": 1})) == {"value": 1}
    assert _unwrap_tool_data({"value": 2}) == {"value": 2}
    assert _unwrap_tool_data(None) == {}
    service = workflow()
    needs = service._extract_needs_basic(
        "We need automated billing. A short note. Our challenge is reporting!"
    )
    assert needs == ["We need automated billing", "Our challenge is reporting"]
    assert service._extract_needs_basic("Plain long statement") == ["Plain long statement"]
    assert service._calculate_similarity("automated billing", "billing workflow") == 0.5
    assert service._calculate_similarity("", "billing") == 0
    monkeypatch.setenv("LAYER4_LLM_PROVIDER", "provider")
    assert service._resolve_provider_name() == "provider"


@pytest.mark.asyncio
async def test_capability_query_gap_matching_and_fallback() -> None:
    registry = Registry(
        [
            ToolResult.success(
                {
                    "results": [
                        {
                            "c.id": "cap",
                            "c.name": "Billing",
                            "c.description": "automated billing",
                            "c.category": "Finance",
                        }
                    ]
                }
            ),
            ToolResult.success({"results": [{"name": "Billing", "similarity_score": 0.8}]}),
            ToolResult.success({"results": [{"name": "Reporting", "similarity_score": 0.5}]}),
            ToolResult.success({"results": []}),
        ]
    )
    service = workflow(registry)
    capabilities = await service._execute_query_capabilities(state())
    assert capabilities.capability_count == 1 and capabilities.categories == ["Finance"]
    current = state(
        {
            "analyze_prospect": {
                "extracted_needs": ["automated billing", "reporting", "unknown need"]
            },
            "query_capabilities": {"capabilities": capabilities.capabilities},
        }
    )
    gaps = await service._execute_identify_gaps(current)
    assert [gap["gap_type"] for gap in gaps.gaps] == ["none", "coverage", "capability"]
    assert gaps.coverage_percentage == pytest.approx(100 / 3)

    no_needs = await service._execute_identify_gaps(state())
    assert no_needs.error == "No needs extracted"
    no_caps = await service._execute_identify_gaps(
        state({"analyze_prospect": {"extracted_needs": ["need"]}})
    )
    assert no_caps.error == "No capabilities available"

    fallback = workflow(Registry([RuntimeError("search unavailable")]))
    fallback_state = state(
        {
            "analyze_prospect": {"extracted_needs": ["automated billing"]},
            "query_capabilities": {
                "capabilities": [{"name": "Billing", "description": "automated billing"}]
            },
        }
    )
    assert (await fallback._execute_identify_gaps(fallback_state)).gaps[0]["gap_type"] == "none"


@pytest.mark.asyncio
async def test_opportunity_scoring_and_tool_dispatch(monkeypatch) -> None:
    service = workflow()
    assert (await service._execute_score_opportunity(state())).score == 0
    high = state(
        {
            "identify_gaps": {
                "gaps": [
                    {"impact": "high"},
                    {"impact": "high"},
                    {"impact": "medium"},
                ],
                "coverage_percentage": 20,
            }
        }
    )
    result = await service._execute_score_opportunity(high)
    assert result.score >= 70 and len(result.recommendations) >= 3
    medium = state(
        {
            "identify_gaps": {
                "gaps": [{"impact": "medium"}, {"impact": "medium"}],
                "coverage_percentage": 40,
            }
        }
    )
    assert (await service._execute_score_opportunity(medium)).assessment.startswith("Medium")
    low = state({"identify_gaps": {"gaps": [{"impact": "low"}], "coverage_percentage": 100}})
    assert (await service._execute_score_opportunity(low)).assessment.startswith("Lower")

    for name, method, marker in [
        ("analyze_prospect_needs", "_execute_analyze_prospect", "analyze"),
        ("query_graph", "_execute_query_capabilities", "query"),
        ("identify_gaps", "_execute_identify_gaps", "gaps"),
        ("score_opportunity", "_execute_score_opportunity", "score"),
        ("generate_hypotheses", "_execute_llm_hypotheses", "llm"),
    ]:
        monkeypatch.setattr(service, method, lambda _state, value=marker: _value({"path": value}))
        assert await service._execute_tool(name, state(), {}) == {"path": marker}


class Redis:
    def __init__(self):
        self.values = {}

    def setex(self, key, _expiry, value):
        self.values[key] = value

    def get(self, key):
        return self.values.get(key)


def test_email_config_and_token_generation(monkeypatch) -> None:
    monkeypatch.setenv("SMTP_PORT", "invalid")
    assert EmailConfig.from_env().smtp_port == 587
    with pytest.raises(ValueError, match="SMTP port"):
        EmailConfig(smtp_port=0)
    redis = Redis()
    service = EmailVerificationService(redis, token_expiry_hours=1000)
    assert service.token_expiry_hours == 168
    token = service.generate_token(TENANT, "user@example.test")
    stored = json.loads(redis.values[f"email_verification:{token}"])
    assert stored["tenant_id"] == str(TENANT) and not stored["used"]


@pytest.mark.asyncio
async def test_token_verification_and_consumption() -> None:
    assert await EmailVerificationService().verify_token("missing") is None
    redis = Redis()
    service = EmailVerificationService(redis)
    redis.values["email_verification:bad"] = "not json"
    assert await service.verify_token("bad") is None
    redis.values["email_verification:used"] = json.dumps({"used": True})
    assert await service.verify_token("used") is None
    redis.values["email_verification:expired"] = json.dumps(
        {
            "tenant_id": str(TENANT),
            "email": "user@example.test",
            "expires": (datetime.now(UTC) - timedelta(hours=1)).isoformat(),
            "used": False,
        }
    )
    assert await service.verify_token("expired") is None
    token = service.generate_token(TENANT, "user@example.test")
    verified = await service.verify_token(token)
    assert verified.tenant_id == TENANT and verified.email == "user@example.test"
    await service.mark_token_used(token)
    assert await service.verify_token(token) is None
    await EmailVerificationService().mark_token_used(token)


@pytest.mark.asyncio
async def test_email_provider_routing_and_development_fallback(monkeypatch) -> None:
    service = EmailVerificationService()
    service.config = EmailConfig(environment="production")
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    assert not await service.send_verification_email("to@test", "Tenant", "token")
    monkeypatch.setenv("ENVIRONMENT", "development")
    assert await service.send_verification_email("to@test", "Tenant", "token")

    service.config = EmailConfig(sendgrid_api_key="key")
    monkeypatch.setattr(service, "_send_sendgrid", lambda *_args: _value(True))
    assert await service.send_verification_email("to@test", "Tenant", "token")
    service.config = EmailConfig(smtp_host="smtp.test")
    monkeypatch.setattr(service, "_send_smtp", lambda *_args: _value(True))
    assert await service.send_verification_email("to@test", "Tenant", "token")


async def _value(value):
    return value
