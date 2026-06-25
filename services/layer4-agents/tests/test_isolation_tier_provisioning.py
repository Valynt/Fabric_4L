from __future__ import annotations

"""Tests for S2-07: Unsupported isolation tiers rejected at provisioning time.

Verifies:
- isolation_tier="schema" raises ValueError at _validate_request, before any DB write
- isolation_tier="database" raises ValueError at _validate_request, before any DB write
- isolation_tier="shared" passes validation (the only supported tier)
- Error message names the unsupported tier and states the supported alternative
- get_tiered_db_session raises 422 (not 501) for schema/database tiers
"""


from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException

from layer4_agents.services.tenant_provisioning import (
    TenantProvisioningService,
    TenantProvisionRequest,
)


def _make_service() -> TenantProvisioningService:
    return TenantProvisioningService(db_session=AsyncMock(), neo4j_driver=None)


# ---------------------------------------------------------------------------
# Provisioning validation
# ---------------------------------------------------------------------------


def test_schema_tier_rejected_at_validation():
    """isolation_tier='schema' must raise ValueError before any DB access."""
    service = _make_service()
    request = TenantProvisionRequest(
        tenant_name="test-tenant",
        admin_email="admin@example.com",
        isolation_tier="schema",
    )
    with pytest.raises(ValueError) as exc_info:
        service._validate_request(request)

    msg = str(exc_info.value)
    assert "schema" in msg
    assert "shared" in msg  # must name the supported alternative


def test_database_tier_rejected_at_validation():
    """isolation_tier='database' must raise ValueError before any DB access."""
    service = _make_service()
    request = TenantProvisionRequest(
        tenant_name="test-tenant",
        admin_email="admin@example.com",
        isolation_tier="database",
    )
    with pytest.raises(ValueError) as exc_info:
        service._validate_request(request)

    msg = str(exc_info.value)
    assert "database" in msg
    assert "shared" in msg


def test_shared_tier_passes_validation():
    """isolation_tier='shared' must not raise."""
    service = _make_service()
    request = TenantProvisionRequest(
        tenant_name="test-tenant",
        admin_email="admin@example.com",
        isolation_tier="shared",
    )
    # Must not raise
    service._validate_request(request)


def test_unknown_tier_rejected_at_validation():
    """Unknown tier names must raise ValueError."""
    service = _make_service()
    request = TenantProvisionRequest(
        tenant_name="test-tenant",
        admin_email="admin@example.com",
        isolation_tier="row_level",
    )
    with pytest.raises(ValueError):
        service._validate_request(request)


@pytest.mark.asyncio
async def test_schema_tier_rejected_before_db_write():
    """provision_tenant with schema tier must raise before any DB execute call."""
    mock_db = AsyncMock()
    service = TenantProvisioningService(db_session=mock_db, neo4j_driver=None)

    request = TenantProvisionRequest(
        tenant_name="test-tenant",
        admin_email="admin@example.com",
        isolation_tier="schema",
    )

    with pytest.raises(ValueError):
        await service.provision_tenant(request)

    # No DB writes should have occurred
    mock_db.execute.assert_not_called()


# ---------------------------------------------------------------------------
# get_tiered_db_session: 422 not 501 for reserved tiers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_get_tiered_db_session_schema_raises_422():
    """get_tiered_db_session with schema tier must raise HTTP 422, not 501."""
    import uuid

    from layer4_agents.database import get_tiered_db_session

    tenant_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        async with get_tiered_db_session(tenant_id, isolation_tier="schema"):
            pass  # pragma: no cover

    assert exc_info.value.status_code == 422
    assert "shared" in exc_info.value.detail


@pytest.mark.asyncio
async def test_get_tiered_db_session_database_raises_422():
    """get_tiered_db_session with database tier must raise HTTP 422, not 501."""
    import uuid

    from layer4_agents.database import get_tiered_db_session

    tenant_id = uuid.uuid4()

    with pytest.raises(HTTPException) as exc_info:
        async with get_tiered_db_session(tenant_id, isolation_tier="database"):
            pass  # pragma: no cover

    assert exc_info.value.status_code == 422


@pytest.mark.asyncio
async def test_get_tiered_db_session_emits_deprecation_warning():
    """get_tiered_db_session must emit DeprecationWarning on every call."""
    import uuid
    import warnings

    from layer4_agents.database import get_tiered_db_session

    tenant_id = uuid.uuid4()

    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        with pytest.raises(Exception):
            # schema tier raises 422 — we just need the warning to fire first
            async with get_tiered_db_session(tenant_id, isolation_tier="schema"):
                pass  # pragma: no cover

    deprecation_warnings = [w for w in caught if issubclass(w.category, DeprecationWarning)]
    assert deprecation_warnings, "Expected a DeprecationWarning from get_tiered_db_session()"
    assert "get_db_from_context" in str(deprecation_warnings[0].message)


# ---------------------------------------------------------------------------
# db_session_for_context: 422 not 501 for unsupported tiers
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_db_session_for_context_unsupported_tier_raises_422():
    """db_session_for_context with an unsupported isolation tier must raise HTTP 422, not 501."""
    from unittest.mock import AsyncMock, patch

    from layer4_agents.database import db_session_for_context

    context = MagicMock()
    context.tenant_id = "00000000-0000-0000-0000-000000000001"
    context.isolation_tier = "database"  # unsupported

    # Patch SHARED_IDENTITY_AVAILABLE so the function proceeds past the guard
    with patch("layer4_agents.database.SHARED_IDENTITY_AVAILABLE", True), \
         patch("layer4_agents.database.validate_tenant_id", return_value="00000000-0000-0000-0000-000000000001"), \
         patch("layer4_agents.database.get_session_factory") as mock_factory:

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=False)
        mock_factory.return_value.return_value = mock_session

        with pytest.raises(HTTPException) as exc_info:
            async with db_session_for_context(context):
                pass  # pragma: no cover

    assert exc_info.value.status_code == 422
    assert "shared" in exc_info.value.detail
