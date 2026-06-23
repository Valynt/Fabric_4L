"""Password hashing for human users (bcrypt).

API keys use HMAC-SHA256 (see ``value_fabric.shared.identity.hashing``) for
throughput reasons.  Human passwords use bcrypt (~100 ms/hash) which is
appropriate for low-frequency authentication operations.
"""

from __future__ import annotations

import asyncio
import logging
import os

from passlib.context import CryptContext

logger = logging.getLogger(__name__)

# bcrypt has a 72-byte password limit. We explicitly reject passwords longer
# than this limit to prevent silent truncation vulnerabilities.
MAX_BCRYPT_PASSWORD_BYTES = 72


class PasswordTooLongError(ValueError):
    """Raised when a password exceeds the bcrypt 72-byte limit."""

    def __init__(self, length: int, max_length: int = MAX_BCRYPT_PASSWORD_BYTES):
        super().__init__(
            f"Password exceeds {max_length} byte limit (got {length} bytes). "
            f"Passwords longer than {max_length} bytes cannot be securely hashed with bcrypt."
        )
        self.length = length
        self.max_length = max_length


# Lazy-initialized CryptContext so env vars can be set before first use.
_pwd_context: CryptContext | None = None


def _get_pwd_context() -> CryptContext:
    global _pwd_context
    if _pwd_context is None:
        _use_bcrypt = os.getenv("USE_BCRYPT", "true").lower() == "true"
        # Auto-detect bcrypt/passlib incompatibility (e.g. bcrypt 5.0.0)
        if _use_bcrypt:
            try:
                _test_ctx = CryptContext(schemes=["bcrypt"], deprecated="auto")
                _test_ctx.hash("probe")
            except asyncio.CancelledError:
                raise
            except Exception as exc:
                logger.warning(
                    "bcrypt/passlib compatibility issue detected (%s). "
                    "Falling back to sha256_crypt. Set USE_BCRYPT=false to suppress this warning.",
                    exc,
                )
                _use_bcrypt = False
        if not _use_bcrypt:
            logger.info("Using sha256_crypt for password hashing")
        _pwd_context = CryptContext(
            schemes=["bcrypt"] if _use_bcrypt else ["sha256_crypt"],
            deprecated="auto",
        )
    return _pwd_context


def _is_bcrypt_active() -> bool:
    """Return True if the active hashing scheme is bcrypt."""
    ctx = _get_pwd_context()
    # passlib's default_scheme() returns the active scheme name
    scheme: str = ctx.default_scheme()
    return scheme == "bcrypt"


def hash_password(password: str) -> str:
    """Hash a plain-text password.

    Enforces the bcrypt 72-byte limit only when bcrypt is the active scheme.

    Raises:
        PasswordTooLongError: If the password exceeds the byte limit and bcrypt is active.
    """
    if _is_bcrypt_active():
        password_bytes = password.encode("utf-8")
        if len(password_bytes) > MAX_BCRYPT_PASSWORD_BYTES:
            raise PasswordTooLongError(len(password_bytes))
    hashed: str = _get_pwd_context().hash(password)
    return hashed


def verify_password(plain: str, hashed: str) -> bool:
    """Verify a plain-text password against a stored hash.

    Rejects legacy sha256$ prefixed hashes unconditionally (security hardening).
    """
    if hashed.startswith("sha256$"):
        return False
    try:
        ok: bool = _get_pwd_context().verify(plain, hashed)
        return ok
    except asyncio.CancelledError:
        raise
    except Exception:
        return False
