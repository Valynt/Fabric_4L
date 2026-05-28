#!/usr/bin/env python3
"""Enforce reports/ evidence artifact policy.

Rules:
1) reports/ artifacts are generated diagnostics and should not be treated as authoritative
   ship/no-ship evidence unless explicitly linked to gate output metadata.
2) Files containing known failing snapshot markers (e.g., "errors during collection")
   are forbidden outside the explicit archive allowlist path.
"""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
REPORTS_DIR = ROOT / "reports"
ARCHIVE_ALLOWLIST_PREFIX = REPORTS_DIR / "archive"
FAIL_MARKERS = (
    "errors during collection",
    "Interrupted:",
)


def is_text_candidate(path: Path) -> bool:
    return path.suffix.lower() in {".md", ".txt", ".log", ".json", ".yaml", ".yml"}


def main() -> int:
    if not REPORTS_DIR.exists():
        return 0

    violations: list[str] = []
    for file_path in REPORTS_DIR.rglob("*"):
        if not file_path.is_file() or not is_text_candidate(file_path):
            continue

        text = file_path.read_text(encoding="utf-8", errors="ignore")
        lowered = text.lower()

        has_failure_marker = any(marker.lower() in lowered for marker in FAIL_MARKERS)
        if has_failure_marker and not file_path.resolve().is_relative_to(ARCHIVE_ALLOWLIST_PREFIX.resolve()):
            violations.append(
                f"{file_path.relative_to(ROOT)} contains failing snapshot markers but is not under "
                f"{ARCHIVE_ALLOWLIST_PREFIX.relative_to(ROOT)}/"
            )

    if violations:
        print("FAIL reports evidence policy violations detected:")
        for violation in violations:
            print(f" - {violation}")
        print(
            "\nMove failing/historical snapshots into reports/archive/<date-context>/ or remove them."
        )
        return 1

    print("PASS reports evidence policy check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
