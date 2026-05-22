"""Detect non-canonical runtime imports that still target value_fabric facades.

This gate reports Python imports that still reference compatibility namespaces
under ``value_fabric`` for runtime layer packages.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

RUNTIME_PATTERNS = {
    "layer1": re.compile(r"\b(from|import)\s+value_fabric\.layer1(\b|\.)"),
    "layer2": re.compile(r"\b(from|import)\s+value_fabric\.layer2(\b|\.)"),
    "layer3": re.compile(r"\b(from|import)\s+value_fabric\.layer3(\b|\.)"),
    "layer4": re.compile(r"\b(from|import)\s+value_fabric\.layer4(\b|\.)"),
    "layer6": re.compile(r"\b(from|import)\s+value_fabric\.layer6(\b|\.)"),
}

CANONICAL_HINTS = {
    "layer1": "services/layer1-ingestion/src/layer1_ingestion/",
    "layer2": "services/layer2-extraction/src/layer2_extraction/",
    "layer3": "services/layer3-knowledge/src/",
    "layer4": "services/layer4-agents/src/",
    "layer6": "services/layer6-benchmarks/src/",
}

SKIP_DIRS = {".git", ".venv", "venv", "node_modules", "__pycache__", ".pytest_cache", ".mypy_cache"}

# Known intentional references: shim implementation, docs/governance, and CI check scripts.
ALLOW_PREFIXES = (
    "value_fabric/",
    "docs/",
    "scripts/ci/",
    "tests/contract/",
    "tests/arch/",
)


def _allowed(rel_path: str) -> bool:
    return rel_path.startswith(ALLOW_PREFIXES)


def _scan() -> dict[str, list[str]]:
    violations: dict[str, list[str]] = {k: [] for k in RUNTIME_PATTERNS}
    for root in (REPO_ROOT / "services", REPO_ROOT / "tests", REPO_ROOT / "scripts"):
        if not root.exists():
            continue
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
            for fname in filenames:
                if not fname.endswith(".py"):
                    continue
                file_path = Path(dirpath) / fname
                rel_path = file_path.relative_to(REPO_ROOT).as_posix()
                if _allowed(rel_path):
                    continue
                content = file_path.read_text(encoding="utf-8")
                for layer, pattern in RUNTIME_PATTERNS.items():
                    if pattern.search(content):
                        violations[layer].append(rel_path)
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Check non-canonical runtime imports")
    parser.add_argument("--strict", action="store_true", help="Fail when violations are present")
    args = parser.parse_args(argv)

    violations = _scan()
    total = sum(len(v) for v in violations.values())
    if total == 0:
        print("No non-canonical runtime imports found.")
        return 0

    print("Non-canonical runtime imports detected:")
    for layer, files in violations.items():
        if not files:
            continue
        print(f"\n- {layer}: {len(files)} file(s)")
        print(f"  Canonical path hint: {CANONICAL_HINTS[layer]}")
        for rel in sorted(set(files)):
            print(f"    - {rel}")

    if args.strict:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
