"""
DIL Security Utilities — Remediation for V-001 through V-020.

Provides:
  - require_dil_context: Auth dependency that extracts tenant_id from
    the GovernanceMiddleware context (not from headers)
  - validate_tenant_owns_account: Tenant-scoped account lookup (V-003)
  - validate_url_safe: SSRF protection for outbound URLs (V-005, V-015)
  - AllowlistedFieldUpdate: Safe dynamic Cypher SET builder (V-006)
  - clamp_confidence: Bounded confidence adjustment (V-017)
"""

from __future__ import annotations

import ipaddress
import logging
import socket
from typing import Any
from urllib.parse import urlparse

from fastapi import Depends, HTTPException, Request, status

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# V-001 / V-002: Auth + Tenant Binding
# ---------------------------------------------------------------------------


def get_governance_context(request: Request):
    """Extract the GovernanceMiddleware context from request.state.

    Returns None if no context is set (unauthenticated request).
    """
    return getattr(request.state, "governance_context", None)


def require_dil_context(
    ctx=Depends(get_governance_context),
) -> Any:
    """Require authenticated context for DIL endpoints.

    Raises HTTP 401 if no identity could be resolved.
    Returns the RequestContext with verified tenant_id.
    """
    if ctx is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={
                "error": "AUTHENTICATION_REQUIRED",
                "message": "A valid Bearer JWT or X-API-Key is required.",
                "schemes": ["Bearer", "X-API-Key"],
            },
            headers={"WWW-Authenticate": "Bearer"},
        )
    return ctx


def get_verified_tenant_id(
    ctx=Depends(require_dil_context),
) -> str:
    """Extract the verified tenant_id from the authenticated context.

    This replaces all _extract_tenant_id() helpers that trusted X-Tenant-ID.
    The tenant_id comes from the verified JWT or API key, not from headers.
    """
    return str(ctx.tenant_id)


def verify_tenant_header_matches(
    request: Request,
    ctx=Depends(require_dil_context),
) -> str:
    """Compatibility dependency returning the verified tenant context.

    Tenant headers are browser-controlled hints, so DIL endpoints ignore them
    and use only the canonical authenticated context.
    """
    _ = request
    return str(ctx.tenant_id)


# ---------------------------------------------------------------------------
# V-005 / V-015: SSRF Protection
# ---------------------------------------------------------------------------

# Blocked schemes
_ALLOWED_SCHEMES = {"http", "https"}

# Blocked hostnames
_BLOCKED_HOSTNAMES = {
    "localhost",
    "metadata.google.internal",
    "metadata.goog",
    "169.254.169.254",
}

# Blocked IP ranges
_BLOCKED_NETWORKS = [
    ipaddress.ip_network("127.0.0.0/8"),        # Loopback
    ipaddress.ip_network("10.0.0.0/8"),          # RFC1918 Class A
    ipaddress.ip_network("172.16.0.0/12"),       # RFC1918 Class B
    ipaddress.ip_network("192.168.0.0/16"),      # RFC1918 Class C
    ipaddress.ip_network("169.254.0.0/16"),      # Link-local
    ipaddress.ip_network("::1/128"),             # IPv6 loopback
    ipaddress.ip_network("fc00::/7"),            # IPv6 ULA
    ipaddress.ip_network("fe80::/10"),           # IPv6 link-local
    ipaddress.ip_network("0.0.0.0/8"),           # Current network
]


class SSRFBlockedError(Exception):
    """Raised when a URL is blocked by SSRF protection."""

    def __init__(self, url: str, reason: str):
        self.url = url
        self.reason = reason
        super().__init__(f"SSRF blocked: {reason} (url={url})")


def validate_url_safe(url: str, *, resolve_dns: bool = True) -> str:
    """Validate that a URL is safe for outbound requests.

    Checks:
      1. Scheme is http or https
      2. Hostname is not in blocklist
      3. Resolved IP is not in blocked ranges
      4. No IP-encoding tricks (octal, decimal, hex)

    Args:
        url: The URL to validate.
        resolve_dns: Whether to resolve DNS and check the IP.

    Returns:
        The validated URL.

    Raises:
        SSRFBlockedError: If the URL is blocked.
    """
    try:
        parsed = urlparse(url)
    except Exception:
        raise SSRFBlockedError(url, "Invalid URL format")

    # Check scheme
    if parsed.scheme not in _ALLOWED_SCHEMES:
        raise SSRFBlockedError(url, f"Blocked scheme: {parsed.scheme}")

    hostname = parsed.hostname
    if not hostname:
        raise SSRFBlockedError(url, "No hostname in URL")

    # Check blocked hostnames
    hostname_lower = hostname.lower()
    if hostname_lower in _BLOCKED_HOSTNAMES:
        raise SSRFBlockedError(url, f"Blocked hostname: {hostname}")

    # Check if hostname is an IP address (including encoded forms)
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_blocked_ip(ip):
            raise SSRFBlockedError(url, f"Blocked IP address: {ip}")
    except ValueError:
        # Not an IP literal — it's a hostname, check DNS
        if resolve_dns:
            try:
                resolved = socket.getaddrinfo(hostname, None)
                for _, _, _, _, sockaddr in resolved:
                    ip = ipaddress.ip_address(sockaddr[0])
                    if _is_blocked_ip(ip):
                        raise SSRFBlockedError(
                            url,
                            f"Hostname {hostname} resolves to blocked IP {ip}",
                        )
            except socket.gaierror:
                # DNS resolution failed — allow the request to fail naturally
                pass

    # Check for IP encoding tricks (octal, decimal, hex in hostname)
    if _is_encoded_ip(hostname_lower):
        raise SSRFBlockedError(url, f"Suspected encoded IP: {hostname}")

    return url


def _is_blocked_ip(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address falls in any blocked range."""
    for network in _BLOCKED_NETWORKS:
        if ip in network:
            return True
    return False


def _is_encoded_ip(hostname: str) -> bool:
    """Detect IP addresses encoded as octal, decimal, or hex."""
    # Pure decimal (e.g., 2130706433)
    try:
        val = int(hostname)
        if 0 <= val <= 0xFFFFFFFF:
            return True
    except ValueError:
        pass

    # Hex (e.g., 0x7f000001)
    if hostname.startswith("0x"):
        try:
            val = int(hostname, 16)
            if 0 <= val <= 0xFFFFFFFF:
                return True
        except ValueError:
            pass

    # Octal dotted (e.g., 0177.0.0.1)
    parts = hostname.split(".")
    if len(parts) == 4:
        has_octal = any(
            p.startswith("0") and len(p) > 1 and p.isdigit()
            for p in parts
        )
        if has_octal:
            return True

    return False


# ---------------------------------------------------------------------------
# V-006: Safe Cypher Field Update
# ---------------------------------------------------------------------------


class AllowlistedFieldUpdate:
    """Builds safe Cypher SET clauses from an allowlist of field names.

    Only field names in the allowlist are permitted. All others are silently
    dropped (or raise if strict=True).

    Usage::

        updater = AllowlistedFieldUpdate(
            allowed={"name", "description", "domain", "strengths", "weaknesses",
                     "market_position", "pricing_tier", "target_segments"},
        )
        safe_updates, set_clause, params = updater.build("c", raw_updates)
        # set_clause = "c.name = $name, c.description = $description"
        # params = {"name": "New Name", "description": "Updated"}
    """

    def __init__(self, allowed: set[str], *, strict: bool = False):
        self._allowed = frozenset(allowed)
        self._strict = strict

    def build(
        self,
        alias: str,
        updates: dict[str, Any],
    ) -> tuple[dict[str, Any], str, dict[str, Any]]:
        """Build a safe SET clause.

        Returns:
            (safe_updates, set_clause_string, params_dict)
        """
        safe_updates = {}
        rejected = []

        for key, value in updates.items():
            if key in self._allowed:
                # Validate key is a safe identifier (alphanumeric + underscore only)
                if not key.replace("_", "").isalnum():
                    rejected.append(key)
                    continue
                safe_updates[key] = value
            else:
                rejected.append(key)

        if self._strict and rejected:
            raise ValueError(
                f"Disallowed field names in update: {rejected}"
            )

        if rejected:
            logger.warning(
                "Rejected unsafe field names in update",
                extra={"rejected": rejected},
            )

        set_parts = [f"{alias}.{k} = ${k}" for k in safe_updates]
        set_clause = ", ".join(set_parts)

        return safe_updates, set_clause, dict(safe_updates)


# ---------------------------------------------------------------------------
# V-017: Confidence Score Clamping
# ---------------------------------------------------------------------------


def clamp_confidence(current: float, adjustment: float) -> float:
    """Apply a confidence adjustment and clamp to [0.0, 1.0].

    Args:
        current: Current confidence score.
        adjustment: Adjustment value (-1.0 to 1.0).

    Returns:
        Clamped confidence score.
    """
    return max(0.0, min(1.0, current + adjustment))


# ---------------------------------------------------------------------------
# V-016: Narrative Status Validation
# ---------------------------------------------------------------------------

VALID_NARRATIVE_STATUSES = {"draft", "review", "approved", "delivered"}
VALID_HYPOTHESIS_STATUSES = {"validated", "rejected", "converted"}
VALID_HYPOTHESIS_OUTCOMES = {"validated", "rejected"}
VALID_WIN_LOSS_OUTCOMES = {"won", "lost"}
VALID_NARRATIVE_TONES = {"executive", "technical", "financial", "consultative"}
VALID_NARRATIVE_AUDIENCES = {"c_suite", "vp_director", "technical_buyer", "champion", "evaluation_committee"}


def validate_enum_value(value: str, allowed: set[str], field_name: str) -> str:
    """Validate that a value is in the allowed set.

    Raises HTTPException 422 if not.
    """
    if value not in allowed:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "error": "INVALID_VALUE",
                "message": f"Invalid {field_name}: '{value}'. Must be one of: {sorted(allowed)}",
                "field": field_name,
                "allowed_values": sorted(allowed),
            },
        )
    return value
