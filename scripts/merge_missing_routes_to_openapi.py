#!/usr/bin/env python3
"""
Static route scanner for FastAPI routers.

Parses router Python files using the AST (no imports required) and merges
missing paths into existing OpenAPI JSON specs.

This is a remediation helper for BLOCKER-003 and BLOCKER-004 where backend
routes exist in code but generated OpenAPI specs are stale.

Usage:
    python scripts/merge_missing_routes_to_openapi.py --layer layer4-agents
    python scripts/merge_missing_routes_to_openapi.py --all
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any


def extract_router_prefix(path: Path) -> str:
    """Extract the prefix from `router = APIRouter(prefix="...")` in a file."""
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == "router":
                    if isinstance(node.value, ast.Call):
                        for kw in node.value.keywords:
                            if kw.arg == "prefix" and isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                                return kw.value.value
    return ""


def extract_routes_from_file(path: Path) -> list[dict[str, str]]:
    """Extract @router.{method}("/path") decorators from a Python file."""
    routes: list[dict[str, str]] = []
    source = path.read_text(encoding="utf-8")
    tree = ast.parse(source)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for deco in node.decorator_list:
            call = None
            if isinstance(deco, ast.Call):
                call = deco
            elif isinstance(deco, ast.Attribute) and deco.attr in ("get", "post", "put", "patch", "delete"):
                # Bare decorator without args
                routes.append({"method": deco.attr.upper(), "path": ""})
                continue
            if call is None:
                continue

            func = call.func
            if not isinstance(func, ast.Attribute):
                continue
            if func.attr not in ("get", "post", "put", "patch", "delete"):
                continue

            method = func.attr.upper()
            path_arg = ""
            if call.args and isinstance(call.args[0], ast.Constant) and isinstance(call.args[0].value, str):
                path_arg = call.args[0].value

            routes.append({"method": method, "path": path_arg, "source": str(path)})

    return routes


def collect_routes_from_routers(router_dirs: Path | list[Path], app_prefix: str = "/v1") -> list[dict[str, str]]:
    """Collect all routes from router files in one or more directories."""
    routes: list[dict[str, str]] = []
    dirs = [router_dirs] if isinstance(router_dirs, Path) else router_dirs
    for router_dir in dirs:
        if not router_dir.exists():
            continue
        for py_file in sorted(router_dir.glob("*.py")):
            if py_file.name.startswith("_"):
                continue
            router_prefix = extract_router_prefix(py_file)
            file_routes = extract_routes_from_file(py_file)
            for r in file_routes:
                # Build full path: app_prefix + router_prefix + route_path
                segments = []
                for p in [app_prefix, router_prefix, r["path"]]:
                    if p:
                        segments.append(p.strip("/"))
                full_path = "/" + "/".join(segments)
                routes.append({"method": r["method"], "path": full_path, "source": str(py_file)})

    return routes


def load_openapi(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def save_openapi(path: Path, spec: dict[str, Any]) -> None:
    path.write_text(json.dumps(spec, indent=2, ensure_ascii=False), encoding="utf-8")


def merge_routes(spec: dict[str, Any], routes: list[dict[str, str]], layer: str) -> tuple[int, int]:
    """Merge missing routes into spec. Returns (added, existing)."""
    added = 0
    existing = 0
    paths = spec.setdefault("paths", {})

    for r in routes:
        path = r["path"]
        method = r["method"].lower()
        if not path or not method:
            continue

        # Normalize path: remove double slashes
        path = re.sub(r"/+", "/", path)

        path_node = paths.setdefault(path, {})
        if method in path_node:
            existing += 1
            continue

        # Add a minimal stub
        path_node[method] = {
            "tags": [layer],
            "summary": f"{method.upper()} {path}",
            "description": f"Discovered from router source ({r.get('source', 'unknown')}).",
            "operationId": f"discovered_{method}_{path.replace('/', '_').replace('{', '').replace('}', '').strip('_')}",
            "responses": {
                "200": {"description": "Successful Response"},
                "422": {"description": "Validation Error"},
            },
        }
        added += 1

    return added, existing


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Merge missing routes into OpenAPI specs")
    parser.add_argument("--layer", choices=["layer1-ingestion", "layer2-extraction", "layer3-knowledge", "layer4-agents", "layer5-ground-truth", "layer6-benchmarks"], help="Layer to process")
    parser.add_argument("--all", action="store_true", help="Process all layers")
    args = parser.parse_args()

    layers_to_process = []
    if args.all:
        layers_to_process = ["layer1-ingestion", "layer2-extraction", "layer3-knowledge", "layer4-agents", "layer5-ground-truth", "layer6-benchmarks"]
    elif args.layer:
        layers_to_process = [args.layer]
    else:
        parser.print_help()
        return 1

    layer_configs = {
        "layer1-ingestion": {
            "router_dir": Path("services/layer1-ingestion/src/api/routes"),
            "spec_path": Path("contracts/openapi/layer1-ingestion.json"),
            "prefix": "/api/v1/ingestion",
            "main_path": "layer1_ingestion/api/main.py",
        },
        "layer2-extraction": {
            "router_dir": Path("services/layer2-extraction/src/layer2_extraction/api/routes"),
            "spec_path": Path("contracts/openapi/layer2-extraction.json"),
            "prefix": "",
            "main_path": "layer2_extraction/api/main.py",
        },
        "layer3-knowledge": {
            "router_dir": Path("services/layer3-knowledge/src/api/routes"),
            "spec_path": Path("contracts/openapi/layer3-knowledge.json"),
            "prefix": "/v1",
        },
        "layer4-agents": {
            "router_dir": [
                Path("services/layer4-agents/src/layer4_agents/api/routes"),
                Path("services/layer4-agents/src/layer4_agents/tenants/api/routes"),
                Path("services/layer4-agents/src/layer4_agents/registry/api"),
                Path("services/layer4-agents/src/layer4_agents/messaging"),
            ],
            "spec_path": Path("contracts/openapi/layer4-agents.json"),
            "prefix": "/v1",
        },
        "layer5-ground-truth": {
            "router_dir": Path("services/layer5-ground-truth/src/layer5_ground_truth/api/routes"),
            "spec_path": Path("contracts/openapi/layer5-ground-truth.json"),
            "prefix": "/api/v1",
        },
        "layer6-benchmarks": {
            "router_dir": Path("services/layer6-benchmarks/src/api/routes"),
            "spec_path": Path("contracts/openapi/layer6-benchmarks.json"),
            "prefix": "",
        },
    }

    changed = False
    for layer in layers_to_process:
        config = layer_configs.get(layer)
        if not config:
            continue

        router_dir = config["router_dir"]
        spec_path = config["spec_path"]
        prefix = config["prefix"]

        if not spec_path.exists():
            print(f"[WARN] Spec not found: {spec_path}")
            continue

        print(f"\n📦 Processing {layer}...")
        routes = collect_routes_from_routers(router_dir, prefix)
        dirs_display = router_dir if isinstance(router_dir, Path) else ", ".join(str(d) for d in router_dir)
        print(f"   Discovered {len(routes)} routes from {dirs_display}")

        spec = load_openapi(spec_path)
        before_paths = len(spec.get("paths", {}))
        added, existing = merge_routes(spec, routes, layer)
        after_paths = len(spec.get("paths", {}))

        if added:
            save_openapi(spec_path, spec)
            changed = True
            print(f"   ✅ Added {added} missing routes ({existing} already present)")
            print(f"   Paths: {before_paths} → {after_paths}")
        else:
            print(f"   ✅ No missing routes ({existing} present)")

    print()
    return 0 if not changed else 0


if __name__ == "__main__":
    sys.exit(main())
