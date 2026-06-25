#!/usr/bin/env python3
from __future__ import annotations

import ast
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
MATRIX = ROOT / "docs/governance/layer5-tenant-isolation-matrix.md"
API_FILES = [
    ROOT / "services/layer5-ground-truth/src/layer5_ground_truth/api/router.py",
    ROOT
    / "services/layer5-ground-truth/src/layer5_ground_truth/api/model_registry_routes.py",
]

ROW = re.compile(
    r"^\|\s*(GET|POST|PUT|PATCH|DELETE)\s*\|\s*`([^`]+)`\s*\|.*\|\s*(covered|gap)\s*\|\s*$"
)


def _extract_route_from_decorator(dec: ast.AST) -> tuple[str, str] | None:
    """Return (METHOD, route) for a FastAPI router decorator, or None."""
    if (
        isinstance(dec, ast.Call)
        and isinstance(dec.func, ast.Attribute)
        and isinstance(dec.func.value, ast.Name)
        and dec.func.value.id == "router"
    ):
        method = dec.func.attr.upper()
        if (
            dec.args
            and isinstance(dec.args[0], ast.Constant)
            and isinstance(dec.args[0].value, str)
        ):
            route = "/api/v1" + dec.args[0].value
            return method, route
    return None


def _has_caller_dependency(node: ast.AsyncFunctionDef) -> bool:
    """Return True if the function has a `caller: ... = Depends(get_current_user)` default."""
    for arg, default in zip(
        node.args.args[-len(node.args.defaults) :], node.args.defaults
    ):
        if arg.arg != "caller":
            continue
        if (
            isinstance(default, ast.Call)
            and isinstance(default.func, ast.Name)
            and default.func.id == "Depends"
            and default.args
            and isinstance(default.args[0], ast.Name)
            and default.args[0].id == "get_current_user"
        ):
            return True
    return False


def tenant_routes(path: Path) -> set[tuple[str, str]]:
    tree = ast.parse(path.read_text(encoding="utf-8"))
    out: set[tuple[str, str]] = set()
    for node in tree.body:
        if not isinstance(node, ast.AsyncFunctionDef):
            continue

        extracted: tuple[str, str] | None = None
        for dec in node.decorator_list:
            extracted = _extract_route_from_decorator(dec)
            if extracted is not None:
                break

        if extracted is None or not _has_caller_dependency(node):
            continue

        out.add(extracted)
    return out


def matrix_routes() -> tuple[set[tuple[str, str]], list[tuple[str, str]]]:
    present: set[tuple[str, str]] = set()
    gaps: list[tuple[str, str]] = []
    for line in MATRIX.read_text(encoding="utf-8").splitlines():
        m = ROW.match(line)
        if not m:
            continue
        key = (m.group(1), m.group(2))
        present.add(key)
        if m.group(3) == "gap":
            gaps.append(key)
    return present, gaps


def main() -> int:
    discovered = set().union(*(tenant_routes(f) for f in API_FILES))
    mapped, gaps = matrix_routes()

    missing = sorted(discovered - mapped)
    stale = sorted(mapped - discovered)

    if missing or stale or gaps:
        if missing:
            print("Missing Layer 5 tenant-isolation matrix entries:", file=sys.stderr)
            for m, p in missing:
                print(f"  - {m} {p}", file=sys.stderr)
        if stale:
            print("Stale matrix entries (route no longer discovered):", file=sys.stderr)
            for m, p in stale:
                print(f"  - {m} {p}", file=sys.stderr)
        if gaps:
            print("Coverage gaps must be resolved before merge:", file=sys.stderr)
            for m, p in gaps:
                print(f"  - {m} {p}", file=sys.stderr)
        return 1

    print(
        f"Layer 5 tenant-isolation matrix check passed ({len(discovered)} routes mapped)."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
