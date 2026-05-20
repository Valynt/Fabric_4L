"""Access control for Prometheus `/metrics` endpoints.

All layers expose `/metrics` for Prometheus scraping. To prevent accidental
public exposure of internal counters (which can leak tenant volume, error
rates, build info, etc.) every layer must gate the endpoint with the same
verification logic.

Verification order:
  1. ``Authorization: Bearer <token>`` matching ``METRICS_INTERNAL_SCRAPE_TOKEN``.
  2. ``X-Prometheus-Scrape-Token: <token>`` matching the same env var.
  3. Origin IP in RFC1918 private space or loopback (cluster-internal scrape).
  4. ``ENVIRONMENT=development`` AND ``ALLOW_INSECURE_DEV_AUTH_BYPASS=true``.

A denied request is logged with diagnostic context and returns ``False``.
"""

from __future__ import annotations

import logging
import os
import secrets
from collections.abc import Mapping
from typing import Any

logger = logging.getLogger(__name__)

PRODUCTION_LIKE_ENVIRONMENTS = {"production", "prod", "staging", "stage", "release", "uat"}


def _header_get(headers: Any, name: str) -> str:
    """Return a header value using case-insensitive lookup semantics.

    Starlette/FastAPI ``Headers`` already implements case-insensitive ``get``;
    this helper preserves that behavior while also protecting tests and adapters
    that pass a plain ``dict`` with lower-case or mixed-case keys.
    """
    value = headers.get(name, "") if hasattr(headers, "get") else ""
    if value:
        return str(value)
    if isinstance(headers, Mapping):
        wanted = name.lower()
        for key, candidate in headers.items():
            if str(key).lower() == wanted:
                return str(candidate)
    return ""


def _runtime_environment() -> str:
    """Resolve deployment environment consistently across service conventions.

    A production-like value in any supported variable wins over a permissive
    development value, preventing accidental metrics exposure in mixed runtime
    configurations such as ``ENVIRONMENT=development`` plus ``APP_ENV=production``.
    """
    candidates = [
        value.lower()
        for value in (os.getenv("ENVIRONMENT"), os.getenv("APP_ENV"), os.getenv("NODE_ENV"))
        if value
    ]
    for value in candidates:
        if value in PRODUCTION_LIKE_ENVIRONMENTS:
            return value
    return candidates[0] if candidates else "development"


def is_internal_ip(ip: str) -> bool:
    """Return True for RFC1918 private IPv4 ranges and loopback addresses."""
    if not ip:
        return False

    # IPv4-mapped IPv6 (e.g. ::ffff:10.0.0.1)
    if ip.startswith("::ffff:"):
        ip = ip[7:]

    if ip.startswith("10."):
        return True

    if ip.startswith("172."):
        try:
            second_octet = int(ip.split(".")[1])
            if 16 <= second_octet <= 31:
                return True
        except (ValueError, IndexError):
            pass

    if ip.startswith("192.168."):
        return True

    if ip in ("127.0.0.1", "localhost", "::1"):
        return True

    return False


def verify_metrics_access(request: Any) -> bool:
    """Verify a request is authorized to scrape ``/metrics``.

    Args:
        request: A Starlette/FastAPI ``Request``-like object exposing
            ``.headers`` (mapping) and ``.client.host``.

    Returns:
        True if any verification path succeeds, False otherwise.
    """
    expected_token = os.getenv("METRICS_INTERNAL_SCRAPE_TOKEN", "")
    headers = request.headers
    auth_header = _header_get(headers, "Authorization")

    # 1. Bearer token
    if expected_token and auth_header.startswith("Bearer "):
        provided = auth_header[7:]
        return secrets.compare_digest(provided, expected_token)

    # 2. Custom scrape token header
    scrape_header = _header_get(headers, "X-Prometheus-Scrape-Token")
    if expected_token and scrape_header:
        return secrets.compare_digest(scrape_header, expected_token)

    # 3. Internal network origin
    client_host = request.client.host if getattr(request, "client", None) else None
    if client_host and is_internal_ip(client_host):
        return True

    # 4. Development bypass (explicit opt-in only)
    env = _runtime_environment()
    allow_bypass = os.getenv("ALLOW_INSECURE_DEV_AUTH_BYPASS", "").lower() == "true"
    if env == "development" and allow_bypass:
        # Emit a WARNING so operators notice bypass is active.
        # The flag= extra field lets log aggregators alert on this event.
        logger.warning(
            "metrics_dev_bypass_enabled",
            extra={"flag": "ALLOW_INSECURE_DEV_AUTH_BYPASS"},
        )
        return True

    logger.warning(
        "Metrics access denied: client=%s, has_auth_header=%s, env=%s, bypass_allowed=%s",
        client_host,
        bool(auth_header),
        env,
        allow_bypass,
    )
    return False
