"""Install Python dev dependencies for Fabric_4L service tests.

This is the portable implementation behind ``make setup``. It intentionally
keeps dependency installation centralized so local Windows shells and POSIX CI
use the same service list.
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]

INSTALL_TARGETS = (
    ("pytest support packages", None, ("pytest-timeout", "pytest-randomly", "pytest-env"), False),
    ("shared package", REPO_ROOT, ("-e", "packages/shared/src"), True),
    ("platform contract package", REPO_ROOT, ("-e", "packages/platform-contract/src/python"), True),
    ("API service dev dependencies", REPO_ROOT / "services/api", ("-e", ".[dev]"), False),
    ("Layer 1 dev dependencies", REPO_ROOT / "services/layer1-ingestion", ("-e", ".[dev]"), False),
    ("Layer 2 dev dependencies", REPO_ROOT / "services/layer2-extraction", ("-e", ".[dev]"), False),
    ("Layer 2.5 dev dependencies", REPO_ROOT / "services/layer2-5-signal-refinery", ("-e", ".[dev]"), False),
    ("Layer 3 dev dependencies", REPO_ROOT / "services/layer3-knowledge", ("-e", ".[dev]"), False),
    ("Layer 4 dev dependencies", REPO_ROOT / "services/layer4-agents", ("-e", ".[dev]"), False),
    ("Layer 5 dev dependencies", REPO_ROOT / "services/layer5-ground-truth", ("-e", ".[dev]"), False),
    ("Layer 6 dev dependencies", REPO_ROOT / "services/layer6-benchmarks", ("-e", ".[dev]"), False),
)


def _run_install(label: str, cwd: Path | None, args: tuple[str, ...], optional: bool) -> None:
    print(f"-> Installing {label}...")
    completed = subprocess.run(
        [sys.executable, "-m", "pip", "install", *args, "-q"],
        cwd=str(cwd or REPO_ROOT),
    )
    if completed.returncode == 0:
        return
    if optional:
        print(f"-> Skipping optional {label}: pip exited {completed.returncode}")
        return
    raise subprocess.CalledProcessError(completed.returncode, completed.args)


def main() -> int:
    print(f"-> Installing into {sys.executable}")
    for label, cwd, args, optional in INSTALL_TARGETS:
        _run_install(label, cwd, args, optional)
    print(f"OK: all service dependencies installed into {sys.executable}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
