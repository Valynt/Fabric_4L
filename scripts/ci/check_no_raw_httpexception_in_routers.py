"""CI gate — forbid raw `raise HTTPException(...)` in router/API boundary code.

Part of PR3 of the elevate-to-9 plan. Routers must use canonical exceptions
from ``value_fabric.shared.error_handling.exceptions`` so error responses are
consistently shaped, logged, and observed.

Scope (router/API boundary):
- ``services/*/src/**/api/routes/**/*.py``
- ``services/*/src/**/api/main.py``
- ``services/api/app/routers/**/*.py``
- ``services/layer4-agents/src/layer4_agents/tenants/api/routes/**/*.py``

Behavior:
- Walks each matching file with the ``ast`` module and reports every
  ``raise HTTPException(...)`` site.
- Compares the offender set against the baseline file
  ``config/ci/httpexception_router_allowlist.txt``.
- Fails the build with exit code 1 if new offenders appear.
- ``--update-baseline`` rewrites the baseline (run locally, never in CI).

Usage::

    python scripts/ci/check_no_raw_httpexception_in_routers.py
    python scripts/ci/check_no_raw_httpexception_in_routers.py --update-baseline
"""

from __future__ import annotations

import argparse
import ast
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
BASELINE_FILE = REPO_ROOT / "config" / "ci" / "httpexception_router_allowlist.txt"

ROUTER_GLOBS = (
    "services/*/src/**/api/routes/**/*.py",
    "services/*/src/**/api/main.py",
    "services/api/app/routers/**/*.py",
    "services/api/app/main.py",
    "services/layer4-agents/src/layer4_agents/tenants/api/routes/**/*.py",
    "services/layer2-extraction/src/layer2_extraction/api/main.py",
    "services/layer5-ground-truth/src/layer5_ground_truth/api/**/*.py",
    "services/layer6-benchmarks/src/api/main.py",
)


def _collect_router_files() -> list[Path]:
    seen: set[Path] = set()
    for pattern in ROUTER_GLOBS:
        for path in REPO_ROOT.glob(pattern):
            if path.is_file() and path.suffix == ".py":
                seen.add(path)
    return sorted(seen)


def _find_http_exception_raises(path: Path) -> list[tuple[int, str]]:
    try:
        source = path.read_text(encoding="utf-8")
    except OSError:
        return []
    try:
        tree = ast.parse(source, filename=str(path))
    except SyntaxError:
        return []

    offenders: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Raise) or node.exc is None:
            continue
        exc = node.exc
        # raise HTTPException(...)
        if isinstance(exc, ast.Call):
            func = exc.func
            if isinstance(func, ast.Name) and func.id == "HTTPException":
                offenders.append((node.lineno, "HTTPException(...)"))
            elif isinstance(func, ast.Attribute) and func.attr == "HTTPException":
                offenders.append((node.lineno, "*.HTTPException(...)"))
        # raise HTTPException (no args, rare)
        elif isinstance(exc, ast.Name) and exc.id == "HTTPException":
            offenders.append((node.lineno, "HTTPException"))
    return offenders


def _format_offender(path: Path, line_no: int) -> str:
    rel = path.resolve().relative_to(REPO_ROOT).as_posix()
    return f"{rel}:{line_no}"


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
        "# Router HTTPException baseline (PR3 of elevate-to-9 plan).\n"
        "#\n"
        "# Each line is a frozen pre-existing `raise HTTPException(...)` site in router\n"
        "# code. New entries require explicit migration to canonical exceptions in\n"
        "# value_fabric.shared.error_handling.exceptions. Removing entries (i.e.,\n"
        "# migrating them) is always welcome.\n"
        "#\n"
        "# Format: <repo-relative-posix-path>:<line-no>\n"
    )
    BASELINE_FILE.parent.mkdir(parents=True, exist_ok=True)
    BASELINE_FILE.write_text(
        header + "\n".join(sorted(offenders)) + ("\n" if offenders else ""),
        encoding="utf-8",
    )


def scan() -> tuple[set[str], list[Path]]:
    files = _collect_router_files()
    offenders: set[str] = set()
    for f in files:
        for line_no, _ in _find_http_exception_raises(f):
            offenders.add(_format_offender(f, line_no))
    return offenders, files


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--update-baseline",
        action="store_true",
        help="Rewrite the baseline file to match the current state.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Suppress info output; only print violations.",
    )
    args = parser.parse_args(argv)

    offenders, scanned_files = scan()

    if args.update_baseline:
        _write_baseline(offenders)
        print(f"Baseline updated: {len(offenders)} entries -> {BASELINE_FILE}")
        return 0

    baseline = _load_baseline()
    new_offenders = sorted(offenders - baseline)
    removed = sorted(baseline - offenders)

    if not args.quiet:
        print(
            f"Scanned {len(scanned_files)} router files; "
            f"{len(offenders)} HTTPException sites; "
            f"{len(baseline)} in baseline."
        )

    if new_offenders:
        print(
            "\nFAIL: new raw HTTPException usage in router code. "
            "Use canonical exceptions from value_fabric.shared.error_handling.exceptions:",
            file=sys.stderr,
        )
        for entry in new_offenders:
            print(f"  + {entry}", file=sys.stderr)
        print(
            "\nMapping guidance:\n"
            "  400 -> BadRequestError\n"
            "  401 -> AuthenticationError\n"
            "  403 -> AuthorizationError (or TenantIsolationError)\n"
            "  404 -> NotFoundError\n"
            "  409 -> ConflictError\n"
            "  422 -> ValidationError\n"
            "  429 -> RateLimitError\n"
            "  503 -> ServiceUnavailableError\n",
            file=sys.stderr,
        )
        return 1

    if removed and not args.quiet:
        print(
            f"\nNote: {len(removed)} baseline entries no longer present "
            "(migrated). Consider running with --update-baseline."
        )

    return 0


if __name__ == "__main__":
    sys.exit(main())
