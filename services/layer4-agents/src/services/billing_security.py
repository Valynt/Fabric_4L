from __future__ import annotations

"""Canonical Stripe billing webhook security primitives.

This module is the single source of truth for Stripe webhook source-IP checks
and request metadata extraction used by billing webhook entry points.
"""

import ipaddress
import os
from collections.abc import Iterable

from fastapi import Request

_DEFAULT_STRIPE_WEBHOOK_IP_CIDRS: tuple[str, ...] = (
    "3.18.12.63/32",
    "3.130.192.231/32",
    "13.235.14.237/32",
    "13.235.122.149/32",
    "35.154.171.200/32",
    "35.154.171.208/32",
    "52.15.183.38/32",
    "52.15.183.39/32",
    "54.88.130.27/32",
    "54.88.130.28/32",
    "54.187.174.169/32",
    "54.187.174.170/32",
)


def _parse_cidrs(cidr_values: Iterable[str]) -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    networks: list[ipaddress.IPv4Network | ipaddress.IPv6Network] = []
    for raw in cidr_values:
        value = raw.strip()
        if not value:
            continue
        networks.append(ipaddress.ip_network(value, strict=False))
    return networks


def _load_stripe_webhook_ip_networks() -> list[ipaddress.IPv4Network | ipaddress.IPv6Network]:
    configured = os.environ.get("STRIPE_WEBHOOK_IP_CIDRS", "")
    if configured.strip():
        return _parse_cidrs(configured.split(","))
    return _parse_cidrs(_DEFAULT_STRIPE_WEBHOOK_IP_CIDRS)


STRIPE_WEBHOOK_IPS = _load_stripe_webhook_ip_networks()
STRIPE_WEBHOOK_SKIP_IP_CHECK = os.environ.get("STRIPE_WEBHOOK_SKIP_IP_CHECK", "").lower() in ("true", "1", "yes")

if os.environ.get("ENVIRONMENT") == "production" and STRIPE_WEBHOOK_SKIP_IP_CHECK:
    raise RuntimeError("STRIPE_WEBHOOK_SKIP_IP_CHECK cannot be enabled in production")


def is_stripe_webhook_ip(client_ip: str) -> bool:
    try:
        ip = ipaddress.ip_address(client_ip)
        if ip.is_loopback:
            return True
        return any(ip in network for network in STRIPE_WEBHOOK_IPS)
    except ValueError:
        return False


def get_client_ip(request: Request) -> str:
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    real_ip = request.headers.get("X-Real-IP")
    if real_ip:
        return real_ip
    if hasattr(request, "client") and request.client:
        return request.client.host
    return ""
