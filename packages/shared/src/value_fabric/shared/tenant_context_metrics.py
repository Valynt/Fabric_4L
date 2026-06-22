"""Tenant-context security metrics shared by identity and data boundaries."""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

try:
    from prometheus_client import Counter, REGISTRY

    _TENANT_CONTEXT_INCONSISTENT_ACCESS_METRIC = "tenant_context_inconsistent_access_total"
    if _TENANT_CONTEXT_INCONSISTENT_ACCESS_METRIC in REGISTRY._names_to_collectors:
        _TENANT_CONTEXT_INCONSISTENT_ACCESS = REGISTRY._names_to_collectors[
            _TENANT_CONTEXT_INCONSISTENT_ACCESS_METRIC
        ]
    else:
        _TENANT_CONTEXT_INCONSISTENT_ACCESS = Counter(
            _TENANT_CONTEXT_INCONSISTENT_ACCESS_METRIC,
            "Total tenant-context mismatch attempts rejected by canonical boundaries.",
            ["layer", "service", "route", "source"],
        )
    _TENANT_CONTEXT_METRICS_AVAILABLE = True
except ImportError:  # pragma: no cover - prometheus_client is optional in minimal runtimes
    _TENANT_CONTEXT_INCONSISTENT_ACCESS = None
    _TENANT_CONTEXT_METRICS_AVAILABLE = False


def record_inconsistent_tenant_context_access(
    *,
    layer: str = "shared",
    service: str = "identity",
    route: str = "unknown",
    source: str = "unknown",
) -> None:
    """Record a rejected tenant-context mismatch without exposing tenant IDs."""

    if not _TENANT_CONTEXT_METRICS_AVAILABLE or _TENANT_CONTEXT_INCONSISTENT_ACCESS is None:
        return

    try:
        _TENANT_CONTEXT_INCONSISTENT_ACCESS.labels(
            layer=str(layer or "unknown"),
            service=str(service or "unknown"),
            route=str(route or "unknown"),
            source=str(source or "unknown"),
        ).inc()
    except Exception:
        logger.debug("Failed to record tenant context inconsistency metric", exc_info=True)


__all__ = ["record_inconsistent_tenant_context_access"]
