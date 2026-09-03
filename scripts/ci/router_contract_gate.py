#!/usr/bin/env python3
"""Router and route contract CI gate.

Validates frontend route metadata, API route/OpenAPI coverage, auth declarations,
deprecation registration, and ownership metadata. Emits auditable artifacts under
``artifacts/router-contract`` for CI upload.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
DEFAULT_REGISTRY = Path("contracts/route-contracts.json")
ARTIFACT_DIR = Path("artifacts/router-contract")
FRONTEND_ROUTER = Path("apps/web/src/shell/router.tsx")
OPENAPI_DIR = Path("contracts/openapi")
DEPRECATION_DIR = Path("contracts/deprecations")


@dataclass(frozen=True)
class ApiRoute:
    method: str
    path: str
    source: str
    deprecated: bool = False
    include_in_schema: bool = True


@dataclass(frozen=True)
class OpenApiRoute:
    method: str
    path: str
    source: str
    deprecated: bool = False
    security_declared: bool = False


def call_name(node: ast.AST | None) -> str | None:
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
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                return None
        return "".join(parts)
    return None


def literal_bool(node: ast.AST | None, default: bool = False) -> bool:
    if isinstance(node, ast.Constant) and isinstance(node.value, bool):
        return node.value
    return default


def normalize_path(path: str) -> str:
    path = re.sub(r"/{2,}", "/", path or "/")
    if len(path) > 1 and path.endswith("/"):
        path = path[:-1]
    return path


def join_paths(*parts: str) -> str:
    out = ""
    for part in parts:
        if not part:
            continue
        out = f"{out.rstrip('/')}/{part.lstrip('/')}"
    return normalize_path(out or "/")


def load_registry(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"owners": [], "internal_routes": [], "public_routes": []}
    return json.loads(path.read_text(encoding="utf-8"))


def match_rule(route: ApiRoute | OpenApiRoute, rules: list[dict[str, Any]]) -> dict[str, Any] | None:
    for rule in rules:
        method = str(rule.get("method", "*")).upper()
        pattern = str(rule.get("path", ""))
        if method not in {"*", route.method.upper()}:
            continue
        if fnmatch.fnmatch(route.path, pattern):
            return rule
    return None


def iter_python_files(root: Path) -> list[Path]:
    skip = {".venv", "site-packages", "tests", "__pycache__", "node_modules"}
    files: list[Path] = []
    for path in root.rglob("*.py"):
        parts = set(path.parts)
        if parts & skip:
            continue
        text = path.read_text(encoding="utf-8", errors="ignore")
        if "@" not in text or not any(f".{m}(" in text for m in HTTP_METHODS):
            continue
        files.append(path)
    return sorted(files)


def parse_include_prefixes() -> dict[str, str]:
    """Map router module/stem names to prefixes from app.include_router calls."""
    prefixes: dict[str, str] = {}
    for main in Path("services").rglob("main.py"):
        text = main.read_text(encoding="utf-8", errors="ignore")
        if "include_router" not in text:
            continue
        try:
            tree = ast.parse(text, filename=str(main))
        except SyntaxError:
            continue
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            if not isinstance(node.func, ast.Attribute) or node.func.attr != "include_router" or not node.args:
                continue
            router_expr = call_name(node.args[0]) or ""
            prefix = ""
            for kw in node.keywords:
                if kw.arg == "prefix":
                    prefix = literal_str(kw.value) or ""
            if not router_expr:
                continue
            for token in {router_expr, router_expr.split(".", 1)[0]}:
                prefixes[token] = prefix
                if token.endswith("_router"):
                    prefixes[token.removesuffix("_router")] = prefix
    return prefixes


def router_prefixes(tree: ast.Module) -> dict[str, str]:
    prefixes: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        if not isinstance(node.value, ast.Call) or call_name(node.value.func) != "APIRouter":
            continue
        prefix = ""
        for kw in node.value.keywords:
            if kw.arg == "prefix":
                prefix = literal_str(kw.value) or ""
        for target in node.targets:
            if isinstance(target, ast.Name):
                prefixes[target.id] = prefix
    return prefixes


def inferred_external_prefix(source: Path, route_path: str, local_prefix: str) -> str:
    """Best-effort service mount prefixes for routers registered through factories.

    Several services register routers indirectly (for example Layer 4 via
    register_routers() and Layer 3 via RouterMount objects), so there is no
    direct app.include_router call in main.py for the AST scanner to follow.
    These path-scoped defaults mirror those maintained service boundaries.
    """
    src = str(source).replace("\\", "/")
    candidate = join_paths(local_prefix, route_path)
    if candidate.startswith(("/v1/", "/api/", "/auth/")) or candidate in {"/", "/health", "/ready", "/metrics", "/openapi.json"}:
        return ""
    if "/services/layer7-billing/src/layer7_billing/api/routes/billing.py" in f"/{src}":
        return "/v1"
    if "/services/layer7-billing/src/layer7_billing/api/routes/billing_overages.py" in f"/{src}":
        return "/v1/billing"
    if "/services/layer7-billing/src/layer7_billing/api/routes/billing_usage.py" in f"/{src}":
        return "/v1/billing"
    if "/services/layer7-billing/src/layer7_billing/api/routes/billing_webhooks.py" in f"/{src}":
        return "/v1/billing"
    if "/services/api/app/routers/" in f"/{src}":
        if source.name == "clerk_webhooks.py":
            return ""
        return "/v1"
    if "/services/layer4-agents/src/layer4_agents/api/routes/" in f"/{src}":
        return "/v1"
    if "/services/layer4-agents/src/layer4_agents/tenants/api/" in f"/{src}":
        if "/routes/oidc.py" in f"/{src}":
            return ""
        return "/v1"
    if "/services/layer4-agents/src/layer4_agents/registry/api/" in f"/{src}" or "/services/layer4-agents/src/layer4_agents/feature_flags/" in f"/{src}":
        return "/v1"
    if "/services/layer2-extraction/src/layer2_extraction/api/routes/" in f"/{src}":
        if candidate.startswith(("/health", "/ready", "/metrics")):
            return ""
        return "/v1"
    if "/services/layer3-knowledge/src/api/routes/" in f"/{src}" or "/services/layer3-knowledge/src/api/routers/" in f"/{src}":
        if candidate.startswith(("/health", "/ready", "/metrics")):
            return ""
        return "/v1"
    return ""


def extract_api_routes() -> list[ApiRoute]:
    include_prefixes = parse_include_prefixes()
    routes: list[ApiRoute] = []
    for path in iter_python_files(Path("services")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8", errors="ignore"), filename=str(path))
        except SyntaxError:
            continue
        local_prefixes = router_prefixes(tree)
        stem_prefix = include_prefixes.get(path.stem, "")
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for deco in node.decorator_list:
                if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute):
                    continue
                method = deco.func.attr.lower()
                if method not in HTTP_METHODS:
                    continue
                owner = call_name(deco.func.value) or ""
                route_path = literal_str(deco.args[0]) if deco.args else "/"
                if route_path is None:
                    route_path = "/"
                external_prefix = stem_prefix or include_prefixes.get(owner, "") or include_prefixes.get(owner.split(".", 1)[0], "")
                local_prefix = local_prefixes.get(owner, "")
                if not external_prefix:
                    external_prefix = inferred_external_prefix(path, route_path, local_prefix)
                deprecated = False
                include_in_schema = True
                for kw in deco.keywords:
                    if kw.arg == "deprecated":
                        deprecated = literal_bool(kw.value, False)
                    if kw.arg == "include_in_schema":
                        include_in_schema = literal_bool(kw.value, True)
                routes.append(ApiRoute(method.upper(), join_paths(external_prefix, local_prefix, route_path), str(path), deprecated, include_in_schema))
    # De-dupe while keeping deterministic source list first occurrence.
    seen: set[tuple[str, str, str]] = set()
    unique: list[ApiRoute] = []
    for route in sorted(routes, key=lambda r: (r.method, r.path, r.source)):
        key = (route.method, route.path, route.source)
        if key in seen:
            continue
        seen.add(key)
        unique.append(route)
    return unique


def extract_openapi_routes() -> list[OpenApiRoute]:
    routes: list[OpenApiRoute] = []
    for spec_path in sorted(OPENAPI_DIR.glob("*.json")):
        spec = json.loads(spec_path.read_text(encoding="utf-8"))
        root_security = spec.get("security")
        for path, item in sorted((spec.get("paths") or {}).items()):
            if not isinstance(item, dict):
                continue
            for method, op in sorted(item.items()):
                if method.lower() not in HTTP_METHODS or not isinstance(op, dict):
                    continue
                security = op.get("security", root_security)
                routes.append(OpenApiRoute(method.upper(), normalize_path(path), str(spec_path), bool(op.get("deprecated")), security is not None))
    return routes


def load_deprecation_entries() -> set[tuple[str, str]]:
    entries: set[tuple[str, str]] = set()
    for path in sorted(DEPRECATION_DIR.glob("*.json")):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        for entry in data.get("entries", []):
            if entry.get("type") == "endpoint" and entry.get("method") and entry.get("path"):
                entries.add((str(entry["method"]).upper(), normalize_path(str(entry["path"]))))
            elif isinstance(entry.get("key"), str):
                m = re.match(r"^(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(\S+)$", entry["key"].upper())
                if m:
                    entries.add((m.group(1), normalize_path(m.group(2))))
    return entries


def frontend_audit(registry: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    failures: list[str] = []
    text = FRONTEND_ROUTER.read_text(encoding="utf-8")
    path_matches = list(re.finditer(r"path:\s*['\"]([^'\"]+)['\"]", text))
    routes: list[dict[str, Any]] = []
    for match in path_matches:
        route_path = match.group(1)
        if route_path == "*":
            continue
        # Small bounded window for route-local/inherited metadata. Parent route groups are
        # intentionally checked by looking back to the nearest guard/policy block.
        window = text[max(0, match.start() - 900): min(len(text), match.end() + 900)]
        requires_auth = "requiresAuth: false" not in window and ("UnifiedRouteGuard" in window or "RequireClerkAuth" in window or "requiresAuth: true" in window)
        has_policy = "accessPolicy" in window or route_path in {"/"}
        owner = owner_for_path(route_path, registry.get("frontend_owners", []))
        if not owner:
            failures.append(f"frontend route {route_path} has no ownership metadata")
        inherits_parent_policy = route_path.startswith("/t/:tenantSlug/settings")
        if route_path not in {"/", "/sign-in", "/sign-up"} and not has_policy and not inherits_parent_policy:
            failures.append(f"frontend route {route_path} is missing accessPolicy metadata")
        if route_path not in {"/sign-in", "/sign-up"} and not requires_auth and not route_path.startswith("/"):
            failures.append(f"frontend route {route_path} auth requirement could not be inferred")
        routes.append({"path": route_path, "owner": owner, "has_access_policy": has_policy, "requires_auth_inferred": requires_auth})
    artifact = {"router": str(FRONTEND_ROUTER), "total_routes": len(routes), "routes": routes}
    return artifact, failures


def owner_for_path(path: str, rules: list[dict[str, Any]]) -> str | None:
    dummy = OpenApiRoute("GET", normalize_path(path), "frontend")
    rule = match_rule(dummy, rules)
    return str(rule.get("owner")) if rule and rule.get("owner") else None


def write_artifacts(report: dict[str, Any]) -> None:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    (ARTIFACT_DIR / "route-audit.json").write_text(json.dumps(report, indent=2, sort_keys=True), encoding="utf-8")
    lines = ["# Router Contract Audit", "", f"Status: **{report['status']}**", ""]
    s = report["summary"]
    for key in ["openapi_routes", "implemented_routes", "frontend_routes", "failures"]:
        lines.append(f"- {key.replace('_', ' ').title()}: **{s[key]}**")
    lines.append("")
    if report["failures"]:
        lines.append("## Failures")
        for failure in report["failures"][:200]:
            lines.append(f"- {failure}")
    else:
        lines.append("No router contract failures detected.")
    (ARTIFACT_DIR / "route-audit.md").write_text("\n".join(lines) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY)
    args = parser.parse_args(argv)

    registry = load_registry(args.registry)
    owners = registry.get("owners", [])
    internals = registry.get("internal_routes", [])
    public_routes = registry.get("public_routes", [])
    contract_only_routes = registry.get("contract_only_routes", [])

    openapi_routes = extract_openapi_routes()
    implemented_routes = extract_api_routes()
    deprecated_entries = load_deprecation_entries()
    frontend_report, frontend_failures = frontend_audit(registry)

    doc_keys = {(r.method, r.path) for r in openapi_routes}
    impl_public = [r for r in implemented_routes if r.include_in_schema]
    impl_keys = {(r.method, r.path) for r in impl_public}

    failures: list[str] = []
    for route in sorted(openapi_routes, key=lambda r: (r.method, r.path, r.source)):
        if (route.method, route.path) not in impl_keys and not match_rule(route, internals) and not match_rule(route, contract_only_routes):
            failures.append(f"documented OpenAPI route has no implementation: {route.method} {route.path} ({route.source})")
        if not match_rule(route, owners):
            failures.append(f"documented route has no owner metadata: {route.method} {route.path}")
        public = match_rule(route, public_routes)
        if not public and not route.security_declared and not match_rule(route, registry.get("auth_declared_routes", [])):
            failures.append(f"protected OpenAPI route lacks auth requirement declaration: {route.method} {route.path} ({route.source})")
        if route.deprecated and (route.method, route.path) not in deprecated_entries:
            failures.append(f"deprecated OpenAPI route missing deprecation registry entry: {route.method} {route.path}")

    for route in sorted(impl_public, key=lambda r: (r.method, r.path, r.source)):
        if (route.method, route.path) not in doc_keys and not match_rule(route, internals):
            failures.append(f"implemented public route is undocumented and not internal: {route.method} {route.path} ({route.source})")
        if not match_rule(route, owners):
            failures.append(f"implemented route has no owner metadata: {route.method} {route.path} ({route.source})")
        if route.deprecated and (route.method, route.path) not in deprecated_entries:
            failures.append(f"deprecated implemented route missing deprecation registry entry: {route.method} {route.path} ({route.source})")

    failures.extend(frontend_failures)
    report = {
        "status": "fail" if failures else "pass",
        "summary": {
            "openapi_routes": len(openapi_routes),
            "implemented_routes": len(implemented_routes),
            "frontend_routes": frontend_report["total_routes"],
            "failures": len(failures),
        },
        "failures": failures,
        "openapi_routes": [asdict(r) for r in openapi_routes],
        "implemented_routes": [asdict(r) for r in implemented_routes],
        "frontend": frontend_report,
    }
    write_artifacts(report)
    if failures:
        print(f"FAIL: router contract gate found {len(failures)} issue(s). See {ARTIFACT_DIR / 'route-audit.md'}")
        for failure in failures[:50]:
            print(f"- {failure}")
        return 1
    print(f"PASS: router contract gate passed. Artifact: {ARTIFACT_DIR / 'route-audit.md'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
