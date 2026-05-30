#!/usr/bin/env python3
"""Static migration/runtime consistency checks for database readiness.

This check intentionally avoids opening live database connections. It validates
that committed migration metadata and runtime database URL declarations remain
aligned with the repository-owned readiness docs and local service layout.
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
    versions_dir: Path | None
    env_vars: tuple[str, ...]


SERVICE_CONTRACTS = (
    ServiceRuntimeContract(
        "layer1-ingestion",
        Path("services/layer1-ingestion/migrations/versions"),
        ("LAYER1_DATABASE_URL", "DATABASE_URL"),
    ),
    ServiceRuntimeContract(
        "layer2-extraction",
        Path("services/layer2-extraction/migrations/versions"),
        ("LAYER2_DATABASE_URL", "DATABASE_URL"),
    ),
    ServiceRuntimeContract(
        "layer4-agents",
        Path("services/layer4-agents/migrations/versions"),
        ("LAYER4_DATABASE_URL", "LANGGRAPH_CHECKPOINT_DB_URL", "DATABASE_URL"),
    ),
    ServiceRuntimeContract(
        "layer5-ground-truth",
        Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
        ("LAYER5_DATABASE_URL", "LAYER5_DATABASE_URL_SYNC", "DATABASE_URL", "DATABASE_URL_SYNC"),
    ),
    ServiceRuntimeContract(
        "layer6-benchmarks",
        Path("services/layer6-benchmarks/migrations/versions"),
        ("LAYER6_DATABASE_URL", "LAYER6_DATABASE_URL_SYNC", "DATABASE_URL", "DATABASE_URL_SYNC"),
    ),
)


def _literal_assignment(module: ast.Module, name: str) -> object | None:
    for node in module.body:
        target_names: list[str] = []
        value: ast.AST | None = None
        if isinstance(node, ast.Assign):
            target_names = [target.id for target in node.targets if isinstance(target, ast.Name)]
            value = node.value
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_names = [node.target.id]
            value = node.value
        if name in target_names and value is not None:
            try:
                return ast.literal_eval(value)
            except (ValueError, SyntaxError):
                return None
    return None


def _parse_revision_file(path: Path) -> tuple[str | None, tuple[str, ...]]:
    module = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    revision = _literal_assignment(module, "revision")
    down_revision = _literal_assignment(module, "down_revision")

    revision_id = revision if isinstance(revision, str) else None
    parents: tuple[str, ...]
    if isinstance(down_revision, str):
        parents = (down_revision,)
    elif isinstance(down_revision, (tuple, list)):
        parents = tuple(parent for parent in down_revision if isinstance(parent, str))
    else:
        parents = ()
    return revision_id, parents


def assert_single_head_per_service() -> list[str]:
    errors: list[str] = []
    for contract in SERVICE_CONTRACTS:
        if contract.versions_dir is None:
            continue
        versions = ROOT / contract.versions_dir
        if not versions.exists():
            errors.append(f"{contract.name}: migration versions directory missing: {contract.versions_dir}")
            continue

        python_migrations = sorted(versions.glob("*.py"))
        cypher_migrations = sorted(versions.glob("*.cypher"))
        if cypher_migrations and not python_migrations:
            continue

        revisions: dict[str, str] = {}
        parent_revisions: set[str] = set()
        for pyf in python_migrations:
            if pyf.name.startswith(("__", ".")):
                continue
            revision, parents = _parse_revision_file(pyf)
            if revision is None:
                continue
            if revision in revisions:
                errors.append(
                    f"{contract.name}: duplicate revision {revision!r} in {revisions[revision]} and {pyf.name}"
                )
            revisions[revision] = pyf.name
            parent_revisions.update(parents)

        if not revisions:
            errors.append(f"{contract.name}: no revision identifiers found in {contract.versions_dir}")
            continue

        heads = sorted(revision for revision in revisions if revision not in parent_revisions)
        if len(heads) != 1:
            errors.append(f"{contract.name}: expected exactly one migration head, found {len(heads)}: {heads}")
    return errors


def parse_env_example() -> dict[str, str]:
    parsed: dict[str, str] = {}
    for line in ENV_EXAMPLE.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        parsed[key.strip()] = value.strip()
    return parsed


def assert_runtime_urls() -> list[str]:
    env = parse_env_example()
    errors: list[str] = []
    for contract in SERVICE_CONTRACTS:
        if not any(name in env and env[name] for name in contract.env_vars):
            errors.append(f"{contract.name}: missing expected DB env vars in .env.example ({contract.env_vars})")
            continue
        for var in contract.env_vars:
            if var in env and env[var] and "postgresql://" not in env[var] and "postgresql+" not in env[var]:
                errors.append(f"{contract.name}: env var {var} must be a PostgreSQL DSN")
    return errors


def main() -> int:
    errors = [*assert_single_head_per_service(), *assert_runtime_urls()]
    if errors:
        for err in errors:
            print(f"ERROR: {err}")
        return 1
    print("Migration/runtime consistency checks passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
