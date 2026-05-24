"""Ed25519 sign / verify primitives for the internal AuthContext envelope.

Design notes:
    - Algorithm is fixed to ``EdDSA`` (Ed25519). Allowing per-token
      algorithm negotiation is a footgun in JWT.
    - The gateway holds exactly one *current* signing key. Verifiers
      hold a key set indexed by ``kid`` so we can rotate without
      downtime: publish new public key first, flip signing key second,
      retire old public key third.
    - PEM is the on-disk / Infisical format. We wrap that in a small
      :class:`KeySet` to keep callers honest.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Mapping
import logging

import jwt as pyjwt
from jwt import (
    ExpiredSignatureError,
    InvalidAudienceError,
    InvalidIssuerError,
    InvalidSignatureError,
    InvalidTokenError,
    PyJWTError,
)

from .context import AuthContext, DEFAULT_AUDIENCE, DEFAULT_ISSUER
from .errors import EnvelopeExpiredError, EnvelopeInvalidError

logger = logging.getLogger(__name__)

ALGORITHM = "EdDSA"


@dataclass(frozen=True)
class SigningKey:
    """Gateway-only Ed25519 signing key."""

    kid: str
    private_pem: str


@dataclass(frozen=True)
class VerificationKey:
    """L1–L6 verification key (public half)."""

    kid: str
    public_pem: str


class KeySet:
    """Set of verification keys indexed by ``kid``.

    Phase 1 keeps this in-memory; Phase 4 will fetch from Infisical
    on rotation events.
    """

    def __init__(self, keys: list[VerificationKey]) -> None:
        if not keys:
            raise ValueError("KeySet requires at least one verification key")
        self._by_kid: dict[str, VerificationKey] = {k.kid: k for k in keys}

    def get(self, kid: str) -> VerificationKey | None:
        return self._by_kid.get(kid)

    def kids(self) -> list[str]:
        return sorted(self._by_kid.keys())


def sign_envelope(
    auth: AuthContext,
    *,
    signing_key: SigningKey,
) -> str:
    """Sign an :class:`AuthContext` and return the compact JWT string.

    The ``kid`` on the AuthContext must match the signing key's kid;
    this is a sanity check to make rotation mistakes explode loudly.
    """
    if auth.kid != signing_key.kid:
        raise ValueError(
            f"AuthContext.kid ({auth.kid!r}) does not match signing key kid "
            f"({signing_key.kid!r}); refusing to sign."
        )

    return pyjwt.encode(
        auth.to_jwt_claims(),
        signing_key.private_pem,
        algorithm=ALGORITHM,
        headers={"kid": signing_key.kid, "typ": "JWT"},
    )


def verify_envelope(
    token: str,
    *,
    key_set: KeySet,
    expected_issuer: str = DEFAULT_ISSUER,
    expected_audience: str = DEFAULT_AUDIENCE,
    leeway_seconds: int = 5,
    now: int | None = None,
) -> AuthContext:
    """Verify a signed envelope token. Raises sanitized errors on failure."""
    try:
        unverified_header = pyjwt.get_unverified_header(token)
    except PyJWTError as exc:
        logger.warning("envelope header parse failed: %s", exc)
        raise EnvelopeInvalidError(log_detail=f"header parse failed: {exc}") from exc

    if unverified_header.get("alg") != ALGORITHM:
        logger.warning(
            "envelope rejected: unexpected alg=%s", unverified_header.get("alg")
        )
        raise EnvelopeInvalidError(
            log_detail=f"unexpected alg={unverified_header.get('alg')!r}"
        )

    kid = unverified_header.get("kid")
    if not kid or not isinstance(kid, str):
        raise EnvelopeInvalidError(log_detail="missing kid")

    verification_key = key_set.get(kid)
    if verification_key is None:
        logger.warning("envelope rejected: unknown kid=%s", kid)
        raise EnvelopeInvalidError(log_detail=f"unknown kid={kid!r}")

    try:
        claims: Mapping[str, Any] = pyjwt.decode(
            token,
            verification_key.public_pem,
            algorithms=[ALGORITHM],
            audience=expected_audience,
            issuer=expected_issuer,
            leeway=leeway_seconds,
            options={
                "require": ["iat", "exp", "nbf", "iss", "aud"],
                "verify_signature": True,
                "verify_exp": True,
                "verify_nbf": True,
                "verify_iat": True,
                "verify_iss": True,
                "verify_aud": True,
            },
        )
    except ExpiredSignatureError as exc:
        raise EnvelopeExpiredError(log_detail=str(exc)) from exc
    except (InvalidSignatureError, InvalidIssuerError, InvalidAudienceError) as exc:
        raise EnvelopeInvalidError(log_detail=str(exc)) from exc
    except InvalidTokenError as exc:
        raise EnvelopeInvalidError(log_detail=str(exc)) from exc

    try:
        auth = AuthContext.from_jwt_claims(dict(claims), kid=kid)
    except (KeyError, ValueError, TypeError) as exc:
        raise EnvelopeInvalidError(log_detail=f"claim shape invalid: {exc}") from exc

    # Belt & braces: enforce expiry against the AuthContext's own iat/exp,
    # in case PyJWT decode is ever misconfigured.
    current = now if now is not None else int(datetime.now(timezone.utc).timestamp())
    if current >= auth.exp + leeway_seconds:
        raise EnvelopeExpiredError(log_detail="exp <= now")

    return auth
