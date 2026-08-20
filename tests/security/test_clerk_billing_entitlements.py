"""Tests for Clerk Billing webhook integration and Fabric tenant entitlement synchronization."""

import base64
import hashlib
import hmac
import json
import time
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from app.core.auth_directory import AuthDirectory, get_auth_directory
from app.core.billing_entitlements import (
    PLAN_ENTITLEMENT_MAP,
    process_clerk_billing_event,
    resolve_plan_entitlements,
)
from app.main import app


def _compute_svix_signature(secret: str, svix_id: str, svix_ts: str, body: bytes) -> str:
    key = base64.b64decode(secret.replace("whsec_", ""))
    to_sign = f"{svix_id}.{svix_ts}.".encode() + body
    sig = hmac.new(key, to_sign, hashlib.sha256).digest()
    return f"v1,{base64.b64encode(sig).decode()}"


@pytest.fixture
def clean_directory():
    directory = get_auth_directory()
    directory.reset()
    yield directory
    directory.reset()


def test_resolve_plan_entitlements_basic():
    starter = resolve_plan_entitlements("starter")
    assert "tier:starter" in starter
    assert "features:l1_ingestion" in starter

    pro = resolve_plan_entitlements("pro")
    assert "tier:pro" in pro
    assert "features:l3_graph_rag" in pro

    enterprise = resolve_plan_entitlements("enterprise")
    assert "tier:enterprise" in enterprise
    assert "features:l4_autonomous_agents" in enterprise
    assert "features:sso_enforced" in enterprise


def test_resolve_plan_entitlements_with_custom_features_and_addons():
    entitlements = resolve_plan_entitlements(
        "pro",
        features=["custom_crawler", "features:extra_storage"],
        add_ons=["dedicated_support"],
    )
    assert "tier:pro" in entitlements
    assert "features:custom_crawler" in entitlements
    assert "features:extra_storage" in entitlements
    assert "addon:dedicated_support" in entitlements


def test_billing_event_subscription_created_and_downgrade(clean_directory: AuthDirectory):
    tenant = clean_directory.upsert_tenant(
        clerk_org_id="org_billing_test",
        name="Billing Test Corp",
        slug="billing-test",
        status="active",
    )

    # 1. Process subscription.created with Pro plan
    created_data = {
        "organization_id": "org_billing_test",
        "status": "active",
        "plan_slug": "pro",
        "current_period_end": int(time.time()) + 86400 * 30,
    }
    applied = process_clerk_billing_event("subscription.created", created_data, directory=clean_directory)
    assert applied is True

    proj = clean_directory._tenant_entitlements.get(tenant.id)
    assert "tier:pro" in proj
    assert "features:l3_graph_rag" in proj

    # 2. Upgrade to enterprise via subscription.updated
    upgrade_data = {
        "organization_id": "org_billing_test",
        "status": "active",
        "plan_slug": "enterprise",
        "current_period_end": int(time.time()) + 86400 * 365,
    }
    applied = process_clerk_billing_event("subscription.updated", upgrade_data, directory=clean_directory)
    assert applied is True

    proj = clean_directory._tenant_entitlements.get(tenant.id)
    assert "tier:enterprise" in proj
    assert "features:l4_autonomous_agents" in proj
    assert "features:sso_enforced" in proj

    # 3. Cancel / delete subscription -> fallback to starter
    cancel_data = {
        "organization_id": "org_billing_test",
        "status": "canceled",
    }
    applied = process_clerk_billing_event("subscription.canceled", cancel_data, directory=clean_directory)
    assert applied is True

    proj = clean_directory._tenant_entitlements.get(tenant.id)
    assert "tier:starter" in proj
    assert "features:l4_autonomous_agents" not in proj


def test_billing_webhook_e2e_svix_flow(clean_directory: AuthDirectory):
    tenant = clean_directory.upsert_tenant(
        clerk_org_id="org_webhook_billing",
        name="Webhook Billing Co",
        slug="wh-billing",
        status="active",
    )

    client = TestClient(app)
    mock_secret = "whsec_" + base64.b64encode(b"billing_webhook_secret_key_12345").decode()

    with patch("app.routers.clerk_webhooks.get_auth_settings") as mock_settings:
        from app.core.clerk_config import ClerkSettings, FabricAuthSettings

        mock_settings.return_value = FabricAuthSettings(
            clerk=ClerkSettings(
                publishable_key="pk_test_123",
                secret_key="sk_test_123",
                jwks_url="https://api.clerk.com/v1/jwks",
                webhook_secret=mock_secret,
            )
        )

        payload = {
            "type": "subscription.created",
            "data": {
                "organization_id": "org_webhook_billing",
                "status": "active",
                "plan_slug": "enterprise",
                "current_period_end": int(time.time()) + 86400 * 30,
            },
        }
        body = json.dumps(payload).encode("utf-8")
        svix_id = f"msg_billing_{int(time.time())}"
        svix_ts = str(int(time.time()))
        sig = _compute_svix_signature(mock_secret, svix_id, svix_ts, body)

        resp = client.post(
            "/internal/webhooks/clerk",
            content=body,
            headers={
                "svix-id": svix_id,
                "svix-timestamp": svix_ts,
                "svix-signature": sig,
                "content-type": "application/json",
            },
        )
        assert resp.status_code == 204

        proj = clean_directory._tenant_entitlements.get(tenant.id)
        assert "tier:enterprise" in proj
        assert "features:sso_enforced" in proj
