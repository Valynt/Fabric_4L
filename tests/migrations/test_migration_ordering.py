from __future__ import annotations

from pathlib import Path

from scripts.ci import check_migration_entrypoints as entrypoints
from scripts.ci import migration_status_report as status_report

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_alembic_revision_graphs_are_ordered_and_single_headed() -> None:
    failures: list[str] = []

    for service in status_report.ALEMBIC_SERVICES:
        versions_dir = REPO_ROOT / service.service_dir / service.versions_dir
        revisions, errors = status_report.extract_revision_graph(versions_dir)
        heads = status_report.graph_heads(revisions)

        if not revisions:
            failures.append(f"{service.name}: no migration revisions found")
        if errors:
            failures.append(f"{service.name}: graph errors: {errors}")
        if len(heads) != 1:
            failures.append(f"{service.name}: expected one head, found {heads}")

    assert not failures, "Migration ordering failures: " + "; ".join(failures)


def test_file_managed_migrations_have_deterministic_numeric_order() -> None:
    failures: list[str] = []

    for service in status_report.FILE_MANAGED_SERVICES:
        versions_dir = REPO_ROOT / service.service_dir / service.versions_dir
        files = sorted(
            path.name
            for path in versions_dir.iterdir()
            if path.is_file() and path.suffix in {".py", ".cypher"} and path.name[:3].isdigit()
        )
        prefixes = [name[:3] for name in files]

        if not files:
            failures.append(f"{service.name}: no numeric file-managed migrations found")
        if prefixes != sorted(prefixes):
            failures.append(f"{service.name}: migration files are not lexically ordered: {files}")
        if len(prefixes) != len(set(prefixes)):
            failures.append(f"{service.name}: duplicate numeric migration prefixes: {files}")

    assert not failures, "File-managed migration ordering failures: " + "; ".join(failures)


def test_migration_entrypoint_contract_covers_status_report_services() -> None:
    entrypoint_services = {contract.name for contract in entrypoints.CONTRACTS}
    status_services = {
        service.name
        for service in (*status_report.ALEMBIC_SERVICES, *status_report.FILE_MANAGED_SERVICES)
    }

    assert entrypoint_services == status_services

