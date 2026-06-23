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
DOCS_ARCHIVE_DIR = ROOT / "docs" / "archive" / "evidence" / "reports"
ARCHIVE_ALLOWLIST_PREFIXES = (REPORTS_DIR / "archive", DOCS_ARCHIVE_DIR)
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
        in_allowed_archive = any(
            file_path.resolve().is_relative_to(prefix.resolve())
            for prefix in ARCHIVE_ALLOWLIST_PREFIXES
        )
        if has_failure_marker and not in_allowed_archive:
            violations.append(
                f"{file_path.relative_to(ROOT)} contains failing snapshot markers but is not under "
                f"any allowed archive prefix: {', '.join(str(p.relative_to(ROOT)) for p in ARCHIVE_ALLOWLIST_PREFIXES)}"
            )

    if violations:
        print("FAIL reports evidence policy violations detected:")
        for violation in violations:
            print(f" - {violation}")
        print(
            "\nMove failing/historical snapshots into reports/archive/<date-context>/ or "
            "docs/archive/evidence/reports/<date-context>/, or remove them."
        )
        return 1

    print("PASS reports evidence policy check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
