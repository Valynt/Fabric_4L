"""CI gate — only the shared framework may initialize an OTel TracerProvider.

Part of PR5 of the elevate-to-9 plan. Services must obtain tracers via
``opentelemetry.trace.get_tracer(__name__)`` and let the shared framework's
``init_telemetry()`` install the provider exactly once.

This gate fails when any module outside the allowlist:

- Instantiates ``TracerProvider(...)``
- Calls ``set_tracer_provider(...)``

Allowlist:
- ``packages/shared/src/value_fabric/shared/fastapi_framework/app.py`` (canonical init)
- ``tests/`` and ``conftest.py`` files (fixtures may set in-memory providers)
- ``scripts/`` (one-shot tooling)

A baseline file freezes pre-existing offenders. New offenders fail the build.

.. note::

    The gate flags **any** call named ``TracerProvider`` or ``set_tracer_provider``
    regardless of the defining module. If a service defines its own unrelated class
    with the same name, it will be flagged; add it to the baseline or rename the
    class to avoid the collision.

Usage::

    python scripts/ci/check_otel_tracer_provider_centralization.py
    python scripts/ci/check_otel_tracer_provider_centralization.py --update-baseline
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

_DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]

REPO_ROOT: Path = _DEFAULT_REPO_ROOT
BASELINE_FILE: Path = REPO_ROOT / "config" / "ci" / "otel_tracer_provider_baseline.txt"

SCAN_ROOTS = (
    REPO_ROOT / "services",
    REPO_ROOT / "packages" / "shared" / "src",
    REPO_ROOT / "value_fabric",
)

ALLOWED_PATH_FRAGMENTS = (
    "/tests/",
    "/test_",
    "conftest.py",
    "/scripts/",
    "packages/shared/src/value_fabric/shared/fastapi_framework/app.py",
    "packages/shared/src/value_fabric/shared/observability/platform.py",
)

EXCLUDED_DIR_NAMES = frozenset(
    {
        ".venv",
        "venv",
        "node_modules",
        "__pycache__",
        ".pytest_cache",
        ".hypothesis",
        ".uv-cache-local",
        ".tmp-local",
        ".mypy_cache",
        ".ruff_cache",
        "dist",
        "build",
    }
)


def _iter_python_files(root: Path):
    for path in root.iterdir():
        if path.is_dir():
            if path.name in EXCLUDED_DIR_NAMES or path.name.startswith("."):
                continue
            yield from _iter_python_files(path)
        elif path.suffix == ".py":
            yield path


def _is_allowlisted(path: Path) -> bool:
    rel = path.as_posix()
    return any(frag in rel for frag in ALLOWED_PATH_FRAGMENTS)


def _find_tracer_provider_offenders(path: Path) -> list[tuple[int, str]]:
    try:
        source = path.read_text(encoding="utf-8", errors="ignore")
    except OSError:
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = None
            if isinstance(func, ast.Name):
                name = func.id
            elif isinstance(func, ast.Attribute):
                name = func.attr
            if name == "TracerProvider":
                offenders.append((node.lineno, "TracerProvider(...)"))
            elif name == "set_tracer_provider":
                offenders.append((node.lineno, "set_tracer_provider(...)"))
    return offenders


def _format(path: Path, line: int) -> str:
    rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    return f"{rel}:{line}"


def _load_baseline() -> set[str]:
    if not BASELINE_FILE.exists():
        return set()
    entries: set[str] = set()
    for raw in BASELINE_FILE.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        entries.add(line)
    return entries


def _write_baseline(offenders: set[str]) -> None:
    header = (
        "# OTel TracerProvider centralization baseline (PR5 of elevate-to-9 plan).\n"
        "#\n"
        "# Frozen pre-existing TracerProvider/set_tracer_provider call sites outside\n"
        "# the shared framework. New entries are not permitted; migrate sites to use\n"
        "# the shared observability platform client (`configure_platform`).\n"
        "#\n"
        "# Format: <repo-relative-posix-path>:<line>\n"
    )
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(
        header + "\n".join(sorted(offenders)) + ("\n" if offenders else ""),
        encoding="utf-8",
    )


def scan() -> tuple[set[str], int]:
    offenders: set[str] = set()
    scanned = 0
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for py in _iter_python_files(root):
            if _is_allowlisted(py):
                continue
            scanned += 1
            for line, _ in _find_tracer_provider_offenders(py):
                offenders.add(_format(py, line))
    return offenders, scanned


def main(argv: list[str] | None = None) -> int:
    global REPO_ROOT, BASELINE_FILE, SCAN_ROOTS

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--update-baseline", action="store_true")
    parser.add_argument("--quiet", action="store_true")
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        dest="repo_root",
        help="Override the repository root (for testing).",
    )
    args = parser.parse_args(argv)

    if args.repo_root is not None:
        REPO_ROOT = args.repo_root.resolve()
        BASELINE_FILE = REPO_ROOT / "config" / "ci" / "otel_tracer_provider_baseline.txt"
        SCAN_ROOTS = (
            REPO_ROOT / "services",
            REPO_ROOT / "packages" / "shared" / "src",
            REPO_ROOT / "value_fabric",
        )

    offenders, scanned = scan()

    if args.update_baseline:
        _write_baseline(offenders)
        print(f"Baseline updated: {len(offenders)} entries -> {BASELINE_FILE}")
        return 0

    baseline = _load_baseline()
    new_offenders = sorted(offenders - baseline)

    if not args.quiet:
        print(
            f"Scanned {scanned} files; "
            f"{len(offenders)} TracerProvider/set_tracer_provider sites; "
            f"{len(baseline)} in baseline."
        )

    if new_offenders:
        print(
            "\nFAIL: new TracerProvider/set_tracer_provider use outside the shared framework. "
            "Use opentelemetry.trace.get_tracer(__name__) and let init_telemetry() install the provider.",
            file=sys.stderr,
        )
        for entry in new_offenders:
            print(f"  + {entry}", file=sys.stderr)
        return 1

    return 0


if __name__ == "__main__":
    sys.exit(main())
