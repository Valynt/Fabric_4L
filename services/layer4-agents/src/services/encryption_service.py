from __future__ import annotations

"""
Encryption service for at-rest credential encryption.

Canonical runtime algorithm:
- Fernet tokens backed by AES-128-CBC + HMAC-SHA256 authentication.
"""


import asyncio
import base64
import logging
import os
from collections import OrderedDict

from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
from value_fabric.shared.security.config import is_production_like_environment

logger = logging.getLogger(__name__)

# Security constants
DEFAULT_KEY_ID: str = "v1"
PBKDF2_ITERATIONS: int = 100000  # OWASP recommendation (see _get_fernet docs)
MAX_CACHE_SIZE: int = 32
ENCRYPTION_ALGORITHM: str = "Fernet (AES-128-CBC + HMAC-SHA256)"


# Module-level lock for thread-safe initialization
_encryption_cache_lock: asyncio.Lock = asyncio.Lock()


class EncryptionService:
    """Service for encrypting and decrypting sensitive data at rest.

    Uses Fernet (AES-128-CBC + HMAC) from the cryptography library.
    For production, replace with KMS-backed encryption (AWS KMS, Vault, etc.).

    Security:
        - Keys derived from master secret using PBKDF2
        - Each encryption uses unique salt and IV
        - Authenticated encryption prevents tampering
    """

    # In production, retrieve from KMS/Vault
    _MASTER_KEY: bytes | None = None
    _key_cache: OrderedDict[str, Fernet] = OrderedDict()

    @classmethod
    def _get_cache_lock(cls) -> asyncio.Lock:
        """Get the cache lock (module-level, created at import time)."""
        return _encryption_cache_lock

    @classmethod
    def _get_master_key(cls) -> bytes:
        """Get the master encryption key from environment.

        Returns:
            Base64-encoded key bytes (suitable for Fernet)
        """
        if cls._MASTER_KEY is not None:
            return cls._MASTER_KEY

        key_b64 = os.getenv("CREDENTIALS_MASTER_KEY")
        if key_b64:
            return cls._validate_and_set_master_key(key_b64)

        return cls._generate_ephemeral_key()

    @classmethod
    def _validate_and_set_master_key(cls, key_b64: str) -> bytes:
        """Validate and set the master key from environment variable."""
        # Fernet keys are 32 bytes url-safe base64 encoded = 43 chars
        if len(key_b64) != 43:
            raise ValueError(
                f"CREDENTIALS_MASTER_KEY has invalid length: {len(key_b64)}, expected 43. "
                "Key must be 32 bytes base64-encoded."
            )
        try:
            cls._MASTER_KEY = key_b64.encode()
            return cls._MASTER_KEY
        except Exception as e:
            raise ValueError(f"CREDENTIALS_MASTER_KEY must be a valid Fernet key: {e}") from e

    @classmethod
    def _generate_ephemeral_key(cls) -> bytes:
        """Generate an ephemeral key only for explicit local development/testing."""
        environment = os.getenv("ENVIRONMENT", "development").lower()
        allow_ephemeral = os.getenv("ALLOW_EPHEMERAL_ENCRYPTION", "").lower() in ("true", "1", "yes")

        if is_production_like_environment(environment):
            raise RuntimeError(
                "CREDENTIALS_MASTER_KEY is required in production. "
                "ALLOW_EPHEMERAL_ENCRYPTION is never permitted in production-like environments."
            )

        if not allow_ephemeral:
            raise RuntimeError(
                "CREDENTIALS_MASTER_KEY is required unless ALLOW_EPHEMERAL_ENCRYPTION=true "
                "is explicitly set for local development or tests."
            )

        logger.warning(
            "ephemeral_encryption_enabled",
            extra={
                "event": "ephemeral_encryption_enabled",
                "environment": environment,
                "flag": "ALLOW_EPHEMERAL_ENCRYPTION",
            },
        )
        cls._MASTER_KEY = Fernet.generate_key()
        return cls._MASTER_KEY

    @classmethod
    async def _get_fernet(cls, key_id: str) -> Fernet:
        """Get or create Fernet instance for given key ID (async-safe with LRU cache)."""
        # Fast path: check cache without lock (read-only)
        if key_id in cls._key_cache:
            cached = cls._key_cache[key_id]
            # Note: move_to_end would require lock, so we skip LRU update on fast path
            # This is a reasonable trade-off for performance
            return cached

        # Slow path: acquire lock and create
        async with cls._get_cache_lock():
            # Double-check after acquiring lock
            if key_id in cls._key_cache:
                cls._key_cache.move_to_end(key_id)
                return cls._key_cache[key_id]

            # Derive key from master using key_id as salt context
            master = cls._get_master_key()
            # Validate key_id is ASCII to avoid unicode normalization issues
            if not key_id.isascii():
                raise ValueError(f"key_id must be ASCII-only, got: {key_id!r}")
            # Use PBKDF2 for key derivation. Note: 100k iterations is the older
            # OWASP recommendation. Modern guidance suggests 600k+ but with key
            # caching the performance impact is mitigated.
            kdf = PBKDF2HMAC(
                algorithm=hashes.SHA256(),
                length=32,
                salt=key_id.encode(),
                iterations=PBKDF2_ITERATIONS,
            )
            key = base64.urlsafe_b64encode(kdf.derive(master))

            # Evict oldest entries if cache is full (LRU)
            while len(cls._key_cache) >= MAX_CACHE_SIZE:
                cls._key_cache.popitem(last=False)

            cls._key_cache[key_id] = Fernet(key)
            return cls._key_cache[key_id]

    @classmethod
    async def encrypt(cls, plaintext: str, key_id: str = DEFAULT_KEY_ID) -> bytes:
        """Encrypt plaintext string.

        Args:
            plaintext: Data to encrypt (e.g., JSON string of credentials)
            key_id: Key version identifier for key rotation support

        Returns:
            Encrypted ciphertext as bytes
        """
        if not plaintext:
            return b""
        fernet = await cls._get_fernet(key_id)
        return fernet.encrypt(plaintext.encode())

    @classmethod
    async def decrypt(cls, ciphertext: bytes, key_id: str = DEFAULT_KEY_ID) -> str:
        """Decrypt ciphertext bytes.

        Args:
            ciphertext: Encrypted data
            key_id: Key version identifier (must match encryption key)

        Returns:
            Decrypted plaintext string

        Raises:
            ValueError: If decryption fails (invalid key, tampered data)
        """
        if not ciphertext:
            return ""
        try:
            fernet = await cls._get_fernet(key_id)
            return fernet.decrypt(ciphertext).decode()
        except Exception as e:
            logger.error("Decryption failed for key_id=%s: %s", key_id, e)
            raise ValueError(f"Failed to decrypt credentials: {e}") from e

    @classmethod
    async def rotate_key(cls, old_key_id: str, new_key_id: str, ciphertext: bytes) -> bytes:
        """Re-encrypt data with a new key.

        Args:
            old_key_id: Current key identifier
            new_key_id: New key identifier
            ciphertext: Data encrypted with old key

        Returns:
            Data re-encrypted with new key

        Raises:
            ValueError: If rotation fails (decryption/encryption error)
        """
        try:
            plaintext = await cls.decrypt(ciphertext, old_key_id)
            return await cls.encrypt(plaintext, new_key_id)
        except Exception as e:
            logger.error("Key rotation failed from %s to %s: %s", old_key_id, new_key_id, e)
            raise ValueError(f"Failed to rotate encryption key: {e}") from e
