#!/usr/bin/env python3
from __future__ import annotations

import ast
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
POSTGRES_SUITE = (
    ROOT / "tests" / "production_readiness" / "test_postgres_production_invariants.py"
)
BYPASS_SUITE = (
    ROOT / "tests" / "production_readiness" / "test_db_adapter_bypass_conformance.py"
)
REQUIRED_INVARIANTS = {
    "rls": ("rls", "tenant"),
    "migrations": ("migration", "alembic"),
    "constraints": ("constraint",),
    "indexes": ("index",),
    "tenant context hooks": ("tenant", "app.tenant_id"),
    "transaction semantics": ("transaction", "commit", "rollback"),
}


def _markers_for(node: ast.AST) -> set[str]:
    markers: set[str] = set()
    for decorator in getattr(node, "decorator_list", []):
        current = decorator
        if isinstance(current, ast.Call):
            current = current.func
        parts: list[str] = []
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        dotted = ".".join(reversed(parts))
        if dotted.startswith("pytest.mark."):
            markers.add(dotted.removeprefix("pytest.mark."))
    return markers


def _test_functions(path: Path) -> list[ast.FunctionDef | ast.AsyncFunctionDef]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    return [
        node
        for node in ast.walk(tree)
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        and node.name.startswith("test_")
    ]


def main() -> int:
    errors: list[str] = []
    for required in (POSTGRES_SUITE, BYPASS_SUITE):
        if not required.exists():
            errors.append(
                f"Missing required DB production-readiness suite: {required.relative_to(ROOT)}"
            )

    if not errors:
        postgres_tests = _test_functions(POSTGRES_SUITE)
        if not postgres_tests:
            errors.append(f"{POSTGRES_SUITE.relative_to(ROOT)} contains no tests")
        for node in postgres_tests:
            markers = _markers_for(node)
            missing = {
                "postgres_only",
                "requires_postgres",
                "production_db_invariant",
            } - markers
            if missing:
                errors.append(
                    f"{POSTGRES_SUITE.relative_to(ROOT)}::{node.name} missing marker(s): {', '.join(sorted(missing))}"
                )

        combined = "\n".join(
            path.read_text(encoding="utf-8").lower()
            for path in (POSTGRES_SUITE, BYPASS_SUITE)
        )
        for label, tokens in REQUIRED_INVARIANTS.items():
            if not any(token in combined for token in tokens):
                errors.append(
                    f"No production DB readiness coverage references {label}."
                )

        for path in ROOT.rglob("test_*.py"):
            if any(
                part in {".venv", "node_modules", "quarantine"} for part in path.parts
            ):
                continue
            text = path.read_text(encoding="utf-8").lower()
            if (
                "production_db_invariant" in text
                and "sqlite" in text
                and "postgres_only" not in text
            ):
                errors.append(
                    f"{path.relative_to(ROOT)} validates a production DB invariant with SQLite but is not postgres_only."
                )

    if errors:
        print("db-production-readiness split violations:")
        for error in errors:
            print(f" - {error}")
        return 1
    print("DB production-readiness split check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
