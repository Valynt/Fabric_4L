from __future__ import annotations

import json
import logging
import os
import re
import threading
import time
from typing import Any
from uuid import UUID

import httpx
import jwt
from fastapi import HTTPException, status
from value_fabric.shared.models.typed_dict import TypedDictModel

from .models import TokenClaims
from .permissions import normalize_role_claims


class get_jwksResult(TypedDictModel):
    keys: list[Any]


class _build_keysetResult(TypedDictModel):
    active_kid: Any
    algorithm: Any
    signing_key: Any
    verify: Any


logger = logging.getLogger(__name__)

_DEFAULT_ALGORITHM = "HS256"
_DEFAULT_TENANT_CLAIM = "tenant_id"
_DEFAULT_USER_CLAIM = "sub"
_DEFAULT_ROLES_CLAIM = "roles"
_DEFAULT_ORG_CLAIM = "org_id"
_DEFAULT_WORKSPACE_CLAIM = "workspace_id"
_DEFAULT_INTERNAL_ISSUER = "value-fabric-internal"
_DEFAULT_INTERNAL_AUDIENCE = "value-fabric-services"

# Keycloak integration defaults
_DEFAULT_KEYCLOAK_REALM = "fabric"
_DEFAULT_KEYCLOAK_JWKS_PATH = "/protocol/openid-connect/certs"

_DEVELOPMENT_ENVIRONMENTS = {"local", "dev", "development", "test", "testing", "ci"}
_ENV_KEYS = ("ENVIRONMENT", "ENV", "APP_ENV", "VF_ENV", "VALUE_FABRIC_ENV", "PYTHON_ENV")
_LEGACY_TEST_TENANT_ID_RE = re.compile(r"^tenant-[a-z0-9]+(?:-[a-z0-9]+)*$")
_TEST_RUNTIME_SENTINEL_KEYS = ("PYTEST_CURRENT_TEST", "PYTEST_VERSION", "VALUE_FABRIC_TEST_RUNTIME")
_PRODUCTION_LIKE_MARKER_KEYS = (
    "KUBERNETES_SERVICE_HOST",
    "K_SERVICE",
    "ECS_CONTAINER_METADATA_URI",
    "ECS_CONTAINER_METADATA_URI_V4",
    "AWS_EXECUTION_ENV",
    "DYNO",
)
_PRODUCTION_LIKE_ENVIRONMENTS = {"prod", "production", "staging", "stage", "preprod", "pre-production"}
_REQUIRED_REGISTERED_CLAIMS = ("exp", "iss", "aud")
_ALLOWED_EXTERNAL_ALGORITHMS = {"RS256", "ES256"}


def _normalize_origin(value: str) -> str:
    return value.strip().rstrip("/")


def _configured_clerk_issuers() -> set[str]:
    return {
        issuer
        for issuer in (
            os.getenv("CLERK_ISSUER", "").strip(),
            os.getenv("CLERK_JWT_ISSUER", "").strip(),
        )
        if issuer
    }


def _is_clerk_issuer(issuer: Any) -> bool:
    if not isinstance(issuer, str) or not issuer.strip():
        return False
    return issuer.strip().rstrip("/") in {_normalize_origin(value) for value in _configured_clerk_issuers()}


def _configured_clerk_authorized_parties() -> set[str]:
    return {
        _normalize_origin(value)
        for value in os.getenv("CLERK_AUTHORIZED_PARTIES", "").split(",")
        if value.strip()
    }


def _clerk_authorized_party_allowed(payload: dict[str, Any]) -> bool:
    allowed_parties = _configured_clerk_authorized_parties()
    if not allowed_parties:
        return True
    azp = payload.get("azp")
    if not isinstance(azp, str) or not azp.strip():
        return False
    return _normalize_origin(azp) in allowed_parties


def _detect_environment() -> str:
    for key in _ENV_KEYS:
        value = os.getenv(key)
        if value and value.strip():
            return value.strip().lower()
    return "development"


def _is_non_dev_environment() -> bool:
    return _detect_environment() not in _DEVELOPMENT_ENVIRONMENTS


def _allow_legacy_test_tenant_ids() -> bool:
    explicit_test_flag = (
        os.getenv("ALLOW_LEGACY_TEST_TENANT_IDS", "").strip().lower() == "true"
        or os.getenv("TESTING", "").strip().lower() == "true"
    )
    explicit_test_runtime = any(os.getenv(key, "").strip() for key in _TEST_RUNTIME_SENTINEL_KEYS)
    production_like_markers_present = any(
        os.getenv(key, "").strip() for key in _PRODUCTION_LIKE_MARKER_KEYS
    ) or _detect_environment() in _PRODUCTION_LIKE_ENVIRONMENTS
    allowed = explicit_test_flag and explicit_test_runtime and not production_like_markers_present
    if allowed:
        logger.warning(
            "legacy_tenant_id_mode_enabled",
            extra={
                "event": "legacy_tenant_id_mode_enabled",
                "component": "identity.jwt",
                "environment": _detect_environment(),
                "test_runtime_keys": [
                    key for key in _TEST_RUNTIME_SENTINEL_KEYS if os.getenv(key, "").strip()
                ],
            },
        )
    return allowed


def _get_jwt_secret() -> str:
    secret = os.getenv("JWT_SECRET", "").strip()

    if not secret:
        raise RuntimeError(
            "JWT_SECRET is required and is currently unset. "
            "Set JWT_SECRET in your environment (for local development, copy "
            ".env.example to .env/.env.dev and provide a strong secret)."
        )

    if len(secret) < 32:
        raise RuntimeError(
            f"JWT_SECRET must be at least 32 characters for security (got {len(secret)}). "
            "Set a stronger secret in your environment."
        )

    return secret


def _get_jwt_algorithm() -> str:
    return os.getenv("JWT_ALGORITHM", _DEFAULT_ALGORITHM).strip().upper()


def _get_revoked_kids() -> set[str]:
    return {kid.strip() for kid in os.getenv("JWT_REVOKED_KIDS", "").split(",") if kid.strip()}


def _build_keyset() -> dict[str, Any]:
    algorithm = _get_jwt_algorithm()
    active_kid = os.getenv("JWT_ACTIVE_KID", "active").strip() or "active"
    previous_kid = os.getenv("JWT_PREVIOUS_KID", "").strip()

    if algorithm == "HS256":
        active_secret = _get_jwt_secret()
        previous_secret = os.getenv("JWT_PREVIOUS_SECRET", "").strip()
        verify = {active_kid: active_secret}
        if previous_kid and previous_secret:
            verify[previous_kid] = previous_secret
        return _build_keysetResult.model_validate({"algorithm": algorithm, "active_kid": active_kid, "signing_key": active_secret, "verify": verify})

    if algorithm in {"RS256", "ES256"}:
        active_private = os.getenv("JWT_PRIVATE_KEY_PEM", "").strip()
        active_public = os.getenv("JWT_PUBLIC_KEY_PEM", "").strip()
        previous_public = os.getenv("JWT_PREVIOUS_PUBLIC_KEY_PEM", "").strip()
        if not active_private:
            raise RuntimeError(f"JWT_PRIVATE_KEY_PEM is required when JWT_ALGORITHM={algorithm}")
        if not active_public:
            raise RuntimeError(f"JWT_PUBLIC_KEY_PEM is required when JWT_ALGORITHM={algorithm}")
        verify = {active_kid: active_public}
        if previous_kid and previous_public:
            verify[previous_kid] = previous_public
        return _build_keysetResult.model_validate({"algorithm": algorithm, "active_kid": active_kid, "signing_key": active_private, "verify": verify})

    raise RuntimeError(f"Unsupported JWT_ALGORITHM: {algorithm}")


def get_jwks() -> dict[str, Any]:
    keyset = _build_keyset()
    alg = keyset["algorithm"]
    if alg not in {"RS256", "ES256"}:
        return get_jwksResult.model_validate({"keys": []})
    keys = []
    for kid, public_key in keyset["verify"].items():
        jwk_json = jwt.algorithms.get_default_algorithms()[alg].to_jwk(public_key)
        key_obj = json.loads(jwk_json)
        key_obj["kid"] = kid
        key_obj["alg"] = alg
        key_obj["use"] = "sig"
        keys.append(key_obj)
    return get_jwksResult.model_validate({"keys": keys})


_JWKS_URL_CACHE: dict[str, Any] = {}
_JWKS_URL_CACHE_EXPIRY: dict[str, float] = {}
_JWKS_URL_CACHE_TTL_SECONDS = 300  # 5 minutes
_JWKS_URL_CACHE_LOCK = threading.Lock()


def _fetch_jwks_from_url(url: str) -> dict[str, Any] | None:
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


def _build_keycloak_jwks_url() -> str | None:
    """Build Keycloak JWKS URL from KEYCLOAK_URL and KEYCLOAK_REALM."""
    keycloak_url = os.getenv("KEYCLOAK_URL", "").strip().rstrip("/")
    realm = os.getenv("KEYCLOAK_REALM", _DEFAULT_KEYCLOAK_REALM).strip()
    if keycloak_url and realm:
        return f"{keycloak_url}/realms/{realm}{_DEFAULT_KEYCLOAK_JWKS_PATH}"
    return None


def _find_key_in_jwks(jwks: dict[str, Any], kid: str) -> Any | None:
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


def _resolve_external_key(header: dict[str, Any], issuer: str) -> Any | None:
    kid = header.get("kid")
    if not kid:
        return None
    if kid in _get_revoked_kids():
        return None

    jwks: dict[str, Any] | None = None

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


def decode_jwt(token: str) -> TokenClaims | None:
    tenant_claim = os.getenv("JWT_TENANT_CLAIM", _DEFAULT_TENANT_CLAIM)
    user_claim = os.getenv("JWT_USER_CLAIM", _DEFAULT_USER_CLAIM)
    roles_claim = os.getenv("JWT_ROLES_CLAIM", _DEFAULT_ROLES_CLAIM)
    internal_issuer = os.getenv("JWT_ISSUER", _DEFAULT_INTERNAL_ISSUER)
    internal_audience = os.getenv("JWT_AUDIENCE", _DEFAULT_INTERNAL_AUDIENCE)
    # Support both generic OIDC and Clerk-specific issuer configuration.
    # CLERK_ISSUER is the canonical gateway env; CLERK_JWT_ISSUER remains
    # accepted as a compatibility alias for older deployment notes.
    oidc_issuer = (
        os.getenv("OIDC_ISSUER", "").strip()
        or os.getenv("CLERK_ISSUER", "").strip()
        or os.getenv("CLERK_JWT_ISSUER", "").strip()
    )
    oidc_audience = os.getenv("OIDC_AUDIENCE", "").strip() or os.getenv("CLERK_JWT_AUDIENCE", "").strip()
    # Clerk-specific JWKS URL override
    clerk_jwks_url = os.getenv("CLERK_JWKS_URL", "").strip()
    if clerk_jwks_url and not os.getenv("OIDC_JWKS_URL", "").strip():
        os.environ.setdefault("OIDC_JWKS_URL", clerk_jwks_url)

    try:
        header = jwt.get_unverified_header(token)
        unverified = jwt.decode(
            token,
            options={
                "verify_signature": False,
                "verify_exp": False,
                "verify_aud": False,
                "verify_iss": False,
                "verify_iat": False,
                "verify_nbf": False,
            },
        )
        header_alg = str(header.get("alg", "")).strip().upper()
        if not header_alg:
            return None
        issuer = unverified.get("iss")
        if any(unverified.get(claim) in (None, "") for claim in _REQUIRED_REGISTERED_CLAIMS):
            return None
        audience = oidc_audience if oidc_issuer and issuer == oidc_issuer else internal_audience
        expected_issuer = oidc_issuer if oidc_issuer and issuer == oidc_issuer else internal_issuer

        if expected_issuer is not None and issuer != expected_issuer:
            return None

        kid = header.get("kid")
        if kid and kid in _get_revoked_kids():
            return None

        payload: dict[str, Any]
        if expected_issuer == oidc_issuer:
            if header_alg not in _ALLOWED_EXTERNAL_ALGORITHMS:
                return None
            verify_key = _resolve_external_key(header, issuer)
            if verify_key is None:
                return None
            payload = jwt.decode(
                token,
                verify_key,
                algorithms=[header_alg],
                audience=audience,
                issuer=expected_issuer,
                options={
                    "require": list(_REQUIRED_REGISTERED_CLAIMS),
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                },
            )
            if _is_clerk_issuer(expected_issuer) and not _clerk_authorized_party_allowed(payload):
                return None
        else:
            keyset = _build_keyset()
            algorithm = keyset["algorithm"]
            if header_alg != algorithm:
                return None
            decode_kwargs: dict[str, Any] = {
                "algorithms": [algorithm],
                "audience": audience,
                "issuer": expected_issuer,
                "options": {
                    "require": list(_REQUIRED_REGISTERED_CLAIMS),
                    "verify_exp": True,
                    "verify_aud": True,
                    "verify_iss": True,
                    "verify_iat": True,
                    "verify_nbf": True,
                },
            }
            verify_keys = keyset["verify"]
            if kid and kid in verify_keys:
                candidates = [verify_keys[kid]]
            elif kid and kid not in verify_keys:
                return None
            else:
                candidates = list(verify_keys.values())
            payload = None
            for key in candidates:
                try:
                    payload = jwt.decode(token, key, **decode_kwargs)
                    break
                except jwt.ExpiredSignatureError:
                    raise
                except jwt.InvalidTokenError:
                    continue
            if payload is None:
                return None
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token has expired.", headers={"WWW-Authenticate": "Bearer"})
    except jwt.InvalidTokenError:
        return None

    raw_tenant = payload.get(tenant_claim)
    if not raw_tenant:
        return None
    try:
        tenant_id: UUID | str = UUID(str(raw_tenant))
    except (ValueError, AttributeError):
        if _allow_legacy_test_tenant_ids() and _LEGACY_TEST_TENANT_ID_RE.fullmatch(str(raw_tenant)):
            tenant_id = str(raw_tenant)
        else:
            return None

    roles = payload.get(roles_claim, [])
    if not roles and payload.get("role"):
        roles = [payload.get("role")]
    if isinstance(roles, str):
        roles = [roles]
    roles = normalize_role_claims(roles)
    exp = payload.get("exp")
    iat = payload.get("iat")
    jti = payload.get("jti")
    org_claim = os.getenv("JWT_ORG_CLAIM", _DEFAULT_ORG_CLAIM)
    workspace_claim = os.getenv("JWT_WORKSPACE_CLAIM", _DEFAULT_WORKSPACE_CLAIM)
    standard_claims = {
        tenant_claim, user_claim, roles_claim, org_claim, workspace_claim,
        "role", "exp", "iat", "jti", "api_key_id", "email", "name", "impersonator_id",
    }
    extra: dict[str, Any] = {k: v for k, v in payload.items() if k not in standard_claims}

    return TokenClaims(
        sub=payload.get(user_claim, ""),
        tenant_id=str(tenant_id) if tenant_id else None,
        org_id=payload.get(org_claim),
        workspace_id=payload.get(workspace_claim),
        roles=roles if isinstance(roles, list) else [roles] if roles else [],
        email=payload.get("email"),
        name=payload.get("name"),
        impersonator_id=payload.get("impersonator_id"),
        exp=exp if isinstance(exp, int) else None,
        iat=iat if isinstance(iat, int) else None,
        jti=jti if isinstance(jti, str) else None,
        extra_claims=extra,
    )


def encode_jwt(
    tenant_id: UUID,
    *,
    user_id: str | None = None,
    roles: list[str] | None = None,
    api_key_id: str | None = None,
    extra_claims: dict | None = None,
    expires_in_seconds: int = 3600,
) -> str:
    keyset = _build_keyset()
    algorithm = keyset["algorithm"]
    tenant_claim = os.getenv("JWT_TENANT_CLAIM", _DEFAULT_TENANT_CLAIM)
    user_claim = os.getenv("JWT_USER_CLAIM", _DEFAULT_USER_CLAIM)
    roles_claim = os.getenv("JWT_ROLES_CLAIM", _DEFAULT_ROLES_CLAIM)
    now = int(time.time())
    payload: dict = {
        tenant_claim: str(tenant_id),
        "iat": now,
        "nbf": now,  # services/api decode_token requires nbf; keep in sync
        "exp": now + expires_in_seconds,
        "iss": os.getenv("JWT_ISSUER", _DEFAULT_INTERNAL_ISSUER),
        "aud": os.getenv("JWT_AUDIENCE", _DEFAULT_INTERNAL_AUDIENCE),
    }
    if user_id is not None:
        payload[user_claim] = user_id
    if roles is not None:
        payload[roles_claim] = roles
    if api_key_id is not None:
        payload["api_key_id"] = api_key_id
    if extra_claims:
        payload.update(extra_claims)

    headers = {"kid": keyset["active_kid"]}
    return jwt.encode(payload, keyset["signing_key"], algorithm=algorithm, headers=headers)


# ---------------------------------------------------------------------------
# Service-to-service JWT helpers (P1-001)
# ---------------------------------------------------------------------------

_S2S_ISSUER = "value-fabric-s2s"
_S2S_ALGORITHM = "HS256"


class ServiceJwtClaims(TypedDictModel):
    sub: str
    aud: str
    tenant_id: str
    iat: int
    exp: int
    iss: str


def _get_service_auth_secret() -> str | None:
    return os.getenv("SERVICE_AUTH_SECRET", "").strip() or None


def encode_service_jwt(
    tenant_id: UUID | str,
    sub: str,
    aud: str,
    *,
    expires_in_seconds: int = 300,
) -> str | None:
    """Sign a service-to-service JWT using SERVICE_AUTH_SECRET.

    Returns None when SERVICE_AUTH_SECRET is not configured.
    """
    secret = _get_service_auth_secret()
    if not secret:
        return None
    now = int(time.time())
    payload: dict = {
        "sub": sub,
        "aud": aud,
        "tenant_id": str(tenant_id),
        "iat": now,
        "nbf": now,
        "exp": now + expires_in_seconds,
        "iss": _S2S_ISSUER,
    }
    return jwt.encode(payload, secret, algorithm=_S2S_ALGORITHM)


def decode_service_jwt(token: str, expected_audience: str | None = None) -> ServiceJwtClaims | None:
    """Verify a service-to-service JWT signed with SERVICE_AUTH_SECRET.

    Returns None for invalid, expired, or malformed tokens.

    Args:
        token: The JWT token to verify.
        expected_audience: Optional audience to validate. If provided, the token's
            aud claim must match exactly. If not provided, audience validation
            is skipped (caller must validate).

    Raises:
        jwt.ExpiredSignatureError: If the token has expired.
    """
    secret = _get_service_auth_secret()
    if not secret:
        return None
    try:
        options = {
            "require": ["exp", "iss", "aud", "sub", "tenant_id"],
            "verify_exp": True,
            "verify_aud": expected_audience is not None,
            "verify_iss": True,
            "verify_iat": True,
            "verify_nbf": True,
        }
        decode_kwargs = {
            "algorithms": [_S2S_ALGORITHM],
            "issuer": _S2S_ISSUER,
            "options": options,
        }
        if expected_audience is not None:
            decode_kwargs["audience"] = expected_audience

        payload = jwt.decode(token, secret, **decode_kwargs)
        return ServiceJwtClaims.model_validate(payload)
    except jwt.ExpiredSignatureError:
        raise
    except Exception:
        return None
