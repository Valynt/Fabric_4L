#!/usr/bin/env python3
"""Deprecation drift gate: fail if known anti-patterns reappear.

Checks for:
- datetime.utcnow() in source code (deprecated in Python 3.12)
- Pydantic v1-only APIs: parse_raw, parse_obj, parse_file, __root__, etc.
- blanket DeprecationWarning / PendingDeprecationWarning suppression in pytest configs
- invalid FastAPI response field types (Request | None)
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SCAN_ROOTS = (
    REPO_ROOT / "value_fabric",
    REPO_ROOT / "services",
    REPO_ROOT / "tests",
    REPO_ROOT / "scripts",
)

SKIP_DIRS = {"__pycache__", ".venv", ".uv-cache-local", ".venv-verify", ".hypothesis", ".git", "node_modules", ".tmp-local", ".tox"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    category: str
    message: str


# Pattern definitions
UTCNOW_RE = re.compile(r"datetime\.utcnow\(")
PYDANTIC_V1_RE = re.compile(r"\.parse_raw\(|\.parse_obj\(|\.parse_file\(|__root__\s*=")
REQUEST_TYPE_RESPONSE_RE = re.compile(r"Request\s*\|\s*None")
BROAD_DEPRECATION_RE = re.compile(
    r"ignore::(?:DeprecationWarning|PendingDeprecationWarning)\s*$",
    re.MULTILINE,
)

ALLOWLIST: dict[str, set[tuple[str, int]]] = {
    # This script's own literal regex definitions
    "utcnow": {("scripts/ci/check_deprecation_drift.py", 0)},
    "pydantic_v1": {("scripts/ci/check_deprecation_drift.py", 0)},
    "request_type_response": {("scripts/ci/check_deprecation_drift.py", 0)},
}


def _iter_source_files():
    import os
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if fname.endswith(".py") or fname.endswith(".ini"):
                    yield Path(dirpath) / fname


def _is_allowlisted(finding: Finding) -> bool:
    allowed = ALLOWLIST.get(finding.category, set())
    normalized_path = finding.path.replace("\\", "/")
    for path_sub, line in allowed:
        if path_sub in normalized_path and (line == 0 or line == finding.line):
            return True
    return False


def scan() -> list[Finding]:
    findings: list[Finding] = []

    for path in _iter_source_files():
        rel = str(path.relative_to(REPO_ROOT))
        source = path.read_text(encoding="utf-8", errors="ignore")
        lines = source.splitlines()

        if path.suffix == ".py":
            # Helper: skip matches inside regex literal definitions
            def _in_regex_literal(pos: int) -> bool:
                line_start = source.rfind("\n", 0, pos)
                line_text = source[line_start + 1 : pos]
                return line_text.strip().startswith("r\"") or "re.compile(" in line_text

            # 1. datetime.utcnow()
            for m in UTCNOW_RE.finditer(source):
                line_num = source[: m.start()].count("\n") + 1
                if _in_regex_literal(m.start()):
                    continue
                findings.append(Finding(rel, line_num, "utcnow", "datetime.utcnow() is deprecated in Python 3.12; use datetime.now(UTC)"))

            # 2. Pydantic v1 APIs
            for m in PYDANTIC_V1_RE.finditer(source):
                line_num = source[: m.start()].count("\n") + 1
                if _in_regex_literal(m.start()):
                    continue
                findings.append(Finding(rel, line_num, "pydantic_v1", "Pydantic v1 API detected; migrate to v2 equivalent"))

            # 3. Request | None as response field type
            for m in REQUEST_TYPE_RESPONSE_RE.finditer(source):
                line_num = source[: m.start()].count("\n") + 1
                if _in_regex_literal(m.start()):
                    continue
                findings.append(Finding(rel, line_num, "request_type_response", "Request | None is not a valid Pydantic response field type"))

        elif path.suffix == ".ini":
            # 4. broad deprecation suppression
            for m in BROAD_DEPRECATION_RE.finditer(source):
                line_num = source[: m.start()].count("\n") + 1
                line_text = lines[line_num - 1] if line_num <= len(lines) else ""
                if ":" not in line_text.split("#")[0]:
                    findings.append(Finding(rel, line_num, "broad_deprecation_suppression", "blanket deprecation warning suppression in pytest config"))

    seen = set()
    deduped = []
    for f in findings:
        key = (f.path, f.line, f.category, f.message)
        if key not in seen and not _is_allowlisted(f):
            seen.add(key)
            deduped.append(f)

    return deduped


BASELINE_PATH = REPO_ROOT / "docs" / "reference" / "deprecation-drift-baseline.json"


def _load_baseline() -> set[tuple[str, int, str, str]]:
    if not BASELINE_PATH.exists():
        return set()
    data = json.loads(BASELINE_PATH.read_text(encoding="utf-8"))
    return {
        (str(item["path"]).replace("\\", "/"), int(item["line"]), str(item["category"]), str(item["message"]))
        for item in data.get("findings", [])
    }


def _subtract_baseline(
    findings: list[Finding], baseline: set[tuple[str, int, str, str]]
) -> list[Finding]:
    return [
        f for f in findings
        if (f.path.replace("\\", "/"), f.line, f.category, f.message) not in baseline
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict", action="store_true")
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--use-baseline", action="store_true")
    args = parser.parse_args(argv)

    findings = scan()
    if args.use_baseline:
        baseline = _load_baseline()
        findings = _subtract_baseline(findings, baseline)

    if args.json:
        print(json.dumps([asdict(f) for f in findings], indent=2))
    else:
        print(f"Deprecation drift findings: {len(findings)}")
        for f in findings:
            print(f"  [{f.category}] {f.path}:{f.line} :: {f.message}")

    return 1 if args.strict and findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
