#!/usr/bin/env python3
"""
CI guard for tenant-context singleton integrity.

The shared identity modules own process-wide tenant state (``ContextVar``,
rate-limit buckets, etc.).  The monorepo can expose the same physical files
through two import trees:

- ``value_fabric.shared.identity.*`` (canonical namespace-shim path)
- ``packages.shared.src.value_fabric.shared.identity.*`` (direct package path,
  reachable when ``packages/shared/src`` is on ``sys.path``)

If runtime code imports these modules through the direct package path, or mixes
both paths in the same file, Python can load independent module objects and
silently break tenant isolation.

This check:

1. Runs ``scripts/verify_tenant_drift.py`` to confirm the runtime singleton
   guard is working.
2. Scans source files for forbidden direct imports of
   ``packages.shared.src.value_fabric.shared.identity.{context,middleware,dependencies}``.
3. Reports any file that imports the same logical module through both the
   canonical and direct package paths.

Exit codes:
    0 - No drift detected.
    1 - Singleton violation or forbidden import detected.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIRS = ("services", "packages", "value_fabric", "scripts")
VERIFY_SCRIPT = ROOT / "scripts" / "verify_tenant_drift.py"

# Source files that are intentionally allowed to import through both paths
# because their sole purpose is to verify the singleton guard.
ALLOWLIST = {
    "scripts/verify_tenant_drift.py",
    "tests/security/test_tenant_context_import_singleton.py",
}

DIRECT_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+"
    r"(packages\.shared\.src\.value_fabric\.shared\.identity\.(context|middleware|dependencies))"
)
CANONICAL_IMPORT_RE = re.compile(
    r"^\s*(?:from|import)\s+"
    r"(value_fabric\.shared\.identity\.(context|middleware|dependencies))"
)


def _is_runtime_python(rel: str) -> bool:
    if not rel.endswith(".py"):
        return False
    ignored_parts = {"__pycache__", ".venv", "venv", "node_modules"}
    return not any(part in ignored_parts for part in rel.split("/"))


def _iter_runtime_files(repo_root: Path) -> list[Path]:
    files: list[Path] = []
    for directory in RUNTIME_DIRS:
        root = repo_root / directory
        if not root.exists():
            continue
        files.extend(
            p
            for p in root.rglob("*.py")
            if _is_runtime_python(p.relative_to(repo_root).as_posix())
        )
    return sorted(files)


def _run_dynamic_check() -> tuple[bool, str]:
    """Execute the standalone drift verification script."""
    result = subprocess.run(
        [sys.executable, str(VERIFY_SCRIPT)],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        return False, (
            f"Dynamic singleton check failed (exit {result.returncode}):\n"
            f"{result.stdout}\n{result.stderr}"
        )
    return True, ""


def _scan_static(repo_root: Path) -> tuple[list[str], list[str]]:
    forbidden: list[str] = []
    mixed: list[str] = []

    for p in _iter_runtime_files(repo_root):
        rel = p.relative_to(repo_root).as_posix()
        if rel in ALLOWLIST:
            continue

        source = p.read_text(encoding="utf-8", errors="ignore")
        has_canonical = False
        has_direct = False

        for lineno, line in enumerate(source.splitlines(), 1):
            if CANONICAL_IMPORT_RE.match(line):
                has_canonical = True
            if DIRECT_IMPORT_RE.match(line):
                has_direct = True
                forbidden.append(f"{rel}:{lineno}:{line.strip()}")

        if has_canonical and has_direct:
            mixed.append(f"{rel}: imports identity modules through both canonical and direct package paths")

    return forbidden, mixed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Verify tenant-context singleton integrity across namespace import paths."
    )
    parser.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)

    repo_root = args.repo_root.resolve()

    ok, message = _run_dynamic_check()
    if not ok:
        print(message)
        return 1

    forbidden, mixed = _scan_static(repo_root)
    if forbidden:
        print("Forbidden direct imports of the tenant identity modules:")
        for item in forbidden:
            print(f"  {item}")

    if mixed:
        print("Files importing tenant identity modules through BOTH paths:")
        for item in mixed:
            print(f"  {item}")

    if forbidden or mixed:
        return 1

    print("Tenant context singleton integrity check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
