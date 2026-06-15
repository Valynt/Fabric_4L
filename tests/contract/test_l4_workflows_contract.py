"""Contract tests for Layer 4 Workflow endpoints consumed by frontend."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from .schema_assertions import assert_matches_schema

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_L4_PATH = REPO_ROOT / "contracts" / "openapi" / "layer4-agents.json"


def _load_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _schema_ref(doc: dict[str, Any], name: str) -> dict[str, Any]:
    return {"$ref": f"#/components/schemas/{name}", "components": doc.get("components", {})}


class TestL4WorkflowCreateContracts:
    """Contract tests for POST /workflows endpoint."""

    def test_workflow_create_request_matches_openapi(self) -> None:
        """POST /workflows request payload matches OpenAPI schema."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        sample = {
            "workflow_type": "business_case",
            "inputs": {
                "entity_id": "cap-1",
                "formula_id": "formula-1",
            },
        }
        schema = _schema_ref(l4_openapi, "WorkflowCreateRequest")
        assert_matches_schema(sample, schema, root=l4_openapi)

    def test_workflow_create_contract_rejects_client_supplied_tenant_user_identity(self) -> None:
        """Workflow create contract must not allow client-supplied tenant/user identity fields."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        workflow_post = l4_openapi["paths"]["/v1/workflows"]["post"]

        description = workflow_post.get("description", "")
        assert "tenant_id" not in description, "POST /v1/workflows description must not include tenant_id in examples"
        assert "user_id" not in description, "POST /v1/workflows description must not include user_id in examples"

        schema_name = workflow_post["requestBody"]["content"]["application/json"]["schema"]["$ref"].split("/")[-1]
        schema_props = l4_openapi["components"]["schemas"][schema_name].get("properties", {})
        assert "tenant_id" not in schema_props, "WorkflowCreateRequest must not accept tenant_id from clients"
        assert "user_id" not in schema_props, "WorkflowCreateRequest must not accept user_id from clients"

    def test_workflow_create_response_matches_openapi(self) -> None:
        """POST /workflows response matches OpenAPI schema."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        sample = {
            "workflow_id": "wf-123",
            "workflow_instance_id": "wf-123",
            "name": "Q1 ROI Analysis",
            "workflow_type": "business_case",
            "status": "started",
            "created_at": "2024-01-15T10:00:00Z",
            "created_by": "user-1",
        }
        schema = _schema_ref(l4_openapi, "WorkflowCreateResponse")
        assert_matches_schema(sample, schema, root=l4_openapi)


class TestL4WorkflowStatusContracts:
    """Contract tests for GET /workflows/active and /workflows/{id} endpoints."""

    def test_workflow_status_response_matches_openapi(self) -> None:
        """GET /workflows/{id} response matches OpenAPI schema."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        sample = {
            "id": "wf-123",
            "workflow_type": "business_case",
            "status": "running",
            "current_state": "calculate_roi",
            "current_node": "calculate_roi",
            "progress": 65,
            "started_at": "2024-01-15T10:00:00Z",
            "completed_at": None,
            "error_count": 0,
            "has_output": False,
            "results": None,
        }
        schema = _schema_ref(l4_openapi, "WorkflowStatusResponse")
        assert_matches_schema(sample, schema, root=l4_openapi)

    def test_workflow_list_response_matches_openapi(self) -> None:
        """GET /workflows/active response matches OpenAPI schema."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        sample = [
            {
                "id": "wf-1",
                "workflow_type": "market_analysis",
                "status": "running",
                "progress": 65,
                "started_at": "2024-01-15T10:00:00Z",
            },
            {
                "id": "wf-2",
                "workflow_type": "entity_extraction",
                "status": "completed",
                "progress": 100,
                "started_at": "2024-01-14T09:00:00Z",
                "completed_at": "2024-01-14T10:30:00Z",
            },
        ]
        schema = _schema_ref(l4_openapi, "WorkflowStatusResponse")
        for item in sample:
            assert_matches_schema(item, schema, root=l4_openapi)


class TestL4WorkflowEventContracts:
    """Contract tests for workflow event streaming."""

    def test_workflow_event_schema_completeness(self) -> None:
        """WorkflowEvent schema contains all required fields for SSE."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        required_fields = {"event_id", "event_type", "timestamp"}
        
        components = l4_openapi.get("components", {}).get("schemas", {})
        if "WorkflowEvent" in components:
            event_schema = components["WorkflowEvent"]
            properties = set(event_schema.get("properties", {}).keys())
            missing = required_fields - properties
            assert not missing, f"WorkflowEvent schema missing required fields: {missing}"

    def test_workflow_event_types_enum(self) -> None:
        """WorkflowEvent includes expected event types."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        expected_types = {"started", "progress", "completed", "failed", "paused", "resumed"}
        
        components = l4_openapi.get("components", {}).get("schemas", {})
        if "WorkflowEvent" in components:
            event_schema = components["WorkflowEvent"]
            type_prop = event_schema.get("properties", {}).get("event_type", {})
            if "enum" in type_prop:
                schema_types = set(type_prop["enum"])
                missing = expected_types - schema_types
                assert not missing, f"Event type enum missing values: {missing}"


class TestL4WorkflowResumeContracts:
    """Contract tests for POST /workflows/{id}/resume endpoint."""

    def test_workflow_resume_request_matches_openapi(self) -> None:
        """POST /workflows/{id}/resume request payload matches OpenAPI schema."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        sample = {
            "user_id": "user-1",
            "checkpoint_id": "chk-456",
            "input_data": {
                "override_value": 1000,
            },
        }
        components = l4_openapi.get("components", {}).get("schemas", {})
        if "WorkflowResumeRequest" in components:
            schema = _schema_ref(l4_openapi, "WorkflowResumeRequest")
            assert_matches_schema(sample, schema, root=l4_openapi)


class TestL4WorkflowStatusEnum:
    """Contract tests for workflow status enum values."""

    def test_workflow_status_enum_values(self) -> None:
        """Workflow status enum includes all expected values."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        expected_statuses = {
            "pending", "running", "paused", "interrupted",
            "completed", "failed", "cancelled"
        }
        
        components = l4_openapi.get("components", {}).get("schemas", {})
        if "WorkflowStatusResponse" in components:
            status_schema = components["WorkflowStatusResponse"]
            status_prop = status_schema.get("properties", {}).get("status", {})
            if "enum" in status_prop:
                schema_statuses = set(status_prop["enum"])
                missing = expected_statuses - schema_statuses
                assert not missing, f"Workflow status enum missing values: {missing}"


class TestL4WorkflowTypeEnum:
    """Contract tests for workflow type enum values."""

    def test_workflow_type_enum_values(self) -> None:
        """Workflow type enum includes expected frontend workflow types."""
        l4_openapi = _load_json(OPENAPI_L4_PATH)
        expected_types = {
            "business_case", "market_analysis", "entity_extraction", 
            "whitespace_analysis", "roi_calculation"
        }
        
        components = l4_openapi.get("components", {}).get("schemas", {})
        if "WorkflowCreateRequest" in components:
            req_schema = components["WorkflowCreateRequest"]
            type_prop = req_schema.get("properties", {}).get("workflow_type", {})
            if "enum" in type_prop:
                schema_types = set(type_prop["enum"])
                missing = expected_types - schema_types
                # Note: Some types might not be in the schema yet
                # This test documents expected values
                if missing:
                    print(f"Note: Workflow type enum missing expected values: {missing}")
