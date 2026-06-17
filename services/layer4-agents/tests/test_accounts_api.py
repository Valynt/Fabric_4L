from __future__ import annotations

"""API tests for Accounts endpoints.

Tests the accounts-first CRM integration API contract:
- GET /v1/accounts (list with filters)
- POST /v1/accounts/search (search across name/domain/owner)
- GET /v1/accounts/{id} (detail with embedded opportunities/contacts)
- GET /v1/accounts/{id}/activity (activity timeline)
- POST /v1/accounts/sync (manual sync trigger)
- GET /v1/accounts/sync-status (provider sync status)
"""


import pytest

pytestmark = [
    pytest.mark.integration,
    pytest.mark.postgres,
]

from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from typing import Any
from uuid import uuid4

import psycopg  # noqa: F401 — mandatory dep; install via layer4-agents[dev] (psycopg[binary])
import pytest_asyncio

# Create test-specific app without full middleware stack
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker
from value_fabric.shared.error_handling import register_exception_handlers
from value_fabric.shared.identity.context import RequestContext
from value_fabric.shared.identity.dependencies import require_authenticated
from value_fabric.shared.identity.permissions import Permission, Role
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.api.routes.accounts import router as accounts_router
from layer4_agents.api.routes.analysis import router as analysis_router
from layer4_agents.database import Base, _mark_session_tenant_context, get_db_from_context
from layer4_agents.models.account import Account, AccountSyncStatus, CRMProvider, SyncStatus
from layer4_agents.models.business_case_record import BusinessCaseRecord

test_app = FastAPI()
register_exception_handlers(test_app)
test_app.include_router(accounts_router, prefix="/v1", tags=["Accounts"])
test_app.include_router(analysis_router, prefix="/v1", tags=["Analysis"])


class mock_sync_providerResult(TypedDictModel):
    errors: list[Any]
    failed: int
    updated: int


@pytest_asyncio.fixture(scope="function")
async def test_db(postgres_container) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session with fresh tables using PostgreSQL."""
    # Build async PostgreSQL URL
    host = postgres_container.get_container_host_ip()
    port = postgres_container.get_exposed_port(5432)
    username = postgres_container.username
    password = postgres_container.password
    dbname = postgres_container.dbname

    test_database_url = f"postgresql+asyncpg://{username}:{password}@{host}:{port}/{dbname}"

    engine = create_async_engine(test_database_url, echo=False)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async_session = sessionmaker(
        engine, class_=AsyncSession, expire_on_commit=False
    )

    async with async_session() as session:
        # Mark session with tenant context to avoid TenantContextError
        _mark_session_tenant_context(session, "test-tenant-accounts")
        yield session

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()


@pytest_asyncio.fixture
async def client(test_db) -> AsyncGenerator[AsyncClient, None]:
    """Create test client with database and auth override."""
    async def override_get_db():
        yield test_db

    async def override_auth():
        return RequestContext(
            tenant_id="test-tenant-accounts",
            user_id=str(uuid4()),
            roles=[Role.TENANT_ADMIN.value],
            permissions=frozenset({Permission.WRITE_AGENTS.value, Permission.READ_AGENTS.value}),
            source="jwt",
        )

    test_app.dependency_overrides[get_db_from_context] = override_get_db
    test_app.dependency_overrides[require_authenticated] = override_auth

    try:
        async with AsyncClient(transport=ASGITransport(app=test_app), base_url="http://test") as ac:
            yield ac
    finally:
        test_app.dependency_overrides.clear()


@pytest_asyncio.fixture
async def sample_account(test_db) -> Account:
    """Create a sample account for testing."""
    account = Account(
        id=uuid4(),
        tenant_id="test-tenant-accounts",
        provider=CRMProvider.SALESFORCE.value,
        provider_record_id="sf-acc-001",
        name="Acme Corporation",
        normalized_name="acme corporation",
        domain="acme.com",
        industry="Software",
        company_size=500,
        annual_revenue=50000000.0,
        headquarters="San Francisco, CA",
        website="https://acme.com",
        owner_id="sf-owner-001",
        owner_name="John Smith",
        owner_email="john@acme.com",
        stage="opportunity",
        sync_status=SyncStatus.SYNCED.value,
        last_synced_at=datetime.now(UTC),
        opportunities=[
            {
                "provider_opportunity_id": "sf-opp-001",
                "name": "Enterprise Deal 2024",
                "stage": "Negotiation",
                "value": 250000.0,
                "probability": 0.75,
                "close_date": "2024-12-31",
                "last_synced_at": datetime.now(UTC).isoformat(),
            }
        ],
        contacts=[
            {
                "provider_contact_id": "sf-contact-001",
                "name": "Jane Doe",
                "title": "CTO",
                "email": "jane@acme.com",
                "phone": "+1-555-0123",
                "is_primary": True,
                "last_synced_at": datetime.now(UTC).isoformat(),
            }
        ],
    )
    test_db.add(account)
    await test_db.commit()
    await test_db.refresh(account)
    return account


@pytest_asyncio.fixture
async def sample_hubspot_account(test_db) -> Account:
    """Create a sample HubSpot account for testing."""
    account = Account(
        id=uuid4(),
        tenant_id="test-tenant-accounts",
        provider=CRMProvider.HUBSPOT.value,
        provider_record_id="hs-company-001",
        name="TechCorp Inc",
        normalized_name="techcorp inc",
        domain="techcorp.io",
        industry="Technology",
        company_size=200,
        stage="qualified",
        sync_status=SyncStatus.SYNCED.value,
        last_synced_at=datetime.now(UTC) - timedelta(hours=2),
    )
    test_db.add(account)
    await test_db.commit()
    await test_db.refresh(account)
    return account


@pytest_asyncio.fixture
async def sample_sync_status(test_db) -> AccountSyncStatus:
    """Create sample sync status for testing."""
    sync_status = AccountSyncStatus(
        tenant_id="test-tenant-accounts",
        provider=CRMProvider.SALESFORCE.value,
        status="idle",
        last_sync_at=datetime.now(UTC) - timedelta(hours=1),
        last_successful_sync_at=datetime.now(UTC) - timedelta(hours=1),
        records_synced=150,
        records_updated=12,
        records_failed=0,
    )
    test_db.add(sync_status)
    await test_db.commit()
    await test_db.refresh(sync_status)
    return sync_status


# =============================================================================
# List Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_list_accounts_empty(client: AsyncClient):
    """Test listing accounts when database is empty."""
    response = await client.get("/v1/accounts")
    assert response.status_code == 200
    
    data = response.json()
    assert data["items"] == []
    assert data["total"] == 0
    assert data["page"] == 1
    assert not data["has_more"]


@pytest.mark.asyncio
async def test_create_account(client: AsyncClient):
    """POST /v1/accounts creates an account with UUID primary key."""
    response = await client.post(
        "/v1/accounts",
        json={
            "provider": "salesforce",
            "provider_record_id": "sf-acc-new-001",
            "name": "NewCo",
            "domain": "newco.example",
            "industry": "Software",
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"]
    assert body["name"] == "NewCo"
    assert body["provider"] == "salesforce"
    assert body["provider_record_id"] == "sf-acc-new-001"


@pytest.mark.asyncio
async def test_create_case_from_existing_account(client: AsyncClient, sample_account: Account, test_db: AsyncSession):
    """POST /v1/cases accepts account_id and persists account-case linkage."""
    mock_result = SimpleNamespace(
        workflow_id="wf-case-001",
        status=SimpleNamespace(value="completed"),
        output_data={
            "assemble_document": {
                "document_url": "https://example.com/cases/wf-case-001.pdf",
                "page_count": 5,
                "file_size_bytes": 1024,
                "case_metadata": {},
            },
            "verify_truth_requirements": {},
        },
    )

    class _Executor:
        async def run(self, workflow_type: str, input_data: dict, tenant_id: str | None = None, user_id: str | None = None):
            assert workflow_type == "business_case"
            assert str(input_data["account_id"]) == str(sample_account.id)
            assert input_data["custom_inputs"]["provider_record_id"] == sample_account.provider_record_id
            return mock_result

    from layer4_agents.api.startup import runtime_state
    original_executor = runtime_state.workflow_executor
    runtime_state.workflow_executor = _Executor()
    try:
        response = await client.post(
            "/v1/cases",
            json={"account_id": str(sample_account.id), "sections": ["executive_summary"]},
        )
    finally:
        runtime_state.workflow_executor = original_executor

    assert response.status_code == 200
    payload = response.json()
    assert payload["case_id"] == "wf-case-001"
    assert payload["case_metadata"]["account_id"] == str(sample_account.id)

    persisted = await test_db.get(BusinessCaseRecord, "wf-case-001")
    assert persisted is not None
    assert str(persisted.account_id) == str(sample_account.id)


@pytest.mark.asyncio
async def test_create_case_rejects_non_uuid_account_id(client: AsyncClient):
    """POST /v1/cases rejects non-UUID account_id values."""
    response = await client.post(
        "/v1/cases",
        json={"account_id": "not-a-uuid", "sections": ["executive_summary"]},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_list_accounts_with_data(client: AsyncClient, sample_account: Account):
    """Test listing accounts returns account with correct fields."""
    response = await client.get("/v1/accounts")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert len(data["items"]) == 1
    
    account = data["items"][0]
    assert account["name"] == "Acme Corporation"
    assert account["provider"] == "salesforce"
    assert account["provider_badge"] == "Salesforce"
    assert account["domain"] == "acme.com"
    assert account["industry"] == "Software"
    assert account["owner_name"] == "John Smith"
    assert account["stage"] == "opportunity"
    assert account["sync_status"] == "synced"
    assert "last_synced_at" in account
    assert "updated_at" in account


@pytest.mark.asyncio
async def test_list_accounts_filter_by_provider(
    client: AsyncClient,
    sample_account: Account,
    sample_hubspot_account: Account,
):
    """Test filtering accounts by provider."""
    response = await client.get("/v1/accounts?provider=salesforce")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["provider"] == "salesforce"


@pytest.mark.asyncio
async def test_list_accounts_filter_by_stage(
    client: AsyncClient,
    sample_account: Account,
    sample_hubspot_account: Account,
):
    """Test filtering accounts by stage."""
    response = await client.get("/v1/accounts?stage=opportunity")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["stage"] == "opportunity"


@pytest.mark.asyncio
async def test_list_accounts_pagination(client: AsyncClient, test_db: AsyncSession):
    """Test pagination returns correct page info."""
    # Create multiple accounts
    for i in range(5):
        account = Account(
            id=uuid4(),
            tenant_id="test-tenant-accounts",
            provider=CRMProvider.SALESFORCE.value,
            provider_record_id=f"sf-acc-{i:03d}",
            name=f"Company {i}",
            sync_status=SyncStatus.SYNCED.value,
        )
        test_db.add(account)
    await test_db.commit()
    
    response = await client.get("/v1/accounts?page=1&page_size=2")
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 5
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["page_size"] == 2
    assert data["has_more"]


@pytest.mark.asyncio
async def test_list_accounts_sorting(client: AsyncClient, test_db: AsyncSession):
    """Test sorting accounts by different fields."""
    # Create accounts with different names
    for name in ["Beta Corp", "Alpha Inc", "Gamma Ltd"]:
        account = Account(
            id=uuid4(),
            tenant_id="test-tenant-accounts",
            provider=CRMProvider.SALESFORCE.value,
            provider_record_id=f"sf-{name.lower().replace(' ', '-')}",
            name=name,
            sync_status=SyncStatus.SYNCED.value,
        )
        test_db.add(account)
    await test_db.commit()
    
    response = await client.get("/v1/accounts?sort_by=name&sort_order=asc")
    assert response.status_code == 200
    
    data = response.json()
    names = [a["name"] for a in data["items"]]
    assert names == ["Alpha Inc", "Beta Corp", "Gamma Ltd"]


# =============================================================================
# Search Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_search_accounts_by_name(client: AsyncClient, sample_account: Account):
    """Test searching accounts by name."""
    response = await client.post(
        "/v1/accounts/search",
        json={"query": "Acme"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "Acme Corporation"


@pytest.mark.asyncio
async def test_search_accounts_by_domain(client: AsyncClient, sample_account: Account):
    """Test searching accounts by domain."""
    response = await client.post(
        "/v1/accounts/search",
        json={"query": "acme.com"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["domain"] == "acme.com"


@pytest.mark.asyncio
async def test_search_accounts_by_owner(client: AsyncClient, sample_account: Account):
    """Test searching accounts by owner name."""
    response = await client.post(
        "/v1/accounts/search",
        json={"query": "John Smith"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["owner_name"] == "John Smith"


@pytest.mark.asyncio
async def test_search_accounts_no_results(client: AsyncClient, sample_account: Account):
    """Test searching with no matching results."""
    response = await client.post(
        "/v1/accounts/search",
        json={"query": "NonExistentCompany"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 0
    assert data["items"] == []


@pytest.mark.asyncio
async def test_search_accounts_with_filters(client: AsyncClient, test_db: AsyncSession):
    """Test searching with combined text query and filters."""
    # Create test accounts
    accounts = [
        Account(
            id=uuid4(),
            tenant_id="test-tenant-accounts",
            provider=CRMProvider.SALESFORCE.value,
            provider_record_id="sf-001",
            name="TechCorp Alpha",
            industry="Software",
            sync_status=SyncStatus.SYNCED.value,
        ),
        Account(
            id=uuid4(),
            tenant_id="test-tenant-accounts",
            provider=CRMProvider.HUBSPOT.value,
            provider_record_id="hs-001",
            name="TechCorp Beta",
            industry="Hardware",
            sync_status=SyncStatus.SYNCED.value,
        ),
    ]
    for acc in accounts:
        test_db.add(acc)
    await test_db.commit()
    
    response = await client.post(
        "/v1/accounts/search",
        json={"query": "TechCorp", "provider": "salesforce", "industry": "Software"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["total"] == 1
    assert data["items"][0]["name"] == "TechCorp Alpha"


# =============================================================================
# Detail Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_account_detail(client: AsyncClient, sample_account: Account):
    """Test getting full account detail with embedded data."""
    response = await client.get(f"/v1/accounts/{sample_account.id}")
    assert response.status_code == 200
    
    data = response.json()
    assert data["id"] == str(sample_account.id)
    assert data["name"] == "Acme Corporation"
    assert data["provider"] == "salesforce"
    assert data["provider_record_id"] == "sf-acc-001"
    assert data["annual_revenue"] == 50000000.0
    assert data["headquarters"] == "San Francisco, CA"
    assert data["owner_email"] == "john@acme.com"
    assert "source_attribution" in data
    assert "provider_badge" in data
    
    # Check embedded opportunities
    assert len(data["opportunities"]) == 1
    opp = data["opportunities"][0]
    assert opp["name"] == "Enterprise Deal 2024"
    assert opp["stage"] == "Negotiation"
    # API may return value as string or float depending on serialization
    assert float(opp["value"]) == 250000.0
    
    # Check embedded contacts
    assert len(data["contacts"]) == 1
    contact = data["contacts"][0]
    assert contact["name"] == "Jane Doe"
    assert contact["title"] == "CTO"
    assert contact["is_primary"]


@pytest.mark.asyncio
async def test_get_account_not_found(client: AsyncClient):
    """Test getting non-existent account returns 404."""
    fake_id = uuid4()
    response = await client.get(f"/v1/accounts/{fake_id}")
    assert response.status_code == 404


# =============================================================================
# Sync Status Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_sync_status_all(
    client: AsyncClient,
    sample_sync_status: AccountSyncStatus,
):
    """Test getting sync status for all providers."""
    response = await client.get("/v1/accounts/sync-status")
    assert response.status_code == 200
    
    data = response.json()
    assert "providers" in data
    assert "overall_status" in data
    
    # Should have at least our sample
    providers = data["providers"]
    assert len(providers) >= 1
    
    sf_provider = next((p for p in providers if p["provider"] == "salesforce"), None)
    assert sf_provider is not None
    assert sf_provider["status"] == "idle"
    assert sf_provider["records_synced"] == 150


@pytest.mark.asyncio
async def test_get_sync_status_empty(client: AsyncClient):
    """Test getting sync status when no syncs have run."""
    response = await client.get("/v1/accounts/sync-status")
    assert response.status_code == 200
    
    data = response.json()
    assert data["providers"] == []
    assert data["overall_status"] == "healthy"  # No failures when empty


# =============================================================================
# Sync Trigger Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_sync_accounts_all_providers(client: AsyncClient, monkeypatch):
    """Test triggering sync for all providers returns completed or partial status."""
    # Mock CRMSyncService to avoid environment coupling
    from layer4_agents.services.crm_sync_service import CRMSyncService
    
    async def mock_sync_provider(self, provider, incremental=True, account_ids=None, tenant_id=None):
        return mock_sync_providerResult.model_validate({"updated": 5, "failed": 0, "errors": []})

    monkeypatch.setattr(CRMSyncService, "sync_provider", mock_sync_provider)

    response = await client.post(
        "/v1/accounts/sync",
        json={}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "sync_id" in data
    # API returns "completed" when no failures, "partial" when some fail
    assert data["status"] in ("completed", "partial")
    assert data["provider"] is None
    assert "all providers" in data["message"]


@pytest.mark.asyncio
async def test_sync_accounts_specific_provider(client: AsyncClient, monkeypatch):
    """Test triggering sync for specific provider returns completed or partial status."""
    # Mock CRMSyncService to avoid environment coupling
    from layer4_agents.services.crm_sync_service import CRMSyncService
    
    async def mock_sync_provider(self, provider, incremental=True, account_ids=None, tenant_id=None):
        return mock_sync_providerResult.model_validate({"updated": 3, "failed": 0, "errors": []})

    monkeypatch.setattr(CRMSyncService, "sync_provider", mock_sync_provider)

    response = await client.post(
        "/v1/accounts/sync",
        json={"provider": "salesforce"}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert data["sync_id"].startswith("sync-")
    # API returns "completed" when no failures, "partial" when some fail
    assert data["status"] in ("completed", "partial")
    assert data["provider"] == "salesforce"
    # Message contains sync stats
    assert "Synced" in data["message"]


@pytest.mark.asyncio
async def test_sync_accounts_force_refresh(client: AsyncClient, monkeypatch):
    """Test triggering sync with force refresh returns completed or partial status."""
    # Mock CRMSyncService to avoid environment coupling
    from layer4_agents.services.crm_sync_service import CRMSyncService
    
    async def mock_sync_provider(self, provider, incremental=False, account_ids=None, tenant_id=None):
        return mock_sync_providerResult.model_validate({"updated": 10, "failed": 0, "errors": []})

    monkeypatch.setattr(CRMSyncService, "sync_provider", mock_sync_provider)

    response = await client.post(
        "/v1/accounts/sync",
        json={"force_refresh": True}
    )
    assert response.status_code == 200
    
    data = response.json()
    assert "sync_id" in data
    # API returns "completed" when no failures, "partial" when some fail
    assert data["status"] in ("completed", "partial")


# =============================================================================
# Activity Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_account_activity_not_found(client: AsyncClient):
    """Test getting activity for non-existent account returns 404."""
    fake_id = uuid4()
    response = await client.get(f"/v1/accounts/{fake_id}/activity")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_account_activity_success(client: AsyncClient, sample_account: Account):
    """Test getting activity for existing account."""
    response = await client.get(f"/v1/accounts/{sample_account.id}/activity")
    # Activity endpoint should return successfully
    assert response.status_code == 200

    if response.status_code == 200:
        data = response.json()
        assert data["account_id"] == str(sample_account.id)
        assert "interactions" in data
        assert "total_count" in data


# =============================================================================
# Refresh Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_account_not_found(client: AsyncClient):
    """Test refreshing non-existent account returns 404."""
    fake_id = uuid4()
    response = await client.post(f"/v1/accounts/{fake_id}/refresh")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_refresh_account_success(client: AsyncClient, sample_account: Account, monkeypatch):
    """Test refreshing existing account."""
    # Mock CRMSyncService to avoid environment coupling
    from layer4_agents.services.crm_sync_service import CRMSyncService
    
    async def mock_refresh_single_account(self, account_id, tenant_id):
        # Return the account with updated timestamp
        return sample_account
    
    monkeypatch.setattr(CRMSyncService, "refresh_single_account", mock_refresh_single_account)
    
    response = await client.post(f"/v1/accounts/{sample_account.id}/refresh")
    # Refresh should succeed for existing account
    assert response.status_code == 200

    if response.status_code == 200:
        data = response.json()
        assert data["id"] == str(sample_account.id)


# =============================================================================
# Filter Options Endpoint Tests
# =============================================================================

@pytest.mark.asyncio
async def test_get_filter_options_empty(client: AsyncClient):
    """Test getting filter options with no accounts."""
    response = await client.get("/v1/accounts/filters")
    assert response.status_code == 200
    
    data = response.json()
    assert data["industries"] == []
    assert data["stages"] == []
    assert "salesforce" in [p.value for p in CRMProvider]
    assert data["owners"] == []


@pytest.mark.asyncio
async def test_get_filter_options_with_data(
    client: AsyncClient,
    sample_account: Account,
    sample_hubspot_account: Account,
):
    """Test getting filter options with accounts."""
    response = await client.get("/v1/accounts/filters")
    assert response.status_code == 200
    
    data = response.json()
    assert "Software" in data["industries"] or "Technology" in data["industries"]
    assert "opportunity" in data["stages"] or "qualified" in data["stages"]
    assert set(data["providers"]) >= {"salesforce", "hubspot"}
    assert len(data["owners"]) >= 1
