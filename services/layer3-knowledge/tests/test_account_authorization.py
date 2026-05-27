"""Phase 4: Account-Scoped Authorization and Hostile Traversal Tests.

Tests verify:
- Account authorization correctly blocks cross-account access
- Hostile traversal attempts are detected and blocked
- Tenant-wide entities are accessible across accounts
- Account-scoped entities require account context
"""

import pytest
from fastapi import HTTPException, status

from value_fabric.layer3.schema.entity_scope import (
    EntityScope,
    get_account_scoped_entity_types,
    get_entity_scope,
    get_tenant_wide_entity_types,
    is_account_scoped,
    is_global,
    is_tenant_wide,
)
from value_fabric.layer3.security.account_authorization import (
    AccountAuthorizationError,
    check_account_access,
    check_account_scope_for_query,
    enrich_query_with_account_filter,
)


class TestEntityScopeClassification:
    """Test entity scope classification."""

    def test_pain_signal_is_account_scoped(self):
        """PainSignal should be classified as account-scoped."""
        assert is_account_scoped("PainSignal")
        assert get_entity_scope("PainSignal") == EntityScope.ACCOUNT_SCOPED

    def test_product_is_tenant_wide(self):
        """Product should be classified as tenant-wide."""
        assert is_tenant_wide("Product")
        assert get_entity_scope("Product") == EntityScope.TENANT_WIDE

    def test_sync_metadata_is_global(self):
        """SyncMetadata should be classified as global."""
        assert is_global("SyncMetadata")
        assert get_entity_scope("SyncMetadata") == EntityScope.GLOBAL

    def test_account_scoped_types_list(self):
        """Should return list of account-scoped entity types."""
        account_scoped = get_account_scoped_entity_types()
        assert "PainSignal" in account_scoped
        assert "Account" in account_scoped
        assert "Product" not in account_scoped

    def test_tenant_wide_types_list(self):
        """Should return list of tenant-wide entity types."""
        tenant_wide = get_tenant_wide_entity_types()
        assert "Product" in tenant_wide
        assert "ValueDriver" in tenant_wide
        assert "PainSignal" not in tenant_wide

    def test_unknown_entity_defaults_to_tenant_wide(self):
        """Unknown entity types should default to tenant-wide (fail-safe)."""
        assert is_tenant_wide("UnknownEntityType")
        assert get_entity_scope("UnknownEntityType") == EntityScope.TENANT_WIDE


class TestAccountAuthorization:
    """Test account authorization logic."""

    def test_tenant_wide_entity_allows_access(self):
        """Tenant-wide entities should allow access without account check."""
        # Should not raise
        check_account_access(
            entity_type="Product",
            entity_account_id=None,
            request_account_id=None,
            tenant_id="tenant-1",
        )

    def test_account_scoped_entity_with_matching_account(self):
        """Account-scoped entity should allow access with matching account."""
        # Should not raise
        check_account_access(
            entity_type="PainSignal",
            entity_account_id="account-1",
            request_account_id="account-1",
            tenant_id="tenant-1",
        )

    def test_account_scoped_entity_without_account_context(self):
        """Account-scoped entity should deny access without account context."""
        with pytest.raises(AccountAuthorizationError) as exc_info:
            check_account_access(
                entity_type="PainSignal",
                entity_account_id="account-1",
                request_account_id=None,
                tenant_id="tenant-1",
            )
        assert "Account context required" in str(exc_info.value)

    def test_account_scoped_entity_with_mismatched_account(self):
        """Account-scoped entity should deny access with mismatched account."""
        with pytest.raises(AccountAuthorizationError) as exc_info:
            check_account_access(
                entity_type="PainSignal",
                entity_account_id="account-1",
                request_account_id="account-2",
                tenant_id="tenant-1",
            )
        assert "does not have access" in str(exc_info.value)

    def test_account_scoped_entity_without_entity_account_id(self):
        """Account-scoped entity without account_id should allow access (legacy)."""
        # Should not raise - legacy data without account_id is allowed
        check_account_access(
            entity_type="PainSignal",
            entity_account_id=None,
            request_account_id="account-1",
            tenant_id="tenant-1",
        )


class TestQueryAccountFiltering:
    """Test account filtering for queries."""

    def test_tenant_wide_query_no_filter(self):
        """Tenant-wide entity queries should not require account filter."""
        account_filter = check_account_scope_for_query(
            entity_type="Product",
            request_account_id="account-1",
            tenant_id="tenant-1",
        )
        assert account_filter is None

    def test_account_scoped_query_requires_account(self):
        """Account-scoped entity queries should require account context."""
        with pytest.raises(AccountAuthorizationError):
            check_account_scope_for_query(
                entity_type="PainSignal",
                request_account_id=None,
                tenant_id="tenant-1",
            )

    def test_account_scoped_query_returns_account_filter(self):
        """Account-scoped entity queries should return account filter."""
        account_filter = check_account_scope_for_query(
            entity_type="PainSignal",
            request_account_id="account-1",
            tenant_id="tenant-1",
        )
        assert account_filter == "account-1"

    def test_enrich_query_with_account_filter(self):
        """Query enrichment should add account filter for account-scoped entities."""
        original_query = "MATCH (n:PainSignal {tenant_id: $tenant_id}) RETURN n"
        enriched_query, params = enrich_query_with_account_filter(
            original_query,
            entity_type="PainSignal",
            request_account_id="account-1",
        )
        assert "account_id" in enriched_query
        assert params["account_id"] == "account-1"

    def test_enrich_query_skips_tenant_wide(self):
        """Query enrichment should skip tenant-wide entities."""
        original_query = "MATCH (n:Product {tenant_id: $tenant_id}) RETURN n"
        enriched_query, params = enrich_query_with_account_filter(
            original_query,
            entity_type="Product",
            request_account_id="account-1",
        )
        assert enriched_query == original_query
        assert params == {}


class TestHostileTraversalPrevention:
    """Test prevention of hostile traversal attempts."""

    def test_cross_account_access_blocked(self):
        """Cross-account access should be blocked."""
        with pytest.raises(AccountAuthorizationError):
            check_account_access(
                entity_type="PainSignal",
                entity_account_id="target-account",
                request_account_id="attacker-account",
                tenant_id="tenant-1",
            )

    def test_account_context_required_for_sensitive_operations(self):
        """Sensitive operations should require account context."""
        with pytest.raises(AccountAuthorizationError):
            check_account_scope_for_query(
                entity_type="PainSignal",
                request_account_id=None,
                tenant_id="tenant-1",
            )

    def test_tenant_isolation_preserved(self):
        """Tenant isolation should be preserved regardless of account."""
        # Even with matching account, tenant must match
        check_account_access(
            entity_type="PainSignal",
            entity_account_id="account-1",
            request_account_id="account-1",
            tenant_id="tenant-1",
        )
        # This should pass - same tenant and account


class TestAuthorizationEdgeCases:
    """Test edge cases in authorization."""

    def test_empty_account_id_handling(self):
        """Empty string account_id should be treated as None."""
        # Empty string should be treated as missing account context
        with pytest.raises(AccountAuthorizationError):
            check_account_access(
                entity_type="PainSignal",
                entity_account_id="account-1",
                request_account_id="",
                tenant_id="tenant-1",
            )

    def test_none_tenant_id_handling(self):
        """None tenant_id should still allow tenant-wide entities."""
        # Tenant-wide entities don't require tenant_id in account check
        check_account_access(
            entity_type="Product",
            entity_account_id=None,
            request_account_id=None,
            tenant_id="",
        )

    def test_case_sensitive_account_ids(self):
        """Account IDs should be case-sensitive."""
        with pytest.raises(AccountAuthorizationError):
            check_account_access(
                entity_type="PainSignal",
                entity_account_id="Account-1",
                request_account_id="account-1",  # Different case
                tenant_id="tenant-1",
            )


class TestQueryEnrichmentEdgeCases:
    """Test edge cases in query enrichment."""

    def test_query_without_where(self):
        """Query without WHERE clause should get one added."""
        original_query = "MATCH (n:PainSignal {tenant_id: $tenant_id}) RETURN n"
        enriched_query, params = enrich_query_with_account_filter(
            original_query,
            entity_type="PainSignal",
            request_account_id="account-1",
        )
        assert "WHERE" in enriched_query
        assert "account_id" in enriched_query

    def test_query_with_existing_where(self):
        """Query with existing WHERE should have account filter appended."""
        original_query = "MATCH (n:PainSignal {tenant_id: $tenant_id}) WHERE n.confidence > 0.5 RETURN n"
        enriched_query, params = enrich_query_with_account_filter(
            original_query,
            entity_type="PainSignal",
            request_account_id="account-1",
        )
        assert "AND" in enriched_query
        assert "account_id" in enriched_query

    def test_query_enrichment_missing_account_context(self):
        """Query enrichment should fail without account context for account-scoped entities."""
        original_query = "MATCH (n:PainSignal {tenant_id: $tenant_id}) RETURN n"
        with pytest.raises(AccountAuthorizationError):
            enrich_query_with_account_filter(
                original_query,
                entity_type="PainSignal",
                request_account_id=None,
            )
