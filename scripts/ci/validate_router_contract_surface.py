#!/usr/bin/env python3
"""Validate static API routing contract artifacts.

This is a non-mutating companion to the root `pnpm test:router` command. It
checks that committed OpenAPI route surfaces are present for every maintained
layer and that the shared system-route JSON Schema is well-formed. Frontend
routing behavior is covered by the Vitest portion of `pnpm test:router`.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any

import jsonschema

REPO_ROOT = Path(__file__).resolve().parents[2]
OPENAPI_DIR = REPO_ROOT / "contracts" / "openapi"
SYSTEM_ROUTE_SCHEMA = (
    REPO_ROOT / "contracts" / "jsonschema" / "system-route-health.json"
)
REQUIRED_OPENAPI_SPECS = (
    "layer1-ingestion.json",
    "layer2-extraction.json",
    "layer3-knowledge.json",
    "layer4-agents.json",
    "layer5-ground-truth.json",
    "layer6-benchmarks.json",
)


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


def _validate_openapi_routes() -> int:
    route_count = 0
    for name in REQUIRED_OPENAPI_SPECS:
        path = OPENAPI_DIR / name
        if not path.exists():
            raise ValueError(
                f"Missing required OpenAPI route contract: {path.relative_to(REPO_ROOT)}"
            )
        document = _load_json(path)
        paths = document.get("paths")
        if not isinstance(paths, dict) or not paths:
            raise ValueError(
                f"{path.relative_to(REPO_ROOT)} must define a non-empty paths object"
            )
        for route, operations in paths.items():
            if not isinstance(route, str) or not route.startswith("/"):
                raise ValueError(
                    f"{path.relative_to(REPO_ROOT)} has invalid route key: {route!r}"
                )
            if not isinstance(operations, dict) or not operations:
                raise ValueError(
                    f"{path.relative_to(REPO_ROOT)} route {route} must define operations"
                )
        route_count += len(paths)
    print(
        f"Validated {route_count} API route contract path(s) across {len(REQUIRED_OPENAPI_SPECS)} layer OpenAPI specs."
    )
    return route_count


def _validate_system_route_schema() -> None:
    schema = _load_json(SYSTEM_ROUTE_SCHEMA)
    jsonschema.Draft202012Validator.check_schema(schema)
    print(
        f"Validated shared system-route schema: {SYSTEM_ROUTE_SCHEMA.relative_to(REPO_ROOT)}."
    )


def main() -> int:
    try:
        _validate_openapi_routes()
        _validate_system_route_schema()
    except ValueError as exc:
        print(
            f"[FAIL] Router contract surface validation failed: {exc}", file=sys.stderr
        )
        return 1
    print("[PASS] Router contract surface validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
