"""Clerk JWT verification for the Fabric4L API gateway.

Phase 1 design notes:
    - Only this module talks to Clerk. L1\u2013L6 must never import it.
    - JWKS is cached in-process with a TTL; a 401 with kid=unknown forces
      a refresh exactly once per request to handle key rotation gracefully.
    - The ``authorized_parties`` (azp) claim is enforced when the
      configuration provides it; this matches Clerk's recommended
      backend verification flow.
"""
from __future__ import annotations

import json
import logging
import threading
import time
from dataclasses import dataclass
from typing import Any

import httpx
import jwt as pyjwt
from jwt import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    PyJWKClient,
    PyJWKClientError,
)

from .clerk_config import ClerkSettings

logger = logging.getLogger(__name__)

_JWKS_CACHE_TTL_SECONDS = 600  # 10 minutes
_JWKS_FETCH_TIMEOUT_SECONDS = 5.0


class ClerkTokenError(Exception):
    """Sanitized error for Clerk verification failures."""

    code: str = "auth.clerk_token_invalid"
    http_status: int = 401
    public_message: str = "Authentication required."

    def __init__(self, *, log_detail: str | None = None) -> None:
        super().__init__(log_detail or self.public_message)
        self.log_detail = log_detail


class ClerkTokenExpired(ClerkTokenError):
    code = "auth.clerk_token_expired"


class ClerkAuthorizedPartyError(ClerkTokenError):
    code = "auth.clerk_unauthorized_party"
    http_status = 403
    public_message = "You do not have access to this resource."


@dataclass(frozen=True)
class ClerkClaims:
    sub: str               # Clerk user id
    org_id: str | None     # active organization id ("org_..."); may be absent
    org_role: str | None
    org_permissions: tuple[str, ...]
    azp: str | None
    raw: dict[str, Any]


class ClerkJWKSCache:
    """In-process JWKS cache with on-miss refresh."""

    def __init__(self, jwks_url: str) -> None:
        self._jwks_url = jwks_url
        self._lock = threading.Lock()
        self._jwks: dict[str, Any] | None = None
        self._fetched_at: float = 0.0

    def _is_stale(self) -> bool:
        return (time.time() - self._fetched_at) > _JWKS_CACHE_TTL_SECONDS

    def _fetch(self) -> dict[str, Any]:
        with httpx.Client(timeout=_JWKS_FETCH_TIMEOUT_SECONDS) as client:
            response = client.get(self._jwks_url)
            response.raise_for_status()
            data = response.json()
        if not isinstance(data, dict) or "keys" not in data:
            raise ClerkTokenError(log_detail=f"invalid JWKS payload from {self._jwks_url}")
        return data

    def get(self, *, force_refresh: bool = False) -> dict[str, Any]:
        with self._lock:
            if force_refresh or self._jwks is None or self._is_stale():
                logger.info(
                    "Fetching Clerk JWKS (force=%s, stale=%s)",
                    force_refresh,
                    self._is_stale(),
                )
                try:
                    fresh_jwks = self._fetch()
                    self._jwks = fresh_jwks
                    self._fetched_at = time.time()
                except Exception as exc:
                    if self._jwks is not None:
                        logger.warning(
                            "JWKS endpoint outage or fetch failure (%s); falling back to cached JWKS",
                            exc,
                        )
                        return self._jwks
                    raise ClerkTokenError(log_detail=f"JWKS fetch failed: {exc}") from exc
            return self._jwks

    def signing_key_for_kid(self, kid: str, *, force_refresh: bool = False) -> Any:
        jwks = self.get(force_refresh=force_refresh)
        for entry in jwks.get("keys", []):
            if entry.get("kid") == kid:
                # Use PyJWT's helper to materialize the public key from the JWK.
                return pyjwt.algorithms.RSAAlgorithm.from_jwk(json.dumps(entry))
        raise ClerkTokenError(log_detail=f"no JWKS entry for kid={kid!r}")

    def get_status(self) -> dict[str, Any]:
        with self._lock:
            cached_count = len(self._jwks.get("keys", [])) if self._jwks else 0
            if cached_count > 0:
                age = time.time() - self._fetched_at
                status = "fresh" if age < _JWKS_CACHE_TTL_SECONDS else "stale"
            else:
                status = "empty"
            return {
                "status": status,
                "cached_keys_count": cached_count,
                "fetched_at": self._fetched_at,
            }


class ClerkVerifier:
    """Verifies Clerk-issued JWTs and returns sanitized claims."""

    def __init__(
        self,
        settings: ClerkSettings,
        *,
        jwks_cache: ClerkJWKSCache | None = None,
    ) -> None:
        self._settings = settings
        self._jwks_cache = jwks_cache or ClerkJWKSCache(settings.jwks_url)

    @property
    def jwks_cache(self) -> ClerkJWKSCache | None:
        return self._jwks_cache

    def verify(self, token: str) -> ClerkClaims:
        if not token or not isinstance(token, str):
            raise ClerkTokenError(log_detail="empty token")

        try:
            unverified_header = pyjwt.get_unverified_header(token)
        except InvalidTokenError as exc:
            raise ClerkTokenError(log_detail=f"header parse failed: {exc}") from exc

        alg = unverified_header.get("alg")
        if alg != "RS256":
            # Clerk uses RS256; reject anything else (especially "none").
            raise ClerkTokenError(log_detail=f"unsupported alg={alg!r}")

        kid = unverified_header.get("kid")
        if not kid:
            raise ClerkTokenError(log_detail="missing kid")

        # Resolve signing key: prefer pinned PEM if operator configured one.
        try:
            if self._settings.pinned_jwt_pem:
                signing_key = self._settings.pinned_jwt_pem
            else:
                try:
                    signing_key = self._jwks_cache.signing_key_for_kid(kid)
                except ClerkTokenError:
                    # Allow exactly one forced refresh on cache miss.
                    signing_key = self._jwks_cache.signing_key_for_kid(
                        kid, force_refresh=True
                    )
        except (PyJWKClientError, httpx.HTTPError) as exc:
            raise ClerkTokenError(log_detail=f"JWKS fetch failed: {exc}") from exc

        try:
            claims: dict[str, Any] = pyjwt.decode(
                token,
                signing_key,
                algorithms=["RS256"],
                audience=self._settings.jwt_audience,
                issuer=self._settings.issuer,
                leeway=self._settings.leeway_seconds,
                options={
                    "require": ["sub", "iss", "aud", "exp", "iat"],
                    "verify_signature": True,
                    "verify_exp": True,
                    "verify_iss": True,
                    "verify_aud": True,
                },
            )
        except ExpiredSignatureError as exc:
            raise ClerkTokenExpired(log_detail="token_expired") from exc
        except (
            InvalidSignatureError,
            InvalidIssuerError,
            InvalidAudienceError,
            InvalidTokenError,
        ) as exc:
            raise ClerkTokenError(log_detail="token_invalid") from exc

        # azp (authorized party) check — Clerk recommends this for SPA tokens.
        azp = claims.get("azp")
        if self._settings.authorized_parties:
            if azp is None or azp not in self._settings.authorized_parties:
                raise ClerkAuthorizedPartyError(
                    log_detail=f"azp={azp!r} not in authorized_parties"
                )

        org_id = claims.get("org_id")
        org_role = claims.get("org_role")
        org_permissions_raw = claims.get("org_permissions") or []
        if not isinstance(org_permissions_raw, list):
            raise ClerkTokenError(log_detail="org_permissions must be a list")

        return ClerkClaims(
            sub=str(claims["sub"]),
            org_id=str(org_id) if org_id is not None else None,
            org_role=str(org_role) if org_role is not None else None,
            org_permissions=tuple(str(p) for p in org_permissions_raw),
            azp=str(azp) if azp is not None else None,
            raw=claims,
        )
