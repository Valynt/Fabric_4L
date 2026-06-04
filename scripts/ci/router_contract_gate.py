#!/usr/bin/env python3
"""Router/API/frontend route contract gate.

This is a static CI gate for route drift. It intentionally avoids importing service
applications so it can run in lightweight CI jobs without databases, queues, or
provider credentials.
"""
from __future__ import annotations

import argparse
import ast
import fnmatch
import json
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:  # pragma: no cover - CI images install pyyaml, but keep message clear.
    yaml = None  # type: ignore[assignment]

HTTP_METHODS = {"get", "post", "put", "patch", "delete", "options", "head"}
ROUTE_GLOBS = [
    "services/api/app/main.py",
    "services/api/app/routers/*.py",
    "services/layer1-ingestion/src/layer1_ingestion/api/main*.py",
    "services/layer1-ingestion/src/layer1_ingestion/api/routes/*.py",
    "services/layer2-extraction/src/layer2_extraction/api/main.py",
    "services/layer2-extraction/src/layer2_extraction/api/routes/*.py",
    "services/layer3-knowledge/src/api/main.py",
    "services/layer3-knowledge/src/api/routes/*.py",
    "services/layer3-knowledge/src/api/routers/*.py",
    "services/layer4-agents/src/layer4_agents/api/main.py",
    "services/layer4-agents/src/layer4_agents/api/routers.py",
    "services/layer4-agents/src/layer4_agents/api/routes/*.py",
    "services/layer4-agents/src/layer4_agents/feature_flags/api/routes.py",
    "services/layer4-agents/src/layer4_agents/registry/api/routes.py",
    "services/layer4-agents/src/layer4_agents/tenants/api/routes/*.py",
    "services/layer5-ground-truth/src/layer5_ground_truth/api/*.py",
    "services/layer6-benchmarks/src/layer6_benchmarks/api/main.py",
    "services/layer6-benchmarks/src/layer6_benchmarks/api/routes/*.py",
    "services/layer7-billing/src/layer7_billing/api/main.py",
    "services/layer7-billing/src/layer7_billing/api/routes/*.py",
]
OPENAPI_GLOB = "contracts/openapi/*.json"
ALLOWLIST = Path("contracts/route-auth-allowlist.yaml")
DEPRECATIONS_DIR = Path("contracts/deprecations")
BASELINE = Path("contracts/router-contract-baseline.json")
ARTIFACT_DIR = Path("artifacts/router-contract")

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
    "get_current_user",
    "get_auth_context",
    "get_tenant_context",
    "require_tenant_context",
    "require_admin",
}
SECURITY_KEYS = ("security", "x-auth-required", "x-authentication", "x-fabric-auth")

SERVICE_PREFIXES = (
    "/api/v1/ingestion",
    "/api/v1/governance",
    "/api/v1",
    "/v1",
)

@dataclass(frozen=True)
class RouteKey:
    method: str
    path: str

    @property
    def text(self) -> str:
        return f"{self.method} {self.path}"

@dataclass
class ImplementedRoute:
    method: str
    path: str
    source: str
    function: str
    owner: str
    auth_present: bool
    include_in_schema: bool
    deprecated: bool
    line: int

    @property
    def key(self) -> RouteKey:
        return RouteKey(self.method, normalize_path(self.path))

@dataclass
class OpenApiRoute:
    method: str
    path: str
    source: str
    operation_id: str
    owner: str
    auth_declared: bool
    deprecated: bool
    internal: bool

    @property
    def key(self) -> RouteKey:
        return RouteKey(self.method, normalize_path(self.path))

@dataclass
class GateReport:
    documented_routes: list[dict[str, Any]] = field(default_factory=list)
    implemented_routes: list[dict[str, Any]] = field(default_factory=list)
    missing_openapi_coverage: list[str] = field(default_factory=list)
    undocumented_public_routes: list[str] = field(default_factory=list)
    auth_mismatches: list[str] = field(default_factory=list)
    deprecated_routes_missing_registry: list[str] = field(default_factory=list)
    missing_ownership_metadata: list[str] = field(default_factory=list)
    frontend_route_audit: str = "not-run"


def call_name(node: ast.AST | None) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        parent = call_name(node.value)
        return f"{parent}.{node.attr}" if parent else node.attr
    if isinstance(node, ast.Call):
        return call_name(node.func)
    return None


def literal(node: ast.AST | None) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List | ast.Tuple):
        return [literal(elt) for elt in node.elts]
    return None


def truthy_kw(call: ast.Call, name: str, *, default: bool) -> bool:
    for kw in call.keywords:
        if kw.arg == name:
            value = literal(kw.value)
            if isinstance(value, bool):
                return value
            return default
    return default


def kw_literal(call: ast.Call, name: str) -> Any:
    for kw in call.keywords:
        if kw.arg == name:
            return literal(kw.value)
    return None


def has_auth_dependency(node: ast.AST) -> bool:
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            name = call_name(child.func)
            short = name.rsplit(".", 1)[-1] if name else None
            if name in AUTH_CALL_NAMES or short in AUTH_CALL_NAMES:
                return True
    return False


def join_path(prefix: str, path: str) -> str:
    if not prefix and not path:
        return "/"
    if path == "/":
        return normalize_slashes(prefix or "/")
    return normalize_slashes("/" + "/".join(part.strip("/") for part in (prefix, path) if part))


def normalize_slashes(path: str) -> str:
    return re.sub(r"/{2,}", "/", path) or "/"


def normalize_path(path: str) -> str:
    path = normalize_slashes(path.split("?", 1)[0]).rstrip("/") or "/"
    path = re.sub(r"\{[^}/]+\}", "{}", path)
    return path


def path_aliases(path: str) -> set[str]:
    normalized = normalize_path(path)
    aliases = {normalized}
    stripped = {normalized}
    for prefix in SERVICE_PREFIXES:
        if normalized == prefix:
            stripped.add("/")
        elif normalized.startswith(prefix + "/"):
            stripped.add(normalize_path(normalized[len(prefix):]))
    aliases.update(stripped)
    for base in tuple(stripped):
        for prefix in SERVICE_PREFIXES:
            aliases.add(normalize_path(join_path(prefix, base)))
    return aliases


def route_alias_keys(method: str, path: str) -> set[RouteKey]:
    return {RouteKey(method.upper(), alias) for alias in path_aliases(path)}


def owner_for_source(source: str, tags: Iterable[str] = ()) -> str:
    if "services/api/" in source:
        return "api-gateway"
    if "layer1-ingestion" in source:
        return "layer1-ingestion"
    if "layer2-extraction" in source:
        return "layer2-extraction"
    if "layer3-knowledge" in source:
        return "layer3-knowledge"
    if "layer4-agents" in source:
        return "layer4-agents"
    if "layer5-ground-truth" in source:
        return "layer5-ground-truth"
    if "layer6-benchmarks" in source:
        return "layer6-benchmarks"
    if "layer7-billing" in source:
        return "layer7-billing"
    for tag in tags:
        if tag:
            return str(tag)
    return "unknown"


def extract_router_prefixes(tree: ast.Module) -> dict[str, str]:
    prefixes: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Assign) and isinstance(node.value, ast.Call):
            if call_name(node.value.func) != "APIRouter":
                continue
            prefix = kw_literal(node.value, "prefix") or ""
            for target in node.targets:
                if isinstance(target, ast.Name):
                    prefixes[target.id] = str(prefix)
    return prefixes


def extract_routes_from_file(path: Path) -> list[ImplementedRoute]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        raise RuntimeError(f"failed to parse {path}: {exc}") from exc
    prefixes = extract_router_prefixes(tree)
    routes: list[ImplementedRoute] = []
    source = path.as_posix()
    for node in ast.walk(tree):
        if not isinstance(node, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        function_auth = has_auth_dependency(node)
        for deco in node.decorator_list:
            if not isinstance(deco, ast.Call) or not isinstance(deco.func, ast.Attribute):
                continue
            method = deco.func.attr.lower()
            if method not in HTTP_METHODS:
                continue
            router_name = call_name(deco.func.value) or ""
            route_path = deco.args and literal(deco.args[0]) or "/"
            if not isinstance(route_path, str):
                route_path = "/"
            full_path = join_path(prefixes.get(router_name, ""), route_path)
            tags = kw_literal(deco, "tags") or []
            if not isinstance(tags, list):
                tags = []
            routes.append(
                ImplementedRoute(
                    method=method.upper(),
                    path=full_path,
                    source=source,
                    function=node.name,
                    owner=owner_for_source(source, tags),
                    auth_present=function_auth or has_auth_dependency(deco),
                    include_in_schema=truthy_kw(deco, "include_in_schema", default=True),
                    deprecated=truthy_kw(deco, "deprecated", default=False),
                    line=getattr(node, "lineno", 0),
                )
            )
    return routes


def discover_route_files(repo_root: Path) -> list[Path]:
    files: set[Path] = set()
    for pattern in ROUTE_GLOBS:
        files.update(repo_root.glob(pattern))
    return sorted(p for p in files if p.is_file() and p.name != "__init__.py")


def load_openapi_routes(repo_root: Path) -> list[OpenApiRoute]:
    routes: list[OpenApiRoute] = []
    for spec_path in sorted(repo_root.glob(OPENAPI_GLOB)):
        data = json.loads(spec_path.read_text(encoding="utf-8"))
        global_security = bool(data.get("security"))
        for raw_path, path_item in (data.get("paths") or {}).items():
            if not isinstance(path_item, dict):
                continue
            for method, operation in path_item.items():
                if method.lower() not in HTTP_METHODS or not isinstance(operation, dict):
                    continue
                tags = operation.get("tags") or []
                if not isinstance(tags, list):
                    tags = []
                owner = operation.get("x-route-owner") or operation.get("x-owner") or owner_for_source(spec_path.as_posix(), tags)
                auth_declared = global_security or any(key in operation for key in SECURITY_KEYS)
                desc = " ".join(str(operation.get(k, "")) for k in ("summary", "description")).lower()
                if "requires a tenant-scoped bearer token" in desc or "requires authentication" in desc:
                    auth_declared = True
                routes.append(
                    OpenApiRoute(
                        method=method.upper(),
                        path=raw_path,
                        source=spec_path.as_posix(),
                        operation_id=str(operation.get("operationId") or ""),
                        owner=str(owner or ""),
                        auth_declared=auth_declared,
                        deprecated=bool(operation.get("deprecated")),
                        internal=bool(operation.get("x-internal")),
                    )
                )
    return routes


def load_yaml(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if yaml is None:
        raise RuntimeError("PyYAML is required to read route contract YAML files")
    return yaml.safe_load(path.read_text(encoding="utf-8")) or {}


def is_allowlisted(route: ImplementedRoute, allowlist: list[dict[str, Any]]) -> bool:
    for item in allowlist:
        method = str(item.get("method", "*")).upper()
        pattern = str(item.get("path", ""))
        if method not in {"*", route.method}:
            continue
        if any(fnmatch.fnmatch(alias, pattern) for alias in path_aliases(route.path)):
            return True
    return False


def load_deprecation_keys(repo_root: Path) -> set[str]:
    keys: set[str] = set()
    dep_dir = repo_root / DEPRECATIONS_DIR
    if not dep_dir.exists():
        return keys
    for path in dep_dir.glob("*.json"):
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue
        entries = data.get("entries") if isinstance(data, dict) else None
        if isinstance(entries, list):
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                key = entry.get("key")
                method = entry.get("method")
                route_path = entry.get("path")
                if key:
                    keys.add(str(key).upper())
                if method and route_path:
                    keys.add(f"{str(method).upper()} {normalize_path(str(route_path))}")
    return keys


def route_in_docs(route: ImplementedRoute, documented_keys: set[RouteKey]) -> bool:
    return any(alias in documented_keys for alias in route_alias_keys(route.method, route.path))


def docs_have_impl(route: OpenApiRoute, implemented_keys: set[RouteKey]) -> bool:
    return any(alias in implemented_keys for alias in route_alias_keys(route.method, route.path))


def run_frontend_route_audit(repo_root: Path) -> str:
    extract = subprocess.run(
        [sys.executable, "scripts/extract-routes-audit.py"],
        cwd=repo_root,
        text=True,
        capture_output=True,
    )
    if extract.returncode != 0:
        sys.stdout.write(extract.stdout)
        sys.stderr.write(extract.stderr)
        raise RuntimeError("frontend route audit extraction failed")
    cmd = [sys.executable, "scripts/check-route-audit-freshness.py", "--repo-root", str(repo_root)]
    result = subprocess.run(cmd, cwd=repo_root, text=True, capture_output=True)
    if result.returncode != 0:
        sys.stdout.write(result.stdout)
        sys.stderr.write(result.stderr)
        raise RuntimeError("frontend route audit freshness check failed")
    return "\n".join(part for part in (extract.stdout.strip(), result.stdout.strip()) if part)


def apply_baseline(repo_root: Path, report: GateReport) -> dict[str, int]:
    baseline_path = repo_root / BASELINE
    if not baseline_path.exists():
        return {}
    data = json.loads(baseline_path.read_text(encoding="utf-8"))
    counts: dict[str, int] = {}
    for attr in (
        "missing_openapi_coverage",
        "undocumented_public_routes",
        "auth_mismatches",
        "deprecated_routes_missing_registry",
        "missing_ownership_metadata",
    ):
        known = set(data.get(attr) or [])
        current = list(getattr(report, attr))
        filtered = [item for item in current if item not in known]
        setattr(report, attr, filtered)
        counts[attr] = len(current) - len(filtered)
    return counts


def relativize_report_sources(repo_root: Path, routes: list[ImplementedRoute] | list[OpenApiRoute]) -> None:
    root = repo_root.as_posix().rstrip("/") + "/"
    for route in routes:
        if route.source.startswith(root):
            route.source = route.source[len(root):]


def write_artifacts(repo_root: Path, report: GateReport) -> None:
    out_dir = repo_root / ARTIFACT_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "router-contract-audit.json").write_text(json.dumps(asdict(report), indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = ["# Router Contract Audit", ""]
    md.append(f"- Documented routes: {len(report.documented_routes)}")
    md.append(f"- Implemented routes: {len(report.implemented_routes)}")
    md.append(f"- Missing OpenAPI coverage: {len(report.missing_openapi_coverage)}")
    md.append(f"- Undocumented public routes: {len(report.undocumented_public_routes)}")
    md.append(f"- Auth mismatches: {len(report.auth_mismatches)}")
    md.append(f"- Deprecated routes missing registry entries: {len(report.deprecated_routes_missing_registry)}")
    md.append(f"- Missing ownership metadata: {len(report.missing_ownership_metadata)}")
    md.append("")
    for title, items in [
        ("Missing OpenAPI coverage", report.missing_openapi_coverage),
        ("Undocumented public routes", report.undocumented_public_routes),
        ("Auth mismatches", report.auth_mismatches),
        ("Deprecated routes missing registry entries", report.deprecated_routes_missing_registry),
        ("Missing ownership metadata", report.missing_ownership_metadata),
    ]:
        md.extend([f"## {title}", ""])
        if not items:
            md.append("None.")
        else:
            md.extend(f"- {item}" for item in items[:500])
        md.append("")
    (out_dir / "router-contract-audit.md").write_text("\n".join(md), encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument("--skip-frontend-audit", action="store_true")
    args = parser.parse_args(argv)
    repo_root = args.repo_root.resolve()

    allowlist = load_yaml(repo_root / ALLOWLIST).get("allowlist", [])
    if not isinstance(allowlist, list):
        allowlist = []
    deprecation_keys = load_deprecation_keys(repo_root)

    implemented = [route for file in discover_route_files(repo_root) for route in extract_routes_from_file(file)]
    documented = load_openapi_routes(repo_root)
    relativize_report_sources(repo_root, implemented)
    relativize_report_sources(repo_root, documented)

    implemented_keys = {alias for route in implemented for alias in route_alias_keys(route.method, route.path)}
    documented_keys = {alias for route in documented for alias in route_alias_keys(route.method, route.path)}

    report = GateReport(
        documented_routes=[asdict(route) for route in documented],
        implemented_routes=[asdict(route) for route in implemented],
    )

    for route in documented:
        if not route.internal and not docs_have_impl(route, implemented_keys):
            report.missing_openapi_coverage.append(f"{route.method} {route.path} [{route.source}]")
        if not route.owner or route.owner == "unknown":
            report.missing_ownership_metadata.append(f"{route.method} {route.path} [{route.source}]")
        if route.deprecated and f"{route.method} {normalize_path(route.path)}".upper() not in deprecation_keys:
            report.deprecated_routes_missing_registry.append(f"{route.method} {route.path} [{route.source}]")

    for route in implemented:
        documented_match = route_in_docs(route, documented_keys)
        internal = not route.include_in_schema
        deprecated_key = f"{route.method} {route.key.path}".upper()
        if route.deprecated and deprecated_key not in deprecation_keys:
            report.deprecated_routes_missing_registry.append(f"{route.method} {route.path} [{route.source}:{route.line}]")
        if not route.owner or route.owner == "unknown":
            report.missing_ownership_metadata.append(f"{route.method} {route.path} [{route.source}:{route.line}]")
        if not documented_match and not internal and not is_allowlisted(route, allowlist):
            report.undocumented_public_routes.append(f"{route.method} {route.path} [{route.source}:{route.line}]")
        if not route.auth_present and not is_allowlisted(route, allowlist) and not internal:
            report.auth_mismatches.append(f"{route.method} {route.path} missing route auth dependency [{route.source}:{route.line}]")

    if not args.skip_frontend_audit:
        try:
            report.frontend_route_audit = run_frontend_route_audit(repo_root)
        except RuntimeError as exc:
            report.frontend_route_audit = str(exc)
            report.auth_mismatches.append(str(exc))

    # Stable ordering for deterministic artifacts.
    for attr in (
        "missing_openapi_coverage",
        "undocumented_public_routes",
        "auth_mismatches",
        "deprecated_routes_missing_registry",
        "missing_ownership_metadata",
    ):
        setattr(report, attr, sorted(set(getattr(report, attr))))

    baseline_counts = apply_baseline(repo_root, report)
    write_artifacts(repo_root, report)

    print("Router contract gate summary")
    print(f"  documented routes: {len(documented)}")
    print(f"  implemented routes: {len(implemented)}")
    if baseline_counts:
        print("  baseline suppressions: " + ", ".join(f"{key}={value}" for key, value in sorted(baseline_counts.items())))
    print(f"  artifact: {ARTIFACT_DIR / 'router-contract-audit.json'}")
    failures = (
        report.missing_openapi_coverage
        + report.undocumented_public_routes
        + report.auth_mismatches
        + report.deprecated_routes_missing_registry
        + report.missing_ownership_metadata
    )
    if failures:
        print("FAIL: router contract gate found route drift:")
        for failure in failures[:100]:
            print(f"  - {failure}")
        if len(failures) > 100:
            print(f"  ... {len(failures) - 100} more; see {ARTIFACT_DIR / 'router-contract-audit.md'}")
        return 1
    print("PASS: router contract gate passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
