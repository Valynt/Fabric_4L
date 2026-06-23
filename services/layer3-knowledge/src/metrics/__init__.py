"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Metrics package initialization.
"""

from .prometheus_metrics import (
    MetricsConfig,
    MetricsMiddleware,
    PrometheusMetrics,
    get_metrics,
    initialize_metrics,
    track_metrics,
)

__all__ = [
    "MetricsConfig",
    "PrometheusMetrics",
    "MetricsMiddleware",
    "get_metrics",
    "initialize_metrics",
    "track_metrics",
]
