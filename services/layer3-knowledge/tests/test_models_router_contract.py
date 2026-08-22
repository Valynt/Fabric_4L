"""Contract and tenant boundary tests for models_router."""

from unittest.mock import AsyncMock, MagicMock, patch
import pytest
from fastapi.testclient import TestClient

from src.api.main import app
from src.api.routes.models_router import (
    FOLDER_ALL,
    FOLDER_FAVORITES,
    FOLDER_MY_MODELS,
    FOLDER_SHARED,
    ModelCreateRequest,
    ModelDetail,
    ModelListResponse,
    ModelStatus,
    ModelSummary,
    ValidationError,
    _build_list_models_query_and_params,
    _model_node_to_summary,
    _validate_list_models_params,
)


@pytest.mark.unit
def test_validate_list_models_params_valid():
    """Verify valid folder, sort_by, and sort_dir pass without error."""
    _validate_list_models_params(FOLDER_ALL, "updated_at", "desc")
    _validate_list_models_params(FOLDER_MY_MODELS, "name", "asc")
    _validate_list_models_params(FOLDER_SHARED, "created_at", "desc")


@pytest.mark.unit
def test_validate_list_models_params_invalid():
    """Verify invalid parameters raise ValidationError."""
    with pytest.raises(ValidationError, match="Invalid folder"):
        _validate_list_models_params("unknown-folder", "updated_at", "desc")

    with pytest.raises(ValidationError, match="Invalid sort_by"):
        _validate_list_models_params(FOLDER_ALL, "invalid_field", "desc")

    with pytest.raises(ValidationError, match="Invalid sort_dir"):
        _validate_list_models_params(FOLDER_ALL, "updated_at", "diagonal")


@pytest.mark.unit
def test_build_list_models_query_and_params():
    """Verify query string construction and parameter binding for list_models."""
    count_q, data_q, params = _build_list_models_query_and_params(
        current_tenant="tenant-99",
        current_user="user-1",
        folder=FOLDER_MY_MODELS,
        status="active",
        industry="Retail",
        search="inventory",
        sort_by="name",
        sort_dir="asc",
        limit=20,
        offset=0,
    )
    assert "m.tenant_id = $tenant_id" in count_q
    assert "m.owner = $user_id" in count_q
    assert "m.status = $status" in count_q
    assert "m.industry = $industry" in count_q
    assert "m.name CONTAINS $search" in count_q
    assert "ORDER BY m.name ASC" in data_q
    assert params["tenant_id"] == "tenant-99"
    assert params["user_id"] == "user-1"
    assert params["status"] == "active"
    assert params["industry"] == "Retail"
    assert params["search"] == "inventory"


@pytest.mark.unit
def test_model_node_to_summary():
    """Verify dictionary record from Neo4j is transformed to ModelSummary properly."""
    record = {
        "m": {
            "model_id": "mdl_123",
            "name": "Supply Chain ROI",
            "description": "Logistics cost reduction",
            "industry": "Manufacturing",
            "tags": ["supply-chain", "logistics"],
            "status": "active",
            "folder": "my-models",
            "formula_count": 3,
            "entity_count": 8,
            "driver_count": 2,
            "created_at": "2026-01-01T00:00:00Z",
            "updated_at": "2026-01-02T00:00:00Z",
            "owner": "user-42",
            "is_shared": False,
        }
    }
    summary = _model_node_to_summary(record)
    assert summary.model_id == "mdl_123"
    assert summary.name == "Supply Chain ROI"
    assert summary.status == ModelStatus.ACTIVE
    assert summary.formula_count == 3
    assert summary.entity_count == 8


@pytest.mark.unit
def test_unauthenticated_request_rejected_fail_closed():
    """Verify that requests without tenant credentials receive 401/403."""
    client = TestClient(app)
    response = client.get("/v1/models")
    assert response.status_code in (401, 403)
