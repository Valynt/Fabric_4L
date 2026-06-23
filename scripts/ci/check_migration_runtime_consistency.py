#!/usr/bin/env python3
"""Static consistency checks between Alembic migrations and runtime DB config.

This check intentionally does not connect to a database. Migration graph
integrity remains covered by ``check-migration-heads`` and
``check-migration-entrypoints``; this script verifies that checked-in runtime
configuration exposes PostgreSQL DSNs for the services that own runtime DBs.
Live upgrade/downgrade validation remains in ``check_migration_drift``.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_EXAMPLE = ROOT / ".env.example"


@dataclass(frozen=True)
class ServiceRuntimeContract:
    name: str
    versions_dir: Path
    env_vars: tuple[str, ...]


SERVICE_CONTRACTS: tuple[ServiceRuntimeContract, ...] = (
    ServiceRuntimeContract(
        "layer1-ingestion",
        Path("services/layer1-ingestion/migrations/versions"),
        ("LAYER1_DATABASE_URL", "LAYER1_DATABASE_URL_SYNC"),
    ),
    ServiceRuntimeContract(
        "layer2-extraction",
        Path("services/layer2-extraction/migrations/versions"),
        ("LAYER2_DATABASE_URL", "LAYER2_DATABASE_URL_SYNC"),
    ),
    ServiceRuntimeContract(
        "layer2-5-signal-refinery",
        Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
        ("LAYER2_5_DATABASE_URL",),
    ),
    ServiceRuntimeContract(
        "layer4-agents",
        Path("services/layer4-agents/migrations/versions"),
        ("LAYER4_DATABASE_URL", "LAYER4_DATABASE_URL_SYNC", "CHECKPOINT_DATABASE_URL"),
    ),
    ServiceRuntimeContract(
        "layer5-ground-truth",
        Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
        ("LAYER5_DATABASE_URL", "LAYER5_DATABASE_URL_SYNC"),
    ),
    ServiceRuntimeContract(
        "layer6-benchmarks",
        Path("services/layer6-benchmarks/migrations/versions"),
        ("LAYER6_DATABASE_URL", "LAYER6_DATABASE_URL_SYNC"),
    ),
    ServiceRuntimeContract(
        "api",
        Path("services/api/migrations/versions"),
        (),
    ),
)


def _literal_assignment(tree: ast.Module, name: str) -> object | None:
    for node in tree.body:
        value: ast.expr | None = None
        matched = False
        if isinstance(node, ast.Assign):
            matched = any(isinstance(target, ast.Name) and target.id == name for target in node.targets)
            value = node.value
        elif isinstance(node, ast.AnnAssign):
            matched = isinstance(node.target, ast.Name) and node.target.id == name
            value = node.value
        if matched and value is not None:
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return None
    return None


def _migration_revisions(versions_dir: Path) -> tuple[set[str], set[str], list[str]]:
    revisions: set[str] = set()
    down_revisions: set[str] = set()
    errors: list[str] = []
    python_files = sorted(path for path in versions_dir.glob("*.py") if not path.name.startswith("__"))
    if not python_files:
        ordered_scripts = sorted(
            path for path in versions_dir.iterdir() if path.is_file() and not path.name.startswith(("__", "."))
        )
        for path in ordered_scripts:
            revisions.add(path.stem)
        down_revisions.update(path.stem for path in ordered_scripts[:-1])
        return revisions, down_revisions, errors

    for path in python_files:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        revision = _literal_assignment(tree, "revision")
        down_revision = _literal_assignment(tree, "down_revision")
        if not isinstance(revision, str) or not revision:
            errors.append(f"{path.relative_to(ROOT)}: missing literal revision")
            continue
        if revision in revisions:
            errors.append(f"{path.relative_to(ROOT)}: duplicate revision {revision}")
        revisions.add(revision)
        if isinstance(down_revision, str):
            down_revisions.add(down_revision)
        elif isinstance(down_revision, tuple):
            down_revisions.update(item for item in down_revision if isinstance(item, str))
        elif down_revision is not None:
            errors.append(f"{path.relative_to(ROOT)}: down_revision must be None, str, or tuple[str, ...]")
    return revisions, down_revisions, errors


def assert_single_head_per_service() -> list[str]:
    errors: list[str] = []
    for contract in SERVICE_CONTRACTS:
        versions_dir = ROOT / contract.versions_dir
        if not versions_dir.exists():
            errors.append(f"{contract.name}: missing versions directory {contract.versions_dir}")
            continue
        revisions, down_revisions, graph_errors = _migration_revisions(versions_dir)
        errors.extend(f"{contract.name}: {error}" for error in graph_errors)
        if not revisions:
            errors.append(f"{contract.name}: no migration revisions found in {contract.versions_dir}")
            continue
        missing_down_revisions = sorted(down_revisions - revisions)
        if missing_down_revisions:
            errors.append(
                f"{contract.name}: down_revision(s) not present in revision set: {', '.join(missing_down_revisions)}"
            )
        heads = revisions - down_revisions
        if len(heads) != 1:
            errors.append(f"{contract.name}: expected exactly one migration head, found {len(heads)} ({sorted(heads)})")
    return errors


def parse_env_example() -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def assert_runtime_urls() -> list[str]:
    env = parse_env_example()
    errors: list[str] = []
    for contract in SERVICE_CONTRACTS:
        if not contract.env_vars:
            continue
        present = [var for var in contract.env_vars if env.get(var)]
        if not present:
            errors.append(f"{contract.name}: missing DB env vars in .env.example ({', '.join(contract.env_vars)})")
            continue
        for var in present:
            value = env[var]
            if not (value.startswith("postgresql://") or value.startswith("postgresql+") or value.startswith("postgres://")):
                errors.append(f"{contract.name}: env var {var} must be a PostgreSQL DSN, got {value!r}")
    return errors


def main() -> int:
    errors = assert_runtime_urls()
    if errors:
        print("Migration/runtime consistency violations:")
        for err in errors:
            print(f" - {err}")
        return 1
    print("Migration/runtime consistency checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
