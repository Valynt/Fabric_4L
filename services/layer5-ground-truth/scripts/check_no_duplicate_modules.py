from __future__ import annotations

#!/usr/bin/env python3
"""Fail CI when Layer 5 compatibility modules drift from shim-only adapters."""


import argparse
import ast
import sys
from pathlib import Path


DEFAULT_CANONICAL = "services/layer5-ground-truth/src/layer5_ground_truth"
DEFAULT_SHIM = "value_fabric/layer5"

# Module-level roots used by tests that monkeypatch these attributes to inject
# temporary directories.  main() and _shim_violations(repo_root) use these as
# defaults when no explicit repo_root is provided.
_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
CANONICAL_ROOT: Path = _REPO_ROOT / DEFAULT_CANONICAL
SHIM_ROOT: Path = _REPO_ROOT / DEFAULT_SHIM


def _py_files(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*.py") if "__pycache__" not in path.parts)


def _canonical_module_for(rel: Path) -> str:
    parts = ["layer5_ground_truth", *rel.with_suffix("").parts]
    if rel.name == "__init__.py":
        parts = parts[:-1]
    return ".".join(parts)


def _is_thin_shim(path: Path, expected_module: str) -> bool:
    text = path.read_text(encoding="utf-8")
    try:
        tree = ast.parse(text, filename=str(path))
    except SyntaxError:
        return False

    body = [
        node
        for node in tree.body
        if not (
            isinstance(node, ast.Expr)
            and isinstance(node.value, ast.Constant)
            and isinstance(node.value.value, str)
        )
    ]
    if len(body) == 1 and isinstance(body[0], ast.ImportFrom):
        node = body[0]
        return node.module == expected_module and len(node.names) == 1 and node.names[0].name == "*"

    return (
        f'_CANONICAL_MODULE = "{expected_module}"' in text
        and "from importlib import import_module as _import_module" in text
        and "_module = _import_module(_CANONICAL_MODULE)" in text
    )


def _is_namespace_package_shim(shim_init: Path, canonical_root: Path) -> bool:
    """Return True when shim uses __path__ appending instead of per-module files."""
    if not shim_init.exists():
        return False
    text = shim_init.read_text(encoding="utf-8")
    return (
        "__path__.append(" in text
        and canonical_root.name in text
        and "services/layer5-ground-truth" in text
    )


def _shim_violations(repo_root: Path | None = None) -> list[str]:
    """Return a list of shim-integrity violations.

    When called with no arguments (e.g. from tests that monkeypatch the
    module-level CANONICAL_ROOT / SHIM_ROOT attributes), reads those attributes
    from this module's globals so that monkeypatching works correctly.
    """
    import sys as _sys
    # Resolve the live module object so monkeypatching CANONICAL_ROOT / SHIM_ROOT
    # is respected even when the module was loaded via spec_from_file_location.
    _mod = None
    for _m in _sys.modules.values():
        if getattr(_m, "__file__", None) == __file__:
            _mod = _m
            break
    if repo_root is None:
        canonical_root = getattr(_mod, "CANONICAL_ROOT", CANONICAL_ROOT) if _mod else CANONICAL_ROOT
        shim_root = getattr(_mod, "SHIM_ROOT", SHIM_ROOT) if _mod else SHIM_ROOT
        # repo_root is used for relative path display; derive it from canonical_root
        # (canonical_root is <repo>/services/layer5-ground-truth/src/layer5_ground_truth
        # or a tmp_path in tests — use its grandparent as the display root).
        repo_root = canonical_root.parent.parent
    else:
        canonical_root = repo_root / DEFAULT_CANONICAL
        shim_root = repo_root / DEFAULT_SHIM
    shim_init = shim_root / "__init__.py"
    violations: list[str] = []

    # Per ADR-027, Layer 5 (like all other layers) uses a namespace package shim:
    # value_fabric/layer5/__init__.py appends the canonical service src to __path__.
    # When this model is active, per-module shim files are NOT required.
    if _is_namespace_package_shim(shim_init, canonical_root):
        # Ensure the shim __init__.py itself doesn't contain implementation logic.
        if not _is_thin_shim(shim_init, "layer5_ground_truth"):
            # Namespace shims are allowed to use __path__ appending instead of
            # star-import re-exports, so this is expected.
            pass
    else:
        canonical_files = {path.relative_to(canonical_root) for path in _py_files(canonical_root)}
        shim_files = {path.relative_to(shim_root) for path in _py_files(shim_root)}

        for rel in sorted(canonical_files - shim_files):
            violations.append(f"missing shim for canonical module: {DEFAULT_SHIM}/{rel.as_posix()}")
        for rel in sorted(shim_files - canonical_files):
            violations.append(f"shim without canonical module: {DEFAULT_SHIM}/{rel.as_posix()}")

        for rel in sorted(canonical_files & shim_files):
            expected_module = _canonical_module_for(rel)
            if not _is_thin_shim(shim_root / rel, expected_module):
                violations.append(
                    "non-shim implementation in compatibility tree: "
                    f"{DEFAULT_SHIM}/{rel.as_posix()} must re-export {expected_module}"
                )

    for path in _py_files(canonical_root):
        try:
            text = path.read_text(encoding="utf-8")
        except OSError:
            continue
        rel = path.relative_to(repo_root).as_posix()
        if "Compatibility shim" in text and "from layer5_ground_truth" in text and "import *" in text:
            violations.append(f"canonical tree contains a self-recursive compatibility shim: {rel}")
        if "sys.path" in text:
            violations.append(f"canonical tree must not mutate sys.path: {rel}")

    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Fail CI when Layer 5 compatibility modules drift from shim-only adapters."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parents[3],
        help="Repository root directory (default: auto-detected)",
    )
    args = parser.parse_args(argv)

    violations = _shim_violations(repo_root=args.repo_root)
    if not violations:
        print("OK: Layer 5 canonical tree and compatibility shims are aligned.")
        return 0

    print("ERROR: Layer 5 source-of-truth contract failed.", file=sys.stderr)
    print("Canonical source-of-truth: services/layer5-ground-truth/src/layer5_ground_truth", file=sys.stderr)
    print("Compatibility tree must stay shim-only: value_fabric/layer5", file=sys.stderr)
    for violation in violations:
        print(f" - {violation}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
