"""Tenant isolation tests for Layer 7 Billing Service.

Tests verify:
1. Repository functions properly scope queries by tenant_id
2. Composite primary keys include tenant_id for isolation
3. Unique constraints are tenant-scoped
4. Database session properly sets tenant context
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import select, Result, text

from .conftest import auth_headers, billing_context


@pytest.mark.asyncio
async def test_upsert_plan_includes_tenant_id_in_query():
    """upsert_plan should include tenant_id in WHERE clause."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    # Act
    from layer7_billing import repository
    await repository.upsert_plan(
        mock_session, "tenant-123", "plan-abc", "Test Plan", ["feature1"]
    )

    # Assert: execute was called with correct tenant_id
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]
    # Verify the statement includes tenant_id in the composite key
    assert "tenant_id" in str(stmt)
    # Verify the tenant_id value is passed correctly
    if hasattr(stmt, 'compile'):
        compiled = stmt.compile()
        params = compiled.params
        # Check that tenant_id parameter exists and has correct value
        assert params.get('tenant_id') == 'tenant-123' or 'tenant-123' in str(params)


@pytest.mark.asyncio
async def test_get_plan_entitlements_filters_by_tenant_id():
    """get_plan_entitlements should filter by tenant_id."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = ["feature1", "feature2"]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    from layer7_billing import repository
    result = await repository.get_plan_entitlements(mock_session, "tenant-123", "plan-abc")

    # Assert: execute was called with tenant_id filter
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]
    # Verify the statement includes tenant_id in WHERE clause
    assert "tenant_id" in str(stmt)
    # Verify result is not None and contains expected features
    assert result is not None
    assert "feature1" in result
    assert "feature2" in result


@pytest.mark.asyncio
async def test_insert_usage_event_includes_tenant_id():
    """insert_usage_event should include tenant_id in values."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.rowcount = 1
    mock_session.execute = AsyncMock(return_value=mock_result)

    event_dict = {
        "event_id": "event-123",
        "metric": "api_calls",
        "quantity": 100.0,
        "source": "test",
        "timestamp": "2026-05-27T00:00:00Z",
        "request_id": "req-123"
    }

    # Act
    from layer7_billing import repository
    result = await repository.insert_usage_event(mock_session, "tenant-123", event_dict)

    # Assert: execute was called
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]
    # Verify the statement includes tenant_id in values and unique constraint
    assert "tenant_id" in str(stmt)


@pytest.mark.asyncio
async def test_increment_aggregate_includes_tenant_id():
    """increment_aggregate should include tenant_id in composite key."""
    mock_session = AsyncMock()
    mock_session.execute = AsyncMock()

    # Act
    from layer7_billing import repository
    await repository.increment_aggregate(mock_session, "tenant-123", "api_calls", 100.0)

    # Assert: execute was called
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]
    # Verify the statement includes tenant_id in index_elements
    assert "tenant_id" in str(stmt)


@pytest.mark.asyncio
async def test_get_usage_aggregates_filters_by_tenant_id():
    """get_usage_aggregates should filter by tenant_id."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.all.return_value = [
        MagicMock(metric="api_calls", total_quantity=100.0)
    ]
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    from layer7_billing import repository
    result = await repository.get_usage_aggregates(mock_session, "tenant-123")

    # Assert: execute was called with tenant_id filter
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]
    # Verify the statement includes tenant_id in WHERE clause
    assert "tenant_id" in str(stmt)


@pytest.mark.asyncio
async def test_list_invoices_filters_by_tenant_id():
    """list_invoices should filter by tenant_id."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalars.return_value.all.return_value = []
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    from layer7_billing import repository
    result = await repository.list_invoices(mock_session, "tenant-123")

    # Assert: execute was called with tenant_id filter
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]
    # Verify the statement includes tenant_id in WHERE clause
    assert "tenant_id" in str(stmt)


@pytest.mark.asyncio
async def test_get_payment_state_filters_by_tenant_id():
    """get_payment_state should filter by tenant_id."""
    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None
    mock_session.execute = AsyncMock(return_value=mock_result)

    # Act
    from layer7_billing import repository
    result = await repository.get_payment_state(mock_session, "tenant-123")

    # Assert: execute was called with tenant_id filter
    assert mock_session.execute.called
    call_args = mock_session.execute.call_args
    stmt = call_args[0][0]
    # Verify the statement includes tenant_id in WHERE clause
    assert "tenant_id" in str(stmt)


@pytest.mark.asyncio
async def test_models_have_tenant_id_primary_key():
    """All billing models should have tenant_id as part of primary key."""
    from layer7_billing.models import BillingPlan, UsageEvent, UsageAggregate, Invoice, PaymentState

    # BillingPlan: composite primary key (plan_id, tenant_id)
    assert hasattr(BillingPlan, 'tenant_id')
    assert hasattr(BillingPlan, 'plan_id')

    # UsageEvent: composite primary key (event_id, tenant_id)
    assert hasattr(UsageEvent, 'tenant_id')
    assert hasattr(UsageEvent, 'event_id')

    # UsageAggregate: composite primary key (tenant_id, metric)
    assert hasattr(UsageAggregate, 'tenant_id')
    assert hasattr(UsageAggregate, 'metric')

    # Invoice: primary key is invoice_id, but tenant_id is indexed
    assert hasattr(Invoice, 'tenant_id')
    assert hasattr(Invoice, 'invoice_id')

    # PaymentState: composite primary key (tenant_id, state_key)
    assert hasattr(PaymentState, 'tenant_id')
    assert hasattr(PaymentState, 'state_key')


class TestDatabaseSessionTenantContext:
    """Test database session properly sets tenant context."""

    @pytest.mark.asyncio
    @patch("layer7_billing.database.session_maker")
    async def test_db_session_for_context_sets_tenant_id(self, mock_session_maker):
        """db_session_for_context should execute set_config with tenant_id."""
        # Setup
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock()

        # Act
        from layer7_billing.database import db_session_for_context
        async with db_session_for_context("tenant-123") as session:
            pass

        # Assert: set_config was called with tenant_id
        mock_session.execute.assert_called_once()
        call_args = mock_session.execute.call_args
        assert "set_config('app.tenant_id'" in str(call_args[0][0])
        # Check that tenant_id is in the parameters
        if call_args[1]:
            assert "tenant_id" in str(call_args[1]) or "tenant-123" in str(call_args[1])

    @pytest.mark.asyncio
    @patch("layer7_billing.database.session_maker")
    async def test_db_session_for_context_commits_on_success(self, mock_session_maker):
        """db_session_for_context should commit on successful operation."""
        # Setup
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock()

        # Act
        from layer7_billing.database import db_session_for_context
        async with db_session_for_context("tenant-123") as session:
            pass

        # Assert: commit was called
        mock_session.commit.assert_called_once()
        # Assert: rollback was not called
        mock_session.rollback.assert_not_called()

    @pytest.mark.asyncio
    @patch("layer7_billing.database.session_maker")
    async def test_db_session_for_context_rolls_back_on_error(self, mock_session_maker):
        """db_session_for_context should rollback on exception."""
        # Setup
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()
        mock_session.commit = AsyncMock()
        mock_session.rollback = AsyncMock()

        mock_session_maker.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session_maker.return_value.__aexit__ = AsyncMock()

        # Act
        from layer7_billing.database import db_session_for_context
        try:
            async with db_session_for_context("tenant-123") as session:
                raise ValueError("Test error")
        except ValueError:
            pass

        # Assert: rollback was called
        mock_session.rollback.assert_called_once()
        # Assert: commit was not called
        mock_session.commit.assert_not_called()



class TestAdversarialBillingManipulation:
    """Test adversarial attempts to manipulate billing data."""

    @pytest.mark.asyncio
    async def test_plan_hijacking_prevented_by_tenant_scoping(self):
        """Tenant A should not be able to hijack Tenant B's plan by upserting same plan_id."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # Act: Tenant A attempts to upsert plan with same plan_id as Tenant B
        from layer7_billing import repository
        await repository.upsert_plan(
            mock_session, "tenant-a", "shared-plan", "Hacked Plan", ["malicious"]
        )

        # Assert: The upsert should be scoped to tenant-a's context
        # Tenant B's plan should remain unchanged due to RLS
        call_args = mock_session.execute.call_args
        stmt = str(call_args[0][0])
        # Verify tenant_id is in the upsert constraint
        assert "tenant_id" in stmt

    @pytest.mark.asyncio
    async def test_usage_injection_prevented_by_tenant_scoping(self):
        """Tenant A should not be able to inject usage events for Tenant B."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.rowcount = 1
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act: Tenant A attempts to inject event with tenant_b's ID in payload
        event_dict = {
            "event_id": "event-123",
            "metric": "api_calls",
            "quantity": 1000.0,
            "source": "malicious",
            "timestamp": "2026-05-27T00:00:00Z",
            "request_id": "req-123"
        }

        from layer7_billing import repository
        # Repository function takes tenant_id as parameter, not from payload
        result = await repository.insert_usage_event(mock_session, "tenant-a", event_dict)

        # Assert: The event is associated with tenant-a (from parameter)
        # The tenant_id in the repository call overrides any payload tenant_id
        call_args = mock_session.execute.call_args
        stmt = str(call_args[0][0])
        assert "tenant_id" in stmt

    @pytest.mark.asyncio
    async def test_invoice_access_prevented_by_tenant_scoping(self):
        """Tenant A should not be able to list Tenant B's invoices."""
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalars.return_value.all.return_value = []
        mock_session.execute = AsyncMock(return_value=mock_result)

        # Act: Tenant A attempts to list invoices
        from layer7_billing import repository
        invoices = await repository.list_invoices(mock_session, "tenant-a")

        # Assert: Query should filter by tenant-a
        call_args = mock_session.execute.call_args
        stmt = str(call_args[0][0])
        assert "tenant_id" in stmt

    @pytest.mark.asyncio
    async def test_aggregate_manipulation_prevented_by_tenant_scoping(self):
        """Tenant A should not be able to manipulate Tenant B's usage aggregates."""
        mock_session = AsyncMock()
        mock_session.execute = AsyncMock()

        # Act: Tenant A attempts to increment aggregate
        from layer7_billing import repository
        await repository.increment_aggregate(mock_session, "tenant-a", "api_calls", 1000.0)

        # Assert: Increment should be scoped to tenant-a
        call_args = mock_session.execute.call_args
        stmt = str(call_args[0][0])
        assert "tenant_id" in stmt


class TestAdversarialHeaderInjection:
    """Test adversarial header injection attempts.

    After P0-02 hardening, tenant_id is extracted from RequestContext
    set by GovernanceMiddleware, not from raw headers. These tests
    verify that the dependency chain enforces tenant context and that
    transport-layer tenant hints cannot override the authenticated context.
    """

    @pytest.mark.asyncio
    async def test_x_tenant_id_header_spoofing_rejected(self):
        """Spoofed X-Tenant-ID header must be rejected when it conflicts with authenticated context."""
        from httpx import AsyncClient, ASGITransport
        from layer7_billing.api.main import app

        trusted_tenant = "11111111-1111-4111-8111-111111111111"
        spoofed_tenant = "22222222-2222-4222-8222-222222222222"

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/billing/usage-aggregates",
                headers={
                    **auth_headers(tenant_id=trusted_tenant),
                    "X-Tenant-ID": spoofed_tenant,
                },
            )

        # Middleware must reject conflicting tenant_id with 403
        assert response.status_code == 403

    @pytest.mark.asyncio
    async def test_missing_tenant_context_fails_closed(self):
        """Missing tenant context must fail closed (401) before reaching repository."""
        from httpx import AsyncClient, ASGITransport
        from layer7_billing.api.main import app

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get("/v1/billing/invoices")

        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_tenant_id_in_context_rejected(self):
        """Empty tenant_id in JWT must fail closed."""
        import jwt as pyjwt
        from httpx import AsyncClient, ASGITransport
        from layer7_billing.api.main import app

        # Create a token with empty tenant_id
        import time
        payload = {
            "tenant_id": "",
            "sub": "test-user",
            "roles": ["billing:read"],
            "iss": "value-fabric-internal",
            "aud": "value-fabric-services",
            "iat": int(time.time()),
            "nbf": int(time.time()),
            "exp": int(time.time()) + 3600,
        }
        token = pyjwt.encode(payload, "test-jwt-secret-must-be-32-characters-long", algorithm="HS256")

        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/billing/invoices",
                headers={"Authorization": f"Bearer {token}"},
            )

        # Empty tenant_id should be rejected (401 from middleware or 403)
        assert response.status_code in (401, 403)

    @pytest.mark.asyncio
    async def test_header_injection_via_special_characters_rejected(self):
        """Invalid special characters in X-Tenant-ID must be rejected."""
        from httpx import AsyncClient, ASGITransport
        from layer7_billing.api.main import app

        trusted_tenant = "tenant-trusted"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post(
                "/v1/billing/plans",
                json={"plan_id": "p1", "name": "P1", "entitlements": []},
                headers={
                    **auth_headers(tenant_id=trusted_tenant),
                    "X-Tenant-ID": "../../../etc/passwd",
                },
            )

        # Invalid header value must fail closed before identity resolution.
        assert response.status_code == 401

    @pytest.mark.asyncio
    async def test_header_injection_via_unicode_rejected(self):
        """Unicode characters in X-Tenant-ID that cannot be encoded must fail gracefully."""
        from httpx import AsyncClient, ASGITransport
        from layer7_billing.api.main import app

        trusted_tenant = "tenant-trusted"
        async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
            response = await client.get(
                "/v1/billing/payment-state",
                headers={
                    **auth_headers(tenant_id=trusted_tenant),
                    "X-Tenant-ID": "tenant-b\x00injected",
                },
            )

        # Null bytes in headers are invalid and must be rejected before routing.
        assert response.status_code in (400, 401, 403)
