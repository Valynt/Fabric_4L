"""Helpers to register the FabricAuthMiddleware from environment configuration.

L1\u2013L6 service entry points should call :func:`register_fabric_auth_from_env`
exactly once during app construction. The helper is a no-op when the
required env vars are absent so it can be safely committed to every
service before any layer is flipped to enforce mode.

Required env vars (set per service via Infisical at ``/layer{N}-*``):
    FABRIC_AUTH_PUBLIC_KEYS    JSON list/object of {kid, public_pem}.
    FABRIC_AUTH_ISSUER         Defaults to ``fabric4l-gateway``.
    FABRIC_AUTH_AUDIENCE       Defaults to ``fabric4l-internal``.
    FABRIC_AUTH_MODE           ``observe`` (default) or ``enforce``.

L1\u2013L6 services MUST NOT receive ``CLERK_*`` env vars; the architecture
sentinel test enforces this.
"""
from __future__ import annotations

import json
import logging
import os

from .context import DEFAULT_AUDIENCE, DEFAULT_ISSUER
from .middleware import FabricAuthMiddleware
from .signer import KeySet, VerificationKey

logger = logging.getLogger(__name__)


def _load_keys_from_env(raw: str) -> list[VerificationKey]:
    parsed = json.loads(raw)
    keys: list[VerificationKey] = []
    if isinstance(parsed, list):
        for entry in parsed:
            keys.append(
                VerificationKey(kid=str(entry["kid"]), public_pem=str(entry["public_pem"]))
            )
    elif isinstance(parsed, dict):
        for kid, pem in parsed.items():
            keys.append(VerificationKey(kid=str(kid), public_pem=str(pem)))
    else:
        raise ValueError("FABRIC_AUTH_PUBLIC_KEYS must be a JSON list or object")
    return keys


def register_fabric_auth_from_env(app, *, service_name: str | None = None) -> bool:
    """Register :class:`FabricAuthMiddleware` if the env is configured.

    Returns ``True`` when the middleware was registered, ``False`` when
    it was skipped (no keys configured). Logs a structured line either
    way so rollout state is observable.

    Calling this multiple times on the same app is harmless except that
    each call will add another middleware instance \u2014 callers are
    responsible for calling it once.
    """
    raw = os.getenv("FABRIC_AUTH_PUBLIC_KEYS", "").strip()
    if not raw:
        logger.info(
            "fabric_auth.skip service=%s reason=FABRIC_AUTH_PUBLIC_KEYS_unset",
            service_name or "<unknown>",
        )
        return False

    try:
        keys = _load_keys_from_env(raw)
    except (ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        logger.error(
            "fabric_auth.disabled service=%s reason=invalid_public_keys detail=%s",
            service_name or "<unknown>",
            exc,
        )
        return False

    if not keys:
        return False

    mode = os.getenv("FABRIC_AUTH_MODE", "observe").strip().lower()
    if mode not in {"observe", "enforce"}:
        logger.error(
            "fabric_auth.disabled service=%s reason=invalid_mode value=%s",
            service_name or "<unknown>",
            mode,
        )
        return False

    issuer = os.getenv("FABRIC_AUTH_ISSUER", DEFAULT_ISSUER)
    audience = os.getenv("FABRIC_AUTH_AUDIENCE", DEFAULT_AUDIENCE)

    app.add_middleware(
        FabricAuthMiddleware,
        key_set=KeySet(keys),
        expected_issuer=issuer,
        expected_audience=audience,
        mode=mode,
    )
    logger.info(
        "fabric_auth.registered service=%s mode=%s kids=%s",
        service_name or "<unknown>",
        mode,
        ",".join(sorted(k.kid for k in keys)),
    )
    return True
