#!/usr/bin/env python3
"""Fail CI when lockfiles contain known placeholder boilerplate."""
from pathlib import Path
import sys

LOCKFILES = [
    Path("services/layer3-knowledge/requirements.lock"),
    Path("services/layer6-benchmarks/requirements.lock"),
]

PLACEHOLDER_PATTERNS = (
    "This file serves as a placeholder",
    "Run the following to regenerate:",
)

failures: list[str] = []
for path in LOCKFILES:
    if not path.exists():
        failures.append(f"missing lockfile: {path}")
        continue
    text = path.read_text(encoding="utf-8", errors="replace")
    if any(pattern in text for pattern in PLACEHOLDER_PATTERNS):
        failures.append(f"placeholder boilerplate detected in {path}")

if failures:
    print("FAIL Lockfile placeholder validation failed:")
    for failure in failures:
        print(f"  - {failure}")
    sys.exit(1)

print("PASS Lockfile placeholder validation passed.")
