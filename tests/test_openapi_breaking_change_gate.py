import pytest
from scripts.ci.openapi_breaking_change_gate import compare_specs


def _operation(request_schema=None, response_schema=None, security=None, error_schema=None):
    op = {
        "responses": {
            "200": {
                "description": "ok",
                "content": {"application/json": {"schema": response_schema or {"type": "object"}}},
            },
            "400": {
                "description": "bad request",
                "content": {
                    "application/json": {
                        "schema": error_schema
                        or {
                            "type": "object",
                            "properties": {"detail": {"type": "string"}, "code": {"type": "string"}},
                        }
                    }
                },
            },
        }
    }
    if request_schema is not None:
        op["requestBody"] = {
            "content": {"application/json": {"schema": request_schema}}
        }
    if security is not None:
        op["security"] = security
    return op


@pytest.mark.unit
def test_compare_specs_detects_required_breaking_categories():
    baseline = {
        "openapi": "3.1.0",
        "paths": {
            "/removed": {"get": _operation()},
            "/widgets": {
                "post": _operation(
                    request_schema={
                        "type": "object",
                        "required": ["name"],
                        "properties": {
                            "name": {"type": ["string", "null"]},
                            "mode": {"type": "string", "enum": ["auto", "manual"]},
                            "legacy": {"type": "string"},
                        },
                    },
                    response_schema={
                        "type": "object",
                        "properties": {"id": {"type": "string"}, "status": {"type": "string"}},
                    },
                    security=[{"bearerAuth": []}],
                ),
                "delete": _operation(),
            },
        },
    }
    current = {
        "openapi": "3.1.0",
        "paths": {
            "/widgets": {
                "post": _operation(
                    request_schema={
                        "type": "object",
                        "required": ["name", "mode"],
                        "properties": {
                            "name": {"type": "string"},
                            "mode": {"type": "string", "enum": ["auto"]},
                        },
                    },
                    response_schema={
                        "type": "object",
                        "properties": {"id": {"type": "string"}},
                    },
                    security=[{"oauth2": ["widgets:write"]}],
                    error_schema={
                        "type": "object",
                        "properties": {"detail": {"type": "string"}},
                    },
                )
            }
        },
    }

    categories = {finding.category for finding in compare_specs("layer-test.json", baseline, current)}

    assert "paths_removed" in categories
    assert "methods_removed" in categories
    assert "request_fields_removed" in categories
    assert "response_fields_removed" in categories
    assert "type_narrowing" in categories
    assert "enum_values_removed" in categories
    assert "auth_security_contract_changed" in categories
    assert "required_fields_added" in categories
    assert "error_response_contract_drift" in categories
