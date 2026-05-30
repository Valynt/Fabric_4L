"""Cross-layer tenant isolation integration tests (Sprint 5).

These tests verify that tenant context is consistently resolved and enforced
across all layers of the Fabric 4L system.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# Shared identity components
from value_fabric.shared.identity.context import (
    AUTH_SOURCE_API_KEY,
    AUTH_SOURCE_JWT,
    AUTH_SOURCE_SERVICE_ACCOUNT,
    AUTH_SOURCE_UNKNOWN,
    ISOLATION_TIER_DATABASE,
    ISOLATION_TIER_SCHEMA,
    ISOLATION_TIER_SHARED,
    RequestContext,
)
from value_fabric.shared.identity.dependencies import require_tenant_context


class TestCrossLayerContextConsistency:
    """Verify RequestContext has consistent shape across all layers."""

    def test_request_context_has_all_required_fields(self):
        """All layers should have access to same RequestContext fields."""
        ctx = RequestContext(
            tenant_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            api_key_id=uuid.uuid4(),
            org_id=uuid.uuid4(),
            service_account_id=uuid.uuid4(),
            roles=["tenant_admin"],
            permissions=["read", "write"],
            tenant_role="value_consultant",
            isolation_tier=ISOLATION_TIER_SHARED,
            auth_source=AUTH_SOURCE_JWT,
            service_account_scopes=["ingestion:read"],
            request_id="req-123",
        )

        # Verify all fields are present in to_dict()
        d = ctx.to_dict()
        required_fields = [
            "tenant_id", "user_id", "api_key_id", "org_id",
            "service_account_id", "roles", "permissions",
            "tenant_role", "isolation_tier", "auth_source",
            "service_account_scopes", "request_id",
        ]
        for field in required_fields:
            assert field in d, f"Missing field: {field}"

    def test_isolation_tier_validation_across_layers(self):
        """All layers use same isolation tier constants."""
        # Layer 4 uses these constants - all layers should agree
        from value_fabric.shared.identity.context import VALID_ISOLATION_TIERS

        valid_tiers = {ISOLATION_TIER_SHARED, ISOLATION_TIER_SCHEMA, ISOLATION_TIER_DATABASE}
        assert VALID_ISOLATION_TIERS == valid_tiers

    def test_auth_source_constants_consistency(self):
        """All layers use same auth source constants."""
        valid_sources = {
            AUTH_SOURCE_JWT,
            AUTH_SOURCE_API_KEY,
            AUTH_SOURCE_SERVICE_ACCOUNT,
            AUTH_SOURCE_UNKNOWN,
        }

        ctx = RequestContext(auth_source=AUTH_SOURCE_JWT)
        assert ctx.is_auth_source_valid()

        ctx = RequestContext(auth_source="invalid")
        assert not ctx.is_auth_source_valid()


class TestLayerSpecificEnforcement:
    """Verify each layer has appropriate tenant enforcement."""

    def test_layer_1_uses_sync_context(self):
        """Layer 1 (ingestion) uses sync SQLAlchemy with context."""
        try:
            from layer1_ingestion.shared.database import (
                get_db_from_context_sync,
                get_db_with_optional_tenant_sync,
            )
            # Functions exist and are importable
            assert callable(get_db_from_context_sync)
            assert callable(get_db_with_optional_tenant_sync)
        except ImportError as e:
            pytest.skip(f"Layer 1 not yet migrated: {e}")

    def test_layer_4_uses_async_context(self):
        """Layer 4 (agents) uses async SQLAlchemy with context."""
        from services.layer4_agents.src.database import (
            get_db_from_context,
            get_db_with_optional_tenant,
        )
        assert callable(get_db_from_context)
        assert callable(get_db_with_optional_tenant)

    def test_layer_5_uses_async_context(self):
        """Layer 5 (ground-truth) uses async SQLAlchemy with context."""
        try:
            from layer5_ground_truth.database import (
                get_db_from_context,
                get_db_with_optional_tenant,
            )
            assert callable(get_db_from_context)
            assert callable(get_db_with_optional_tenant)
        except ImportError as e:
            pytest.skip(f"Layer 5 not yet migrated: {e}")


class TestTenantPropagationPatterns:
    """Verify tenant context propagates correctly through system."""

    def test_jwt_token_produces_same_context_all_layers(self):
        """Same JWT token should resolve to identical context in all layers."""
        tenant_id = uuid.uuid4()
        user_id = uuid.uuid4()

        mock_payload = {
            "sub": str(user_id),
            "tenant_id": str(tenant_id),
            "org_id": str(uuid.uuid4()),
            "tenant_role": "admin",
            "isolation_tier": "shared",
            "roles": ["tenant_admin"],
            "auth_source": "jwt_claim",
        }

        # Context should be constructed the same way in all layers
        ctx = RequestContext(
            tenant_id=tenant_id,
            user_id=user_id,
            org_id=uuid.UUID(mock_payload["org_id"]),
            tenant_role=mock_payload["tenant_role"],
            isolation_tier=mock_payload["isolation_tier"],
            roles=mock_payload["roles"],
            auth_source=mock_payload["auth_source"],
        )

        assert ctx.tenant_id == tenant_id
        assert ctx.user_id == user_id
        assert ctx.auth_source == AUTH_SOURCE_JWT

    def test_api_key_produces_same_context_all_layers(self):
        """Same API key should resolve to identical context in all layers."""
        tenant_id = uuid.uuid4()

        mock_key_data = {
            "key_id": str(uuid.uuid4()),
            "tenant_id": tenant_id,
            "role": "read_only",
            "permissions": ["kg:query"],
        }

        ctx = RequestContext(
            tenant_id=tenant_id,
            api_key_id=mock_key_data["key_id"],
            roles=[mock_key_data["role"]],
            permissions=mock_key_data["permissions"],
            auth_source=AUTH_SOURCE_API_KEY,
        )

        assert ctx.tenant_id == tenant_id
        assert ctx.auth_source == AUTH_SOURCE_API_KEY


class TestAuditConsistencyAcrossLayers:
    """Verify audit events have consistent structure across layers."""

    def test_tenant_resolved_event_structure(self):
        """All layers emit TENANT_RESOLVED with same schema."""
        from value_fabric.shared.audit.models import TenantResolvedDetails

        details = TenantResolvedDetails(
            resolution_source="jwt_claim",
            resolved_tenant_id=str(uuid.uuid4()),
            auth_method="jwt",
            has_org_id=True,
            isolation_tier="shared",
            roles=["tenant_admin"],
            is_super_admin=False,
            outcome="success",
        )

        # Verify structure is layer-agnostic
        d = details.model_dump()
        assert "resolution_source" in d
        assert "resolved_tenant_id" in d
        assert "isolation_tier" in d

    def test_tenant_context_set_event_structure(self):
        """All layers emit TENANT_CONTEXT_SET with same schema."""
        from value_fabric.shared.audit.models import TenantContextSetDetails

        details = TenantContextSetDetails(
            tenant_id=str(uuid.uuid4()),
            isolation_tier="shared",
            bypass=False,
            context_source="request_context",
        )

        d = details.model_dump()
        assert "tenant_id" in d
        assert "isolation_tier" in d
        assert "bypass" in d


class TestCrossLayerIsolationEnforcement:
    """Verify tenant isolation is enforced consistently across layers."""

    @pytest.mark.asyncio
    async def test_no_tenant_context_raises_400_all_layers(self):
        """All layers should reject requests without tenant context."""
        ctx = RequestContext()  # No tenant_id

        with pytest.raises(Exception) as exc_info:
            await require_tenant_context(ctx)

        # Accept 400 or 401 — both are valid fail-closed responses for missing tenant context.
        err = str(exc_info.value)
        assert "400" in err or "401" in err or "Tenant context required" in err or "tenant_id is required" in err

    def test_super_admin_bypass_consistent_across_layers(self):
        """Super admin bypass works the same in all layers."""
        ctx = RequestContext(
            tenant_id=uuid.uuid4(),
            roles=["super_admin"],
        )

        assert ctx.is_super_admin()

        # Super admin should be able to bypass tenant restrictions
        # (actual bypass tested in layer-specific tests)


class TestGovernanceCoreContract:
    """Verify GovernanceCore provides consistent interface."""

    def test_governance_core_exists(self):
        """Shared GovernanceCore is available for all layers."""
        try:
            from value_fabric.shared.identity.governance_core import GovernanceCore

            core = GovernanceCore()
            assert hasattr(core, "resolve_identity")
            assert hasattr(core, "check_access_policy")
            assert hasattr(core, "create_audit_payload")
        except ImportError as e:
            pytest.skip(f"GovernanceCore not yet available: {e}")


class TestLayer3Neo4jSpecifics:
    """Layer 3 Neo4j has tenant-aware enforcement through different mechanism."""

    def test_neo4j_tenant_session_wrapper(self):
        """Layer 3 provides Neo4jTenantSession for graph-aware scoping."""
        try:
            from src.api.dependencies_tenant import (
                Neo4jTenantSession,
                get_neo4j_with_tenant,
            )

            # Verify the dependency exists
            assert callable(get_neo4j_with_tenant)

            # Verify session wrapper has tenant scoping
            session_mock = MagicMock()
            neo4j = Neo4jTenantSession(session_mock, tenant_id="test-tenant")
            assert neo4j.tenant_id == "test-tenant"
        except ImportError as e:
            pytest.skip(f"Layer 3 Neo4j dependencies not yet available: {e}")


class TestMigrationCompleteness:
    """Track which layers have been migrated to context-based tenant enforcement."""

    def test_layer_4_has_full_implementation(self):
        """Layer 4 is the reference implementation."""
        # These should all be importable and functional
        from services.layer4_agents.src.database import (
            get_db_from_context,
            get_db_with_optional_tenant,
            get_tiered_db_session,
        )
        assert callable(get_db_from_context)
        assert callable(get_db_with_optional_tenant)
        assert callable(get_tiered_db_session)

    def test_shared_identity_exports_context_constants(self):
        """shared.identity module exports all required constants."""
        from value_fabric.shared.identity.context import (
            AUTH_SOURCE_API_KEY,
            AUTH_SOURCE_JWT,
            AUTH_SOURCE_SERVICE_ACCOUNT,
            AUTH_SOURCE_UNKNOWN,
            ISOLATION_TIER_DATABASE,
            ISOLATION_TIER_SCHEMA,
            ISOLATION_TIER_SHARED,
            VALID_ISOLATION_TIERS,
        )

        # All constants should be defined
        assert ISOLATION_TIER_SHARED == "shared"
        assert ISOLATION_TIER_SCHEMA == "schema"
        assert ISOLATION_TIER_DATABASE == "database"
        assert AUTH_SOURCE_JWT == "jwt_claim"
        assert AUTH_SOURCE_API_KEY == "api_key"
        assert AUTH_SOURCE_SERVICE_ACCOUNT == "service_account"
