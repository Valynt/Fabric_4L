from __future__ import annotations

"""
Tests for EncryptionService.

Covers:
- Encrypt/decrypt roundtrip
- Empty string handling
- Key rotation
- Non-ASCII key_id rejection
- Production safety guard (ephemeral key blocked without opt-in)
- Master key length validation
- LRU cache eviction (MAX_CACHE_SIZE)
"""


import os
from unittest.mock import patch

import pytest
from cryptography.fernet import Fernet

from layer4_agents.services.encryption_service import (
    DEFAULT_KEY_ID,
    MAX_CACHE_SIZE,
    EncryptionService,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_service():
    """Reset EncryptionService class-level state between tests."""
    EncryptionService._MASTER_KEY = None
    EncryptionService._key_cache.clear()


@pytest.fixture(autouse=True)
def reset_encryption_state():
    """Ensure EncryptionService state is clean for every test."""
    _reset_service()
    yield
    _reset_service()


@pytest.fixture
def valid_fernet_key() -> str:
    """Generate a valid 43-char URL-safe base64 key (32 bytes, no padding).

    The service expects keys without the trailing '=' padding that
    Fernet.generate_key() normally appends.
    """
    return Fernet.generate_key().rstrip(b"=").decode()


# ---------------------------------------------------------------------------
# Encrypt / Decrypt roundtrip
# ---------------------------------------------------------------------------

class TestEncryptDecryptRoundtrip:
    """Basic encrypt/decrypt correctness."""

    @pytest.mark.asyncio
    async def test_roundtrip_default_key(self, valid_fernet_key):
        """Encrypting then decrypting returns original plaintext."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            plaintext = "super-secret-credential"
            ciphertext = await EncryptionService.encrypt(plaintext)
            assert ciphertext != plaintext.encode()
            recovered = await EncryptionService.decrypt(ciphertext)
            assert recovered == plaintext

    @pytest.mark.asyncio
    async def test_roundtrip_custom_key_id(self, valid_fernet_key):
        """Custom key_id still produces a valid roundtrip."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            plaintext = "another-secret"
            ciphertext = await EncryptionService.encrypt(plaintext, key_id="v2")
            recovered = await EncryptionService.decrypt(ciphertext, key_id="v2")
            assert recovered == plaintext

    @pytest.mark.asyncio
    async def test_different_key_ids_produce_different_ciphertexts(self, valid_fernet_key):
        """Same plaintext encrypted with different key_ids yields different ciphertexts."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            ct1 = await EncryptionService.encrypt("data", key_id="v1")
            _reset_service()
            ct2 = await EncryptionService.encrypt("data", key_id="v2")
            assert ct1 != ct2


# ---------------------------------------------------------------------------
# Empty string edge cases
# ---------------------------------------------------------------------------

class TestEmptyStringHandling:
    """Ensure empty strings are handled gracefully without error."""

    @pytest.mark.asyncio
    async def test_encrypt_empty_string_returns_empty_bytes(self, valid_fernet_key):
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            result = await EncryptionService.encrypt("")
            assert result == b""

    @pytest.mark.asyncio
    async def test_decrypt_empty_bytes_returns_empty_string(self, valid_fernet_key):
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            result = await EncryptionService.decrypt(b"")
            assert result == ""


# ---------------------------------------------------------------------------
# Key rotation
# ---------------------------------------------------------------------------

class TestKeyRotation:
    """Key rotation re-encrypts with new key and old key can no longer decrypt."""

    @pytest.mark.asyncio
    async def test_rotate_key_produces_valid_ciphertext(self, valid_fernet_key):
        """rotate_key returns ciphertext decryptable with new key_id."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            plaintext = "rotate-me"
            old_ct = await EncryptionService.encrypt(plaintext, key_id="v1")
            new_ct = await EncryptionService.rotate_key("v1", "v2", old_ct)
            recovered = await EncryptionService.decrypt(new_ct, key_id="v2")
            assert recovered == plaintext

    @pytest.mark.asyncio
    async def test_rotate_key_old_key_cannot_decrypt_new_ciphertext(self, valid_fernet_key):
        """Ciphertext produced by rotate_key cannot be decrypted with old key."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            plaintext = "secret"
            old_ct = await EncryptionService.encrypt(plaintext, key_id="v1")
            new_ct = await EncryptionService.rotate_key("v1", "v2", old_ct)
            with pytest.raises(ValueError):
                await EncryptionService.decrypt(new_ct, key_id="v1")

    @pytest.mark.asyncio
    async def test_rotate_key_raises_on_bad_ciphertext(self, valid_fernet_key):
        """rotate_key raises ValueError for corrupted ciphertext."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            with pytest.raises(ValueError, match="Failed to rotate"):
                await EncryptionService.rotate_key("v1", "v2", b"corrupted-garbage")


# ---------------------------------------------------------------------------
# Decryption failure
# ---------------------------------------------------------------------------

class TestDecryptionFailure:
    """Decrypting with wrong key or corrupted data raises ValueError."""

    @pytest.mark.asyncio
    async def test_decrypt_corrupted_bytes_raises(self, valid_fernet_key):
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            with pytest.raises(ValueError, match="Failed to decrypt"):
                await EncryptionService.decrypt(b"not-valid-ciphertext")

    @pytest.mark.asyncio
    async def test_decrypt_wrong_key_id_raises(self, valid_fernet_key):
        """Ciphertext encrypted with v1 cannot be decrypted with v2."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            ciphertext = await EncryptionService.encrypt("secret", key_id="v1")
            with pytest.raises(ValueError):
                await EncryptionService.decrypt(ciphertext, key_id="v2")


# ---------------------------------------------------------------------------
# Non-ASCII key_id
# ---------------------------------------------------------------------------

class TestNonAsciiKeyId:
    """Non-ASCII key_ids are rejected with a clear error."""

    @pytest.mark.asyncio
    async def test_non_ascii_key_id_raises_value_error(self, valid_fernet_key):
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            with pytest.raises(ValueError, match="ASCII"):
                await EncryptionService.encrypt("data", key_id="кey")


# ---------------------------------------------------------------------------
# Master key validation
# ---------------------------------------------------------------------------

class TestMasterKeyValidation:
    """Validate the CREDENTIALS_MASTER_KEY environment variable."""

    def test_invalid_key_length_raises(self):
        """A key that is not 43 chars raises ValueError."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": "too-short"}):
            with pytest.raises(ValueError, match="invalid length"):
                EncryptionService._get_master_key()

    def test_valid_key_sets_master_key(self, valid_fernet_key):
        """A 43-char key is accepted and stored."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            key = EncryptionService._get_master_key()
            assert key == valid_fernet_key.encode()


# ---------------------------------------------------------------------------
# Production safety guard
# ---------------------------------------------------------------------------

class TestProductionSafetyGuard:
    """Ephemeral key generation is blocked in production without opt-in."""

    def test_production_without_key_raises(self):
        """No CREDENTIALS_MASTER_KEY + ENVIRONMENT=production raises RuntimeError."""
        env = {"ENVIRONMENT": "production"}
        # Ensure no key is set
        env_clean = {k: v for k, v in os.environ.items() if k != "CREDENTIALS_MASTER_KEY"}
        env_clean.update(env)
        with patch.dict(os.environ, env_clean, clear=True):
            with pytest.raises(RuntimeError, match="CREDENTIALS_MASTER_KEY is required"):
                EncryptionService._generate_ephemeral_key()

    def test_production_with_opt_in_allowed(self):
        """Production-like environments ignore ALLOW_EPHEMERAL_ENCRYPTION."""
        env_clean = {k: v for k, v in os.environ.items() if k != "CREDENTIALS_MASTER_KEY"}
        env_clean.update({"ENVIRONMENT": "production", "ALLOW_EPHEMERAL_ENCRYPTION": "true"})
        with patch.dict(os.environ, env_clean, clear=True):
            with pytest.raises(RuntimeError, match="never permitted"):
                EncryptionService._generate_ephemeral_key()

    def test_development_generates_ephemeral_key(self):
        """Non-production still requires explicit opt-in before using ephemeral keys."""
        env_clean = {k: v for k, v in os.environ.items() if k != "CREDENTIALS_MASTER_KEY"}
        env_clean["ENVIRONMENT"] = "development"
        with patch.dict(os.environ, env_clean, clear=True):
            with pytest.raises(RuntimeError, match="ALLOW_EPHEMERAL_ENCRYPTION=true"):
                EncryptionService._generate_ephemeral_key()

    def test_development_with_opt_in_generates_ephemeral_key(self):
        """Explicit local-dev opt-in allows ephemeral key generation."""
        env_clean = {k: v for k, v in os.environ.items() if k != "CREDENTIALS_MASTER_KEY"}
        env_clean.update({"ENVIRONMENT": "development", "ALLOW_EPHEMERAL_ENCRYPTION": "true"})
        with patch.dict(os.environ, env_clean, clear=True):
            key = EncryptionService._generate_ephemeral_key()
            assert key is not None


# ---------------------------------------------------------------------------
# LRU cache eviction
# ---------------------------------------------------------------------------

class TestLRUCacheEviction:
    """Cache evicts oldest entries when MAX_CACHE_SIZE is reached."""

    @pytest.mark.asyncio
    async def test_cache_does_not_exceed_max_size(self, valid_fernet_key):
        """Creating more than MAX_CACHE_SIZE distinct key_ids doesn't grow cache beyond limit."""
        with patch.dict(os.environ, {"CREDENTIALS_MASTER_KEY": valid_fernet_key}):
            for i in range(MAX_CACHE_SIZE + 5):
                await EncryptionService._get_fernet(f"key{i}")

            assert len(EncryptionService._key_cache) <= MAX_CACHE_SIZE
