"""Run mypy for one service layer without shell-specific recipe syntax."""

from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


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

    mypy = shutil.which("mypy")
    if mypy is None:
        print("mypy not found. Run: pip install mypy", file=sys.stderr)
        return 1

    return subprocess.run([mypy, *paths, *flags], cwd=service_dir, check=False).returncode


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
