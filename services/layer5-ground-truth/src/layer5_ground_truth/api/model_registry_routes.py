from value_fabric.shared.error_handling.exceptions import (
    ConflictError,
    NotFoundError,
    ValidationError,
)

"""
FastAPI router for Model Registry API.

Endpoints:
  POST   /models                       — Register a new ModelVersion
  GET    /models                       — List ModelVersions (paginated)
  GET    /models/{id}                  — Get a ModelVersion
  POST   /models/{id}/deprecate        — Deprecate a model version
  POST   /models/{id}/promote         — Promote to environment
  GET    /models/{id}/deployments     — Get deployments for a model
  GET    /models/{id}/evaluations     — Get evaluations for a model
  GET    /deployments                 — List all deployments
  POST   /deployments/{id}/rollback   — Rollback a deployment
  POST   /evaluations                  — Record a model evaluation
  GET    /evaluations                  — List evaluations

All endpoints are organization-scoped for multi-tenancy.
"""

import logging
from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Query, status
from sqlalchemy import and_, desc, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from ..database import get_db_from_context
from ..models.model_registry import (
    DeploymentEnvironment,
    DeploymentStatus,
    ModelDeployment,
    ModelEvaluation,
    ModelVersion,
)
from .auth import TokenClaims, get_current_user
from .schemas import (
    ModelDeploymentListResponse,
    ModelDeploymentResponse,
    ModelEvaluationCreate,
    ModelEvaluationListResponse,
    ModelEvaluationResponse,
    ModelVersionCreate,
    ModelVersionListResponse,
    ModelVersionResponse,
    ModelVersionSummary,
    PromoteModelRequest,
    PromoteModelResponse,
    RollbackModelRequest,
    RollbackModelResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1", tags=["model-registry"])


# ============================================================================
# Model Version Endpoints
# ============================================================================


@router.post(
    "/models",
    response_model=ModelVersionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register a new ModelVersion",
    description="Register a new LLM model version with cost tracking and capabilities.",
)
async def create_model_version(
    payload: ModelVersionCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ModelVersionResponse:
    """Register a new model version."""
    tenant_id = caller.tenant_id

    # Check for duplicate (org + provider + name + version)
    existing = await db.execute(
        select(ModelVersion).where(
            and_(
                ModelVersion.tenant_id == tenant_id,
                ModelVersion.provider == payload.provider.value,
                ModelVersion.name == payload.name,
                ModelVersion.version == payload.version,
                ModelVersion.deprecated_at.is_(None),
            )
        )
    )
    if existing.scalar_one_or_none():
        raise ConflictError(message=f"Model version already exists: {payload.provider.value}/{payload.name}@{payload.version}")

    # If setting as default, clear other defaults for this provider
    if payload.is_default:
        await db.execute(
            update(ModelVersion)
            .where(
                and_(
                    ModelVersion.tenant_id == tenant_id,
                    ModelVersion.provider == payload.provider.value,
                    ModelVersion.is_default.is_(True),
                )
            )
            .values(is_default=False)
        )

    model = ModelVersion(
        tenant_id=tenant_id,
        name=payload.name,
        provider=payload.provider.value,
        version=payload.version,
        model_identifier=payload.model_identifier,
        capabilities=[c.value for c in payload.capabilities],
        context_window=payload.context_window,
        max_output_tokens=payload.max_output_tokens,
        cost_per_1k_input=payload.cost_per_1k_input,
        cost_per_1k_output=payload.cost_per_1k_output,
        cost_per_1k_cached=payload.cost_per_1k_cached,
        description=payload.description,
        extra_metadata=payload.extra_metadata,
        is_default=payload.is_default,
        created_by=caller.user_id or caller.email,
    )

    db.add(model)
    await db.flush()

    logger.info(
        "Registered model version: %s/%s@%s (org=%s)",
        model.provider,
        model.name,
        model.version,
        tenant_id,
    )

    return ModelVersionResponse.model_validate(model)


@router.get(
    "/models",
    response_model=ModelVersionListResponse,
    summary="List ModelVersions",
    description="Paginated, filterable list of model versions for the organization.",
)
async def list_model_versions(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    provider: str | None = Query(default=None, description="Filter by provider"),
    is_active: bool | None = Query(default=None, description="Filter by active status"),
    is_default: bool | None = Query(default=None, description="Filter by default flag"),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ModelVersionListResponse:
    """List model versions with filtering."""
    tenant_id = caller.tenant_id

    query = select(ModelVersion).where(
        and_(
            ModelVersion.tenant_id == tenant_id,
            ModelVersion.deprecated_at.is_(None),
        )
    )

    if provider:
        query = query.where(ModelVersion.provider == provider)
    if is_active is not None:
        query = query.where(ModelVersion.is_active == is_active)
    if is_default is not None:
        query = query.where(ModelVersion.is_default == is_default)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(ModelVersion.created_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    items = result.scalars().all()

    summaries = [ModelVersionSummary.model_validate(item) for item in items]

    return ModelVersionListResponse(
        items=summaries,
        total=total,
        limit=limit,
        offset=offset,
        has_more=(offset + limit) < total,
    )


@router.get(
    "/models/{model_id}",
    response_model=ModelVersionResponse,
    summary="Get a ModelVersion",
    description="Retrieve a single ModelVersion with full details.",
)
async def get_model_version(
    model_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ModelVersionResponse:
    """Get a model version by ID."""
    tenant_id = caller.tenant_id

    result = await db.execute(
        select(ModelVersion).where(
            and_(
                ModelVersion.id == model_id,
                ModelVersion.tenant_id == tenant_id,
            )
        )
    )
    model = result.scalar_one_or_none()

    if not model:
        raise NotFoundError(message = str(f"ModelVersion {model_id} not found"))

    return ModelVersionResponse.model_validate(model)


@router.post(
    "/models/{model_id}/deprecate",
    response_model=ModelVersionResponse,
    summary="Deprecate a ModelVersion",
    description="Mark a model version as deprecated (soft delete).",
)
async def deprecate_model_version(
    model_id: UUID,
    reason: str | None = Query(default=None, description="Deprecation reason"),
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ModelVersionResponse:
    """Deprecate a model version."""
    tenant_id = caller.tenant_id

    result = await db.execute(
        select(ModelVersion).where(
            and_(
                ModelVersion.id == model_id,
                ModelVersion.tenant_id == tenant_id,
            )
        )
    )
    model = result.scalar_one_or_none()

    if not model:
        raise NotFoundError(message = str(f"ModelVersion {model_id} not found"))

    if model.deprecated_at:
        raise ValidationError(message = str(f"ModelVersion {model_id} is already deprecated"))

    model.deprecated_at = datetime.now(UTC)
    model.deprecation_reason = reason or "Manually deprecated"
    model.is_active = False

    logger.info(
        "Deprecated model version: %s/%s@%s (org=%s, reason=%s)",
        model.provider,
        model.name,
        model.version,
        tenant_id,
        model.deprecation_reason,
    )

    return ModelVersionResponse.model_validate(model)


@router.post(
    "/models/{model_id}/set-default",
    response_model=ModelVersionResponse,
    summary="Set as default model",
    description="Set this model version as the default for its provider.",
)
async def set_default_model_version(
    model_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ModelVersionResponse:
    """Set a model version as default for its provider."""
    tenant_id = caller.tenant_id

    # Get the target model
    result = await db.execute(
        select(ModelVersion).where(
            and_(
                ModelVersion.id == model_id,
                ModelVersion.tenant_id == tenant_id,
            )
        )
    )
    model = result.scalar_one_or_none()

    if not model:
        raise NotFoundError(message = str(f"ModelVersion {model_id} not found"))

    if model.deprecated_at:
        raise ValidationError(message = "Cannot set deprecated model as default")

    # Clear other defaults for this provider
    await db.execute(
        update(ModelVersion)
        .where(
            and_(
                ModelVersion.tenant_id == tenant_id,
                ModelVersion.provider == model.provider,
                ModelVersion.is_default.is_(True),
                ModelVersion.id != model_id,
            )
        )
        .values(is_default=False)
    )

    model.is_default = True
    await db.flush()

    logger.info(
        "Set default model: %s/%s@%s (org=%s)",
        model.provider,
        model.name,
        model.version,
        tenant_id,
    )

    return ModelVersionResponse.model_validate(model)


# ============================================================================
# Model Deployment Endpoints
# ============================================================================


@router.post(
    "/models/{model_id}/promote",
    response_model=PromoteModelResponse,
    summary="Promote model to environment",
    description="Deploy or update a model version in a specific environment.",
)
async def promote_model(
    model_id: UUID,
    payload: PromoteModelRequest,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> PromoteModelResponse:
    """Promote a model version to an environment."""
    tenant_id = caller.tenant_id

    # Verify model exists and is active
    model_result = await db.execute(
        select(ModelVersion).where(
            and_(
                ModelVersion.id == model_id,
                ModelVersion.tenant_id == tenant_id,
                ModelVersion.deprecated_at.is_(None),
            )
        )
    )
    model = model_result.scalar_one_or_none()

    if not model:
        raise NotFoundError(message = str(f"ModelVersion {model_id} not found or deprecated"))

    if not model.is_active:
        raise ValidationError(message = "Cannot deploy inactive model version")

    # Check for existing deployment
    existing_result = await db.execute(
        select(ModelDeployment).where(
            and_(
                ModelDeployment.model_version_id == model_id,
                ModelDeployment.tenant_id == tenant_id,
                ModelDeployment.environment == payload.environment.value,
            )
        )
    )
    existing = existing_result.scalar_one_or_none()

    if existing:
        # Update existing deployment
        existing.traffic_percentage = payload.traffic_percentage
        existing.is_default_for_env = payload.make_default
        existing.status = DeploymentStatus.ACTIVE.value
        existing.deployed_at = datetime.now(UTC)
        existing.deployed_by = caller.user_id or caller.email
        deployment = existing
    else:
        # Create new deployment
        deployment = ModelDeployment(
            tenant_id=tenant_id,
            model_version_id=model_id,
            environment=payload.environment.value,
            status=DeploymentStatus.ACTIVE.value,
            traffic_percentage=payload.traffic_percentage,
            is_default_for_env=payload.make_default,
            deployed_at=datetime.now(UTC),
            deployed_by=caller.user_id or caller.email,
        )
        db.add(deployment)
        await db.refresh(deployment)

    # If making default, clear other defaults for this environment
    if payload.make_default:
        await db.execute(
            update(ModelDeployment)
            .where(
                and_(
                    ModelDeployment.tenant_id == tenant_id,
                    ModelDeployment.environment == payload.environment.value,
                    ModelDeployment.is_default_for_env.is_(True),
                    ModelDeployment.model_version_id != model_id,
                )
            )
            .values(is_default_for_env=False)
        )

    logger.info(
        "Promoted model %s/%s@%s to %s (traffic=%d%%)",
        model.provider,
        model.name,
        model.version,
        payload.environment.value,
        payload.traffic_percentage,
    )

    return PromoteModelResponse(
        deployment_id=deployment.id,
        model_version_id=model_id,
        environment=payload.environment.value,
        status=DeploymentStatus.ACTIVE.value,
        traffic_percentage=payload.traffic_percentage,
        is_default_for_env=payload.make_default,
        deployed_at=deployment.deployed_at,
        message=f"Successfully promoted {model.name}@{model.version} to {payload.environment.value}",
    )


@router.get(
    "/models/{model_id}/deployments",
    response_model=ModelDeploymentListResponse,
    summary="Get model deployments",
    description="Get all deployments for a specific model version.",
)
async def get_model_deployments(
    model_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ModelDeploymentListResponse:
    """Get deployments for a model version."""
    tenant_id = caller.tenant_id

    result = await db.execute(
        select(ModelDeployment).where(
            and_(
                ModelDeployment.model_version_id == model_id,
                ModelDeployment.tenant_id == tenant_id,
            )
        )
    )
    deployments = result.scalars().all()

    return ModelDeploymentListResponse(
        items=[ModelDeploymentResponse.model_validate(d) for d in deployments],
        total=len(deployments),
    )


@router.get(
    "/deployments",
    response_model=ModelDeploymentListResponse,
    summary="List all deployments",
    description="List all model deployments across all versions.",
)
async def list_deployments(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    environment: DeploymentEnvironment | None = Query(default=None),
    status: str | None = Query(default=None),
) -> ModelDeploymentListResponse:
    """List all deployments with optional filtering."""
    tenant_id = caller.tenant_id

    query = select(ModelDeployment).where(
        ModelDeployment.tenant_id == tenant_id
    )

    if environment:
        query = query.where(ModelDeployment.environment == environment.value)
    if status:
        query = query.where(ModelDeployment.status == status)

    result = await db.execute(query)
    deployments = result.scalars().all()

    return ModelDeploymentListResponse(
        items=[ModelDeploymentResponse.model_validate(d) for d in deployments],
        total=len(deployments),
    )


@router.post(
    "/deployments/{deployment_id}/rollback",
    response_model=RollbackModelResponse,
    summary="Rollback a deployment",
    description="Rollback a deployment to previous state.",
)
async def rollback_deployment(
    deployment_id: UUID,
    payload: RollbackModelRequest,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> RollbackModelResponse:
    """Rollback a deployment."""
    tenant_id = caller.tenant_id

    result = await db.execute(
        select(ModelDeployment).where(
            and_(
                ModelDeployment.id == deployment_id,
                ModelDeployment.tenant_id == tenant_id,
            )
        )
    )
    deployment = result.scalar_one_or_none()

    if not deployment:
        raise NotFoundError(message = str(f"Deployment {deployment_id} not found"))

    previous_status = deployment.status

    deployment.status = DeploymentStatus.ROLLED_BACK.value
    deployment.rolled_back_at = datetime.now(UTC)
    deployment.rolled_back_by = caller.user_id or caller.email
    deployment.rollback_reason = payload.reason

    logger.info(
        "Rolled back deployment %s (reason: %s)",
        deployment_id,
        payload.reason,
    )

    return RollbackModelResponse(
        deployment_id=deployment_id,
        previous_status=previous_status,
        new_status=DeploymentStatus.ROLLED_BACK.value,
        rolled_back_at=deployment.rolled_back_at,
        message=f"Successfully rolled back deployment: {payload.reason}",
    )


# ============================================================================
# Model Evaluation Endpoints
# ============================================================================


@router.post(
    "/evaluations",
    response_model=ModelEvaluationResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Record model evaluation",
    description="Record benchmark evaluation results for a model version.",
)
async def create_evaluation(
    payload: ModelEvaluationCreate,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ModelEvaluationResponse:
    """Record a model evaluation."""
    tenant_id = caller.tenant_id

    # Verify model exists
    model_result = await db.execute(
        select(ModelVersion).where(
            and_(
                ModelVersion.id == payload.model_version_id,
                ModelVersion.tenant_id == tenant_id,
            )
        )
    )
    model = model_result.scalar_one_or_none()

    if not model:
        raise NotFoundError(message = str(f"ModelVersion {payload.model_version_id} not found"))

    evaluation = ModelEvaluation(
        tenant_id=tenant_id,
        model_version_id=payload.model_version_id,
        benchmark_name=payload.benchmark_name,
        benchmark_version=payload.benchmark_version,
        score=payload.score,
        score_details=payload.score_details,
        sample_size=payload.sample_size,
        cost_usd=payload.cost_usd,
        duration_seconds=payload.duration_seconds,
        evaluation_config=payload.evaluation_config,
        notes=payload.notes,
        artifact_urls=payload.artifact_urls,
        evaluated_by=caller.user_id or caller.email,
    )

    db.add(evaluation)
    await db.refresh(evaluation)

    logger.info(
        "Recorded evaluation for %s/%s@%s: %s=%.4f",
        model.provider,
        model.name,
        model.version,
        payload.benchmark_name,
        payload.score,
    )

    return ModelEvaluationResponse.model_validate(evaluation)


@router.get(
    "/evaluations",
    response_model=ModelEvaluationListResponse,
    summary="List evaluations",
    description="List model evaluations with optional filtering.",
)
async def list_evaluations(
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
    model_version_id: UUID | None = Query(default=None),
    benchmark_name: str | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
) -> ModelEvaluationListResponse:
    """List evaluations with filtering."""
    tenant_id = caller.tenant_id

    query = select(ModelEvaluation).where(
        ModelEvaluation.tenant_id == tenant_id
    )

    if model_version_id:
        query = query.where(ModelEvaluation.model_version_id == model_version_id)
    if benchmark_name:
        query = query.where(ModelEvaluation.benchmark_name == benchmark_name)

    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0

    # Get paginated results
    query = query.order_by(desc(ModelEvaluation.evaluated_at)).offset(offset).limit(limit)
    result = await db.execute(query)
    evaluations = result.scalars().all()

    return ModelEvaluationListResponse(
        items=[ModelEvaluationResponse.model_validate(e) for e in evaluations],
        total=total,
    )


@router.get(
    "/models/{model_id}/evaluations",
    response_model=ModelEvaluationListResponse,
    summary="Get model evaluations",
    description="Get all evaluations for a specific model version.",
)
async def get_model_evaluations(
    model_id: UUID,
    caller: TokenClaims = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_from_context),
) -> ModelEvaluationListResponse:
    """Get evaluations for a model version."""
    tenant_id = caller.tenant_id

    result = await db.execute(
        select(ModelEvaluation).where(
            and_(
                ModelEvaluation.model_version_id == model_id,
                ModelEvaluation.tenant_id == tenant_id,
            )
        )
    )
    evaluations = result.scalars().all()

    return ModelEvaluationListResponse(
        items=[ModelEvaluationResponse.model_validate(e) for e in evaluations],
        total=len(evaluations),
    )
