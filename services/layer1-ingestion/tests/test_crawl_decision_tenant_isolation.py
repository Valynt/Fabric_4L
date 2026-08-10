import uuid
from datetime import UTC, datetime

import pytest

from layer1_ingestion.crawler.decision_store import (
    CrawlDecisionRecord,
    InMemoryCrawlDecisionRepository,
)


def _make_record(
    tenant_id: str,
    decision_id: str | None = None,
    job_id: str | None = None,
    url: str = "https://example.com/page",
    domain: str = "example.com",
) -> CrawlDecisionRecord:
    return CrawlDecisionRecord(
        decision_id=decision_id or str(uuid.uuid4()),
        job_id=job_id or str(uuid.uuid4()),
        tenant_id=tenant_id,
        url=url,
        domain=domain,
        requested_path="/page",
        router_decision="crawl",
        router_rule="default",
        quality_passed=True,
        quality_checks={},
        fallback_reason=None,
        final_path="fast",
        status_code=200,
        fast_duration_ms=10,
        browser_duration_ms=None,
        fetch_time_ms=10,
        bytes_transferred=100,
        spa_detected=False,
        text_length=50,
        created_at=datetime.now(UTC),
    )


@pytest.fixture
def repo():
    return InMemoryCrawlDecisionRepository()


@pytest.mark.asyncio
async def test_get_by_id_requires_tenant(repo):
    with pytest.raises(TypeError):
        await repo.get_by_id(str(uuid.uuid4()))


@pytest.mark.asyncio
async def test_get_by_id_filters_by_tenant(repo):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    record_a = _make_record(tenant_a)
    record_b = _make_record(tenant_b)

    await repo.save(record_a)
    await repo.save(record_b)

    assert await repo.get_by_id(record_a.decision_id, tenant_id=tenant_a) is not None
    assert await repo.get_by_id(record_a.decision_id, tenant_id=tenant_b) is None


@pytest.mark.asyncio
async def test_get_by_job_filters_by_tenant(repo):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    job_id = str(uuid.uuid4())
    record_a = _make_record(tenant_a, job_id=job_id)
    record_b = _make_record(tenant_b, job_id=job_id)

    await repo.save(record_a)
    await repo.save(record_b)

    results = await repo.get_by_job(job_id, tenant_id=tenant_a)
    assert len(results) == 1
    assert results[0].tenant_id == tenant_a


@pytest.mark.asyncio
async def test_get_by_url_filters_by_tenant(repo):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    url = "https://example.com/page"
    record_a = _make_record(tenant_a, url=url)
    record_b = _make_record(tenant_b, url=url)

    await repo.save(record_a)
    await repo.save(record_b)

    results = await repo.get_by_url(url, tenant_id=tenant_a)
    assert len(results) == 1
    assert results[0].tenant_id == tenant_a


@pytest.mark.asyncio
async def test_get_by_domain_filters_by_tenant(repo):
    tenant_a = str(uuid.uuid4())
    tenant_b = str(uuid.uuid4())
    domain = "example.com"
    record_a = _make_record(tenant_a, domain=domain)
    record_b = _make_record(tenant_b, domain=domain)

    await repo.save(record_a)
    await repo.save(record_b)

    results = await repo.get_by_domain(domain, tenant_id=tenant_a)
    assert len(results) == 1
    assert results[0].tenant_id == tenant_a
