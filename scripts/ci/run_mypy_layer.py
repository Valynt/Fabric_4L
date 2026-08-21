"""Run mypy for one service layer without shell-specific recipe syntax."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


def _build_mypy_command(paths: list[str], flags: list[str]) -> list[str]:
    """Build the mypy command as an argument list.

    Uses ``sys.executable -m mypy`` when the ``mypy`` console-script is not on
    PATH (common on Windows). Passing the executable as a list element — never
    a space-joined or shlex-split string — preserves Windows paths containing
    backslashes and spaces.
    """
    mypy = shutil.which("mypy")
    if mypy is None:
        # On Windows the `mypy` console-script is not guaranteed to be on
        # PATH; fall back to `sys.executable -m mypy` so the wrapper works
        # cross-platform. Mirrors check_mypy_baseline.py.
        return [sys.executable, "-m", "mypy", *paths, *flags]
    return [mypy, *paths, *flags]


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print(
            "Usage: run_mypy_layer.py <service-dir> <path> [<path> ...] -- [mypy flags...]",
            file=sys.stderr,
        )
        return 2

    try:
        separator = argv.index("--")
    except ValueError:
        paths = argv[1:]
        flags: list[str] = []
    else:
        paths = argv[1:separator]
        flags = argv[separator + 1 :]

    service_dir = Path(argv[0])
    if not paths:
        print(
            "Usage: run_mypy_layer.py <service-dir> <path> [<path> ...] -- [mypy flags...]",
            file=sys.stderr,
        )
        return 2

    if not service_dir.exists():
        print(f"Service directory not found: {service_dir}", file=sys.stderr)
        return 2

    cmd = _build_mypy_command(paths, flags)
    return subprocess.run(cmd, cwd=service_dir, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
