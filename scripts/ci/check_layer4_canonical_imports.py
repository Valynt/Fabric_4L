#!/usr/bin/env python3
"""Fail when deprecated Layer 4 namespace imports are introduced.

The shim has been neutralized. All Layer 4 code must use canonical imports:
  - ``layer4_agents.*``   for the package namespace
  - ``api.*``, ``services.*``, etc. when running with services/layer4-agents/src on sys.path
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_ROOTS = [REPO_ROOT / "services", REPO_ROOT / "tests", REPO_ROOT / "scripts"]
PY_FILES = ("*.py",)
# Files permitted to still reference value_fabric.layer4 (e.g., neutralized shim stubs,
# verification/migration scripts, CI allowlist checks, shim neutralization tests).
ALLOWED_PREFIXES = (
    "value_fabric/",
    "scripts/verify_layer4",
    "scripts/migrate_l4",
    "scripts/ci/check_layer4_canonical_imports.py",
    "archive/",
    "tests/ci/test_layer4_canonical_service_imports.py",
    "services/layer4-agents/tests/test_code_quality.py",
)
PATTERN = re.compile(
    r"(^|\s)(from|import)\s+("
    r"value_fabric\.layer4|"
    r"value_fabric\.layer4_agents|"
    r"src\.fabric\.l4|"
    r"fabric\.l4"
    r")(\.|\s|$)"
)


def main() -> int:
    violations: list[str] = []
    for root in SCAN_ROOTS:
        for pat in PY_FILES:
            for path in root.rglob(pat):
                rel = path.relative_to(REPO_ROOT).as_posix()
                if any(rel.startswith(prefix) for prefix in ALLOWED_PREFIXES):
                    continue

                try:
                    text = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
                for i, line in enumerate(text.splitlines(), start=1):
                    if PATTERN.search(line):
                        violations.append(f"{rel}:{i}: {line.strip()}")

    if violations:
        print(
            "Layer 4 shim import check failed. Use canonical 'layer4_agents.*' imports instead of deprecated Layer 4 namespaces.",
            file=sys.stderr,
        )
        for item in violations:
            print(f"  - {item}", file=sys.stderr)
        return 1

    print("OK: no deprecated Layer 4 namespace imports found in scanned roots.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
