from __future__ import annotations

import asyncio
from types import SimpleNamespace
from uuid import uuid4

import pytest

from layer4_agents.models.company_knowledge import (
    CrawlStatus,
    ProfileStatus,
    ReviewStatus,
    SourceType,
)
from layer4_agents.services.company_knowledge_service import CompanyKnowledgeService


class Result:
    def __init__(self, *, scalar=None, values=()):
        self.value = scalar
        self.values = list(values)

    def scalar_one_or_none(self):
        return self.value

    def scalar(self):
        return self.value

    def scalars(self):
        return SimpleNamespace(all=lambda: self.values)


class DB:
    def __init__(self, results=()):
        self.results = list(results)
        self.added = []
        self.commits = 0
        self.refreshed = []
        self.queries = []

    def add(self, value):
        self.added.append(value)

    async def commit(self):
        self.commits += 1

    async def refresh(self, value):
        self.refreshed.append(value)

    async def execute(self, query):
        self.queries.append(query)
        return self.results.pop(0) if self.results else Result()


def profile(**overrides):
    values = {
        "id": uuid4(),
        "tenant_id": "tenant",
        "company_name": "Acme",
        "website": "https://acme.test",
        "status": ProfileStatus.DRAFT.value,
        "version": 1,
        "active_source_ids": [],
        "identity": {},
        "product_catalog": {},
        "personas": {},
        "use_cases": {},
        "value_drivers": {},
    }
    values.update(overrides)
    return SimpleNamespace(**values)


def source(**overrides):
    values = {
        "id": uuid4(),
        "profile_id": uuid4(),
        "tenant_id": "tenant",
        "source_url": "https://acme.test",
        "page_type": "home",
        "extra_metadata": {},
        "crawl_status": CrawlStatus.PENDING.value,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


@pytest.mark.asyncio
async def test_profile_crud_and_state_transitions() -> None:
    db = DB(
        [
            Result(scalar=None),
            Result(scalar=profile()),
            Result(values=[profile()]),
            Result(scalar=1),
        ]
    )
    service = CompanyKnowledgeService(db)
    created = await service.create_profile("tenant", "Acme", "https://acme.test")
    assert created.company_name == "Acme"
    assert await service.get_profile(uuid4(), "tenant") is None
    assert (await service.get_active_profile("tenant")).company_name == "Acme"
    listed, total = await service.list_profiles("tenant", ProfileStatus.DRAFT, page=2, page_size=5)
    assert len(listed) == 1 and total == 1

    current = profile()

    async def get_profile(*_args):
        return current

    service.get_profile = get_profile
    updated = await service.update_profile(
        current.id, "tenant", {"company_name": "New", "bad": "x", "website": None}
    )
    assert updated.company_name == "New" and not hasattr(updated, "bad")
    approved = await service.approve_profile(current.id, "tenant", uuid4())
    assert approved.status == ProfileStatus.APPROVED.value and approved.version == 2
    assert await service.approve_profile(current.id, "tenant", uuid4()) is current
    archived = await service.archive_profile(current.id, "tenant")
    assert archived.status == ProfileStatus.ARCHIVED.value

    async def missing(*_args):
        return None

    service.get_profile = missing
    assert await service.update_profile(uuid4(), "tenant", {}) is None
    assert await service.approve_profile(uuid4(), "tenant", uuid4()) is None
    assert await service.archive_profile(uuid4(), "tenant") is None


@pytest.mark.asyncio
async def test_active_profile_falls_back_to_latest_draft() -> None:
    draft = profile()
    service = CompanyKnowledgeService(DB([Result(scalar=None), Result(scalar=draft)]))
    assert await service.get_active_profile("tenant") is draft


@pytest.mark.asyncio
async def test_source_crud_filters_and_status_updates() -> None:
    parent = profile()
    db = DB(
        [
            Result(scalar=parent),
            Result(scalar=source()),
            Result(values=[source()]),
            Result(scalar=2),
        ]
    )
    service = CompanyKnowledgeService(db)
    added = await service.add_knowledge_source(
        "tenant",
        parent.id,
        SourceType.WEBSITE,
        source_url="https://acme.test",
        authority_weight="high",
        page_type="home",
        extra_metadata={"source": "manual"},
    )
    assert added.crawl_status == CrawlStatus.PENDING.value
    assert parent.active_source_ids
    assert await service.get_knowledge_source(uuid4(), "tenant") is not None
    listed, total = await service.list_knowledge_sources(
        "tenant", parent.id, SourceType.WEBSITE, page=2, page_size=5
    )
    assert len(listed) == 1 and total == 2

    current = source(extra_metadata={"old": 1})

    async def get_source(*_args):
        return current

    service.get_knowledge_source = get_source
    updated = await service.update_crawl_status(
        current.id, "tenant", CrawlStatus.COMPLETE, {"new": 2}
    )
    assert updated.extra_metadata == {"old": 1, "new": 2}

    async def missing(*_args):
        return None

    service.get_knowledge_source = missing
    assert await service.update_crawl_status(uuid4(), "tenant", CrawlStatus.FAILED) is None


@pytest.mark.asyncio
async def test_extraction_crud_filters_and_review_transitions() -> None:
    db = DB(
        [
            Result(scalar=SimpleNamespace(id=uuid4())),
            Result(values=[SimpleNamespace(id=uuid4())]),
            Result(scalar=3),
        ]
    )
    service = CompanyKnowledgeService(db)
    created = await service.create_extraction_record(
        "tenant",
        uuid4(),
        uuid4(),
        {"drivers": []},
        confidence=0.8,
        requires_review=True,
        page_type="home",
        extraction_version="1",
        llm_model="model",
        trace_span_id="trace",
    )
    assert created.confidence == 0.8
    assert await service.get_extraction_record(uuid4(), "tenant") is not None
    records, total = await service.list_extraction_records(
        "tenant", uuid4(), uuid4(), 0.5, True, ReviewStatus.PENDING, 2, 5
    )
    assert len(records) == 1 and total == 3

    record = SimpleNamespace(
        extracted={"old": 1},
        requires_review=True,
        review_status=None,
        reviewed_by=None,
        reviewed_at=None,
        updated_at=None,
    )

    async def get_record(*_args):
        return record

    service.get_extraction_record = get_record
    reviewed = await service.review_extraction_record(
        uuid4(), "tenant", ReviewStatus.MODIFIED, uuid4(), {"new": 2}
    )
    assert reviewed.extracted == {"old": 1, "new": 2}
    assert reviewed.requires_review is False
    await service.review_extraction_record(uuid4(), "tenant", ReviewStatus.REJECTED, uuid4())

    async def missing(*_args):
        return None

    service.get_extraction_record = missing
    assert (
        await service.review_extraction_record(uuid4(), "tenant", ReviewStatus.ACCEPTED, uuid4())
        is None
    )


@pytest.mark.asyncio
async def test_icp_crud_and_update_allowlist() -> None:
    db = DB(
        [Result(scalar=SimpleNamespace(id=uuid4())), Result(scalar=SimpleNamespace(id=uuid4()))]
    )
    service = CompanyKnowledgeService(db)
    created = await service.create_icp_profile(
        "tenant",
        uuid4(),
        ["SaaS"],
        ["enterprise"],
        [{"role": "CFO"}],
        [],
        ["cost"],
        ["growth"],
        ["fit"],
        ["regulated"],
        competitive_context={"x": 1},
        buying_committee_structure={"roles": []},
        typical_sales_motion="enterprise",
        confidence=0.8,
    )
    assert created.industries == ["SaaS"]
    assert await service.get_icp_profile(uuid4(), "tenant") is not None
    assert await service.get_icp_for_profile(uuid4(), "tenant") is not None

    current = SimpleNamespace(industries=["old"], updated_at=None)

    async def get_icp(*_args):
        return current

    service.get_icp_profile = get_icp
    updated = await service.update_icp_profile(uuid4(), "tenant", {"industries": ["new"], "bad": 1})
    assert updated.industries == ["new"] and not hasattr(updated, "bad")

    async def missing(*_args):
        return None

    service.get_icp_profile = missing
    assert await service.update_icp_profile(uuid4(), "tenant", {}) is None


@pytest.mark.parametrize(
    ("current", "sources", "pending", "icp", "expected"),
    [
        (None, 0, 0, False, "Enter your company website"),
        (profile(status=ProfileStatus.APPROVED.value), 1, 0, True, "approved"),
        (profile(), 0, 0, False, "Add your company website"),
        (profile(), 1, 2, False, "Review 2 low-confidence extractions"),
        (profile(), 1, 0, False, "ideal customer profile"),
        (profile(), 1, 0, True, "Review your draft profile"),
        (profile(status="processing"), 1, 0, True, "Continue refining"),
    ],
)
def test_onboarding_next_step_matrix(current, sources, pending, icp, expected) -> None:
    assert expected in CompanyKnowledgeService(DB())._determine_next_step(
        current, sources, pending, icp
    )


@pytest.mark.asyncio
async def test_onboarding_status_aggregates_profile_counts() -> None:
    active = profile(status=ProfileStatus.APPROVED.value)
    service = CompanyKnowledgeService(
        DB(
            [
                Result(scalar=3),
                Result(scalar=4),
                Result(scalar=1),
                Result(scalar=2),
                Result(scalar=1),
                Result(scalar=0.75),
                Result(scalar=1),
            ]
        )
    )

    async def get_active(_tenant):
        return active

    service.get_active_profile = get_active
    result = await service.get_onboarding_status("tenant")
    assert result["sources_count"] == 3
    assert result["average_confidence"] == 0.75
    assert result["icp_present"] is True
    assert result["has_approved_profile"] is True


@pytest.mark.asyncio
async def test_pipeline_client_is_required() -> None:
    with pytest.raises(RuntimeError, match="not configured"):
        CompanyKnowledgeService(DB())._require_pipeline_client()


@pytest.mark.asyncio
async def test_layer1_crawl_success_failure_and_validation() -> None:
    src = source()

    class Pipeline:
        async def crawl_website(self, **kwargs):
            self.kwargs = kwargs
            return {"target_id": "target", "job_id": "job"}

    pipeline = Pipeline()
    service = CompanyKnowledgeService(DB(), pipeline)
    statuses = []

    async def get_source(*_args):
        return src

    async def update(**kwargs):
        statuses.append(kwargs)

    service.get_knowledge_source = get_source
    service.update_crawl_status = update
    result = await service.trigger_layer1_crawl(src.id, "tenant")
    assert result["job_id"] == "job"
    assert statuses[-1]["crawl_status"] == CrawlStatus.IN_PROGRESS

    async def fail(**_kwargs):
        raise RuntimeError("offline")

    pipeline.crawl_website = fail
    with pytest.raises(RuntimeError, match="offline"):
        await service.trigger_layer1_crawl(src.id, "tenant")
    assert statuses[-1]["crawl_status"] == CrawlStatus.FAILED

    service.get_knowledge_source = lambda *_args: None


@pytest.mark.asyncio
async def test_layer2_extraction_persists_record_and_status() -> None:
    src = source()

    class Pipeline:
        async def extract_value_attributes(self, **kwargs):
            self.kwargs = kwargs
            return {
                "extracted_entities": {"drivers": []},
                "confidence": 0.7,
                "extraction_version": "2",
                "model_version": "model",
                "job_id": "job",
            }

    service = CompanyKnowledgeService(DB(), Pipeline())
    service.get_knowledge_source = lambda *_args: asyncio.sleep(0, result=src)
    record = SimpleNamespace(id=uuid4())
    captured = {}

    async def create(**kwargs):
        captured.update(kwargs)
        return record

    async def update(**kwargs):
        captured["status"] = kwargs

    service.create_extraction_record = create
    service.update_crawl_status = update
    result = await service.trigger_layer2_extraction(src.id, "tenant", "content", "markdown")
    assert result["confidence"] == 0.7
    assert captured["requires_review"] is True
    assert captured["status"]["crawl_status"] == CrawlStatus.COMPLETE


@pytest.mark.asyncio
async def test_layer3_sync_builds_rdf_and_validates_contract() -> None:
    approved = profile(
        status=ProfileStatus.APPROVED.value,
        identity={"industry": "SaaS"},
        product_catalog={"products": [{"name": 'Product "One"'}]},
        personas={"personas": [{"name": "CFO"}]},
        use_cases={"use_cases": [{"name": "Planning"}]},
        value_drivers={"drivers": [{"name": "Growth"}]},
    )

    class Pipeline:
        async def ingest_profile(self, **kwargs):
            self.kwargs = kwargs
            return {
                "status": "completed",
                "source_id": kwargs["ingestion_payload"]["source_id"],
                "entities_loaded": 5,
                "relationships_loaded": 4,
                "triples_processed": 10,
            }

    pipeline = Pipeline()
    service = CompanyKnowledgeService(DB(), pipeline)
    service.get_profile = lambda *_args: asyncio.sleep(0, result=approved)
    result = await service.sync_profile_to_layer3(
        approved.id, "tenant", {"Authorization": "Bearer safe"}
    )
    assert result["entities_loaded"] == 5
    assert 'Product_\\"One\\"' in pipeline.kwargs["ingestion_payload"]["rdf_data"]
    assert pipeline.kwargs["passthrough_headers"]["Authorization"] == "Bearer safe"

    pipeline.ingest_profile = lambda **_kwargs: asyncio.sleep(0, result={"status": "bad"})
    with pytest.raises(ValueError, match="contract mismatch"):
        await service.sync_profile_to_layer3(approved.id, "tenant")


@pytest.mark.asyncio
async def test_pipeline_operations_propagate_cancellation() -> None:
    src = source()

    class Pipeline:
        async def crawl_website(self, **_kwargs):
            raise asyncio.CancelledError

        async def extract_value_attributes(self, **_kwargs):
            raise asyncio.CancelledError

    service = CompanyKnowledgeService(DB(), Pipeline())
    service.get_knowledge_source = lambda *_args: asyncio.sleep(0, result=src)
    with pytest.raises(asyncio.CancelledError):
        await service.trigger_layer1_crawl(src.id, "tenant")
    with pytest.raises(asyncio.CancelledError):
        await service.trigger_layer2_extraction(src.id, "tenant", "content", "markdown")
