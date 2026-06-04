from __future__ import annotations

import ast
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
MIGRATION_ROOTS = (
    Path("services/layer1-ingestion/migrations/versions"),
    Path("services/layer2-extraction/migrations/versions"),
    Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
    Path("services/layer4-agents/migrations/versions"),
    Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
    Path("services/api/migrations/versions"),
)


def _migration_files() -> list[Path]:
    files: list[Path] = []
    for root in MIGRATION_ROOTS:
        files.extend(sorted((REPO_ROOT / root).glob("*.py")))
    return [path for path in files if not path.name.startswith("__")]


def _call_name(node: ast.Call) -> str:
    func = node.func
    if isinstance(func, ast.Attribute):
        return func.attr
    if isinstance(func, ast.Name):
        return func.id
    return ""


def test_non_nullable_existing_column_additions_are_expand_contract_safe() -> None:
    failures: list[str] = []

    for path in _migration_files():
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call) or _call_name(node) != "add_column":
                continue
            call_text = ast.get_source_segment(source, node) or ""
            if "nullable=False" not in call_text:
                continue
            if any(marker in call_text for marker in ("server_default", "default=")):
                continue
            if any(marker in source.lower() for marker in ("backfill", "expand/contract", "phased rollout")):
                continue
            failures.append(f"{path.relative_to(REPO_ROOT)} adds a non-null column without default/backfill evidence")

    assert not failures, "Backward-compatible migration gaps: " + "; ".join(failures)


def test_set_not_null_migrations_check_or_backfill_existing_rows_first() -> None:
    failures: list[str] = []

    for path in _migration_files():
        source = path.read_text(encoding="utf-8")
        if "nullable=False" not in source or "alter_column" not in source:
            continue
        if "new_column_name" in source and "existing_nullable=False" in source:
            continue
        if "server_default" in source:
            continue
        lower = source.lower()
        has_precondition = any(
            marker in lower
            for marker in (
                "where",
                "is null",
                "select",
                "update",
                "backfill",
                "runtimeerror",
                "production approval",
            )
        )
        if not has_precondition:
            failures.append(str(path.relative_to(REPO_ROOT)))

    assert not failures, "SET NOT NULL migrations need precondition/backfill evidence: " + ", ".join(failures)
