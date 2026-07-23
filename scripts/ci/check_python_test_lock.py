from __future__ import annotations

import argparse
import shutil
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REQUIREMENTS = ROOT / "tests/requirements-test.txt"
DEFAULT_LOCK = ROOT / "tests/requirements-test.lock"


def compile_command(requirements: Path, output: Path) -> list[str]:
    return [
        "uv",
        "pip",
        "compile",
        str(requirements),
        "--python-version",
        "3.11",
        "--python-platform",
        "x86_64-unknown-linux-gnu",
        "--generate-hashes",
        "--custom-compile-command",
        "python scripts/ci/check_python_test_lock.py --write",
        "--output-file",
        str(output),
    ]


def write_lock(requirements: Path, lock: Path) -> int:
    completed = subprocess.run(compile_command(requirements, lock), cwd=ROOT, check=False)
    return completed.returncode


def check_lock(requirements: Path, lock: Path) -> int:
    if not requirements.is_file() or not lock.is_file():
        return 1
    with tempfile.TemporaryDirectory(prefix="fabric-python-lock-") as temp_dir:
        candidate = Path(temp_dir) / lock.name
        shutil.copy2(lock, candidate)
        completed = subprocess.run(compile_command(requirements, candidate), cwd=ROOT, check=False)
        if completed.returncode != 0:
            return completed.returncode
        return 0 if candidate.read_bytes() == lock.read_bytes() else 1


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args()
    if args.write:
        return write_lock(DEFAULT_REQUIREMENTS, DEFAULT_LOCK)
    return check_lock(DEFAULT_REQUIREMENTS, DEFAULT_LOCK)


if __name__ == "__main__":
    raise SystemExit(main())
