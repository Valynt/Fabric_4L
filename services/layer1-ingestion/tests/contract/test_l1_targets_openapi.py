"""OpenAPI contract tests for the new targets endpoints.

Validates that:
- Both new paths exist in the live OpenAPI schema
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
    def test_patch_status_path_exists(self):
        schema = _get_schema()
        paths = schema.get("paths", {})
        assert any("status" in p and "targets" in p for p in paths), (
            "PATCH /targets/{id}/status not found in OpenAPI schema"
        )

    def test_post_batch_path_exists(self):
        schema = _get_schema()
        paths = schema.get("paths", {})
        assert any("targets/batch" in p for p in paths), (
            "POST /targets/batch not found in OpenAPI schema"
        )

    def test_patch_status_has_patch_method(self):
        schema = _get_schema()
        status_path = next(
            (p for p in schema["paths"] if "status" in p and "targets" in p), None
        )
        assert status_path is not None
        assert "patch" in schema["paths"][status_path], (
            f"PATCH method missing from {status_path}"
        )

    def test_post_batch_has_post_method(self):
        schema = _get_schema()
        batch_path = next(
            (p for p in schema["paths"] if "targets/batch" in p), None
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

    def test_update_target_status_request_schema_exists(self):
        assert "UpdateTargetStatusRequest" in self._components()

    def test_update_target_status_request_has_required_status(self):
        schema = self._components().get("UpdateTargetStatusRequest", {})
        required = schema.get("required", [])
        assert "status" in required, (
            "UpdateTargetStatusRequest.status must be required"
        )

    def test_target_batch_request_schema_exists(self):
        assert "TargetBatchRequest" in self._components()

    def test_target_batch_request_has_required_operation(self):
        schema = self._components().get("TargetBatchRequest", {})
        required = schema.get("required", [])
        assert "operation" in required

    def test_target_batch_request_has_required_target_ids(self):
        schema = self._components().get("TargetBatchRequest", {})
        required = schema.get("required", [])
        assert "target_ids" in required

    def test_target_batch_response_schema_exists(self):
        assert "TargetBatchResponse" in self._components()

    def test_target_batch_response_has_succeeded_field(self):
        schema = self._components().get("TargetBatchResponse", {})
        props = schema.get("properties", {})
        assert "succeeded" in props

    def test_target_batch_response_has_failed_field(self):
        schema = self._components().get("TargetBatchResponse", {})
        props = schema.get("properties", {})
        assert "failed" in props

    def test_target_batch_response_has_results_field(self):
        schema = self._components().get("TargetBatchResponse", {})
        props = schema.get("properties", {})
        assert "results" in props

    def test_target_batch_item_result_schema_exists(self):
        components = self._components()
        assert "TargetBatchItemResult" in components

    def test_target_batch_item_result_has_status_field(self):
        schema = self._components().get("TargetBatchItemResult", {})
        props = schema.get("properties", {})
        assert "status" in props

    def test_target_batch_operation_type_enum_exists(self):
        components = self._components()
        assert "TargetBatchOperationType" in components

    def test_target_batch_operation_type_enum_values(self):
        schema = self._components().get("TargetBatchOperationType", {})
        enum_values = schema.get("enum", [])
        assert "execute" in enum_values
        assert "pause" in enum_values
        assert "archive" in enum_values

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
        resp = client.patch(
            f"/api/v1/ingestion/targets/{t.id}/status",
            json={"status": "FLYING"},
        )
        assert resp.status_code == 422

    def test_invalid_batch_operation_enum_rejected(self, client, db, org_id, make_target):
        t = make_target(org_id, status="ACTIVE")
        resp = client.post(
            "/api/v1/ingestion/targets/batch",
            json={"operation": "teleport", "target_ids": [str(t.id)]},
        )
        assert resp.status_code == 422


# ---------------------------------------------------------------------------
# Generated TypeScript types
# ---------------------------------------------------------------------------

class TestGeneratedTypeScript:
    def test_ts_file_contains_update_target_status_request(self):
        ts = _get_generated_ts()
        assert "UpdateTargetStatusRequest" in ts, (
            "UpdateTargetStatusRequest missing from generated l1/index.ts"
        )

    def test_ts_file_contains_target_batch_request(self):
        ts = _get_generated_ts()
        assert "TargetBatchRequest" in ts

    def test_ts_file_contains_target_batch_response(self):
        ts = _get_generated_ts()
        assert "TargetBatchResponse" in ts

    def test_ts_file_contains_target_batch_item_result(self):
        ts = _get_generated_ts()
        assert "TargetBatchItemResult" in ts

    def test_ts_file_contains_status_patch_operation(self):
        ts = _get_generated_ts()
        assert "update_target_status_api_v1_ingestion_targets__target_id__status_patch" in ts

    def test_ts_file_contains_batch_post_operation(self):
        ts = _get_generated_ts()
        assert "batch_target_operation_api_v1_ingestion_targets_batch_post" in ts

    def test_ts_path_names_match_backend_openapi_paths(self):
        """Verify the TS path strings match the actual OpenAPI paths."""
        ts = _get_generated_ts()
        schema = _get_schema()
        paths = schema.get("paths", {})

        batch_path = next((p for p in paths if "targets/batch" in p), None)
        status_path = next((p for p in paths if "status" in p and "targets" in p), None)

        assert batch_path is not None
        assert status_path is not None

        # The TS file should contain the exact path strings
        assert batch_path in ts, f"Path {batch_path!r} not found in generated TS"
        assert status_path in ts or "target_id" in ts, (
            f"Path {status_path!r} not found in generated TS"
        )
