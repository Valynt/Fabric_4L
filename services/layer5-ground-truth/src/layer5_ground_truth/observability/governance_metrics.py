"""
Governance Metrics Module.

Prometheus metrics for Layer 5 governance operations with safe labels.
"""

from prometheus_client import Counter, Histogram
from prometheus_client.registry import CollectorRegistry

# Use a custom registry to avoid conflicts with other layers
GOVERNANCE_REGISTRY = CollectorRegistry()

# Governance operation counters
GOVERNANCE_OPERATIONS_TOTAL = Counter(
    "layer5_governance_operations_total",
    "Total number of governance operations",
    ["operation", "entity_type", "status"],
    registry=GOVERNANCE_REGISTRY,
)

# Governance operation duration histogram
GOVERNANCE_OPERATION_DURATION_SECONDS = Histogram(
    "layer5_governance_operation_duration_seconds",
    "Duration of governance operations in seconds",
    ["operation", "entity_type"],
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
    registry=GOVERNANCE_REGISTRY,
)


def record_governance_operation(operation: str, entity_type: str, status: str):
    """Record a governance operation."""
    GOVERNANCE_OPERATIONS_TOTAL.labels(
        operation=operation,
        entity_type=entity_type,
        status=status,
    ).inc()


def record_governance_operation_duration(operation: str, entity_type: str, duration: float):
    """Record governance operation duration."""
    GOVERNANCE_OPERATION_DURATION_SECONDS.labels(
        operation=operation,
        entity_type=entity_type,
    ).observe(duration)


def get_metrics() -> str:
    """Get all governance metrics in Prometheus format."""
    from prometheus_client import exposition

    return exposition.generate_latest(GOVERNANCE_REGISTRY)
