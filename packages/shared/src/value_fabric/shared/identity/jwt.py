"""Backward-compatible public façade for shared JWT helpers.

Implementation is split by key configuration, external JWKS resolution, and
token operations. This module intentionally preserves existing import paths.
"""
from .jwt_external import (
    _JWKS_URL_CACHE, _JWKS_URL_CACHE_EXPIRY, _JWKS_URL_CACHE_LOCK,
    _JWKS_URL_CACHE_TTL_SECONDS, _build_keycloak_jwks_url,
    _fetch_jwks_from_url, _find_key_in_jwks, _resolve_external_key,
)
from .jwt_keys import (
    _build_keyset, _get_jwt_algorithm, _get_jwt_secret, _get_revoked_kids,
    get_jwks,
)
from .jwt_tokens import (
    ServiceJwtClaims, TokenClaims, _allow_legacy_test_tenant_ids,
    _clerk_authorized_party_allowed, _configured_clerk_authorized_parties,
    _configured_clerk_issuers, _detect_environment, _is_clerk_issuer,
    _is_non_dev_environment, _normalize_origin, decode_jwt,
    decode_service_jwt, encode_jwt, encode_service_jwt,
)

__all__ = [
    "TokenClaims", "ServiceJwtClaims", "decode_jwt", "encode_jwt",
    "decode_service_jwt", "encode_service_jwt", "get_jwks",
    "_JWKS_URL_CACHE", "_JWKS_URL_CACHE_EXPIRY", "_JWKS_URL_CACHE_LOCK",
    "_JWKS_URL_CACHE_TTL_SECONDS", "_build_keycloak_jwks_url",
    "_fetch_jwks_from_url", "_find_key_in_jwks", "_resolve_external_key",
    "_build_keyset", "_get_jwt_algorithm", "_get_jwt_secret",
    "_get_revoked_kids", "_allow_legacy_test_tenant_ids",
    "_clerk_authorized_party_allowed", "_configured_clerk_authorized_parties",
    "_configured_clerk_issuers", "_detect_environment", "_is_clerk_issuer",
    "_is_non_dev_environment", "_normalize_origin",
]
