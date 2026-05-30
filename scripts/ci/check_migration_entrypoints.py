#!/usr/bin/env python3
"""Validate migration entrypoints and revision history commands per maintained service."""

from __future__ import annotations

import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class ServiceMigrationContract:
    name: str
    service_dir: Path
    required_paths: tuple[Path, ...]
    entrypoint_command: tuple[str, ...]
    history_commands: tuple[tuple[str, ...], ...]


REPO_ROOT = Path(__file__).resolve().parents[2]

CONTRACTS: tuple[ServiceMigrationContract, ...] = (
    ServiceMigrationContract(
        name="layer1-ingestion",
        service_dir=Path("services/layer1-ingestion"),
        required_paths=(Path("alembic.ini"), Path("migrations/env.py"), Path("migrations/versions")),
        entrypoint_command=("alembic", "-c", "alembic.ini", "current", "--help"),
        history_commands=(("alembic", "-c", "alembic.ini", "history", "--help"), ("alembic", "-c", "alembic.ini", "heads", "--help")),
    ),
    ServiceMigrationContract(
        name="layer2-extraction",
        service_dir=Path("services/layer2-extraction"),
        required_paths=(Path("alembic.ini"), Path("migrations/env.py"), Path("migrations/versions")),
        entrypoint_command=("alembic", "-c", "alembic.ini", "current", "--help"),
        history_commands=(("alembic", "-c", "alembic.ini", "history", "--help"), ("alembic", "-c", "alembic.ini", "heads", "--help")),
    ),
    ServiceMigrationContract(
        name="layer2-5-signal-refinery",
        service_dir=Path("services/layer2-5-signal-refinery"),
        required_paths=(
            Path("alembic.ini"),
            Path("src/layer2_5_signal_refinery/migrations/env.py"),
            Path("src/layer2_5_signal_refinery/migrations/versions"),
        ),
        entrypoint_command=("alembic", "-c", "alembic.ini", "current", "--help"),
        history_commands=(("alembic", "-c", "alembic.ini", "history", "--help"), ("alembic", "-c", "alembic.ini", "heads", "--help")),
    ),
    ServiceMigrationContract(
        name="layer3-knowledge",
        service_dir=Path("services/layer3-knowledge"),
        required_paths=(Path("src/migrations"),),
        entrypoint_command=("python", "-m", "pip", "--version"),
        history_commands=(("python", "-c", "from pathlib import Path; p=Path('src/migrations'); files=sorted(x.name for x in p.iterdir() if x.is_file()); print(len(files))"),),
    ),
    ServiceMigrationContract(
        name="layer4-agents",
        service_dir=Path("services/layer4-agents"),
        required_paths=(Path("alembic.ini"), Path("migrations/env.py"), Path("migrations/versions")),
        entrypoint_command=("alembic", "-c", "alembic.ini", "current", "--help"),
        history_commands=(("alembic", "-c", "alembic.ini", "history", "--help"), ("alembic", "-c", "alembic.ini", "heads", "--help")),
    ),
    ServiceMigrationContract(
        name="layer5-ground-truth",
        service_dir=Path("services/layer5-ground-truth"),
        required_paths=(
            Path("alembic.ini"),
            Path("src/layer5_ground_truth/migrations/env.py"),
            Path("src/layer5_ground_truth/migrations/versions"),
        ),
        entrypoint_command=("alembic", "-c", "alembic.ini", "current", "--help"),
        history_commands=(("alembic", "-c", "alembic.ini", "history", "--help"), ("alembic", "-c", "alembic.ini", "heads", "--help")),
    ),
    ServiceMigrationContract(
        name="api",
        service_dir=Path("services/api/migrations"),
        required_paths=(Path("alembic.ini"), Path("env.py"), Path("versions")),
        entrypoint_command=("alembic", "-c", "alembic.ini", "current", "--help"),
        history_commands=(("alembic", "-c", "alembic.ini", "history", "--help"), ("alembic", "-c", "alembic.ini", "heads", "--help")),
    ),
    ServiceMigrationContract(
        name="layer6-benchmarks",
        service_dir=Path("services/layer6-benchmarks"),
        required_paths=(Path("migrations/versions"),),
        entrypoint_command=("python", "-m", "pip", "--version"),
        history_commands=(("python", "-c", "from pathlib import Path; p=Path('migrations/versions'); files=sorted(x.name for x in p.iterdir() if x.is_file()); print(len(files))"),),
    ),
)


def _check_commands_available() -> list[str]:
    missing: list[str] = []
    for executable in ("python", "alembic"):
        if shutil.which(executable) is None:
            missing.append(executable)
    return missing


def _run_command(cmd: tuple[str, ...], cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, text=True, capture_output=True, check=False)


def _find_versions_dir(service_dir: Path) -> Path | None:
    candidates = [
        service_dir / "migrations" / "versions",
        service_dir / "src" / "layer2_5_signal_refinery" / "migrations" / "versions",
        service_dir / "src" / "layer5_ground_truth" / "migrations" / "versions",
        service_dir / "versions",
    ]
    for c in candidates:
        if c.exists():
            return c
    return None


def _check_alembic_graph(service_dir: Path) -> list[str]:
    """Statically inspect migration files for graph integrity (no DB required)."""
    errors: list[str] = []
    versions_dir = _find_versions_dir(service_dir)
    if not versions_dir:
        return errors

    revisions: dict[str, dict] = {}
    seen_files: dict[str, list[str]] = {}
    for f in sorted(versions_dir.glob("*.py")):
        if f.name.startswith(("__", ".")):
            continue
        source = f.read_text(encoding="utf-8", errors="ignore")
        rev: str | None = None
        down_rev: str | None = None
        for line in source.splitlines():
            line = line.strip()
            if line.startswith("revision") and ("=" in line or ":" in line):
                try:
                    rev = line.split("=")[-1].split(":")[-1].strip().strip('"').strip("'")
                except Exception:
                    pass
            if line.startswith("down_revision") and ("=" in line or ":" in line):
                try:
                    val = line.split("=", 1)[-1].strip()
                    if val.startswith("(") and val.endswith(")"):
                        # Tuple of down revisions (merge migration)
                        down_rev = tuple(
                            v.strip().strip('"').strip("'")
                            for v in val[1:-1].split(",")
                            if v.strip()
                        )
                    else:
                        down_rev = val.strip('"').strip("'")
                        down_rev = down_rev if down_rev and down_rev != "None" else None
                except Exception:
                    pass
        if rev:
            revisions[rev] = {"file": f.name, "down_revision": down_rev}
            seen_files.setdefault(rev, []).append(f.name)

    if not revisions:
        return errors

    # Detect duplicate revision IDs
    for rev, files in seen_files.items():
        if len(files) > 1:
            errors.append(f"duplicate revision ID '{rev}' in files: {files}")

    # Build reverse map: parent -> children
    children: dict[str, list[str]] = {}
    for rev, info in revisions.items():
        down = info["down_revision"]
        if down:
            if isinstance(down, tuple):
                for d in down:
                    children.setdefault(d, []).append(rev)
            else:
                children.setdefault(down, []).append(rev)

    heads = [rev for rev in revisions if rev not in children]
    if len(heads) > 1:
        errors.append(f"multi-head detected ({len(heads)} heads: {heads})")

    return errors


def main() -> int:
    missing_bins = _check_commands_available()
    if missing_bins:
        print(f"[!] Missing executables in PATH: {', '.join(missing_bins)} -- command-based checks will be skipped")

    has_alembic = "alembic" not in missing_bins
    errors: list[str] = []

    for contract in CONTRACTS:
        service_root = REPO_ROOT / contract.service_dir
        if not service_root.exists():
            errors.append(f"{contract.name}: service directory missing: {contract.service_dir}")
            continue

        for rel_path in contract.required_paths:
            candidate = service_root / rel_path
            if not candidate.exists():
                errors.append(f"{contract.name}: required migration path missing: {contract.service_dir / rel_path}")

        needs_alembic = any("alembic" in part for part in contract.entrypoint_command)
        if has_alembic or not needs_alembic:
            entrypoint_result = _run_command(contract.entrypoint_command, service_root)
            if entrypoint_result.returncode != 0:
                errors.append(
                    f"{contract.name}: entrypoint command failed: {' '.join(contract.entrypoint_command)}\n"
                    f"stdout: {entrypoint_result.stdout.strip()}\n"
                    f"stderr: {entrypoint_result.stderr.strip()}"
                )

            for history_command in contract.history_commands:
                history_result = _run_command(history_command, service_root)
                if history_result.returncode != 0:
                    errors.append(
                        f"{contract.name}: history command failed: {' '.join(history_command)}\n"
                        f"stdout: {history_result.stdout.strip()}\n"
                        f"stderr: {history_result.stderr.strip()}"
                    )
                elif not history_result.stdout.strip():
                    errors.append(f"{contract.name}: history command returned no migration revisions: {' '.join(history_command)}")

        # Static graph integrity check (no DB required)
        graph_errors = _check_alembic_graph(service_root)
        for err in graph_errors:
            errors.append(f"{contract.name}: {err}")

    if errors:
        print("[FAIL] Migration entrypoint contract failed:\n")
        for err in errors:
            print(f"- {err}")
        return 1

    print("[PASS] Migration entrypoint contract passed for all maintained layer services.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
