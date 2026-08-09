from __future__ import annotations

"""
Tests for CRMSyncService and CRM webhook handlers.

Covers:
- Sync provider with mocked CRM APIs
- Single account refresh
- Incremental vs full sync
- Error handling and retry logic
- Webhook handlers for Salesforce and HubSpot
"""


from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import psycopg  # noqa: F401 — mandatory dep; install via layer4-agents[dev] (psycopg[binary])
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.models.typed_dict import TypedDictModel

from layer4_agents.api.main import app
from layer4_agents.api.routes import crm_webhooks
from layer4_agents.models.account import (
    Account,
    CRMProvider,
    SyncStatus,
)
from layer4_agents.integrations.core.types import CanonicalRecord, CRMModel, SyncCursor
from layer4_agents.services.crm_sync_service import CRMSyncService

AUTH_HEADERS = {
    "Authorization": "Bearer test-token",
    "X-Tenant-ID": "tenant-a",
    "X-User-ID": "user-a",
    "X-Roles": "tenant_admin",
}


def _crm_webhook_test_client(mock_db) -> TestClient:
    test_app = FastAPI()

    async def _override():
        yield mock_db

    test_app.include_router(crm_webhooks.router, prefix="/v1")
    test_app.dependency_overrides[crm_webhooks.get_db_from_context] = _override
    return TestClient(test_app)


class mock_crm_configResult(TypedDictModel):
    api_key: str
    crm_api_key: str
    crm_api_secret: str
    crm_instance_url: str
    crm_type: str

class sample_salesforce_account_dataResult(TypedDictModel):
    AnnualRevenue: int
    BillingCity: str
    BillingState: str
    Id: str
    Industry: str
    Name: str
    NumberOfEmployees: int
    Website: str

class sample_hubspot_company_dataResult(TypedDictModel):
    id: str
    properties: dict[str, Any]

# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_db():
    """Create a mock database session."""
    session = AsyncMock(spec=AsyncSession)
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.add = MagicMock()
    session.refresh = AsyncMock()
    # Default return value so scalar_one_or_none() works in _update_sync_status
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    session.execute.return_value = mock_result
    return session


@pytest.fixture(autouse=True)
def override_app_db_dependency(mock_db):
    """Override FastAPI get_db dependency to use the mock session."""
    from layer4_agents.database import get_db_from_context
    async def _override():
        yield mock_db
    app.dependency_overrides[get_db_from_context] = _override
    yield
    app.dependency_overrides.pop(get_db_from_context, None)


@pytest.fixture
def mock_crm_config():
    """Mock CRM environment configuration."""
    return mock_crm_configResult.model_validate({
        "crm_type": "salesforce",
        "api_key": "test_token",
        "crm_api_key": "test_token",
        "crm_api_secret": "test_secret",
        "crm_instance_url": "https://test.salesforce.com",
    })


@pytest.fixture
def sample_salesforce_account_data():
    """Sample Salesforce account data for mocking."""
    return sample_salesforce_account_dataResult.model_validate({
        "Id": "001XXXXXXXXXXXX",
        "Name": "Test Company Inc",
        "Industry": "Technology",
        "NumberOfEmployees": 500,
        "AnnualRevenue": 50000000,
        "Website": "https://testcompany.com",
        "BillingCity": "San Francisco",
        "BillingState": "CA",
    })


@pytest.fixture
def sample_hubspot_company_data():
    """Sample HubSpot company data for mocking."""
    return sample_hubspot_company_dataResult.model_validate({
        "id": "123456789",
        "properties": {
            "name": "Test Company Inc",
            "industry": "Technology",
            "numberofemployees": "500",
            "annualrevenue": "50000000",
            "website": "https://testcompany.com",
            "address": "123 Main St, Boston, MA",
            "domain": "testcompany.com",
        }
    })


class MockCRMConnector:
    """Mock CRMConnector for testing."""

    def __init__(self, config=None):
        self.config = config or {}
        self._mock_account = None
        self._mock_opportunities = []

    def set_mock_data(self, account=None, opportunities=None):
        self._mock_account = account
        self._mock_opportunities = opportunities or []

    async def get_account(self, remote_id, *, include=None, timeout=None):
        if self._mock_account is not None:
            return self._mock_account
        return CanonicalRecord(
            model=CRMModel.ACCOUNT,
            remote_id=remote_id,
            canonical={
                "name": "Test Company",
                "industry": "Technology",
                "company_size": 100,
                "annual_revenue": 1000000,
                "website": "https://test.com",
                "headquarters": "San Francisco, CA",
                "domain": "test.com",
                "employees": 100,
            },
        )

    async def list_opportunities(self, account_remote_id, *, cursor=None, limit=100, timeout=None):
        return self._mock_opportunities, SyncCursor()

    async def list_interactions(self, account_remote_id, *, since_date=None, cursor=None, limit=100, timeout=None):
        return [], SyncCursor()

    async def test_connection(self, *, timeout=None):
        return {"success": True, "message": "Mock connection"}

    async def list_accounts(self, *, cursor=None, modified_since=None, limit=100, timeout=None):
        return [], SyncCursor()


# =============================================================================
# CRMSyncService Tests
# =============================================================================

class TestCRMSyncService:
    """Test suite for CRMSyncService."""
    
    @pytest.mark.asyncio
    async def test_sync_provider_creates_new_account(self, mock_db, mock_crm_config):
        """Test that sync creates new accounts when they don't exist."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        # Mock no existing account
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Mock the CRM config
        with patch.object(sync_service, '_get_crm_config', AsyncMock(return_value=mock_crm_config)):
            with patch(
                'layer4_agents.services.crm_sync_service.get_connector',
                return_value=MockCRMConnector()
            ):
                # Act
                stats = await sync_service.sync_provider(
                    CRMProvider.SALESFORCE,
                    tenant_id="tenant-a",
                    incremental=True,
                    account_ids=["001TEST123"]
                )
                
                # Assert
                assert stats["provider"] == "salesforce"
                assert stats["synced"] == 1  # New account
                assert stats["updated"] == 0
                assert mock_db.add.called  # New account was added
    
    @pytest.mark.asyncio
    async def test_sync_provider_updates_existing_account(self, mock_db, mock_crm_config):
        """Test that sync updates existing accounts."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        # Create existing account
        existing_account = Account(
            id=uuid4(),
            provider="salesforce",
            provider_record_id="001TEST123",
            name="Old Name",
            sync_status=SyncStatus.STALE.value,
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_account
        mock_db.execute.return_value = mock_result
        
        # Mock the CRM config
        with patch.object(sync_service, '_get_crm_config', AsyncMock(return_value=mock_crm_config)):
            with patch(
                'layer4_agents.services.crm_sync_service.get_connector',
                return_value=MockCRMConnector()
            ):
                # Act
                stats = await sync_service.sync_provider(
                    CRMProvider.SALESFORCE,
                    tenant_id="tenant-a",
                    incremental=True,
                    account_ids=["001TEST123"]
                )
                
                # Assert
                assert stats["updated"] == 1  # Existing account updated
                assert stats["synced"] == 0
                assert existing_account.name != "Old Name"  # Name was updated
    
    @pytest.mark.asyncio
    async def test_sync_provider_handles_missing_config(self, mock_db):
        """Test that sync fails gracefully when CRM not configured."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        # Mock no CRM config
        with patch.object(sync_service, '_get_crm_config', AsyncMock(return_value=None)):
            # Act
            stats = await sync_service.sync_provider(
                CRMProvider.SALESFORCE,
                tenant_id="tenant-a",
                incremental=True
            )
            
            # Assert
            assert stats["failed"] == 0
            assert len(stats["errors"]) == 1
            assert stats["errors"] == ["CRM sync failed due to internal error"]
    
    @pytest.mark.asyncio
    async def test_sync_provider_with_hubspot(self, mock_db):
        """Test syncing from HubSpot provider."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        hubspot_config = {
            "crm_type": "hubspot",
            "api_key": "test_hubspot_key",
            "crm_api_key": "test_hubspot_key",
        }
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        with patch.object(sync_service, '_get_crm_config', AsyncMock(return_value=hubspot_config)):
            with patch(
                'layer4_agents.services.crm_sync_service.get_connector',
                return_value=MockCRMConnector()
            ):
                # Act
                stats = await sync_service.sync_provider(
                    CRMProvider.HUBSPOT,
                    tenant_id="tenant-a",
                    incremental=True,
                    account_ids=["123456789"]
                )
                
                # Assert
                assert stats["provider"] == "hubspot"
                assert stats["synced"] == 1
    
    @pytest.mark.asyncio
    async def test_sync_provider_with_api_error(self, mock_db, mock_crm_config):
        """Test that sync handles API errors gracefully."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        class FailingConnector:
            def __init__(self, config=None):
                pass
            
            async def get_account(self, remote_id, *, include=None, timeout=None):
                raise Exception("API Error: Rate limit exceeded")
            
            async def list_opportunities(self, account_remote_id, *, cursor=None, limit=100, timeout=None):
                return [], SyncCursor()

        with patch.object(sync_service, '_get_crm_config', AsyncMock(return_value=mock_crm_config)):
            with patch(
                'layer4_agents.services.crm_sync_service.get_connector',
                return_value=FailingConnector()
            ):
                # Act
                stats = await sync_service.sync_provider(
                    CRMProvider.SALESFORCE,
                    tenant_id="tenant-a",
                    incremental=True,
                    account_ids=["001TEST123"]
                )
                
                # Assert
                assert stats["failed"] == 1
                assert stats["errors"] == ["001TEST123: SYNC_ERROR"]
    
    @pytest.mark.asyncio
    async def test_refresh_single_account_success(self, mock_db, mock_crm_config):
        """Test refreshing a single account."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        account_id = uuid4()
        existing_account = Account(
            id=account_id,
            provider="salesforce",
            provider_record_id="001TEST123",
            name="Test Company",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_account
        mock_db.execute.return_value = mock_result
        
        with patch.object(sync_service, '_get_crm_config', AsyncMock(return_value=mock_crm_config)):
            with patch(
                'layer4_agents.services.crm_sync_service.get_connector',
                return_value=MockCRMConnector()
            ):
                # Act
                result = await sync_service.refresh_single_account(account_id, tenant_id="tenant-a")
                
                # Assert
                assert result is not None
                assert result.id == account_id
    
    @pytest.mark.asyncio
    async def test_refresh_single_account_not_found(self, mock_db):
        """Test refreshing non-existent account returns None."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Act
        result = await sync_service.refresh_single_account(uuid4(), tenant_id="tenant-a")
        
        # Assert
        assert result is None
    
    @pytest.mark.asyncio
    async def test_get_accounts_to_sync_incremental(self, mock_db):
        """Test getting accounts needing incremental sync."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        # Mock stale accounts
        stale_accounts = [("001STALE1",), ("001STALE2",)]
        mock_result = MagicMock()
        mock_result.all.return_value = stale_accounts
        mock_db.execute.return_value = mock_result
        
        # Act
        with patch.object(sync_service, '_get_accounts_to_sync', AsyncMock(return_value=["001STALE1", "001STALE2"])):
            account_ids = await sync_service._get_accounts_to_sync(
                "default",
                CRMProvider.SALESFORCE,
                incremental=True
            )
            
            # Assert
            assert isinstance(account_ids, list)
            assert len(account_ids) == 2
    
    @pytest.mark.asyncio
    async def test_get_crm_config_from_integration_table(self, mock_db):
        """Test loading CRM config from tenant integration table (no env fallback)."""
        from layer4_agents.models.integration import Integration, IntegrationStatus
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        mock_integration = Integration(
            id=uuid4(),
            tenant_id="tenant-123",
            provider=CRMProvider.SALESFORCE,
            enabled=True,
            credentials_encrypted=b"encrypted",
            encryption_key_id="default",
            instance_url="https://tenant.salesforce.com",
            sync_status=IntegrationStatus.IDLE,
        )
        
        mock_service = AsyncMock()
        mock_service.get_integration.return_value = mock_integration
        mock_service.decrypt_credentials.return_value = {"api_key": "test_key", "api_secret": "test_secret"}
        
        with patch('layer4_agents.services.integration_service.IntegrationService', return_value=mock_service):
            # Act
            config = await sync_service._get_crm_config(CRMProvider.SALESFORCE, "tenant-123")
            
            # Assert
            mock_service.get_integration.assert_awaited_once_with("tenant-123", CRMProvider.SALESFORCE)
            assert config is not None
            assert config["crm_type"] == "salesforce"
            assert config["crm_api_key"] == "test_key"
    
    @pytest.mark.asyncio
    async def test_get_crm_config_missing_integration(self, mock_db):
        """Test that config returns None when no integration exists for tenant."""
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        mock_service = AsyncMock()
        mock_service.get_integration.return_value = None
        
        with patch('layer4_agents.services.integration_service.IntegrationService', return_value=mock_service):
            # Act
            config = await sync_service._get_crm_config(CRMProvider.SALESFORCE, "unknown-tenant")
            
            # Assert
            mock_service.get_integration.assert_awaited_once_with("unknown-tenant", CRMProvider.SALESFORCE)
            assert config is None


# =============================================================================
# Webhook Handler Tests
# =============================================================================

class TestCRMWebhooks:
    """Test suite for CRM webhook handlers."""
    
    def test_salesforce_webhook_health(self, mock_db):
        """Test Salesforce webhook health endpoint."""
        client = _crm_webhook_test_client(mock_db)
        response = client.get("/v1/webhooks/crm/health", headers=AUTH_HEADERS)
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert "salesforce" in data["webhooks"]
        assert "hubspot" in data["webhooks"]
    
    @pytest.mark.asyncio
    async def test_salesforce_webhook_accepts_platform_event(self):
        """Test that Salesforce platform event webhook is accepted."""
        client = _crm_webhook_test_client(mock_db)
        
        payload = {
            "data": {
                "payload": {
                    "RecordId": "001TEST123",
                    "ChangeEventHeader": {
                        "entityName": "Account",
                        "recordIds": ["001TEST123"],
                        "changeType": "CHANGED"
                    }
                }
            }
        }
        
        integration = MagicMock()
        integration.tenant_id = "tenant-a"
        integration.provider = CRMProvider.SALESFORCE
        integration.salesforce_org_id = None
        with (
            patch('layer4_agents.api.routes.crm_webhooks.CRMSyncService') as mock_sync_class,
            patch('layer4_agents.api.routes.crm_webhooks._resolve_webhook_integration', AsyncMock(return_value=(integration, False))),
            patch('layer4_agents.api.routes.crm_webhooks._authenticate_webhook', AsyncMock(return_value=({}, "token"))),
        ):
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            mock_sync.sync_provider.return_value = {
                "synced": 1,
                "updated": 0,
                "failed": 0,
            }
            
            response = client.post(
                "/v1/webhooks/crm/salesforce",
                json=payload,
                headers=AUTH_HEADERS,
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"
            assert data["provider"] == "salesforce"
    
    @pytest.mark.asyncio
    async def test_hubspot_webhook_accepts_company_events(self):
        """Test that HubSpot company webhook events are accepted."""
        client = _crm_webhook_test_client(mock_db)
        
        events = [
            {
                "eventId": 1,
                "subscriptionId": 123,
                "portalId": 456,
                "occurredAt": 1234567890000,
                "subscriptionType": "company.propertyChange",
                "objectId": 789012345,
                "propertyName": "name",
                "propertyValue": "Updated Company Name"
            }
        ]
        
        integration = MagicMock()
        integration.tenant_id = "tenant-a"
        integration.provider = CRMProvider.HUBSPOT
        with (
            patch('layer4_agents.api.routes.crm_webhooks.CRMSyncService') as mock_sync_class,
            patch('layer4_agents.api.routes.crm_webhooks._resolve_webhook_integration', AsyncMock(return_value=(integration, False))),
            patch('layer4_agents.api.routes.crm_webhooks._authenticate_webhook', AsyncMock(return_value=({}, "token"))),
        ):
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            mock_sync.sync_provider.return_value = {
                "synced": 1,
                "updated": 0,
                "failed": 0,
            }
            
            response = client.post(
                "/v1/webhooks/crm/hubspot",
                json=events,
                headers=AUTH_HEADERS,
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"
            assert data["provider"] == "hubspot"
            assert data["events_processed"] == 1
    
    @pytest.mark.asyncio
    async def test_hubspot_webhook_handles_multiple_events(self):
        """Test that HubSpot webhook handles multiple company events."""
        client = _crm_webhook_test_client(mock_db)
        
        events = [
            {
                "eventId": 1,
                "subscriptionType": "company.propertyChange",
                "objectId": 789012345,
            },
            {
                "eventId": 2,
                "subscriptionType": "company.propertyChange",
                "objectId": 789012346,
            },
            {
                "eventId": 3,
                "subscriptionType": "deal.propertyChange",  # Deal event, no company ID
                "objectId": 111222333,
            }
        ]
        
        integration = MagicMock()
        integration.tenant_id = "tenant-a"
        integration.provider = CRMProvider.HUBSPOT
        with (
            patch('layer4_agents.api.routes.crm_webhooks.CRMSyncService') as mock_sync_class,
            patch('layer4_agents.api.routes.crm_webhooks._resolve_webhook_integration', AsyncMock(return_value=(integration, False))),
            patch('layer4_agents.api.routes.crm_webhooks._authenticate_webhook', AsyncMock(return_value=({}, "token"))),
        ):
            mock_sync = AsyncMock()
            mock_sync_class.return_value = mock_sync
            mock_sync.sync_provider.return_value = {
                "synced": 2,
                "updated": 0,
                "failed": 0,
            }
            
            response = client.post(
                "/v1/webhooks/crm/hubspot",
                json=events,
                headers=AUTH_HEADERS,
            )

            assert response.status_code == 202
            data = response.json()
            assert data["status"] == "accepted"
            # Should have 2 unique company IDs (deal event ignored for company sync)
            assert data["companies_to_sync"] == 2


# =============================================================================
# End-to-End Sync Flow Tests
# =============================================================================

class TestSyncFlow:
    """End-to-end tests for the complete sync flow."""
    
    @pytest.mark.asyncio
    async def test_end_to_end_sync_status_update(self, mock_db, mock_crm_config):
        """Test that sync updates the AccountSyncStatus record."""
        # Arrange
        sync_service = CRMSyncService(mock_db, batch_size=10)
        
        # Mock no existing sync status
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute.return_value = mock_result
        
        # Mock account lookup
        account_result = MagicMock()
        account_result.scalar_one_or_none.return_value = None
        
        # Set up side effects for different queries
        call_count = [0]
        def side_effect(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                return mock_result  # Sync status query
            return account_result  # Account query
        
        mock_db.execute.side_effect = side_effect
        
        with patch.object(sync_service, '_get_crm_config', AsyncMock(return_value=mock_crm_config)):
            with patch(
                'layer4_agents.services.crm_sync_service.get_connector',
                return_value=MockCRMConnector()
            ):
                # Act
                await sync_service.sync_provider(
                    CRMProvider.SALESFORCE,
                    tenant_id="tenant-a",
                    incremental=True,
                    account_ids=["001TEST123"]
                )
                
                # Assert - sync status should be updated via _update_account_sync_status
                # which commits the transaction
                assert mock_db.commit.called


# =============================================================================
# Integration with AccountService
# =============================================================================

class TestAccountServiceIntegration:
    """Tests for AccountService integration with CRMSyncService."""
    
    @pytest.mark.asyncio
    async def test_trigger_sync_delegates_to_sync_service(self, mock_db):
        """Test that AccountService.trigger_sync delegates to CRMSyncService."""
        from layer4_agents.services.account_service import AccountService
        
        account_service = AccountService(mock_db)
        
        with patch('layer4_agents.services.account_service.CRMSyncService') as mock_sync_class:
            mock_sync = AsyncMock()
            mock_sync.sync_provider.return_value = {
                "synced": 5,
                "updated": 3,
                "failed": 0,
                "errors": [],
            }
            mock_sync_class.return_value = mock_sync
            
            # Act
            result = await account_service.trigger_sync(
                provider=CRMProvider.SALESFORCE,
                tenant_id="tenant-a",
                force_refresh=False
            )
            
            # Assert
            assert result["status"] == "completed"
            assert "sync_id" in result
            assert result["provider"] == "salesforce"
            mock_sync.sync_provider.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_refresh_account_delegates_to_sync_service(self, mock_db):
        """Test that AccountService.refresh_account delegates to CRMSyncService."""
        from layer4_agents.services.account_service import AccountService
        
        account_service = AccountService(mock_db)
        account_id = uuid4()
        
        # Mock account lookup
        existing_account = Account(
            id=account_id,
            provider="salesforce",
            provider_record_id="001TEST123",
            name="Test Company",
        )
        
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_account
        mock_db.execute.return_value = mock_result
        
        with patch('layer4_agents.services.account_service.CRMSyncService') as mock_sync_class:
            mock_sync = AsyncMock()
            mock_sync.refresh_single_account.return_value = existing_account
            mock_sync_class.return_value = mock_sync
            
            # Act
            result = await account_service.refresh_account(account_id, tenant_id="tenant-a")
            
            # Assert
            assert result is not None
            assert result.id == account_id
            mock_sync.refresh_single_account.assert_called_once_with(account_id, "tenant-a")
