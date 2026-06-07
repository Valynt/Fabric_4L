from src.services.compat_metrics import deprecation_ready_for_removal


def test_deprecation_ready_for_removal_when_no_legacy_usage() -> None:
    assert deprecation_ready_for_removal({"route_hits": {}, "legacy_field_hits": {}}) is True


def test_deprecation_not_ready_when_usage_exceeds_threshold() -> None:
    snapshot = {
        "route_hits": {"/v1/query|tenant-a|web": 1},
        "legacy_field_hits": {"search_type=fulltext|tenant-a|web": 0},
    }
    assert deprecation_ready_for_removal(snapshot) is False
