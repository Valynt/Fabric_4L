#!/usr/bin/env python3
"""Validate the root schema-contract command surface without mutating artifacts.

This gate is intentionally static: it validates committed OpenAPI contracts,
JSON Schema contracts, and Layer 4 tool manifests without regenerating OpenAPI
or applying migrations. Root pnpm aliases use this script as the canonical
non-mutating schema status check for local development and CI.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_DIR = REPO_ROOT / "contracts" / "openapi"
JSONSCHEMA_DIR = REPO_ROOT / "contracts" / "jsonschema"
TOOL_MANIFEST_DIR = REPO_ROOT / "contracts" / "tool-manifests"


def _load_json(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise ValueError(
            f"{path.relative_to(REPO_ROOT)} is invalid JSON: line {exc.lineno}, column {exc.colno}: {exc.msg}"
        ) from exc
    if not isinstance(data, dict):
        raise ValueError(f"{path.relative_to(REPO_ROOT)} must contain a JSON object")
    return data


def _validate_openapi() -> int:
    specs = sorted(OPENAPI_DIR.glob("*.json"))
    if not specs:
        raise ValueError("No OpenAPI contracts found under contracts/openapi")

    for spec in specs:
        document = _load_json(spec)
        if not str(document.get("openapi", "")).startswith("3."):
            raise ValueError(
                f"{spec.relative_to(REPO_ROOT)} must declare an OpenAPI 3.x version"
            )
        paths = document.get("paths")
        if not isinstance(paths, dict) or not paths:
            raise ValueError(
                f"{spec.relative_to(REPO_ROOT)} must define a non-empty paths object"
            )
        schemas = document.get("components", {}).get("schemas", {})
        if not isinstance(schemas, dict):
            raise ValueError(
                f"{spec.relative_to(REPO_ROOT)} components.schemas must be an object when present"
            )
    print(f"Validated {len(specs)} OpenAPI contract artifact(s).")
    return len(specs)


def _validate_jsonschemas() -> int:
    schemas = sorted(JSONSCHEMA_DIR.glob("*.json"))
    if not schemas:
        raise ValueError("No JSON Schema contracts found under contracts/jsonschema")

    for schema in schemas:
        document = _load_json(schema)
        jsonschema.Draft202012Validator.check_schema(document)
    print(f"Validated {len(schemas)} JSON Schema contract artifact(s).")
    return len(schemas)


def _validate_tool_manifests() -> int:
    manifests = sorted(TOOL_MANIFEST_DIR.glob("*.json"))
    if not manifests:
        raise ValueError("No tool manifests found under contracts/tool-manifests")

    for manifest in manifests:
        document = _load_json(manifest)
        missing = [
            field
            for field in ("$schema", "name", "version", "description", "parameters")
            if field not in document
        ]
        if missing:
            raise ValueError(
                f"{manifest.relative_to(REPO_ROOT)} missing required field(s): {', '.join(missing)}"
            )
        parameters = document["parameters"]
        if not isinstance(parameters, dict) or parameters.get("type") != "object":
            raise ValueError(
                f"{manifest.relative_to(REPO_ROOT)} parameters must be a JSON object schema"
            )
        if not isinstance(parameters.get("properties"), dict):
            raise ValueError(
                f"{manifest.relative_to(REPO_ROOT)} parameters.properties must be an object"
            )
        required = parameters.get("required", [])
        if required is not None and not isinstance(required, list):
            raise ValueError(
                f"{manifest.relative_to(REPO_ROOT)} parameters.required must be a list when present"
            )
        missing_properties = sorted(set(required or []) - set(parameters["properties"]))
        if missing_properties:
            raise ValueError(
                f"{manifest.relative_to(REPO_ROOT)} required fields missing from properties: {', '.join(missing_properties)}"
            )
        jsonschema.Draft202012Validator.check_schema(parameters)
    print(f"Validated {len(manifests)} tool manifest contract artifact(s).")
    return len(manifests)


def main() -> int:
    try:
        _validate_openapi()
        _validate_jsonschemas()
        _validate_tool_manifests()
    except ValueError as exc:
        print(
            f"[FAIL] Schema contract surface validation failed: {exc}", file=sys.stderr
        )
        return 1

    print("[PASS] Schema contract surface validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
