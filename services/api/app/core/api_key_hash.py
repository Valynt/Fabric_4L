"""API-key secret handling for the gateway.

Raw keys use the format ``vf_<random>`` and are hashed with HMAC-SHA256
using ``API_KEY_HMAC_SECRET``. Only the hash, prefix, and key_id are stored.
"""

from __future__ import annotations

import hmac
import os
import secrets


def _hmac_secret() -> str:
    return os.environ.get("API_KEY_HMAC_SECRET", "")


def hash_api_key(raw_key: str) -> str:
    """Return the 64-character hex HMAC-SHA256 digest of a raw API key."""
    secret = _hmac_secret().encode("utf-8")
    return hmac.new(secret, raw_key.encode("utf-8"), "sha256").hexdigest()


def extract_key_prefix(raw_key: str, length: int = 9) -> str:
    """Return a display-safe prefix of the raw key."""
    return raw_key[:length]


def generate_api_key(*, name: str) -> tuple[str, str, str]:
    """Generate a new raw API key, key_id, and prefix.

    Returns ``(raw_key, key_id, prefix)``. The raw key must be shown exactly once.
    """
    random_part = secrets.token_urlsafe(48)[:61]
    raw_key = f"vf_{random_part}"
    key_id = f"vf_key_{secrets.token_urlsafe(8)}"
    prefix = extract_key_prefix(raw_key, length=12)
    return raw_key, key_id, prefix
