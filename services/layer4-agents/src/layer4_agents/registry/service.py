from __future__ import annotations

"""Model Registry service layer."""


import logging
import os
from typing import Any
from uuid import UUID

try:
    from value_fabric.shared.audit import AuditAction, AuditOutcome, emit_audit_event
except ImportError as e:
    raise RuntimeError(
        "shared.audit package is required for audit functionality. "
        "Install the shared package or set PYTHONPATH to include packages/shared/src/value_fabric/shared"
    ) from e
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .eval_gate import check_eval_gate
from .models import ModelPromotionLog, ModelVersion

logger = logging.getLogger(__name__)

FALLBACK_LLM_MODEL: str = os.getenv("LLM_MODEL", "gpt-4o")
"""Default LLM model when registry lookup fails or is unavailable."""
ALLOWED_MODEL_STAGES = {"dev", "staging", "production", "deprecated"}


class PromotionError(Exception):
    """Raised when a model promotion is not allowed."""

    pass


class ModelRegistryService:
    """Business logic for registering and promoting models."""

    # -----------------------------------------------------------------------
    # CRUD
    # -----------------------------------------------------------------------

    @staticmethod
    async def register_model(
        db: AsyncSession,
        tenant_id: UUID,
        provider: str,
        model_name: str,
        model_version: str,
        stage: str = "dev",
        config: dict[str, Any] | None = None,
        eval_score: float | None = None,
        eval_run_id: str | None = None,
    ) -> ModelVersion:
        """Register a new model version."""
        model = ModelVersion(
            tenant_id=tenant_id,
            provider=provider,
            model_name=model_name,
            model_version=model_version,
            stage=stage,
            config=config or {},
            eval_score=eval_score,
            eval_run_id=eval_run_id,
        )
        db.add(model)
        await db.flush()

        emit_audit_event(
            AuditAction.MODEL_REGISTERED,
            AuditOutcome.SUCCESS,
            resource_type="ModelVersion",
            resource_id=str(model.id),
            tenant_id=tenant_id,
            details={
                "provider": provider,
                "model_name": model_name,
                "model_version": model_version,
                "stage": stage,
            },
        )
        logger.info(
            "Registered model %s/%s (%s) for tenant %s",
            provider,
            model_name,
            model_version,
            tenant_id,
        )
        return model

    @staticmethod
    async def list_models(
        db: AsyncSession,
        tenant_id: UUID,
        stage: str | None = None,
    ) -> list[ModelVersion]:
        """List model versions for a tenant, optionally filtered by stage."""
        q = select(ModelVersion).where(ModelVersion.tenant_id == tenant_id)
        if stage:
            q = q.where(ModelVersion.stage == stage)
        q = q.order_by(ModelVersion.created_at.desc())
        result = await db.execute(q)
        return list(result.scalars().all())

    @staticmethod
    async def get_active_production_model(
        db: AsyncSession,
        tenant_id: UUID,
        provider: str,
    ) -> ModelVersion | None:
        """Return the latest production model for a tenant/provider."""
        result = await db.execute(
            select(ModelVersion)
            .where(
                ModelVersion.tenant_id == tenant_id,
                ModelVersion.provider == provider,
                ModelVersion.stage == "production",
            )
            .order_by(ModelVersion.created_at.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    @staticmethod
    async def get_model(
        db: AsyncSession,
        model_version_id: UUID,
    ) -> ModelVersion | None:
        """Fetch a single model version by ID."""
        result = await db.execute(select(ModelVersion).where(ModelVersion.id == model_version_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def get_promotion_history(
        db: AsyncSession,
        model_version_id: UUID,
    ) -> list[ModelPromotionLog]:
        """Return the promotion audit trail for a model version."""
        result = await db.execute(
            select(ModelPromotionLog)
            .where(ModelPromotionLog.model_version_id == model_version_id)
            .order_by(ModelPromotionLog.created_at.desc())
        )
        return list(result.scalars().all())

    # -----------------------------------------------------------------------
    # Promotion
    # -----------------------------------------------------------------------

    @staticmethod
    async def promote_model(
        db: AsyncSession,
        model_version_id: UUID,
        to_stage: str,
        promoted_by: UUID | None = None,
        reason: str | None = None,
    ) -> ModelVersion:
        """Promote a model version to a new stage.

        Gates:
        - dev → staging: always allowed
        - staging → production: requires eval_score >= threshold
        - production → deprecated: always allowed
        """
        result = await db.execute(select(ModelVersion).where(ModelVersion.id == model_version_id))
        model = result.scalar_one_or_none()
        if model is None:
            raise PromotionError(f"Model version {model_version_id} not found")

        from_stage = model.stage
        if from_stage not in ALLOWED_MODEL_STAGES or to_stage not in ALLOWED_MODEL_STAGES:
            raise PromotionError(
                f"Invalid stage transition {from_stage!r} -> {to_stage!r}. "
                f"Allowed states: {sorted(ALLOWED_MODEL_STAGES)}"
            )

        if from_stage == to_stage:
            raise PromotionError(f"Model is already in stage '{to_stage}'")

        allowed_transitions: dict[str, set[str]] = {
            "dev": {"staging"},
            "staging": {"production", "deprecated"},
            "production": {"deprecated"},
            "deprecated": set(),
        }
        if to_stage not in allowed_transitions[from_stage]:
            raise PromotionError(
                f"Forbidden stage transition {from_stage!r} -> {to_stage!r}. "
                f"Allowed targets: {sorted(allowed_transitions[from_stage])}"
            )

        # Enforce promotion gates
        eval_passed = None
        if from_stage == "staging" and to_stage == "production":
            eval_passed = await check_eval_gate(db, model_version_id)
            if not eval_passed:
                raise PromotionError("Evaluation gate failed: eval_score below promotion threshold")

        # Update model
        model.stage = to_stage
        model.promoted_by = promoted_by

        # Log promotion
        log_entry = ModelPromotionLog(
            model_version_id=model_version_id,
            from_stage=from_stage,
            to_stage=to_stage,
            promoted_by=promoted_by,
            reason=reason,
            eval_score=model.eval_score,
            eval_gate_passed=eval_passed if eval_passed is not None else True,
        )
        db.add(log_entry)
        await db.flush()

        # Audit event
        action = (
            AuditAction.MODEL_DEPRECATED if to_stage == "deprecated" else AuditAction.MODEL_PROMOTED
        )
        emit_audit_event(
            action,
            AuditOutcome.SUCCESS,
            resource_type="ModelVersion",
            resource_id=str(model.id),
            tenant_id=model.tenant_id,
            details={
                "from_stage": from_stage,
                "to_stage": to_stage,
                "reason": reason,
                "eval_score": model.eval_score,
            },
        )
        logger.info(
            "Promoted model %s from %s to %s",
            model_version_id,
            from_stage,
            to_stage,
        )
        return model


async def resolve_llm_model(
    db: AsyncSession,
    tenant_id: UUID,
    provider: str = "openai",
) -> str:
    """Resolve the active production model name for a tenant/provider.

    Falls back to ``os.getenv('LLM_MODEL', 'gpt-4o')`` if no production model
    is registered.
    """
    model = await ModelRegistryService.get_active_production_model(db, tenant_id, provider)
    if model:
        return model.model_name
    return FALLBACK_LLM_MODEL
