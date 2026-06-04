#!/usr/bin/env python3
"""Fail on suspicious tracked path artifacts and unapproved .env-style tracked files."""
from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

ALLOWED_ENV_BASENAMES = {
    ".env.example",
    ".env.dev.example",
    ".env.production-compose.template",
}

ALLOWED_ENV_SUFFIXES = (
    ".env.example",
    ".env.template",
)
ALLOWED_ENV_PATHS = {
    "apps/web/.env.local.mock-auth.example",
}

DRIVE_LETTER_PREFIX = re.compile(r"^[A-Za-z][:][\\/]")
ESCAPED_DRIVE_LIKE = re.compile(r"^[A-Za-z](?:Users|\\x[0-9a-fA-F]{2}|\\[0-7]{3})")


def tracked_files() -> list[str]:
    out = subprocess.check_output(["git", "ls-files", "-z"], cwd=ROOT)
    return [p.decode("utf-8", errors="replace") for p in out.split(b"\0") if p]


def is_allowed_env_path(path: str) -> bool:
    if path in ALLOWED_ENV_PATHS:
        return True
    name = Path(path).name
    if name in ALLOWED_ENV_BASENAMES:
        return True
    return any(path.endswith(suffix) for suffix in ALLOWED_ENV_SUFFIXES)


def main() -> int:
    violations: list[str] = []

    for path in tracked_files():
        normalized = path.replace("\\", "/")

        if DRIVE_LETTER_PREFIX.search(path) or DRIVE_LETTER_PREFIX.search(normalized):
            violations.append(f"{path}: drive-letter path prefix is forbidden")

        if ESCAPED_DRIVE_LIKE.search(path):
            violations.append(f"{path}: escaped/non-portable path prefix is forbidden")

        env_like = Path(path).name.startswith(".env") or normalized.endswith(".env") or "/.env" in normalized
        if env_like and not is_allowed_env_path(path):
            violations.append(f"{path}: tracked .env-style file is not in approved template allowlist")

    if violations:
        print("FAIL path/env hygiene policy violations detected:", file=sys.stderr)
        for item in violations:
            print(f"  - {item}", file=sys.stderr)
        print(
            "\nAllowed tracked env templates: .env.example, .env.dev.example, *.env.example, *.env.template, .env.production-compose.template",
            file=sys.stderr,
        )
        return 1

    print("PASS path/env hygiene check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
