"""
Test suite for Model Registry.

Covers:
  - ModelVersion CRUD operations
  - ModelDeployment promotion and rollback
  - ModelEvaluation recording
  - Multi-tenancy isolation
  - API contract validation
"""

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest
import sqlalchemy as sa
from fastapi import status
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from layer5_ground_truth.models.model_registry import (
    DeploymentEnvironment,
    DeploymentStatus,
    ModelCapability,
    ModelDeployment,
    ModelEvaluation,
    ModelProvider,
    ModelVersion,
)


# -----------------------------------------------------------------------------
# Fixtures
# -----------------------------------------------------------------------------


@pytest.fixture
async def sample_model_version(db: AsyncSession, tenant_id: str) -> ModelVersion:
    """Create a sample model version for testing."""
    model = ModelVersion(
        tenant_id=uuid.UUID(tenant_id),
        name="gpt-4-turbo",
        provider=ModelProvider.OPENAI.value,
        version="1.0.0",
        model_identifier="gpt-4-turbo-preview",
        capabilities=[ModelCapability.JSON_MODE.value, ModelCapability.FUNCTION_CALLING.value],
        context_window=128000,
        max_output_tokens=4096,
        cost_per_1k_input=Decimal("0.01"),
        cost_per_1k_output=Decimal("0.03"),
        description="GPT-4 Turbo model for testing",
        is_active=True,
        created_by="test@example.com",
    )
    db.add(model)
    await db.commit()
    await db.refresh(model)
    return model


@pytest.fixture
async def sample_deployment(
    db: AsyncSession,
    tenant_id: str,
    sample_model_version: ModelVersion,
) -> ModelDeployment:
    """Create a sample deployment for testing."""
    deployment = ModelDeployment(
        tenant_id=uuid.UUID(tenant_id),
        model_version_id=sample_model_version.id,
        environment=DeploymentEnvironment.DEVELOPMENT.value,
        status=DeploymentStatus.ACTIVE.value,
        traffic_percentage=100,
        is_default_for_env=True,
        deployed_at=datetime.now(UTC),
        deployed_by="test@example.com",
    )
    db.add(deployment)
    await db.commit()
    await db.refresh(deployment)
    return deployment


@pytest.fixture
async def sample_evaluation(
    db: AsyncSession,
    tenant_id: str,
    sample_model_version: ModelVersion,
) -> ModelEvaluation:
    """Create a sample evaluation for testing."""
    evaluation = ModelEvaluation(
        tenant_id=uuid.UUID(tenant_id),
        model_version_id=sample_model_version.id,
        benchmark_name="mmlu",
        benchmark_version="v1",
        score=Decimal("0.8750"),
        score_details={"stem": 0.90, "humanities": 0.85},
        sample_size=1000,
        cost_usd=Decimal("5.25"),
        duration_seconds=3600,
        evaluated_by="test@example.com",
    )
    db.add(evaluation)
    await db.commit()
    await db.refresh(evaluation)
    return evaluation


# -----------------------------------------------------------------------------
# ModelVersion Tests
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
class TestModelVersionCRUD:
    """Tests for ModelVersion CRUD operations."""

    async def test_create_model_version(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Test creating a new model version via API."""
        payload = {
            "name": "claude-3-opus",
            "provider": "anthropic",
            "version": "20240229",
            "model_identifier": "claude-3-opus-20240229",
            "capabilities": ["json_mode", "function_calling", "vision"],
            "context_window": 200000,
            "max_output_tokens": 4096,
            "cost_per_1k_input": 0.015,
            "cost_per_1k_output": 0.075,
            "description": "Claude 3 Opus model",
            "metadata": {"api_version": "v1"},
        }

        response = await async_client.post(
            "/api/v1/models",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["provider"] == payload["provider"]
        assert data["version"] == payload["version"]
        assert data["capabilities"] == payload["capabilities"]
        assert data["cost_per_1k_input"] == payload["cost_per_1k_input"]
        assert data["is_active"] is True
        assert "id" in data

    async def test_create_duplicate_model_version_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
    ) -> None:
        """Test that creating duplicate model version returns 409."""
        payload = {
            "name": sample_model_version.name,
            "provider": sample_model_version.provider,
            "version": sample_model_version.version,
            "model_identifier": "different-identifier",
            "capabilities": [],
        }

        response = await async_client.post(
            "/api/v1/models",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_409_CONFLICT
        assert "already exists" in response.json()["error"]["message"].lower()

    async def test_list_model_versions(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
    ) -> None:
        """Test listing model versions."""
        response = await async_client.get(
            "/api/v1/models",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1
        assert any(item["id"] == str(sample_model_version.id) for item in data["items"])

    async def test_list_model_versions_with_filter(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
    ) -> None:
        """Test listing model versions with provider filter."""
        response = await async_client.get(
            "/api/v1/models?provider=openai",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(item["provider"] == "openai" for item in data["items"])

    async def test_get_model_version(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
    ) -> None:
        """Test getting a specific model version."""
        response = await async_client.get(
            f"/api/v1/models/{sample_model_version.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["id"] == str(sample_model_version.id)
        assert data["name"] == sample_model_version.name

    async def test_get_nonexistent_model_version(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Test getting a non-existent model version returns 404."""
        fake_id = str(uuid.uuid4())
        response = await async_client.get(
            f"/api/v1/models/{fake_id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_deprecate_model_version(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
    ) -> None:
        """Test deprecating a model version."""
        response = await async_client.post(
            f"/api/v1/models/{sample_model_version.id}/deprecate?reason=Outdated",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_active"] is False
        assert data["deprecated_at"] is not None
        assert data["deprecation_reason"] == "Outdated"

    async def test_set_default_model_version(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
    ) -> None:
        """Test setting a model version as default."""
        response = await async_client.post(
            f"/api/v1/models/{sample_model_version.id}/set-default",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["is_default"] is True


# -----------------------------------------------------------------------------
# ModelDeployment Tests
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
class TestModelDeployment:
    """Tests for ModelDeployment operations."""

    async def test_promote_model(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
    ) -> None:
        """Test promoting a model to an environment."""
        payload = {
            "environment": "staging",
            "traffic_percentage": 50,
            "make_default": True,
        }

        response = await async_client.post(
            f"/api/v1/models/{sample_model_version.id}/promote",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["model_version_id"] == str(sample_model_version.id)
        assert data["environment"] == "staging"
        assert data["traffic_percentage"] == 50
        assert data["is_default_for_env"] is True
        assert "deployment_id" in data

    async def test_promote_inactive_model_fails(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
        db: AsyncSession,
    ) -> None:
        """Test that promoting an inactive model fails."""
        # Deactivate the model first
        sample_model_version.is_active = False
        await db.commit()

        payload = {
            "environment": "production",
            "traffic_percentage": 100,
        }

        response = await async_client.post(
            f"/api/v1/models/{sample_model_version.id}/promote",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_422_UNPROCESSABLE_ENTITY
        assert "inactive" in response.json()["error"]["message"].lower()

    async def test_list_deployments(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_deployment: ModelDeployment,
    ) -> None:
        """Test listing all deployments."""
        response = await async_client.get(
            "/api/v1/deployments",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert any(item["id"] == str(sample_deployment.id) for item in data["items"])

    async def test_list_deployments_with_filter(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_deployment: ModelDeployment,
    ) -> None:
        """Test listing deployments with environment filter."""
        response = await async_client.get(
            "/api/v1/deployments?environment=development",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(item["environment"] == "development" for item in data["items"])

    async def test_rollback_deployment(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_deployment: ModelDeployment,
    ) -> None:
        """Test rolling back a deployment."""
        payload = {"reason": "High error rate detected"}

        response = await async_client.post(
            f"/api/v1/deployments/{sample_deployment.id}/rollback",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["deployment_id"] == str(sample_deployment.id)
        assert data["new_status"] == "rolled_back"
        assert "rolled_back_at" in data

    async def test_get_model_deployments(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
        sample_deployment: ModelDeployment,
    ) -> None:
        """Test getting deployments for a specific model."""
        response = await async_client.get(
            f"/api/v1/models/{sample_model_version.id}/deployments",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert any(item["id"] == str(sample_deployment.id) for item in data["items"])


# -----------------------------------------------------------------------------
# ModelEvaluation Tests
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
class TestModelEvaluation:
    """Tests for ModelEvaluation operations."""

    async def test_create_evaluation(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
    ) -> None:
        """Test recording a model evaluation."""
        payload = {
            "model_version_id": str(sample_model_version.id),
            "benchmark_name": "human-eval",
            "benchmark_version": "v2",
            "score": 0.92,
            "score_details": {"pass_at_1": 0.89, "pass_at_100": 0.95},
            "sample_size": 164,
            "cost_usd": 12.50,
            "duration_seconds": 1800,
            "evaluation_config": {"temperature": 0.2, "top_p": 0.95},
            "notes": "Strong performance on coding tasks",
        }

        response = await async_client.post(
            "/api/v1/evaluations",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_201_CREATED
        data = response.json()
        assert data["model_version_id"] == str(sample_model_version.id)
        assert data["benchmark_name"] == "human-eval"
        assert data["score"] == 0.92
        assert data["sample_size"] == 164

    async def test_create_evaluation_for_nonexistent_model(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
    ) -> None:
        """Test that creating evaluation for non-existent model returns 404."""
        payload = {
            "model_version_id": str(uuid.uuid4()),
            "benchmark_name": "mmlu",
            "score": 0.85,
        }

        response = await async_client.post(
            "/api/v1/evaluations",
            json=payload,
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_list_evaluations(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_evaluation: ModelEvaluation,
    ) -> None:
        """Test listing evaluations."""
        response = await async_client.get(
            "/api/v1/evaluations",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert data["total"] >= 1

    async def test_list_evaluations_with_filter(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
        sample_evaluation: ModelEvaluation,
    ) -> None:
        """Test listing evaluations with model_version_id filter."""
        response = await async_client.get(
            f"/api/v1/evaluations?model_version_id={sample_model_version.id}",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert all(
            item["model_version_id"] == str(sample_model_version.id)
            for item in data["items"]
        )

    async def test_get_model_evaluations(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        sample_model_version: ModelVersion,
        sample_evaluation: ModelEvaluation,
    ) -> None:
        """Test getting evaluations for a specific model."""
        response = await async_client.get(
            f"/api/v1/models/{sample_model_version.id}/evaluations",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["total"] >= 1
        assert any(item["id"] == str(sample_evaluation.id) for item in data["items"])


# -----------------------------------------------------------------------------
# Multi-tenancy Tests
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
class TestMultiTenancy:
    """Tests for organization isolation."""

    async def test_cannot_access_other_org_model(
        self,
        tenant_aware_client: AsyncClient,
        sample_model_version: ModelVersion,
        db: AsyncSession,
    ) -> None:
        """Test that models from other orgs are not accessible."""
        response = await tenant_aware_client.get(
            f"/api/v1/models/{sample_model_version.id}",
            headers={"X-Test-Tenant": str(uuid.uuid4())},
        )

        # Should return 404 (not 403) to avoid leaking existence
        assert response.status_code == status.HTTP_404_NOT_FOUND

    async def test_list_only_shows_own_org_models(
        self,
        async_client: AsyncClient,
        auth_headers: dict,
        db: AsyncSession,
        tenant_id: str,
    ) -> None:
        """Test that list only returns models for the authenticated org."""
        # Create a model for a different org directly in DB
        other_org_id = uuid.uuid4()
        other_model = ModelVersion(
            tenant_id=other_org_id,
            name="other-model",
            provider=ModelProvider.OPENAI.value,
            version="1.0.0",
            model_identifier="gpt-4",
            capabilities=[],
            cost_per_1k_input=Decimal("0.01"),
            cost_per_1k_output=Decimal("0.03"),
        )
        db.add(other_model)
        await db.commit()

        # List should only show models for our org
        response = await async_client.get(
            "/api/v1/models",
            headers=auth_headers,
        )

        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        # Should not include the other org's model
        assert not any(item["name"] == "other-model" for item in data["items"])


# -----------------------------------------------------------------------------
# Database Model Tests
# -----------------------------------------------------------------------------


@pytest.mark.asyncio
class TestDatabaseModels:
    """Direct database model tests."""

    async def test_model_version_relationships(
        self,
        db: AsyncSession,
        sample_model_version: ModelVersion,
        sample_deployment: ModelDeployment,
        sample_evaluation: ModelEvaluation,
    ) -> None:
        """Test that relationships work correctly."""
        # Refresh to load relationships
        await db.refresh(sample_model_version)

        assert len(sample_model_version.deployments) >= 1
        assert len(sample_model_version.evaluations) >= 1
        assert any(d.id == sample_deployment.id for d in sample_model_version.deployments)
        assert any(e.id == sample_evaluation.id for e in sample_model_version.evaluations)

    async def test_model_deployment_cascade_delete(
        self,
        db: AsyncSession,
        sample_model_version: ModelVersion,
        sample_deployment: ModelDeployment,
    ) -> None:
        """Test that deleting a model version cascades to deployments."""
        deployment_id = sample_deployment.id

        # Delete the model version
        await db.delete(sample_model_version)
        await db.commit()

        # Deployment should be deleted (cascade)
        result = await db.execute(
            sa.select(ModelDeployment).where(ModelDeployment.id == deployment_id)
        )
        assert result.scalar_one_or_none() is None

    async def test_model_evaluation_cascade_delete(
        self,
        db: AsyncSession,
        sample_model_version: ModelVersion,
        sample_evaluation: ModelEvaluation,
    ) -> None:
        """Test that deleting a model version cascades to evaluations."""
        evaluation_id = sample_evaluation.id

        # Delete the model version
        await db.delete(sample_model_version)
        await db.commit()

        # Evaluation should be deleted (cascade)
        import sqlalchemy as sa
        result = await db.execute(
            sa.select(ModelEvaluation).where(ModelEvaluation.id == evaluation_id)
        )
        assert result.scalar_one_or_none() is None
