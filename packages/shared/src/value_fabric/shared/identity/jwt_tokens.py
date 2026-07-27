"""Platform and service-to-service JWT token operations."""
from __future__ import annotations

import logging
import os
import re
import time
from typing import Any, Dict, List, Optional
from uuid import UUID

import jwt
from fastapi import HTTPException, status

from .jwt_external import _resolve_external_key
from .jwt_keys import _build_keyset, _get_revoked_kids
from .models import TokenClaims
from .permissions import normalize_role_claims
from value_fabric.shared.models.typed_dict import TypedDictModel

logger = logging.getLogger("value_fabric.shared.identity.jwt")

_DEFAULT_TENANT_CLAIM = "tenant_id"
_DEFAULT_USER_CLAIM = "sub"
_DEFAULT_ROLES_CLAIM = "roles"
_DEFAULT_ORG_CLAIM = "org_id"
_DEFAULT_WORKSPACE_CLAIM = "workspace_id"
_DEFAULT_INTERNAL_ISSUER = "value-fabric-internal"
_DEFAULT_INTERNAL_AUDIENCE = "value-fabric-services"
_DEVELOPMENT_ENVIRONMENTS = {"local", "dev", "development", "test", "testing", "ci"}
_ENV_KEYS = ("ENVIRONMENT", "ENV", "APP_ENV", "VF_ENV", "VALUE_FABRIC_ENV", "PYTHON_ENV")
_LEGACY_TEST_TENANT_ID_RE = re.compile(r"^tenant-[a-z0-9]+(?:-[a-z0-9]+)*$")
_TEST_RUNTIME_SENTINEL_KEYS = ("PYTEST_CURRENT_TEST", "PYTEST_VERSION", "VALUE_FABRIC_TEST_RUNTIME")
_PRODUCTION_LIKE_MARKER_KEYS = ("KUBERNETES_SERVICE_HOST", "K_SERVICE", "ECS_CONTAINER_METADATA_URI", "ECS_CONTAINER_METADATA_URI_V4", "AWS_EXECUTION_ENV", "DYNO")
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


def _clerk_authorized_party_allowed(payload: Dict[str, Any]) -> bool:
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


def decode_jwt(token: str) -> Optional[TokenClaims]:
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
            logger.debug("Unexpected JWT issuer: %s", issuer)
            return None

        kid = header.get("kid")
        if kid and kid in _get_revoked_kids():
            logger.debug("JWT kid revoked: %s", kid)
            return None

        payload: Dict[str, Any]
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
                logger.debug("Clerk JWT authorized party rejected")
                return None
        else:
            keyset = _build_keyset()
            algorithm = keyset["algorithm"]
            if header_alg != algorithm:
                return None
            decode_kwargs: Dict[str, Any] = {
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
    extra: Dict[str, Any] = {k: v for k, v in payload.items() if k not in standard_claims}

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
    user_id: Optional[str] = None,
    roles: Optional[List[str]] = None,
    api_key_id: Optional[str] = None,
    extra_claims: Optional[dict] = None,
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


def _get_service_auth_secret() -> Optional[str]:
    return os.getenv("SERVICE_AUTH_SECRET", "").strip() or None


def encode_service_jwt(
    tenant_id: UUID | str,
    sub: str,
    aud: str,
    *,
    expires_in_seconds: int = 300,
) -> Optional[str]:
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


def decode_service_jwt(token: str, expected_audience: Optional[str] = None) -> Optional[ServiceJwtClaims]:
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
