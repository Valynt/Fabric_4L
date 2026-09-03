"""Lightweight JSON-schema-like assertions for contract tests.

This avoids third-party runtime dependencies in CI while still validating against
contracts/jsonschema and contracts/openapi artifacts.
"""

from __future__ import annotations

from typing import Any


class SchemaValidationError(AssertionError):
    """Raised when payload does not satisfy schema constraints."""


TYPE_MAP = {
    "object": dict,
    "array": list,
    "string": str,
    "number": (int, float),
    "integer": int,
    "boolean": bool,
}


def assert_matches_schema(instance: Any, schema: dict[str, Any], *, root: dict[str, Any] | None = None, path: str = "$") -> None:
    """Assert an instance satisfies a JSON Schema subset used in repo contracts."""
    root_schema = root or schema

    if "$ref" in schema:
        ref = schema["$ref"]
        if not isinstance(ref, str) or not ref.startswith("#/"):
            raise SchemaValidationError(f"{path}: unsupported $ref format {ref!r}")
        target = root_schema
        for part in ref[2:].split("/"):
            if not isinstance(target, dict) or part not in target:
                raise SchemaValidationError(f"{path}: unresolved $ref {ref}")
            target = target[part]
        assert_matches_schema(instance, target, root=root_schema, path=path)
        return

    if "allOf" in schema:
        for sub in schema["allOf"]:
            assert_matches_schema(instance, sub, root=root_schema, path=path)

    if "anyOf" in schema:
        errors: list[str] = []
        for sub in schema["anyOf"]:
            try:
                assert_matches_schema(instance, sub, root=root_schema, path=path)
                break
            except SchemaValidationError as exc:
                errors.append(str(exc))
        else:
            raise SchemaValidationError(f"{path}: failed anyOf validation ({'; '.join(errors)})")

    expected_type = schema.get("type")
    if isinstance(expected_type, list):
        matched = False
        for one in expected_type:
            expected_python = TYPE_MAP.get(one)
            if expected_python and isinstance(instance, expected_python):
                matched = True
                break
            if one == "null" and instance is None:
                matched = True
                break
        if not matched:
            raise SchemaValidationError(f"{path}: expected one of types {expected_type}, got {type(instance).__name__}")
    elif expected_type:
        expected_python = TYPE_MAP.get(expected_type)
        if expected_python and not isinstance(instance, expected_python):
            raise SchemaValidationError(
                f"{path}: expected type {expected_type}, got {type(instance).__name__}"
            )

    if "enum" in schema and instance not in schema["enum"]:
        raise SchemaValidationError(f"{path}: value {instance!r} not in enum {schema['enum']!r}")

    if isinstance(instance, (int, float)) and not isinstance(instance, bool):
        minimum = schema.get("minimum")
        maximum = schema.get("maximum")
        if minimum is not None and instance < minimum:
            raise SchemaValidationError(f"{path}: {instance} < minimum {minimum}")
        if maximum is not None and instance > maximum:
            raise SchemaValidationError(f"{path}: {instance} > maximum {maximum}")

    if isinstance(instance, str):
        min_len = schema.get("minLength")
        max_len = schema.get("maxLength")
        if min_len is not None and len(instance) < min_len:
            raise SchemaValidationError(f"{path}: string shorter than minLength {min_len}")
        if max_len is not None and len(instance) > max_len:
            raise SchemaValidationError(f"{path}: string longer than maxLength {max_len}")

    if isinstance(instance, dict):
        required = schema.get("required", [])
        for key in required:
            if key not in instance:
                raise SchemaValidationError(f"{path}: missing required property {key!r}")

        properties: dict[str, Any] = schema.get("properties", {})
        for key, value in instance.items():
            if key in properties:
                assert_matches_schema(
                    value,
                    properties[key],
                    root=root_schema,
                    path=f"{path}.{key}",
                )

        if schema.get("additionalProperties") is False:
            unknown = set(instance) - set(properties)
            if unknown:
                raise SchemaValidationError(f"{path}: additional properties not allowed: {sorted(unknown)}")

    if isinstance(instance, list) and "items" in schema:
        item_schema = schema["items"]
        for idx, item in enumerate(instance):
            assert_matches_schema(item, item_schema, root=root_schema, path=f"{path}[{idx}]")
