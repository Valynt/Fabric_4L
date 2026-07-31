#!/usr/bin/env python3
"""Verify pinned Node security backports before scanner metadata exceptions."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
REACT_ROUTER_ADVISORY = "GHSA-qwww-vcr4-c8h2"


def check() -> list[str]:
    errors: list[str] = []
    package = json.loads((ROOT / "package.json").read_text(encoding="utf-8"))
    pnpm = package.get("pnpm", {})
    overrides = pnpm.get("overrides", {})
    patched = pnpm.get("patchedDependencies", {})

    for selector in (
        "brace-expansion@^1.1.7",
        "brace-expansion@^2.0.1",
        "brace-expansion@^5.0.0",
    ):
        if overrides.get(selector) != "5.0.8":
            errors.append(
                f"{selector} must resolve to scanner-recognized patched version 5.0.8"
            )

    expected_patches = {
        "brace-expansion@5.0.8": "patches/brace-expansion@5.0.8.patch",
        "react-router@7.18.0": "patches/react-router@7.18.0.patch",
    }
    for dependency, patch_path in expected_patches.items():
        if patched.get(dependency) != patch_path:
            errors.append(f"missing pinned patch registration for {dependency}")
        elif not (ROOT / patch_path).is_file():
            errors.append(f"registered patch does not exist: {patch_path}")

    brace_patch = (ROOT / expected_patches["brace-expansion@5.0.8"]).read_text(
        encoding="utf-8"
    )
    for marker in ("module.exports = expand", "EXPANSION_MAX_LENGTH"):
        if marker not in brace_patch:
            errors.append(
                f"brace-expansion compatibility patch missing marker: {marker}"
            )

    router_patch = (ROOT / expected_patches["react-router@7.18.0"]).read_text(
        encoding="utf-8"
    )
    for marker in (
        "potentialCSRFAttackError = error",
        'method: "GET"',
        "if (!potentialCSRFAttackError)",
        "onError?.(error)",
    ):
        if router_patch.count(marker) < 4:
            errors.append(
                f"React Router CSRF backport missing compiled marker: {marker}"
            )

    return errors


def main() -> int:
    errors = check()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    print(
        "Node security backports verified: brace-expansion 5.0.8 compatibility and "
        f"React Router upstream fix for {REACT_ROUTER_ADVISORY}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
