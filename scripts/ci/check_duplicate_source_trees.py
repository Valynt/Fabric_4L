"""Runtime source-tree shim drift gate.

Ensures compatibility trees remain thin shims and do not reintroduce duplicate
logic. Per ADR-027, services/layerX/src/ is canonical; value_fabric/layerX/ is
the backward-compatibility shim tree. Layer 4 additionally packages only
``services/layer4-agents/src/layer4_agents``; legacy top-level Layer 4 trees
(for example ``src/api``, ``src/agents``, ``src/engine``, ``src/workflows``,
``src/services``, and any other top-level package mirrored under ``layer4_agents``)
must also remain explicit re-export shims.

Two valid shim patterns are accepted:
  1. Path-appender shim: modifies __path__ to point at the canonical service tree.
  2. Re-export shim: ``from <canonical_package> import *``
"""

from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - Python <3.11 fallback for local tooling
    import tomli as tomllib  # type: ignore[no-redef]

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
LAYER4_SERVICE_ROOT = REPO_ROOT / "services/layer4-agents"
LAYER4_SRC_ROOT = LAYER4_SERVICE_ROOT / "src"
LAYER4_CANONICAL_PACKAGE = LAYER4_SRC_ROOT / "layer4_agents"
LAYER4_EXPECTED_PACKAGES = ["src/layer4_agents"]

# Pattern for re-export shims: from <module> import *
SHIM_REEXPORT_RE = re.compile(r"^\s*from\s+([\w\.]+)\s+import\s+\*", re.MULTILINE)
# Pattern for path-appender shims: __path__.append(...) or __path__.insert(...)
SHIM_PATH_APPENDER_RE = re.compile(r"__path__\.(append|insert)\s*\(", re.MULTILINE)


@dataclass(frozen=True)
class LayerMap:
    layer: str
    # canonical_root: the authoritative implementation tree (services/layerX/src/)
    canonical_root: Path
    # compat_root: the backward-compatibility shim tree (value_fabric/layerX/)
    compat_root: Path
    # canonical_import_root: the import prefix for the canonical package
    canonical_import_root: str


# Per ADR-027 (Accepted 2026-05-13): services/ is canonical, value_fabric/ is shim.
LAYER_MAP: tuple[LayerMap, ...] = (
    LayerMap(
        "layer1",
        REPO_ROOT / "services/layer1-ingestion/src",
        REPO_ROOT / "value_fabric/layer1",
        "value_fabric.layer1",
    ),
    LayerMap(
        "layer2",
        REPO_ROOT / "services/layer2-extraction/src/layer2_extraction",
        REPO_ROOT / "value_fabric/layer2",
        "value_fabric.layer2",
    ),
    LayerMap(
        "layer3",
        REPO_ROOT / "services/layer3-knowledge/src",
        REPO_ROOT / "value_fabric/layer3",
        "value_fabric.layer3",
    ),
    LayerMap(
        "layer4",
        REPO_ROOT / "services/layer4-agents/src",
        REPO_ROOT / "value_fabric/layer4",
        "value_fabric.layer4",
    ),
    LayerMap(
        "layer5",
        REPO_ROOT / "services/layer5-ground-truth/src/layer5_ground_truth",
        REPO_ROOT / "value_fabric/layer5",
        "layer5_ground_truth",
    ),
    LayerMap(
        "layer6",
        REPO_ROOT / "services/layer6-benchmarks/src",
        REPO_ROOT / "value_fabric/layer6",
        "value_fabric.layer6",
    ),
)


def _expected_module(import_root: str, rel: Path) -> str:
    parts = rel.with_suffix("").parts
    if parts and parts[-1] == "__init__":
        parts = parts[:-1]
    suffix = ".".join(parts)
    return f"{import_root}.{suffix}" if suffix else import_root


def _has_implementation(text: str) -> bool:
    """Return True if the source defines any class, function, or async function.

    Used to reject files that combine a shim pattern with implementation logic.
    """
    try:
        tree = ast.parse(text)
    except SyntaxError:
        return True  # Unparseable — treat as non-shim to be safe.
    return any(
        isinstance(node, (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef))
        for node in ast.walk(tree)
    )


def _is_valid_shim(path: Path, expected_module: str) -> bool:
    """Return True if path is a recognised backward-compatibility shim.

    Accepts two patterns:
    - Path-appender: modifies ``__path__`` to redirect imports to the canonical tree.
    - Re-export: ``from <expected_module> import *``

    In both cases the file must contain no class or function definitions —
    implementation logic in a shim indicates an incomplete migration.
    """
    text = path.read_text(encoding="utf-8")
    if len(text) > 4000:
        # Shims must be small; large files contain implementation logic.
        return False
    # Accept path-appender shims (ADR-027 canonical pattern for value_fabric/layerX/).
    if SHIM_PATH_APPENDER_RE.search(text):
        # Reject if the file also contains class/function definitions.
        return not _has_implementation(text)
    # Accept empty namespace placeholders for package roots that only document the shim.
    stripped_lines = [
        line.strip()
        for line in text.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if path.name == "__init__.py" and not stripped_lines:
        return True
    # Accept re-export shims.
    match = SHIM_REEXPORT_RE.search(text)
    return bool(match and match.group(1) == expected_module)


def _iter_py(root: Path) -> set[Path]:
    return {p.relative_to(root) for p in root.rglob("*.py")}


def _check_layer4_package_source() -> list[dict[str, str]]:
    """Assert Layer 4 packaging only includes the canonical layer4_agents tree."""
    pyproject_path = LAYER4_SERVICE_ROOT / "pyproject.toml"
    if not pyproject_path.exists():
        return [
            {
                "layer": "layer4",
                "canonical": str(pyproject_path.relative_to(REPO_ROOT).as_posix()),
                "compatibility": "missing",
                "expected_import": "packages = ['src/layer4_agents']",
            }
        ]
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    packages = (
        data.get("tool", {})
        .get("hatch", {})
        .get("build", {})
        .get("targets", {})
        .get("wheel", {})
        .get("packages")
    )
    if packages == LAYER4_EXPECTED_PACKAGES:
        return []
    return [
        {
            "layer": "layer4",
            "canonical": str(pyproject_path.relative_to(REPO_ROOT).as_posix()),
            "compatibility": json.dumps(packages),
            "expected_import": "packages = ['src/layer4_agents']",
        }
    ]


def _find_layer4_top_level_violations() -> list[dict[str, str]]:
    """Reject implementation files duplicated outside the canonical layer4_agents package."""
    violations: list[dict[str, str]] = []
    for canonical_root in sorted(p for p in LAYER4_CANONICAL_PACKAGE.iterdir() if p.is_dir()):
        package = canonical_root.name
        compat_root = LAYER4_SRC_ROOT / package
        if not compat_root.exists():
            continue
        shared = _iter_py(compat_root) & _iter_py(canonical_root)
        for rel in sorted(shared):
            compat_file = compat_root / rel
            expected = _expected_module(f"layer4_agents.{package}", rel)
            if not _is_valid_shim(compat_file, expected):
                violations.append(
                    {
                        "layer": "layer4-top-level",
                        "canonical": str((canonical_root / rel).relative_to(REPO_ROOT).as_posix()),
                        "compatibility": str(compat_file.relative_to(REPO_ROOT).as_posix()),
                        "expected_import": expected,
                    }
                )
    return violations


def find_violations(layers: set[str]) -> list[dict[str, str]]:
    violations: list[dict[str, str]] = []
    for m in LAYER_MAP:
        if m.layer not in layers or not m.canonical_root.exists() or not m.compat_root.exists():
            continue
        canonical_files = _iter_py(m.canonical_root)
        compat_files = _iter_py(m.compat_root)
        shared = canonical_files & compat_files
        for rel in sorted(shared):
            compat_file = m.compat_root / rel
            expected = _expected_module(m.canonical_import_root, rel)
            if not _is_valid_shim(compat_file, expected):
                violations.append(
                    {
                        "layer": m.layer,
                        "canonical": str((m.canonical_root / rel).relative_to(REPO_ROOT).as_posix()),
                        "compatibility": str(compat_file.relative_to(REPO_ROOT).as_posix()),
                        "expected_import": expected,
                    }
                )
    if "layer4" in layers:
        violations.extend(_check_layer4_package_source())
        violations.extend(_find_layer4_top_level_violations())
    return violations


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--json", action="store_true", help="emit machine-readable JSON summary")
    parser.add_argument(
        "--layers",
        nargs="+",
        choices=[m.layer for m in LAYER_MAP],
        default=[m.layer for m in LAYER_MAP],
    )
    args = parser.parse_args(argv)

    violations = find_violations(set(args.layers))
    if args.json:
        print(json.dumps({"pass": not violations, "violations": violations}))
    else:
        if violations:
            print("ERROR: Compatibility modules must be explicit shims.", file=sys.stderr)
            for v in violations:
                print(
                    f"  [{v['layer']}] {v['compatibility']} "
                    f"(expected: from {v['expected_import']} import *)",
                    file=sys.stderr,
                )
        else:
            print("No non-shim duplicate runtime modules detected.")
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
