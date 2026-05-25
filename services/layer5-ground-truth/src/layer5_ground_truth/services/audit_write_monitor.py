"""Runtime counters for audit write failures."""

from collections.abc import Mapping

_audit_write_stats = {"failures_total": 0}


def record_audit_write_failure() -> None:
    _audit_write_stats["failures_total"] += 1
    try:
        from metrics.prometheus_metrics import get_metrics

        metrics = get_metrics()
        if metrics is not None:
            metrics.increment_audit_write_failures()
    except Exception:
        return


def get_audit_write_stats() -> Mapping[str, int]:
    return dict(_audit_write_stats)
