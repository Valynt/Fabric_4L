from __future__ import annotations

import ast
import re
from dataclasses import dataclass
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2] / "src" / "layer4_agents"

FIELD_NAMES = {
    "sync_status",
    "operational_status",
    "observed_sync_status",
    "error_class",
    "last_known_good_at",
}

# Only these modules may mutate reducer/legacy status fields. Everyone else must
# route through apply_observation (or, for migrations, use SQL in the listed file).
ALLOWLIST: set[str] = {
    # The reducer and its single sanctioned application helper.
    "integration/connectors/core/state.py",
    # Model definition and defaults.
    "models/integration.py",
    # Backfill / drift-repair migrations.
    "migrations/versions/043_add_integration_operational_status_fields.py",
    "migrations/versions/044_repair_integration_state_drift.py",
}

# Regex for simple cases the AST visitor may miss (e.g., dynamic setattr or SQL).
TEXT_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    # setattr(integration, "sync_status", ...)
    (
        "setattr(integration, ...)",
        re.compile(
            r"setattr\s*\(\s*\bintegration\b\s*,\s*['\"]?\b(" + "|".join(FIELD_NAMES) + r")\b['\"]?"
        ),
    ),
    # update(Integration).values(sync_status=...)
    (
        "update(Integration).values()",
        re.compile(
            r"update\s*\(\s*\bIntegration\b\s*\)[^)]*\.\s*values\s*\([^)]*\b("
            + "|".join(FIELD_NAMES)
            + r")\b"
        ),
    ),
]


@dataclass(frozen=True)
class _Violation:
    rel: str
    lineno: int
    line: str
    kind: str

    def __str__(self) -> str:
        return f"{self.rel}:{self.lineno}: [{self.kind}] {self.line.strip()}"


class _ReducerWriteVisitor(ast.NodeVisitor):
    def __init__(self, rel: str, source: str) -> None:
        self.rel = rel
        self.lines = source.splitlines()
        self.violations: list[_Violation] = []

    def _field_in_node(self, node: ast.AST) -> str | None:
        if isinstance(node, ast.Name) and node.id in FIELD_NAMES:
            return node.id
        if isinstance(node, ast.Constant) and node.value in FIELD_NAMES:
            return node.value
        return None

    def _is_integration_target(self, node: ast.AST) -> bool:
        return isinstance(node, ast.Name) and node.id == "integration"

    def _check_assignment_target(self, target: ast.AST, kind: str) -> None:
        # attribute assignment: integration.<field> = ...
        if (
            isinstance(target, ast.Attribute)
            and target.attr in FIELD_NAMES
            and self._is_integration_target(target.value)
        ):
            self._add(target.lineno, kind)
        # subscript assignment: integration["<field>"] = ...
        if isinstance(target, ast.Subscript) and self._is_integration_target(target.value):
            field = self._field_in_node(target.slice)
            if field:
                self._add(target.lineno, kind)
        # tuple/unpack assignment containing the field name (rare)
        if isinstance(target, ast.Tuple):
            for elt in target.elts:
                self._check_assignment_target(elt, kind)

    def _add(self, lineno: int, kind: str) -> None:
        line = self.lines[lineno - 1] if 1 <= lineno <= len(self.lines) else ""
        self.violations.append(_Violation(self.rel, lineno, line, kind))

    def visit_Assign(self, node: ast.Assign) -> None:  # noqa: N802
        for target in node.targets:
            self._check_assignment_target(target, "assign")
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:  # noqa: N802
        self._check_assignment_target(node.target, "ann_assign")
        self.generic_visit(node)

    def visit_AugAssign(self, node: ast.AugAssign) -> None:  # noqa: N802
        self._check_assignment_target(node.target, "aug_assign")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        # Integration(sync_status=..., operational_status=...)
        if isinstance(func, ast.Name) and func.id == "Integration":
            for kw in node.keywords:
                if kw.arg in FIELD_NAMES:
                    lineno = kw.value.lineno if hasattr(kw.value, "lineno") else node.lineno
                    self._add(lineno, "constructor_kw")
        self.generic_visit(node)


def test_integration_maps_reducer_columns() -> None:
    from layer4_agents.models.integration import Integration

    mapped_columns = set(Integration.__mapper__.columns.keys())

    assert {
        "operational_status",
        "observed_sync_status",
        "error_class",
        "last_known_good_at",
    }.issubset(mapped_columns)


class TestReducerStatusWritesEnforced:
    """Repo-level guard: Integration reducer/legacy status fields must only be mutated via apply_observation."""

    def test_no_direct_assignment_outside_allowlist(self) -> None:
        src_root = ROOT
        assert src_root.exists(), f"Source root not found: {src_root}"

        files = [
            p
            for p in src_root.rglob("*.py")
            if "__pycache__" not in p.parts and "tests" not in p.parts
        ]

        violations: list[_Violation] = []

        for path in files:
            rel = path.relative_to(src_root).as_posix()
            if rel in ALLOWLIST:
                continue

            source = path.read_text(encoding="utf-8")

            # AST pass
            try:
                tree = ast.parse(source)
            except SyntaxError as exc:
                pytest.fail(f"Syntax error in {rel}: {exc}")
            visitor = _ReducerWriteVisitor(rel, source)
            visitor.visit(tree)
            violations.extend(visitor.violations)

            # Text pass for dynamic patterns the AST may miss.
            for kind, pattern in TEXT_PATTERNS:
                for lineno, line in enumerate(source.splitlines(), start=1):
                    if pattern.search(line):
                        violations.append(_Violation(rel, lineno, line, kind))

        assert (
            not violations
        ), "Direct reducer/legacy status writes found outside allowlist:\n" + "\n".join(
            str(v) for v in violations
        )

    def test_apply_observation_is_the_only_writer(self) -> None:
        """Only state.py defines apply_observation and assigns reducer columns."""
        state_path = ROOT / "integration" / "connectors" / "core" / "state.py"
        assert state_path.exists()
        source = state_path.read_text(encoding="utf-8")

        # apply_observation should be defined here.
        assert "def apply_observation(" in source

        # No other module should define it (cheap check).
        for path in ROOT.rglob("*.py"):
            if "__pycache__" in path.parts or "tests" in path.parts:
                continue
            if path == state_path:
                continue
            if "def apply_observation(" in path.read_text(encoding="utf-8"):
                pytest.fail(f"Duplicate apply_observation definition in {path}")
