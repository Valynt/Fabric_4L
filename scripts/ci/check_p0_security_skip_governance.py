#!/usr/bin/env python3
"""P0/security skip-governance ratchet.

Narrowly scoped CI guard over P0/security test paths. It fails CI when:

* a new skipped/xfailed P0 security test appears without allowlist metadata,
* an allowlisted skip passes its expiry date,
* a P0/security file contains an unconditional ``pytest.skip``,
  ``@pytest.mark.skip``, or ``@pytest.mark.xfail`` without an approved entry
  in ``config/ci/p0_security_skip_allowlist.yaml``,
* a P0/security skip is matched by more than one allowlist entry (ambiguous
  ownership, per the allowlist's "exactly one match per skip" contract).

Unlike ``check_test_skip_governance.py`` (which audits *all* test debt across
the repo), this check concerns only P0/security paths so a skipped P0 test
cannot silently disappear into an otherwise green run.

Exit codes:
    0 - no violations
    1 - one or more allowlist / governance violations
"""
from __future__ import annotations

import argparse
import fnmatch
import json
import re
import sys
from dataclasses import asdict, dataclass
from datetime import UTC, date, datetime
from pathlib import Path

import yaml

P0_SECURITY_DIRS = ("tests/security/",)
# Files governed by this ratchet for this remediation. Scope is deliberately
# narrow: only the remediation targets are enforced so adding the guard cannot
# fail CI on unrelated, out-of-scope pre-existing skips. Broaden by adding
# paths here once the coarser out-of-scope suites are remediated.
GOVERNED_PATHS = (
    "tests/security/test_cross_layer_tenant_isolation.py",
    "tests/security/test_webhook_security_p0.py",
)
SCAN_ROOTS = ["tests", "services", "apps/web/e2e"]
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}
EXCLUDED_PARTS = {
    ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tmp",
    ".venv", "venv", "__pycache__", "coverage", "dist", "node_modules",
    "playwright-report", "test-results",
}
SKIP_MARKERS: list[tuple[str, re.Pattern[str]]] = [
    ("pytest.skip", re.compile(r"\bpytest\.skip\s*\(")),
    ("pytest.mark.skip", re.compile(r"\bpytest\.mark\.skip(?:if)?\s*\(")),
    ("pytest.mark.xfail", re.compile(r"\bpytest\.mark\.xfail\s*\(")),
]


@dataclass(frozen=True)
class SkipFinding:
    path: str
    line: int
    marker: str
    text: str


@dataclass(frozen=True)
class AllowEntry:
    id: str
    path_pattern: str
    reason_pattern: str
    owner: str
    reason: str
    expiry: date
    issue: str
    classification: str

    def matches(self, finding: SkipFinding) -> bool:
        return (
            fnmatch.fnmatch(finding.path, self.path_pattern)
            and bool(re.search(self.reason_pattern, finding.text, re.IGNORECASE))
        )


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _is_p0_security_path(relative: Path, governed_paths: tuple[str, ...]) -> bool:
    posix = relative.as_posix()
    return posix in governed_paths


def _iter_files(root: Path, scan_roots: tuple[str, ...], governed_paths: tuple[str, ...]) -> list[Path]:
    files: set[Path] = set()
    for scan_root in scan_roots:
        base = root / scan_root
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else base.rglob("*")
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            relative = path.relative_to(root)
            if set(relative.parts) & EXCLUDED_PARTS or not _is_p0_security_path(relative, governed_paths):
                continue
            files.add(path)
    return sorted(files)


def _find_skips(root: Path, scan_roots: tuple[str, ...], governed_paths: tuple[str, ...]) -> list[SkipFinding]:
    findings: list[SkipFinding] = []
    for path in _iter_files(root, scan_roots, governed_paths):
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "pytest.skip.Exception" in line:
                continue
            for marker, pattern in SKIP_MARKERS:
                match = pattern.search(line)
                prefix = line[: match.start()] if match else ""
                inside_string = prefix.count('"') % 2 == 1 or prefix.count("'") % 2 == 1
                if match and not inside_string:
                    findings.append(
                        SkipFinding(path.relative_to(root).as_posix(), number, marker, line.strip())
                    )
                    break
    return findings


def _load_allowlist(path: Path, today: date) -> tuple[list[AllowEntry], list[str]]:
    errors: list[str] = []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, yaml.YAMLError) as exc:
        return [], [f"cannot parse allowlist: {exc}"]
    if not isinstance(raw, dict) or not isinstance(raw.get("entries", []), list):
        return [], ["allowlist must contain an entries list"]
    required = {"id", "path_pattern", "reason_pattern", "owner", "reason", "expiry", "issue", "classification"}
    entries: list[AllowEntry] = []
    for item in raw.get("entries", []):
        if not isinstance(item, dict):
            errors.append("allowlist entry must be a mapping")
            continue
        missing = sorted(required - item.keys())
        if missing:
            errors.append(f"entry {item.get('id', '?')} missing: {', '.join(missing)}")
            continue
        try:
            expiry = date.fromisoformat(str(item["expiry"]))
        except ValueError:
            errors.append(f"entry {item['id']} expiry not an ISO date")
            continue
        if expiry < today:
            errors.append(f"allowlist entry {item['id']} expired on {expiry}")
        try:
            re.compile(str(item["reason_pattern"]))
        except re.error as exc:
            errors.append(f"entry {item['id']} invalid reason_pattern: {exc}")
            continue
        entries.append(AllowEntry(
            id=str(item["id"]), path_pattern=str(item["path_pattern"]),
            reason_pattern=str(item["reason_pattern"]), owner=str(item["owner"]),
            reason=str(item["reason"]), expiry=expiry, issue=str(item["issue"]),
            classification=str(item["classification"]),
        ))
    return entries, errors


def evaluate(
    root: Path,
    allowlist_path: Path,
    today: date,
    *,
    scan_roots: tuple[str, ...] = SCAN_ROOTS,
    governed_paths: tuple[str, ...] = GOVERNED_PATHS,
) -> dict:
    findings = _find_skips(root, scan_roots, governed_paths)
    entries, errors = _load_allowlist(allowlist_path, today)
    matched_ids: set[str] = set()
    uncovered: list[SkipFinding] = []
    ambiguous: list[tuple[SkipFinding, list[str]]] = []
    for finding in findings:
        matches = [e for e in entries if e.matches(finding)]
        if not matches:
            uncovered.append(finding)
        elif len(matches) > 1:
            # Allowlist promises exactly one owning entry per skip. Multiple
            # matches hide overlapping patterns, so fail on ambiguity.
            ambiguous.append((finding, [e.id for e in matches]))
            matched_ids.update(e.id for e in matches)
        else:
            matched_ids.add(matches[0].id)
    stale = sorted(e.id for e in entries if e.id not in matched_ids)
    violations = [f"unapproved P0/security skip: {f.path}:{f.line} ({f.marker})" for f in uncovered]
    violations.extend(
        f"ambiguous allowlist match (covered by multiple entries): {f.path}:{f.line} -> {ids}"
        for f, ids in ambiguous
    )
    violations.extend(errors)
    return {
        "scanned_files": len(_iter_files(root, scan_roots, governed_paths)),
        "skip_count": len(findings),
        "covered_skips": list(matched_ids),
        "uncovered_skips": [asdict(f) for f in uncovered],
        "ambiguous_skips": [
            {"path": f.path, "line": f.line, "matched_ids": ids} for f, ids in ambiguous
        ],
        "stale_allowlist_entries": stale,
        "violation_count": len(violations),
        "violations": violations,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--allowlist", type=Path, default=Path("config/ci/p0_security_skip_allowlist.yaml")
    )
    parser.add_argument("--root", type=Path, default=_repo_root())
    parser.add_argument("--json-out", type=Path, default=None)
    args = parser.parse_args(argv)
    allowlist_path = args.allowlist if args.allowlist.is_absolute() else args.root / args.allowlist
    report = evaluate(args.root, allowlist_path, datetime.now(UTC).date())
    if args.json_out:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(
        f"p0-security skip governance: {report['scanned_files']} files, "
        f"{report['skip_count']} skips, {report['violation_count']} violations"
    )
    for message in report["violations"]:
        print(f"ERROR: {message}", file=sys.stderr)
    return 1 if report["violation_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
