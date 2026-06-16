"""Regression tests for Layer 3 tenant-scoped Cypher validation.

These tests prove that the static Cypher validator rejects tenant-owned
queries unless they contain an explicit tenant_id predicate bound to a
parameter, and that unsafe f-string interpolation is caught as an
unscoped query.
"""

import pytest

from src.utils.cypher_security import (
    TenantCypherValidationError,
    validate_tenant_scoped_cypher,
)


class TestTenantScopedCypherValidation:
    def test_query_with_tenant_predicate_passes(self):
        query = """
            MATCH (t:ROITemplate {tenant_id: $tenant_id})
            RETURN t
        """
        validate_tenant_scoped_cypher(query)

    def test_query_without_tenant_predicate_fails(self):
        query = """
            MATCH (t:ROITemplate)
            RETURN t
        """
        with pytest.raises(TenantCypherValidationError):
            validate_tenant_scoped_cypher(query)

    def test_query_with_alternative_tenant_param_passes(self):
        query = """
            MATCH (e:Evidence)
            WHERE e.tenant_id = $tenant_id
            RETURN e
        """
        validate_tenant_scoped_cypher(query)

    def test_query_with_injected_fstring_value_fails(self):
        # This mimics a regression where user input is interpolated directly.
        tenant = "malicious' OR '1'='1"
        query = f"MATCH (t:ROITemplate) WHERE t.name = '{tenant}' RETURN t"
        # The validator should reject this because it lacks a tenant predicate
        # and is built with unsafe interpolation.
        with pytest.raises(TenantCypherValidationError):
            validate_tenant_scoped_cypher(query)
