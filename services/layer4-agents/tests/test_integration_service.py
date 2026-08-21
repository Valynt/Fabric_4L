from __future__ import annotations

"""
Unit tests for Integration Service refinements.

Tests validation logic, edge cases, and error handling.
"""


import json
from unittest.mock import AsyncMock

import pytest

from layer4_agents.models.account import CRMProvider
from layer4_agents.models.integration import Integration
from layer4_agents.services.encryption_service import DEFAULT_KEY_ID, EncryptionService
from layer4_agents.services.integration_service import (
    IntegrationService,
    IntegrationValidationError,
)


@pytest.fixture(autouse=True)
def clear_encryption_cache(monkeypatch):
    """Clear encryption cache between tests to prevent pollution."""
    from collections import OrderedDict

    # Set a deterministic 32-byte Fernet key (43 chars url-safe base64) and
    # allow ephemeral fallback so the invalid key in pytest.ini is overridden.
    monkeypatch.setenv("CREDENTIALS_MASTER_KEY", "ZHVtbXlfdGVzdF9tYXN0ZXJfa2V5XzMyX2J5dGVzISE=")
    monkeypatch.setenv("ALLOW_EPHEMERAL_ENCRYPTION", "true")
    EncryptionService._MASTER_KEY = None
    EncryptionService._key_cache = OrderedDict()
    EncryptionService._cache_lock = None
    yield


class TestIntegrationValidation:
    """Test suite for integration configuration validation."""

    def test_validate_config_valid(self):
        """Test valid configuration passes validation."""
        service = IntegrationService(None)  # db not needed for validation

        # Should not raise
        service._validate_config(
            enabled=True,
            credentials={"api_key": "valid_key"},
            sync_interval=60,
            batch_size=100,
            instance_url="https://instance.salesforce.com",
        )

    def test_validate_config_missing_api_key_when_enabled(self):
        """Test that enabled=True requires api_key."""
        service = IntegrationService(None)

        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=True,
                credentials={},  # Missing api_key
                sync_interval=60,
                batch_size=100,
            )

        assert "api_key is required" in str(exc.value)

    def test_validate_config_disabled_no_api_key(self):
        """Test that disabled integration doesn't require api_key."""
        service = IntegrationService(None)

        # Should not raise - disabled integrations don't need credentials
        service._validate_config(
            enabled=False,
            credentials={},
            sync_interval=60,
            batch_size=100,
        )

    def test_validate_config_invalid_sync_interval(self):
        """Test sync_interval bounds validation."""
        service = IntegrationService(None)

        # Too low
        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=4,  # Below minimum of 5
                batch_size=100,
            )
        assert "between 5 and 1440" in str(exc.value)

        # Too high
        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=1441,  # Above maximum
                batch_size=100,
            )
        assert "between 5 and 1440" in str(exc.value)

    def test_validate_config_invalid_batch_size(self):
        """Test batch_size bounds validation."""
        service = IntegrationService(None)

        # Too low
        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=60,
                batch_size=9,  # Below minimum of 10
            )
        assert "between 10 and 500" in str(exc.value)

        # Too high
        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=60,
                batch_size=501,  # Above maximum
            )
        assert "between 10 and 500" in str(exc.value)

    def test_validate_config_invalid_instance_url(self):
        """Test instance_url format validation."""
        service = IntegrationService(None)

        # Invalid URL
        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=60,
                batch_size=100,
                instance_url="not-a-valid-url",
            )
        assert "valid HTTP/HTTPS URL" in str(exc.value)

        # FTP is not allowed
        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=60,
                batch_size=100,
                instance_url="ftp://example.com",
            )
        assert "valid HTTP/HTTPS URL" in str(exc.value)

    def test_validate_config_valid_instance_urls(self):
        """Test that valid HTTPS instance URLs pass."""
        service = IntegrationService(None)

        valid_urls = [
            "https://instance.salesforce.com",
            "https://api.hubspot.com",
            "https://my-org.my.salesforce.com",
            "https://10.0.0.1:443",
        ]

        for url in valid_urls:
            # Should not raise
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=60,
                batch_size=100,
                instance_url=url,
            )

    def test_validate_config_http_localhost_allowed(self):
        """Test that HTTP is allowed only for localhost."""
        service = IntegrationService(None)

        # HTTP on localhost should be allowed
        service._validate_config(
            enabled=False,
            credentials={},
            sync_interval=60,
            batch_size=100,
            instance_url="http://localhost:8080",
        )

    def test_validate_config_http_production_rejected(self):
        """Test that HTTP is rejected for production URLs."""
        service = IntegrationService(None)

        # HTTP on production domains should fail
        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=60,
                batch_size=100,
                instance_url="http://instance.salesforce.com",
            )
        assert "HTTPS is required" in str(exc.value)

    def test_validate_config_http_localhost_subdomain_rejected(self):
        """Test that HTTP is rejected for localhost subdomains (not actual localhost)."""
        service = IntegrationService(None)

        # HTTP on localhost.something.com should fail (not real localhost)
        with pytest.raises(IntegrationValidationError) as exc:
            service._validate_config(
                enabled=False,
                credentials={},
                sync_interval=60,
                batch_size=100,
                instance_url="http://localhost.mydomain.com",
            )
        assert "HTTPS is required" in str(exc.value)

    def test_validate_config_none_instance_url(self):
        """Test that None instance_url is allowed."""
        service = IntegrationService(None)

        # Should not raise
        service._validate_config(
            enabled=False,
            credentials={},
            sync_interval=60,
            batch_size=100,
            instance_url=None,
        )


class TestIntegrationConfigUpdates:
    """Regression coverage for integration update drift."""

    @pytest.mark.asyncio
    async def test_salesforce_update_preserves_existing_instance_url_column_when_credentials_omit_it(self):
        """Pre-existing Salesforce rows may keep instance_url outside encrypted credentials."""
        db = AsyncMock()
        service = IntegrationService(db)
        existing = Integration(
            tenant_id="tenant-1",
            provider=CRMProvider.SALESFORCE,
            enabled=True,
            credentials_encrypted=await EncryptionService.encrypt(
                json.dumps({"api_key": "old-token"}), key_id=DEFAULT_KEY_ID
            ),
            encryption_key_id=DEFAULT_KEY_ID,
            instance_url="https://tenant.my.salesforce.com",
            sync_interval_minutes=60,
            sync_batch_size=100,
        )
        service.get_integration = AsyncMock(return_value=existing)

        integration, created = await service.create_or_update_integration(
            tenant_id="tenant-1",
            provider=CRMProvider.SALESFORCE,
            enabled=True,
            credentials={"api_key": "new-token"},
            instance_url=None,
            sync_interval_minutes=60,
            sync_batch_size=100,
            user_id="user-1",
        )

        assert created is False
        assert integration.instance_url == "https://tenant.my.salesforce.com"


class TestEncryptionService:
    """Test suite for encryption service."""

    @pytest.mark.asyncio
    async def test_encryption_roundtrip(self):
        """Test that encrypt/decrypt preserves data."""
        test_data = '{"api_key": "secret123", "api_secret": "supersecret"}'

        encrypted = await EncryptionService.encrypt(test_data, key_id=DEFAULT_KEY_ID)
        assert encrypted != test_data.encode()
        assert isinstance(encrypted, bytes)

        decrypted = await EncryptionService.decrypt(encrypted, key_id=DEFAULT_KEY_ID)
        assert decrypted == test_data

    @pytest.mark.asyncio
    async def test_encryption_empty_data(self):
        """Test that empty data is handled gracefully."""
        # Empty string returns empty bytes
        assert await EncryptionService.encrypt("", key_id=DEFAULT_KEY_ID) == b""
        assert await EncryptionService.decrypt(b"", key_id=DEFAULT_KEY_ID) == ""

    @pytest.mark.asyncio
    async def test_encryption_different_keys(self):
        """Test that different key_ids produce different ciphertexts."""
        test_data = "sensitive data"

        encrypted_v1 = await EncryptionService.encrypt(test_data, key_id=DEFAULT_KEY_ID)
        encrypted_v2 = await EncryptionService.encrypt(test_data, key_id="v2")

        # Same plaintext, different ciphertexts
        assert encrypted_v1 != encrypted_v2

        # But both decrypt correctly with their keys
        assert await EncryptionService.decrypt(encrypted_v1, key_id=DEFAULT_KEY_ID) == test_data
        assert await EncryptionService.decrypt(encrypted_v2, key_id="v2") == test_data

    @pytest.mark.asyncio
    async def test_decryption_wrong_key_fails(self):
        """Test that decrypting with wrong key fails appropriately."""
        test_data = "sensitive data"
        encrypted = await EncryptionService.encrypt(test_data, key_id=DEFAULT_KEY_ID)

        # Decrypting with wrong key should fail
        with pytest.raises(ValueError) as exc:
            await EncryptionService.decrypt(encrypted, key_id="wrong_key")

        assert "Failed to decrypt" in str(exc.value)


def test_connection_result_allows_success_without_error_code() -> None:
    from layer4_agents.services.integration_service import IntegrationService_test_connectionResult

    result = IntegrationService_test_connectionResult.model_validate(
        {
            "success": True,
            "message": "Connected",
            "details": {"organization": "Acme"},
        }
    )

    assert result.success is True
    assert result.message == "Connected"
    assert result.error_code is None
