#!/usr/bin/env python3
"""Enforce versioned shared-boundary surfaces (R2 / brooks-shared-hub-remediation Step 4).

The ``value_fabric.shared.identity`` and ``value_fabric.shared.error_handling`` modules are
imported by every service in the platform: a change to either exported surface
(``__all__``) ripples to all nine services. To bound that change radius, each boundary
carries a ``SURFACE_VERSION`` marker and its current surface is pinned in
``config/ci/shared_surface_contract.json``.

This standalone checker (CI-safe: AST-based, no service imports) enforces the bounded-change
policy:

- ``--check`` (default): regenerate the snapshot in memory and compare against the committed
  baseline. Any drift (surface or version change without coordinated regeneration) fails with
  exit 1, instructing the author to run ``--update`` and commit the regenerated baseline.
- ``--update``: regenerate ``config/ci/shared_surface_contract.json`` from the live
  ``__init__.py`` sources. Refuses to change a boundary's surface at an unchanged version
  (a surface change must be accompanied by a ``SURFACE_VERSION`` bump) and refuses version
  regressions.

The runtime counterpart is ``tests/contract/test_shared_boundary_contracts.py``, which imports
the modules and asserts the live surface matches this baseline.
"""

from __future__ import annotations

import argparse
import ast
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SHARED_SRC = REPO_ROOT / "packages" / "shared" / "src" / "value_fabric" / "shared"
BASELINE_PATH = REPO_ROOT / "config" / "ci" / "shared_surface_contract.json"

# The versioned shared-boundary surfaces governed by this check.
BOUNDARIES = ("identity", "error_handling")

SCHEMA_VERSION = 1
GENERATOR = "scripts/ci/check_shared_boundary_surfaces.py"


def _extract_surface(source_text: str) -> tuple[str, list[str]]:
    """Extract (SURFACE_VERSION, sorted __all__) from boundary source via AST.

    Works without importing the module so the check is deterministic and dependency-free
    (suitable for lightweight CI structural-preflight jobs).
    """
    tree = ast.parse(source_text)
    version: str | None = None
    names: list[str] = []

    for node in tree.body:
        if not isinstance(node, ast.Assign):
            continue
        for target in node.targets:
            if not isinstance(target, ast.Name):
                continue
            if target.id == "SURFACE_VERSION":
                if isinstance(node.value, ast.Constant) and isinstance(node.value.value, str):
                    version = node.value.value
            elif target.id == "__all__":
                if isinstance(node.value, ast.List):
                    names = [
                        elt.value
                        for elt in node.value.elts
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
                    ]
                    names = sorted(set(names))

    if version is None:
        raise SystemExit(
            f"FATAL: {SHARED_SRC}: boundary source is missing the SURFACE_VERSION marker. "
            "Add `SURFACE_VERSION = \"MAJOR.MINOR.PATCH\"` (outside __all__)."
        )
    return version, names


def build_snapshot() -> dict:
    boundaries: dict[str, dict] = {}
    for name in BOUNDARIES:
        module_path = SHARED_SRC / name / "__init__.py"
        if not module_path.is_file():
            raise SystemExit(f"FATAL: missing versioned boundary module: {module_path}")
        version, surface = _extract_surface(module_path.read_text(encoding="utf-8"))
        boundaries[name] = {"version": version, "surface": surface}
    return {
        "schema_version": SCHEMA_VERSION,
        "generator": GENERATOR,
        "boundaries": boundaries,
    }


def _load_baseline() -> dict:
    if not BASELINE_PATH.is_file():
        raise SystemExit(
            f"FATAL: missing committed baseline {BASELINE_PATH}. Run with --update to generate it."
        )
    return json.loads(BASELINE_PATH.read_text(encoding="utf-8"))


def _write_baseline(snapshot: dict) -> None:
    BASELINE_PATH.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_PATH.write_text(json.dumps(snapshot, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def _version_tuple(version: str) -> tuple[int, ...]:
    try:
        return tuple(int(part) for part in version.split("."))
    except ValueError as exc:  # pragma: no cover - defensive
        raise SystemExit(f"FATAL: non-numeric SURFACE_VERSION {version!r}") from exc


def _describe_diff(live: dict, baseline: dict) -> list[str]:
    lines: list[str] = []
    live_boundaries = live["boundaries"]
    baseline_boundaries = baseline.get("boundaries", {})
    for name in BOUNDARIES:
        live_entry = live_boundaries.get(name, {})
        base_entry = baseline_boundaries.get(name)
        if base_entry is None:
            lines.append(f"  {name}: not present in committed baseline")
            continue
        if live_entry.get("version") != base_entry.get("version"):
            lines.append(
                f"  {name}: version {base_entry.get('version')!r} -> {live_entry.get('version')!r}"
            )
        if live_entry.get("surface") != base_entry.get("surface"):
            old_surface: set[str] = set(base_entry.get("surface", []))
            new_surface: set[str] = set(live_entry.get("surface", []))
            added = sorted(new_surface - old_surface)
            removed = sorted(old_surface - new_surface)
            if added:
                lines.append(f"  {name}: added exported names: {', '.join(added)}")
            if removed:
                lines.append(f"  {name}: removed exported names: {', '.join(removed)}")
    return lines


def _cmd_check() -> int:
    live = build_snapshot()
    baseline = _load_baseline()
    if live.get("schema_version") != baseline.get("schema_version"):
        print(
            f"Schema mismatch: live={live.get('schema_version')!r} "
            f"baseline={baseline.get('schema_version')!r}. Regenerate with --update."
        )
        return 1
    if live == baseline:
        return 0

    print(f"Shared-boundary surface contract drift detected in {BASELINE_PATH.name}:")
    for line in _describe_diff(live, baseline):
        print(line)
    print(
        "A boundary's public surface (`__all__`) or version changed without coordinated "
        "regeneration. If you intentionally changed a boundary surface, bump its "
        f"SURFACE_VERSION marker and run: python {GENERATOR} --update; then commit the "
        "regenerated baseline."
    )
    return 1


def _cmd_update() -> int:
    live = build_snapshot()
    if BASELINE_PATH.is_file():
        baseline = _load_baseline()
        for name, live_entry in live["boundaries"].items():
            base_entry = baseline.get("boundaries", {}).get(name)
            if base_entry is None:
                continue
            if live_entry["version"] == base_entry["version"]:
                if live_entry["surface"] != base_entry["surface"]:
                    print(
                        f"Refusing to update: surface of '{name}' changed at unchanged version "
                        f"{live_entry['version']!r}. A surface change requires a "
                        "SURFACE_VERSION bump (bounded-change policy)."
                    )
                    return 1
            elif _version_tuple(live_entry["version"]) < _version_tuple(base_entry["version"]):
                print(
                    f"Refusing to update: '{name}' version regression "
                    f"{base_entry['version']!r} -> {live_entry['version']!r}."
                )
                return 1

    _write_baseline(live)
    print(f"Updated {BASELINE_PATH.relative_to(REPO_ROOT)}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update",
        action="store_true",
        help="Regenerate config/ci/shared_surface_contract.json from live boundary sources.",
    )
    args = parser.parse_args()

    if args.update:
        return _cmd_update()
    return _cmd_check()


if __name__ == "__main__":
    sys.exit(main())