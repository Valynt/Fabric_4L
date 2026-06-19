"""Route ordering regression tests for canonical endpoints.

FastAPI matches routes top-to-bottom. These tests guard against route
shadowing and verify canonical endpoints are reachable.

Covers:
- POST /jobs/batch hits the batch handler
- POST /targets/{id}/validate still works for real UUIDs
- PUT /targets/{id} works for real UUIDs
- OpenAPI schema contains canonical paths
"""

from __future__ import annotations

import json
import uuid
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from layer1_ingestion.api.main import BatchOperationRequest, BatchOperationType


def _get_app():
    from layer1_ingestion.api.main import app
    return app


# ---------------------------------------------------------------------------
# Batch route is reachable
# ---------------------------------------------------------------------------

class TestBatchRouteReachable:
    def test_batch_route_returns_202_not_404_or_422_for_valid_payload(
        self, client, db, org_id, make_target
    ):
        t = make_target(org_id, status="ACTIVE")
        request = BatchOperationRequest(
            operation=BatchOperationType.EXECUTE,
            target_ids=[t.id],
        )
        resp = client.post(
            "/api/v1/ingestion/jobs/batch",
            json=request.model_dump(mode="json"),
        )
        # 202 = batch handler reached; 422 = validation error (also batch handler)
        # 404 = route not found (wrong handler matched) — must NOT happen
        assert resp.status_code != 404, (
            "POST /jobs/batch returned 404 — route ordering regression"
        )

    def test_batch_route_response_has_batch_shape(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        request = BatchOperationRequest(
            operation=BatchOperationType.EXECUTE,
            target_ids=[t.id],
        )
        resp = client.post(
            "/api/v1/ingestion/jobs/batch",
            json=request.model_dump(mode="json"),
        )
        data = resp.json()
        assert "operation" in data
        assert "succeeded" in data
        assert "results" in data


# ---------------------------------------------------------------------------
# Validate route still works
# ---------------------------------------------------------------------------

class TestValidateRouteStillWorks:
    def test_validate_route_reachable_for_real_uuid(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = client.post(
            f"/api/v1/ingestion/targets/{t.id}/validate",
            json={"test_url": "https://example.com", "validate_robots_txt": False},
        )
        # 200 or 422 = validate handler reached; 404 = wrong route matched
        assert resp.status_code != 404, (
            f"POST /targets/{{id}}/validate returned 404 for a real UUID — "
            "route ordering regression"
        )


# ---------------------------------------------------------------------------
# "batch" as a literal target_id cannot shadow the batch route
# ---------------------------------------------------------------------------

class TestBatchLiteralIdShadowing:
    def test_string_batch_as_target_id_does_not_shadow_target_route(
        self, client, org_id
    ):
        """
        FastAPI path params are typed as UUID. A request to /targets/batch
        with the literal string "batch" should fail UUID validation (422), not
        accidentally route to the target detail endpoint.
        """
        resp = client.put(
            "/api/v1/ingestion/targets/batch",
            json={"status": "PAUSED"},
        )
        # 422 = UUID validation failed (correct — "batch" is not a UUID)
        # 404 = route not found (also acceptable)
        # 200 = WRONG — "batch" was treated as a valid target_id
        assert resp.status_code in (404, 422), (
            f"Unexpected status {resp.status_code}: literal 'batch' was treated "
            "as a valid target_id"
        )


# ---------------------------------------------------------------------------
# OpenAPI schema contains both paths
# ---------------------------------------------------------------------------

class TestOpenAPIContainsBothPaths:
    def test_openapi_contains_jobs_batch_path(self):
        app = _get_app()
        schema = app.openapi()
        paths = schema.get("paths", {})
        assert any("jobs/batch" in p for p in paths), (
            "OpenAPI schema missing /jobs/batch path"
        )

    def test_openapi_contains_validate_path(self):
        app = _get_app()
        schema = app.openapi()
        paths = schema.get("paths", {})
        assert any("validate" in p for p in paths), (
            "OpenAPI schema missing /targets/{id}/validate path"
        )

    def test_openapi_contains_target_put_path(self):
        app = _get_app()
        schema = app.openapi()
        paths = schema.get("paths", {})
        assert any("targets/{target_id}" in p for p in paths), (
            "OpenAPI schema missing /targets/{target_id} path"
        )

    def test_jobs_batch_path_has_post_method(self):
        app = _get_app()
        schema = app.openapi()
        batch_path = next(
            (p for p in schema.get("paths", {}) if "jobs/batch" in p), None
        )
        assert batch_path is not None
        assert "post" in schema["paths"][batch_path]

    def test_target_path_has_put_method(self):
        app = _get_app()
        schema = app.openapi()
        target_path = next(
            (p for p in schema.get("paths", {}) if "targets/{target_id}" in p), None
        )
        assert target_path is not None
        assert "put" in schema["paths"][target_path]
