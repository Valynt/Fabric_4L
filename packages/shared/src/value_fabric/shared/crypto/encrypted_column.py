"""Application-level field encryption for SQLAlchemy.

Uses Fernet (symmetric AES-128-CBC + HMAC-SHA256) from the cryptography library.
The master key is read from ``CREDENTIALS_MASTER_KEY`` and deterministically
derived into a Fernet-compatible 32-byte key via SHA-256.

Encrypted fields are transparent to application code: values are encrypted on
bind (write) and decrypted on result (read).  None values pass through
unchanged.

For PII fields that require exact-match database lookups (e.g. email), use the
:func:`blind_index` helper to produce a deterministic HMAC-SHA256 hash stored
in a companion column.  The hash allows ``WHERE email_hash = ?`` queries
without revealing the plaintext.
"""

from __future__ import annotations

import base64
import functools
import hashlib
import hmac
import logging
import os

from sqlalchemy import Text, TypeDecorator
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)


@functools.lru_cache(maxsize=32)
def _derive_fernet_key(master_key: str) -> bytes:
    """Derive a Fernet-compatible 32-byte key from an arbitrary master key.

    Fernet requires a 32-byte value base64-encoded to 44 characters.
    We hash the master key with SHA-256 to get exactly 32 bytes, then
    wrap it in URL-safe base64 so Fernet accepts it.
    """
    raw = hashlib.sha256(master_key.encode("utf-8")).digest()
    return base64.urlsafe_b64encode(raw)


@functools.lru_cache(maxsize=32)
def _get_fernet_for_key(master_key: str) -> Fernet:
    """Instantiate and cache a Fernet cipher instance for a given master key."""
    return Fernet(_derive_fernet_key(master_key))


def _is_production_like() -> bool:
    """Return True if the current environment is production-like."""
    env = os.getenv("ENVIRONMENT", "development").strip().lower()
    return env in {"production", "prod", "staging", "stage"}


def _get_fernet() -> Fernet | None:
    """Return a Fernet instance or None if no key is configured."""
    key = os.getenv("CREDENTIALS_MASTER_KEY", "").strip()
    if not key:
        return None
    return _get_fernet_for_key(key)


@functools.lru_cache(maxsize=32)
def _derive_blind_index_key(raw_key_bytes: bytes) -> bytes:
    """Derive an HMAC-SHA256 key for blind indexing from raw key bytes."""
    return hashlib.sha256(raw_key_bytes + b"::blind-index-v1").digest()


def blind_index(plaintext: str | None, key: bytes | str | None = None) -> str | None:
    """Create a deterministic blind index for exact-match queries on encrypted data.

    Uses HMAC-SHA256 with a key derived from the master encryption key.
    The output is a 64-character hex string suitable for indexing, unique
    constraints, and exact lookups without revealing the plaintext.

    The plaintext is normalised (lower-cased and stripped) before hashing so
    that ``'Alice@Example.COM'`` and ``'alice@example.com'`` produce the same
    index.

    Args:
        plaintext: The raw value to index.  ``None`` returns ``None``.
        key: Optional raw key bytes or string.  Defaults to deriving from
            ``CREDENTIALS_MASTER_KEY``.

    Returns:
        A 64-character hex HMAC digest, or ``None`` when input is ``None``.
    """
    if plaintext is None:
        return None

    if key is None:
        master = os.getenv("CREDENTIALS_MASTER_KEY", "").strip()
        if not master:
            return None
        raw_key = master.encode()
    elif isinstance(key, str):
        raw_key = key.encode()
    else:
        raw_key = key

    # Derive a separate HMAC key so that a compromise of the blind-index
    # cannot be replayed against the Fernet ciphertext.
    hmac_key = _derive_blind_index_key(raw_key)
    normalised = plaintext.lower().strip().encode("utf-8")
    return hmac.new(hmac_key, normalised, hashlib.sha256).hexdigest()


class EncryptedString(TypeDecorator):
    """SQLAlchemy type that transparently encrypts/decrypts string values at rest.

    Storage uses :class:`sqlalchemy.Text` to accommodate Fernet overhead
    (ciphertext is roughly 1.35x the plaintext size plus a 128-bit HMAC).

    When ``CREDENTIALS_MASTER_KEY`` is not set, values are stored as plaintext
    with a warning so that local development and tests without encryption
    configured do not fail catastrophically.  In production the key is
    mandatory (enforced by :class:`ProductionSafetyValidator`).

    Legacy unencrypted values are handled gracefully: if decryption fails,
    the raw value is returned as-is, allowing a rolling migration.
    """

    impl = Text
    cache_ok = True

    def process_bind_param(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        fernet = _get_fernet()
        if fernet is None:
            if _is_production_like():
                raise RuntimeError(
                    "CREDENTIALS_MASTER_KEY is required in production-like environments. "
                    "EncryptedString cannot fall back to plaintext."
                )
            logger.warning(
                "CREDENTIALS_MASTER_KEY not set; storing plaintext. "
                "Configure a strong 256-bit key for production."
            )
            return value
        # Fernet produces URL-safe base64; store as ascii text.
        return fernet.encrypt(value.encode("utf-8")).decode("ascii")

    def process_result_value(self, value: str | None, dialect) -> str | None:
        if value is None:
            return None
        fernet = _get_fernet()
        if fernet is None:
            return value
        try:
            return fernet.decrypt(value.encode("ascii")).decode("utf-8")
        except InvalidToken:
            # Graceful fallback for legacy unencrypted data.
            # Log at WARNING level so configuration errors are visible in production.
            logger.warning(
                "InvalidToken on EncryptedString decrypt; returning raw value. "
                "This may indicate a CREDENTIALS_MASTER_KEY mismatch or legacy unencrypted data."
            )
            return value
