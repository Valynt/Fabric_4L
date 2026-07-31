#!/usr/bin/env python3
"""Validate Fabric_4L production OpenAPI documentation completeness.

The generated API contract is consumed by security assessors and client
integrations. This CI gate intentionally checks more than JSON syntax: every
operation must have a meaningful description, every operation parameter must be
explained, every schema/property must be documented, write request bodies must
have examples, write responses must include examples, and operations must carry
an explicit Fabric layer tag.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head", "trace"}
WRITE_METHODS = {"post", "put", "patch"}
LAYER_TAGS = {
    "L1-Ingestion",
    "L2-Extraction",
    "L3-Knowledge",
    "L4-Agents",
    "L5-Ground-Truth",
    "L6-Benchmarks",
    "Platform",
}
GENERIC_DESCRIPTIONS = {
    "todo",
    "tbd",
    "n/a",
    "none",
    "description",
    "operation completed successfully.",
}


def has_meaningful_text(value: object, *, min_words: int = 4) -> bool:
    if not isinstance(value, str):
        return False
    text = " ".join(value.strip().split())
    if not text or text.lower() in GENERIC_DESCRIPTIONS:
        return False
    return len(text.split()) >= min_words


def iter_operations(spec: dict[str, object]):
    for path, path_item in spec.get("paths", {}).items():
        if not isinstance(path_item, dict):
            continue
        for method, operation in path_item.items():
            if method.lower() in HTTP_METHODS and isinstance(operation, dict):
                yield path, method.lower(), operation


def collect_errors(spec: dict[str, object]) -> list[str]:
    errors: list[str] = []

    for path, method, operation in iter_operations(spec):
        op_label = f"{method.upper()} {path}"
        if not has_meaningful_text(operation.get("description")):
            errors.append(f"{op_label}: missing meaningful operation description")

        tags = operation.get("tags") or []
        if not any(tag in LAYER_TAGS for tag in tags):
            errors.append(f"{op_label}: missing Fabric layer tag ({', '.join(sorted(LAYER_TAGS))})")

        for parameter in operation.get("parameters") or []:
            name = parameter.get("name", "<unnamed>")
            if not has_meaningful_text(parameter.get("description")):
                errors.append(f"{op_label}: parameter {name!r} missing meaningful description")

        if method in WRITE_METHODS and operation.get("requestBody"):
            content = operation["requestBody"].get("content") or {}
            for media_type, media in content.items():
                if not isinstance(media, dict):
                    continue
                if not (media.get("examples") or media.get("example")):
                    errors.append(f"{op_label}: {media_type} request body missing example")

            success_responses = {
                code: response
                for code, response in (operation.get("responses") or {}).items()
                if str(code).startswith("2") and isinstance(response, dict)
            }
            for code, response in success_responses.items():
                for media_type, media in (response.get("content") or {}).items():
                    if isinstance(media, dict) and not (media.get("examples") or media.get("example")):
                        errors.append(f"{op_label}: {code} {media_type} response missing example")

    schemas = spec.get("components", {}).get("schemas", {})
    for schema_name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        if not has_meaningful_text(schema.get("description")):
            errors.append(f"schema {schema_name}: missing meaningful description")
        for property_name, property_schema in (schema.get("properties") or {}).items():
            if isinstance(property_schema, dict) and not has_meaningful_text(property_schema.get("description")):
                errors.append(f"schema {schema_name}.{property_name}: missing meaningful description")

    return errors


def load_baseline(path: Path | None) -> set[str]:
    if path is None:
        return set()
    payload = json.loads(path.read_text(encoding="utf-8"))
    violations = payload.get("violations", [])
    if not isinstance(violations, list) or not all(isinstance(item, str) for item in violations):
        raise ValueError(f"OpenAPI documentation baseline has invalid violations list: {path}")
    return set(violations)


def write_baseline(path: Path, errors: Iterable[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "description": (
            "Baseline for existing Fabric_4L OpenAPI documentation completeness debt. "
            "New violations fail scripts/ci/validate_fabric_openapi_docs.py."
        ),
        "violations": list(errors),
    }
    path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")


def validate(spec: dict[str, object], *, baseline: Iterable[str] | None = None) -> list[str]:
    approved = set(baseline or [])
    all_errors = set(collect_errors(spec))
    new_errors = sorted(all_errors - approved)
    stale_approvals = [f"STALE BASELINE: {error}" for error in sorted(approved - all_errors)]
    return new_errors + stale_approvals


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "spec",
        nargs="?",
        default="contracts/openapi/fabric-4l-api.json",
        type=Path,
        help="Path to the Fabric_4L OpenAPI JSON document.",
    )
    parser.add_argument(
        "--baseline",
        type=Path,
        help="JSON baseline of existing documentation violations to subtract from the gate.",
    )
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Write the current violation set to --baseline and exit successfully.",
    )
    args = parser.parse_args(argv)

    if args.update_baseline and args.baseline is None:
        parser.error("--update-baseline requires --baseline")

    try:
        spec = json.loads(args.spec.read_text())
    except json.JSONDecodeError as exc:
        print(f"OpenAPI JSON is invalid: {exc}", file=sys.stderr)
        return 1

    all_errors = collect_errors(spec)
    if args.update_baseline:
        write_baseline(args.baseline, all_errors)
        print(f"Fabric_4L OpenAPI documentation baseline updated ({len(all_errors)} violations).")
        return 0

    try:
        baseline = load_baseline(args.baseline)
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"OpenAPI documentation baseline is invalid: {exc}", file=sys.stderr)
        return 1

    errors = validate(spec, baseline=baseline)
    if errors:
        print("Fabric_4L OpenAPI documentation validation failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    operation_count = sum(1 for _ in iter_operations(spec))
    schema_count = len(spec.get("components", {}).get("schemas", {}))
    print(f"Fabric_4L OpenAPI documentation validation passed ({operation_count} operations, {schema_count} schemas).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
