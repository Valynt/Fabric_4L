#!/usr/bin/env python3
from __future__ import annotations

import pathlib
import re
import sys

PROD_DIRS = [
    pathlib.Path("apps/web/src"),
    pathlib.Path("services"),
    pathlib.Path("value_fabric"),
]
DENY = [
    r"tenant-e2e-001",
    r"case-e2e-approved-001",
    r"playwright-backend-validation-seed",
    r"svc-playwright-backend-validation",
    r"e2e-admin@valuefabric\.test",
]
ALLOW_PATH_SEGMENTS = (
    "/tests/",
    "/test_",
    "/__tests__/",
    ".test.",
    "/e2e/",
    "/fixtures/",
)
SKIP_PATH_SEGMENTS = (
    "/.venv",
    "/.venv-verify",
    "/.uv-cache",
    "/__pycache__",
    "/.pytest_cache",
    "/.mypy_cache",
    "/.ruff_cache",
    "/.hypothesis",
    "/node_modules",
    "/dist",
    "/build",
    "/.git",
    "/.tmp",
)

viol = []
for base in PROD_DIRS:
    for p in base.rglob("*"):
        if not p.is_file() or p.suffix in {
            ".png",
            ".jpg",
            ".jpeg",
            ".svg",
            ".lock",
            ".min",
            ".map",
        }:
            continue
        sp = str(p).replace("\\", "/")
        if any(seg in sp for seg in ALLOW_PATH_SEGMENTS):
            continue
        if any(seg in sp for seg in SKIP_PATH_SEGMENTS):
            continue
        try:
            txt = p.read_text(encoding="utf-8")
        except Exception:
            continue
        for pat in DENY:
            for m in re.finditer(pat, txt):
                viol.append(
                    f"{sp}:{txt[:m.start()].count(chr(10)) + 1}: matched '{pat}'"
                )

if viol:
    print("Found E2E-only constants in production paths:")
    print("\n".join(viol))
    sys.exit(1)

print("No E2E-only constants found in production paths.")
