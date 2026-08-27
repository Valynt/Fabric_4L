from __future__ import annotations

"""Compatibility metrics for deprecated Layer 3 usage."""


from collections import Counter

from . import compat_policy

try:
    from prometheus_client import Counter as PromCounter
except Exception:  # pragma: no cover
    PromCounter = None

_DEPRECATED_ROUTE_HITS: Counter[tuple[str, str, str]] = Counter()
_DEPRECATED_LEGACY_FIELD_HITS: Counter[tuple[str, str, str]] = Counter()
_DEPRECATED_FIELD_USAGE_COUNTERS: Counter[str] = Counter()
DEPRECATION_ACCEPTANCE_THRESHOLDS = compat_policy.DEPRECATION_ACCEPTANCE_THRESHOLDS

if PromCounter is not None:
    from prometheus_client import REGISTRY

    _ROUTE_COUNTER: PromCounter | None = None
    _FIELD_COUNTER: PromCounter | None = None

    def _get_or_create_counter(name: str, description: str, labels: list[str]) -> PromCounter:
        """Return the singleton counter or create one, tolerating test re-imports."""
        global _ROUTE_COUNTER, _FIELD_COUNTER

        if name == "layer3_deprecated_route_hits_total" and _ROUTE_COUNTER is not None:
            return _ROUTE_COUNTER
        if name == "layer3_legacy_field_usage_total" and _FIELD_COUNTER is not None:
            return _FIELD_COUNTER

        collector_name = name.removesuffix("_total")
        existing = REGISTRY._names_to_collectors.get(name) or REGISTRY._names_to_collectors.get(
            collector_name
        )
        if isinstance(existing, PromCounter):
            counter = existing
        else:
            if existing is not None:
                try:
                    REGISTRY.unregister(existing)
                except KeyError:
                    pass
            counter = PromCounter(name, description, labels)

        if name == "layer3_deprecated_route_hits_total":
            _ROUTE_COUNTER = counter
        elif name == "layer3_legacy_field_usage_total":
            _FIELD_COUNTER = counter

        return counter

    _ROUTE_COUNTER = _get_or_create_counter(
        "layer3_deprecated_route_hits_total",
        "Deprecated Layer 3 route hits",
        ["route", "tenant_id", "app_client"],
    )
    _FIELD_COUNTER = _get_or_create_counter(
        "layer3_legacy_field_usage_total",
        "Legacy field usage in Layer 3 compatibility paths",
        ["field", "tenant_id", "app_client"],
    )
else:
    _ROUTE_COUNTER = None
    _FIELD_COUNTER = None


def record_deprecated_route_hit(route: str, *, tenant_id: str, app_client: str) -> None:
    key = (route, tenant_id or "unknown", app_client or "unknown")
    _DEPRECATED_ROUTE_HITS[key] += 1
    if _ROUTE_COUNTER is not None:
        _ROUTE_COUNTER.labels(route=key[0], tenant_id=key[1], app_client=key[2]).inc()


def record_deprecated_legacy_field_usage(field: str, *, tenant_id: str, app_client: str) -> None:
    key = (field, tenant_id or "unknown", app_client or "unknown")
    _DEPRECATED_LEGACY_FIELD_HITS[key] += 1
    if _FIELD_COUNTER is not None:
        _FIELD_COUNTER.labels(field=key[0], tenant_id=key[1], app_client=key[2]).inc()


def record_deprecated_field_usage(metric: str) -> None:
    """Increment a cumulative legacy field usage counter for deprecation telemetry."""
    _DEPRECATED_FIELD_USAGE_COUNTERS[metric] += 1


def get_deprecated_field_usage_counters() -> dict[str, int]:
    """Return cumulative legacy field usage counters for deprecation telemetry."""
    return {
        "graph_node_request_legacy_fields": _DEPRECATED_FIELD_USAGE_COUNTERS.get("graph_node_request_legacy_fields", 0),
        "graph_edge_request_legacy_fields": _DEPRECATED_FIELD_USAGE_COUNTERS.get("graph_edge_request_legacy_fields", 0),
        "graph_node_response_legacy_fields": _DEPRECATED_FIELD_USAGE_COUNTERS.get("graph_node_response_legacy_fields", 0),
        "graph_edge_response_legacy_fields": _DEPRECATED_FIELD_USAGE_COUNTERS.get("graph_edge_response_legacy_fields", 0),
    }


def get_compat_metrics_snapshot() -> dict[str, dict[str, int]]:
    return {
        "route_hits": {"|".join(key): value for key, value in _DEPRECATED_ROUTE_HITS.items()},
        "legacy_field_hits": {"|".join(key): value for key, value in _DEPRECATED_LEGACY_FIELD_HITS.items()},
    }


def deprecation_ready_for_removal(
    snapshot: dict[str, dict[str, int]] | None = None,
    *,
    thresholds: dict[str, int] | None = None,
) -> bool:
    """Return whether compatibility usage is below hard-removal thresholds."""
    snapshot = snapshot or get_compat_metrics_snapshot()
    return compat_policy.deprecation_ready_for_removal(snapshot, thresholds=thresholds)
