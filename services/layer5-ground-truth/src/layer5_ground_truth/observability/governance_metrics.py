"""
Governance Metrics Module.

Prometheus metrics for Layer 5 governance operations with safe labels.
"""

from prometheus_client import Counter, Histogram, Gauge
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

# Approval workflow metrics
APPROVAL_REQUESTS_TOTAL = Counter(
    "layer5_approval_requests_total",
    "Total number of approval requests",
    ["entity_type", "status"],
    registry=GOVERNANCE_REGISTRY,
)

APPROVAL_REQUESTS_PENDING = Gauge(
    "layer5_approval_requests_pending",
    "Number of pending approval requests",
    ["entity_type"],
    registry=GOVERNANCE_REGISTRY,
)

# Governance entity counts
GOVERNANCE_ENTITIES_TOTAL = Gauge(
    "layer5_governance_entities_total",
    "Total number of governance entities by type and status",
    ["entity_type", "status"],
    registry=GOVERNANCE_REGISTRY,
)

# Value realization metrics
VALUE_ENTRIES_TOTAL = Counter(
    "layer5_value_entries_total",
    "Total number of value realization entries",
    ["entry_type"],
    registry=GOVERNANCE_REGISTRY,
)

VALUE_UPDATES_TOTAL = Counter(
    "layer5_value_updates_total",
    "Total number of value updates",
    ["update_reason"],
    registry=GOVERNANCE_REGISTRY,
)

# Policy evaluation metrics
POLICY_EVALUATIONS_TOTAL = Counter(
    "layer5_policy_evaluations_total",
    "Total number of policy evaluations",
    ["policy_type", "compliance_status"],
    registry=GOVERNANCE_REGISTRY,
)

# Assumption metrics
ASSUMPTION_EVIDENCE_TOTAL = Counter(
    "layer5_assumption_evidence_total",
    "Total number of evidence items added to assumptions",
    ["evidence_type"],
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


def record_approval_request(entity_type: str, status: str):
    """Record an approval request."""
    APPROVAL_REQUESTS_TOTAL.labels(
        entity_type=entity_type,
        status=status,
    ).inc()


def update_pending_approvals(entity_type: str, count: int):
    """Update pending approval count."""
    APPROVAL_REQUESTS_PENDING.labels(entity_type=entity_type).set(count)


def update_entity_count(entity_type: str, status: str, count: int):
    """Update governance entity count."""
    GOVERNANCE_ENTITIES_TOTAL.labels(
        entity_type=entity_type,
        status=status,
    ).set(count)


def record_value_entry(entry_type: str):
    """Record a value entry creation."""
    VALUE_ENTRIES_TOTAL.labels(entry_type=entry_type).inc()


def record_value_update(update_reason: str):
    """Record a value update."""
    VALUE_UPDATES_TOTAL.labels(update_reason=update_reason).inc()


def record_policy_evaluation(policy_type: str, compliance_status: str):
    """Record a policy evaluation."""
    POLICY_EVALUATIONS_TOTAL.labels(
        policy_type=policy_type,
        compliance_status=compliance_status,
    ).inc()


def record_assumption_evidence(evidence_type: str):
    """Record assumption evidence addition."""
    ASSUMPTION_EVIDENCE_TOTAL.labels(evidence_type=evidence_type).inc()


def get_metrics() -> str:
    """Get all governance metrics in Prometheus format."""
    from prometheus_client import exposition

    return exposition.generate_latest(GOVERNANCE_REGISTRY)
