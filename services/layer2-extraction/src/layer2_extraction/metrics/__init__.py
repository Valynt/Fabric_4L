"""Layer 2 metrics package."""

from typing import Any


class _MetricsCollector:
    """Placeholder metrics collector for Layer 2."""

    def get_metrics(self) -> dict[str, Any]:
        return {}

    def record_extraction(self, **kwargs: Any) -> None:
        pass

    def record_cache_hit(self, **kwargs: Any) -> None:
        pass

    def record_cache_miss(self, **kwargs: Any) -> None:
        pass


def get_metrics() -> _MetricsCollector:
    return _MetricsCollector()


__all__ = ["get_metrics"]
