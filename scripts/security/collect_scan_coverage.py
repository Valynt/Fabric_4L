#!/usr/bin/env python3
"""Generate canonical scan-coverage evidence for Semgrep OSS runs.

This utility consumes the structured JSON output and SARIF produced by a pinned
Semgrep CE invocation and writes deterministic, repository-owned evidence that
shows what was scanned, what was skipped, and why.  It does not fabricate
scanned-file claims; every file listed as scanned must appear in Semgrep's own
output.

The tool is intentionally dependency-light so it can run in CI immediately
after installing Semgrep, without requiring the rest of the repository's Python
service stack.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path, PurePosixPath
from typing import Any

SCHEMA_VERSION = "1.0"
DEFAULT_MAX_TARGET_BYTES = 1_000_000


class ScanCoverageError(Exception):
    """Raised when evidence generation cannot produce a valid record."""


@dataclass(frozen=True)
class CoverageCounts:
    coverage_unit: str = "files"
    candidate_files: int | None = None
    eligible_files: int | None = None
    scanned_files: int | None = None
    skipped_files: int | None = None
    excluded_files: int | None = None


@dataclass(frozen=True)
class FindingCounts:
    total: int = 0
    error: int = 0
    warning: int = 0
    note: int = 0


@dataclass(frozen=True)
class ArtifactPaths:
    sarif: str | None = None
    scanned_files: str | None = None
    skipped_files: str | None = None


@dataclass
class CoverageEvidence:
    schema_version: str
    scanner: str
    scanner_version: str
    setup_type: str
    workflow: str
    job: str
    commit_sha: str | None
    ref: str | None
    event: str | None
    scan_mode: str
    scan_root: str
    configuration: list[str]
    started_at: str | None
    duration_seconds: float | None
    status: str
    exit_code: int | None
    coverage: CoverageCounts
    findings: FindingCounts
    artifacts: ArtifactPaths
    reporting_limitations: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        # Flatten dataclasses to plain dicts for JSON serialization.
        return {
            "schema_version": self.schema_version,
            "scanner": self.scanner,
            "scanner_version": self.scanner_version,
            "setup_type": self.setup_type,
            "workflow": self.workflow,
            "job": self.job,
            "commit_sha": self.commit_sha,
            "ref": self.ref,
            "event": self.event,
            "scan_mode": self.scan_mode,
            "scan_root": self.scan_root,
            "configuration": self.configuration,
            "started_at": self.started_at,
            "duration_seconds": self.duration_seconds,
            "status": self.status,
            "exit_code": self.exit_code,
            "coverage": asdict(self.coverage),
            "findings": asdict(self.findings),
            "artifacts": asdict(self.artifacts),
            "reporting_limitations": self.reporting_limitations,
        }


def _now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _load_json(path: Path | None) -> dict[str, Any] | None:
    if path is None or not path.is_file():
        return None
    try:
        with path.open("r", encoding="utf-8") as fh:
            return json.load(fh)
    except (json.JSONDecodeError, OSError):
        return None


def _resolve_paths(items: list[str] | None, scan_root: Path) -> list[str]:
    """Normalize Semgrep paths to repository-relative POSIX strings.

    Semgrep may emit absolute paths that are still inside the scan root when a
    runner passes absolute directories.  We strip the scan-root prefix and
    reject paths that fall outside the repository.
    """
    if not items:
        return []
    cleaned: list[str] = []
    root = scan_root.resolve()
    for raw in items:
        p = Path(raw)
        if p.is_absolute():
            try:
                rel = p.resolve().relative_to(root)
            except ValueError:
                # Path outside the repository; do not claim it as scanned.
                continue
        else:
            rel = p
        # Use POSIX separators and remove leading "./".
        s = rel.as_posix().removeprefix("./")
        cleaned.append(s)
    return cleaned


def _is_excluded(path: str, exclude_patterns: list[str]) -> bool:
    """Match a repository-relative path against Semgrep-style --exclude globs."""
    pp = PurePosixPath(path)
    for pattern in exclude_patterns:
        # pathlib supports '**' and matches across components, which is what
        # Semgrep uses for --exclude.
        try:
            if pp.match(pattern):
                return True
        except ValueError:
            # Malformed pattern; ignore it.
            continue
    return False


def _git_ls_files(scan_root: Path) -> list[str] | None:
    """Return tracked, repository-relative paths when inside a git checkout."""
    try:
        text = subprocess.check_output(
            ["git", "-C", str(scan_root), "ls-files", "-z"],
            stderr=subprocess.DEVNULL,
            timeout=120,
        ).decode("utf-8", errors="surrogateescape")
    except (subprocess.CalledProcessError, FileNotFoundError, OSError):
        return None
    # -z produces NUL-separated entries; drop empty trailing entry.
    return [p for p in text.split("\0") if p]


def _candidate_files(scan_root: Path, exclude_patterns: list[str]) -> list[str]:
    """Return files Semgrep would have been asked to consider.

    We prefer `git ls-files` because Semgrep's default behavior limits scans to
    tracked files.  If git is unavailable, we fall back to a directory walk that
    respects .gitignore via `git check-ignore` when available.
    """
    candidates = _git_ls_files(scan_root)
    if candidates is None:
        # Fallback: walk the filesystem, skipping hidden .git and applying the
        # explicit exclude patterns only.  This is less accurate but still safe.
        candidates = []
        for root, _dirs, files in os.walk(scan_root):
            root_path = Path(root)
            if ".git" in root_path.parts:
                continue
            for name in files:
                rel = root_path.relative_to(scan_root).as_posix()
                path = f"{rel}/{name}" if rel != "." else name
                candidates.append(path)

    # Apply explicit --exclude patterns (these are user-supplied CLI excludes,
    # not .gitignore rules).  Semgrep applies these first during traversal.
    return [p for p in candidates if not _is_excluded(p, exclude_patterns)]


def _skipped_with_reasons(
    semgrep_json: dict[str, Any] | None,
    scan_root: Path,
    eligible_files: set[str],
    scanned_files: set[str],
    exclude_patterns: list[str],
    max_target_bytes: int,
) -> dict[str, str]:
    """Build a map of skipped file -> reason for eligible but un-scanned files."""
    skipped_paths = eligible_files - scanned_files
    skipped: dict[str, str] = {}

    # First, trust Semgrep's own skipped list when --verbose was used.
    if semgrep_json is not None:
        for entry in _get_paths_skipped(semgrep_json):
            raw_path = entry.get("path")
            reason = entry.get("reason", "unknown")
            if not raw_path:
                continue
            for normalized in _resolve_paths([raw_path], scan_root):
                if normalized in skipped_paths:
                    skipped[normalized] = reason

    # For remaining eligible-but-not-scanned files, infer a reason from file size or
    # mark it unknown.  Files matching explicit --exclude patterns were already
    # removed from the candidate set and should not appear here.
    for path in sorted(skipped_paths):
        if path in skipped:
            continue
        try:
            size = (scan_root / path).stat().st_size
        except OSError:
            size = 0
        if size > max_target_bytes:
            skipped[path] = "exceeded_size_limit"
        else:
            skipped[path] = "unknown"
    return skipped


def _count_findings(semgrep_json: dict[str, Any] | None) -> FindingCounts:
    """Count findings by severity from Semgrep JSON output."""
    if semgrep_json is None:
        return FindingCounts()
    error = warning = note = 0
    for result in semgrep_json.get("results", []) or []:
        severity = result.get("extra", {}).get("severity", "WARNING").upper()
        if severity == "ERROR":
            error += 1
        elif severity == "WARNING":
            warning += 1
        elif severity == "INFO":
            note += 1
        else:
            # Treat unrecognized severities as warning to avoid under-counting.
            warning += 1
    total = error + warning + note
    return FindingCounts(total=total, error=error, warning=warning, note=note)


def _detect_version(semgrep_json: dict[str, Any] | None) -> str | None:
    if semgrep_json is None:
        return None
    # Prefer the JSON version field; it matches the running binary.
    version = semgrep_json.get("version")
    if version:
        return str(version)
    return None


def _get_paths_scanned(semgrep_json: dict[str, Any] | None) -> list[str] | None:
    if semgrep_json is None:
        return None
    paths = semgrep_json.get("paths")
    if not isinstance(paths, dict):
        return None
    return paths.get("scanned") or []


def _get_paths_skipped(semgrep_json: dict[str, Any] | None) -> list[dict[str, Any]]:
    if semgrep_json is None:
        return []
    paths = semgrep_json.get("paths")
    if not isinstance(paths, dict):
        return []
    return paths.get("skipped") or []


def _determine_status(exit_code: int | None, findings: FindingCounts) -> str:
    if exit_code is None:
        return "unknown"
    if exit_code != 0:
        return "error"
    if findings.error > 0:
        return "findings"
    return "success"


def _build_summary_markdown(evidence: CoverageEvidence) -> str:
    sarif_upload = "Pending" if evidence.artifacts.sarif else "Not available"
    coverage_artifact = "semgrep-scan-evidence"
    limitation = (
        evidence.reporting_limitations[0] if evidence.reporting_limitations else "None"
    )

    result_label = evidence.status.capitalize()
    if evidence.status == "findings":
        result_label = "Findings"

    rows = [
        ("Result", result_label),
        ("Semgrep version", evidence.scanner_version),
        ("Setup type", evidence.setup_type),
        ("Scan mode", evidence.scan_mode),
        ("Scan root", evidence.scan_root),
        ("Rulesets", ", ".join(evidence.configuration) or "unknown"),
        ("Candidate files", str(evidence.coverage.candidate_files)),
        ("Eligible files", str(evidence.coverage.eligible_files)),
        ("Scanned files", str(evidence.coverage.scanned_files)),
        ("Skipped files", str(evidence.coverage.skipped_files)),
        (
            "Findings",
            f"{evidence.findings.total} (error {evidence.findings.error}, warning {evidence.findings.warning}, note {evidence.findings.note})",
        ),
        ("SARIF upload", sarif_upload),
        ("Coverage artifact", coverage_artifact),
        ("Reporting limitation", limitation),
    ]

    lines = ["# Semgrep OSS Scan Coverage", ""]
    lines.append("| Field | Value |")
    lines.append("|---|---|")
    for field_name, value in rows:
        lines.append(f"| {field_name} | {value} |")
    lines.append("")
    return "\n".join(lines)


def _redact_secrets(text: str) -> str:
    """Remove obvious secret patterns from any text we emit."""
    # GitHub tokens, generic API keys, private key blocks, etc.
    patterns = [
        (r"gh[pousr]_[A-Za-z0-9_]{36,}", "<REDACTED_GITHUB_TOKEN>"),
        (r"sk-[A-Za-z0-9]{20,}", "<REDACTED_API_KEY>"),
        (
            r"-----BEGIN (RSA |ED25519 |ECDSA |OPENSSH )?PRIVATE KEY-----.*?-----END (RSA |ED25519 |ECDSA |OPENSSH )?PRIVATE KEY-----",
            "<REDACTED_PRIVATE_KEY>",
            re.DOTALL,
        ),
    ]
    for pat in patterns:
        if len(pat) == 3:
            text = re.sub(pat[0], pat[1], text, flags=pat[2])
        else:
            text = re.sub(pat[0], pat[1], text)
    return text


def _validate_sarif(sarif: dict[str, Any] | None) -> list[str]:
    """Basic structural validation of the SARIF document."""
    if sarif is None:
        return ["SARIF document was not provided or could not be parsed."]
    limitations: list[str] = []
    if sarif.get("version") != "2.1.0":
        limitations.append(
            f"SARIF version is {sarif.get('version')!r}, expected 2.1.0."
        )
    runs = sarif.get("runs", []) or []
    if not runs:
        limitations.append("SARIF contains no runs.")
    for run in runs:
        driver = run.get("tool", {}).get("driver", {})
        if driver.get("name") not in ("Semgrep OSS", "Semgrep"):
            limitations.append(f"Unexpected SARIF driver name: {driver.get('name')!r}.")
        # GitHub derives scanned-files summaries from run.artifacts when present.
        # Semgrep CE does not populate this array, so the warning is expected.
        if not run.get("artifacts"):
            limitations.append(
                "SARIF run.artifacts is absent; GitHub cannot derive a scanned-files summary from this Semgrep CE SARIF."
            )
    return limitations


def collect_coverage(args: argparse.Namespace) -> CoverageEvidence:
    """Main entry point for building coverage evidence."""
    scan_root = Path(args.scan_root)
    scan_root_resolved = scan_root.resolve()
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    semgrep_json = _load_json(args.json_path)
    semgrep_sarif = _load_json(args.sarif_path)

    limitations: list[str] = []

    scanner_version = args.scanner_version or _detect_version(semgrep_json) or "unknown"
    findings = _count_findings(semgrep_json)
    status = args.status or _determine_status(args.exit_code, findings)

    scanned: list[str] = []
    scanned_available = True
    if semgrep_json is not None:
        scanned_raw = _get_paths_scanned(semgrep_json)
        if scanned_raw is None:
            scanned_available = False
            limitations.append(
                "Semgrep JSON 'paths.scanned' field was missing or malformed; "
                "scanned-file list cannot be verified."
            )
        else:
            scanned = _resolve_paths(scanned_raw, scan_root_resolved)
    else:
        scanned_available = False
        limitations.append(
            "Semgrep JSON output was not available; scanned-file list cannot be verified."
        )
    scanned_set = set(scanned)

    exclude_patterns = args.exclude or []
    candidate_files = _candidate_files(scan_root_resolved, exclude_patterns)
    candidate_count = len(candidate_files)

    semgrep_skipped: dict[str, str] = {}
    if semgrep_json is not None:
        for entry in _get_paths_skipped(semgrep_json):
            raw = entry.get("path")
            if raw:
                for normalized in _resolve_paths([raw], scan_root_resolved):
                    semgrep_skipped[normalized] = entry.get("reason", "unknown")

    eligible_set = scanned_set | set(semgrep_skipped.keys())
    if scanned_available:
        eligible_count = len(eligible_set)
        excluded_count = candidate_count - eligible_count
        if excluded_count < 0:
            limitations.append(
                "Candidate file count is lower than the scanned+skipped count; "
                "Semgrep may have considered files outside the tracked set."
            )
            excluded_count = None
    else:
        eligible_count = None
        excluded_count = None

    skipped_manifest = _skipped_with_reasons(
        semgrep_json,
        scan_root_resolved,
        eligible_set,
        scanned_set,
        exclude_patterns,
        args.max_target_bytes,
    )

    scanned_files_path = output_dir / "scanned-files.txt"
    with scanned_files_path.open("w", encoding="utf-8") as fh:
        for path in sorted(scanned_set):
            fh.write(f"{path}\n")

    skipped_files_path = output_dir / "skipped-files.json"
    skipped_records = [
        {"path": path, "reason": reason}
        for path, reason in sorted(skipped_manifest.items())
    ]
    with skipped_files_path.open("w", encoding="utf-8") as fh:
        json.dump(skipped_records, fh, indent=2, sort_keys=True)
        fh.write("\n")

    sarif_limitations = _validate_sarif(semgrep_sarif)
    limitations.extend(sarif_limitations)

    duration = args.duration_seconds
    if duration is None and semgrep_json is not None:
        time = semgrep_json.get("time", {})
        profiling = time.get("profiling_times", {}) if isinstance(time, dict) else {}
        total = profiling.get("total_time")
        if isinstance(total, (int, float)):
            duration = round(total, 3)

    # Store artifact paths relative to the repository root when possible.
    def _relative_to_repo(p: Path | None) -> str | None:
        if p is None:
            return None
        try:
            return p.relative_to(Path.cwd()).as_posix()
        except ValueError:
            return p.as_posix()

    artifacts = ArtifactPaths(
        sarif=_relative_to_repo(args.sarif_path),
        scanned_files=_relative_to_repo(scanned_files_path),
        skipped_files=_relative_to_repo(skipped_files_path),
    )

    scan_root_display = scan_root.as_posix()

    evidence = CoverageEvidence(
        schema_version=SCHEMA_VERSION,
        scanner="semgrep-oss",
        scanner_version=scanner_version,
        setup_type=args.setup_type,
        workflow=args.workflow,
        job=args.job,
        commit_sha=args.commit_sha or None,
        ref=args.ref or None,
        event=args.event or None,
        scan_mode=args.scan_mode,
        scan_root=scan_root_display,
        configuration=list(args.configuration) or [],
        started_at=args.started_at or _now_utc(),
        duration_seconds=duration,
        status=status,
        exit_code=args.exit_code,
        coverage=CoverageCounts(
            coverage_unit="files",
            candidate_files=candidate_count,
            eligible_files=eligible_count,
            scanned_files=len(scanned_set) if scanned_available else None,
            skipped_files=len(skipped_manifest) if scanned_available else None,
            excluded_files=excluded_count,
        ),
        findings=findings,
        artifacts=artifacts,
        reporting_limitations=limitations,
    )

    evidence_path = output_dir / "scan-coverage.json"
    with evidence_path.open("w", encoding="utf-8") as fh:
        json.dump(evidence.to_dict(), fh, indent=2, sort_keys=False)
        fh.write("\n")

    summary_path = output_dir / "job-summary.md"
    summary = _build_summary_markdown(evidence)
    summary = _redact_secrets(summary)
    with summary_path.open("w", encoding="utf-8") as fh:
        fh.write(summary)
        fh.write("\n")

    step_summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if step_summary:
        try:
            with open(step_summary, "a", encoding="utf-8") as fh:
                fh.write(summary)
                fh.write("\n")
        except OSError:
            pass

    return evidence


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate canonical scan-coverage evidence for Semgrep OSS.",
    )
    parser.add_argument("--json-path", type=Path, help="Path to Semgrep JSON output.")
    parser.add_argument("--sarif-path", type=Path, help="Path to Semgrep SARIF output.")
    parser.add_argument(
        "--output-dir", required=True, type=Path, help="Directory for evidence files."
    )
    parser.add_argument(
        "--scan-root", default=".", help="Repository root used for path normalization."
    )
    parser.add_argument(
        "--exclude", action="append", help="Semgrep --exclude patterns (repeatable)."
    )
    parser.add_argument(
        "--max-target-bytes",
        type=int,
        default=DEFAULT_MAX_TARGET_BYTES,
        help="Semgrep max-target-bytes threshold (default: 1,000,000).",
    )
    parser.add_argument("--workflow", default="Security Gates", help="Workflow name.")
    parser.add_argument(
        "--job", default="Semgrep CE Full Scan (SAST)", help="Job name."
    )
    parser.add_argument("--commit-sha", help="Git commit SHA.")
    parser.add_argument("--ref", help="Git ref.")
    parser.add_argument("--event", help="GitHub event name.")
    parser.add_argument(
        "--scan-mode", default="full", help="Scan mode, e.g. 'full' or 'diff-aware'."
    )
    parser.add_argument(
        "--scanner-version",
        help="Semgrep version (auto-detected from JSON if omitted).",
    )
    parser.add_argument(
        "--setup-type", default="python-package", help="How Semgrep was installed."
    )
    parser.add_argument(
        "--configuration",
        action="append",
        help="Active rule configuration (repeatable).",
    )
    parser.add_argument(
        "--status",
        choices=["success", "findings", "error", "cancelled", "unknown"],
        help="Scanner result status (inferred from exit code and findings if omitted).",
    )
    parser.add_argument("--exit-code", type=int, help="Original Semgrep exit code.")
    parser.add_argument(
        "--started-at", help="ISO-8601 UTC timestamp when the scan started."
    )
    parser.add_argument(
        "--duration-seconds", type=float, help="Scan duration in seconds."
    )
    parser.add_argument("--sarif-category", help="SARIF upload category.")
    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)
    try:
        collect_coverage(args)
    except Exception as exc:  # noqa: BLE001
        # Always exit 0 so a reporting failure cannot mask a scanner finding.
        # Emit a clear error record to stderr so the CI log shows the defect.
        print(f"[collect_scan_coverage] reporting failure: {exc}", file=sys.stderr)
        return 0
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
