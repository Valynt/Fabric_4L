"""Tests for safe identifier handling in tenant provisioning DDL."""

import re
from unittest.mock import AsyncMock
from uuid import uuid4

import pytest

from layer4_agents.services.tenant_provisioning import TenantProvisioningService


def _safe_schema_name(tenant_id: str) -> str:
    """Derive the same schema name the service uses."""
    return f"tenant_{tenant_id.replace('-', '')[:8]}"


def test_derived_schema_name_is_safe_identifier():
    """Schema names derived from UUIDs must be simple PostgreSQL identifiers."""
    tenant_id = uuid4()
    schema_name = _safe_schema_name(str(tenant_id))
    assert re.match(r"^[a-z_][a-z0-9_]*$", schema_name)


@pytest.mark.parametrize(
    "malicious_input",
    [
        "tenant_; DROP TABLE users;--",
        'tenant_"quoted"',
        "tenant_ schema",
        "tenant_../etc",
    ],
)
def test_malicious_schema_names_are_rejected(malicious_input: str):
    """Strings that are not plain identifiers must fail the safety regex."""
    assert re.match(r"^[a-z_][a-z0-9_]*$", malicious_input) is None


@pytest.mark.asyncio
async def test_grant_statement_uses_quoted_identifiers():
    """The GRANT statement should safely quote derived identifiers."""
    fake_session = AsyncMock()
    service = TenantProvisioningService(db_session=fake_session, neo4j_driver=None)

    tenant_id = uuid4()
    await service._setup_postgres_rls(tenant_id=tenant_id, isolation_tier="schema")

    calls = [call.args[0] for call in fake_session.execute.await_args_list]
    grant_call = next((str(c) for c in calls if "GRANT USAGE" in str(c)), None)
    assert grant_call is not None

    schema_name = _safe_schema_name(str(tenant_id))
    assert f'GRANT USAGE ON SCHEMA "{schema_name}" TO "app_user"' in grant_call
