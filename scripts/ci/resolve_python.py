from __future__ import annotations

import subprocess
import sys


def _version_for(command: list[str]) -> tuple[int, int] | None:
    try:
        completed = subprocess.run(
            [*command, "-c", "import sys; print(f'{sys.version_info[0]}.{sys.version_info[1]}')"],
            check=True,
            capture_output=True,
            text=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return None

    try:
        major, minor = completed.stdout.strip().split(".", 1)
        return int(major), int(minor)
    except ValueError:
        return None


def main() -> int:
    candidates = [
        ["python3.11"],
        ["python3"],
        ["python"],
        ["py", "-3.11"],
        [sys.executable],
    ]

    for command in candidates:
        version = _version_for(command)
        if version is not None and version >= (3, 11):
            print(" ".join(command))
            return 0

    print("python3.11")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
