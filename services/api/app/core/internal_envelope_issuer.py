"""Mints the signed Fabric4L internal AuthContext envelope at the gateway.

Provides:
    - :func:`issue_envelope` — sign an :class:`AuthContext` for downstream calls.
    - :func:`build_internal_headers` — convenience for httpx clients.
    - :class:`InternalServiceClientFactory` — produces httpx clients that
      auto-attach the envelope to every outbound L1\u2013L6 call.

The signing key never leaves the gateway process.
"""
from __future__ import annotations

import logging
from typing import Mapping

import httpx

from value_fabric.shared.identity.fabric_auth import AuthContext, sign_envelope

from .clerk_config import InternalEnvelopeSettings

logger = logging.getLogger(__name__)

ENVELOPE_HEADER = "X-Fabric-Auth"
TENANT_HINT_HEADER = "X-Tenant-ID"
REQUEST_ID_HEADER = "X-Request-ID"


def issue_envelope(auth: AuthContext, *, settings: InternalEnvelopeSettings) -> str:
    if settings.signing_key is None:
        raise RuntimeError("issue_envelope requires a configured signing_key")
    return sign_envelope(auth, signing_key=settings.signing_key)


def build_internal_headers(
    auth: AuthContext, *, settings: InternalEnvelopeSettings
) -> dict[str, str]:
    """Return the canonical header set for service-to-service calls.

    The tenant hint and request id are observability-only; downstream
    services must trust only the signed envelope for authorization.
    """
    token = issue_envelope(auth, settings=settings)
    return {
        ENVELOPE_HEADER: token,
        TENANT_HINT_HEADER: auth.tenant_id,
        REQUEST_ID_HEADER: auth.request_id,
    }


class InternalServiceClientFactory:
    """Creates httpx clients that attach a fresh envelope per request.

    The envelope is rebuilt on each call (rather than per-client) so it
    naturally honors the configured TTL — there is no risk of replaying
    a stale envelope across long-lived background tasks.
    """

    def __init__(self, settings: InternalEnvelopeSettings) -> None:
        if settings.signing_key is None:
            raise RuntimeError(
                "InternalServiceClientFactory requires gateway signing_key"
            )
        self._settings = settings

    def headers_for(self, auth: AuthContext) -> dict[str, str]:
        return build_internal_headers(auth, settings=self._settings)

    def client(
        self,
        *,
        base_url: str,
        timeout: float = 10.0,
        extra_headers: Mapping[str, str] | None = None,
    ) -> httpx.Client:
        """Return an httpx.Client bound to ``base_url``.

        The caller passes the current :class:`AuthContext` to ``send``
        below; the envelope is added at send-time.
        """
        headers = dict(extra_headers or {})
        return httpx.Client(base_url=base_url, timeout=timeout, headers=headers)

    def send(
        self,
        client: httpx.Client,
        *,
        method: str,
        url: str,
        auth: AuthContext,
        **kwargs,
    ) -> httpx.Response:
        merged_headers: dict[str, str] = dict(kwargs.pop("headers", {}) or {})
        merged_headers.update(self.headers_for(auth))
        return client.request(method, url, headers=merged_headers, **kwargs)
