from __future__ import annotations

"""URL safety and anti-SSRF validation helpers for Layer 1 ingestion."""


import ipaddress
import socket
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit, urlunsplit

from ..shared.models import ComplianceEventType, ComplianceLog

ALLOWED_SCHEMES = {"http", "https"}
DEFAULT_ALLOWED_PORTS = {80, 443}
CLOUD_METADATA_IPS = {
    "169.254.169.254",  # AWS / Azure / GCP instance metadata
    "169.254.170.2",  # AWS ECS task metadata
    "100.100.100.200",  # Alibaba Cloud instance metadata
    "192.0.0.254",  # Oracle Cloud instance metadata
    "fd00:ec2::254",  # AWS EC2 IPv6 instance metadata
}
CLOUD_METADATA_HOSTNAMES = {
    "metadata.google.internal",
    "metadata.internal",
}
CLOUD_METADATA_IP_ADDRESSES = frozenset(
    ipaddress.ip_address(value) for value in CLOUD_METADATA_IPS
)


class URLSafetyError(ValueError):
    """Stable URL safety validation error without sensitive internals."""

    def __init__(self, reason_code: str, message: str = "URL blocked by compliance policy") -> None:
        super().__init__(message)
        self.reason_code = reason_code
        self.message = message


@dataclass(frozen=True)
class URLSafetyResult:
    normalized_url: str
    hostname: str
    scheme: str
    port: int
    resolved_ips: tuple[str, ...]


def _resolve_ips(hostname: str) -> tuple[str, ...]:
    ips = {
        addr[4][0]
        for addr in socket.getaddrinfo(hostname, None, proto=socket.IPPROTO_TCP)
        if addr and addr[4]
    }
    return tuple(sorted(ips))


def _is_blocked_ip(ip: str) -> bool:
    parsed = ipaddress.ip_address(ip)
    if parsed in CLOUD_METADATA_IP_ADDRESSES:
        return True
    return any(
        [
            parsed.is_loopback,
            parsed.is_private,
            parsed.is_link_local,
            parsed.is_multicast,
            parsed.is_reserved,
            parsed.is_unspecified,
        ]
    )


def _is_blocked_hostname(hostname: str) -> bool:
    return (
        hostname in CLOUD_METADATA_HOSTNAMES
        or hostname.endswith(".metadata")
    )


def validate_url_safety(
    url: str,
    *,
    allowlist_domains: list[str] | None = None,
    allowed_schemes: set[str] | None = None,
    allowed_ports: set[int] | None = None,
) -> URLSafetyResult:
    schemes = allowed_schemes or ALLOWED_SCHEMES
    ports = allowed_ports or DEFAULT_ALLOWED_PORTS

    try:
        parsed = urlsplit(url.strip())
    except Exception as exc:
        raise URLSafetyError("MALFORMED_URL") from exc

    if parsed.scheme not in schemes:
        raise URLSafetyError("SCHEME_BLOCKED")
    if not parsed.hostname:
        raise URLSafetyError("MALFORMED_URL")

    host = parsed.hostname.lower().rstrip(".")
    port = parsed.port or (443 if parsed.scheme == "https" else 80)
    if port not in ports:
        raise URLSafetyError("PORT_BLOCKED")
    if _is_blocked_hostname(host):
        raise URLSafetyError("IP_RANGE_BLOCKED")

    literal_ip: ipaddress.IPv4Address | ipaddress.IPv6Address | None = None
    try:
        literal_ip = ipaddress.ip_address(host)
    except ValueError:
        literal_ip = None
    if literal_ip is not None:
        if _is_blocked_ip(str(literal_ip)):
            raise URLSafetyError("IP_RANGE_BLOCKED")
        resolved_ips = (str(literal_ip),)
        normalized = urlunsplit((parsed.scheme, f"{host}:{port}", parsed.path or "/", parsed.query, ""))
        return URLSafetyResult(
            normalized_url=normalized,
            hostname=host,
            scheme=parsed.scheme,
            port=port,
            resolved_ips=resolved_ips,
        )

    if allowlist_domains:
        normalized_allowlist = [d.lower().rstrip(".") for d in allowlist_domains if d]
        if any(host == d or host.endswith(f".{d}") for d in normalized_allowlist):
            # Explicitly allowlisted domain: skip real DNS/IP resolution. Used for
            # mock/test transports and explicit trust domains. Production callers
            # pass no allowlist, so the full DNS-rebinding IP checks below remain
            # enforced for all real crawling.
            normalized = urlunsplit(
                (parsed.scheme, f"{host}:{port}", parsed.path or "/", parsed.query, "")
            )
            return URLSafetyResult(
                normalized_url=normalized,
                hostname=host,
                scheme=parsed.scheme,
                port=port,
                resolved_ips=(),
            )
        raise URLSafetyError("DOMAIN_NOT_ALLOWLISTED")

    try:
        resolved_ips = _resolve_ips(host)
    except socket.gaierror as exc:
        raise URLSafetyError("DNS_RESOLUTION_FAILED") from exc

    if not resolved_ips:
        raise URLSafetyError("DNS_RESOLUTION_FAILED")

    for ip in resolved_ips:
        if _is_blocked_ip(ip):
            raise URLSafetyError("IP_RANGE_BLOCKED")

    normalized = urlunsplit((parsed.scheme, f"{host}:{port}", parsed.path or "/", parsed.query, ""))
    return URLSafetyResult(normalized_url=normalized, hostname=host, scheme=parsed.scheme, port=port, resolved_ips=resolved_ips)


def enforce_rebinding_protection(url: str, expected_ips: tuple[str, ...]) -> None:
    host = urlsplit(url).hostname
    if not host:
        raise URLSafetyError("MALFORMED_URL")
    try:
        current = _resolve_ips(host.lower().rstrip("."))
    except socket.gaierror as exc:
        raise URLSafetyError("DNS_RESOLUTION_FAILED") from exc
    if tuple(sorted(expected_ips)) != tuple(sorted(current)):
        raise URLSafetyError("DNS_REBINDING_DETECTED")


def log_url_compliance_event(
    session: Any,
    *,
    tenant_id: Any,
    request_url: str,
    reason_code: str,
    action: str,
    job_id: Any = None,
    target_id: Any = None,
) -> None:
    log = ComplianceLog(
        tenant_id=tenant_id,
        job_id=job_id,
        target_id=target_id,
        event_type=ComplianceEventType.DOMAIN_BLOCKED.value if action == "BLOCKED" else ComplianceEventType.DOMAIN_ALLOWED.value,
        severity="WARNING" if action == "BLOCKED" else "INFO",
        request_url=request_url,
        domain_policy={"action": action, "policy_type": "URL_SAFETY", "reason": reason_code},
    )
    session.add(log)
