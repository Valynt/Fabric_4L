"""Backward-compatible public façade for shared JWT helpers.

Implementation is split by key configuration, external JWKS resolution, and
token operations. This module intentionally preserves existing import paths.
"""
from .jwt_external import (
    _JWKS_URL_CACHE,
    _JWKS_URL_CACHE_EXPIRY,
    _JWKS_URL_CACHE_LOCK,
    _JWKS_URL_CACHE_TTL_SECONDS,
    _build_keycloak_jwks_url,
    _fetch_jwks_from_url,
    _find_key_in_jwks,
    _resolve_external_key,
)
from .jwt_keys import (
    _build_keyset,
    _get_jwt_algorithm,
    _get_jwt_secret,
    _get_revoked_kids,
    get_jwks,
)
from .jwt_tokens import (
    ServiceJwtClaims,
    TokenClaims,
    _allow_legacy_test_tenant_ids,
    _configured_oidc_authorized_parties,
    _configured_oidc_issuers,
    _detect_environment,
    _is_non_dev_environment,
    _is_oidc_issuer,
    _normalize_origin,
    _oidc_authorized_party_allowed,
    decode_jwt,
    decode_service_jwt,
    encode_jwt,
    encode_service_jwt,
)

__all__ = [
    "_JWKS_URL_CACHE",
    "_JWKS_URL_CACHE_EXPIRY",
    "_JWKS_URL_CACHE_LOCK",
    "_JWKS_URL_CACHE_TTL_SECONDS",
    "ServiceJwtClaims",
    "TokenClaims",
    "_allow_legacy_test_tenant_ids",
    "_build_keycloak_jwks_url",
    "_build_keyset",
    "_configured_oidc_authorized_parties",
    "_configured_oidc_issuers",
    "_detect_environment",
    "_fetch_jwks_from_url",
    "_find_key_in_jwks",
    "_get_jwt_algorithm",
    "_get_jwt_secret",
    "_get_revoked_kids",
    "_is_non_dev_environment",
    "_is_oidc_issuer",
    "_normalize_origin",
    "_oidc_authorized_party_allowed",
    "_resolve_external_key",
    "decode_jwt",
    "decode_service_jwt",
    "encode_jwt",
    "encode_service_jwt",
    "get_jwks",
]
