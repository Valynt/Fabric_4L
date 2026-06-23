#!/usr/bin/env python3
"""Fail on raw HTTPException usage in route modules outside explicit allowlist."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ALLOWLIST_PATH = REPO_ROOT / "config" / "ci" / "http_exception_route_allowlist.txt"


def load_allowlist() -> set[str]:
    if not ALLOWLIST_PATH.exists():
        return set()
    out: set[str] = set()
    for line in ALLOWLIST_PATH.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        out.add(line)
    return out


def target_files() -> list[Path]:
    files = list((REPO_ROOT / "services").glob("*/src/**/*.py"))
    files += list((REPO_ROOT / "value_fabric").glob("**/api/routes/**/*.py"))
    return sorted(set(files))


def has_raw_raise_http_exception(tree: ast.AST) -> list[int]:
    lines: list[int] = []
    for n in ast.walk(tree):
        if isinstance(n, ast.Raise) and isinstance(n.exc, ast.Call):
            fn = n.exc.func
            if isinstance(fn, ast.Name) and fn.id == "HTTPException":
                lines.append(n.lineno)
    return lines


def main() -> int:
    allowlist = load_allowlist()
    violations: list[tuple[str, int]] = []

    for file in target_files():
        rel = file.relative_to(REPO_ROOT).as_posix()
        if rel in allowlist:
            continue
        src = file.read_text(encoding="utf-8")
        if "HTTPException" not in src:
            continue
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for ln in has_raw_raise_http_exception(tree):
            violations.append((rel, ln))

    if violations:
        print("FAIL: raw HTTPException usage found in route modules:")
        for rel, ln in violations:
            print(f"  - {rel}:{ln}")
        print(f"Allowlist path: {ALLOWLIST_PATH.relative_to(REPO_ROOT)}")
        return 1

    print("PASS: no raw HTTPException usage in route modules")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
