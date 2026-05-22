#!/usr/bin/env python3
"""Detect deprecated namespace imports and enforce migration policy.

Features:
- Categorized reporting (production vs compatibility shims vs docs/comments/tests)
- Baseline-aware strict gating for net-new findings
- Optional ratchet gate to prevent baseline growth
- Optional shim-drift heuristic for wrapper logic
"""

from __future__ import annotations

import argparse
import ast
import json
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (Path("services"), Path("value_fabric"), Path("tests"), Path("scripts"), Path("docs"))
DEPRECATED_PREFIXES = ("value_fabric.layer1_ingestion", "value_fabric.layer3_knowledge")
BASELINE_PATH = Path("docs/reference/deprecated-namespace-import-baseline.json")
ALLOWLIST = {
    Path("tests/ci/test_deprecated_namespace_imports.py"),
}

PRODUCTION_ROOTS = (Path("services"), Path("value_fabric"))
COMPAT_SHIM_HINTS = (
    "compat",
    "shim",
    "legacy",
    "wrapper",
)


@dataclass(frozen=True)
class DeprecatedImport:
    path: str
    line: int
    statement: str
    deprecated_namespace: str
    category: str


@dataclass(frozen=True)
class ShimViolation:
    path: str
    line: int
    category: str
    message: str


def _iter_python_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        abs_root = repo_root / root
        if not abs_root.exists():
            continue
        for file_path in abs_root.rglob("*.py"):
            rel = file_path.relative_to(repo_root)
            if rel in ALLOWLIST:
                continue
            files.append(file_path)
    return sorted(files)


def _deprecated_target(name: str) -> str | None:
    for prefix in DEPRECATED_PREFIXES:
        if name == prefix or name.startswith(prefix + "."):
            return prefix
    return None


def _categorize_path(rel_path: str) -> str:
    p = Path(rel_path)
    if p.parts and p.parts[0] == "docs":
        return "docs_comments_tests"
    if p.parts and p.parts[0] == "tests":
        return "docs_comments_tests"
    if p.parts and p.parts[0] == "scripts":
        return "docs_comments_tests"
    lowered = rel_path.lower()
    if any(h in lowered for h in COMPAT_SHIM_HINTS):
        return "compatibility_shims"
    if p.parts and Path(p.parts[0]) in PRODUCTION_ROOTS:
        return "production"
    return "docs_comments_tests"


def _scan_file(file_path: Path, repo_root: Path) -> list[DeprecatedImport]:
    source = file_path.read_text(encoding="utf-8", errors="ignore")
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    lines = source.splitlines()
    rel = str(file_path.relative_to(repo_root))
    findings: list[DeprecatedImport] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                prefix = _deprecated_target(alias.name)
                if prefix:
                    findings.append(DeprecatedImport(rel, node.lineno, lines[node.lineno - 1].strip(), prefix, _categorize_path(rel)))
        elif isinstance(node, ast.ImportFrom) and node.module:
            prefix = _deprecated_target(node.module)
            if prefix:
                findings.append(DeprecatedImport(rel, node.lineno, lines[node.lineno - 1].strip(), prefix, _categorize_path(rel)))

    return findings


def scan(repo_root: Path) -> list[DeprecatedImport]:
    findings: list[DeprecatedImport] = []
    for file_path in _iter_python_files(repo_root):
        findings.extend(_scan_file(file_path, repo_root))
    return sorted(findings, key=lambda x: (x.path, x.line, x.statement))


def _load_baseline(repo_root: Path, baseline_path: Path) -> set[tuple[str, int, str, str]]:
    abs_path = repo_root / baseline_path
    if not abs_path.exists():
        return set()
    payload = json.loads(abs_path.read_text(encoding="utf-8"))
    return {
        (
            str(item["path"]),
            int(item["line"]),
            str(item["statement"]),
            str(item["deprecated_namespace"]),
        )
        for item in payload
    }


def _subtract_baseline(findings: list[DeprecatedImport], baseline: set[tuple[str, int, str, str]]) -> list[DeprecatedImport]:
    return [f for f in findings if (f.path, f.line, f.statement, f.deprecated_namespace) not in baseline]


def _check_shim_violations(repo_root: Path) -> list[ShimViolation]:
    findings: list[ShimViolation] = []
    wrapper_root = repo_root / "services" / "layer3-knowledge" / "src"
    canonical_root = repo_root / "value_fabric" / "layer3"
    if not wrapper_root.exists() or not canonical_root.exists():
        return findings
    canonical_files = {p.relative_to(canonical_root): p for p in canonical_root.rglob("*.py")}
    for wrapper_file in wrapper_root.rglob("*.py"):
        rel = wrapper_file.relative_to(wrapper_root)
        if rel not in canonical_files:
            continue
        canonical_file = canonical_files[rel]
        wrapper_src = wrapper_file.read_text(encoding="utf-8")
        canonical_src = canonical_file.read_text(encoding="utf-8")
        wrapper_lines = [l for l in wrapper_src.splitlines() if l.strip() and not l.strip().startswith("#")]
        canonical_lines = [l for l in canonical_src.splitlines() if l.strip() and not l.strip().startswith("#")]
        if len(wrapper_lines) > 5 and len(wrapper_lines) > len(canonical_lines) * 0.3:
            findings.append(ShimViolation(str(wrapper_file.relative_to(repo_root)), 1, "shim_contains_logic", f"wrapper file {rel} appears to contain duplicated domain logic (>30% of canonical size)"))
    return findings


def _summary_by_category(findings: list[DeprecatedImport]) -> dict[str, int]:
    out = {"production": 0, "compatibility_shims": 0, "docs_comments_tests": 0}
    for f in findings:
        out[f.category] = out.get(f.category, 0) + 1
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", default=str(REPO_ROOT))
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--use-baseline", action="store_true")
    parser.add_argument("--baseline-path", default=str(BASELINE_PATH))
    parser.add_argument("--check-shims", action="store_true")
    parser.add_argument("--enforce-ratchet", action="store_true", help="Fail strict mode if current findings exceed baseline count")
    args = parser.parse_args(argv)

    repo_root = Path(args.repo_root).resolve()
    all_findings = scan(repo_root)
    baseline = _load_baseline(repo_root, Path(args.baseline_path)) if args.use_baseline or args.enforce_ratchet else set()
    findings = _subtract_baseline(all_findings, baseline) if args.use_baseline else all_findings
    shim_findings = _check_shim_violations(repo_root) if args.check_shims else []

    ratchet_violation = False
    if args.enforce_ratchet:
        ratchet_violation = len(all_findings) > len(baseline)

    summary = _summary_by_category(findings)

    if args.json:
        print(json.dumps({
            "summary": summary,
            "deprecated_imports": [asdict(i) for i in findings],
            "all_findings": [asdict(i) for i in all_findings],
            "shim_violations": [asdict(i) for i in shim_findings],
            "ratchet": {"baseline_count": len(baseline), "current_count": len(all_findings), "violated": ratchet_violation},
        }, indent=2))
    else:
        print("Deprecated namespace import summary:")
        print(f"  production: {summary.get('production', 0)}")
        print(f"  compatibility_shims: {summary.get('compatibility_shims', 0)}")
        print(f"  docs_comments_tests: {summary.get('docs_comments_tests', 0)}")
        print(f"Net-new findings after baseline subtraction: {len(findings)}")
        for f in findings:
            print(f"{f.path}:{f.line} :: {f.statement} [{f.deprecated_namespace}] ({f.category})")
        if shim_findings:
            print(f"Shim logic violations: {len(shim_findings)}")
            for f in shim_findings:
                print(f"{f.path}:{f.line} :: [{f.category}] {f.message}")
        if args.enforce_ratchet:
            status = "VIOLATION" if ratchet_violation else "OK"
            print(f"Ratchet baseline status: {status} (current={len(all_findings)}, baseline={len(baseline)})")

    has_issues = bool(findings) or bool(shim_findings) or ratchet_violation
    return 1 if args.strict and has_issues else 0


if __name__ == "__main__":
    raise SystemExit(main())
