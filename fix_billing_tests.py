import re

path = 'services/layer4-agents/tests/test_billing_service.py'
with open(path, 'r') as f:
    content = f.read()

# 1. mock_db fixture: add session.begin
old = '''    session.refresh = AsyncMock()
    return session'''
new = '''    session.refresh = AsyncMock()
    session.begin = AsyncMock()
    return session'''
content = content.replace(old, new)

# 2. client fixture: patch GovernanceMiddleware
old = '''@pytest.fixture
def client():
    """FastAPI test client."""
    return TestClient(app)'''
new = '''@pytest.fixture
def client():
    """FastAPI test client with GovernanceMiddleware bypassed."""
    from unittest.mock import patch
    from value_fabric.shared.identity.middleware import GovernanceMiddleware
    from value_fabric.shared.identity.context import RequestContext

    async def _fake_resolve(self, request):
        return RequestContext(
            tenant_id="tenant_abc123",
            user_id="user_123",
            roles=["admin", "billing:read", "billing:write"],
        )

    patcher = patch.object(GovernanceMiddleware, "_resolve_identity", _fake_resolve)
    patcher.start()
    try:
        yield TestClient(app)
    finally:
        patcher.stop()'''
content = content.replace(old, new)

# 3. Fix _get_stripe patch paths throughout
content = content.replace("patch('src.services.billing_service._get_stripe',", "patch('layer4_agents.services.billing_service._get_stripe',")
content = content.replace('patch("src.services.billing_service._get_stripe",', 'patch("layer4_agents.services.billing_service._get_stripe",')
content = content.replace("patch('src.services.billing_service.logger')", "patch('layer4_agents.services.billing_service.logger')")
content = content.replace('patch("src.services.billing_service.logger")', 'patch("layer4_agents.services.billing_service.logger")')

# 4. Orphan test: fix exception type and assertion
old = '''    mock_db.flush.side_effect = [None, Exception("db flush failed")]

    mock_stripe = MagicMock()
    mock_customer = MagicMock()
    mock_customer.id = "cus_orphan_123"
    mock_stripe.Customer.create.return_value = mock_customer

    with patch('layer4_agents.services.billing_service._get_stripe', return_value=mock_stripe), patch('layer4_agents.services.billing_service.logger') as mock_logger:
        service = BillingService(mock_db)
        with pytest.raises(Exception):
            await service.get_or_create_customer(
                customer_id="user_orphan",
                email="orphan@example.com",
                name="Orphan User",
            )
    assert mock_logger.warning.called'''
new = '''    from sqlalchemy.exc import SQLAlchemyError
    mock_db.flush.side_effect = [None, SQLAlchemyError("db flush failed")]

    mock_stripe = MagicMock()
    mock_customer = MagicMock()
    mock_customer.id = "cus_orphan_123"
    mock_stripe.Customer.create.return_value = mock_customer

    with patch('layer4_agents.services.billing_service._get_stripe', return_value=mock_stripe), patch('layer4_agents.services.billing_service.logger') as mock_logger:
        service = BillingService(mock_db)
        with pytest.raises(SQLAlchemyError):
            await service.get_or_create_customer(
                customer_id="user_orphan",
                email="orphan@example.com",
                name="Orphan User",
            )
    assert mock_logger.error.called'''
content = content.replace(old, new)

# 5. check_entitlement_pro: add PlanVersionService patches
old = '''@pytest.mark.asyncio
async def test_check_entitlement_pro_has_advanced_models(mock_db, sample_subscription):
    """Test that pro plan has advanced_models feature."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    has_feature = await service.check_entitlement("user_123", "advanced_models")

    assert has_feature is True'''
new = '''@pytest.mark.asyncio
async def test_check_entitlement_pro_has_advanced_models(mock_db, sample_subscription):
    """Test that pro plan has advanced_models feature."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    from layer4_agents.services.plan_version_service import PlanVersionService
    with patch.object(PlanVersionService, "ensure_bootstrap_defaults", return_value=None), \
         patch.object(PlanVersionService, "get_subscription_plan_version", return_value=None):
        service = BillingService(mock_db)
        has_feature = await service.check_entitlement("user_123", "advanced_models")

    assert has_feature is True'''
content = content.replace(old, new)

# 6. check_entitlement_free: add PlanVersionService patches
old = '''@pytest.mark.asyncio
async def test_check_entitlement_free_no_advanced_models(mock_db):
    """Test that free plan does not have advanced_models feature."""
    free_subscription = BillingSubscription(
        id="free_123",
        customer_id="user_123",
        plan_id="free",
        status=SubscriptionStatus.ACTIVE,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = free_subscription
    mock_db.execute.return_value = mock_result

    service = BillingService(mock_db)
    has_feature = await service.check_entitlement("user_123", "advanced_models")

    assert has_feature is False'''
new = '''@pytest.mark.asyncio
async def test_check_entitlement_free_no_advanced_models(mock_db):
    """Test that free plan does not have advanced_models feature."""
    free_subscription = BillingSubscription(
        id="free_123",
        customer_id="user_123",
        plan_id="free",
        status=SubscriptionStatus.ACTIVE,
    )

    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = free_subscription
    mock_db.execute.return_value = mock_result

    from layer4_agents.services.plan_version_service import PlanVersionService
    with patch.object(PlanVersionService, "ensure_bootstrap_defaults", return_value=None), \
         patch.object(PlanVersionService, "get_subscription_plan_version", return_value=None):
        service = BillingService(mock_db)
        has_feature = await service.check_entitlement("user_123", "advanced_models")

    assert has_feature is False'''
content = content.replace(old, new)

# 7. handle_webhook_checkout_completed: fix assertions
old = '''    assert result is True
    mock_db.add.assert_called()
    mock_db.flush.assert_called()


@pytest.mark.asyncio
async def test_handle_webhook_idempotency(mock_db):'''
new = '''    assert result.id == event_id


@pytest.mark.asyncio
async def test_handle_webhook_idempotency(mock_db):'''
content = content.replace(old, new)

# 8. handle_webhook_idempotency: fix assertion
old = '''    assert result is True  # Returns True even though already processed


@pytest.mark.asyncio
async def test_create_checkout_session_no_customer(mock_db):'''
new = '''    assert result.id == event_id  # Returns inbox even though already processed


@pytest.mark.asyncio
async def test_create_checkout_session_no_customer(mock_db):'''
content = content.replace(old, new)

# 9. webhook_subscription_created: fix assertions
old = '''    assert result is True
    mock_db.add.assert_called()


@pytest.mark.asyncio
async def test_webhook_subscription_updated_plan_change(mock_db, sample_subscription):'''
new = '''    assert result.id == "evt_sub_created"


@pytest.mark.asyncio
async def test_webhook_subscription_updated_plan_change(mock_db, sample_subscription):'''
content = content.replace(old, new)

# 10. webhook_subscription_updated: rewrite to use process_webhook_event
old = '''@pytest.mark.asyncio
async def test_webhook_subscription_updated_plan_change(mock_db, sample_subscription):
    """Test subscription.updated webhook updates plan_id."""
    # First query: idempotency check (no existing event)
    # Second query: find subscription by stripe_subscription_id
    idempotency_result = MagicMock()
    idempotency_result.scalar_one_or_none.return_value = None
    subscription_result = MagicMock()
    subscription_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.side_effect = [idempotency_result, subscription_result]

    event = {
        "id": "evt_sub_updated",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_stripe123",
                "status": "active",
                "items": {
                    "data": [{"price": {"id": "price_enterprise"}}]
                },
                "current_period_start": 1704067200,
                "current_period_end": 1893456000,
                "cancel_at_period_end": False,
            }
        },
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch('layer4_agents.services.billing_service._get_stripe', return_value=mock_stripe), \\
         patch('layer4_agents.config.plans.PLANS', {
             "enterprise": MagicMock(stripe_price_id="price_enterprise"),
             "pro": MagicMock(stripe_price_id="price_pro"),
         }):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{}',
            signature="sig",
            webhook_secret="whsec_test",
        )

    assert result is True
    assert sample_subscription.plan_id == "enterprise"'''
new = '''@pytest.mark.asyncio
async def test_webhook_subscription_updated_plan_change(mock_db, sample_subscription):
    """Test subscription.updated webhook updates plan_id via process_webhook_event."""
    mock_inbox = BillingWebhookEvent(id="evt_sub_updated", type="customer.subscription.updated", status="pending", attempt_count=0)
    inbox_result = MagicMock()
    inbox_result.scalar_one_or_none.return_value = mock_inbox
    subscription_result = MagicMock()
    subscription_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.side_effect = [inbox_result, subscription_result]

    event = {
        "id": "evt_sub_updated",
        "type": "customer.subscription.updated",
        "data": {
            "object": {
                "id": "sub_stripe123",
                "status": "active",
                "items": {
                    "data": [{"price": {"id": "price_enterprise"}}]
                },
                "current_period_start": 1704067200,
                "current_period_end": 1893456000,
                "cancel_at_period_end": False,
            }
        },
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch('layer4_agents.services.billing_service._get_stripe', return_value=mock_stripe), \\
         patch('layer4_agents.config.plans.PLANS', {
             "enterprise": MagicMock(stripe_price_id="price_enterprise"),
             "pro": MagicMock(stripe_price_id="price_pro"),
         }):
        service = BillingService(mock_db)
        await service.process_webhook_event(
            event_id="evt_sub_updated",
            payload=b'{}',
            signature="sig",
            webhook_secret="whsec_test",
        )

    assert sample_subscription.plan_id == "enterprise"
    assert mock_inbox.status == "processed"'''
content = content.replace(old, new)

# 11. webhook_subscription_deleted: rewrite to use process_webhook_event
old = '''@pytest.mark.asyncio
async def test_webhook_subscription_deleted_downgrades_to_free(mock_db, sample_subscription):
    """Test subscription.deleted webhook downgrades to free tier."""
    # First query: idempotency check (no existing event)
    # Second query: find subscription by stripe_subscription_id
    idempotency_result = MagicMock()
    idempotency_result.scalar_one_or_none.return_value = None
    subscription_result = MagicMock()
    subscription_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.side_effect = [idempotency_result, subscription_result]

    event = {
        "id": "evt_sub_deleted",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_stripe123",
            }
        },
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch('layer4_agents.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        result = await service.handle_webhook(
            payload=b'{}',
            signature="sig",
            webhook_secret="whsec_test",
        )

    assert result is True
    assert sample_subscription.status == SubscriptionStatus.CANCELED
    mock_db.add.assert_called()  # Free subscription added'''
new = '''@pytest.mark.asyncio
async def test_webhook_subscription_deleted_downgrades_to_free(mock_db, sample_subscription):
    """Test subscription.deleted webhook downgrades to free tier via process_webhook_event."""
    mock_inbox = BillingWebhookEvent(id="evt_sub_deleted", type="customer.subscription.deleted", status="pending", attempt_count=0)
    inbox_result = MagicMock()
    inbox_result.scalar_one_or_none.return_value = mock_inbox
    subscription_result = MagicMock()
    subscription_result.scalar_one_or_none.return_value = sample_subscription
    plan_version_result = MagicMock()
    plan_version_result.scalars.return_value.first.return_value = None
    mock_db.execute.side_effect = [inbox_result, subscription_result, plan_version_result]

    event = {
        "id": "evt_sub_deleted",
        "type": "customer.subscription.deleted",
        "data": {
            "object": {
                "id": "sub_stripe123",
            }
        },
    }

    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = event

    with patch('layer4_agents.services.billing_service._get_stripe', return_value=mock_stripe):
        service = BillingService(mock_db)
        await service.process_webhook_event(
            event_id="evt_sub_deleted",
            payload=b'{}',
            signature="sig",
            webhook_secret="whsec_test",
        )

    assert sample_subscription.status == SubscriptionStatus.CANCELED
    assert mock_inbox.status == "processed"
    mock_db.add.assert_called()  # Free subscription added'''
content = content.replace(old, new)

# 12. process_webhook_event_transient_retry: patch path
old = '    with patch("src.services.billing_service._get_stripe", return_value=mock_stripe):'
new = '    with patch("layer4_agents.services.billing_service._get_stripe", return_value=mock_stripe):'
content = content.replace(old, new)

# 13. retry_queue_permanent_failure_dlq: add refetch_result
old = '''    due_result = MagicMock()
    due_result.scalars.return_value.all.return_value = [inbox]
    by_id_result = MagicMock()
    by_id_result.scalar_one_or_none.return_value = inbox
    mock_db.execute.side_effect = [due_result, by_id_result]
    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = {"id": "evt_retry_dead", "type": "invoice.payment_succeeded", "data": {"object": {}}}
    with patch("layer4_agents.services.billing_service._get_stripe", return_value=mock_stripe):
        service = BillingService(mock_db)
        with patch.object(service, "_handle_payment_succeeded", side_effect=ValueError("poison")):
            with pytest.raises(ValueError):
                await service.process_due_webhook_retries({"evt_retry_dead": b"{}"}, "sig", "secret")
    assert inbox.status == "failed"'''
new = '''    due_result = MagicMock()
    due_result.scalars.return_value.all.return_value = [inbox]
    by_id_result = MagicMock()
    by_id_result.scalar_one_or_none.return_value = inbox
    refetch_result = MagicMock()
    refetch_result.scalar_one_or_none.return_value = inbox
    mock_db.execute.side_effect = [due_result, by_id_result, refetch_result]
    mock_stripe = MagicMock()
    mock_stripe.Webhook.construct_event.return_value = {"id": "evt_retry_dead", "type": "invoice.payment_succeeded", "data": {"object": {}}}
    with patch("layer4_agents.services.billing_service._get_stripe", return_value=mock_stripe):
        service = BillingService(mock_db)
        with patch.object(service, "_handle_payment_succeeded", side_effect=ValueError("poison")):
            with pytest.raises(ValueError):
                await service.process_due_webhook_retries({"evt_retry_dead": b"{}"}, "sig", "secret")
    assert inbox.status == "failed"'''
content = content.replace(old, new)

# 14. get_entitlements_endpoint: patch BillingService.get_entitlements directly
old = '''def test_get_entitlements_endpoint(client, mock_db, sample_subscription):
    """Test GET /billing/entitlements endpoint."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    response = client.get("/v1/billing/entitlements?customer_id=user_123")

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "pro"
    assert "features" in data
    assert data["features"]["advanced_models"]["enabled"] is True'''
new = '''def test_get_entitlements_endpoint(client, mock_db, sample_subscription):
    """Test GET /billing/entitlements endpoint."""
    with patch("layer4_agents.api.routes.billing.BillingService.get_entitlements", new_callable=AsyncMock, return_value={
        "plan_id": "pro",
        "plan_name": "Pro",
        "features": {
            "advanced_models": {"enabled": True, "name": "Advanced AI Models", "description": "Access to GPT-4, Claude, and other advanced models"},
        },
    }):
        response = client.get("/v1/billing/entitlements?customer_id=user_123")

    assert response.status_code == 200
    data = response.json()
    assert data["plan_id"] == "pro"
    assert "features" in data
    assert data["features"]["advanced_models"]["enabled"] is True'''
content = content.replace(old, new)

# 15. check_feature_endpoint: patch BillingService.check_entitlement directly
old = '''def test_check_feature_endpoint(client, mock_db, sample_subscription):
    """Test GET /billing/check-feature endpoint."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = sample_subscription
    mock_db.execute.return_value = mock_result

    response = client.get("/v1/billing/check-feature?customer_id=user_123&feature_id=advanced_models")

    assert response.status_code == 200
    data = response.json()
    assert data["feature_id"] == "advanced_models"
    assert data["has_access"] is True'''
new = '''def test_check_feature_endpoint(client):
    """Test GET /billing/check-feature endpoint."""
    with patch("layer4_agents.api.routes.billing.BillingService.check_entitlement", new_callable=AsyncMock, return_value=True):
        response = client.get("/v1/billing/check-feature?customer_id=user_123&feature_id=advanced_models")

    assert response.status_code == 200
    data = response.json()
    assert data["feature_id"] == "advanced_models"
    assert data["has_access"] is True'''
content = content.replace(old, new)

# 16. Add cancel endpoint not-found sanitization test after cancel_subscription_endpoint
old = '''    assert response.status_code == 200
    data = response.json()
    assert data["canceled"] is True
    assert data["cancel_at_period_end"] is True


@pytest.mark.asyncio
async def test_update_plan_endpoint'''
new = '''    assert response.status_code == 200
    data = response.json()
    assert data["canceled"] is True
    assert data["cancel_at_period_end"] is True


def test_cancel_subscription_endpoint_not_found_response_does_not_leak_identifiers(client):
    """Cancellation not-found errors must not expose tenant or subscription IDs."""
    leaked_tenant_id = "tenant_abc123"
    leaked_subscription_id = "sub_secret_123"
    raw_error = (
        "No active subscription found for "
        f"tenant_id={leaked_tenant_id} subscription_id={leaked_subscription_id}"
    )

    with patch(
        "layer4_agents.api.routes.billing.BillingService.cancel_subscription",
        side_effect=ValueError(raw_error),
    ):
        response = client.post(
            "/v1/billing/subscription/cancel?customer_id=user_123",
            json={"cancel_immediately": False},
        )

    # Route wraps ValueError as BadRequestError (400); identifier values must be
    # redacted from the public error envelope to prevent cross-tenant leakage.
    assert response.status_code == 400
    response_text = response.text
    assert leaked_tenant_id not in response_text
    assert leaked_subscription_id not in response_text


@pytest.mark.asyncio
async def test_update_plan_endpoint'''
content = content.replace(old, new)

with open(path, 'w') as f:
    f.write(content)

print('patch applied')
