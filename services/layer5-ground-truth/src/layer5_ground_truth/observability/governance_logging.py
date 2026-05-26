"""
Governance Structured Logging Module.

Structured logging for all Layer 5 governance actions with required fields.
"""

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from .structured_logging import get_logger

logger = get_logger(__name__)


class GovernanceLogger:
    """Structured logger for governance operations."""

    @staticmethod
    def log_governance_action(
        action: str,
        entity_type: str,
        entity_id: UUID,
        tenant_id: UUID,
        user_id: str,
        status: str,
        details: dict[str, Any] | None = None,
    ):
        """Log a governance action with required fields."""
        log_data = {
            "event": "governance_action",
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id),
            "tenant_id": str(tenant_id),
            "user_id": user_id,
            "status": status,
            "timestamp": datetime.now(UTC).isoformat(),
            "details": details or {},
        }
        logger.info("governance_action", **log_data)

    @staticmethod
    def log_formula_created(
        formula_id: UUID,
        tenant_id: UUID,
        user_id: str,
        name: str,
        slug: str,
        formula_type: str,
    ):
        """Log formula creation."""
        GovernanceLogger.log_governance_action(
            action="formula_created",
            entity_type="formula",
            entity_id=formula_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status="success",
            details={
                "name": name,
                "slug": slug,
                "formula_type": formula_type,
            },
        )

    @staticmethod
    def log_formula_version_created(
        formula_id: UUID,
        version: str,
        tenant_id: UUID,
        user_id: str,
    ):
        """Log formula version creation."""
        GovernanceLogger.log_governance_action(
            action="formula_version_created",
            entity_type="formula_version",
            entity_id=formula_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status="success",
            details={"version": version},
        )

    @staticmethod
    def log_formula_approved(
        formula_id: UUID,
        version: str,
        tenant_id: UUID,
        approver: str,
    ):
        """Log formula approval."""
        GovernanceLogger.log_governance_action(
            action="formula_approved",
            entity_type="formula",
            entity_id=formula_id,
            tenant_id=tenant_id,
            user_id=approver,
            status="success",
            details={"version": version},
        )

    @staticmethod
    def log_formula_deprecated(
        formula_id: UUID,
        tenant_id: UUID,
        deprecator: str,
        reason: str,
    ):
        """Log formula deprecation."""
        GovernanceLogger.log_governance_action(
            action="formula_deprecated",
            entity_type="formula",
            entity_id=formula_id,
            tenant_id=tenant_id,
            user_id=deprecator,
            status="success",
            details={"reason": reason},
        )

    @staticmethod
    def log_benchmark_created(
        benchmark_id: UUID,
        tenant_id: UUID,
        user_id: str,
        name: str,
        slug: str,
        benchmark_type: str,
    ):
        """Log benchmark creation."""
        GovernanceLogger.log_governance_action(
            action="benchmark_created",
            entity_type="benchmark",
            entity_id=benchmark_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status="success",
            details={
                "name": name,
                "slug": slug,
                "benchmark_type": benchmark_type,
            },
        )

    @staticmethod
    def log_benchmark_approved(
        benchmark_id: UUID,
        version: str,
        tenant_id: UUID,
        approver: str,
    ):
        """Log benchmark approval."""
        GovernanceLogger.log_governance_action(
            action="benchmark_approved",
            entity_type="benchmark",
            entity_id=benchmark_id,
            tenant_id=tenant_id,
            user_id=approver,
            status="success",
            details={"version": version},
        )

    @staticmethod
    def log_policy_created(
        policy_id: UUID,
        tenant_id: UUID,
        user_id: str,
        name: str,
        slug: str,
        policy_type: str,
    ):
        """Log policy creation."""
        GovernanceLogger.log_governance_action(
            action="policy_created",
            entity_type="policy",
            entity_id=policy_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status="success",
            details={
                "name": name,
                "slug": slug,
                "policy_type": policy_type,
            },
        )

    @staticmethod
    def log_policy_evaluated(
        policy_id: UUID,
        entity_id: UUID,
        entity_type: str,
        tenant_id: UUID,
        evaluator: str,
        is_compliant: bool,
    ):
        """Log policy evaluation."""
        GovernanceLogger.log_governance_action(
            action="policy_evaluated",
            entity_type="policy",
            entity_id=policy_id,
            tenant_id=tenant_id,
            user_id=evaluator,
            status="success",
            details={
                "target_entity_id": str(entity_id),
                "target_entity_type": entity_type,
                "is_compliant": is_compliant,
            },
        )

    @staticmethod
    def log_assumption_created(
        assumption_id: UUID,
        tenant_id: UUID,
        user_id: str,
        name: str,
        slug: str,
        assumption_type: str,
        impact_level: str,
    ):
        """Log assumption creation."""
        GovernanceLogger.log_governance_action(
            action="assumption_created",
            entity_type="assumption",
            entity_id=assumption_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status="success",
            details={
                "name": name,
                "slug": slug,
                "assumption_type": assumption_type,
                "impact_level": impact_level,
            },
        )

    @staticmethod
    def log_assumption_evidence_added(
        assumption_id: UUID,
        tenant_id: UUID,
        user_id: str,
        evidence_type: str,
    ):
        """Log assumption evidence addition."""
        GovernanceLogger.log_governance_action(
            action="assumption_evidence_added",
            entity_type="assumption",
            entity_id=assumption_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status="success",
            details={"evidence_type": evidence_type},
        )

    @staticmethod
    def log_assumption_approved(
        assumption_id: UUID,
        tenant_id: UUID,
        approver: str,
    ):
        """Log assumption approval."""
        GovernanceLogger.log_governance_action(
            action="assumption_approved",
            entity_type="assumption",
            entity_id=assumption_id,
            tenant_id=tenant_id,
            user_id=approver,
            status="success",
        )

    @staticmethod
    def log_value_entry_created(
        entry_id: UUID,
        tenant_id: UUID,
        user_id: str,
        entry_type: str,
        entry_name: str,
        current_value: float,
    ):
        """Log value entry creation."""
        GovernanceLogger.log_governance_action(
            action="value_entry_created",
            entity_type="value_entry",
            entity_id=entry_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status="success",
            details={
                "entry_type": entry_type,
                "entry_name": entry_name,
                "current_value": current_value,
            },
        )

    @staticmethod
    def log_value_update_added(
        entry_id: UUID,
        tenant_id: UUID,
        user_id: str,
        old_value: float,
        new_value: float,
        update_reason: str,
    ):
        """Log value update addition."""
        GovernanceLogger.log_governance_action(
            action="value_update_added",
            entity_type="value_entry",
            entity_id=entry_id,
            tenant_id=tenant_id,
            user_id=user_id,
            status="success",
            details={
                "old_value": old_value,
                "new_value": new_value,
                "value_change": new_value - old_value,
                "update_reason": update_reason,
            },
        )

    @staticmethod
    def log_approval_requested(
        approval_id: UUID,
        entity_type: str,
        entity_id: UUID,
        entity_version: str,
        tenant_id: UUID,
        requester: str,
    ):
        """Log approval request."""
        GovernanceLogger.log_governance_action(
            action="approval_requested",
            entity_type="approval",
            entity_id=approval_id,
            tenant_id=tenant_id,
            user_id=requester,
            status="success",
            details={
                "target_entity_type": entity_type,
                "target_entity_id": str(entity_id),
                "target_entity_version": entity_version,
            },
        )

    @staticmethod
    def log_approval_approved(
        approval_id: UUID,
        tenant_id: UUID,
        approver: str,
    ):
        """Log approval approval."""
        GovernanceLogger.log_governance_action(
            action="approval_approved",
            entity_type="approval",
            entity_id=approval_id,
            tenant_id=tenant_id,
            user_id=approver,
            status="success",
        )

    @staticmethod
    def log_approval_rejected(
        approval_id: UUID,
        tenant_id: UUID,
        reviewer: str,
    ):
        """Log approval rejection."""
        GovernanceLogger.log_governance_action(
            action="approval_rejected",
            entity_type="approval",
            entity_id=approval_id,
            tenant_id=tenant_id,
            user_id=reviewer,
            status="success",
        )

    @staticmethod
    def log_governance_error(
        action: str,
        entity_type: str,
        entity_id: UUID | None,
        tenant_id: UUID,
        user_id: str,
        error_type: str,
        error_message: str,
    ):
        """Log a governance error."""
        log_data = {
            "event": "governance_error",
            "action": action,
            "entity_type": entity_type,
            "entity_id": str(entity_id) if entity_id else None,
            "tenant_id": str(tenant_id),
            "user_id": user_id,
            "error_type": error_type,
            "error_message": error_message,
            "timestamp": datetime.now(UTC).isoformat(),
        }
        logger.error("Governance error: %s", log_data)
