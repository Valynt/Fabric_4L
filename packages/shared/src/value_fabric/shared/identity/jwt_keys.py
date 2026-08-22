"""JWT signing-key configuration and JWKS publication."""

from __future__ import annotations

import json
import os
from typing import Any, Dict

import jwt

from pydantic import BaseModel, ConfigDict

from value_fabric.shared.models.typed_dict import TypedDictModel


class get_jwksResult(BaseModel):
    model_config = ConfigDict(extra="allow")
    keys: list[Any]

    def __getitem__(self, key: str) -> object:
        try:
            return getattr(self, key)
        except AttributeError as exc:
            raise KeyError(key) from exc

    def __setitem__(self, key: str, value: object) -> None:
        setattr(self, key, value)

    def __contains__(self, key: str) -> bool:
        return hasattr(self, key)

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)

    def __iter__(self):
        return iter(self.model_dump())

    def items(self):
        return self.model_dump().items()

    def values(self):
        return self.model_dump().values()

    def __len__(self) -> int:
        return len(self.model_dump())


class _build_keysetResult(TypedDictModel):
    active_kid: Any
    algorithm: Any
    signing_key: Any
    verify: Any


_DEFAULT_ALGORITHM = "HS256"


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
    return {
        kid.strip()
        for kid in os.getenv("JWT_REVOKED_KIDS", "").split(",")
        if kid.strip()
    }


def _build_keyset() -> Dict[str, Any]:
    algorithm = _get_jwt_algorithm()
    active_kid = os.getenv("JWT_ACTIVE_KID", "active").strip() or "active"
    previous_kid = os.getenv("JWT_PREVIOUS_KID", "").strip()
    if algorithm == "HS256":
        active_secret = _get_jwt_secret()
        previous_secret = os.getenv("JWT_PREVIOUS_SECRET", "").strip()
        verify = {active_kid: active_secret}
        if previous_kid and previous_secret:
            verify[previous_kid] = previous_secret
        return _build_keysetResult.model_validate(
            {
                "algorithm": algorithm,
                "active_kid": active_kid,
                "signing_key": active_secret,
                "verify": verify,
            }
        )
    if algorithm in {"RS256", "ES256"}:
        active_private = os.getenv("JWT_PRIVATE_KEY_PEM", "").strip()
        active_public = os.getenv("JWT_PUBLIC_KEY_PEM", "").strip()
        previous_public = os.getenv("JWT_PREVIOUS_PUBLIC_KEY_PEM", "").strip()
        if not active_private:
            raise RuntimeError(
                f"JWT_PRIVATE_KEY_PEM is required when JWT_ALGORITHM={algorithm}"
            )
        if not active_public:
            raise RuntimeError(
                f"JWT_PUBLIC_KEY_PEM is required when JWT_ALGORITHM={algorithm}"
            )
        verify = {active_kid: active_public}
        if previous_kid and previous_public:
            verify[previous_kid] = previous_public
        return _build_keysetResult.model_validate(
            {
                "algorithm": algorithm,
                "active_kid": active_kid,
                "signing_key": active_private,
                "verify": verify,
            }
        )
    raise RuntimeError(f"Unsupported JWT_ALGORITHM: {algorithm}")


def get_jwks() -> Dict[str, Any]:
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
