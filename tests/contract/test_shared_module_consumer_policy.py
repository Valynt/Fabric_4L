"""Contract test: every shared module must have a consumer or an explicit allowlist entry.

Enforces the R4 remediation (brooks-shared-hub-remediation Step 1): a module may not
live in ``packages/shared/src/value_fabric/shared/`` without at least one external
consumer (runtime or test) or an explicit allowlist justification. This prevents
speculative modules from accumulating surface area that must be maintained, reviewed,
and versioned with no consumers delivering value.

A "consumer" is any tracked Python file outside the shared package that references
``value_fabric.shared.<module>`` (dotted import) or ``from value_fabric.shared import <module>``.

Allowlisted modules are exceptions where the module is intentionally kept: test-tree
consumers that keep the module alive (``testing``, ``projections``) or modules outside
the current Step-1 deletion scope that are tracked for future cleanup
(``mcp_gateway``, ``storage``, and the top-level ``http_client``, ``tenant_context_metrics``,
``security_middleware`` modules).
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

SHARED_DIR = REPO_ROOT / "packages" / "shared" / "src" / "value_fabric" / "shared"

# Modules intentionally kept despite having no external consumer, with the reason.
# - testing: imported unconditionally by per-service conftests (L1, L2, L2-5, L5)
#   and tests/conftest.py; test-only infrastructure that keeps the shared hub testable.
# - projections: used by tests/integration/test_cross_store_consistency.py.
# - mcp_gateway / storage / http_client / tenant_context_metrics / security_middleware:
#   zero external consumers found during Step 1 but outside the approved deletion list;
#   tracked here so future cleanups can archive them deliberately.
ALLOWLIST: dict[str, str] = {
    "testing": "test-only infrastructure imported by per-service conftests (L1/L2/L2-5/L5) and tests/conftest.py",
    "projections": "test-only consumer tests/integration/test_cross_store_consistency.py",
    "mcp_gateway": "zero external consumers; outside Step-1 deletion scope, tracked for cleanup",
    "storage": "zero external consumers; outside Step-1 deletion scope, tracked for cleanup",
    "http_client": "zero external consumers; outside Step-1 deletion scope, tracked for cleanup",
    "tenant_context_metrics": "zero external consumers (internal shared consumers only); outside Step-1 deletion scope, tracked for cleanup",
    "security_middleware": "zero external consumers (test-only tests/security/test_security_headers.py); outside Step-1 deletion scope, tracked for cleanup",
}

# Modules that were archived in Step 1. If one is ever re-added it must acquire a
# consumer or an allowlist entry, so this is documentation, not an escape hatch.
ARCHIVED: dict[str, str] = {
    "billing_schemas": "archived Step 1 (R4): zero consumers",
    "tracing": "archived Step 1 (R4): zero consumers",
    "tests": "archived Step 1 (R4): zero consumers",
}


def _tracked_python_files() -> list[Path]:
    """Return the repo-relative paths of every git-tracked ``.py`` file."""
    result = subprocess.run(
        ["git", "ls-files", "*.py"],
        capture_output=True,
        text=True,
        cwd=REPO_ROOT,
        check=False,
    )
    if result.returncode != 0:
        raise AssertionError(f"git ls-files failed: {result.stderr}")
    return [Path(line) for line in result.stdout.splitlines() if line]


def _is_test_path(rel: Path) -> bool:
    return "tests" in rel.parts


def _module_names() -> list[str]:
    """Return every importable module name directly under the shared package."""
    names: list[str] = []
    for child in sorted(SHARED_DIR.iterdir()):
        if child.name.startswith("__") or child.name.startswith("."):
            continue
        if child.name in {"py.typed"}:
            continue
        if child.is_dir():
            names.append(child.name)
        elif child.suffix == ".py":
            names.append(child.stem)
    return names


def _consumers(module: str) -> tuple[list[Path], list[Path]]:
    """Return (runtime, test) consumers of ``value_fabric.shared.<module>``.

    A consumer is a git-tracked ``.py`` file outside the shared package that references
    the module via dotted import or ``from value_fabric.shared import ...``.
    """
    dotted = re.compile(r"value_fabric\.shared\." + re.escape(module) + r"\b")
    from_import = re.compile(
        r"from\s+value_fabric\.shared\s+import\s+[^\n]*\b" + re.escape(module) + r"\b"
    )
    runtime: list[Path] = []
    test: list[Path] = []
    for rel in _tracked_python_files():
        if rel.is_relative_to(SHARED_DIR):
            continue
        try:
            content = (REPO_ROOT / rel).read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        if not (dotted.search(content) or from_import.search(content)):
            continue
        (test if _is_test_path(rel) else runtime).append(rel)
    return runtime, test


def test_every_shared_module_has_a_consumer_or_allowlist_entry() -> None:
    """No module may live in ``shared`` without a consumer or an allowlist entry."""
    violations: list[str] = []
    for module in _module_names():
        if module in ARCHIVED:
            continue
        runtime, test = _consumers(module)
        if runtime or test:
            continue
        if module not in ALLOWLIST:
            violations.append(module)

    assert not violations, (
        "Shared modules without any external consumer must be removed or added to the "
        f"ALLOWLIST in {Path(__file__).name} with a justification. Violations: {sorted(violations)}"
    )


def test_allowlist_entries_are_not_dead_and_are_documented() -> None:
    """Allowlist entries must still exist on disk (no stale exceptions)."""
    missing = [
        name
        for name in ALLOWLIST
        if not (SHARED_DIR / name).exists()
        and not (SHARED_DIR / f"{name}.py").exists()
    ]
    assert not missing, (
        f"Allowlist entries reference modules that no longer exist: {sorted(missing)}. "
        "Remove the stale allowlist entry."
    )


def test_archived_modules_are_gone() -> None:
    """Modules archived in Step 1 must not exist on disk."""
    present = [
        name
        for name in ARCHIVED
        if (SHARED_DIR / name).exists() or (SHARED_DIR / f"{name}.py").exists()
    ]
    assert not present, (
        f"Archived shared modules were re-created on disk: {sorted(present)}. "
        "Re-add them only with a real consumer and a contract test."
    )
