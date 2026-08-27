#!/usr/bin/env python3
"""Authoritative, fail-closed test-debt governance evaluator."""
from __future__ import annotations

import argparse
import fnmatch
import json
import os
import re
import sys
import time
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any

import yaml

SCHEMA_VERSION = "1.0"
DEFAULT_SCAN_ROOTS = ["tests", "services", "apps/web/e2e"]
SOURCE_SUFFIXES = {".py", ".ts", ".tsx", ".js", ".jsx", ".mjs"}
EXCLUDED_PARTS = {
    ".git", ".mypy_cache", ".pytest_cache", ".ruff_cache", ".tmp",
    ".venv", "venv", "__pycache__", "coverage", "dist", "node_modules",
    "playwright-report", "test-results",
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
    # pytest decorator markers (no source-scan regex; reconciled by nodeid).
    ("flaky", re.compile(r"flaky-no-source-scan")),
    ("quarantine", re.compile(r"quarantine-no-source-scan")),
]
SUPPORTED_MARKERS = {name for name, _ in MARKERS}
FORBIDDEN_MARKERS = {"test.only", "describe.only", "it.only"}
VALID_SEVERITIES = {"P0", "P1", "P2"}
VALID_LAUNCH_GATES = {"mandatory", "optional", "excluded"}
VALID_CLASSIFICATIONS = {
    "valid_environment_limitation", "temporary_bug_waiver", "obsolete_test",
    "unacceptable_coverage_gap", "quarantine",
}
VALID_DISPOSITIONS = {"retain", "remove", "repair", "replace_with_characterization"}
FLAKY_MARKERS = {"flaky", "quarantine"}
FLAKY_EXTRA_FIELDS = {
    "nodeid", "introduced_or_detected_on", "issue", "failure_evidence",
    "affected_gate", "retry_count", "status",
}
VALID_FLAKY_STATUSES = {"proposed", "active", "renewed", "resolved"}
CRITICAL_PATH_PARTS = (
    "/security/", "tenant", "auth", "gateway", "/contract/", "golden",
    "persistence", "/release/", "certif",
)
TEMPORAL_PATTERN = re.compile(
    r"\b(?:TODO|FIXME|temporary|temporarily|until|expires?|expiry|soon|later|"
    r"next\s+(?:sprint|quarter|month|week|release)|Q[1-4]|H[1-2]|for\s+now|"
    r"short[ -]term)\b|\b20\d{2}[-/]\d{1,2}[-/]\d{1,2}\b",
    re.IGNORECASE,
)


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
    reason_pattern: str
    owner: str
    reason: str
    expires_on: date
    severity: str
    launch_gate: str
    classification: str
    disposition: str
    ticket_id: str
    work_item: str
    due_on: date

    def matches(self, finding: Finding) -> bool:
        return (
            self.marker == finding.marker
            and fnmatch.fnmatch(finding.path, self.path_pattern)
            and bool(re.search(self.reason_pattern, finding.text, re.IGNORECASE))
        )


@dataclass(frozen=True)
class Violation:
    code: str
    message: str
    path: str | None = None
    entry_id: str | None = None
    line: int | None = None


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def _violation(code: str, message: str, **location: Any) -> Violation:
    return Violation(code, message, **location)


def _load_register(path: Path, today: date) -> tuple[list[RegisterEntry], list[Violation]]:
    violations: list[Violation] = []
    try:
        raw = yaml.safe_load(path.read_text(encoding="utf-8")) if path.exists() else {}
    except (OSError, yaml.YAMLError) as exc:
        return [], [_violation("TDG100", f"cannot parse canonical register: {exc}")]
    if not isinstance(raw, dict) or not isinstance(raw.get("entries", []), list):
        return [], [_violation("TDG101", "register must contain an entries list")]
    required = {
        "id", "path_pattern", "marker", "reason_pattern", "owner", "reason",
        "expires_on", "severity", "launch_gate", "classification", "disposition",
        "remediation",
    }
    entries: list[RegisterEntry] = []
    ids: set[str] = set()
    keys: set[tuple[str, str, str]] = set()
    for index, item in enumerate(raw.get("entries", [])):
        if not isinstance(item, dict):
            violations.append(_violation("TDG102", f"entry {index} must be a mapping"))
            continue
        entry_id = str(item.get("id", f"entries[{index}]")).strip()
        missing = sorted(required - item.keys())
        remediation = item.get("remediation")
        if not isinstance(remediation, dict):
            remediation = {}
        missing_remediation = sorted({"ticket_id", "work_item", "due_on"} - remediation.keys())
        if missing or missing_remediation:
            fields = missing + [f"remediation.{name}" for name in missing_remediation]
            violations.append(_violation("TDG102", f"missing required fields: {', '.join(fields)}", entry_id=entry_id))
            continue
        if entry_id in ids:
            violations.append(_violation("TDG103", "duplicate entry id", entry_id=entry_id))
        ids.add(entry_id)
        key = (str(item["path_pattern"]), str(item["marker"]), str(item["reason_pattern"]))
        if key in keys:
            violations.append(_violation("TDG104", "duplicate path/marker/reason key", entry_id=entry_id))
        keys.add(key)
        severity = str(item["severity"])
        classification = str(item["classification"])
        disposition = str(item["disposition"])
        launch_gate = str(item["launch_gate"])
        marker = str(item["marker"])
        enum_checks = (
            (severity, VALID_SEVERITIES, "TDG105", "severity"),
            (classification, VALID_CLASSIFICATIONS, "TDG106", "classification"),
            (disposition, VALID_DISPOSITIONS, "TDG107", "disposition"),
            (launch_gate, VALID_LAUNCH_GATES, "TDG108", "launch_gate"),
            (marker, SUPPORTED_MARKERS - FORBIDDEN_MARKERS, "TDG109", "marker"),
        )
        for value, allowed, code, field in enum_checks:
            if value not in allowed:
                violations.append(_violation(code, f"unknown {field}: {value}", entry_id=entry_id))
        try:
            expires_on = date.fromisoformat(str(item["expires_on"]))
            due_on = date.fromisoformat(str(remediation["due_on"]))
        except ValueError:
            violations.append(_violation("TDG110", "expires_on and remediation.due_on must be ISO dates", entry_id=entry_id))
            continue
        if expires_on < today:
            violations.append(_violation("TDG111", f"registration expired on {expires_on}", entry_id=entry_id))
        is_flaky = marker in FLAKY_MARKERS
        if is_flaky:
            missing_flaky = sorted(FLAKY_EXTRA_FIELDS - item.keys())
            if missing_flaky:
                violations.append(_violation(
                    "TDG102",
                    f"missing flaky quarantine fields: {', '.join(missing_flaky)}",
                    entry_id=entry_id,
                ))
            status = str(item.get("status", ""))
            if status not in VALID_FLAKY_STATUSES:
                violations.append(_violation("TDG109", f"unknown flaky status: {status}", entry_id=entry_id))
        if is_flaky and expires_on < today:
            violations.append(_violation(
                "TDG116",
                f"flaky quarantine expired on {expires_on} for nodeid {item.get('nodeid', '?')}; "
                "quarantine must be renewed or the test re-enabled",
                entry_id=entry_id,
            ))
        if due_on > expires_on:
            violations.append(_violation("TDG112", "remediation due date is after expiry", entry_id=entry_id))
        text_fields = (item["path_pattern"], item["reason_pattern"], item["owner"], item["reason"], remediation["ticket_id"], remediation["work_item"])
        if any(not str(value).strip() for value in text_fields):
            violations.append(_violation("TDG113", "ownership, reason, matching, and remediation fields must be non-empty", entry_id=entry_id))
        try:
            re.compile(str(item["reason_pattern"]))
        except re.error as exc:
            violations.append(_violation("TDG114", f"invalid reason_pattern: {exc}", entry_id=entry_id))
            continue
        if classification == "valid_environment_limitation" and disposition != "retain":
            violations.append(_violation("TDG115", "environment limitations must use retain disposition", entry_id=entry_id))
        entries.append(RegisterEntry(
            id=entry_id, path_pattern=str(item["path_pattern"]), marker=marker,
            reason_pattern=str(item["reason_pattern"]), owner=str(item["owner"]),
            reason=str(item["reason"]), expires_on=expires_on, severity=severity,
            launch_gate=launch_gate, classification=classification,
            disposition=disposition, ticket_id=str(remediation["ticket_id"]),
            work_item=str(remediation["work_item"]), due_on=due_on,
        ))
    return entries, violations


def _is_test_surface(relative: Path, explicit_roots: bool) -> bool:
    posix = relative.as_posix()
    if explicit_roots:
        return True
    return (
        posix.startswith("tests/")
        or posix.startswith("apps/web/e2e/")
        or (posix.startswith("services/") and "/tests/" in f"/{posix}")
    )


def _iter_files(root: Path, scan_roots: list[str]) -> list[Path]:
    explicit = bool(scan_roots)
    roots = scan_roots or DEFAULT_SCAN_ROOTS
    files: set[Path] = set()
    for scan_root in roots:
        base = root / scan_root
        if not base.exists():
            continue
        candidates = [base] if base.is_file() else base.rglob("*")
        for path in candidates:
            if not path.is_file() or path.suffix.lower() not in SOURCE_SUFFIXES:
                continue
            relative = path.relative_to(root)
            if set(relative.parts) & EXCLUDED_PARTS or not _is_test_surface(relative, explicit):
                continue
            files.add(path)
    return sorted(files)


def _find_markers(root: Path, scan_roots: list[str]) -> tuple[list[Finding], int]:
    findings: list[Finding] = []
    files = _iter_files(root, scan_roots)
    for path in files:
        for number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "pytest.skip.Exception" in line:
                continue
            for marker, pattern in MARKERS:
                match = pattern.search(line)
                prefix = line[: match.start()] if match else ""
                # Scanner tests embed marker examples in string literals. Static debt
                # discovery must identify calls, not prose or fixture strings.
                inside_string = prefix.count('"') % 2 == 1 or prefix.count("'") % 2 == 1
                if match and not inside_string:
                    findings.append(Finding(path.relative_to(root).as_posix(), number, marker, line.strip()))
    return findings, len(files)


def _critical(path: str) -> bool:
    lowered = f"/{path.lower()}"
    return any(part in lowered for part in CRITICAL_PATH_PARTS)


def _entry_json(entry: RegisterEntry) -> dict[str, Any]:
    data = asdict(entry)
    data["expires_on"] = entry.expires_on.isoformat()
    data["due_on"] = entry.due_on.isoformat()
    return data


def evaluate(root: Path, register_path: Path, scan_roots: list[str], today: date) -> dict[str, Any]:
    started = time.perf_counter()
    register, violations = _load_register(register_path, today)
    findings, scanned_files = _find_markers(root, scan_roots)
    matched_ids: set[str] = set()
    unregistered: list[Finding] = []
    forbidden: list[Finding] = []
    ambiguous: list[Finding] = []
    for finding in findings:
        if finding.marker in FORBIDDEN_MARKERS:
            forbidden.append(finding)
            violations.append(_violation("TDG200", "focused-test marker is forbidden", path=finding.path, line=finding.line))
            continue
        matches = [entry for entry in register if entry.matches(finding)]
        if not matches:
            unregistered.append(finding)
            violations.append(_violation("TDG201", "unregistered test debt", path=finding.path, line=finding.line))
            continue
        if len(matches) > 1:
            ambiguous.append(finding)
            violations.append(_violation("TDG202", "marker matches multiple registrations", path=finding.path, line=finding.line))
        matched_ids.update(entry.id for entry in matches)
    stale = sorted(entry.id for entry in register if entry.id not in matched_ids)
    for entry_id in stale:
        violations.append(_violation("TDG203", "registration does not match a marker", entry_id=entry_id))
    for entry in register:
        if _critical(entry.path_pattern) and (
            entry.classification == "obsolete_test"
            or (entry.classification == "unacceptable_coverage_gap" and entry.disposition == "retain")
        ):
            violations.append(_violation("TDG301", "critical-path debt uses a prohibited policy", entry_id=entry.id))
        if TEMPORAL_PATTERN.search(entry.reason) and not entry.ticket_id:
            violations.append(_violation("TDG302", "temporal debt lacks remediation ticket", entry_id=entry.id))
    classification_counts = {name: 0 for name in sorted(VALID_CLASSIFICATIONS)}
    marker_counts: dict[str, int] = {}
    for entry in register:
        classification_counts[entry.classification] = classification_counts.get(entry.classification, 0) + 1
    for finding in findings:
        marker_counts[finding.marker] = marker_counts.get(finding.marker, 0) + 1
    inventory: dict[str, list[dict[str, Any]]] = {"P0": [], "P1": [], "P2": [], "VALID": []}
    for entry in register:
        group = "VALID" if entry.classification == "valid_environment_limitation" and entry.disposition == "retain" else entry.severity
        if group not in inventory:
            group = "P2"
        inventory[group].append(_entry_json(entry))
    for values in inventory.values():
        values.sort(key=lambda item: (item["due_on"], item["path_pattern"], item["id"]))
    domain_order = {"tenant": 0, "auth": 1, "security": 2, "gateway": 3, "contract": 4, "golden": 5, "persistence": 6, "release": 7}
    def rank(item: dict[str, Any]) -> tuple[Any, ...]:
        path = item["path_pattern"].lower()
        domain = min((score for name, score in domain_order.items() if name in path), default=8)
        return (domain, item["launch_gate"] != "mandatory", item["due_on"], item["path_pattern"], item["id"])
    remediation_queue = sorted(inventory["P0"], key=rank)
    expired_count = sum(item.code == "TDG111" for item in violations)
    mandatory_p0 = [entry for entry in register if entry.severity == "P0" and entry.launch_gate == "mandatory"]
    elapsed = round(time.perf_counter() - started, 6)
    summary = {
        "total_registered_markers": len(register), "total_detected_markers": len(findings),
        "expired_register_entries": expired_count, "unregistered_markers": len(unregistered),
        "forbidden_markers": len(forbidden), "matched_register_entries": len(matched_ids),
        "mandatory_p0_register_entries": len(mandatory_p0), "classification_counts": classification_counts,
        "ambiguous_markers": len(ambiguous), "stale_register_entries": len(stale),
        "violation_count": len(violations), "elapsed_seconds": elapsed,
    }
    return {
        "schema_version": SCHEMA_VERSION, "generated_on": today.isoformat(),
        "scan_roots": scan_roots or DEFAULT_SCAN_ROOTS, "scanned_files": scanned_files,
        "summary": summary, "marker_counts": marker_counts,
        "violations": [asdict(item) for item in violations],
        "findings": [asdict(item) for item in findings], "unregistered": [asdict(item) for item in unregistered],
        "forbidden": [asdict(item) for item in forbidden], "ambiguous": [asdict(item) for item in ambiguous],
        "stale_entries": stale, "inventory": inventory, "remediation_queue": remediation_queue,
        "registered_entries": len(register), "matched_entries": len(matched_ids),
        "total_registered_markers": len(register), "expired_register_entries": expired_count,
        "unregistered_markers": len(unregistered), "forbidden_markers": len(forbidden),
        "matched_register_entries": len(matched_ids),
        "register_errors": [item.message for item in violations if item.code.startswith("TDG1")],
        "mandatory_p0_entries": [_entry_json(entry) for entry in mandatory_p0],
    }


def _render_markdown(report: dict[str, Any]) -> str:
    summary = report["summary"]
    lines = ["# Test-Debt Governance Report", "", f"Schema: `{report['schema_version']}`", "", "## Metrics", "", "| Metric | Count |", "| --- | ---: |"]
    for key in ("scanned_files", "total_detected_markers", "total_registered_markers", "unregistered_markers", "ambiguous_markers", "stale_register_entries", "violation_count"):
        value = report.get(key, summary.get(key, 0))
        lines.append(f"| {key.replace('_', ' ').title()} | {value} |")
    lines += ["", "## Inventory", "", "| Group | Count |", "| --- | ---: |"]
    for group in ("P0", "P1", "P2", "VALID"):
        lines.append(f"| {group} | {len(report['inventory'][group])} |")
    lines += ["", "## Next remediation wave", ""]
    for item in report["remediation_queue"][:10]:
        lines.append(f"- `{item['id']}` — `{item['path_pattern']}` — {item['work_item']}")
    lines += ["", "## Violations", ""]
    lines.extend(f"- `{item['code']}` {item['message']}" for item in report["violations"]) or lines.append("- None")
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--register", type=Path, default=Path("config/ci/test_skip_register.yaml"))
    parser.add_argument("--root", type=Path, default=_repo_root())
    parser.add_argument("--scan-root", action="append", dest="scan_roots")
    parser.add_argument("--write-report", "--json-out", type=Path, dest="json_out")
    parser.add_argument("--md-out", type=Path)
    parser.add_argument("--collection-evidence", type=Path, help="Subordinate pytest collection output")
    parser.add_argument("--fail-mandatory-p0", action="store_true")
    args = parser.parse_args(argv)
    register_path = args.register if args.register.is_absolute() else args.root / args.register
    report = evaluate(args.root, register_path, args.scan_roots or [], date.today())
    if args.collection_evidence and args.collection_evidence.exists():
        report["collection_evidence"] = {"path": str(args.collection_evidence), "bytes": args.collection_evidence.stat().st_size}
    for path, content in ((args.json_out, json.dumps(report, indent=2) + "\n"), (args.md_out, _render_markdown(report))):
        if path:
            path.parent.mkdir(parents=True, exist_ok=True); path.write_text(content, encoding="utf-8")
    if summary_path := os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(summary_path).open("a", encoding="utf-8") as handle: handle.write(_render_markdown(report))
    print(f"test-debt governance: {report['scanned_files']} files, {len(report['findings'])} markers, {len(report['violations'])} violations")
    for item in report["violations"]:
        print(f"ERROR {item['code']}: {item['message']} ({item.get('path') or item.get('entry_id') or 'register'})", file=sys.stderr)
    release_failure = args.fail_mandatory_p0 and bool(report["mandatory_p0_entries"])
    return 1 if report["violations"] or release_failure else 0


if __name__ == "__main__":
    raise SystemExit(main())
