from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import UUID

import pytest

import layer4_agents.services.context_gatherer as module
from layer4_agents.services.context_gatherer import (
    ContextGatheringService,
    _hypothesis_dedup_key,
)

ACCOUNT_ID = "5f7ed580-763c-4adb-9b4d-4c79e5152548"
TENANT = "550e8400-e29b-41d4-a716-446655440000"


def test_hypothesis_dedup_key_prefers_id_and_has_stable_fallback() -> None:
    assert _hypothesis_dedup_key({"id": "h1", "hypothesis_text": "ignored"}) == "id:h1"
    value = {"hypothesis_text": "Text", "status": "draft", "confidence_score": 0.8}
    assert _hypothesis_dedup_key(value) == _hypothesis_dedup_key(dict(value))
    assert _hypothesis_dedup_key(value)[0] == "fallback"


@pytest.mark.asyncio
async def test_gather_without_account_and_complete_parallel_result() -> None:
    svc = ContextGatheringService()
    assert await svc.gather(account_id=None, tenant_id=TENANT) == {"tenant_id": TENANT}

    async def parallel(**kwargs):
        assert kwargs == {"account_id": ACCOUNT_ID, "tenant_id": TENANT, "industry": "software"}
        return {"name": "Acme"}, [{"id": "s"}], [{"id": "h"}], {"total": 1}

    svc._gather_parallel = parallel
    result = await svc.gather(account_id=ACCOUNT_ID, tenant_id=TENANT, industry="software")
    assert result == {
        "tenant_id": TENANT,
        "account": {"name": "Acme"},
        "signals": [{"id": "s"}],
        "hypotheses": [{"id": "h"}],
        "evidence": {"total": 1},
    }


@pytest.mark.asyncio
async def test_gather_parallel_degrades_independent_failures() -> None:
    svc = ContextGatheringService()

    async def account(*_args):
        raise RuntimeError("account")

    async def signals(*_args):
        return [{"id": "s"}]

    async def hypotheses(*_args):
        raise RuntimeError("hypothesis")

    async def evidence(*_args):
        return {"total": 1}

    svc._get_account_summary = account
    svc._get_account_signals = signals
    svc._get_account_hypotheses = hypotheses
    svc._get_evidence_summary = evidence
    assert await svc._gather_parallel(account_id=ACCOUNT_ID, tenant_id=TENANT, industry=None) == (
        None,
        [{"id": "s"}],
        [],
        {"total": 1},
    )


@pytest.mark.asyncio
async def test_account_summary_maps_fields_missing_errors_and_cancel(monkeypatch) -> None:
    account = SimpleNamespace(
        id=UUID(ACCOUNT_ID),
        name="Acme",
        industry="software",
        region="NA",
        company_size=100,
        annual_revenue=1000,
        headquarters="NYC",
        website="https://acme.test",
        stage="customer",
        segment="enterprise",
        owner_name="Owner",
    )
    calls = []

    class AccountService:
        def __init__(self, db):
            calls.append(db)

        async def get_account(self, account_id, *, tenant_id):
            assert account_id == UUID(ACCOUNT_ID) and tenant_id == TENANT
            return account

    monkeypatch.setattr("layer4_agents.services.account_service.AccountService", AccountService)
    db = object()
    result = await ContextGatheringService(db=db)._get_account_summary(ACCOUNT_ID, TENANT)
    assert result["name"] == "Acme" and result["id"] == ACCOUNT_ID and calls == [db]
    assert await ContextGatheringService()._get_account_summary(ACCOUNT_ID, TENANT) is None

    class Missing(AccountService):
        async def get_account(self, *_args, **_kwargs):
            return None

    monkeypatch.setattr("layer4_agents.services.account_service.AccountService", Missing)
    assert await ContextGatheringService(db=db)._get_account_summary(ACCOUNT_ID, TENANT) is None
    assert await ContextGatheringService(db=db)._get_account_summary("bad-uuid", TENANT) is None

    class Cancel(AccountService):
        async def get_account(self, *_args, **_kwargs):
            raise asyncio.CancelledError

    monkeypatch.setattr("layer4_agents.services.account_service.AccountService", Cancel)
    with pytest.raises(asyncio.CancelledError):
        await ContextGatheringService(db=db)._get_account_summary(ACCOUNT_ID, TENANT)


@pytest.mark.asyncio
async def test_signal_mapping_tenant_params_failures_and_cancel(monkeypatch) -> None:
    calls = []
    values = [
        [
            {
                "signal": {
                    "id": "s1",
                    "name": "Signal",
                    "category": "pain",
                    "confidence_score": 0.9,
                    "description": "Description",
                }
            },
            {"signal": None},
        ],
        RuntimeError("offline"),
        asyncio.CancelledError(),
    ]

    async def query(**kwargs):
        calls.append(kwargs)
        value = values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(module, "run_tenant_validated_query", query)
    svc = ContextGatheringService(neo4j_driver=object())
    result = await svc._get_account_signals(ACCOUNT_ID, TENANT)
    assert result == [
        {
            "id": "s1",
            "name": "Signal",
            "category": "pain",
            "confidence": 0.9,
            "impact": "Description",
            "status": "unreviewed",
        }
    ]
    assert calls[0]["tenant_id"] == TENANT and calls[0]["params"]["limit"] == module.MAX_SIGNALS
    assert await svc._get_account_signals(ACCOUNT_ID, TENANT) == []
    with pytest.raises(asyncio.CancelledError):
        await svc._get_account_signals(ACCOUNT_ID, TENANT)
    assert await ContextGatheringService()._get_account_signals(ACCOUNT_ID, TENANT) == []


@pytest.mark.asyncio
async def test_hypothesis_mapping_failures_and_cancel(monkeypatch) -> None:
    values = [
        [
            {
                "hypothesis": {
                    "id": "h1",
                    "hypothesis_text": "Reduce cost",
                    "status": "draft",
                    "confidence_score": 0.8,
                    "value_path_category": "efficiency",
                    "estimated_impact_usd": 1000,
                    "capability_name": "Automation",
                    "signal_name": "Backlog",
                }
            },
            {},
        ],
        RuntimeError("offline"),
        asyncio.CancelledError(),
    ]

    async def query(**_kwargs):
        value = values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(module, "run_tenant_validated_query", query)
    svc = ContextGatheringService(neo4j_driver=object())
    result = await svc._get_account_hypotheses(ACCOUNT_ID, TENANT)
    assert result[0]["text"] == "Reduce cost" and result[0]["capability"] == "Automation"
    assert await svc._get_account_hypotheses(ACCOUNT_ID, TENANT) == []
    with pytest.raises(asyncio.CancelledError):
        await svc._get_account_hypotheses(ACCOUNT_ID, TENANT)
    assert await ContextGatheringService()._get_account_hypotheses(ACCOUNT_ID, TENANT) == []


@pytest.mark.asyncio
async def test_evidence_summary_industry_defaults_empty_errors_and_cancel(monkeypatch) -> None:
    calls = []
    values = [
        [{"total": 2, "avg_deal_size": 1234.567, "avg_ttv": 45.6}],
        [{"total": None, "avg_deal_size": None, "avg_ttv": None}],
        [],
        RuntimeError("offline"),
        asyncio.CancelledError(),
    ]

    async def query(**kwargs):
        calls.append(kwargs)
        value = values.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    monkeypatch.setattr(module, "run_tenant_validated_query", query)
    svc = ContextGatheringService(neo4j_driver=object())
    result = await svc._get_evidence_summary("software", TENANT)
    assert result == {
        "total_case_studies": 2,
        "avg_deal_size": 1234.57,
        "avg_time_to_value_days": 46.0,
    }
    assert calls[0]["params"] == {"industry": "software"} and "e.industry" in calls[0]["query"]
    assert await svc._get_evidence_summary(None, TENANT) == {
        "total_case_studies": 0,
        "avg_deal_size": 0,
        "avg_time_to_value_days": 180,
    }
    assert calls[1]["params"] == {} and "e.industry =" not in calls[1]["query"]
    assert await svc._get_evidence_summary(None, TENANT) is None
    assert await svc._get_evidence_summary(None, TENANT) is None
    with pytest.raises(asyncio.CancelledError):
        await svc._get_evidence_summary(None, TENANT)
    assert await ContextGatheringService()._get_evidence_summary(None, TENANT) is None
