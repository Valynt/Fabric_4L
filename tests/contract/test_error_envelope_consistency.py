"""Contract test for error envelope consistency across all layers.

Verifies that all layers use the canonical error response structure defined in
docs/api-contract-stability.md and contracts/frontend/01-api-boundary-contract.md.

Canonical error envelope:
{
  "message": "Human-readable error message",
  "code": "ERROR_CODE",
  "trace_id": "uuid-for-correlation",
  "details": {}  // Optional sanitized details
}
"""

import json
from pathlib import Path
from typing import Any

import pytest

# Mark all tests as static contract tests (no service dependencies)
pytestmark = pytest.mark.contract_static


def load_openapi_spec(layer_name: str) -> dict[str, Any]:
    """Load OpenAPI spec for a given layer."""
    spec_path = Path(__file__).parent.parent.parent / "contracts" / "openapi" / f"{layer_name}.json"
    with open(spec_path) as f:
        return json.load(f)


def get_error_response_schemas(spec: dict[str, Any]) -> list[tuple[str, str, dict[str, Any]]]:
    """Extract all error response schemas from an OpenAPI spec.
    
    Returns list of (path, method, schema) tuples.
    """
    error_schemas = []
    
    for path, path_item in spec.get("paths", {}).items():
        for method, operation in path_item.items():
            if method not in ["get", "post", "put", "delete", "patch"]:
                continue
                
            for status_code, response in operation.get("responses", {}).items():
                if status_code.startswith("4") or status_code.startswith("5"):
                    content = response.get("content", {}).get("application/json", {})
                    schema = content.get("schema", {})
                    if schema:
                        error_schemas.append((path, method.upper(), schema))
    
    return error_schemas


def is_canonical_error_schema(schema: dict[str, Any]) -> bool:
    """Check if a schema matches the canonical error envelope."""
    # Check if it references the canonical ErrorResponse
    if "$ref" in schema:
        ref = schema["$ref"]
        return "ErrorResponse" in ref or "HTTPValidationError" in ref
    
    # Check if it has the required fields inline
    properties = schema.get("properties", {})
    required = schema.get("required", [])
    
    has_message = "message" in properties
    has_code = "code" in properties
    has_trace_id = "trace_id" in properties
    
    return has_message and has_code and has_trace_id


def test_layer1_error_envelope_consistency():
    """Layer 1 should use canonical error envelope."""
    spec = load_openapi_spec("layer1-ingestion")
    error_schemas = get_error_response_schemas(spec)
    
    # Filter out health/metrics endpoints which may have different error handling
    non_health_errors = [
        (path, method, schema) for path, method, schema in error_schemas
        if "/health" not in path and "/metrics" not in path
    ]
    
    non_compliant = []
    for path, method, schema in non_health_errors:
        if not is_canonical_error_schema(schema):
            non_compliant.append((path, method, schema))
    
    if non_compliant:
        pytest.fail(
            f"Layer 1 has {len(non_compliant)} error responses not using canonical envelope:\n"
            + "\n".join(f"  {method} {path}" for path, method, _ in non_compliant[:5])
            + (f"\n  ... and {len(non_compliant) - 5} more" if len(non_compliant) > 5 else "")
        )


def test_layer2_error_envelope_consistency():
    """Layer 2 should use canonical error envelope."""
    spec = load_openapi_spec("layer2-extraction")
    error_schemas = get_error_response_schemas(spec)
    
    non_compliant = []
    for path, method, schema in error_schemas:
        if not is_canonical_error_schema(schema):
            non_compliant.append((path, method, schema))
    
    if non_compliant:
        pytest.fail(
            f"Layer 2 has {len(non_compliant)} error responses not using canonical envelope:\n"
            + "\n".join(f"  {method} {path}" for path, method, _ in non_compliant[:5])
            + (f"\n  ... and {len(non_compliant) - 5} more" if len(non_compliant) > 5 else "")
        )


def test_layer3_error_envelope_consistency():
    """Layer 3 should use canonical error envelope."""
    spec = load_openapi_spec("layer3-knowledge")
    error_schemas = get_error_response_schemas(spec)
    
    non_compliant = []
    for path, method, schema in error_schemas:
        if not is_canonical_error_schema(schema):
            non_compliant.append((path, method, schema))
    
    if non_compliant:
        pytest.fail(
            f"Layer 3 has {len(non_compliant)} error responses not using canonical envelope:\n"
            + "\n".join(f"  {method} {path}" for path, method, _ in non_compliant[:5])
            + (f"\n  ... and {len(non_compliant) - 5} more" if len(non_compliant) > 5 else "")
        )


def test_layer4_error_envelope_consistency():
    """Layer 4 should use canonical error envelope."""
    spec = load_openapi_spec("layer4-agents")
    error_schemas = get_error_response_schemas(spec)
    
    non_compliant = []
    for path, method, schema in error_schemas:
        if not is_canonical_error_schema(schema):
            non_compliant.append((path, method, schema))
    
    if non_compliant:
        pytest.fail(
            f"Layer 4 has {len(non_compliant)} error responses not using canonical envelope:\n"
            + "\n".join(f"  {method} {path}" for path, method, _ in non_compliant[:5])
            + (f"\n  ... and {len(non_compliant) - 5} more" if len(non_compliant) > 5 else "")
        )


def test_layer5_error_envelope_consistency():
    """Layer 5 should use canonical error envelope."""
    spec = load_openapi_spec("layer5-ground-truth")
    error_schemas = get_error_response_schemas(spec)
    
    non_compliant = []
    for path, method, schema in error_schemas:
        if not is_canonical_error_schema(schema):
            non_compliant.append((path, method, schema))
    
    if non_compliant:
        pytest.fail(
            f"Layer 5 has {len(non_compliant)} error responses not using canonical envelope:\n"
            + "\n".join(f"  {method} {path}" for path, method, _ in non_compliant[:5])
            + (f"\n  ... and {len(non_compliant) - 5} more" if len(non_compliant) > 5 else "")
        )


def test_layer6_error_envelope_consistency():
    """Layer 6 should use canonical error envelope."""
    spec = load_openapi_spec("layer6-benchmarks")
    error_schemas = get_error_response_schemas(spec)
    
    non_compliant = []
    for path, method, schema in error_schemas:
        if not is_canonical_error_schema(schema):
            non_compliant.append((path, method, schema))
    
    if non_compliant:
        pytest.fail(
            f"Layer 6 has {len(non_compliant)} error responses not using canonical envelope:\n"
            + "\n".join(f"  {method} {path}" for path, method, _ in non_compliant[:5])
            + (f"\n  ... and {len(non_compliant) - 5} more" if len(non_compliant) > 5 else "")
        )


def test_httpvalidationerror_deprecated_in_all_layers():
    """HTTPValidationError should be marked as deprecated in all layers that use it."""
    layers = ["layer1-ingestion", "layer2-extraction", "layer3-knowledge", "layer4-agents", "layer5-ground-truth", "layer6-benchmarks"]
    
    for layer in layers:
        spec = load_openapi_spec(layer)
        components = spec.get("components", {}).get("schemas", {})
        
        if "HTTPValidationError" in components:
            schema = components["HTTPValidationError"]
            description = schema.get("description", "")
            
            # Should have deprecation notice in description
            if "deprecated" not in description.lower():
                pytest.fail(
                    f"{layer}: HTTPValidationError schema exists but is not marked as deprecated in description"
                )


def test_error_response_canonical_exists_in_all_layers():
    """All layers should have the canonical ErrorResponse schema defined."""
    layers = ["layer1-ingestion", "layer2-extraction", "layer3-knowledge", "layer4-agents", "layer5-ground-truth", "layer6-benchmarks"]
    
    for layer in layers:
        spec = load_openapi_spec(layer)
        components = spec.get("components", {}).get("schemas", {})
        
        if "ErrorResponse" not in components:
            pytest.fail(f"{layer}: Canonical ErrorResponse schema is not defined in components/schemas")
        
        # Verify ErrorResponse has required fields
        error_schema = components["ErrorResponse"]
        properties = error_schema.get("properties", {})
        required = error_schema.get("required", [])
        
        assert "message" in properties, f"{layer}: ErrorResponse missing 'message' field"
        assert "code" in properties, f"{layer}: ErrorResponse missing 'code' field"
        assert "trace_id" in properties, f"{layer}: ErrorResponse missing 'trace_id' field"
        assert "message" in required, f"{layer}: 'message' not marked as required in ErrorResponse"
        assert "code" in required, f"{layer}: 'code' not marked as required in ErrorResponse"
        assert "trace_id" in required, f"{layer}: 'trace_id' not marked as required in ErrorResponse"
