#!/usr/bin/env python3
"""Static guard for Layer 3 Neo4j tenant-scope enforcement.

This script is intentionally conservative. It does not parse Cypher fully; it
blocks obvious raw tenant-owned graph access and documents reviewed global
escape hatches. Runtime execution should still prefer ``ScopedQuery`` objects
from ``TenantScopedCypher`` or explicit ``SystemCypher`` factories.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from dataclasses import dataclass
from pathlib import Path

FALLBACK_TENANT_LABELS = {
    "Account",
    "Battlecard",
    "Benchmark",
    "BenchmarkDataset",
    "Capability",
    "CaseStudy",
    "Community",
    "Competitor",
    "Customer",
    "Entity",
    "Evidence",
    "Formula",
    "FormulaVersion",
    "Industry",
    "Insight",
    "Model",
    "PainSignal",
    "Persona",
    "Product",
    "ROICalculation",
    "ROITemplate",
    "Segment",
    "Signal",
    "Source",
    "UseCase",
    "ValueDriver",
    "ValueModel",
    "ValuePack",
    "ValueTree",
    "Variable",
}


def _load_tenant_labels(root: Path | None = None) -> set[str]:
    """Load tenant-owned Neo4j labels from the shared registry, with a CI-safe fallback."""
    if root is not None:
        shared_src = root / "packages" / "shared" / "src"
        if shared_src.exists() and str(shared_src) not in sys.path:
            sys.path.insert(0, str(shared_src))
    try:
        from value_fabric.shared.identity.isolation import DEFAULT_TENANT_LABEL_POLICY

        return set(DEFAULT_TENANT_LABEL_POLICY.tenant_labels)
    except Exception:
        return set(FALLBACK_TENANT_LABELS)


TENANT_LABELS = _load_tenant_labels()

SCANNED_ROOTS = (
    "services/layer3-knowledge/src/analytics",
    "services/layer3-knowledge/src/retrieval",
    "services/layer3-knowledge/src/ingestion",
    "services/layer3-knowledge/src/services",
    "services/layer3-knowledge/src/api/routes",
    "value_fabric/layer3/analytics",
    "value_fabric/layer3/retrieval",
    "value_fabric/layer3/ingestion",
    "value_fabric/layer3/services",
    "value_fabric/layer3/api/routes",
)

ALLOWED_PATH_FRAGMENTS = (
    "/schema/",
    "/bootstrap/",
    "/migrations/",
)

SYSTEM_SCOPE_MARKERS = (
    "SystemCypher.",
    "QueryScope.SYSTEM",
    "QueryScope.HEALTH",
    "QueryScope.SCHEMA",
    "QueryScope.MIGRATION",
    "QueryScope.BACKUP",
    "tenant-scope: system",
    "tenant-scope: migration",
    "tenant-scope: schema",
    "tenant-scope: health",
    "tenant-scope: backup",
)

TENANT_SCOPE_MARKERS = (
    "TenantScopedCypher",
    "ScopedQuery",
    "custom_tenant_query",
    "_run_scoped",
    "_query_tuple",
    "strict-scoped-query-execution",
    "scoped.cypher",
    "scoped.params",
    "tenant_id",
    "tenantId",
    "$_tenant_id",
    "$tenant_id",
    "$tenantId",
)

MATCH_LABEL_PATTERN = re.compile(
    r"\b(?:MATCH|OPTIONAL\s+MATCH|MERGE|CREATE)\s*\([^)]*:\s*([A-Za-z_][A-Za-z0-9_]*)",
    re.IGNORECASE | re.DOTALL,
)
RUN_CALL_PATTERN = re.compile(r"\.run\s*\(")
DIRECT_NEO4J_RUN_NAMES = {"session", "raw_session", "tx", "transaction"}
CYPHER_KEYWORDS = re.compile(
    r"\b(MATCH|OPTIONAL\s+MATCH|MERGE|CREATE|DELETE|DETACH\s+DELETE|CALL\s+gds|CALL\s+db\.index)\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    severity: str
    message: str
    snippet: str

    def format(self, root: Path) -> str:
        rel = self.path.relative_to(root)
        return f"{self.severity}: {rel}:{self.line}: {self.message}\n    {self.snippet}"


def _line_for_offset(text: str, offset: int) -> int:
    return text.count("\n", 0, offset) + 1


def _safe_constant_value(node: ast.AST) -> str | None:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            else:
                parts.append("${expr}")
        return "".join(parts)
    return None


def _iter_python_string_literals(path: Path) -> list[tuple[int, str]]:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError as exc:
        return [(exc.lineno or 1, f"<syntax error: {exc.msg}>")]
    values: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        value = _safe_constant_value(node)
        if value and CYPHER_KEYWORDS.search(value):
            values.append((getattr(node, "lineno", 1), value))
    return values


def _is_reviewed_system_scope(snippet: str, file_text: str, line: int) -> bool:
    if any(marker in snippet for marker in SYSTEM_SCOPE_MARKERS):
        return True
    lines = file_text.splitlines()
    start = max(0, line - 4)
    end = min(len(lines), line + 3)
    window = "\n".join(lines[start:end])
    return any(marker in window for marker in SYSTEM_SCOPE_MARKERS)


def _is_tenant_scoped(snippet: str, file_text: str, line: int) -> bool:
    if any(marker in snippet for marker in TENANT_SCOPE_MARKERS):
        return True
    lines = file_text.splitlines()
    start = max(0, line - 12)
    end = min(len(lines), line + 12)
    window = "\n".join(lines[start:end])
    return any(marker in window for marker in TENANT_SCOPE_MARKERS)


def _tenant_labels_in(snippet: str) -> set[str]:
    return {label for label in MATCH_LABEL_PATTERN.findall(snippet) if label in TENANT_LABELS}


def _is_high_risk_layer3_runtime(rel: str) -> bool:
    return rel.startswith((
        "services/layer3-knowledge/src/api/routes/",
        "services/layer3-knowledge/src/services/",
        "services/layer3-knowledge/src/agents/",
        "services/layer3-knowledge/src/analytics/",
        "value_fabric/layer3/api/routes/",
        "value_fabric/layer3/services/",
        "value_fabric/layer3/agents/",
        "value_fabric/layer3/analytics/",
    ))


def _run_owner_name(node: ast.AST) -> str | None:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return node.attr
    return None


def _iter_direct_neo4j_run_calls(path: Path) -> list[tuple[int, int]]:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    except SyntaxError as exc:
        return [(exc.lineno or 1, 0)]

    calls: list[tuple[int, int]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        func = node.func
        if not isinstance(func, ast.Attribute) or func.attr != "run":
            continue
        owner = _run_owner_name(func.value)
        if owner in DIRECT_NEO4J_RUN_NAMES:
            calls.append((node.lineno, node.col_offset))
    return calls


def scan_file(path: Path, root: Path) -> list[Finding]:
    rel = str(path.relative_to(root))
    if any(fragment in rel for fragment in ALLOWED_PATH_FRAGMENTS):
        return []

    text = path.read_text(encoding="utf-8")
    findings: list[Finding] = []

    for line, snippet in _iter_python_string_literals(path):
        labels = _tenant_labels_in(snippet)
        if not labels:
            continue
        if _is_reviewed_system_scope(snippet, text, line):
            continue
        if _is_tenant_scoped(snippet, text, line):
            continue
        findings.append(
            Finding(
                path=path,
                line=line,
                severity="ERROR",
                message=f"raw Cypher touches tenant-owned label(s) {sorted(labels)} without tenant scope marker",
                snippet=" ".join(snippet.strip().split())[:240],
            )
        )

    direct_neo4j_run_lines: set[int] = set()
    if _is_high_risk_layer3_runtime(rel):
        for line, _col in _iter_direct_neo4j_run_calls(path):
            direct_neo4j_run_lines.add(line)
            findings.append(
                Finding(
                    path=path,
                    line=line,
                    severity="ERROR",
                    message="direct Neo4j run call is forbidden in high-risk Layer 3 runtime modules; use run_scoped_query or run_validated_query",
                    snippet=text.splitlines()[line - 1].strip()[:240],
                )
            )

    for match in RUN_CALL_PATTERN.finditer(text):
        line = _line_for_offset(text, match.start())
        if line in direct_neo4j_run_lines:
            continue
        if _is_reviewed_system_scope("", text, line) or _is_tenant_scoped("", text, line):
            continue
        findings.append(
            Finding(
                path=path,
                line=line,
                severity="WARN",
                message="Neo4j run call lacks nearby scoped-query or tenant-scope marker",
                snippet=text.splitlines()[line - 1].strip()[:240],
            )
        )

    return findings


def discover_files(root: Path, paths: list[str]) -> list[Path]:
    targets = paths or list(SCANNED_ROOTS)
    files: list[Path] = []
    for target in targets:
        path = root / target
        if path.is_file() and path.suffix == ".py":
            files.append(path)
        elif path.is_dir():
            files.extend(sorted(path.rglob("*.py")))
    return sorted(set(files))


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", default=".", help="repository root")
    parser.add_argument("--paths", nargs="*", default=[], help="specific files or directories to scan")
    parser.add_argument(
        "--warnings-as-errors",
        action="store_true",
        help="treat unclassified session.run warnings as errors",
    )
    args = parser.parse_args(argv)

    root = Path(args.root).resolve()
    global TENANT_LABELS
    TENANT_LABELS = _load_tenant_labels(root)
    findings: list[Finding] = []
    for path in discover_files(root, args.paths):
        findings.extend(scan_file(path, root))

    errors = [f for f in findings if f.severity == "ERROR"]
    warnings = [f for f in findings if f.severity == "WARN"]
    for finding in findings:
        print(finding.format(root))

    print(
        f"Layer 3 Cypher scope scan complete: {len(errors)} error(s), {len(warnings)} warning(s), "
        f"{len(findings)} total finding(s)."
    )
    if errors or (args.warnings_as_errors and warnings):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
