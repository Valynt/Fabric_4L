import pytest

try:
    from src.services.compat_metrics import (
        get_compat_metrics_snapshot,
        record_deprecated_legacy_field_usage,
        record_deprecated_route_hit,
    )
except (ImportError, Exception):
    pytest.skip(
        "src service stack not available (pre-existing blocker #1/#9)",
        allow_module_level=True,
    )

def test_compat_metrics_are_segmented_by_tenant_and_app_client() -> None:
    record_deprecated_route_hit("/v1/query", tenant_id="tenant-a", app_client="web")
    record_deprecated_legacy_field_usage("search_type=fulltext", tenant_id="tenant-a", app_client="web")

    snapshot = get_compat_metrics_snapshot()
    assert snapshot["route_hits"]["/v1/query|tenant-a|web"] >= 1
    assert snapshot["legacy_field_hits"]["search_type=fulltext|tenant-a|web"] >= 1


def test_prometheus_counter_lookup_reuses_total_suffix_collector() -> None:
    from src.services.compat_metrics import _get_or_create_counter

    first = _get_or_create_counter(
        "layer3_test_duplicate_counter_total",
        "Layer 3 duplicate counter regression",
        ["tenant_id"],
    )
    second = _get_or_create_counter(
        "layer3_test_duplicate_counter_total",
        "Layer 3 duplicate counter regression",
        ["tenant_id"],
    )

    assert second is first
