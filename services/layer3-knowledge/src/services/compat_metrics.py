from __future__ import annotations

"""Compatibility metrics for deprecated Layer 3 usage."""


from collections import Counter

try:
    from prometheus_client import Counter as PromCounter
except Exception:  # pragma: no cover
    PromCounter = None

_DEPRECATED_ROUTE_HITS: Counter[tuple[str, str, str]] = Counter()
_DEPRECATED_LEGACY_FIELD_HITS: Counter[tuple[str, str, str]] = Counter()
DEPRECATION_ACCEPTANCE_THRESHOLDS: dict[str, int] = {
    "max_legacy_route_hits_7d": 0,
    "max_legacy_field_hits_7d": 0,
}

if PromCounter is not None:
    from prometheus_client import REGISTRY

    def _get_or_create_counter(name: str, description: str, labels: list[str]) -> PromCounter:
        """Return an existing counter or create a new one, tolerating test re-imports."""
        try:
            return PromCounter(name, description, labels)
        except ValueError as exc:
            if "Duplicated timeseries" in str(exc):
                for collector in REGISTRY._collector_to_names.keys():
                    if isinstance(collector, PromCounter) and collector._name == name:
                        return collector
            raise

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
    thresholds = thresholds or DEPRECATION_ACCEPTANCE_THRESHOLDS
    route_total = sum(snapshot.get("route_hits", {}).values())
    field_total = sum(snapshot.get("legacy_field_hits", {}).values())
    return (
        route_total <= thresholds["max_legacy_route_hits_7d"]
        and field_total <= thresholds["max_legacy_field_hits_7d"]
    )
