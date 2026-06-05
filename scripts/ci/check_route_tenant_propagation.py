"""Static AST gate for tenant propagation in FastAPI route handlers.

Ensures authenticated tenant context variables are forwarded to service/repository calls.
"""
from __future__ import annotations
import argparse
import ast, json, re, subprocess, sys
from pathlib import Path

ROUTE_ROOTS = [Path("services"), Path("value_fabric")]
SKIP_PARTS = {"/tests/", "/.venv/", "/site-packages/"}

class RouteTenantVisitor(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.violations: list[dict[str, object]] = []

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        if not self._is_route_handler(node):
            return
        tenant_vars = {"tenant_id", "effective_tenant_id"}
        tenant_vars |= {a.arg for a in node.args.args if "tenant" in a.arg and "id" in a.arg}
        context_vars = {
            a.arg
            for a in node.args.args
            if a.arg in {"auth", "context", "ctx", "_ctx", "current_user"}
            or self._annotation_name(a.annotation) in {"RequestContext", "TokenPayload", "User"}
        }
        tenant_bound_owners = self._tenant_bound_owners(node, tenant_vars, context_vars)
        tenant_bound_values = self._tenant_bound_values(node, tenant_vars, context_vars)
        for call in [n for n in ast.walk(node) if isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)]:
            owner = self._owner_name(call.func.value)
            if owner not in {"service", "repo", "repository", "manager"}:
                continue
            if owner in tenant_bound_owners:
                continue
            if call.func.attr.startswith("_"):
                continue
            has_tenant_bound_value = any(
                isinstance(arg, ast.Name) and arg.id in tenant_bound_values for arg in call.args
            )
            has_tenant_kw = any(
                kw.arg == "tenant_id" and self._is_tenant_expr(kw.value, tenant_vars, context_vars)
                for kw in call.keywords
                if kw.arg
            )
            has_tenant_pos = any(self._is_tenant_expr(arg, tenant_vars, context_vars) for arg in call.args)
            if not (has_tenant_kw or has_tenant_pos or has_tenant_bound_value):
                self.violations.append({
                    "file": str(self.path),
                    "line": call.lineno,
                    "handler": node.name,
                    "call": ast.unparse(call.func),
                    "message": "Route handler service/repository call is missing authenticated tenant propagation",
                })

    def _owner_name(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        return None

    def _annotation_name(self, node: ast.AST | None) -> str | None:
        if isinstance(node, ast.Name):
            return node.id
        if isinstance(node, ast.Attribute):
            return node.attr
        if isinstance(node, ast.Subscript):
            return self._annotation_name(node.value)
        return None

    def _is_tenant_expr(
        self,
        node: ast.AST,
        tenant_vars: set[str],
        context_vars: set[str],
    ) -> bool:
        if isinstance(node, ast.Name):
            return node.id in tenant_vars
        if isinstance(node, ast.Attribute):
            return (
                node.attr == "tenant_id"
                and isinstance(node.value, ast.Name)
                and node.value.id in context_vars
            )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "str":
            return len(node.args) == 1 and self._is_tenant_expr(node.args[0], tenant_vars, context_vars)
        return False

    def _tenant_bound_owners(
        self,
        node: ast.AsyncFunctionDef,
        tenant_vars: set[str],
        context_vars: set[str],
    ) -> set[str]:
        owners: set[str] = set()
        for stmt in ast.walk(node):
            if not isinstance(stmt, ast.Assign) or not isinstance(stmt.value, ast.Call):
                continue
            target_names = [target.id for target in stmt.targets if isinstance(target, ast.Name)]
            if not target_names:
                continue
            has_tenant_arg = any(self._is_tenant_expr(arg, tenant_vars, context_vars) for arg in stmt.value.args)
            has_tenant_kw = any(
                kw.arg == "tenant_id" and self._is_tenant_expr(kw.value, tenant_vars, context_vars)
                for kw in stmt.value.keywords
                if kw.arg
            )
            if has_tenant_arg or has_tenant_kw:
                owners.update(name for name in target_names if name in {"service", "repo", "repository", "manager"})
        return owners

    def _tenant_bound_values(
        self,
        node: ast.AsyncFunctionDef,
        tenant_vars: set[str],
        context_vars: set[str],
    ) -> set[str]:
        values: set[str] = set()
        for stmt in ast.walk(node):
            if not isinstance(stmt, ast.Assign) or not isinstance(stmt.value, ast.Call):
                continue
            target_names = [target.id for target in stmt.targets if isinstance(target, ast.Name)]
            if not target_names:
                continue
            has_tenant_arg = any(self._is_tenant_expr(arg, tenant_vars, context_vars) for arg in stmt.value.args)
            has_tenant_kw = any(
                kw.arg == "tenant_id" and self._is_tenant_expr(kw.value, tenant_vars, context_vars)
                for kw in stmt.value.keywords
                if kw.arg
            )
            if has_tenant_arg or has_tenant_kw:
                values.update(target_names)
        return values

    def _is_route_handler(self, node: ast.AsyncFunctionDef) -> bool:
        for deco in node.decorator_list:
            if isinstance(deco, ast.Call) and isinstance(deco.func, ast.Attribute) and deco.func.attr in {"get", "post", "put", "patch", "delete"}:
                return True
            if isinstance(deco, ast.Attribute) and deco.attr in {"get", "post", "put", "patch", "delete"}:
                return True
        return False


def iter_route_files() -> list[Path]:
    out = []
    for root in ROUTE_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            s = str(path).replace("\\", "/")
            if any(p in s for p in SKIP_PARTS):
                continue
            if "/api/routes/" in s or "/app/routers/" in s:
                out.append(path)
    return out


def changed_lines(base_ref: str) -> dict[str, set[int]]:
    diff = subprocess.run(
        ["git", "diff", "--unified=0", "--no-color", f"{base_ref}...HEAD", "--", "*.py"],
        capture_output=True,
        text=True,
        check=False,
    ).stdout
    out: dict[str, set[int]] = {}
    cur: str | None = None
    for line in diff.splitlines():
        if line.startswith("+++ b/"):
            cur = line[6:]
            out.setdefault(cur, set())
        elif line.startswith("@@") and cur:
            m = re.search(r"\+(\d+)(?:,(\d+))?", line)
            if not m:
                continue
            start = int(m.group(1))
            count = int(m.group(2) or "1")
            for n in range(start, start + count):
                out[cur].add(n)
    return out


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-ref")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Scan all route files, ignoring --base-ref line scoping.",
    )
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    touched = changed_lines(args.base_ref) if args.base_ref and not args.strict else None
    violations: list[dict[str, object]] = []
    scanned = 0
    for path in iter_route_files():
        scanned += 1
        text = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(text, filename=str(path))
        except SyntaxError:
            continue
        v = RouteTenantVisitor(path)
        v.visit(tree)
        if touched is None:
            violations.extend(v.violations)
        else:
            rel = str(path).replace("\\", "/")
            line_scope = touched.get(rel)
            if not line_scope:
                continue
            violations.extend([i for i in v.violations if int(i["line"]) in line_scope])

    Path("artifacts").mkdir(exist_ok=True)
    report = {"scanned_files": scanned, "violation_count": len(violations), "violations": violations}
    Path("artifacts/route-tenant-propagation.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
    md = ["# Route Tenant Propagation Report", "", f"Scanned files: **{scanned}**", f"Violations: **{len(violations)}**", ""]
    for item in violations[:200]:
        md.append(f"- `{item['file']}:{item['line']}` `{item['handler']}` -> `{item['call']}`")
    Path("artifacts/route-tenant-propagation.md").write_text("\n".join(md), encoding="utf-8")

    if violations:
        print(f"FAIL: {len(violations)} route tenant propagation violations")
        return 1
    print("PASS: Route tenant propagation static checks passed")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
