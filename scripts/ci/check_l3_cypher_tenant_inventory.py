#!/usr/bin/env python3
"""Inventory Layer 3 Cypher execution and enforce tenant-scope classification.

The scanner is intentionally static and conservative: a tenant-owned graph path is
classified as Safe only when the Cypher text (or an approved tenant execution
wrapper) makes tenant scoping visible. Dynamic query construction that cannot be
resolved is classified Unknown and must be remediated or explicitly allowlisted
with an expiry date.
"""
from __future__ import annotations

import argparse
import ast
import json
import re
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGET = ROOT / "services" / "layer3-knowledge" / "src"
DEFAULT_REPORT = ROOT / "docs" / "audit" / "l3-cypher-tenant-inventory.json"
DEFAULT_ALLOWLIST = (
    ROOT / "config" / "production-readiness" / "l3-cypher-tenant-inventory-allowlist.json"
)
SEEDED_PATHS = (
    "services/layer3-knowledge/src/api/routes/analytics.py",
    "services/layer3-knowledge/src/ingestion/sync_manager.py",
    "services/layer3-knowledge/src/ingestion/neo4j_loader.py",
    "services/layer3-knowledge/src/api/routes/signals.py",
    "services/layer3-knowledge/src/api/routes/knowledge.py",
)

CYPHER_KEYWORD_RE = re.compile(
    r"\b(MATCH|OPTIONAL\s+MATCH|MERGE|CREATE|DELETE|DETACH\s+DELETE|SET|REMOVE|UNWIND|CALL|RETURN)\b",
    re.IGNORECASE,
)
LABEL_RE = re.compile(r"(?<![A-Za-z0-9_]):`?([A-Za-z][A-Za-z0-9_]*)`?")
TENANT_PREDICATE_RE = re.compile(r"\btenant_?id\b", re.IGNORECASE)

READ_WORDS = ("MATCH", "OPTIONAL MATCH", "RETURN", "CALL")
WRITE_WORDS = ("CREATE", "MERGE", "SET", "REMOVE")
DELETE_WORDS = ("DELETE", "DETACH DELETE")
SCHEMA_WORDS = ("CONSTRAINT", "INDEX")

# Labels used by schema/bootstrap operations rather than tenant-owned customer
# data. Unknown labels are treated as tenant-owned so new graph paths fail closed.
SYSTEM_LABELS = {
    "Constraint",
    "Index",
    "SchemaMetadata",
    "Migration",
    "GraphMetadata",
}
TENANT_WRAPPER_MARKERS = {
    "Neo4jTenantSession.run",
    "TenantQueryExecutor.run",
    "execute_tenant_query",
    "execute_tenant_scoped",
    "execute_scoped_query",
    "execute_tenant_cypher",
    "run_validated_query",
}


@dataclass(frozen=True)
class Finding:
    file: str
    line: int
    function: str
    labels_touched: list[str]
    operation_type: str
    execution_wrapper: str
    tenant_predicate_status: str
    classification: str
    finding_key: str
    source_kind: str
    snippet: str


class CypherInventory(ast.NodeVisitor):
    def __init__(self, path: Path) -> None:
        self.path = path
        self.rel_file = path.relative_to(ROOT).as_posix()
        self.function_stack: list[str] = []
        self.scope_stack: list[dict[str, str]] = [{}]
        self.module_strings: dict[str, str] = {}
        self.findings: list[Finding] = []
        self.execution_lines: set[tuple[int, str]] = set()

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_function(node)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_function(node)

    def _visit_function(self, node: ast.FunctionDef | ast.AsyncFunctionDef) -> None:
        self.function_stack.append(node.name)
        self.scope_stack.append({})
        self.generic_visit(node)
        self.scope_stack.pop()
        self.function_stack.pop()

    def visit_Assign(self, node: ast.Assign) -> None:
        value = self._literal_string(node.value)
        if value and _looks_like_cypher(value):
            emitted_literal = False
            for target in node.targets:
                for name in self._target_names(target):
                    self.scope_stack[-1][name] = value
                    if not self.function_stack:
                        self.module_strings[name] = value
                    if self._is_cypher_variable_name(name) and not emitted_literal:
                        self.findings.append(
                            self._finding(node, value, "literal-only", "cypher-string")
                        )
                        emitted_literal = True
        self.generic_visit(node)

    def visit_AnnAssign(self, node: ast.AnnAssign) -> None:
        value = self._literal_string(node.value) if node.value is not None else None
        if value and _looks_like_cypher(value):
            emitted_literal = False
            for name in self._target_names(node.target):
                self.scope_stack[-1][name] = value
                if not self.function_stack:
                    self.module_strings[name] = value
                if self._is_cypher_variable_name(name) and not emitted_literal:
                    self.findings.append(
                        self._finding(node, value, "literal-only", "cypher-string")
                    )
                    emitted_literal = True
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        wrapper = self._call_name(node)
        if self._is_execution_call(wrapper):
            query_text = self._extract_query_arg(node)
            source_kind = "run-call"
            if query_text is None:
                query_text = self._nearby_string_context(node) or ""
                source_kind = "run-call-unresolved"
            self.findings.append(self._finding(node, query_text, wrapper, source_kind))
            self.execution_lines.add((getattr(node, "lineno", 1), wrapper))
        self.generic_visit(node)


    @staticmethod
    def _is_cypher_variable_name(name: str) -> bool:
        lowered = name.lower()
        return (
            "cypher" in lowered
            or "query" in lowered
            or "statement" in lowered
            or lowered.endswith("_q")
        )

    @staticmethod
    def _target_names(node: ast.AST) -> Iterable[str]:
        if isinstance(node, ast.Name):
            yield node.id
        elif isinstance(node, (ast.Tuple, ast.List)):
            for element in node.elts:
                yield from CypherInventory._target_names(element)

    def _function(self) -> str:
        return self.function_stack[-1] if self.function_stack else "<module>"

    def _finding(self, node: ast.AST, query_text: str, wrapper: str, source_kind: str) -> Finding:
        labels = sorted({f":{label}" for label in LABEL_RE.findall(query_text)})
        operation = _operation_type(query_text)
        tenant_status = _tenant_status(query_text, wrapper, labels)
        classification = _classification(query_text, wrapper, labels, operation, tenant_status)
        line = getattr(node, "lineno", 1)
        key = f"{self.rel_file}::{self._function()}::{line}::{wrapper}::{source_kind}"
        return Finding(
            file=self.rel_file,
            line=line,
            function=self._function(),
            labels_touched=labels,
            operation_type=operation,
            execution_wrapper=wrapper,
            tenant_predicate_status=tenant_status,
            classification=classification,
            finding_key=key,
            source_kind=source_kind,
            snippet=_snippet(query_text),
        )

    @staticmethod
    def _call_name(node: ast.Call) -> str:
        parts: list[str] = []
        current: ast.AST = node.func
        while isinstance(current, ast.Attribute):
            parts.append(current.attr)
            current = current.value
        if isinstance(current, ast.Name):
            parts.append(current.id)
        return ".".join(reversed(parts)) if parts else "<unknown-call>"

    @staticmethod
    def _is_execution_call(wrapper: str) -> bool:
        parts = wrapper.split(".")
        name = parts[-1]
        if name in {
            "execute_query",
            "run_validated_query",
            "execute_tenant_scoped",
            "execute_tenant_query",
            "execute_scoped_query",
            "execute_tenant_cypher",
            "_run_cypher",
        }:
            return True
        if name != "run":
            return False
        root = parts[0] if parts else ""
        return root in {"session", "tx", "transaction", "neo4j", "graph", "driver", "self"}

    def _extract_query_arg(self, node: ast.Call) -> str | None:
        candidates: list[ast.AST] = []
        if node.args:
            candidates.append(node.args[0])
        for keyword in node.keywords:
            if keyword.arg and keyword.arg.lower() in {"query", "cypher", "statement", "q"}:
                candidates.append(keyword.value)
        for candidate in candidates:
            value = self._literal_string(candidate)
            if value and _looks_like_cypher(value):
                return value
        return None

    def _nearby_string_context(self, node: ast.Call) -> str | None:
        # If session.run(query, params) uses a local variable that was assigned a
        # literal Cypher statement earlier in the function, resolve it.
        if not node.args:
            return None
        first_arg = node.args[0]
        if isinstance(first_arg, ast.Name):
            name = first_arg.id
            for scope in reversed(self.scope_stack):
                if name in scope:
                    return scope[name]
            return self.module_strings.get(name)
        return None

    def _literal_string(self, node: ast.AST | None) -> str | None:
        if node is None:
            return None
        if isinstance(node, ast.Constant) and isinstance(node.value, str):
            return node.value
        if isinstance(node, ast.JoinedStr):
            parts: list[str] = []
            for value in node.values:
                if isinstance(value, ast.Constant) and isinstance(value.value, str):
                    parts.append(value.value)
                elif isinstance(value, ast.FormattedValue):
                    # Preserve enough structure to keep labels around f-string
                    # holes, but mark dynamic pieces as unresolved.
                    parts.append("__DYNAMIC__")
            return "".join(parts)
        if isinstance(node, ast.BinOp) and isinstance(node.op, ast.Add):
            left = self._literal_string(node.left)
            right = self._literal_string(node.right)
            if left is not None and right is not None:
                return left + right
        if isinstance(node, ast.Name):
            for scope in reversed(self.scope_stack):
                if node.id in scope:
                    return scope[node.id]
            return self.module_strings.get(node.id)
        return None


def _looks_like_cypher(text: str) -> bool:
    return bool(CYPHER_KEYWORD_RE.search(text))


def _snippet(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()[:220]


def _operation_type(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text.upper())
    has_delete = any(word in normalized for word in DELETE_WORDS)
    has_write = any(re.search(rf"\b{re.escape(word)}\b", normalized) for word in WRITE_WORDS)
    has_schema = any(word in normalized for word in SCHEMA_WORDS)
    has_read = any(word in normalized for word in READ_WORDS)
    if has_schema:
        return "schema"
    if has_delete and has_write:
        return "read_write_delete" if has_read else "write_delete"
    if has_delete:
        return "delete"
    if has_write:
        return "read_write" if has_read else "write"
    if has_read:
        return "read"
    return "unknown"


def _tenant_status(text: str, wrapper: str, labels: list[str]) -> str:
    if _wrapper_is_tenant_scoped(wrapper):
        return "WrapperInjected"
    if not text:
        return "Unknown"
    if TENANT_PREDICATE_RE.search(text):
        return "Present"
    if labels and all(label[1:] in SYSTEM_LABELS for label in labels):
        return "NotRequiredSystemLabel"
    return "Missing"


def _wrapper_is_tenant_scoped(wrapper: str) -> bool:
    return wrapper in TENANT_WRAPPER_MARKERS or wrapper.rsplit(".", 1)[-1] in TENANT_WRAPPER_MARKERS


def _classification(
    text: str, wrapper: str, labels: list[str], operation: str, tenant_status: str
) -> str:
    if tenant_status in {"Present", "WrapperInjected", "NotRequiredSystemLabel"}:
        return "Safe"
    if not text or "__DYNAMIC__" in text or operation == "unknown":
        return "Unknown"
    tenant_owned = not labels or any(label[1:] not in SYSTEM_LABELS for label in labels)
    if tenant_owned and tenant_status == "Missing":
        return "Unsafe"
    return "Unknown"



def scan_text_fallback(path: Path) -> list[Finding]:
    rel = path.relative_to(ROOT).as_posix()
    findings: list[Finding] = []
    for line_no, line in enumerate(path.read_text(encoding="utf-8", errors="ignore").splitlines(), 1):
        if not _looks_like_cypher(line) or (not LABEL_RE.search(line) and ".run(" not in line):
            continue
        labels = sorted({f":{label}" for label in LABEL_RE.findall(line)})
        operation = _operation_type(line)
        tenant_status = _tenant_status(line, "text-fallback", labels)
        classification = _classification(line, "text-fallback", labels, operation, tenant_status)
        findings.append(
            Finding(
                file=rel,
                line=line_no,
                function="<text-fallback>",
                labels_touched=labels,
                operation_type=operation,
                execution_wrapper="text-fallback",
                tenant_predicate_status=tenant_status,
                classification=classification,
                finding_key=f"{rel}::<text-fallback>::{line_no}::text-fallback::cypher-string",
                source_kind="cypher-string",
                snippet=_snippet(line),
            )
        )
    return findings

def scan(target: Path) -> list[Finding]:
    findings: list[Finding] = []
    for path in sorted(target.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        except SyntaxError:
            # Some legacy compatibility files in this repository are intentionally
            # syntactically broken placeholders. They cannot contain executable
            # Python callsites, so fall back to a conservative text scan for
            # obvious Cypher assignments instead of blocking on parse errors.
            findings.extend(scan_text_fallback(path))
            continue
        visitor = CypherInventory(path)
        visitor.visit(tree)
        findings.extend(visitor.findings)
    # De-duplicate literal strings that are represented by a resolved run call in
    # the same function with identical normalized Cypher text.
    resolved = {
        (f.file, f.function, f.snippet)
        for f in findings
        if f.source_kind in {"run-call", "run-call-unresolved"} and f.snippet
    }
    deduped = [
        f
        for f in findings
        if not (f.source_kind == "cypher-string" and (f.file, f.function, f.snippet) in resolved)
    ]
    return sorted(deduped, key=lambda f: (f.file, f.line, f.execution_wrapper, f.source_kind))


def load_allowlist(path: Path) -> dict[str, dict[str, Any]]:
    if not path.exists():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("allowlist", []) if isinstance(data, dict) else []
    return {str(entry.get("finding_key")): entry for entry in entries if entry.get("finding_key")}


def is_allowed(finding: Finding, allowlist: dict[str, dict[str, Any]], today: date) -> bool:
    entry = allowlist.get(finding.finding_key)
    if not entry:
        return False
    expires_on = entry.get("expires_on")
    if not expires_on:
        return False
    try:
        expiry = date.fromisoformat(str(expires_on))
    except ValueError:
        return False
    return expiry >= today


def build_report(findings: list[Finding], allowlist: dict[str, dict[str, Any]]) -> dict[str, Any]:
    counts: dict[str, int] = {"Safe": 0, "Unsafe": 0, "Unknown": 0}
    for finding in findings:
        counts[finding.classification] = counts.get(finding.classification, 0) + 1
    return {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "target": DEFAULT_TARGET.relative_to(ROOT).as_posix(),
        "allowlist": DEFAULT_ALLOWLIST.relative_to(ROOT).as_posix(),
        "classification_counts": counts,
        "seeded_paths": {
            seeded_path: sum(1 for finding in findings if finding.file == seeded_path)
            for seeded_path in SEEDED_PATHS
        },
        "findings": [asdict(finding) for finding in findings],
        "allowlisted_findings": [
            finding.finding_key for finding in findings if finding.finding_key in allowlist
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", type=Path, default=DEFAULT_TARGET)
    parser.add_argument("--report", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--allowlist", type=Path, default=DEFAULT_ALLOWLIST)
    parser.add_argument(
        "--write-report",
        action="store_true",
        help="Write the machine-readable inventory report to --report.",
    )
    args = parser.parse_args()

    target = args.target if args.target.is_absolute() else ROOT / args.target
    report_path = args.report if args.report.is_absolute() else ROOT / args.report
    allowlist_path = args.allowlist if args.allowlist.is_absolute() else ROOT / args.allowlist

    findings = scan(target)
    allowlist = load_allowlist(allowlist_path)
    today = datetime.now(timezone.utc).date()
    blocking = [
        finding
        for finding in findings
        if finding.classification in {"Unsafe", "Unknown"}
        and not is_allowed(finding, allowlist, today)
    ]

    report = build_report(findings, allowlist)
    report["blocking_findings"] = [finding.finding_key for finding in blocking]

    if args.write_report:
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    else:
        print(json.dumps(report, indent=2, sort_keys=True))

    if blocking:
        print("Layer 3 Cypher tenant inventory check failed:")
        for finding in blocking:
            print(
                f" - {finding.finding_key}: {finding.classification} "
                f"tenant_predicate_status={finding.tenant_predicate_status}"
            )
        return 1

    print(
        "Layer 3 Cypher tenant inventory check passed "
        f"({len(findings)} findings, {report['classification_counts']})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
