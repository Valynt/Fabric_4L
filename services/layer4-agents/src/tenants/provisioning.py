"""Tenant provisioning workflow with async orchestration.

Orchestrates tenant creation steps with retry, rollback, and audit logging.
"""

from __future__ import annotations

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum, auto
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
from value_fabric.shared.models.typed_dict import TypedDictModel
from value_fabric.shared.secrets.infisical_client import TenantSecretManager

from .service import (
    get_tenant,
    update_tenant_status,
)


class ProvisioningState_to_dictResult(TypedDictModel):
    completed_at: Any
    completed_steps: Any
    current_step: Any
    error: Any
    max_retries: Any
    retry_count: Any
    retryable: Any
    started_at: Any
    status: Any
    step_results: Any
    tenant_id: Any

if TYPE_CHECKING:
    from value_fabric.shared.identity.models import TenantModel

logger = logging.getLogger(__name__)

# Constants
DEFAULT_ENVIRONMENTS = ["dev", "test", "staging", "prod"]
MAX_RETRY_DELAY_SECONDS = 60
DEFAULT_MAX_RETRIES = 3
TENANT_STATUS_ACTIVE = "active"
TENANT_STATUS_PENDING = "pending"


class ProvisioningStep(Enum):
    """Steps in the tenant provisioning workflow."""

    CREATE_TENANT_RECORD = auto()
    CREATE_INFISICAL_PATH = auto()
    SEED_DEFAULT_SECRETS = auto()
    UPDATE_TENANT_STATUS = auto()


class ProvisioningStatus(Enum):
    """Status of a provisioning workflow."""

    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    ROLLING_BACK = "rolling_back"
    ROLLED_BACK = "rolled_back"


@dataclass
class ProvisioningState:
    """State of a provisioning workflow execution."""

    tenant_id: UUID
    status: ProvisioningStatus
    current_step: ProvisioningStep | None = None
    completed_steps: list[ProvisioningStep] = field(default_factory=list)
    step_results: dict[str, Any] = field(default_factory=dict)
    error: str | None = None
    retryable: bool = False
    started_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    completed_at: datetime | None = None
    retry_count: int = 0
    max_retries: int = DEFAULT_MAX_RETRIES

    def to_dict(self) -> dict[str, Any]:
        """Convert state to dictionary for serialization."""
        return ProvisioningState_to_dictResult.model_validate({
            "tenant_id": str(self.tenant_id),
            "status": self.status.value,
            "current_step": self.current_step.name if self.current_step else None,
            "completed_steps": [s.name for s in self.completed_steps],
            "step_results": self.step_results,
            "error": self.error,
            "retryable": self.retryable,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "retry_count": self.retry_count,
            "max_retries": self.max_retries,
        })


class TenantProvisioningService:
    """Service for orchestrating tenant provisioning.

    Handles the multi-step workflow of creating tenant infrastructure
    with rollback support on failure.
    """

    def __init__(
        self,
        db: AsyncSession,
        secret_manager: TenantSecretManager | None = None,
    ) -> None:
        """Initialize provisioning service.

        Args:
            db: Database session
            secret_manager: Secret manager for Infisical operations
        """
        self.db = db
        self.secret_manager = secret_manager or TenantSecretManager()

    async def provision_tenant(
        self,
        tenant_id: UUID,
        force_retry: bool = False,
    ) -> ProvisioningState:
        """Provision a tenant through the complete workflow.

        Args:
            tenant_id: UUID of tenant to provision
            force_retry: Whether to force a retry of a failed provisioning

        Returns:
            Final provisioning state
        """
        # Get tenant
        tenant_model = await get_tenant(self.db, tenant_id)
        if not tenant_model:
            return ProvisioningState(
                tenant_id=tenant_id,
                status=ProvisioningStatus.FAILED,
                error="Tenant not found",
                retryable=False,
            )

        # Check if already completed
        if tenant_model.status == TENANT_STATUS_ACTIVE and not force_retry:
            return ProvisioningState(
                tenant_id=tenant_id,
                status=ProvisioningStatus.COMPLETED,
                completed_steps=[
                    ProvisioningStep.CREATE_TENANT_RECORD,
                    ProvisioningStep.CREATE_INFISICAL_PATH,
                    ProvisioningStep.SEED_DEFAULT_SECRETS,
                    ProvisioningStep.UPDATE_TENANT_STATUS,
                ],
                completed_at=datetime.now(UTC),
            )

        # Initialize state
        state = ProvisioningState(
            tenant_id=tenant_id,
            status=ProvisioningStatus.IN_PROGRESS,
        )

        try:
            # Step 1: Create Infisical path
            await self._step_create_infisical_path(state, tenant_model)

            # Step 2: Seed default secrets
            await self._step_seed_default_secrets(state, tenant_model)

            # Step 3: Update tenant status to active
            await self._step_update_tenant_status(state, tenant_model)

            # Mark complete
            state.status = ProvisioningStatus.COMPLETED
            state.completed_at = datetime.now(UTC)
            state.current_step = None

            await emit_audit_event(
                action=AuditAction.TENANT_PROVISIONED,
                outcome=AuditOutcome.SUCCESS,
                resource_type="tenant",
                resource_id=str(tenant_id),
                tenant_id=tenant_id,
                details={
                    "steps_completed": [s.name for s in state.completed_steps],
                    "duration_ms": self._get_duration_ms(state),
                },
            )

            logger.info("Tenant %s provisioned successfully", tenant_id)

        except Exception as e:
            logger.error("Provisioning failed for tenant %s: %s", tenant_id, e)
            state.status = ProvisioningStatus.FAILED
            state.error = "PROVISIONING_ERROR"
            state.retryable = self._is_retryable_error(e)

            await emit_audit_event(
                action=AuditAction.TENANT_PROVISIONING_FAILED,
                outcome=AuditOutcome.FAILURE,
                resource_type="tenant",
                resource_id=str(tenant_id),
                tenant_id=tenant_id,
                details={
                    "error_code": "PROVISIONING_ERROR",
                    "retryable": state.retryable,
                    "step": state.current_step.name if state.current_step else None,
                },
            )

            # Attempt rollback if retryable
            if state.retryable and state.retry_count < state.max_retries:
                state.retry_count += 1
                return await self._retry_provisioning(state, tenant_model)
            else:
                await self._rollback(state, tenant_model)

        return state

    async def _step_create_infisical_path(
        self,
        state: ProvisioningState,
        tenant_model: TenantModel,
    ) -> None:
        """Execute create Infisical path step."""
        state.current_step = ProvisioningStep.CREATE_INFISICAL_PATH

        # Skip if already completed
        if ProvisioningStep.CREATE_INFISICAL_PATH in state.completed_steps:
            logger.debug("Skipping CREATE_INFISICAL_PATH - already completed")
            return

        result = await self.secret_manager.create_tenant_secrets_path(
            str(tenant_model.id),
            environments=DEFAULT_ENVIRONMENTS,
        )

        # Check for failures
        failures = [env for env, data in result.items() if not data.get("success")]
        if failures:
            raise ProvisioningError(
                f"Failed to create Infisical paths in environments: {failures}"
            )

        state.step_results["create_infisical_path"] = result
        state.completed_steps.append(ProvisioningStep.CREATE_INFISICAL_PATH)

        await emit_audit_event(
            action=AuditAction.TENANT_PROVISIONING_STEP_COMPLETE,
            outcome=AuditOutcome.SUCCESS,
            resource_type="tenant",
            resource_id=str(tenant_model.id),
            tenant_id=tenant_model.id,
            details={"step": "CREATE_INFISICAL_PATH", "environments": list(result.keys())},
        )

    async def _step_seed_default_secrets(
        self,
        state: ProvisioningState,
        tenant_model: TenantModel,
    ) -> None:
        """Execute seed default secrets step."""
        state.current_step = ProvisioningStep.SEED_DEFAULT_SECRETS

        if ProvisioningStep.SEED_DEFAULT_SECRETS in state.completed_steps:
            logger.debug("Skipping SEED_DEFAULT_SECRETS - already completed")
            return

        # Seed in dev environment first
        result = await self.secret_manager.seed_default_tenant_secrets(
            str(tenant_model.id),
            tenant_model.name,
            environment="dev",
        )

        if not result.get("success"):
            raise ProvisioningError(
                f"Failed to seed default secrets: {result.get('error')}"
            )

        state.step_results["seed_default_secrets"] = result
        state.completed_steps.append(ProvisioningStep.SEED_DEFAULT_SECRETS)

        await emit_audit_event(
            action=AuditAction.TENANT_PROVISIONING_STEP_COMPLETE,
            outcome=AuditOutcome.SUCCESS,
            resource_type="tenant",
            resource_id=str(tenant_model.id),
            tenant_id=tenant_model.id,
            details={"step": "SEED_DEFAULT_SECRETS", "environment": "dev"},
        )

    async def _step_update_tenant_status(
        self,
        state: ProvisioningState,
        tenant_model: TenantModel,
    ) -> None:
        """Execute update tenant status step."""
        state.current_step = ProvisioningStep.UPDATE_TENANT_STATUS

        if ProvisioningStep.UPDATE_TENANT_STATUS in state.completed_steps:
            logger.debug("Skipping UPDATE_TENANT_STATUS - already completed")
            return

        # Update status to active
        updated = await update_tenant_status(
            self.db,
            tenant_model.id,
            TENANT_STATUS_ACTIVE,
            reason="Provisioning completed",
        )

        if not updated:
            raise ProvisioningError("Failed to update tenant status to active")

        state.step_results["update_tenant_status"] = {"status": "active"}
        state.completed_steps.append(ProvisioningStep.UPDATE_TENANT_STATUS)

        await emit_audit_event(
            action=AuditAction.TENANT_STATUS_CHANGED,
            outcome=AuditOutcome.SUCCESS,
            resource_type="tenant",
            resource_id=str(tenant_model.id),
            tenant_id=tenant_model.id,
            details={
                "old_status": tenant_model.status,
                "new_status": "active",
                "reason": "Provisioning completed",
            },
        )

    async def _retry_provisioning(
        self,
        state: ProvisioningState,
        tenant_model: TenantModel,
    ) -> ProvisioningState:
        """Retry provisioning with exponential backoff."""
        delay = min(2 ** state.retry_count, MAX_RETRY_DELAY_SECONDS)
        logger.info(
            "Retrying provisioning for tenant %s (attempt %d/%d) after %ds",
            tenant_model.id,
            state.retry_count,
            state.max_retries,
            delay,
        )

        await asyncio.sleep(delay)
        return await self.provision_tenant(tenant_model.id, force_retry=True)

    async def _rollback(
        self,
        state: ProvisioningState,
        tenant_model: TenantModel,
    ) -> None:
        """Rollback completed steps on failure."""
        logger.warning("Rolling back provisioning for tenant %s", tenant_model.id)
        state.status = ProvisioningStatus.ROLLING_BACK

        rollback_errors = []

        # Rollback in reverse order
        for step in reversed(state.completed_steps):
            try:
                await self._rollback_step(step, state, tenant_model)
            except Exception as e:
                logger.error("Rollback failed for step %s: %s", step.name, e)
                rollback_errors.append(f"{step.name}: ROLLBACK_ERROR")

        state.status = (
            ProvisioningStatus.ROLLED_BACK
            if not rollback_errors
            else ProvisioningStatus.FAILED
        )

        if rollback_errors:
            state.error = f"Rollback partially failed: {'; '.join(rollback_errors)}"

        await emit_audit_event(
            action=AuditAction.TENANT_PROVISIONING_ROLLBACK,
            outcome=AuditOutcome.FAILURE,
            resource_type="tenant",
            resource_id=str(tenant_model.id),
            tenant_id=tenant_model.id,
            details={
                "completed_steps": [s.name for s in state.completed_steps],
                "errors": rollback_errors,
            },
        )

    async def _rollback_step(
        self,
        step: ProvisioningStep,
        state: ProvisioningState,
        tenant_model: TenantModel,
    ) -> None:
        """Rollback a specific step."""
        if step == ProvisioningStep.CREATE_INFISICAL_PATH:
            # Delete Infisical paths
            await self.secret_manager.delete_tenant_secrets_path(
                str(tenant_model.id),
                environments=DEFAULT_ENVIRONMENTS,
            )
            logger.info("Rolled back Infisical paths for tenant %s", tenant_model.id)

        elif step == ProvisioningStep.SEED_DEFAULT_SECRETS:
            # Secrets are deleted with the path, nothing additional needed
            pass

        elif step == ProvisioningStep.UPDATE_TENANT_STATUS:
            # Update status back to pending
            await update_tenant_status(
                self.db,
                tenant_model.id,
                TENANT_STATUS_PENDING,
                reason="Provisioning failed - rollback",
            )
            logger.info("Rolled back tenant status for tenant %s", tenant_model.id)

    def _is_retryable_error(self, error: Exception) -> bool:
        """Determine if an error is retryable."""
        # Import httpx here to avoid dependency issues at module load time
        try:
            import httpx

            retryable_types = (
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.NetworkError,
            )
            if isinstance(error, retryable_types):
                return True
        except ImportError:
            pass  # httpx not available, fall through to string check

        # Also check for standard Python timeout/network errors
        retryable_std_types = (
            TimeoutError,
            ConnectionError,
        )
        return isinstance(error, retryable_std_types) or "timeout" in str(error).lower()

    def _get_duration_ms(self, state: ProvisioningState) -> int:
        """Calculate provisioning duration in milliseconds."""
        end_time = state.completed_at or datetime.now(UTC)
        return int((end_time - state.started_at).total_seconds() * 1000)


class ProvisioningError(Exception):
    """Error during tenant provisioning."""

    pass


# Convenience function for simple provisioning calls
async def provision_tenant(
    db: AsyncSession,
    tenant_id: UUID,
    secret_manager: TenantSecretManager | None = None,
) -> ProvisioningState:
    """Provision a tenant with a single function call.

    Args:
        db: Database session
        tenant_id: UUID of tenant to provision
        secret_manager: Optional secret manager

    Returns:
        Final provisioning state
    """
    service = TenantProvisioningService(db, secret_manager)
    return await service.provision_tenant(tenant_id)
