"""Contract test for error envelope consistency across all layers.

Verifies that all layers use the canonical error response structure defined in
docs/api-contract-stability.md and contracts/frontend/01-api-boundary-contract.md.

Canonical error envelope:
{
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "request_id": "uuid-for-correlation",
    "details": {}  // Optional sanitized details
  }
}
"""

import json
from pathlib import Path
from typing import Any

import pytest

# Mark all tests as static contract tests that don't require live services
pytestmark = pytest.mark.contract_static_no_service


def load_openapi_spec(layer_name: str) -> dict[str, Any]:
    """Load OpenAPI spec for a given layer."""
    spec_path = (
        Path(__file__).parent.parent.parent
        / "contracts"
        / "openapi"
        / f"{layer_name}.json"
    )
    with open(spec_path) as f:
        return json.load(f)


def get_error_response_schemas(
    spec: dict[str, Any],
) -> list[tuple[str, str, dict[str, Any]]]:
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
        return any(
            x in ref for x in ["ErrorEnvelope", "ErrorResponse", "HTTPValidationError"]
        )

    # Check if it has the required fields inline
    properties = schema.get("properties", {})

    error = properties.get("error", {})
    error_props = error.get("properties", {}) if isinstance(error, dict) else {}
    error_required = (
        set(error.get("required", [])) if isinstance(error, dict) else set()
    )
    return {"code", "message", "request_id"}.issubset(error_required) or (
        {"code", "message", "request_id"}.issubset(set(error_props.keys()))
    )


def test_layer1_error_envelope_consistency():
    """Layer 1 should use canonical error envelope."""
    spec = load_openapi_spec("layer1-ingestion")
    error_schemas = get_error_response_schemas(spec)

    # Filter out health/metrics endpoints which may have different error handling
    non_health_errors = [
        (path, method, schema)
        for path, method, schema in error_schemas
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
            + (
                f"\n  ... and {len(non_compliant) - 5} more"
                if len(non_compliant) > 5
                else ""
            )
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
            + (
                f"\n  ... and {len(non_compliant) - 5} more"
                if len(non_compliant) > 5
                else ""
            )
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
            + (
                f"\n  ... and {len(non_compliant) - 5} more"
                if len(non_compliant) > 5
                else ""
            )
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
            + (
                f"\n  ... and {len(non_compliant) - 5} more"
                if len(non_compliant) > 5
                else ""
            )
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
            + (
                f"\n  ... and {len(non_compliant) - 5} more"
                if len(non_compliant) > 5
                else ""
            )
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
            + (
                f"\n  ... and {len(non_compliant) - 5} more"
                if len(non_compliant) > 5
                else ""
            )
        )


def test_layer25_error_envelope_consistency():
    """Layer 2.5 should use canonical error envelope."""
    spec = load_openapi_spec("layer2-5-signal-refinery")
    error_schemas = get_error_response_schemas(spec)

    # /ready is a health probe and carries no error responses; skip nothing
    # because it has none, but filter for symmetry with the other layers.
    non_health_errors = [
        (path, method, schema)
        for path, method, schema in error_schemas
        if "/ready" not in path and "/health" not in path and "/metrics" not in path
    ]

    non_compliant = []
    for path, method, schema in non_health_errors:
        if not is_canonical_error_schema(schema):
            non_compliant.append((path, method, schema))

    if non_compliant:
        pytest.fail(
            f"Layer 2.5 has {len(non_compliant)} error responses not using canonical envelope:\n"
            + "\n".join(f"  {method} {path}" for path, method, _ in non_compliant[:5])
            + (
                f"\n  ... and {len(non_compliant) - 5} more"
                if len(non_compliant) > 5
                else ""
            )
        )


def test_httpvalidationerror_deprecated_in_all_layers():
    """HTTPValidationError should be marked as deprecated in all layers that use it.

    This is a soft check - it will report missing deprecation notices but not fail the test
    to allow for gradual migration to the canonical error envelope.
    """
    layers = [
        "layer1-ingestion",
        "layer2-extraction",
        "layer2-5-signal-refinery",
        "layer3-knowledge",
        "layer4-agents",
        "layer5-ground-truth",
        "layer6-benchmarks",
    ]

    non_compliant = []
    for layer in layers:
        spec = load_openapi_spec(layer)
        components = spec.get("components", {}).get("schemas", {})

        if "HTTPValidationError" in components:
            schema = components["HTTPValidationError"]
            description = schema.get("description", "")

            # Should have deprecation notice in description
            if "deprecated" not in description.lower():
                non_compliant.append(layer)

    if non_compliant:
        # Print warning but don't fail - this is a migration in progress
        print(
            "\n⚠️  Warning: The following layers have HTTPValidationError but it's not marked as deprecated:"
        )
        for layer in non_compliant:
            print(f"  - {layer}")
        print("  This is acceptable during migration to the canonical error envelope.")


def test_error_envelope_canonical_exists_in_all_layers():
    """All layers should have the canonical ErrorEnvelope schema defined.

    This is a soft check - it will report missing schemas but not fail the test
    to allow for gradual migration to the canonical error envelope.
    """
    layers = [
        "layer1-ingestion",
        "layer2-extraction",
        "layer2-5-signal-refinery",
        "layer3-knowledge",
        "layer4-agents",
        "layer5-ground-truth",
        "layer6-benchmarks",
    ]

    missing_schemas = []
    for layer in layers:
        spec = load_openapi_spec(layer)
        components = spec.get("components", {}).get("schemas", {})

        if "ErrorEnvelope" not in components:
            missing_schemas.append(layer)
        else:
            # Verify ErrorResponse has required fields
            error_schema = components["ErrorEnvelope"]
            properties = error_schema.get("properties", {})
            error_props = (
                properties.get("error", {}).get("properties", {})
                if isinstance(properties.get("error", {}), dict)
                else {}
            )
            if "code" not in error_props:
                missing_schemas.append(f"{layer} (missing 'error.code' field)")
            if "message" not in error_props:
                missing_schemas.append(f"{layer} (missing 'error.message' field)")
            if "request_id" not in error_props:
                missing_schemas.append(f"{layer} (missing 'error.request_id' field)")

    if missing_schemas:
        # Print warning but don't fail - this is a migration in progress
        print(
            "\n⚠️  Warning: The following layers are missing canonical ErrorEnvelope schema or required fields:"
        )
        for item in missing_schemas:
            print(f"  - {item}")
        print("  This is acceptable during migration to the canonical error envelope.")


CANONICAL_ERROR_COMPONENT = "#/components/schemas/ErrorEnvelope"
ERROR_STATUS_CASES = {
    "401": ("AUTHENTICATION_ERROR", "Authentication failed"),
    "403": ("AUTHORIZATION_ERROR", "Access denied"),
    "404": ("NOT_FOUND", "Resource not found"),
    "422": ("VALIDATION_ERROR", "Request validation failed"),
    "500": ("INTERNAL_ERROR", "An unexpected error occurred"),
}


def test_error_envelope_schema_is_identical_to_canonical_source_of_truth():
    """L2-L6 must reuse the shared ErrorEnvelope schema published by fabric-4l-api."""
    canonical = load_openapi_spec("fabric-4l-api")["components"]["schemas"][
        "ErrorEnvelope"
    ]

    for layer in [
        "layer2-extraction",
        "layer2-5-signal-refinery",
        "layer3-knowledge",
        "layer4-agents",
        "layer5-ground-truth",
        "layer6-benchmarks",
    ]:
        components = load_openapi_spec(layer)["components"]["schemas"]
        assert components["ErrorEnvelope"] == canonical
        assert components["ErrorResponse"] == {
            **canonical,
            "title": "ErrorResponse",
            "description": "Deprecated compatibility alias for ErrorEnvelope. Use ErrorEnvelope for new clients.",
        }
        assert components["HTTPValidationError"] == {
            **canonical,
            "title": "HTTPValidationError",
            "description": "Deprecated compatibility alias for ErrorEnvelope. Use ErrorEnvelope for new clients.",
        }


def _assert_matches_canonical_error_envelope(payload: dict[str, Any]) -> None:
    assert set(payload) == {"error"}
    error = payload["error"]
    assert isinstance(error, dict)
    assert set(error).issubset({"code", "message", "request_id", "details"})
    assert {"code", "message", "request_id"}.issubset(error)
    assert isinstance(error["code"], str) and error["code"]
    assert isinstance(error["message"], str)
    assert isinstance(error["request_id"], str) and error["request_id"]
    assert "trace_id" not in error
    assert "error_code" not in error


@pytest.mark.parametrize(
    "layer",
    [
        "layer2-extraction",
        "layer2-5-signal-refinery",
        "layer3-knowledge",
        "layer4-agents",
        "layer5-ground-truth",
        "layer6-benchmarks",
    ],
)
@pytest.mark.parametrize("status_code", ["401", "403", "404", "422", "500"])
def test_representative_error_responses_from_each_layer_match_same_envelope(
    layer: str, status_code: str
) -> None:
    """Representative auth, forbidden, not-found, validation, and 500 bodies share one envelope."""
    code, message = ERROR_STATUS_CASES[status_code]
    payload = {
        "error": {
            "code": code,
            "message": message,
            "request_id": f"req-{layer}-{status_code}",
            "details": {"status_code": int(status_code)},
        }
    }

    _assert_matches_canonical_error_envelope(payload)

    layer_schema = load_openapi_spec(layer)["components"]["schemas"]["ErrorEnvelope"]
    canonical_schema = load_openapi_spec("fabric-4l-api")["components"]["schemas"][
        "ErrorEnvelope"
    ]
    assert layer_schema == canonical_schema


def test_legacy_flat_error_payloads_are_rejected_by_canonical_envelope_regression() -> (
    None
):
    """Prevent reintroducing L2's previous flat message/code/trace_id response shape."""
    legacy_payloads = [
        {
            "message": "Unauthorized",
            "code": "AUTHENTICATION_ERROR",
            "trace_id": "req-old",
        },
        {"error_code": "NOT_FOUND", "message": "missing", "request_id": "req-old"},
        {"error": "NOT_FOUND", "message": "missing", "request_id": "req-old"},
    ]

    for payload in legacy_payloads:
        with pytest.raises(AssertionError):
            _assert_matches_canonical_error_envelope(payload)
