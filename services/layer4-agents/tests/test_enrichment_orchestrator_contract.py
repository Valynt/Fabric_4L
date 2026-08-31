from __future__ import annotations

from types import SimpleNamespace
from uuid import UUID

import httpx
import pytest
from value_fabric.shared.security.dil_auth import SSRFBlockedError

import layer4_agents.services.enrichment_orchestrator as module
from layer4_agents.services.enrichment_orchestrator import (
    EnrichmentOrchestrator,
    EnrichmentSource,
    EnrichmentStatus,
)

TENANT_ID = "550e8400-e29b-41d4-a716-446655440000"

ACCOUNT_ID = UUID("550e8400-e29b-41d4-a716-446655440000")


class Result:
    def __init__(self, rows=()):
        self.rows = list(rows)

    def fetchall(self):
        return self.rows


class DB:
    def __init__(self, account=None, results=()):
        self.account = account
        self.results = list(results)
        self.flushes = self.commits = 0

    async def get(self, *_args):
        return self.account

    async def execute(self, _query):
        return self.results.pop(0)

    async def flush(self):
        self.flushes += 1

    async def commit(self):
        self.commits += 1


def account(**values):
    defaults = {
        "id": ACCOUNT_ID,
        "name": "Example, Inc.",
        "annual_revenue": 20_000_000,
        "website": "https://example.test",
        "domain": "example.test",
        "financials": {},
        "tech_stack": {},
        "enrichment_status": EnrichmentStatus.PENDING,
        "enriched_at": None,
        "enrichment_sources": [],
    }
    defaults.update(values)
    return SimpleNamespace(**defaults)


@pytest.mark.asyncio
async def test_account_enrichment_missing_skipped_success_and_failure(monkeypatch) -> None:
    missing = await EnrichmentOrchestrator(DB()).enrich_account(ACCOUNT_ID)
    assert missing.status == "error" and "not found" in missing.message

    existing = account(enrichment_status=EnrichmentStatus.ENRICHED)
    skipped = await EnrichmentOrchestrator(DB(existing)).enrich_account(ACCOUNT_ID)
    assert skipped.status == "skipped"

    service = EnrichmentOrchestrator(DB(existing))
    outcomes = {
        EnrichmentSource.SEC_EDGAR: {"success": True},
        EnrichmentSource.NEWS_SCAN: RuntimeError("secret"),
    }

    async def enrich(_account, source):
        value = outcomes[source]
        if isinstance(value, Exception):
            raise value
        return value

    monkeypatch.setattr(service, "_enrich_from_source", enrich)
    result = await service.enrich_account(
        ACCOUNT_ID, [EnrichmentSource.SEC_EDGAR, EnrichmentSource.NEWS_SCAN], force=True
    )
    assert result.status == EnrichmentStatus.ENRICHED
    assert result.sources_used == ["sec_edgar"] and result.errors == ["news_scan: ENRICHMENT_ERROR"]
    assert service.db.commits == 1

    service = EnrichmentOrchestrator(DB(account()))
    monkeypatch.setattr(service, "_enrich_from_source", lambda *_args: _raise_async(RuntimeError()))
    failed = await service.enrich_account(ACCOUNT_ID, [EnrichmentSource.NEWS_SCAN])
    assert failed.status == EnrichmentStatus.FAILED


@pytest.mark.asyncio
async def test_batch_status_sources_and_dependency(monkeypatch) -> None:
    service = EnrichmentOrchestrator(DB(results=[Result([])]))
    assert (await service.enrich_batch(TENANT_ID)).status == "no_accounts"

    service.db.results = [Result([(ACCOUNT_ID,), (UUID(int=2),)])]
    calls = []

    async def enrich(account_id, force=False):
        calls.append((account_id, force))
        if account_id.int == 2:
            raise RuntimeError("failed")
        return {"status": EnrichmentStatus.ENRICHED}

    monkeypatch.setattr(service, "enrich_account", enrich)
    result = await service.enrich_batch(TENANT_ID, force=True)
    assert result.total == 2 and result.success == 1 and result.failed == 1

    service.db.results = [
        Result(
            [
                (EnrichmentStatus.ENRICHED, 3),
                (EnrichmentStatus.FAILED, 1),
            ]
        )
    ]
    status = await service.get_enrichment_status(TENANT_ID)
    assert status.total_accounts == 4 and status.coverage_pct == 75.0

    all_sources = service._determine_sources(account())
    # CARGO is only emitted when an intelligence provider is configured;
    # this service has none, so the legacy four are expected.
    assert set(all_sources) == set(EnrichmentSource) - {EnrichmentSource.CARGO}
    assert (
        service._determine_sources(account(name="", annual_revenue=0, website=None, domain=None))
        == []
    )
    assert isinstance(await module.get_enrichment_orchestrator(service.db), EnrichmentOrchestrator)


@pytest.mark.asyncio
async def test_domain_news_and_dispatch_fail_closed(monkeypatch) -> None:
    service = EnrichmentOrchestrator(DB())
    assert not (await service._enrich_from_domain(account(domain=None))).success
    assert not (await service._enrich_from_news(account(name=""))).success
    monkeypatch.delenv("ENRICHMENT_MOCK_MODE", raising=False)
    assert (
        await service._enrich_from_domain(account())
    ).error == "domain_enrichment_not_configured"
    assert (await service._enrich_from_news(account())).error == "news_enrichment_not_configured"
    monkeypatch.setenv("ENRICHMENT_MOCK_MODE", "true")
    assert (await service._enrich_from_domain(account())).success
    assert (await service._enrich_from_news(account())).success

    assert (await service._enrich_from_source(account(), EnrichmentSource.DOMAIN_LOOKUP)).success
    unknown = await service._enrich_from_source(account(), "unknown")
    assert not unknown.success and "Unknown source" in unknown.error


class Response:
    def __init__(self, *, data=None, text="", status=200):
        self.data = data or {}
        self.text = text
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            request = httpx.Request("GET", "https://example.test")
            raise httpx.HTTPStatusError(
                "bad", request=request, response=httpx.Response(self.status_code)
            )

    def json(self):
        return self.data


class Client:
    def __init__(self, responses=()):
        self.responses = list(responses)
        self.is_closed = False

    async def get(self, *_args, **_kwargs):
        value = self.responses.pop(0)
        if isinstance(value, BaseException):
            raise value
        return value

    async def aclose(self):
        self.is_closed = True


@pytest.mark.asyncio
async def test_sec_and_web_source_contracts(monkeypatch) -> None:
    value = account()
    client = Client(
        [
            Response(data={"hits": {"hits": []}}),
            Response(
                data={
                    "hits": {
                        "hits": [
                            {
                                "_source": {
                                    "file_date": "2025-01-01",
                                    "entity_name": "Example",
                                    "period_of_report": "2024",
                                }
                            }
                        ]
                    }
                }
            ),
            Response(text="reactDOM js.stripe.com cloudflare.com"),
        ]
    )
    service = EnrichmentOrchestrator(DB())
    service._http_client = client
    assert not (await service._enrich_from_sec_edgar(value)).success
    sec = await service._enrich_from_sec_edgar(value)
    assert sec.success and value.financials["source"] == "sec_edgar"
    monkeypatch.setattr(module, "validate_url_safe", lambda _url: None)
    web = await service._enrich_from_web_crawl(value)
    assert web.success and web.technologies_found == 3
    assert set(value.tech_stack) == {"frontend", "ecommerce", "infrastructure"}
    await service.close()
    assert client.is_closed

    assert not (await service._enrich_from_web_crawl(account(website=None, domain=None))).success
    monkeypatch.setattr(
        module,
        "validate_url_safe",
        lambda _url: _raise(SSRFBlockedError("blocked", reason="private")),
    )
    blocked = await service._enrich_from_web_crawl(account(website="http://127.0.0.1"))
    assert not blocked.success and "security policy" in blocked.error


def test_tech_detection_deduplicates_signatures() -> None:
    detected = EnrichmentOrchestrator(DB())._detect_tech_stack(
        "google-analytics.com gtag/js reactDOM react.production.min"
    )
    assert detected == {"analytics": ["Google Analytics"], "frontend": ["React"]}


async def _raise_async(error):
    raise error


def _raise(error):
    raise error
