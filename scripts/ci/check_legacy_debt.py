#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from dataclasses import dataclass
from datetime import date
from pathlib import Path
from typing import Any

MARKERS = ("DEPRECATED", "OBSOLETE")
TEXT_EXTENSIONS = {
    ".py", ".ts", ".tsx", ".js", ".jsx", ".json", ".yaml", ".yml", ".md", ".txt", ".sh", ".toml", ".ini", ".cfg",
}
EXCLUDE_DIRS = {".git", "node_modules", ".venv", "venv", "dist", "build", ".mypy_cache", ".pytest_cache", "coverage", "artifacts"}


@dataclass
class Finding:
    kind: str
    key: str
    file: str
    line: int
    text: str


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_EXTENSIONS


def iter_tracked_files(root: Path) -> list[Path] | None:
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z"],
            cwd=root,
            check=True,
            capture_output=True,
            text=False,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    files: list[Path] = []
    for raw in result.stdout.split(b"\0"):
        if not raw:
            continue
        rel = raw.decode("utf-8", errors="ignore")
        path = root / rel
        if is_text_file(path) and not any(part in EXCLUDE_DIRS for part in path.parts):
            files.append(path)
    return files


def iter_files(root: Path) -> list[Path]:
    tracked_files = iter_tracked_files(root)
    if tracked_files is not None:
        return tracked_files

    files: list[Path] = []
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [name for name in dirnames if name not in EXCLUDE_DIRS]
        current_dir = Path(dirpath)
        for filename in filenames:
            p = current_dir / filename
            if p.is_file() and is_text_file(p):
                files.append(p)
    return files


def scan_markers(
    repo_root: Path, excluded_paths: set[str], excluded_prefixes: tuple[str, ...]
) -> list[Finding]:
    findings: list[Finding] = []
    for file_path in iter_files(repo_root):
        rel = file_path.relative_to(repo_root).as_posix()
        if rel in excluded_paths or rel.startswith(excluded_prefixes):
            continue
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except OSError:
            continue
        for idx, line in enumerate(lines, start=1):
            for marker in MARKERS:
                if marker in line:
                    if is_non_debt_marker_usage(marker, line):
                        continue
                    findings.append(Finding("marker", marker, rel, idx, line.strip()))
    return findings


def is_non_debt_marker_usage(marker: str, line: str) -> bool:
    """Ignore domain lifecycle statuses; keep explicit legacy/deprecation notices."""

    if marker != "DEPRECATED":
        return False

    normalized = line.strip().lower()
    semantic_tokens = (
        "approvalstatus.deprecated",
        "artifactstatus.deprecated",
        "formulastatus.deprecated",
        "auditaction.model_deprecated",
        "model_deprecated",
        "deprecated_use",
        'deprecated = "deprecated"',
        "deprecated: \"deprecate\"",
        "status_deprecated",
        "status: enum",
        '"status": "deprecated"',
        "optional filter:",
        "enum [",
        "enum:",
    )
    return any(token in normalized for token in semantic_tokens)


def scan_legacy_dirs(repo_root: Path, legacy_dirs: list[str]) -> list[Finding]:
    findings: list[Finding] = []
    for legacy_dir in legacy_dirs:
        path = repo_root / legacy_dir
        if path.exists():
            findings.append(Finding("legacy_dir", legacy_dir, legacy_dir, 1, "Legacy directory exists"))
    return findings


def load_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def allowed_delta(key: str, approvals: dict[str, Any]) -> int:
    item = approvals.get("approvals", {}).get(key)
    if not item:
        return 0
    expires_on = item.get("expires_on")
    if not expires_on:
        return 0
    if date.fromisoformat(expires_on) < date.today():
        return 0
    return int(item.get("allowed_increase", 0))


def staged_max(key: str, approvals: dict[str, Any], fallback: int) -> int:
    staged = approvals.get("staged_thresholds", {}).get(key, [])
    active_max = fallback
    today = date.today()
    for item in staged:
        effective_on = item.get("effective_on")
        max_count = item.get("max_count")
        if effective_on is None or max_count is None:
            continue
        if date.fromisoformat(effective_on) <= today:
            active_max = int(max_count)
    return active_max


def validate_obsolete_approval_metadata(approvals: dict[str, Any]) -> list[str]:
    errors: list[str] = []
    entries = approvals.get("obsolete_marker_approvals", [])
    for idx, entry in enumerate(entries, start=1):
        owner = (entry.get("owner") or "").strip()
        target_removal_date = entry.get("target_removal_date")
        if not owner:
            errors.append(f"obsolete_marker_approvals[{idx}] is missing owner")
        if not target_removal_date:
            errors.append(f"obsolete_marker_approvals[{idx}] is missing target_removal_date")
            continue
        try:
            date.fromisoformat(target_removal_date)
        except ValueError:
            errors.append(
                f"obsolete_marker_approvals[{idx}] has invalid target_removal_date: {target_removal_date}"
            )
    return errors


def safe_print(text: str, *, file: Any = None) -> None:
    stream = file if file is not None else sys.stdout
    try:
        print(text, file=stream)
    except UnicodeEncodeError:
        print(text.encode(stream.encoding or "utf-8", errors="replace").decode(stream.encoding or "utf-8"), file=stream)


def main() -> int:
    ap = argparse.ArgumentParser(description="Check legacy debt markers/directories against a baseline")
    ap.add_argument("--repo-root", type=Path, default=Path("."))
    ap.add_argument("--baseline", type=Path, default=Path("config/ci/legacy_debt_baseline.json"))
    ap.add_argument("--approvals", type=Path, default=Path("config/ci/legacy_debt_approvals.json"))
    ap.add_argument("--config", type=Path, default=Path("config/ci/legacy_debt_config.json"))
    ap.add_argument("--write-report", type=Path)
    args = ap.parse_args()

    repo_root = args.repo_root.resolve()
    config = load_json(args.config)
    legacy_dirs = config.get("legacy_directories", ["shared", "apps/web/src/legacy", "apps/web/src/obsolete"])

    excluded_paths = set(config.get("excluded_paths", []))
    excluded_prefixes = tuple(config.get("excluded_prefixes", []))
    marker_findings = scan_markers(repo_root, excluded_paths, excluded_prefixes)
    dir_findings = scan_legacy_dirs(repo_root, legacy_dirs)
    findings = marker_findings + dir_findings

    counts: dict[str, int] = {
        "DEPRECATED": sum(1 for f in marker_findings if f.key == "DEPRECATED"),
        "OBSOLETE": sum(1 for f in marker_findings if f.key == "OBSOLETE"),
        "legacy_directories": len(dir_findings),
    }

    baseline = load_json(args.baseline)
    baseline_counts = baseline.get("counts", {})
    approvals = load_json(args.approvals)

    regressions: list[str] = []
    metadata_errors = validate_obsolete_approval_metadata(approvals)
    for key, actual in counts.items():
        base = int(baseline_counts.get(key, 0))
        max_allowed = base + allowed_delta(key, approvals)
        staged_allowed = staged_max(key, approvals, fallback=max_allowed)
        effective_max = min(max_allowed, staged_allowed)
        if actual > effective_max:
            regressions.append(
                f"{key}: {actual} > max {effective_max} (baseline {base}, approved {max_allowed}, staged {staged_allowed})"
            )

    report = {
        "counts": counts,
        "baseline_counts": baseline_counts,
        "regressions": regressions,
        "metadata_errors": metadata_errors,
        "findings": [f.__dict__ for f in findings],
    }

    if args.write_report:
        args.write_report.parent.mkdir(parents=True, exist_ok=True)
        args.write_report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    safe_print("Legacy debt counts: " + json.dumps(counts, sort_keys=True))
    if findings:
        safe_print("Actionable findings:")
        for f in findings:
            safe_print(f"- {f.file}:{f.line} [{f.kind}:{f.key}] {f.text}")

    if metadata_errors:
        safe_print("ERROR: obsolete marker approvals are missing required metadata:", file=sys.stderr)
        for err in metadata_errors:
            safe_print(f"  - {err}", file=sys.stderr)

    if regressions:
        safe_print("ERROR: legacy debt regressions detected:", file=sys.stderr)
        for r in regressions:
            safe_print(f"  - {r}", file=sys.stderr)

    if metadata_errors or regressions:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
