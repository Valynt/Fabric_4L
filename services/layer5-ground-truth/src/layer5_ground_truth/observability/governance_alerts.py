"""
Governance Alerts Module.

Alerting for Layer 5 governance operations including pending approvals,
deprecated use, compliance failures, and audit/queue errors.
"""

import logging
from abc import ABC, abstractmethod
from datetime import UTC, datetime
from enum import Enum
from typing import Any
from uuid import UUID

from prometheus_client import Counter

from .governance_metrics import GOVERNANCE_REGISTRY

logger = logging.getLogger(__name__)


class AlertSeverity(str, Enum):
    """Alert severity levels."""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"
    INFO = "info"


class AlertType(str, Enum):
    """Alert types."""
    PENDING_APPROVAL = "pending_approval"
    DEPRECATED_USE = "deprecated_use"
    COMPLIANCE_FAILURE = "compliance_failure"
    AUDIT_QUEUE_ERROR = "audit_queue_error"
    VALUE_ANOMALY = "value_anomaly"
    ASSUMPTION_EXPIRED = "assumption_expired"
    POLICY_VIOLATION = "policy_violation"


class GovernanceAlert:
    """Governance alert data structure."""

    def __init__(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        message: str,
        details: dict[str, Any] | None = None,
    ):
        self.alert_type = alert_type
        self.severity = severity
        self.tenant_id = tenant_id
        self.entity_type = entity_type
        self.entity_id = entity_id
        self.message = message
        self.details = details or {}
        self.created_at = datetime.now(UTC)

    def to_dict(self) -> dict[str, Any]:
        """Convert alert to dictionary."""
        return {
            "alert_type": self.alert_type.value,
            "severity": self.severity.value,
            "tenant_id": str(self.tenant_id),
            "entity_type": self.entity_type,
            "entity_id": str(self.entity_id),
            "message": self.message,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }


ALERT_HANDLER_FAILURES_TOTAL = Counter(
    "layer5_alert_handler_failures_total",
    "Total number of governance alert handler failures",
    ["handler", "alert_type", "severity"],
    registry=GOVERNANCE_REGISTRY,
)


class AlertHandler(ABC):
    """Base class for alert handlers."""

    @abstractmethod
    async def handle_alert(self, alert: GovernanceAlert) -> bool:
        """Handle an alert. Returns True if handled successfully."""
        ...


class LoggingAlertHandler(AlertHandler):
    """Log alerts to the application logger."""

    async def handle_alert(self, alert: GovernanceAlert) -> bool:
        """Log alert with appropriate severity level."""
        log_level = {
            AlertSeverity.CRITICAL: logging.CRITICAL,
            AlertSeverity.HIGH: logging.ERROR,
            AlertSeverity.MEDIUM: logging.WARNING,
            AlertSeverity.LOW: logging.INFO,
            AlertSeverity.INFO: logging.DEBUG,
        }.get(alert.severity, logging.INFO)

        logger.log(
            log_level,
            f"[{alert.alert_type.value.upper()}] {alert.message} | "
            f"Tenant: {alert.tenant_id} | Entity: {alert.entity_type}:{alert.entity_id} | "
            f"Details: {alert.details}",
        )
        return True


class GovernanceAlertManager:
    """Manager for governance alerts."""

    def __init__(self):
        self.handlers: list[AlertHandler] = [LoggingAlertHandler()]

    def add_handler(self, handler: AlertHandler):
        """Add an alert handler."""
        if not isinstance(handler, AlertHandler):
            raise TypeError(
                "handler must be an AlertHandler implementation; "
                f"got {type(handler).__name__}"
            )
        self.handlers.append(handler)

    async def emit_alert(self, alert: GovernanceAlert):
        """Emit an alert to all registered handlers."""
        for handler in self.handlers:
            try:
                await handler.handle_alert(alert)
            except Exception as exc:
                handler_name = type(handler).__name__
                ALERT_HANDLER_FAILURES_TOTAL.labels(
                    handler=handler_name,
                    alert_type=alert.alert_type.value,
                    severity=alert.severity.value,
                ).inc()
                logger.error(
                    "Alert handler failed",
                    extra={
                        "handler": handler_name,
                        "alert_type": alert.alert_type.value,
                        "alert_severity": alert.severity.value,
                        "tenant_id": str(alert.tenant_id),
                        "entity_type": alert.entity_type,
                        "entity_id": str(alert.entity_id),
                        "error": str(exc),  # ban-str-e-allow: structured-log
                    },
                )

    async def alert_pending_approval(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        entity_version: str,
        pending_duration_hours: float,
    ):
        """Alert for pending approval exceeding threshold."""
        alert = GovernanceAlert(
            alert_type=AlertType.PENDING_APPROVAL,
            severity=AlertSeverity.HIGH if pending_duration_hours > 48 else AlertSeverity.MEDIUM,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            message=f"Pending approval for {entity_type} version {entity_version} has been waiting for {pending_duration_hours:.1f} hours",
            details={
                "entity_version": entity_version,
                "pending_duration_hours": pending_duration_hours,
            },
        )
        await self.emit_alert(alert)

    async def alert_deprecated_use(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        entity_name: str,
        deprecation_date: datetime,
    ):
        """Alert for use of deprecated entity."""
        alert = GovernanceAlert(
            alert_type=AlertType.DEPRECATED_USE,
            severity=AlertSeverity.HIGH,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            message=f"Deprecated {entity_type} '{entity_name}' is being used",
            details={
                "entity_name": entity_name,
                "deprecation_date": deprecation_date.isoformat(),
            },
        )
        await self.emit_alert(alert)

    async def alert_compliance_failure(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        policy_type: str,
        policy_id: UUID,
        failure_reason: str,
    ):
        """Alert for policy compliance failure."""
        alert = GovernanceAlert(
            alert_type=AlertType.COMPLIANCE_FAILURE,
            severity=AlertSeverity.HIGH,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            message=f"Compliance failure for {entity_type} against policy {policy_type}",
            details={
                "policy_type": policy_type,
                "policy_id": str(policy_id),
                "failure_reason": failure_reason,
            },
        )
        await self.emit_alert(alert)

    async def alert_audit_queue_error(
        self,
        tenant_id: UUID,
        error_type: str,
        error_message: str,
        entity_id: UUID | None = None,
    ):
        """Alert for audit queue processing errors."""
        alert = GovernanceAlert(
            alert_type=AlertType.AUDIT_QUEUE_ERROR,
            severity=AlertSeverity.CRITICAL,
            tenant_id=tenant_id,
            entity_type="audit_queue",
            entity_id=entity_id or UUID("00000000-0000-0000-0000-000000000000"),
            message=f"Audit queue error: {error_type}",
            details={
                "error_type": error_type,
                "error_message": error_message,
            },
        )
        await self.emit_alert(alert)

    async def alert_value_anomaly(
        self,
        tenant_id: UUID,
        entry_id: UUID,
        entry_name: str,
        anomaly_type: str,
        expected_range: tuple[float, float],
        actual_value: float,
    ):
        """Alert for value realization anomalies."""
        alert = GovernanceAlert(
            alert_type=AlertType.VALUE_ANOMALY,
            severity=AlertSeverity.MEDIUM,
            tenant_id=tenant_id,
            entity_type="value_entry",
            entity_id=entry_id,
            message=f"Value anomaly detected for entry '{entry_name}': {anomaly_type}",
            details={
                "entry_name": entry_name,
                "anomaly_type": anomaly_type,
                "expected_range": expected_range,
                "actual_value": actual_value,
            },
        )
        await self.emit_alert(alert)

    async def alert_assumption_expired(
        self,
        tenant_id: UUID,
        assumption_id: UUID,
        assumption_name: str,
        expiry_date: datetime,
    ):
        """Alert for expired assumptions."""
        alert = GovernanceAlert(
            alert_type=AlertType.ASSUMPTION_EXPIRED,
            severity=AlertSeverity.MEDIUM,
            tenant_id=tenant_id,
            entity_type="assumption",
            entity_id=assumption_id,
            message=f"Assumption '{assumption_name}' has expired",
            details={
                "assumption_name": assumption_name,
                "expiry_date": expiry_date.isoformat(),
            },
        )
        await self.emit_alert(alert)

    async def alert_policy_violation(
        self,
        tenant_id: UUID,
        entity_type: str,
        entity_id: UUID,
        policy_id: UUID,
        policy_name: str,
        violation_type: str,
    ):
        """Alert for policy violations."""
        alert = GovernanceAlert(
            alert_type=AlertType.POLICY_VIOLATION,
            severity=AlertSeverity.HIGH,
            tenant_id=tenant_id,
            entity_type=entity_type,
            entity_id=entity_id,
            message=f"Policy violation: {policy_name} - {violation_type}",
            details={
                "policy_id": str(policy_id),
                "policy_name": policy_name,
                "violation_type": violation_type,
            },
        )
        await self.emit_alert(alert)


# Global alert manager instance
alert_manager = GovernanceAlertManager()
