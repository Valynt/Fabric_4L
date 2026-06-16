import pytest

from layer4_agents.services.tenant_cypher import (
    TenantCypherValidationError,
    fetch_tenant_validated_records,
)


async def test_query_missing_tenant_predicate_is_rejected():
    with pytest.raises(TenantCypherValidationError, match="tenant"):
        await fetch_tenant_validated_records(
            driver=None,
            query="MATCH (n:ValueHypothesis) RETURN n",
            params={},
            tenant_id="tenant-123",
            operation="test",
        )


async def test_query_with_tenant_predicate_is_accepted():
    # Driver is None so execution will fail, but validation should pass.
    with pytest.raises(AttributeError):
        await fetch_tenant_validated_records(
            driver=None,
            query="MATCH (n:ValueHypothesis {tenant_id: $tenant_id}) RETURN n",
            params={},
            tenant_id="tenant-123",
            operation="test",
        )
