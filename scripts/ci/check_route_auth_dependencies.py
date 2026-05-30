#!/usr/bin/env python3
"""CI gate to enforce auth dependencies on non-allowlisted FastAPI routes.

Scans service entrypoints and internal routers using AST.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
DEFAULT_TARGETS = [
    "services/api/app/main.py",
    "services/layer1-ingestion/src/api/main.py",
    "services/layer2-extraction/src/layer2_extraction/api/main.py",
    "services/layer3-knowledge/src/api/main.py",
    "services/layer4-agents/src/api/main.py",
    "services/layer5-ground-truth/src/layer5_ground_truth/api/main.py",
    "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
]
AUTH_CALL_NAMES = {
    "Depends",
    "Security",
    "require_authenticated",
    "require_auth",
    "require_role",
    "require_permission",
    "get_current_api_key",
    "get_verified_tenant_id",
    "get_request_context",
}


@dataclass
class RouteRecord:
    method: str
    path: str
    source: str
    auth_present: bool
    allowlisted: bool = False


def call_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return call_name(node.func)
    return None


def literal_str(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def has_auth_dependency(node: ast.AST) -> bool:
    for n in ast.walk(node):
        if isinstance(n, ast.Call):
            if call_name(n.func) in AUTH_CALL_NAMES:
                return True
    return False


def extract_router_deps(tree: ast.Module) -> dict[str, bool]:
    router_auth: dict[str, bool] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign) and len(node.targets) == 1 and isinstance(node.targets[0], ast.Name):
            name = node.targets[0].id
            value = node.value
            if isinstance(value, ast.Call) and call_name(value.func) == "APIRouter":
                router_auth[name] = has_auth_dependency(value)
    return router_auth


def extract_include_prefixes(tree: ast.Module) -> dict[str, str]:
    prefixes: dict[str, str] = {}
    for node in tree.body:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            call = node.value
            if isinstance(call.func, ast.Attribute) and call.func.attr == "include_router" and call.args:
                router_name = call_name(call.args[0])
                if not router_name:
                    continue
                pref = ""
                for kw in call.keywords:
                    if kw.arg == "prefix":
                        pref = literal_str(kw.value) or ""
                prefixes[router_name] = pref
                if "." in router_name:
                    prefixes[router_name.split(".", 1)[0]] = pref
    return prefixes


def extract_routes(py_file: Path, base_prefix: str = "") -> tuple[list[RouteRecord], dict[str, str]]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    router_auth = extract_router_deps(tree)
    include_prefixes = extract_include_prefixes(tree)
    records: list[RouteRecord] = []

    for node in tree.body:
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        fn_auth = has_auth_dependency(node)
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call):
                continue
            if not isinstance(deco.func, ast.Attribute):
                continue
            method = deco.func.attr.lower()
            if method not in HTTP_METHODS:
                continue
            router_name = call_name(deco.func.value) or ""
            route_path = literal_str(deco.args[0]) if deco.args else "/"
            if route_path is None:
                route_path = "/"
            full = f"{base_prefix}{route_path}".replace("//", "/")
            auth = fn_auth or has_auth_dependency(deco)
            if router_name in router_auth:
                auth = auth or router_auth[router_name]
            records.append(RouteRecord(method.upper(), full, str(py_file), auth))
    return records, include_prefixes


def load_allowlist(path: Path) -> list[dict[str, Any]]:
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data.get("allowlist", [])


def is_allowlisted(r: RouteRecord, allowlist: list[dict[str, Any]]) -> bool:
    for item in allowlist:
        method = str(item.get("method", "*")).upper()
        pattern = str(item.get("path", ""))
        if method not in {"*", r.method}:
            continue
        if fnmatch.fnmatch(r.path, pattern):
            return True
    return False


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--allowlist", default="contracts/route-auth-allowlist.yaml")
    parser.add_argument("--target", action="append", default=[])
    args = parser.parse_args()

    allowlist = load_allowlist(Path(args.allowlist))
    targets = [Path(t) for t in (args.target or DEFAULT_TARGETS)]
    all_routes: list[RouteRecord] = []

    for target in targets:
        routes, includes = extract_routes(target)
        all_routes.extend(routes)
        # inspect internal routers included by entrypoint
        for router_dir_name in ("routes", "routers"):
            router_dir = target.parent / router_dir_name
            if not router_dir.exists():
                continue
            for router_file in router_dir.glob("*.py"):
                if router_file.name.startswith("_"):
                    continue
                base_prefix = includes.get(router_file.stem, "")
                sub_routes, _ = extract_routes(router_file, base_prefix=base_prefix)
                all_routes.extend(sub_routes)

    failures = []
    public_count = 0
    protected_count = 0

    for route in all_routes:
        route.allowlisted = is_allowlisted(route, allowlist)
        if route.allowlisted:
            public_count += 1
            continue
        if route.auth_present:
            protected_count += 1
            continue
        failures.append(route)

    print(f"Scanned routes: {len(all_routes)}")
    print(f"Public (allowlisted): {public_count}")
    print(f"Protected (auth deps): {protected_count}")

    if failures:
        print("\nFAIL: non-allowlisted routes without auth dependencies:")
        for f in failures:
            print(f"- {f.method} {f.path} [{f.source}]")
        return 1

    print("PASS: all non-allowlisted routes have auth dependencies")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
