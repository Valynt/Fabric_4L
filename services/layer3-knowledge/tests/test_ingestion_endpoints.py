"""Integration tests for ingestion endpoints."""


from types import SimpleNamespace

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from httpx import AsyncClient

from value_fabric.shared.error_handling.handlers import register_exception_handlers

from conftest import TestUtils


class TenantScopedSyncManager:
    """Small in-memory sync manager that only returns data for the caller tenant."""

    def __init__(self):
        self.records = {
            ("tenant-a", "source-a"): {
                "source_id": "source-a",
                "last_extraction_job_id": "job-a",
                "content_hash": "hash-a",
                "synced_at": "2024-01-01T00:00:00Z",
                "status": "synced",
                "error": None,
            },
            ("tenant-b", "source-b"): {
                "source_id": "source-b",
                "last_extraction_job_id": "job-b",
                "content_hash": "hash-b",
                "synced_at": "2024-01-02T00:00:00Z",
                "status": "synced",
                "error": None,
            },
        }
        self.deleted = []
        self.status_calls = []
        self.delete_calls = []

    async def get_sync_status(self, source_id: str, tenant_id: str | None):
        self.status_calls.append((source_id, tenant_id))
        return self.records.get((tenant_id, source_id))

    async def delete_source(self, source_id: str, tenant_id: str | None):
        self.delete_calls.append((source_id, tenant_id))
        key = (tenant_id, source_id)
        if key not in self.records:
            return {"entities_deleted": 0, "relationships_deleted": 0}

        del self.records[key]
        self.deleted.append(key)
        return {"entities_deleted": 3, "relationships_deleted": 4}


@pytest.fixture
def tenant_scoped_ingestion_app():
    """Build a minimal app that mirrors authenticated request context extraction."""
    from api.routes import ingestion

    app = FastAPI()
    manager = TenantScopedSyncManager()

    @app.middleware("http")
    async def authenticated_context_middleware(request: Request, call_next):
        tenant_id = request.headers.get("x-test-tenant")
        if tenant_id:
            request.state.context = SimpleNamespace(tenant_id=tenant_id)
        return await call_next(request)

    app.dependency_overrides[ingestion.get_sync_manager] = lambda: manager
    app.include_router(ingestion.router)
    register_exception_handlers(app)
    return app, manager


class TestIngestionTenantIsolation:
    """Hostile tenant regression coverage for ingestion metadata endpoints."""

    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("get", "/v1/ingest/status/source-a"),
            ("delete", "/v1/ingest/source-a"),
        ],
    )
    def test_missing_auth_context_returns_401(
        self, tenant_scoped_ingestion_app, method, path
    ):
        app, manager = tenant_scoped_ingestion_app

        with TestClient(app) as client:
            response = getattr(client, method)(path)

        assert response.status_code == 401
        assert manager.status_calls == []
        assert manager.delete_calls == []

    def test_tenant_a_cannot_read_tenant_b_sync_metadata(self, tenant_scoped_ingestion_app):
        app, manager = tenant_scoped_ingestion_app

        with TestClient(app) as client:
            response = client.get(
                "/v1/ingest/status/source-b",
                headers={"x-test-tenant": "tenant-a"},
            )

        assert response.status_code == 404
        assert manager.status_calls == [("source-b", "tenant-a")]

    def test_tenant_a_cannot_delete_tenant_b_source_data(self, tenant_scoped_ingestion_app):
        app, manager = tenant_scoped_ingestion_app

        with TestClient(app) as client:
            response = client.delete(
                "/v1/ingest/source-b",
                headers={"x-test-tenant": "tenant-a"},
            )

        assert response.status_code == 200
        assert response.json()["entities_deleted"] == 0
        assert response.json()["relationships_deleted"] == 0
        assert manager.delete_calls == [("source-b", "tenant-a")]
        assert ("tenant-b", "source-b") in manager.records
        assert ("tenant-b", "source-b") not in manager.deleted


class TestIngestionEndpoints:
    """Test ingestion endpoints."""
    
    def test_ingest_endpoint_basic(self, test_client: TestClient, sample_ingestion_request, test_utils: TestUtils):
        """Test basic ingestion endpoint."""
        response = test_client.post("/v1/ingest", json=sample_ingestion_request)
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_ingestion_response(data)
        assert data["source_id"] == sample_ingestion_request["source_id"]
    
    def test_ingest_endpoint_without_hash(self, test_client: TestClient, sample_ingestion_request, test_utils: TestUtils):
        """Test ingestion endpoint without content hash."""
        ingestion_request = sample_ingestion_request.copy()
        del ingestion_request["content_hash"]
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_ingestion_response(data)
        assert data["source_id"] == ingestion_request["source_id"]
    
    def test_ingest_endpoint_invalid_rdf_data(self, test_client: TestClient, sample_ingestion_request):
        """Test ingestion endpoint with invalid RDF data."""
        ingestion_request = sample_ingestion_request.copy()
        ingestion_request["rdf_data"] = ""  # Empty RDF data
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_ingest_endpoint_missing_source_id(self, test_client: TestClient, sample_ingestion_request):
        """Test ingestion endpoint with missing source ID."""
        ingestion_request = sample_ingestion_request.copy()
        del ingestion_request["source_id"]
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_ingest_endpoint_missing_job_id(self, test_client: TestClient, sample_ingestion_request):
        """Test ingestion endpoint with missing job ID."""
        ingestion_request = sample_ingestion_request.copy()
        del ingestion_request["extraction_job_id"]
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_ingest_endpoint_long_source_id(self, test_client: TestClient, sample_ingestion_request):
        """Test ingestion endpoint with too long source ID."""
        ingestion_request = sample_ingestion_request.copy()
        ingestion_request["source_id"] = "x" * 256  # Exceeds max length of 255
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_ingest_endpoint_long_job_id(self, test_client: TestClient, sample_ingestion_request):
        """Test ingestion endpoint with too long job ID."""
        ingestion_request = sample_ingestion_request.copy()
        ingestion_request["extraction_job_id"] = "x" * 256  # Exceeds max length of 255
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_ingest_endpoint_invalid_hash_length(self, test_client: TestClient, sample_ingestion_request):
        """Test ingestion endpoint with invalid hash length."""
        ingestion_request = sample_ingestion_request.copy()
        ingestion_request["content_hash"] = "short_hash"  # Too short
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_ingest_endpoint_invalid_hash_format(self, test_client: TestClient, sample_ingestion_request):
        """Test ingestion endpoint with invalid hash format."""
        ingestion_request = sample_ingestion_request.copy()
        ingestion_request["content_hash"] = "g" * 64  # Invalid characters
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 422  # Validation error
    
    def test_ingest_endpoint_too_large_rdf_data(self, test_client: TestClient, sample_ingestion_request):
        """Test ingestion endpoint with too large RDF data."""
        ingestion_request = sample_ingestion_request.copy()
        ingestion_request["rdf_data"] = "x" * 1000001  # Exceeds max length of 1MB
        
        response = test_client.post("/v1/ingest", json=ingestion_request)
        
        assert response.status_code == 422  # Validation error
    
    @pytest.mark.asyncio
    async def test_ingest_endpoint_async(self, async_client: AsyncClient, sample_ingestion_request, test_utils: TestUtils):
        """Test ingestion endpoint with async client."""
        response = await async_client.post("/v1/ingest", json=sample_ingestion_request)
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_ingestion_response(data)
        assert data["source_id"] == sample_ingestion_request["source_id"]
    
    def test_ingest_endpoint_with_mock_response(self, test_client: TestClient, sample_ingestion_request, mock_app_state, test_utils: TestUtils):
        """Test ingestion endpoint with mocked response."""
        # Configure mock ingestion response
        mock_app_state.sync_manager.ingest_rdf.return_value = {
            "status": "success",
            "source_id": sample_ingestion_request["source_id"],
            "entities_loaded": 10,
            "relationships_loaded": 15,
            "triples_processed": 25,
            "duration_seconds": 3.5,
            "warnings": ["Some triples were skipped due to format issues"]
        }
        
        response = test_client.post("/v1/ingest", json=sample_ingestion_request)
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_ingestion_response(data)
        assert data["entities_loaded"] == 10
        assert data["relationships_loaded"] == 15
        assert data["triples_processed"] == 25
        assert data["duration_seconds"] == 3.5
        assert len(data["warnings"]) == 1
        
        # Verify mock was called with correct parameters
        mock_app_state.sync_manager.ingest_rdf.assert_called_once()
        call_args = mock_app_state.sync_manager.ingest_rdf.call_args
        assert call_args[1]["rdf_data"] == sample_ingestion_request["rdf_data"]
        assert call_args[1]["source_id"] == sample_ingestion_request["source_id"]
        assert call_args[1]["extraction_job_id"] == sample_ingestion_request["extraction_job_id"]
    
    def test_ingest_endpoint_partial_success(self, test_client: TestClient, sample_ingestion_request, mock_app_state):
        """Test ingestion endpoint with partial success."""
        mock_app_state.sync_manager.ingest_rdf.return_value = {
            "status": "partial",
            "source_id": sample_ingestion_request["source_id"],
            "entities_loaded": 8,
            "relationships_loaded": 12,
            "triples_processed": 20,
            "duration_seconds": 2.8,
            "error": "Some entities could not be processed",
            "warnings": ["Entity 5 had missing properties", "Relationship 10 was invalid"]
        }
        
        response = test_client.post("/v1/ingest", json=sample_ingestion_request)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "partial"
        assert data["entities_loaded"] == 8
        assert data["relationships_loaded"] == 12
        assert data["triples_processed"] == 20
        assert "error" in data
        assert len(data["warnings"]) == 2
    
    def test_ingest_endpoint_failure(self, test_client: TestClient, sample_ingestion_request, mock_app_state):
        """Test ingestion endpoint with failure."""
        mock_app_state.sync_manager.ingest_rdf.return_value = {
            "status": "failed",
            "source_id": sample_ingestion_request["source_id"],
            "entities_loaded": 0,
            "relationships_loaded": 0,
            "triples_processed": 0,
            "duration_seconds": 0.5,
            "error": "RDF parsing failed: Invalid syntax at line 15",
            "warnings": []
        }
        
        response = test_client.post("/v1/ingest", json=sample_ingestion_request)
        
        assert response.status_code == 200  # Still returns 200 but with failed status
        data = response.json()
        
        assert data["status"] == "failed"
        assert data["entities_loaded"] == 0
        assert data["relationships_loaded"] == 0
        assert data["triples_processed"] == 0
        assert "error" in data
        assert data["error"] == "RDF parsing failed: Invalid syntax at line 15"
    
    def test_ingest_endpoint_error_handling(self, test_client: TestClient, sample_ingestion_request, mock_app_state):
        """Test ingestion endpoint error handling."""
        # Configure mock to raise exception
        mock_app_state.sync_manager.ingest_rdf.side_effect = Exception("Ingestion service unavailable")
        
        response = test_client.post("/v1/ingest", json=sample_ingestion_request)
        
        assert response.status_code == 500
        data = response.json()
        assert "error" in data
    
    def test_sync_status_endpoint(self, test_client: TestClient, mock_app_state):
        """Test sync status endpoint."""
        mock_app_state.sync_manager.get_sync_status.return_value = {
            "source_id": "test_doc_123",
            "last_extraction_job_id": "job_456",
            "content_hash": "abc123def456",
            "synced_at": "2024-01-01T12:00:00Z",
            "status": "synced",
            "error": None
        }
        
        response = test_client.get("/v1/sync/test_doc_123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["source_id"] == "test_doc_123"
        assert data["last_extraction_job_id"] == "job_456"
        assert data["content_hash"] == "abc123def456"
        assert data["synced_at"] == "2024-01-01T12:00:00Z"
        assert data["status"] == "synced"
        assert data["error"] is None
    
    def test_sync_status_not_found(self, test_client: TestClient, mock_app_state):
        """Test sync status endpoint for non-existent source."""
        mock_app_state.sync_manager.get_sync_status.return_value = None
        
        response = test_client.get("/v1/sync/nonexistent_doc")
        
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data
    
    def test_sync_status_with_error(self, test_client: TestClient, mock_app_state):
        """Test sync status endpoint with error."""
        mock_app_state.sync_manager.get_sync_status.return_value = {
            "source_id": "test_doc_123",
            "last_extraction_job_id": "job_456",
            "content_hash": None,
            "synced_at": None,
            "status": "failed",
            "error": "Connection timeout during sync"
        }
        
        response = test_client.get("/v1/sync/test_doc_123")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["status"] == "failed"
        assert data["error"] == "Connection timeout during sync"
    
    def test_ingest_response_structure_validation(self, test_client: TestClient, sample_ingestion_request, mock_app_state, test_utils: TestUtils):
        """Test ingestion response structure in detail."""
        mock_app_state.sync_manager.ingest_rdf.return_value = {
            "status": "success",
            "source_id": sample_ingestion_request["source_id"],
            "entities_loaded": 15,
            "relationships_loaded": 25,
            "triples_processed": 40,
            "duration_seconds": 4.2,
            "warnings": [
                "Entity 3 had missing description property",
                "Relationship 7 had duplicate source-target pair"
            ]
        }
        
        response = test_client.post("/v1/ingest", json=sample_ingestion_request)
        
        assert response.status_code == 200
        data = response.json()
        
        test_utils.assert_valid_ingestion_response(data)
        
        # Validate detailed structure
        assert data["status"] in ["success", "partial", "failed"]
        assert isinstance(data["entities_loaded"], int)
        assert isinstance(data["relationships_loaded"], int)
        assert isinstance(data["triples_processed"], int)
        assert isinstance(data["duration_seconds"], (int, float, type(None)))
        assert isinstance(data["warnings"], list)
        
        # Validate value ranges
        assert data["entities_loaded"] >= 0
        assert data["relationships_loaded"] >= 0
        assert data["triples_processed"] >= 0
        if data["duration_seconds"] is not None:
            assert data["duration_seconds"] >= 0
        
        # Validate warnings
        for warning in data["warnings"]:
            assert isinstance(warning, str)
            assert len(warning) > 0
        
        # Validate logical consistency
        assert data["triples_processed"] >= data["entities_loaded"]
        assert data["triples_processed"] >= data["relationships_loaded"]

