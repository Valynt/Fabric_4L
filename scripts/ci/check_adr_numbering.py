#!/usr/bin/env python3
"""Validate ADR numbering and filename/header consistency."""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re
import sys

ADR_FILENAME_RE = re.compile(r"^ADR-(\d{3})-[a-z0-9][a-z0-9-]*\.md$")
ADR_HEADER_RE = re.compile(r"^#\s+ADR-(\d{3}):\s+.+$")

# Primary + alternate ADR directories
ADR_DIRS = [
    Path("docs/explanations/adr"),
    Path("docs/architecture"),
]


@dataclass(frozen=True)
class AdrDoc:
    path: Path
    id_str: str
    id_num: int


def discover_adr_files() -> list[Path]:
    files: list[Path] = []
    for adr_dir in ADR_DIRS:
        if not adr_dir.exists():
            continue
        files.extend(
            p for p in adr_dir.glob("*.md") if p.name.lower() != "readme.md" and p.name.lower().startswith("adr-")
        )
    return sorted(files)


def parse_header_id(path: Path) -> str | None:
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        if line.startswith("# "):
            m = ADR_HEADER_RE.match(line.strip())
            return m.group(1) if m else None
    return None


def main() -> int:
    failures: list[str] = []
    docs: list[AdrDoc] = []

    for path in discover_adr_files():
        name_match = ADR_FILENAME_RE.match(path.name)
        if not name_match:
            failures.append(f"Invalid ADR filename format: {path}")
            continue

        file_id = name_match.group(1)
        header_id = parse_header_id(path)
        if header_id is None:
            failures.append(f"Missing/invalid ADR header ('# ADR-###: ...'): {path}")
            continue
        if file_id != header_id:
            failures.append(
                f"Filename/header ADR ID mismatch: {path} (filename ADR-{file_id}, header ADR-{header_id})"
            )

        docs.append(AdrDoc(path=path, id_str=file_id, id_num=int(file_id)))

    # Duplicate ID check
    by_id: dict[int, list[Path]] = {}
    for doc in docs:
        by_id.setdefault(doc.id_num, []).append(doc.path)
    for id_num, paths in sorted(by_id.items()):
        if len(paths) > 1:
            failures.append(
                f"Duplicate ADR ID ADR-{id_num:03d}: {', '.join(str(p) for p in paths)}"
            )

    # Sequential policy check (contiguous from 001..N)
    ids = sorted(by_id.keys())
    if ids:
        expected = list(range(1, len(ids) + 1))
        if ids != expected:
            failures.append(
                "ADR sequence policy violation. "
                f"Expected contiguous IDs {expected[0]:03d}..{expected[-1]:03d}, got: "
                + ", ".join(f"{n:03d}" for n in ids)
            )

    if failures:
        print("ADR numbering check failed:")
        for failure in failures:
            print(f"- {failure}")
        return 1

    print(f"ADR numbering check passed ({len(ids)} ADR files validated).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
