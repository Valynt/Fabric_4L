#!/usr/bin/env python3
"""Gate: block raw exception leakage in HTTP response construction."""
from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = (REPO_ROOT / "value_fabric", REPO_ROOT / "services")
SKIP_DIRS = {".git", "node_modules", "__pycache__", ".venv", ".tox", ".pytest_cache"}

BLOCK_PATTERNS = [
    re.compile(r"detail\s*=\s*str\((?:e|exc)\)"),
    re.compile(r"detail\s*=\s*repr\((?:e|exc)\)"),
    re.compile(r"detail\s*=\s*f[\"'][^\n]*\{(?:e|exc)\}"),
    re.compile(r"[\"'](?:error|message|detail)[\"']\s*:\s*str\((?:e|exc)\)"),
    re.compile(r"[\"'](?:error|message|detail)[\"']\s*:\s*repr\((?:e|exc)\)"),
    re.compile(r"traceback\.format_exc\("),
    re.compile(r"\bexc\.args\b"),
]

ALLOWLIST = (
    "scripts/ci/check_secure_error_envelope.py",
    "tests/security/",
    "tests/gates/",
)


def iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*.py"):
            if any(part in SKIP_DIRS for part in path.parts):
                continue
            files.append(path)
    return files


def is_allowlisted(rel: str) -> bool:
    norm = rel.replace("\\", "/")
    return any(token in norm for token in ALLOWLIST)


def scan() -> list[tuple[str, int, str]]:
    findings: list[tuple[str, int, str]] = []
    for path in iter_files():
        rel = str(path.relative_to(REPO_ROOT)).replace("\\", "/")
        if is_allowlisted(rel):
            continue
        src = path.read_text(encoding="utf-8", errors="ignore")
        for idx, line in enumerate(src.splitlines(), start=1):
            for pattern in BLOCK_PATTERNS:
                if pattern.search(line):
                    findings.append((rel, idx, line.strip()))
    return findings


def main() -> int:
    findings = scan()
    if not findings:
        print("secure-error-envelope gate passed")
        return 0

    print("secure-error-envelope gate FAILED")
    print("Disallowed error-response pattern(s) detected:")
    for rel, line, snippet in findings:
        print(f" - {rel}:{line}: {snippet}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
