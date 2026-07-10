#!/usr/bin/env python3
"""Ensure intentionally unsupported migration downgrades are governed."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
ROLLBACK_RUNBOOK = REPO_ROOT / "docs/operations/runbooks/database-migration-rollback.md"

MIGRATION_ROOTS = (
    Path("services/layer1-ingestion/migrations/versions"),
    Path("services/layer2-extraction/migrations/versions"),
    Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
    Path("services/layer4-agents/migrations/versions"),
    Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
    Path("services/api/migrations/versions"),
)

UNSUPPORTED_MARKERS = (
    "DOWNGRADE_UNSUPPORTED",
    "UNSUPPORTED_DOWNGRADE",
    "production approval",
    "restore from backup",
)

REQUIRED_RUNBOOK_MARKERS = (
    "explicit production approval",
    "restore from backup",
    "forward-fix",
    "rollback strategy",
)


def _downgrade_function(tree: ast.Module) -> ast.FunctionDef | None:
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and node.name == "downgrade":
            return node
    return None


def _raises_unsupported(downgrade: ast.FunctionDef) -> bool:
    for node in ast.walk(downgrade):
        if isinstance(node, ast.Raise):
            text = ast.unparse(node) if hasattr(ast, "unparse") else ""
            if "NotImplemented" in text or "Unsupported" in text or "RuntimeError" in text:
                return True
    return False


def _is_unsupported(source: str) -> bool:
    tree = ast.parse(source)
    downgrade = _downgrade_function(tree)
    if downgrade is None:
        return True
    return _raises_unsupported(downgrade) or any(marker in source for marker in UNSUPPORTED_MARKERS)


def main() -> int:
    if not ROLLBACK_RUNBOOK.exists():
        print(f"ERROR: rollback runbook missing: {ROLLBACK_RUNBOOK.relative_to(REPO_ROOT)}", file=sys.stderr)
        return 1

    runbook = ROLLBACK_RUNBOOK.read_text(encoding="utf-8").lower()
    missing_runbook = [marker for marker in REQUIRED_RUNBOOK_MARKERS if marker not in runbook]
    if missing_runbook:
        print(f"ERROR: rollback runbook missing required markers: {missing_runbook}", file=sys.stderr)
        return 1

    failures: list[str] = []
    for root in MIGRATION_ROOTS:
        for path in sorted((REPO_ROOT / root).glob("*.py")):
            if path.name.startswith("__"):
                continue
            source = path.read_text(encoding="utf-8")
            if not _is_unsupported(source):
                continue
            relative = path.relative_to(REPO_ROOT).as_posix()
            if relative not in runbook:
                failures.append(f"{relative}: unsupported downgrade is not listed in rollback runbook")
            if "explicit production approval" not in source.lower() and relative not in runbook:
                failures.append(f"{relative}: missing explicit production approval documentation")

    if failures:
        print("ERROR: migration rollback policy violations:", file=sys.stderr)
        for failure in failures:
            print(f"  - {failure}", file=sys.stderr)
        return 1

    print("PASS: migration rollback policy is documented and approval-gated")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
