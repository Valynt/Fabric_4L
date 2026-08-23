from __future__ import annotations

"""Allowed service-local exception for Layer 3 service wrapper.

Owner: layer3-knowledge
Removal/migration target: 2026-09-30
Reason: Shared Layer 3 API metrics state.

This module intentionally owns process-local application metrics state so both the
monolith and decomposed route modules can access health metrics without importing
each other during pytest collection or application startup.
"""


import logging
import time
from types import SimpleNamespace
from typing import Any

try:
    import psutil  # type: ignore[import-untyped]
except ImportError:  # pragma: no cover - exercised only in minimal test envs

    class _PsutilFallback:
        @staticmethod
        def virtual_memory() -> SimpleNamespace:
            return SimpleNamespace(used=0, total=0)

        @staticmethod
        def cpu_percent(interval: Any = None) -> float:
            return 0.0

    psutil = _PsutilFallback()

from ..api.models import ServiceMetrics

logger = logging.getLogger(__name__)

_app_start_time = time.time()
_app_metrics: Any | None = None


def set_app_metrics(metrics: Any | None) -> None:
    """Set the global metrics instance for health check access."""
    global _app_metrics
    _app_metrics = metrics


def get_system_metrics() -> ServiceMetrics:
    """Collect system and application metrics from Prometheus."""
    uptime = time.time() - _app_start_time
    memory_info = psutil.virtual_memory()
    memory_usage_mb = memory_info.used / (1024 * 1024)
    cpu_percent = psutil.cpu_percent(interval=None)

    total_requests = 0
    total_errors = 0
    active_connections = 0
    error_rate_percent = 0.0
    metrics_instance = _app_metrics

    if metrics_instance is not None:
        try:
            registry = metrics_instance.config.registry
            prefix = metrics_instance.config.prefix

            for metric in registry.collect():
                if metric.name == f"{prefix}active_connections":
                    for sample in metric.samples:
                        if sample.labels.get("connection_type") == "total":
                            active_connections = int(sample.value)
                            break
                elif metric.name == f"{prefix}http_requests_total":
                    for sample in metric.samples:
                        total_requests += int(sample.value)
                elif metric.name == f"{prefix}errors_total":
                    for sample in metric.samples:
                        total_errors += int(sample.value)

            if total_requests > 0:
                error_rate_percent = round((total_errors / total_requests) * 100, 2)
        except Exception as exc:  # pragma: no cover - defensive metrics path
            logger.warning("Failed to extract Prometheus metrics: %s", exc)

    return ServiceMetrics(
        uptime_seconds=uptime,
        memory_usage_mb=round(memory_usage_mb, 2),
        cpu_percent=round(cpu_percent, 2),
        active_connections=active_connections,
        total_requests=total_requests,
        error_rate_percent=error_rate_percent,
    )
