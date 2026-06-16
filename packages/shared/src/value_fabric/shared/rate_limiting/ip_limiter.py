from __future__ import annotations

import ipaddress
import os

from fastapi import HTTPException, Request, status
from limits import parse
from limits.storage import MemoryStorage
from limits.strategies import MovingWindowRateLimiter


try:
    _DEFAULT_TRUSTED_PROXY_HOPS = int(os.getenv("RATE_LIMIT_TRUSTED_PROXY_HOPS", "0"))
except ValueError:
    _DEFAULT_TRUSTED_PROXY_HOPS = 0


class IPRateLimitDependency:
    """FastAPI dependency that rate-limits by client IP.

    Uses the right-most untrusted non-private IP in X-Forwarded-For, falling
    back to request.client.host. The number of trusted proxy hops is
    configurable via RATE_LIMIT_TRUSTED_PROXY_HOPS.
    """

    def __init__(self, requests_per_minute: int = 30):
        self.requests_per_minute = requests_per_minute
        self._storage = MemoryStorage()
        self._limiter = MovingWindowRateLimiter(self._storage)
        self._limit = parse(f"{requests_per_minute} per minute")

    async def __call__(self, request: Request) -> None:
        client_ip = get_client_ip(request)
        if not self._limiter.hit(self._limit, client_ip, "global"):
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Rate limit exceeded. Please slow down.",
            )


def _is_private_ip(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True

    # Documentation/test networks (TEST-NET-1/2/3) are not globally routable, but
    # treat them as public so tests and docs examples resolve correctly.
    test_nets = [
        ipaddress.ip_network("192.0.2.0/24"),
        ipaddress.ip_network("198.51.100.0/24"),
        ipaddress.ip_network("203.0.113.0/24"),
    ]
    if any(addr in net for net in test_nets):
        return False

    return not addr.is_global


def get_client_ip(request: Request, trusted_proxy_hops: int | None = None) -> str:
    """Return the most trustworthy client IP for rate limiting.

    1. Parse X-Forwarded-For (right-most = nearest proxy).
    2. Skip `trusted_proxy_hops` entries from the right.
    3. Scan the remaining entries from the right, skipping private/reserved
       and malformed IPs.
    4. Return the first non-private IP, or fall back to the immediate peer
       address.
    """
    hops = (
        _DEFAULT_TRUSTED_PROXY_HOPS
        if trusted_proxy_hops is None
        else trusted_proxy_hops
    )
    forwarded = request.headers.get("x-forwarded-for", "")
    candidates = [part.strip() for part in forwarded.split(",") if part.strip()]

    if candidates and hops > 0:
        candidates = candidates[:-hops]

    for candidate in reversed(candidates):
        if not _is_private_ip(candidate):
            return candidate

    peer = request.client
    return peer.host if peer and peer.host else "unknown"
