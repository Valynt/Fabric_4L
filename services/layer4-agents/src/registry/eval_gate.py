from __future__ import annotations

"""Evaluation gate checker for model promotions."""


from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .models import ModelVersion

_DEFAULT_PROMOTION_THRESHOLD = 0.85


async def check_eval_gate(
    db: AsyncSession,
    model_version_id: UUID,
    min_score: float | None = None,
) -> bool:
    """Check whether a model version passes the evaluation gate for promotion.

    If *min_score* is not provided, the threshold is read from the model's
    tenant settings under ``model_registry.promotion_threshold``.
    Falls back to 0.85 if no custom threshold is configured.
    """
    result = await db.execute(select(ModelVersion).where(ModelVersion.id == model_version_id))
    model = result.scalar_one_or_none()
    if model is None:
        return False

    threshold = min_score
    if threshold is None:
        # Attempt to read tenant settings
        from ..tenants.models.tenant import Tenant

        tenant_result = await db.execute(select(Tenant).where(Tenant.id == model.tenant_id))
        tenant = tenant_result.scalar_one_or_none()
        if tenant and tenant.settings:
            registry_settings = tenant.settings.get("model_registry", {})
            threshold = registry_settings.get("promotion_threshold")
        if threshold is None:
            threshold = _DEFAULT_PROMOTION_THRESHOLD

    if model.eval_score is None:
        return False

    return model.eval_score >= threshold
