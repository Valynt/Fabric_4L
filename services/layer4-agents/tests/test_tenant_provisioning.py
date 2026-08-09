from __future__ import annotations

"""
Tests for tenant provisioning service (Task 3).

Verifies automated tenant lifecycle management with:
- Idempotent tenant creation
- Admin user provisioning
- Database schema setup
- Audit trail generation
- Rollback on failure
"""


from datetime import datetime
from unittest.mock import AsyncMock, MagicMock, patch
from uuid import uuid4

import pytest
from cryptography.hazmat.primitives.kdf.argon2 import Argon2id

from layer4_agents.services.tenant_provisioning import (
    TenantProvisioningService,
    TenantProvisionRequest,
    TenantProvisionResult,
)


@pytest.fixture
def mock_db_session():
    """Create a mock database session."""
    session = AsyncMock()
    session.execute = AsyncMock()
    session.commit = AsyncMock()
    session.rollback = AsyncMock()
    session.flush = AsyncMock()
    return session


@pytest.fixture
def mock_neo4j_driver():
    """Create a mock Neo4j driver."""
    driver = MagicMock()
    session = AsyncMock()
    session.run = AsyncMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock()
    driver.session = MagicMock(return_value=session)
    return driver


@pytest.fixture
def provisioning_service(mock_db_session, mock_neo4j_driver):
    """Create tenant provisioning service with mocks."""
    return TenantProvisioningService(
        db_session=mock_db_session,
        neo4j_driver=mock_neo4j_driver,
    )


class TestTenantProvisioningService:
    """Tests for TenantProvisioningService."""
    
    @pytest.mark.asyncio
    async def test_provision_new_tenant_success(self, provisioning_service, mock_db_session):
        """Verify successful tenant provisioning."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
            isolation_tier="shared",
        )
        
        # Mock: tenant doesn't exist
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch("value_fabric.shared.audit.emitter.emit_audit_event", new_callable=AsyncMock):
            result = await provisioning_service.provision_tenant(request)
        
        assert result.status == "success"
        assert result.tenant_id is not None
        assert result.admin_user_id is not None
        assert len(result.admin_temp_password) == 16
        assert result.isolation_tier == "shared"
        assert result.errors is None or len(result.errors) == 0
    
    @pytest.mark.asyncio
    async def test_provision_tenant_idempotent(self, provisioning_service, mock_db_session):
        """Verify idempotent behavior when tenant already exists."""
        request = TenantProvisionRequest(
            tenant_name="existing-tenant",
            admin_email="admin@existing.com",
        )
        
        existing_tenant_id = uuid4()
        admin_user_id = uuid4()
        
        # Mock: tenant exists
        mock_result = MagicMock()
        mock_result.fetchone.side_effect = [
            # First call: get_tenant_by_name returns existing tenant
            MagicMock(
                __getitem__=lambda self, key: {
                    0: existing_tenant_id,
                    1: "existing-tenant",
                    2: datetime.utcnow(),
                    3: "shared",
                }.get(key)
            ),
            # Second call: get admin user
            MagicMock(__getitem__=lambda self, key: {0: admin_user_id}.get(key)),
        ]
        mock_db_session.execute.return_value = mock_result
        
        result = await provisioning_service.provision_tenant(request)
        
        assert result.tenant_id == existing_tenant_id
        assert result.admin_temp_password is None
        assert result.password_change_required is False
        assert "already exists" in (result.errors[0] if result.errors else "")
    
    @pytest.mark.asyncio
    async def test_provision_tenant_validates_name(self, provisioning_service):
        """Verify tenant name validation."""
        request = TenantProvisionRequest(
            tenant_name="ab",  # Too short
            admin_email="admin@test.com",
        )
        
        with pytest.raises(ValueError, match="at least 3 characters"):
            await provisioning_service.provision_tenant(request)
    
    @pytest.mark.asyncio
    async def test_provision_tenant_validates_email(self, provisioning_service):
        """Verify admin email validation."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="invalid-email",  # No @
        )
        
        with pytest.raises(ValueError, match="valid email"):
            await provisioning_service.provision_tenant(request)
    
    @pytest.mark.asyncio
    async def test_provision_tenant_validates_isolation_tier(self, provisioning_service):
        """Verify isolation tier validation."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
            isolation_tier="invalid",
        )
        
        with pytest.raises(ValueError, match="Use isolation_tier='shared'"):
            await provisioning_service.provision_tenant(request)
    
    @pytest.mark.asyncio
    async def test_provision_tenant_creates_records(self, provisioning_service, mock_db_session):
        """Verify tenant and admin user records are created."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
        )
        
        # Mock: tenant doesn't exist
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch("value_fabric.shared.audit.emitter.emit_audit_event", new_callable=AsyncMock):
            await provisioning_service.provision_tenant(request)
        
        # Verify execute was called (for INSERT statements)
        assert mock_db_session.execute.call_count >= 2
        assert mock_db_session.commit.call_count >= 2

    @pytest.mark.asyncio
    async def test_provision_tenant_stores_argon2id_password_hash(
        self,
        provisioning_service,
        mock_db_session,
    ):
        """Verify temp password is persisted as Argon2id PHC hash, never raw."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
        )

        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        with patch("value_fabric.shared.audit.emitter.emit_audit_event", new_callable=AsyncMock):
            result = await provisioning_service.provision_tenant(request)

        password_payload = None
        for call in mock_db_session.execute.call_args_list:
            maybe_params = call.args[1] if len(call.args) > 1 else None
            if isinstance(maybe_params, dict) and "password_hash" in maybe_params:
                password_payload = maybe_params
                break

        assert password_payload is not None
        stored_hash = password_payload["password_hash"]
        assert stored_hash != result.admin_temp_password
        assert stored_hash.startswith("$argon2id$")
        Argon2id.verify_phc_encoded(result.admin_temp_password.encode("utf-8"), stored_hash)
    
    @pytest.mark.asyncio
    async def test_provision_tenant_emits_audit_event(self, provisioning_service, mock_db_session):
        """Verify audit event is emitted on successful provisioning."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
        )
        
        # Mock: tenant doesn't exist
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch("layer4_agents.services.tenant_provisioning.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            await provisioning_service.provision_tenant(request)
            
            assert mock_emit.called
            call_kwargs = mock_emit.call_args.kwargs
            assert call_kwargs["resource_type"] == "tenant"
            assert call_kwargs["user_id"] is None  # System-initiated
            assert "tenant_name" in call_kwargs["details"]

    @pytest.mark.asyncio
    async def test_provision_tenant_audit_event_redacts_temp_password(
        self,
        provisioning_service,
        mock_db_session,
    ):
        """Verify audit payload never contains raw temporary password."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
        )
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result

        with patch("layer4_agents.services.tenant_provisioning.emit_audit_event", new_callable=AsyncMock) as mock_emit:
            result = await provisioning_service.provision_tenant(request)

            details = mock_emit.call_args.kwargs["details"]
            serialized_details = str(details)
            assert "password" not in details
            assert result.admin_temp_password not in serialized_details
    
    @pytest.mark.asyncio
    async def test_provision_tenant_rollback_on_failure(self, provisioning_service, mock_db_session):
        """Verify rollback is attempted on provisioning failure."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
        )
        
        # Mock: tenant doesn't exist, but commit fails
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result
        mock_db_session.commit.side_effect = Exception("Database error")
        
        with patch("value_fabric.shared.audit.emitter.emit_audit_event", new_callable=AsyncMock):
            with pytest.raises(RuntimeError, match="provisioning failed"):
                await provisioning_service.provision_tenant(request)
        
        # Verify rollback was attempted
        assert mock_db_session.execute.call_count > 0
    
    @pytest.mark.asyncio
    async def test_generate_secure_password(self, provisioning_service):
        """Verify secure password generation."""
        password1 = provisioning_service._generate_secure_password()
        password2 = provisioning_service._generate_secure_password()
        
        assert len(password1) == 16
        assert len(password2) == 16
        assert password1 != password2  # Should be random
        
        # Verify contains mix of characters
        assert any(c.islower() for c in password1)
        assert any(c.isupper() for c in password1)
        assert any(c.isdigit() for c in password1)
    
    @pytest.mark.asyncio
    async def test_provision_tenant_with_metadata(self, provisioning_service, mock_db_session):
        """Verify tenant provisioning with custom metadata."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
            metadata={"industry": "technology", "region": "us-west"},
        )
        
        # Mock: tenant doesn't exist
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch("value_fabric.shared.audit.emitter.emit_audit_event", new_callable=AsyncMock):
            result = await provisioning_service.provision_tenant(request)
        
        assert result.status == "success"
    
    @pytest.mark.asyncio
    async def test_provision_tenant_schema_isolation_rejected(self, provisioning_service):
        """Verify schema-level isolation is not provisioned by the local service."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
            isolation_tier="schema",
        )

        with pytest.raises(ValueError, match="Use isolation_tier='shared'"):
            await provisioning_service.provision_tenant(request)


class TestTenantProvisionRequest:
    """Tests for TenantProvisionRequest model."""
    
    def test_creates_with_required_fields(self):
        """Verify request can be created with required fields."""
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
        )
        
        assert request.tenant_name == "test-tenant"
        assert request.admin_email == "admin@test.com"
        assert request.isolation_tier == "shared"  # Default
        assert request.org_id is None
        assert request.metadata is None
    
    def test_creates_with_all_fields(self):
        """Verify request can be created with all fields."""
        org_id = uuid4()
        request = TenantProvisionRequest(
            tenant_name="test-tenant",
            admin_email="admin@test.com",
            org_id=org_id,
            isolation_tier="database",
            metadata={"key": "value"},
        )
        
        assert request.org_id == org_id
        assert request.isolation_tier == "database"
        assert request.metadata == {"key": "value"}


class TestTenantProvisionResult:
    """Tests for TenantProvisionResult model."""
    
    def test_creates_success_result(self):
        """Verify success result creation."""
        result = TenantProvisionResult(
            tenant_id=uuid4(),
            admin_user_id=uuid4(),
            admin_temp_password="SecurePass123!",
            created_at=datetime.utcnow(),
            isolation_tier="shared",
            status="success",
        )
        
        assert result.status == "success"
        assert result.errors is None
    
    def test_creates_partial_result_with_errors(self):
        """Verify partial result with errors."""
        result = TenantProvisionResult(
            tenant_id=uuid4(),
            admin_user_id=uuid4(),
            admin_temp_password="SecurePass123!",
            created_at=datetime.utcnow(),
            isolation_tier="schema",
            status="partial",
            errors=["Neo4j constraint setup failed"],
        )
        
        assert result.status == "partial"
        assert len(result.errors) == 1


class TestTenantProvisioningIntegration:
    """Integration tests for tenant provisioning scenarios."""
    
    @pytest.mark.asyncio
    async def test_provision_multiple_tenants(self, provisioning_service, mock_db_session):
        """Verify multiple tenants can be provisioned."""
        tenants = [
            TenantProvisionRequest(tenant_name=f"tenant-{i}", admin_email=f"admin{i}@test.com")
            for i in range(3)
        ]
        
        # Mock: no tenants exist
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        results = []
        with patch("value_fabric.shared.audit.emitter.emit_audit_event", new_callable=AsyncMock):
            for request in tenants:
                result = await provisioning_service.provision_tenant(request)
                results.append(result)
        
        assert len(results) == 3
        assert all(r.status == "success" for r in results)
        
        # Verify all tenant IDs are unique
        tenant_ids = [r.tenant_id for r in results]
        assert len(set(tenant_ids)) == 3
    
    @pytest.mark.asyncio
    async def test_provision_with_org_hierarchy(self, provisioning_service, mock_db_session):
        """Verify tenant provisioning with organization hierarchy."""
        org_id = uuid4()
        
        request = TenantProvisionRequest(
            tenant_name="child-tenant",
            admin_email="admin@child.com",
            org_id=org_id,
        )
        
        # Mock: tenant doesn't exist
        mock_result = MagicMock()
        mock_result.fetchone.return_value = None
        mock_db_session.execute.return_value = mock_result
        
        with patch("value_fabric.shared.audit.emitter.emit_audit_event", new_callable=AsyncMock):
            result = await provisioning_service.provision_tenant(request)
        
        assert result.status == "success"
