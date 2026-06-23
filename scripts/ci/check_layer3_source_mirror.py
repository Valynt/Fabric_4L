#!/usr/bin/env python3
"""Fail CI when Layer 3 source-of-truth path contracts drift.

Architecture note (ADR-027, accepted 2026-05-13):
  services/layer3-knowledge/src/ is the canonical source tree. The historical
  value_fabric/layer3 namespace is retained only as a compatibility placeholder.

This script enforces two remaining contracts:
  1. value_fabric/layer3 contains no runtime Python files beyond __init__.py.
  2. No file in the service tree may contain unresolved merge-conflict markers.
"""

from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CANONICAL_ROOT = ROOT / "services" / "layer3-knowledge" / "src"
COMPAT_NAMESPACE = ROOT / "value_fabric" / "layer3"
ALLOWED_COMPAT_FILES = {Path("__init__.py")}


def _py_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _violations() -> list[str]:
    violations: list[str] = []
    canonical_files = {path.relative_to(CANONICAL_ROOT) for path in _py_files(CANONICAL_ROOT)}

    # Contract 1: the historical namespace must stay placeholder-only.
    for path in _py_files(COMPAT_NAMESPACE):
        rel = path.relative_to(COMPAT_NAMESPACE)
        if rel not in ALLOWED_COMPAT_FILES:
            violations.append(
                "runtime file found in compatibility namespace: "
                f"value_fabric/layer3/{rel.as_posix()}"
            )

    # Contract 2: no unresolved merge-conflict markers anywhere in the service tree.
    # Match the full three-marker pattern to avoid false positives from section
    # dividers that use repeated '=' characters in comments.
    for rel in sorted(canonical_files):
        path = CANONICAL_ROOT / rel
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        # A real conflict block starts with "<<<<<<< " (7 < followed by a space
        # or branch name) and ends with ">>>>>>> " — check for both anchors.
        if "<<<<<<<" in text and ">>>>>>>" in text:
            violations.append(
                "merge conflict markers detected: "
                f"services/layer3-knowledge/src/{rel.as_posix()}"
            )

    return violations


def main() -> int:
    violations = _violations()
    if not violations:
        print("OK: Layer 3 canonical tree and compatibility shims are aligned.")
        return 0

    print("ERROR: Layer 3 source-of-truth contract failed.")
    print("Canonical source-of-truth: services/layer3-knowledge/src")
    print("Compatibility namespace: value_fabric/layer3 (placeholder/shims only)")
    for violation in violations:
        print(f" - {violation}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
