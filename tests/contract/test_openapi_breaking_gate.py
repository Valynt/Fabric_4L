from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest

SCRIPT_PATH = (
    Path(__file__).resolve().parents[2] / "scripts" / "ci" / "openapi_breaking_gate.py"
)
pytestmark = pytest.mark.contract_static_no_service

spec = importlib.util.spec_from_file_location("openapi_breaking_gate", SCRIPT_PATH)
assert spec and spec.loader
openapi_breaking_gate = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = openapi_breaking_gate
spec.loader.exec_module(openapi_breaking_gate)


def _operation(
    request_schema: dict | None = None,
    response_schema: dict | None = None,
    security=None,
) -> dict:
    operation: dict = {"responses": {"200": {"description": "OK"}}}
    if request_schema is not None:
        operation["requestBody"] = {
            "content": {"application/json": {"schema": request_schema}}
        }
    if response_schema is not None:
        operation["responses"]["200"]["content"] = {
            "application/json": {"schema": response_schema}
        }
    if security is not None:
        operation["security"] = security
    return operation


def _spec(operation: dict) -> dict:
    return {
        "openapi": "3.1.0",
        "paths": {"/widgets": {"post": operation}},
        "components": {"schemas": {}},
    }


def test_detects_removed_method_and_auth_change_without_approval() -> None:
    before = {"demo.json": _spec(_operation(security=[{"bearerAuth": []}]))}
    after = {
        "demo.json": {
            "openapi": "3.1.0",
            "paths": {"/widgets": {}},
            "components": {"schemas": {}},
        }
    }

    findings = openapi_breaking_gate._compare_specs(after, before, approvals={})

    assert [(finding.category, finding.approved) for finding in findings] == [
        ("removed_method", False)
    ]
    assert findings[0].approval_key == "POST /widgets"


def test_deprecation_record_approves_matching_endpoint_break() -> None:
    before = {"demo.json": _spec(_operation(security=[{"bearerAuth": []}]))}
    after = {"demo.json": _spec(_operation(security=[]))}

    findings = openapi_breaking_gate._compare_specs(
        after,
        before,
        approvals={
            "POST /widgets": "contracts/deprecations/generated-contract-deprecations.json"
        },
    )

    assert len(findings) == 1
    assert findings[0].category == "auth_security_contract_change"
    assert findings[0].approved is True


def test_detects_required_request_addition_removed_response_field_and_enum_removal() -> (
    None
):
    before_schema = {
        "type": "object",
        "required": ["status"],
        "properties": {
            "status": {"type": "string", "enum": ["draft", "active", "archived"]},
            "description": {"type": "string"},
        },
    }
    after_schema = {
        "type": "object",
        "required": ["status", "tenant_id"],
        "properties": {
            "status": {"type": "string", "enum": ["draft", "active"]},
            "tenant_id": {"type": "string"},
        },
    }
    before = {
        "demo.json": _spec(
            _operation(request_schema=before_schema, response_schema=before_schema)
        )
    }
    after = {
        "demo.json": _spec(
            _operation(request_schema=after_schema, response_schema=after_schema)
        )
    }

    categories = [
        finding.category
        for finding in openapi_breaking_gate._compare_specs(after, before, approvals={})
    ]

    assert "enum_value_removal" in categories
    assert "required_field_addition" in categories
    assert "removed_response_field" in categories


def test_detects_error_response_contract_drift() -> None:
    before_operation = {
        "responses": {
            "400": {
                "description": "Bad request",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "required": ["code", "message"],
                            "properties": {
                                "code": {"type": "string"},
                                "message": {"type": "string"},
                            },
                        }
                    }
                },
            }
        }
    }
    after_operation = {
        "responses": {
            "400": {
                "description": "Bad request",
                "content": {
                    "application/json": {
                        "schema": {
                            "type": "object",
                            "properties": {"message": {"type": "string"}},
                        }
                    }
                },
            }
        }
    }

    findings = openapi_breaking_gate._compare_specs(
        {"demo.json": _spec(after_operation)},
        {"demo.json": _spec(before_operation)},
        approvals={},
    )

    assert [finding.category for finding in findings] == [
        "error_response_contract_drift"
    ]
