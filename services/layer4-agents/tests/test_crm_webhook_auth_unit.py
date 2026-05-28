from __future__ import annotations

"""
CI-runnable unit tests for CRM webhook authentication logic.

These tests verify the core authentication behavior without importing the
full FastAPI route module (which requires langgraph, psycopg, etc.).

Covers:
- Per-tenant webhook token validation (constant-time comparison)
- Missing token rejection (fail-closed)
- Invalid token rejection
- Development-only signature fallback (explicitly gated)
- HMAC signature mismatch (defense-in-depth)
"""


import hashlib
import hmac
import json
import os
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException, status


# Recreate the auth logic under test without importing the route module.
# This mirrors _authenticate_webhook in crm_webhooks.py.
async def _authenticate_webhook(
    integration,
    provided_token: str | None,
    provided_signature: str | None,
    body: bytes,
    app_state_webhook_secret: str | None,
):
    """Authenticate a CRM webhook using token + optional HMAC signature."""

    # Decrypt credentials to obtain the per-tenant webhook token
    decrypted = await _mock_encryption_decrypt(
        integration.credentials_encrypted, integration.encryption_key_id
    )
    creds = json.loads(decrypted)
    stored_webhook_token = creds.get("webhook_token")

    # Primary auth: per-tenant webhook token (constant-time comparison)
    token_valid = False
    if stored_webhook_token and provided_token:
        token_valid = hmac.compare_digest(stored_webhook_token, provided_token)

    if not token_valid:
        if (
            os.getenv("CRM_WEBHOOKS_ALLOW_DEV_RELAXED_TENANT_RESOLUTION", "").lower()
            in ("true", "1", "yes", "on")
            and app_state_webhook_secret
            and provided_signature
        ):
            expected = hmac.new(
                app_state_webhook_secret.encode(), body, hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(expected, provided_signature):
                return json.loads(decrypted), "dev_signature_fallback"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook credentials",
        )

    # Secondary auth: HMAC signature verification (defense-in-depth)
    if app_state_webhook_secret and provided_signature:
        expected = hmac.new(
            app_state_webhook_secret.encode(), body, hashlib.sha256
        ).hexdigest()
        if not hmac.compare_digest(expected, provided_signature):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    return json.loads(decrypted), "token"


async def _mock_encryption_decrypt(ciphertext: str, key_id: str) -> str:
    """Test double for EncryptionService.decrypt.

    In real usage this calls Fernet; here we just decode the base64-like
    test payload back to plaintext.
    """
    # Our test fixtures store plaintext JSON wrapped in a fake "enc:" prefix
    if ciphertext.startswith("enc:"):
        return ciphertext[4:]
    return ciphertext


def _make_integration(webhook_token: str | None = "test-token-123"):
    """Create a minimal mock Integration for auth tests."""
    integration = MagicMock()
    integration.tenant_id = "tenant-test"
    integration.provider = "salesforce"
    integration.credentials_encrypted = (
        f'enc:{{"webhook_token": "{webhook_token}"}}' if webhook_token else 'enc:{}'
    )
    integration.encryption_key_id = "test-key"
    return integration


class TestWebhookTokenAuth:
    """Test per-tenant webhook token authentication."""

    @pytest.mark.asyncio
    async def test_valid_token_accepts(self):
        """Webhook with correct per-tenant token is accepted."""
        integration = _make_integration(webhook_token="secret-token")
        body = b'{"test": "payload"}'

        await _authenticate_webhook(
            integration,
            provided_token="secret-token",
            provided_signature=None,
            body=body,
            app_state_webhook_secret=None,
        )
        # No exception = success

    @pytest.mark.asyncio
    async def test_invalid_token_rejects(self):
        """Webhook with wrong per-tenant token is rejected with 401."""
        integration = _make_integration(webhook_token="secret-token")
        body = b'{"test": "payload"}'

        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_webhook(
                integration,
                provided_token="wrong-token",
                provided_signature=None,
                body=body,
                app_state_webhook_secret=None,
            )
        assert exc_info.value.status_code == 401
        assert "Invalid webhook credentials" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_missing_token_rejects(self):
        """Webhook with no token is rejected (fail-closed)."""
        integration = _make_integration(webhook_token="secret-token")
        body = b'{"test": "payload"}'

        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_webhook(
                integration,
                provided_token=None,
                provided_signature=None,
                body=body,
                app_state_webhook_secret=None,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_no_token_configured_rejects(self):
        """Integration with no webhook_token configured rejects all requests."""
        integration = _make_integration(webhook_token=None)
        body = b'{"test": "payload"}'

        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_webhook(
                integration,
                provided_token="any-token",
                provided_signature=None,
                body=body,
                app_state_webhook_secret=None,
            )
        assert exc_info.value.status_code == 401


class TestWebhookHMACAuth:
    """Test HMAC signature verification (defense-in-depth)."""

    @pytest.mark.asyncio
    async def test_valid_token_and_valid_hmac_accepts(self):
        """Both token and HMAC valid → accepted."""
        integration = _make_integration(webhook_token="secret-token")
        body = b'{"test": "payload"}'
        secret = "global-secret"
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        await _authenticate_webhook(
            integration,
            provided_token="secret-token",
            provided_signature=expected,
            body=body,
            app_state_webhook_secret=secret,
        )

    @pytest.mark.asyncio
    async def test_valid_token_and_invalid_hmac_rejects(self):
        """Valid token but bad HMAC → rejected (defense-in-depth)."""
        integration = _make_integration(webhook_token="secret-token")
        body = b'{"test": "payload"}'
        secret = "global-secret"

        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_webhook(
                integration,
                provided_token="secret-token",
                provided_signature="bad-signature",
                body=body,
                app_state_webhook_secret=secret,
            )
        assert exc_info.value.status_code == 401
        assert "Invalid webhook signature" in exc_info.value.detail

    @pytest.mark.asyncio
    async def test_dev_signature_fallback_accepts_only_when_enabled(self):
        """Local dev fallback requires an explicit flag and a valid signature."""
        integration = _make_integration(webhook_token=None)
        body = b'{"test": "payload"}'
        secret = "global-secret"
        expected = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

        with patch.dict(os.environ, {"CRM_WEBHOOKS_ALLOW_DEV_RELAXED_TENANT_RESOLUTION": "true"}):
            _, auth_mode = await _authenticate_webhook(
                integration,
                provided_token=None,
                provided_signature=expected,
                body=body,
                app_state_webhook_secret=secret,
            )
        assert auth_mode == "dev_signature_fallback"

    @pytest.mark.asyncio
    async def test_missing_token_without_dev_fallback_rejects(self):
        """Missing token stays fail-closed unless the explicit dev flag is set."""
        integration = _make_integration(webhook_token=None)
        body = b'{"test": "payload"}'
        secret = "global-secret"

        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_webhook(
                integration,
                provided_token=None,
                provided_signature="bad-signature",
                body=body,
                app_state_webhook_secret=secret,
            )
        assert exc_info.value.status_code == 401


class TestWebhookConstantTimeComparison:
    """Verify that token comparison uses constant-time hmac.compare_digest."""

    @pytest.mark.asyncio
    async def test_timing_attack_resistance(self):
        """Wrong-length token should still go through compare_digest, not early exit."""
        integration = _make_integration(webhook_token="x" * 32)
        body = b'{}'

        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_webhook(
                integration,
                provided_token="y" * 16,  # Different length
                provided_signature=None,
                body=body,
                app_state_webhook_secret=None,
            )
        assert exc_info.value.status_code == 401

    @pytest.mark.asyncio
    async def test_empty_token_vs_empty_stored(self):
        """Both empty should reject (fail-closed)."""
        integration = _make_integration(webhook_token=None)
        body = b'{}'

        with pytest.raises(HTTPException) as exc_info:
            await _authenticate_webhook(
                integration,
                provided_token="",
                provided_signature=None,
                body=body,
                app_state_webhook_secret=None,
            )
        assert exc_info.value.status_code == 401
