#!/usr/bin/env python3
"""Regenerate contracts/layer4-route-contract-matrix.json from OpenAPI + source routes.

This script preserves existing matrix metadata (frontend_consumers,
backend_route_files, sse_event_channels) for routes that are already present,
adds entries for OpenAPI routes missing from the matrix, drops entries whose
OpenAPI operation no longer exists, and removes schema references that do not
resolve in the current OpenAPI components object.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

MATRIX_PATH = Path("contracts/layer4-route-contract-matrix.json")
OPENAPI_PATH = Path("contracts/openapi/layer4-agents.json")
ROUTE_DIRS = [
    Path("services/layer4-agents/src/layer4_agents/api/routes"),
    Path("services/layer4-agents/src/layer4_agents/feature_flags/api"),
    Path("services/layer4-agents/src/layer4_agents/tenants/api/routes"),
    Path("services/layer4-agents/src/layer4_agents/registry/api"),
]
ROUTE_RE = re.compile(r"@(?:router|[a-zA-Z_][\w]*)\.(get|post|put|delete|patch)\(\s*['\"]([^'\"]+)")


def discovered_api_routes() -> set[tuple[str, str]]:
    out: set[tuple[str, str]] = set()
    for d in ROUTE_DIRS:
        if not d.exists():
            continue
        for f in d.rglob("*.py"):
            txt = f.read_text(errors="ignore")
            for m in ROUTE_RE.finditer(txt):
                path = m.group(2)
                if path.startswith("/api"):
                    out.add((m.group(1).upper(), path))
    return out


def collect_refs(obj: object) -> list[str]:
    refs: list[str] = []
    if isinstance(obj, dict):
        for k, v in obj.items():
            if k == "$ref" and isinstance(v, str):
                refs.append(v)
            refs.extend(collect_refs(v))
    elif isinstance(obj, list):
        for i in obj:
            refs.extend(collect_refs(i))
    return refs


def resolve_ref(ref: str, root: dict) -> bool:
    if not ref.startswith("#/"):
        return False
    cur = root
    for part in ref[2:].split("/"):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


def strip_invalid_refs(obj: object, root: dict) -> object:
    """Remove schema objects whose $ref does not resolve against the OpenAPI root; keep the rest."""
    if isinstance(obj, dict):
        if "$ref" in obj and isinstance(obj["$ref"], str):
            if not resolve_ref(obj["$ref"], root):
                return {}
        return {k: strip_invalid_refs(v, root) for k, v in obj.items()}
    if isinstance(obj, list):
        return [strip_invalid_refs(i, root) for i in obj]
    return obj


def schema_from_media(response: dict) -> dict:
    content = response.get("content", {})
    media = content.get("application/json") or next(iter(content.values()), {})
    return media.get("schema", {})


def build_entry(path: str, method: str, operation: dict, existing: dict | None, openapi_root: dict) -> dict:
    method_upper = method.upper()
    route_id = f"{method_upper} {path}"

    if existing:
        entry = dict(existing)
    else:
        entry = {
            "route_id": route_id,
            "backend_route_files": [],
            "openapi_path": path,
            "method": method_upper,
            "operation_id": operation.get("operationId", ""),
            "request_schema": None,
            "success_response_schemas": [],
            "error_envelope_schemas": [],
            "sse_event_channels": [],
            "frontend_consumers": [],
        }

    # Always refresh these fields from the current OpenAPI operation so the
    # matrix does not drift from the contract.
    entry["route_id"] = route_id
    entry["openapi_path"] = path
    entry["method"] = method_upper
    entry["operation_id"] = operation.get("operationId", entry.get("operation_id", ""))

    # Request schema
    request_body = operation.get("requestBody", {})
    entry["request_schema"] = schema_from_media(request_body) or None

    # Response schemas
    success_schemas = []
    error_schemas = []
    for status, response in operation.get("responses", {}).items():
        description = response.get("description", "")
        schema = schema_from_media(response)
        target = success_schemas if status.startswith("2") else error_schemas
        target.append({"status_code": status, "description": description, "schema": schema})

    entry["success_response_schemas"] = success_schemas
    entry["error_envelope_schemas"] = error_schemas

    # Strip any invalid schema refs introduced by stale generated names.
    entry = strip_invalid_refs(entry, openapi_root)

    return entry


def main() -> int:
    matrix = json.loads(MATRIX_PATH.read_text(encoding="utf-8"))
    openapi = json.loads(OPENAPI_PATH.read_text(encoding="utf-8"))
    components = openapi.get("components", {})
    paths = openapi.get("paths", {})

    existing_entries = {
        (e["method"], e["openapi_path"]): e for e in matrix.get("entries", [])
    }

    new_entries: list[dict] = []
    seen_keys: set[tuple[str, str]] = set()

    # 1. One entry for every OpenAPI path/method.
    for path, methods in paths.items():
        for method, operation in methods.items():
            if method.startswith("x-") or not isinstance(operation, dict):
                continue
            key = (method.upper(), path)
            seen_keys.add(key)
            existing = existing_entries.get(key)
            new_entries.append(build_entry(path, method, operation, existing, openapi))

    # 2. Entries for discovered /api routes not present in OpenAPI.
    for method, path in discovered_api_routes():
        key = (method, path)
        if key in seen_keys:
            continue
        seen_keys.add(key)
        existing = existing_entries.get(key)
        if existing:
            new_entries.append(existing)
        else:
            new_entries.append(
                {
                    "route_id": f"{method} {path}",
                    "backend_route_files": [],
                    "openapi_path": path,
                    "method": method,
                    "operation_id": "",
                    "request_schema": None,
                    "success_response_schemas": [],
                    "error_envelope_schemas": [],
                    "sse_event_channels": [],
                    "frontend_consumers": [],
                }
            )

    # Sort for stable output.
    new_entries.sort(key=lambda e: (e["openapi_path"], e["method"]))

    matrix["entries"] = new_entries
    MATRIX_PATH.write_text(json.dumps(matrix, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

    print(f"Regenerated {MATRIX_PATH}: {len(new_entries)} entries")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
