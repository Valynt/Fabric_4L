#!/usr/bin/env python3
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

try:
    import yaml
except Exception:  # pragma: no cover
    yaml = None


DEFAULT_SCAN_ROOTS = [
    "apps/web/e2e",
    "tests/ci",
    "tests/contract",
    "tests/release",
    "tests/security",
]

EXCLUDED_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".tmp",
    "coverage",
    "dist",
    "node_modules",
    "playwright-report",
    "test-results",
}

MARKERS: list[tuple[str, re.Pattern[str]]] = [
    ("pytest.skip", re.compile(r"\bpytest\.skip\s*\(")),
    ("pytest.mark.skip", re.compile(r"\bpytest\.mark\.skip(?:if)?\s*\(")),
    ("pytest.mark.xfail", re.compile(r"\bpytest\.mark\.xfail\s*\(")),
    ("test.skip", re.compile(r"\btest\.skip\s*\(")),
    ("test.fixme", re.compile(r"\btest\.fixme\s*\(")),
    ("describe.skip", re.compile(r"\bdescribe\.skip\s*\(")),
    ("it.skip", re.compile(r"\bit\.skip\s*\(")),
    ("test.only", re.compile(r"\btest\.only\s*\(")),
    ("describe.only", re.compile(r"\bdescribe\.only\s*\(")),
    ("it.only", re.compile(r"\bit\.only\s*\(")),
]

VALID_SEVERITIES = {"P0", "P1", "P2"}
VALID_LAUNCH_GATES = {"mandatory", "optional", "excluded"}
VALID_CLASSIFICATIONS = {
    "valid_environment_limitation",
    "temporary_bug_waiver",
    "obsolete_test",
    "unacceptable_coverage_gap",
}
ALWAYS_FORBIDDEN_MARKERS = {"test.only", "describe.only", "it.only"}


@dataclass(frozen=True)
class Finding:
    path: str
    line: int
    marker: str
    text: str


@dataclass(frozen=True)
class RegisterEntry:
    id: str
    path_pattern: str
    marker: str
    owner: str
    reason: str
    expires_on: date
    severity: str
    launch_gate: str
    classification: str
    reason_pattern: str | None = None

    def matches(self, finding: Finding) -> bool:
        if self.marker != finding.marker:
            return False
        if not fnmatch.fnmatch(finding.path, self.path_pattern):
            return False
        if self.reason_pattern and not re.search(
            self.reason_pattern, finding.text, flags=re.IGNORECASE
        ):
            return False
        return True


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _rel(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _load_register(path: Path, today: date) -> tuple[list[RegisterEntry], list[str]]:
    if yaml is None:
        raise RuntimeError("PyYAML is required to parse the skip register")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    entries = raw.get("entries", []) if isinstance(raw, dict) else []
    errors: list[str] = []
    register: list[RegisterEntry] = []
    seen_ids: set[str] = set()
    required = {
        "id",
        "path_pattern",
        "marker",
        "owner",
        "reason",
        "expires_on",
        "severity",
        "launch_gate",
        "classification",
    }
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            errors.append(f"entry {index} is not a mapping")
            continue
        missing = sorted(required - set(entry))
        if missing:
            errors.append(f"entry {index} missing required field(s): {', '.join(missing)}")
            continue
        entry_id = str(entry["id"])
        if entry_id in seen_ids:
            errors.append(f"entry {entry_id} duplicates an existing id")
        seen_ids.add(entry_id)
        marker = str(entry["marker"])
        if marker not in {name for name, _ in MARKERS}:
            errors.append(f"entry {entry_id} has unsupported marker {marker}")
        severity = str(entry["severity"])
        if severity not in VALID_SEVERITIES:
            errors.append(f"entry {entry_id} has invalid severity {severity}")
        launch_gate = str(entry["launch_gate"])
        if launch_gate not in VALID_LAUNCH_GATES:
            errors.append(f"entry {entry_id} has invalid launch_gate {launch_gate}")
        classification = str(entry["classification"])
        if classification not in VALID_CLASSIFICATIONS:
            errors.append(f"entry {entry_id} has invalid classification {classification}")
        try:
            expires_on = date.fromisoformat(str(entry["expires_on"]))
        except ValueError:
            errors.append(f"entry {entry_id} has invalid expires_on {entry['expires_on']}")
            continue
        if expires_on < today:
            errors.append(f"entry {entry_id} expired on {expires_on.isoformat()}")
        if not str(entry["owner"]).strip() or not str(entry["reason"]).strip():
            errors.append(f"entry {entry_id} owner and reason must be non-empty")
        if classification == "temporary_bug_waiver" and (not str(entry["owner"]).strip() or not str(entry["expires_on"]).strip()):
            errors.append(f"entry {entry_id} temporary bug waiver requires owner and expires_on")
        register.append(
            RegisterEntry(
                id=entry_id,
                path_pattern=str(entry["path_pattern"]),
                marker=marker,
                owner=str(entry["owner"]),
                reason=str(entry["reason"]),
                expires_on=expires_on,
                severity=severity,
                launch_gate=launch_gate,
                classification=classification,
                reason_pattern=entry.get("reason_pattern"),
            )
        )
    return register, errors


def _iter_files(root: Path, scan_roots: list[str]) -> list[Path]:
    files: list[Path] = []
    for scan_root in scan_roots:
        base = root / scan_root
        if not base.exists():
            continue
        for path in base.rglob("*"):
            if not path.is_file():
                continue
            rel_parts = set(path.relative_to(root).parts)
            if rel_parts & EXCLUDED_PARTS:
                continue
            if path.suffix.lower() not in {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}:
                continue
            files.append(path)
    return sorted(files)


def _find_markers(root: Path, scan_roots: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for path in _iter_files(root, scan_roots):
        rel = _rel(path, root)
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
            stripped = line.strip()
            if "pytest.skip.Exception" in stripped:
                continue
            for marker, pattern in MARKERS:
                if pattern.search(line):
                    findings.append(Finding(rel, number, marker, stripped))
    return findings


def evaluate(
    root: Path,
    register_path: Path,
    scan_roots: list[str],
    today: date,
) -> dict[str, Any]:
    register, register_errors = _load_register(register_path, today)
    findings = _find_markers(root, scan_roots)
    unregistered: list[Finding] = []
    forbidden: list[Finding] = []
    matched_ids: set[str] = set()

    for finding in findings:
        if finding.marker in ALWAYS_FORBIDDEN_MARKERS:
            forbidden.append(finding)
            continue
        matches = [entry for entry in register if entry.matches(finding)]
        if not matches:
            unregistered.append(finding)
            continue
        matched_ids.update(entry.id for entry in matches)

    stale_entries = [
        entry.id
        for entry in register
        if entry.id not in matched_ids and not any(
            fnmatch.fnmatch(root_path, entry.path_pattern) for root_path in scan_roots
        )
    ]
    expired_entries = [
        error
        for error in register_errors
        if " expired on " in error
    ]
    classification_counts: dict[str, int] = {classification: 0 for classification in sorted(VALID_CLASSIFICATIONS)}
    for entry in register:
        classification_counts[entry.classification] = classification_counts.get(entry.classification, 0) + 1

    mandatory_p0_entries = [
        entry
        for entry in register
        if entry.severity == "P0" and entry.launch_gate == "mandatory"
    ]
    summary = {
        "total_registered_markers": len(register),
        "total_detected_markers": len(findings),
        "expired_register_entries": len(expired_entries),
        "unregistered_markers": len(unregistered),
        "forbidden_markers": len(forbidden),
        "matched_register_entries": len(matched_ids),
        "mandatory_p0_register_entries": len(mandatory_p0_entries),
        "classification_counts": classification_counts,
    }
    return {
        "summary": summary,
        "total_registered_markers": summary["total_registered_markers"],
        "expired_register_entries": summary["expired_register_entries"],
        "unregistered_markers": summary["unregistered_markers"],
        "forbidden_markers": summary["forbidden_markers"],
        "matched_register_entries": summary["matched_register_entries"],
        "register_errors": register_errors,
        "findings": [finding.__dict__ for finding in findings],
        "unregistered": [finding.__dict__ for finding in unregistered],
        "forbidden": [finding.__dict__ for finding in forbidden],
        "mandatory_p0_entries": [
            {**entry.__dict__, "expires_on": entry.expires_on.isoformat()}
            for entry in mandatory_p0_entries
        ],
        "stale_entries": stale_entries,
        "registered_entries": len(register),
        "matched_entries": len(matched_ids),
    }


def _write_github_step_summary(path: Path, report: dict[str, Any]) -> None:
    summary = report["summary"]
    lines = [
        "### Test Skip Governance",
        "",
        "| Metric | Count |",
        "| --- | ---: |",
        f"| Total registered markers | {summary['total_registered_markers']} |",
        f"| Expired register entries | {summary['expired_register_entries']} |",
        f"| Unregistered markers | {summary['unregistered_markers']} |",
        f"| Forbidden markers | {summary['forbidden_markers']} |",
        f"| Matched register entries | {summary['matched_register_entries']} |",
        f"| Mandatory P0 register entries | {summary['mandatory_p0_register_entries']} |",
        "",
    ]
    if report["register_errors"] or report["unregistered"] or report["forbidden"]:
        lines.append("Result: fail-closed violation detected.")
    else:
        lines.append("Result: all detected skip/fixme/xfail markers are governed.")
    lines.append("")
    with path.open("a", encoding="utf-8") as handle:
        handle.write("\n".join(lines))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Fail closed on ungoverned skip/fixme/xfail markers in launch-relevant tests"
    )
    parser.add_argument("--register", type=Path, default=Path("config/ci/test_skip_register.yaml"))
    parser.add_argument("--scan-root", action="append", dest="scan_roots")
    parser.add_argument("--write-report", type=Path)
    parser.add_argument(
        "--fail-mandatory-p0",
        action="store_true",
        help=(
            "Fail if the skip register contains any severity=P0 entries with "
            "launch_gate=mandatory, even before expires_on. Use in release workflows."
        ),
    )
    args = parser.parse_args()

    root = _repo_root()
    scan_roots = args.scan_roots or DEFAULT_SCAN_ROOTS
    report = evaluate(root, root / args.register, scan_roots, date.today())
    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        _write_github_step_summary(Path(summary_path), report)

    print(
        "test skip governance: "
        f"{len(report['findings'])} marker(s), "
        f"{len(report['unregistered'])} unregistered, "
        f"{len(report['forbidden'])} forbidden, "
        f"{report['expired_register_entries']} expired, "
        f"{report['matched_register_entries']} matched, "
        f"{len(report['mandatory_p0_entries'])} mandatory P0, "
        f"{len(report['register_errors'])} register error(s)"
    )
    for key in ("register_errors", "unregistered", "forbidden"):
        for item in report[key]:
            print(f"ERROR {key}: {item}", file=sys.stderr)
    if args.fail_mandatory_p0 and report["mandatory_p0_entries"]:
        for item in report["mandatory_p0_entries"]:
            print(f"ERROR mandatory_p0_entries: {item}", file=sys.stderr)
    return 1 if (
        report["register_errors"]
        or report["unregistered"]
        or report["forbidden"]
        or (args.fail_mandatory_p0 and report["mandatory_p0_entries"])
    ) else 0


if __name__ == "__main__":
    raise SystemExit(main())
