#!/usr/bin/env python3
"""Guard against hard-coded temporal test skips.

The register in config/ci/test_skip_register.yaml is the source of truth for
intentional, time-boxed skips. This script scans test files for skip reasons
that contain temporal language or dates without a linked ticket ID, and fails
if any are found.

Allowed patterns:
- Skip is registered in config/ci/test_skip_register.yaml.
- Skip reason contains an issue tracker reference (e.g., VF-SKIP-123, PROJ-42).

Flagged patterns:
- Reasons containing calendar dates (2026-06-30, 06/30, etc.).
- Reasons containing temporal words (TODO, FIXME, temporary, until, expires,
  soon, later, Q3, H1, etc.) without a ticket reference.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REGISTER_PATH = REPO_ROOT / "config/ci/test_skip_register.yaml"

# File extensions to scan.
SCAN_EXTENSIONS = {".py", ".ts", ".tsx", ".js", ".jsx", ".md"}

# Directories that contain production/test code we care about.
DEFAULT_SCAN_ROOTS = [
    "tests",
    "apps/web/e2e",
    "services",
]

EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    "__pycache__",
    "coverage",
    "dist",
    "node_modules",
    "playwright-report",
    "test-results",
    "venv",
    ".venv",
}

# Skip markers / decorators we inspect.
MARKERS: list[tuple[str, re.Pattern[str]]] = [
    ("pytest.skip", re.compile(r"\bpytest\.skip\s*\(")),
    ("pytest.mark.skip", re.compile(r"\bpytest\.mark\.skip(?:if)?\s*\(")),
    ("pytest.mark.xfail", re.compile(r"\bpytest\.mark\.xfail\s*\(")),
    ("test.skip", re.compile(r"\btest\.skip\s*\(")),
    ("test.fixme", re.compile(r"\btest\.fixme\s*\(")),
    ("describe.skip", re.compile(r"\bdescribe\.skip\s*\(")),
    ("it.skip", re.compile(r"\bit\.skip\s*\(")),
]

# Calendar date patterns.
DATE_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b"),  # 2026-06-30, 2026/06/30
    re.compile(r"\b\d{1,2}[-/]\d{1,2}[-/]20\d{2}\b"),  # 06-30-2026
    re.compile(r"\b\d{1,2}/\d{1,2}/\d{2,4}\b"),         # 6/30/26
]

# Temporal words / phrases that indicate a hand-waved expiry.
TEMPORAL_KEYWORDS: list[re.Pattern[str]] = [
    re.compile(r"\bTODO\b", re.IGNORECASE),
    re.compile(r"\bFIXME\b", re.IGNORECASE),
    re.compile(r"\btemporary\b", re.IGNORECASE),
    re.compile(r"\btemporarily\b", re.IGNORECASE),
    re.compile(r"\buntil\b", re.IGNORECASE),
    re.compile(r"\bexpires\b", re.IGNORECASE),
    re.compile(r"\bexpiry\b", re.IGNORECASE),
    re.compile(r"\bexpiring\b", re.IGNORECASE),
    re.compile(r"\bsoon\b", re.IGNORECASE),
    re.compile(r"\blater\b", re.IGNORECASE),
    re.compile(r"\bnext\s+(?:sprint|quarter|month|week|release)\b", re.IGNORECASE),
    re.compile(r"\bQ[1-4]\b"),
    re.compile(r"\bH[1-2]\b"),
    re.compile(r"\bfor\s+now\b", re.IGNORECASE),
    re.compile(r"\bshort[\s-]term\b", re.IGNORECASE),
]

# Ticket ID patterns that legitimize a temporal skip.
TICKET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\bVF-SKIP-\d+\b"),
    re.compile(r"\b[A-Z][A-Z0-9]+-\d+\b"),  # e.g., JIRA-123, GH-456
]


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    marker: str
    reason: str
    matched_pattern: str


def _load_register(path: Path) -> dict[tuple[str, str, str], dict[str, Any]]:
    """Load registered skips keyed by (path_pattern, marker, reason_pattern)."""
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse the skip register")
    if not path.exists():
        return {}
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    entries = raw.get("entries", []) if isinstance(raw, dict) else []
    register: dict[tuple[str, str, str], dict[str, Any]] = {}
    for entry in entries:
        key = (
            entry.get("path_pattern", ""),
            entry.get("marker", ""),
            entry.get("reason_pattern", ""),
        )
        register[key] = entry
    return register


def _extract_reason(line: str, marker: str) -> str | None:
    """Extract the string reason from a skip marker call, if present."""
    pattern = next((p for name, p in MARKERS if name == marker), None)
    if pattern is None:
        return None

    marker_match = pattern.search(line)
    if marker_match is None:
        return None

    # Find the opening parenthesis of the call. The marker regex may include
    # trailing whitespace and the '(' (e.g., pytest.skip\s*\(); if it does not,
    # search forward from the end of the matched marker text.
    paren_start = marker_match.end() - 1 if line[marker_match.end() - 1] == "(" else line.find("(", marker_match.end())
    if paren_start == -1:
        return None

    # Simple extraction: find the first quoted string in the call arguments.
    for quote in ('"', "'"):
        pos = line.find(quote, paren_start)
        if pos == -1:
            continue
        end = line.find(quote, pos + 1)
        if end == -1:
            continue
        return line[pos + 1 : end]

    # If no quoted string, return the whole argument text (e.g., for f-strings or variables).
    # We truncate at the matching closing paren for simplicity.
    depth = 0
    for i, ch in enumerate(line[paren_start:], paren_start):
        if ch == "(":
            depth += 1
        elif ch == ")":
            depth -= 1
            if depth == 0:
                return line[paren_start + 1 : i].strip()
    return line[paren_start + 1 :].strip()


def _has_temporal_language(reason: str) -> tuple[bool, str]:
    """Return (True, pattern) if reason contains unapproved temporal language."""
    for pattern in DATE_PATTERNS:
        if pattern.search(reason):
            return True, f"date:{pattern.pattern}"
    for pattern in TEMPORAL_KEYWORDS:
        if pattern.search(reason):
            return True, f"keyword:{pattern.pattern}"
    return False, ""


def _has_ticket_reference(reason: str) -> bool:
    return any(pattern.search(reason) for pattern in TICKET_PATTERNS)


def _is_registered(finding: Finding, register: dict[tuple[str, str, str], dict[str, Any]]) -> bool:
    """Check whether a finding matches a registered skip entry."""
    import fnmatch

    for (path_pattern, marker, reason_pattern), entry in register.items():
        if marker != finding.marker:
            continue
        if not fnmatch.fnmatch(finding.path, path_pattern):
            continue
        if reason_pattern and not re.search(reason_pattern, finding.reason, flags=re.IGNORECASE):
            continue
        # Registered entries must have a ticket_id in remediation to be considered tracked.
        remediation = entry.get("remediation", {}) or {}
        if remediation.get("ticket_id"):
            return True
    return False


def _scan_file(path: Path, root: Path) -> list[Finding]:
    findings: list[Finding] = []
    rel = path.relative_to(root).as_posix()
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except UnicodeDecodeError:
        return findings

    for lineno, line in enumerate(lines, start=1):
        for marker, pattern in MARKERS:
            if not pattern.search(line):
                continue
            reason = _extract_reason(line, marker)
            if reason is None:
                continue
            temporal, matched = _has_temporal_language(reason)
            if not temporal:
                continue
            findings.append(Finding(rel, lineno, marker, reason, matched))
    return findings


def _iter_scan_files(root: Path, scan_roots: list[str], excludes: list[str]) -> list[Path]:
    import fnmatch

    files: list[Path] = []
    for scan_root in scan_roots:
        base = root / scan_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            if path.suffix not in SCAN_EXTENSIONS:
                continue
            if any(part in EXCLUDED_PARTS for part in path.parts):
                continue
            rel = path.relative_to(root).as_posix()
            if any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(path.name, pat) for pat in excludes):
                continue
            files.append(path)
    return files


def _load_baseline(path: Path) -> list[dict[str, Any]]:
    """Load known existing temporal skip violations."""
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, list) else data.get("findings", [])


def _finding_in_baseline(finding: Finding, baseline: list[dict[str, Any]]) -> bool:
    for entry in baseline:
        if (
            entry.get("path") == finding.path
            and entry.get("line") == finding.line
            and entry.get("reason") == finding.reason
        ):
            return True
    return False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Guard against hard-coded temporal test skips")
    parser.add_argument("--register", type=Path, default=DEFAULT_REGISTER_PATH, help="Path to test skip register")
    parser.add_argument("--root", type=Path, default=REPO_ROOT, help="Repository root")
    parser.add_argument("--scan-root", action="append", dest="scan_roots", help="Additional scan roots")
    parser.add_argument("--exclude", action="append", dest="excludes", help="Glob patterns to exclude from scan")
    parser.add_argument("--baseline", type=Path, help="JSON file of known existing temporal skips")
    parser.add_argument("--write-baseline", type=Path, help="Write current findings to baseline and exit 0")
    parser.add_argument("--json-out", type=Path, help="Write findings to JSON")
    parser.add_argument("--md-out", type=Path, help="Write findings to Markdown")
    parser.add_argument("--warn-only", action="store_true", help="Exit 0 even if findings exist")
    args = parser.parse_args(argv)

    scan_roots = list(DEFAULT_SCAN_ROOTS)
    if args.scan_roots:
        scan_roots.extend(args.scan_roots)
    scan_roots = list(dict.fromkeys(scan_roots))  # preserve order, deduplicate

    excludes = args.excludes or []
    register = _load_register(args.register)
    baseline = _load_baseline(args.baseline) if args.baseline else []
    files = _iter_scan_files(args.root, scan_roots, excludes)

    raw_findings: list[Finding] = []
    for path in files:
        raw_findings.extend(_scan_file(path, args.root))

    # Filter out registered skips and skips that already reference a ticket ID.
    unregistered = [
        f for f in raw_findings
        if not (_is_registered(f, register) or _has_ticket_reference(f.reason))
    ]

    if args.write_baseline:
        args.write_baseline.parent.mkdir(parents=True, exist_ok=True)
        args.write_baseline.write_text(
            json.dumps(
                [
                    {
                        "path": f.path,
                        "line": f.line,
                        "marker": f.marker,
                        "reason": f.reason,
                        "matched_pattern": f.matched_pattern,
                    }
                    for f in unregistered
                ],
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"Wrote {len(unregistered)} baseline entries to {args.write_baseline}")
        return 0

    # Allow a ratchet: known existing violations are captured in a baseline;
    # only net-new violations fail the gate.
    findings = [f for f in unregistered if not _finding_in_baseline(f, baseline)]

    report = {
        "scanned_files": len(files),
        "register_path": str(args.register.relative_to(args.root).as_posix()),
        "raw_temporal_findings": len(raw_findings),
        "unregistered_temporal_findings": len(unregistered),
        "net_new_findings": len(findings),
        "findings": [
            {
                "path": f.path,
                "line": f.line,
                "marker": f.marker,
                "reason": f.reason,
                "matched_pattern": f.matched_pattern,
            }
            for f in findings
        ],
    }

    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2), encoding="utf-8")

    if args.md_out:
        args.md_out.parent.mkdir(parents=True, exist_ok=True)
        lines = [
            "# Temporal Skip Guard Report",
            "",
            f"- Scanned files: {report['scanned_files']}",
            f"- Register: `{report['register_path']}`",
            f"- Raw temporal findings: {report['raw_temporal_findings']}",
            f"- Unregistered temporal findings: {report['unregistered_temporal_findings']}",
            f"- Net-new findings: {report['net_new_findings']}",
            "",
        ]
        if findings:
            lines.extend(["## Net-new temporal skips", ""])
            lines.append("| File | Line | Marker | Reason | Matched |")
            lines.append("|------|------|--------|--------|--------|")
            for f in findings:
                reason = f.reason.replace("|", "\\|")
                lines.append(f"| {f.path} | {f.line} | {f.marker} | {reason} | {f.matched_pattern} |")
        else:
            lines.append("No net-new temporal skips found.")
        args.md_out.write_text("\n".join(lines) + "\n", encoding="utf-8")

    if findings:
        print(f"ERROR: {len(findings)} net-new temporal skip(s) found.", file=sys.stderr)
        for f in findings:
            print(f"  {f.path}:{f.line} [{f.marker}] {f.reason!r} ({f.matched_pattern})", file=sys.stderr)
        print(
            "\nTemporal skips must be registered in config/ci/test_skip_register.yaml "
            "with a remediation ticket_id, or the skip reason must reference an issue tracker ID. "
            "If these are pre-existing violations, add them to the baseline with --write-baseline.",
            file=sys.stderr,
        )
        return 0 if args.warn_only else 1

    print(f"OK: {report['scanned_files']} files scanned; no net-new temporal skips found.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
