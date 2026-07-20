"""External OIDC and Keycloak JWKS resolution."""
from __future__ import annotations

import json
import logging
import os
import threading
import time
from typing import Any, Dict, Optional

import httpx
import jwt

from .jwt_keys import _get_revoked_kids

logger = logging.getLogger("value_fabric.shared.identity.jwt")
_DEFAULT_KEYCLOAK_REALM = "fabric"
_DEFAULT_KEYCLOAK_JWKS_PATH = "/protocol/openid-connect/certs"

_JWKS_URL_CACHE: Dict[str, Any] = {}
_JWKS_URL_CACHE_EXPIRY: Dict[str, float] = {}
_JWKS_URL_CACHE_TTL_SECONDS = 300  # 5 minutes
_JWKS_URL_CACHE_LOCK = threading.Lock()


def _fetch_jwks_from_url(url: str) -> Optional[Dict[str, Any]]:
    """Fetch JWKS from a URL with thread-safe in-memory caching."""
    now = time.time()
    with _JWKS_URL_CACHE_LOCK:
        cached = _JWKS_URL_CACHE.get(url)
        expiry = _JWKS_URL_CACHE_EXPIRY.get(url, 0)
        if cached and now < expiry:
            return cached
    # Fetch without holding the lock so a slow IdP doesn't block other threads.
    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(url, headers={"Accept": "application/json"})
            response.raise_for_status()
            jwks = response.json()
            with _JWKS_URL_CACHE_LOCK:
                _JWKS_URL_CACHE[url] = jwks
                _JWKS_URL_CACHE_EXPIRY[url] = now + _JWKS_URL_CACHE_TTL_SECONDS
            return jwks
    except Exception as exc:
        logger.warning("Failed to fetch JWKS from %s: %s", url, exc)
        return None


def _build_keycloak_jwks_url() -> Optional[str]:
    """Build Keycloak JWKS URL from KEYCLOAK_URL and KEYCLOAK_REALM."""
    keycloak_url = os.getenv("KEYCLOAK_URL", "").strip().rstrip("/")
    realm = os.getenv("KEYCLOAK_REALM", _DEFAULT_KEYCLOAK_REALM).strip()
    if keycloak_url and realm:
        return f"{keycloak_url}/realms/{realm}{_DEFAULT_KEYCLOAK_JWKS_PATH}"
    return None


def _find_key_in_jwks(jwks: Dict[str, Any], kid: str) -> Optional[Any]:
    """Return the PyJWT algorithm key object for the given kid, or None.

    Returns None (rather than raising) for unknown algorithms, malformed key
    material, or any other parsing error so that callers always fail closed
    instead of propagating a 500.
    """
    for key in jwks.get("keys", []):
        if key.get("kid") == kid:
            try:
                alg_name = key.get("alg", "RS256")
                alg_obj = jwt.algorithms.get_default_algorithms().get(alg_name)
                if alg_obj is None:
                    logger.warning("Unsupported algorithm in JWKS key kid=%s alg=%s", kid, alg_name)
                    return None
                return alg_obj.from_jwk(json.dumps(key))
            except Exception as exc:
                logger.warning("Failed to load JWKS key kid=%s: %s", kid, exc)
                return None
    return None


def _resolve_external_key(header: Dict[str, Any], issuer: str) -> Optional[Any]:
    kid = header.get("kid")
    if not kid:
        return None
    if kid in _get_revoked_kids():
        return None

    jwks: Optional[Dict[str, Any]] = None

    # Try static JWKS JSON first (no network, no cache invalidation needed).
    # If OIDC_JWKS_JSON is set but invalid, fail closed immediately — do NOT
    # fall through to the URL path. An operator who pins keys via this variable
    # expects it to be the sole source of truth; silently falling back to the
    # live JWKS URL would defeat that intent.
    jwks_raw = os.getenv("OIDC_JWKS_JSON", "").strip()
    if jwks_raw:
        try:
            jwks = json.loads(jwks_raw)
        except json.JSONDecodeError:
            logger.error(
                "OIDC_JWKS_JSON is set but contains invalid JSON; "
                "failing closed for kid=%s (fix or unset OIDC_JWKS_JSON)",
                kid,
            )
            return None

        result = _find_key_in_jwks(jwks, kid)
        if result is not None:
            return result
        # Static JWKS doesn't contain the kid — cannot refresh, fail closed.
        logger.debug("No JWKS key found for kid=%s in static OIDC_JWKS_JSON", kid)
        return None

    # Determine the URL source for dynamic fetching (explicit URL or Keycloak auto-build)
    jwks_url = os.getenv("OIDC_JWKS_URL", "").strip() or _build_keycloak_jwks_url()
    if not jwks_url:
        logger.debug("No JWKS URL configured; cannot resolve kid=%s", kid)
        return None

    # First attempt: use cached JWKS (lock is acquired inside _fetch_jwks_from_url)
    jwks = _fetch_jwks_from_url(jwks_url)
    if jwks is not None:
        result = _find_key_in_jwks(jwks, kid)
        if result is not None:
            return result

    # kid not found in cached JWKS — attempt a single cache-busting re-fetch.
    #
    # We must NOT hold the lock across the network call: doing so would block
    # all concurrent JWT verifications (including valid tokens) for the full
    # HTTP timeout whenever the IdP is slow or unreachable.
    #
    # Double-checked locking pattern:
    #   1. Acquire lock → check if another thread already refreshed → evict
    #      stale entry → release lock.
    #   2. Fetch without the lock. Multiple threads may fetch concurrently on
    #      the first rotation; that is acceptable — at most one extra IdP call
    #      per concurrent request, not a full serialisation of all auth traffic.
    #   3. _fetch_jwks_from_url acquires the lock only for the cache write.
    logger.debug("kid=%s not in cached JWKS; forcing re-fetch from %s", kid, jwks_url)

    # Step 1: check under lock whether another thread already refreshed.
    with _JWKS_URL_CACHE_LOCK:
        cached = _JWKS_URL_CACHE.get(jwks_url)
        expiry = _JWKS_URL_CACHE_EXPIRY.get(jwks_url, 0)
        if cached and time.time() < expiry:
            result = _find_key_in_jwks(cached, kid)
            if result is not None:
                return result
        # Evict the stale entry so the next _fetch_jwks_from_url call bypasses
        # the cache check and goes to the network.
        _JWKS_URL_CACHE.pop(jwks_url, None)
        _JWKS_URL_CACHE_EXPIRY.pop(jwks_url, None)

    # Step 2: fetch without holding the lock.
    jwks = _fetch_jwks_from_url(jwks_url)

    if jwks is not None:
        result = _find_key_in_jwks(jwks, kid)
        if result is not None:
            return result

    logger.debug("No JWKS key found for kid=%s issuer=%s after cache refresh", kid, issuer)
    return None
