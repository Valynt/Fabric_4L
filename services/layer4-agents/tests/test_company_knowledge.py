"""Tests for Company Knowledge Onboarding API and service layer.

Covers:
- Service layer CRUD with mocked database
- API endpoint integration with PostgreSQL testcontainer
- Tenant isolation enforcement
- Pipeline integration stubs (Layer 1/2/3 clients mocked)
"""

from __future__ import annotations

import sys
from pathlib import Path

_tests_dir = Path(__file__).parent.resolve()
_layer4_dir = _tests_dir.parent.resolve()
_repo_root = _layer4_dir.parent.parent.resolve()
if str(_repo_root) not in sys.path:
    sys.path.insert(0, str(_repo_root))

from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from testcontainers.postgres import PostgresContainer

from fastapi import FastAPI
from value_fabric.layer4.api.routes import company_knowledge as company_knowledge_route
from value_fabric.layer4.database import get_db_from_context, _mark_session_tenant_context
from value_fabric.layer4.models.company_knowledge import (
    CompanyKnowledgeProfile,
    ICPProfile,
    KnowledgeSource,
    ValueExtractionRecord,
)
from value_fabric.layer4.models.company_knowledge import (
    CompanyKnowledgeProfile,
    CrawlStatus,
    ICPProfile,
    KnowledgeSource,
    ProfileStatus,
    ReviewStatus,
    SourceType,
    ValueExtractionRecord,
)
from value_fabric.layer4.services.company_knowledge_service import CompanyKnowledgeService
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated

pytestmark = [
    pytest.mark.integration,
    pytest.mark.requires_postgres,
]


# ──────────────────────────────────────────────────────────────────────────────
# Integration Test Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(scope="session")
def postgres_container():
    """Start PostgreSQL container for test session."""
    with PostgresContainer("postgres:16-alpine") as postgres:
        yield postgres


@pytest_asyncio.fixture(scope="function")
async def test_db(postgres_container, tenant_id: str) -> AsyncSession:
    """Create a test database session with fresh tables."""
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    username = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname

    test_database_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{dbname}"

    engine = create_async_engine(test_database_url, echo=False)

    # Only create tables needed for company knowledge tests to avoid
    # cross-package foreign key issues with models not imported in this test.
    _test_tables = [
        CompanyKnowledgeProfile.__table__,
        KnowledgeSource.__table__,
        ValueExtractionRecord.__table__,
        ICPProfile.__table__,
    ]

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: [t.create(sync_conn, checkfirst=True) for t in _test_tables])

    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        # Mark session with tenant context to avoid TenantContextError
        _mark_session_tenant_context(session, tenant_id)
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(lambda sync_conn: [t.drop(sync_conn, checkfirst=True) for t in reversed(_test_tables)])
    await engine.dispose()


@pytest.fixture
def tenant_id() -> str:
    """Fixed tenant ID for consistent test isolation."""
    return "test-tenant-123"


@pytest.fixture
def other_tenant_id() -> str:
    """Different tenant ID for isolation tests."""
    return "test-tenant-456"


@pytest.fixture
def mock_auth(tenant_id: str):
    """Create mock auth dependency for a tenant."""

    async def _override_auth():
        return RequestContext(
            tenant_id=tenant_id,
            user_id=uuid4(),
            roles=["tenant_admin"],
            permissions=frozenset({"read:tenant", "write:tenant"}),
            request_id="req-123",
            auth_source="jwt_claim",
            isolation_tier="shared",
        )

    return _override_auth


@pytest.fixture
def mock_auth_other(other_tenant_id: str):
    """Create mock auth dependency for another tenant."""

    async def _override_auth():
        return RequestContext(
            tenant_id=other_tenant_id,
            user_id=uuid4(),
            roles=["tenant_admin"],
            permissions=frozenset({"read:tenant", "write:tenant"}),
            request_id="req-456",
            auth_source="jwt_claim",
            isolation_tier="shared",
        )

    return _override_auth


@pytest.fixture
def test_app() -> FastAPI:
    """Create a minimal FastAPI app with just the company knowledge router."""
    app = FastAPI()
    app.include_router(company_knowledge_route.router, prefix="/v1")
    return app


@pytest_asyncio.fixture
async def client(test_db, mock_auth, test_app) -> AsyncClient:
    """Create test client with database and auth overrides."""

    async def override_get_db_from_context():
        yield test_db

    test_app.dependency_overrides[get_db_from_context] = override_get_db_from_context
    test_app.dependency_overrides[require_authenticated] = mock_auth

    async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
        yield ac

    test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_profile(test_db, tenant_id: str) -> CompanyKnowledgeProfile:
    """Create a sample company knowledge profile."""
    profile = CompanyKnowledgeProfile(
        tenant_id=tenant_id,
        company_name="Acme Corporation",
        website="https://acme.com",
        status=ProfileStatus.DRAFT.value,
        version=1,
        identity={"description": "Test company", "category": "Software"},
        active_source_ids=[],
    )
    test_db.add(profile)
    await test_db.commit()
    await test_db.refresh(profile)
    return profile


@pytest_asyncio.fixture
async def sample_source(test_db, sample_profile, tenant_id: str) -> KnowledgeSource:
    """Create a sample knowledge source."""
    source = KnowledgeSource(
        tenant_id=tenant_id,
        profile_id=sample_profile.id,
        source_type=SourceType.WEBSITE.value,
        source_url="https://acme.com/products",
        crawl_status=CrawlStatus.COMPLETE.value,
        authority_weight="high",
        page_type="product",
        extra_metadata={"pages_crawled": 5},
    )
    test_db.add(source)
    await test_db.commit()
    await test_db.refresh(source)
    return source


@pytest_asyncio.fixture
async def sample_extraction(test_db, sample_profile, sample_source, tenant_id: str) -> ValueExtractionRecord:
    """Create a sample extraction record."""
    record = ValueExtractionRecord(
        tenant_id=tenant_id,
        profile_id=sample_profile.id,
        source_id=sample_source.id,
        extracted={"products": [{"name": "Widget Pro", "description": "Best widget"}]},
        confidence=0.85,
        requires_review=False,
        page_type="product",
        extraction_version="1.0",
        llm_model="gpt-4o",
    )
    test_db.add(record)
    await test_db.commit()
    await test_db.refresh(record)
    return record


@pytest_asyncio.fixture
async def sample_icp(test_db, sample_profile, tenant_id: str) -> ICPProfile:
    """Create a sample ICP profile."""
    icp = ICPProfile(
        tenant_id=tenant_id,
        profile_id=sample_profile.id,
        industries=["Software", "SaaS"],
        company_size=["100-500", "500-1000"],
        buyer_personas=[{"name": "CTO", "concerns": ["scalability"]}],
        user_personas=[{"name": "Developer", "concerns": ["ease of use"]}],
        pain_points=["slow deployment", "high costs"],
        trigger_events=["series B funding", "team expansion"],
        qualification_criteria=["has engineering team > 20"],
        disqualification_criteria=["less than 10 employees"],
        competitive_context={"primary_competitor": "LegacyCo"},
        buying_committee_structure={"decision_maker": "CTO", "influencer": "VP Eng"},
        typical_sales_motion="land-and-expand",
        confidence=0.82,
        source_type="manual",
    )
    test_db.add(icp)
    await test_db.commit()
    await test_db.refresh(icp)
    return icp


# ──────────────────────────────────────────────────────────────────────────────
# Profile Endpoint Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_profile(client: AsyncClient, tenant_id: str):
    """POST /v1/company-knowledge/profiles creates a draft profile."""
    response = await client.post(
        "/v1/company-knowledge/profiles",
        json={"company_name": "NewCo", "website": "https://newco.io"},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["company_name"] == "NewCo"
    assert data["website"] == "https://newco.io"
    assert data["status"] == "draft"
    assert data["version"] == 1
    assert data["tenant_id"] == tenant_id
    assert data["id"] is not None


@pytest.mark.asyncio
async def test_get_current_profile(client: AsyncClient, sample_profile):
    """GET /v1/company-knowledge/profiles/current returns the active profile."""
    response = await client.get("/v1/company-knowledge/profiles/current")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_profile.id)
    assert data["company_name"] == "Acme Corporation"


@pytest.mark.asyncio
async def test_get_current_profile_404_when_empty(client: AsyncClient):
    """GET /v1/company-knowledge/profiles/current returns 404 when no profile."""
    response = await client.get("/v1/company-knowledge/profiles/current")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_profile_by_id(client: AsyncClient, sample_profile):
    """GET /v1/company-knowledge/profiles/{id} returns profile."""
    response = await client.get(f"/v1/company-knowledge/profiles/{sample_profile.id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_profile.id)


@pytest.mark.asyncio
async def test_get_profile_404_for_wrong_id(client: AsyncClient):
    """GET /v1/company-knowledge/profiles/{id} returns 404 for unknown ID."""
    response = await client.get(f"/v1/company-knowledge/profiles/{uuid4()}")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_update_profile(client: AsyncClient, sample_profile):
    """PATCH /v1/company-knowledge/profiles/{id} updates allowed fields."""
    response = await client.patch(
        f"/v1/company-knowledge/profiles/{sample_profile.id}",
        json={
            "company_name": "Acme Inc",
            "identity": {"description": "Updated description"},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["company_name"] == "Acme Inc"
    assert data["identity"]["description"] == "Updated description"


@pytest.mark.asyncio
async def test_approve_profile(client: AsyncClient, sample_profile):
    """POST /v1/company-knowledge/profiles/{id}/approve approves profile."""
    reviewer_id = str(uuid4())
    response = await client.post(
        f"/v1/company-knowledge/profiles/{sample_profile.id}/approve",
        json={"approved_by": reviewer_id},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["version"] == 2
    assert data["approved_by"] == reviewer_id
    assert data["approved_at"] is not None


# ──────────────────────────────────────────────────────────────────────────────
# Knowledge Source Endpoint Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_add_knowledge_source(client: AsyncClient, sample_profile):
    """POST /v1/company-knowledge/sources creates a source."""
    with patch(
        "value_fabric.layer4.api.routes.company_knowledge.CompanyKnowledgeService.trigger_layer1_crawl",
        new_callable=AsyncMock,
    ) as mock_crawl:
        response = await client.post(
            "/v1/company-knowledge/sources",
            json={
                "profile_id": str(sample_profile.id),
                "source_type": "website",
                "source_url": "https://acme.com/blog",
                "authority_weight": "medium",
                "page_type": "blog",
            },
        )
        assert response.status_code == 201
        data = response.json()
        assert data["source_url"] == "https://acme.com/blog"
        assert data["source_type"] == "website"
        assert data["crawl_status"] == "pending"
        mock_crawl.assert_awaited_once()


@pytest.mark.asyncio
async def test_add_manual_source(client: AsyncClient, sample_profile):
    """POST /v1/company-knowledge/sources with manual type has complete status."""
    response = await client.post(
        "/v1/company-knowledge/sources",
        json={
            "profile_id": str(sample_profile.id),
            "source_type": "manual",
            "document_name": "Internal Notes",
            "authority_weight": "high",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["source_type"] == "manual"
    assert data["crawl_status"] == "complete"


@pytest.mark.asyncio
async def test_list_knowledge_sources(client: AsyncClient, sample_source):
    """GET /v1/company-knowledge/sources lists sources."""
    response = await client.get("/v1/company-knowledge/sources")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    assert data["items"][0]["id"] == str(sample_source.id)


# ──────────────────────────────────────────────────────────────────────────────
# Extraction Record Endpoint Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_list_extraction_records(client: AsyncClient, sample_extraction):
    """GET /v1/company-knowledge/extractions lists records."""
    response = await client.get("/v1/company-knowledge/extractions")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["confidence"] == 0.85


@pytest.mark.asyncio
async def test_review_extraction_accept(client: AsyncClient, sample_extraction):
    """POST /v1/company-knowledge/extractions/{id}/review accepts record."""
    response = await client.post(
        f"/v1/company-knowledge/extractions/{sample_extraction.id}/review",
        json={"action": "accepted", "user_edits": None},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["review_status"] == "accepted"
    assert data["requires_review"] is False


@pytest.mark.asyncio
async def test_review_extraction_modify(client: AsyncClient, sample_extraction):
    """POST review with modify action updates extracted data."""
    response = await client.post(
        f"/v1/company-knowledge/extractions/{sample_extraction.id}/review",
        json={
            "action": "modified",
            "user_edits": {"products": [{"name": "Updated Widget"}]},
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert data["review_status"] == "modified"
    assert data["extracted"]["products"][0]["name"] == "Updated Widget"


@pytest.mark.asyncio
async def test_review_extraction_reject(client: AsyncClient, sample_extraction):
    """POST review with reject action marks record rejected."""
    response = await client.post(
        f"/v1/company-knowledge/extractions/{sample_extraction.id}/review",
        json={"action": "rejected"},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["review_status"] == "rejected"


# ──────────────────────────────────────────────────────────────────────────────
# ICP Profile Endpoint Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_create_icp_profile(client: AsyncClient, sample_profile):
    """POST /v1/company-knowledge/icp creates ICP."""
    response = await client.post(
        "/v1/company-knowledge/icp",
        json={
            "profile_id": str(sample_profile.id),
            "industries": ["Fintech"],
            "company_size": ["50-200"],
            "buyer_personas": [{"name": "CFO", "concerns": ["ROI"]}],
            "user_personas": [{"name": "Analyst", "concerns": ["accuracy"]}],
            "pain_points": ["manual reporting"],
            "trigger_events": ["audit season"],
            "qualification_criteria": ["uses QuickBooks"],
            "disqualification_criteria": ["non-profit"],
            "source_type": "manual",
        },
    )
    assert response.status_code == 201
    data = response.json()
    assert data["industries"] == ["Fintech"]
    assert data["profile_id"] == str(sample_profile.id)


@pytest.mark.asyncio
async def test_get_icp_for_current_profile(client: AsyncClient, sample_icp):
    """GET /v1/company-knowledge/icp returns ICP for active profile."""
    response = await client.get("/v1/company-knowledge/icp")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == str(sample_icp.id)
    assert data["industries"] == ["Software", "SaaS"]


@pytest.mark.asyncio
async def test_update_icp_profile(client: AsyncClient, sample_icp):
    """PATCH /v1/company-knowledge/icp/{id} updates ICP."""
    response = await client.patch(
        f"/v1/company-knowledge/icp/{sample_icp.id}",
        json={"industries": ["AI", "ML"], "confidence": 0.95},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["industries"] == ["AI", "ML"]
    assert data["confidence"] == 0.95


# ──────────────────────────────────────────────────────────────────────────────
# Onboarding Status Endpoint Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_onboarding_status(
    client: AsyncClient,
    sample_profile,
    sample_source,
    sample_extraction,
    sample_icp,
):
    """GET /v1/company-knowledge/onboarding-status aggregates progress."""
    response = await client.get("/v1/company-knowledge/onboarding-status")
    assert response.status_code == 200
    data = response.json()
    assert data["tenant_id"] is not None
    assert data["profile_id"] == str(sample_profile.id)
    assert data["sources_count"] == 1
    assert data["extractions_count"] == 1
    assert data["icp_present"] is True
    assert data["has_approved_profile"] is False
    assert "next_step" in data


# ──────────────────────────────────────────────────────────────────────────────
# Tenant Isolation Tests
# ──────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_tenant_isolation_profiles(
    test_db, mock_auth, mock_auth_other, tenant_id, other_tenant_id
):
    """Profiles from one tenant are not visible to another tenant."""
    app = FastAPI()
    app.include_router(company_knowledge_route.router, prefix="/v1")

    async def override_db():
        yield test_db

    app.dependency_overrides[get_db_from_context] = override_db
    app.dependency_overrides[require_authenticated] = mock_auth

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        create_resp = await client.post(
            "/v1/company-knowledge/profiles",
            json={"company_name": "Tenant1Co", "website": "https://t1.co"},
        )
        assert create_resp.status_code == 201
        profile_id = create_resp.json()["id"]

        # Switch to other tenant
        app.dependency_overrides[require_authenticated] = mock_auth_other

        get_resp = await client.get(f"/v1/company-knowledge/profiles/{profile_id}")
        assert get_resp.status_code == 404

    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_tenant_isolation_sources(
    test_db, mock_auth, mock_auth_other, tenant_id, other_tenant_id
):
    """Sources from one tenant are not visible to another tenant."""
    profile = CompanyKnowledgeProfile(
        tenant_id=tenant_id,
        company_name="T1",
        website="https://t1.com",
        status=ProfileStatus.DRAFT.value,
        version=1,
        active_source_ids=[],
    )
    test_db.add(profile)
    await test_db.commit()
    await test_db.refresh(profile)

    source = KnowledgeSource(
        tenant_id=tenant_id,
        profile_id=profile.id,
        source_type=SourceType.WEBSITE.value,
        source_url="https://t1.com",
        crawl_status=CrawlStatus.COMPLETE.value,
        authority_weight="medium",
        extra_metadata={},
    )
    test_db.add(source)
    await test_db.commit()

    app = FastAPI()
    app.include_router(company_knowledge_route.router, prefix="/v1")

    async def override_db():
        yield test_db

    app.dependency_overrides[get_db_from_context] = override_db
    app.dependency_overrides[require_authenticated] = mock_auth_other

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        list_resp = await client.get("/v1/company-knowledge/sources")
        assert list_resp.status_code == 200
        data = list_resp.json()
        assert data["total"] == 0

    app.dependency_overrides.clear()


# ──────────────────────────────────────────────────────────────────────────────
# Service Layer Unit Tests (Mocked DB)
# ──────────────────────────────────────────────────────────────────────────────


class TestCompanyKnowledgeServiceUnit:
    """Unit tests for CompanyKnowledgeService with mocked AsyncSession."""

    def _make_mock_db(self):
        db = MagicMock()
        db.add = MagicMock()
        db.commit = AsyncMock()
        db.refresh = AsyncMock()
        db.execute = AsyncMock()
        return db

    def _mock_execute_result(self, db, record=None, scalar=None):
        """Configure db.execute to return a result with scalar_one_or_none and scalar."""
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = record
        result_mock.scalar.return_value = scalar
        db.execute.return_value = result_mock

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_create_profile(self):
        """Service creates profile with correct defaults."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)

        profile = await svc.create_profile(
            tenant_id="t-123",
            company_name="MockCo",
            website="https://mock.co",
        )
        assert profile.tenant_id == "t-123"
        assert profile.company_name == "MockCo"
        assert profile.status == ProfileStatus.DRAFT.value
        assert profile.version == 1
        db.add.assert_called_once_with(profile)
        db.commit.assert_awaited_once()

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_approve_profile_increments_version(self):
        """Approving a profile increments version and sets approved fields."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)

        existing = CompanyKnowledgeProfile(
            id=uuid4(),
            tenant_id="t-123",
            company_name="MockCo",
            status=ProfileStatus.DRAFT.value,
            version=1,
            active_source_ids=[],
        )
        self._mock_execute_result(db, record=existing)

        approved_by = uuid4()
        result = await svc.approve_profile(existing.id, "t-123", approved_by)
        assert result.status == ProfileStatus.APPROVED.value
        assert result.version == 2
        assert result.approved_by == approved_by
        assert result.approved_at is not None

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_review_extraction_accept(self):
        """Reviewing as accepted updates status correctly."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)

        record = ValueExtractionRecord(
            id=uuid4(),
            tenant_id="t-123",
            profile_id=uuid4(),
            source_id=uuid4(),
            extracted={"foo": "bar"},
            confidence=0.6,
            requires_review=True,
        )
        self._mock_execute_result(db, record=record)

        reviewed_by = uuid4()
        result = await svc.review_extraction_record(
            record_id=record.id,
            tenant_id="t-123",
            action=ReviewStatus.ACCEPTED,
            reviewed_by=reviewed_by,
        )
        assert result.review_status == ReviewStatus.ACCEPTED.value
        assert result.requires_review is False
        assert result.reviewed_by == reviewed_by

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_review_extraction_modify(self):
        """Reviewing as modified merges user edits."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)

        record = ValueExtractionRecord(
            id=uuid4(),
            tenant_id="t-123",
            profile_id=uuid4(),
            source_id=uuid4(),
            extracted={"products": [{"name": "Old"}]},
            confidence=0.6,
            requires_review=True,
        )
        self._mock_execute_result(db, record=record)

        reviewed_by = uuid4()
        result = await svc.review_extraction_record(
            record_id=record.id,
            tenant_id="t-123",
            action=ReviewStatus.MODIFIED,
            reviewed_by=reviewed_by,
            user_edits={"products": [{"name": "New"}]},
        )
        assert result.review_status == ReviewStatus.MODIFIED.value
        assert result.extracted["products"][0]["name"] == "New"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_onboarding_status_no_profile(self):
        """Onboarding status when no profile exists."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)

        # Mock execute to return None for profile queries and 0 for counts
        self._mock_execute_result(db, record=None, scalar=0)

        status = await svc.get_onboarding_status("t-123")
        assert status["profile_id"] is None
        assert status["next_step"] == "Enter your company website to begin."

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_trigger_layer1_crawl(self):
        """Triggering Layer 1 crawl calls client and updates source status."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)

        source = KnowledgeSource(
            id=uuid4(),
            tenant_id="t-123",
            profile_id=uuid4(),
            source_type=SourceType.WEBSITE.value,
            source_url="https://example.com",
            crawl_status=CrawlStatus.PENDING.value,
            authority_weight="medium",
            metadata={},
        )

        # Mock get_knowledge_source to return our source
        svc.get_knowledge_source = AsyncMock(return_value=source)
        svc.update_crawl_status = AsyncMock(return_value=source)

        with patch.object(
            svc, "_get_layer1_client", return_value=MagicMock()
        ) as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.crawl_website = AsyncMock(
                return_value={"target_id": "tgt-1", "job_id": "job-1"}
            )

            result = await svc.trigger_layer1_crawl(source.id, "t-123")
            assert result["target_id"] == "tgt-1"
            mock_client.crawl_website.assert_awaited_once_with(
                url="https://example.com",
                tenant_id="t-123",
                name="Company knowledge crawl: https://example.com",
            )

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_profile_to_layer3(self):
        """Syncing approved profile pushes canonical ingest payload to Layer 3."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)

        profile = CompanyKnowledgeProfile(
            id=uuid4(),
            tenant_id="t-123",
            company_name="SyncCo",
            status=ProfileStatus.APPROVED.value,
            version=2,
            identity={"description": "Test"},
            product_catalog={"products": [{"name": "Product A"}]},
            personas={"personas": [{"name": "Buyer"}]},
            use_cases={"use_cases": [{"name": "UseCase1"}]},
            value_drivers={"drivers": [{"name": "Driver1"}]},
            active_source_ids=[],
        )

        svc.get_profile = AsyncMock(return_value=profile)

        with patch.object(
            svc, "_get_layer3_client", return_value=MagicMock()
        ) as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.ingest = AsyncMock(return_value={
                "status": "success",
                "source_id": f"company-profile:{profile.id}",
                "entities_loaded": 5,
                "relationships_loaded": 0,
                "triples_processed": 10,
            })

            result = await svc.sync_profile_to_layer3(
                profile.id,
                "t-123",
                auth_headers={"Authorization": "Bearer test-token", "X-Tenant-ID": "t-123"},
            )
            assert result["profile_id"] == str(profile.id)
            assert result["ingest_status"] == "success"
            assert result["entities_loaded"] == 5
            mock_client.ingest.assert_awaited_once()
            call_kwargs = mock_client.ingest.await_args.kwargs
            assert call_kwargs["tenant_id"] == "t-123"
            assert call_kwargs["passthrough_headers"]["Authorization"] == "Bearer test-token"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_profile_to_layer3_ingest_failure(self):
        """Syncing raises if canonical ingest call fails."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)
        profile = CompanyKnowledgeProfile(
            id=uuid4(), tenant_id="t-123", company_name="SyncCo", status=ProfileStatus.APPROVED.value, version=2, active_source_ids=[]
        )
        svc.get_profile = AsyncMock(return_value=profile)
        with patch.object(svc, "_get_layer3_client", return_value=MagicMock()) as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.ingest = AsyncMock(side_effect=RuntimeError("layer3 unavailable"))
            with pytest.raises(RuntimeError, match="layer3 unavailable"):
                await svc.sync_profile_to_layer3(profile.id, "t-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_profile_to_layer3_contract_mismatch(self):
        """Syncing raises on Layer 3 response contract mismatch."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)
        profile = CompanyKnowledgeProfile(
            id=uuid4(), tenant_id="t-123", company_name="SyncCo", status=ProfileStatus.APPROVED.value, version=2, active_source_ids=[]
        )
        svc.get_profile = AsyncMock(return_value=profile)
        with patch.object(svc, "_get_layer3_client", return_value=MagicMock()) as mock_client_factory:
            mock_client = mock_client_factory.return_value
            mock_client.ingest = AsyncMock(return_value={"status": "success", "source_id": "x"})
            with pytest.raises(ValueError, match="contract mismatch"):
                await svc.sync_profile_to_layer3(profile.id, "t-123")

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_sync_profile_rejects_unapproved(self):
        """Syncing unapproved profile raises error."""
        db = self._make_mock_db()
        svc = CompanyKnowledgeService(db)

        profile = CompanyKnowledgeProfile(
            id=uuid4(),
            tenant_id="t-123",
            company_name="DraftCo",
            status=ProfileStatus.DRAFT.value,
            version=1,
            active_source_ids=[],
        )
        svc.get_profile = AsyncMock(return_value=profile)

        with pytest.raises(ValueError, match="Only approved profiles"):
            await svc.sync_profile_to_layer3(profile.id, "t-123")
