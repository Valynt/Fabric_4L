#!/usr/bin/env python3
"""Fail when readiness percentages conflict across canonical docs.

Checks:
1) ROADMAP.md, CHANGELOG.md, docs/readiness/current.md must agree on readiness % when declared.
2) Archived docs with readiness percentages must be tagged as historical snapshots.
"""
from __future__ import annotations

import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_FILES = [
    ROOT / "docs/readiness/current.md",
    ROOT / "ROADMAP.md",
    ROOT / "CHANGELOG.md",
]
ARCHIVE_GLOB = "docs/archive/**/*.md"
READINESS_RE = re.compile(r"(?i)launch\s+readiness[^\n\r:]*:\s*\*\*?\s*(\d{1,3})%")
GENERIC_RE = re.compile(r"(?i)readiness[^\n\r:]*:\s*\*\*?\s*(\d{1,3})%")


def parse_readiness_percent(text: str) -> int | None:
    for pat in (READINESS_RE, GENERIC_RE):
        m = pat.search(text)
        if m:
            return int(m.group(1))
    return None


def is_historical_snapshot(path: Path, text: str) -> bool:
    name = path.name
    lowered = text.lower()
    return (
        name.startswith("ARCHIVED_")
        or "historical snapshot" in lowered
        or "snapshot date:" in lowered
    )


def main() -> int:
    errors: list[str] = []
    readiness_values: dict[str, int] = {}

    for file_path in CANONICAL_FILES:
        if not file_path.exists():
            errors.append(f"Missing required file: {file_path.relative_to(ROOT)}")
            continue
        pct = parse_readiness_percent(file_path.read_text(encoding="utf-8"))
        if pct is not None:
            readiness_values[str(file_path.relative_to(ROOT))] = pct

    if len(set(readiness_values.values())) > 1:
        detail = ", ".join(f"{k}={v}%" for k, v in readiness_values.items())
        errors.append(f"Conflicting canonical readiness percentages found: {detail}")

    for archive_file in ROOT.glob(ARCHIVE_GLOB):
        text = archive_file.read_text(encoding="utf-8")
        if parse_readiness_percent(text) is None:
            continue
        if not is_historical_snapshot(archive_file, text):
            errors.append(
                "Archived file declares readiness % but is not tagged historical snapshot: "
                f"{archive_file.relative_to(ROOT)}"
            )

    if errors:
        print("FAIL readiness consistency check failed")
        for err in errors:
            print(f" - {err}")
        return 1

    print("PASS readiness consistency check passed")
    if readiness_values:
        for file_name, pct in readiness_values.items():
            print(f" - {file_name}: {pct}%")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
