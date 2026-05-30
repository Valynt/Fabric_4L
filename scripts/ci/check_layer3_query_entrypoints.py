#!/usr/bin/env python3
from __future__ import annotations

import argparse
import ast
import json
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_TARGETS = (
    Path("services/layer3-knowledge/src/api"),
    Path("services/layer3-knowledge/src/ingestion"),
    Path("services/layer3-knowledge/src/analytics"),
    Path("services/layer3-knowledge/src/agents"),
)
DEFAULT_ALLOWLIST = Path("config/production-readiness/l3-direct-session-run-allowlist.json")
ALLOWED_SCOPES = {"system", "schema", "migration", "bootstrap", "backup", "health"}
APPROVED_HELPERS = {
    "run_scoped_query",
    "run_validated_query",
    "run_tenant_query",
    "run_system_query",
    "execute_tenant_scoped",
    "execute_tenant_query",
    "execute_scoped_query",
}


@dataclass(frozen=True)
class Finding:
    path: Path
    line: int
    function: str
    classification: str
    reason: str

    @property
    def rel(self) -> str:
        return str(self.path.relative_to(ROOT))


class Visitor(ast.NodeVisitor):
    def __init__(self, path: Path):
        self.path = path
        self.findings: list[Finding] = []
        self.stack: list[str] = []

    def _fn(self) -> str:
        return self.stack[-1] if self.stack else "<module>"

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:  # noqa: N802
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:  # noqa: N802
        self.stack.append(node.name)
        self.generic_visit(node)
        self.stack.pop()

    def visit_Call(self, node: ast.Call) -> None:  # noqa: N802
        func = node.func
        if isinstance(func, ast.Attribute) and func.attr == "run":
            if isinstance(func.value, ast.Name) and func.value.id == "session":
                self.findings.append(
                    Finding(
                        self.path,
                        getattr(node, "lineno", 1),
                        self._fn(),
                        "Unsafe",
                        "direct session.run() detected; use run_validated_query, Neo4jTenantSessionSecured.run, or AuditedGraphMutation",
                    )
                )
        elif isinstance(func, ast.Name) and func.id in APPROVED_HELPERS:
            self.findings.append(
                Finding(
                    self.path,
                    getattr(node, "lineno", 1),
                    self._fn(),
                    "Safe",
                    f"approved execution helper used: {func.id}",
                )
            )
        self.generic_visit(node)


def iter_files(targets: list[Path]) -> list[Path]:
    files: list[Path] = []
    for target in targets:
        target = target.resolve()
        if target.is_file() and target.suffix == ".py":
            files.append(target)
        elif target.is_dir():
            files.extend(
                p for p in target.rglob("*.py") if "__pycache__" not in p.parts and "migrations" not in p.parts
            )
    return sorted(set(files))


def _load_allowlist(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    entries = data.get("entries", [])
    if not isinstance(entries, list):
        raise ValueError("allowlist entries must be a list")
    return entries


def _entry_matches(entry: dict[str, Any], finding: Finding) -> bool:
    return (
        entry.get("path") == finding.rel
        and entry.get("function") == finding.function
        and int(entry.get("line", -1)) == finding.line
    )


def _validate_allowlist_entry(entry: dict[str, Any], today: date) -> str | None:
    required = ("path", "function", "line", "owner", "expiry", "scope", "justification")
    missing = [field for field in required if not entry.get(field)]
    if missing:
        return f"allowlist entry missing required field(s): {', '.join(missing)}"
    if entry["scope"] not in ALLOWED_SCOPES:
        return f"allowlist entry has unsupported scope {entry['scope']!r}; allowed: {sorted(ALLOWED_SCOPES)}"
    try:
        expiry = date.fromisoformat(str(entry["expiry"]))
    except ValueError:
        return f"allowlist entry expiry must be ISO date: {entry['expiry']!r}"
    if expiry < today:
        return f"allowlist entry expired on {expiry.isoformat()}"
    if len(str(entry["justification"]).strip()) < 20:
        return "allowlist entry justification must be specific"
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Block direct Neo4j session.run calls in L3 runtime code.")
    parser.add_argument("targets", nargs="*", help="files or directories to scan; defaults to L3 api/ingestion/analytics/agents")
    parser.add_argument("--report-json", default="artifacts/layer3-query-entrypoint-matrix.json")
    parser.add_argument("--allowlist", default=str(DEFAULT_ALLOWLIST))
    args = parser.parse_args()

    targets = [Path(t) for t in args.targets] if args.targets else [ROOT / p for p in DEFAULT_TARGETS]
    allowlist_path = (ROOT / args.allowlist).resolve()
    allowlist = _load_allowlist(allowlist_path)
    today = date.today()
    allowlist_errors = [err for entry in allowlist if (err := _validate_allowlist_entry(entry, today))]

    all_findings: list[Finding] = []
    parse_errors: list[dict[str, str | int]] = []
    for path in iter_files(targets):
        source = path.read_text(encoding="utf-8")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            parse_errors.append({"path": str(path.relative_to(ROOT)), "line": int(exc.lineno or 1), "message": str(exc.msg)})
            continue
        visitor = Visitor(path)
        visitor.visit(tree)
        all_findings.extend(visitor.findings)

    unsafe: list[Finding] = []
    allowed: list[Finding] = []
    for finding in all_findings:
        if finding.classification != "Unsafe":
            continue
        match = next((entry for entry in allowlist if _entry_matches(entry, finding)), None)
        if match:
            allowed.append(Finding(finding.path, finding.line, finding.function, "Allowed", str(match["justification"])))
        else:
            unsafe.append(finding)

    report = {
        "targets": [str((Path(t).resolve()).relative_to(ROOT)) for t in targets],
        "allowlist": str(allowlist_path.relative_to(ROOT)),
        "summary": {
            "Safe": sum(1 for f in all_findings if f.classification == "Safe"),
            "Allowed": len(allowed),
            "Unsafe": len(unsafe),
            "parse_errors": len(parse_errors),
            "allowlist_errors": len(allowlist_errors),
        },
        "allowlist_errors": allowlist_errors,
        "parse_errors": parse_errors,
        "findings": [
            {"path": f.rel, "line": f.line, "function": f.function, "classification": f.classification, "reason": f.reason}
            for f in [*all_findings, *allowed]
        ],
    }

    out = (ROOT / args.report_json).resolve()
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    print(f"Layer 3 query entrypoint matrix written: {out.relative_to(ROOT)}")
    print(
        f"Safe={report['summary']['Safe']} Allowed={len(allowed)} Unsafe={len(unsafe)} "
        f"ParseErrors={len(parse_errors)} AllowlistErrors={len(allowlist_errors)}"
    )
    for finding in unsafe:
        print(f"ERROR: {finding.rel}:{finding.line}:{finding.function}: {finding.reason}")
    for err in allowlist_errors:
        print(f"ERROR: {err}")
    if unsafe or parse_errors or allowlist_errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
