"""OpenAPI contract tests for canonical targets and batch endpoints.

Validates that:
- Canonical paths exist in the live OpenAPI schema
- Required schemas are present with correct required fields
- Enum values are constrained (invalid values rejected)
- Generated frontend type file contains the expected type names
- Client path names match backend OpenAPI paths exactly
"""

from __future__ import annotations

import json
from pathlib import Path


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_schema() -> dict:
    from layer1_ingestion.api.app_monolith import app
    return app.openapi()


def _get_generated_ts() -> str:
    ts_path = (
        Path(__file__).resolve().parents[4]
        / "apps" / "web" / "src" / "api" / "generated" / "l1" / "index.ts"
    )
    if not ts_path.exists():
        return ""
    return ts_path.read_text(encoding="utf-8")


# ---------------------------------------------------------------------------
# Path presence
# ---------------------------------------------------------------------------

class TestPathPresence:
    def test_put_target_path_exists(self):
        schema = _get_schema()
        paths = schema.get("paths", {})
        assert any("targets/{target_id}" in p for p in paths), (
            "PUT /targets/{target_id} not found in OpenAPI schema"
        )

    def test_post_jobs_batch_path_exists(self):
        schema = _get_schema()
        paths = schema.get("paths", {})
        assert any("jobs/batch" in p for p in paths), (
            "POST /jobs/batch not found in OpenAPI schema"
        )

    def test_put_target_has_put_method(self):
        schema = _get_schema()
        target_path = next(
            (p for p in schema["paths"] if "targets/{target_id}" in p), None
        )
        assert target_path is not None
        assert "put" in schema["paths"][target_path], (
            f"PUT method missing from {target_path}"
        )

    def test_put_target_documents_401_response(self):
        schema = _get_schema()
        target_path = next(
            (p for p in schema["paths"] if "targets/{target_id}" in p), None
        )
        assert target_path is not None
        responses = schema["paths"][target_path]["put"].get("responses", {})
        assert "401" in responses

    def test_put_target_documents_404_response(self):
        schema = _get_schema()
        target_path = next(
            (p for p in schema["paths"] if "targets/{target_id}" in p), None
        )
        assert target_path is not None
        responses = schema["paths"][target_path]["put"].get("responses", {})
        assert "404" in responses

    def test_put_target_documents_409_response(self):
        schema = _get_schema()
        target_path = next(
            (p for p in schema["paths"] if "targets/{target_id}" in p), None
        )
        assert target_path is not None
        responses = schema["paths"][target_path]["put"].get("responses", {})
        assert "409" in responses

    def test_post_jobs_batch_has_post_method(self):
        schema = _get_schema()
        batch_path = next(
            (p for p in schema["paths"] if "jobs/batch" in p), None
        )
        assert batch_path is not None
        assert "post" in schema["paths"][batch_path], (
            f"POST method missing from {batch_path}"
        )


# ---------------------------------------------------------------------------
# Schema definitions
# ---------------------------------------------------------------------------

class TestSchemaDefinitions:
    def _components(self):
        return _get_schema().get("components", {}).get("schemas", {})

    def test_update_target_request_schema_exists(self):
        assert "UpdateTargetRequest" in self._components()

    def test_update_target_request_has_status_field(self):
        schema = self._components().get("UpdateTargetRequest", {})
        props = schema.get("properties", {})
        assert "status" in props, (
            "UpdateTargetRequest.status must be present"
        )

    def test_batch_operation_request_schema_exists(self):
        assert "BatchOperationRequest" in self._components()

    def test_batch_operation_request_has_required_operation(self):
        schema = self._components().get("BatchOperationRequest", {})
        required = schema.get("required", [])
        assert "operation" in required

    def test_batch_operation_request_has_target_ids_field(self):
        schema = self._components().get("BatchOperationRequest", {})
        props = schema.get("properties", {})
        assert "target_ids" in props

    def test_batch_operation_response_schema_exists(self):
        assert "BatchOperationResponse" in self._components()

    def test_batch_operation_response_has_succeeded_field(self):
        schema = self._components().get("BatchOperationResponse", {})
        props = schema.get("properties", {})
        assert "succeeded" in props

    def test_batch_operation_response_has_failed_field(self):
        schema = self._components().get("BatchOperationResponse", {})
        props = schema.get("properties", {})
        assert "failed" in props

    def test_batch_operation_response_has_results_field(self):
        schema = self._components().get("BatchOperationResponse", {})
        props = schema.get("properties", {})
        assert "results" in props

    def test_batch_operation_item_result_schema_exists(self):
        components = self._components()
        assert "BatchOperationItemResult" in components

    def test_batch_operation_item_result_has_status_field(self):
        schema = self._components().get("BatchOperationItemResult", {})
        props = schema.get("properties", {})
        assert "status" in props

    def test_batch_operation_type_enum_exists(self):
        components = self._components()
        assert "BatchOperationType" in components

    def test_batch_operation_type_enum_values(self):
        schema = self._components().get("BatchOperationType", {})
        enum_values = schema.get("enum", [])
        assert "execute" in enum_values
        assert "cancel" in enum_values
        assert "retry" in enum_values

    def test_target_status_enum_exists(self):
        components = self._components()
        assert "TargetStatus" in components

    def test_target_status_enum_values(self):
        schema = self._components().get("TargetStatus", {})
        enum_values = schema.get("enum", [])
        assert "ACTIVE" in enum_values
        assert "PAUSED" in enum_values
        assert "ARCHIVED" in enum_values
        assert "ERROR" in enum_values


# ---------------------------------------------------------------------------
# Enum validation (live endpoint)
# ---------------------------------------------------------------------------

class TestEnumValidation:
    def test_invalid_status_enum_rejected_by_schema(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = client.put(
            f"/api/v1/ingestion/targets/{t.id}",
            json={"status": "FLYING"},
        )
        assert resp.status_code == 422

    def test_invalid_batch_operation_enum_rejected(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        # Send raw JSON with invalid enum to bypass Pydantic client-side validation
        resp = client.post(
            "/api/v1/ingestion/jobs/batch",
            json={"operation": "teleport", "target_ids": [str(t.id)]},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Generated TypeScript types
# ---------------------------------------------------------------------------

class TestGeneratedTypeScript:
    def test_ts_file_contains_update_target_request(self):
        ts = _get_generated_ts()
        assert "UpdateTargetRequest" in ts, (
            "UpdateTargetRequest missing from generated l1/index.ts"
        )

    def test_ts_file_contains_batch_operation_request(self):
        ts = _get_generated_ts()
        assert "BatchOperationRequest" in ts

    def test_ts_file_contains_batch_operation_response(self):
        ts = _get_generated_ts()
        assert "BatchOperationResponse" in ts

    def test_ts_file_contains_batch_operation_item_result(self):
        ts = _get_generated_ts()
        assert "BatchOperationItemResult" in ts

    def test_ts_file_contains_target_put_operation(self):
        ts = _get_generated_ts()
        assert "update_target_api_v1_ingestion_targets__target_id__put" in ts

    def test_ts_file_contains_jobs_batch_post_operation(self):
        ts = _get_generated_ts()
        assert "batch_operation_api_v1_ingestion_jobs_batch_post" in ts

    def test_ts_path_names_match_backend_openapi_paths(self):
        """Verify the TS path strings match the actual OpenAPI paths."""
        ts = _get_generated_ts()
        schema = _get_schema()
        paths = schema.get("paths", {})

        batch_path = next((p for p in paths if "jobs/batch" in p), None)
        target_path = next((p for p in paths if "targets/{target_id}" in p), None)

        assert batch_path is not None
        assert target_path is not None

        # The TS file should contain the exact path strings
        assert batch_path in ts, f"Path {batch_path!r} not found in generated TS"
        assert target_path in ts, f"Path {target_path!r} not found in generated TS"
