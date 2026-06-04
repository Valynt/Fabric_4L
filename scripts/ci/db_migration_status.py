#!/usr/bin/env python3
"""Read-only database migration status and drift gate.

Reports Alembic heads, pending revisions, inferred applied history, live
``alembic_version`` state, rollback metadata coverage, and static tenant/RLS
migration validation for every maintained SQL migration root.  The status mode
is intentionally read-only: it only inspects migration files and selects from
PostgreSQL metadata tables.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import os
import re
import sys
from collections import defaultdict, deque
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.exc import SQLAlchemyError

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "db-migrate"


@dataclasses.dataclass(frozen=True)
class MigrationService:
    name: str
    versions_dir: Path
    database_name: str
    url_envs: tuple[str, ...]
    default_url: str
    rollback_runbook_anchor: str | None = None


SERVICES: tuple[MigrationService, ...] = (
    MigrationService(
        name="layer1-ingestion",
        versions_dir=Path("services/layer1-ingestion/migrations/versions"),
        database_name="ingestion",
        url_envs=("LAYER1_DATABASE_URL", "DATABASE_URL"),
        default_url="postgresql+psycopg2://postgres:postgres@localhost:5432/ingestion",
    ),
    MigrationService(
        name="layer2-extraction",
        versions_dir=Path("services/layer2-extraction/migrations/versions"),
        database_name="extraction",
        url_envs=("LAYER2_DATABASE_URL", "DATABASE_URL"),
        default_url="postgresql+psycopg2://postgres:postgres@localhost:5432/extraction",
    ),
    MigrationService(
        name="layer2-5-signal-refinery",
        versions_dir=Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
        database_name="signal_refinery",
        url_envs=("SIGNAL_REFINERY_DATABASE_URL", "DATABASE_URL"),
        default_url="postgresql+psycopg2://postgres:postgres@localhost:5432/signal_refinery",
    ),
    MigrationService(
        name="layer4-agents",
        versions_dir=Path("services/layer4-agents/migrations/versions"),
        database_name="layer4_agents",
        url_envs=("LAYER4_DATABASE_URL", "CHECKPOINT_DATABASE_URL", "DATABASE_URL"),
        default_url="postgresql+psycopg2://postgres:postgres@localhost:5432/layer4_agents",
    ),
    MigrationService(
        name="layer5-ground-truth",
        versions_dir=Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
        database_name="ground_truth",
        url_envs=("DATABASE_URL_SYNC", "LAYER5_DATABASE_URL", "DATABASE_URL"),
        default_url="postgresql+psycopg2://postgres:postgres@localhost:5432/ground_truth",
    ),
    MigrationService(
        name="api",
        versions_dir=Path("services/api/migrations/versions"),
        database_name="valuefabric",
        url_envs=("API_DATABASE_URL", "DATABASE_URL"),
        default_url="postgresql+psycopg2://postgres:postgres@localhost:5432/valuefabric",
        rollback_runbook_anchor="api-gateway-sql-migrations",
    ),
)

ROLLBACK_RUNBOOK = REPO_ROOT / "docs/operations/runbooks/database-migration-rollback.md"
RLS_MARKERS = (
    "ENABLE ROW LEVEL SECURITY",
    "CREATE POLICY",
    "RLS_TABLES",
    "current_setting('app.tenant_id'",
    'current_setting("app.tenant_id"',
)
TENANT_MARKERS = ("tenant_id", "org_id")
ROLLBACK_MARKERS = ("def downgrade", "DOWNGRADE_UNSUPPORTED", "UNSUPPORTED_DOWNGRADE", "restore from backup")


class StatusError(RuntimeError):
    """Raised when status/check generation cannot proceed."""


def _literal_assignment(name: str, source: str, path: Path) -> Any:
    try:
        tree = ast.parse(source)
    except SyntaxError as exc:
        raise StatusError(f"{path.relative_to(REPO_ROOT)} has invalid Python syntax: {exc}") from exc
    for node in tree.body:
        target_name: str | None = None
        value: ast.expr | None = None
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    target_name = target.id
                    value = node.value
                    break
        elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == name:
            target_name = node.target.id
            value = node.value
        if target_name == name and value is not None:
            try:
                return ast.literal_eval(value)
            except (SyntaxError, ValueError) as exc:
                raise StatusError(
                    f"{path.relative_to(REPO_ROOT)} has an unparsable {name} assignment: {exc}"
                ) from exc
    raise StatusError(f"{path.relative_to(REPO_ROOT)} is missing {name!r} migration assignment")


def _as_revision_tuple(value: Any) -> tuple[str, ...]:
    if value is None:
        return ()
    if isinstance(value, str):
        return (value,)
    if isinstance(value, (tuple, list, set)):
        return tuple(str(item) for item in value if item is not None)
    raise StatusError(f"Unsupported down_revision value: {value!r}")


def _load_migrations(service: MigrationService) -> dict[str, dict[str, Any]]:
    root = REPO_ROOT / service.versions_dir
    if not root.exists():
        raise StatusError(f"{service.name}: migration versions directory is missing: {service.versions_dir}")

    revisions: dict[str, dict[str, Any]] = {}
    for path in sorted(root.glob("*.py")):
        if path.name.startswith("__"):
            continue
        source = path.read_text(encoding="utf-8")
        revision = str(_literal_assignment("revision", source, path))
        down_revisions = _as_revision_tuple(_literal_assignment("down_revision", source, path))
        relative = path.relative_to(REPO_ROOT).as_posix()
        if revision in revisions:
            raise StatusError(f"{service.name}: duplicate revision {revision!r} in {relative}")
        revisions[revision] = {
            "revision": revision,
            "down_revisions": list(down_revisions),
            "path": relative,
            "has_downgrade_function": "def downgrade" in source,
            "has_rollback_metadata": any(marker in source for marker in ROLLBACK_MARKERS),
            "mentions_tenant": any(marker in source for marker in TENANT_MARKERS),
            "mentions_rls": any(marker in source for marker in RLS_MARKERS),
        }
    return revisions


def _heads(revisions: dict[str, dict[str, Any]]) -> list[str]:
    parents = {parent for info in revisions.values() for parent in info["down_revisions"] if parent}
    return sorted(rev for rev in revisions if rev not in parents)


def _ancestors(revisions: dict[str, dict[str, Any]], starting_revisions: set[str]) -> set[str]:
    known: set[str] = set()
    queue: deque[str] = deque(starting_revisions)
    while queue:
        revision = queue.popleft()
        if revision in known or revision not in revisions:
            continue
        known.add(revision)
        queue.extend(revisions[revision]["down_revisions"])
    return known


def _descendants(revisions: dict[str, dict[str, Any]], starting_revisions: set[str]) -> set[str]:
    children: dict[str, list[str]] = defaultdict(list)
    for rev, info in revisions.items():
        for parent in info["down_revisions"]:
            children[parent].append(rev)
    seen: set[str] = set()
    queue: deque[str] = deque(starting_revisions)
    while queue:
        revision = queue.popleft()
        for child in children.get(revision, []):
            if child not in seen:
                seen.add(child)
                queue.append(child)
    return seen


def _normalize_postgres_url(raw_url: str) -> str:
    url = make_url(raw_url)
    if not url.drivername.startswith("postgresql"):
        raise StatusError(f"Only PostgreSQL migration status is supported, got {url.drivername!r}")
    return str(url.set(drivername="postgresql+psycopg2"))


def _url_for_service(service: MigrationService, global_url: str | None) -> tuple[str, str]:
    if global_url:
        url = make_url(_normalize_postgres_url(global_url)).set(database=service.database_name)
        return str(url), "--database-url"
    for key in service.url_envs:
        value = os.environ.get(key)
        if value:
            return _normalize_postgres_url(value), key
    return service.default_url, "local-docker-compose-default"


def _current_revisions(service: MigrationService, url: str) -> tuple[list[str], str]:
    engine = create_engine(_normalize_postgres_url(url), isolation_level="AUTOCOMMIT")
    try:
        with engine.connect() as conn:
            exists = conn.execute(
                text("SELECT to_regclass('public.alembic_version') IS NOT NULL")
            ).scalar()
            if not exists:
                return [], "missing alembic_version table"
            rows = conn.execute(text("SELECT version_num FROM public.alembic_version ORDER BY version_num")).fetchall()
            return [str(row[0]) for row in rows], "ok"
    finally:
        engine.dispose()


def _migration_graph_status(service: MigrationService, revisions: dict[str, dict[str, Any]], current: list[str]) -> dict[str, Any]:
    heads = _heads(revisions)
    current_set = set(current)
    known_current = current_set & set(revisions)
    unknown_current = sorted(current_set - set(revisions))
    applied = sorted(_ancestors(revisions, known_current)) if known_current else []
    if not current:
        pending = sorted(revisions)
    else:
        pending = sorted(_descendants(revisions, known_current))
    at_head = bool(current) and sorted(current) == heads
    missing_heads = sorted(set(heads) - current_set)
    drift = bool(unknown_current or missing_heads or (current and not at_head))
    rollback_missing = sorted(info["path"] for info in revisions.values() if not info["has_downgrade_function"])
    rollback_metadata_exists = not rollback_missing
    tenant_migrations = [info for info in revisions.values() if info["mentions_tenant"]]
    rls_migrations = [info for info in revisions.values() if info["mentions_rls"]]
    tenant_rls_status = "pass" if rls_migrations else "warn"
    tenant_rls_notes = [] if rls_migrations else ["No migration file with RLS markers was found for this service."]
    return {
        "service": service.name,
        "migration_files": len(revisions),
        "current_heads": sorted(current),
        "repository_heads": heads,
        "pending_migrations": pending,
        "applied_history": applied,
        "unknown_database_revisions": unknown_current,
        "missing_repository_heads": missing_heads,
        "drift": drift,
        "rollback_metadata_exists": rollback_metadata_exists,
        "rollback_metadata_missing": rollback_missing,
        "tenant_rls_validation": {
            "status": tenant_rls_status,
            "tenant_migration_count": len(tenant_migrations),
            "rls_migration_count": len(rls_migrations),
            "notes": tenant_rls_notes,
        },
    }


def _service_status(service: MigrationService, global_url: str | None) -> dict[str, Any]:
    revisions = _load_migrations(service)
    url, source = _url_for_service(service, global_url)
    status: dict[str, Any] = {
        "service": service.name,
        "versions_dir": service.versions_dir.as_posix(),
        "database": service.database_name,
        "database_url_source": source,
        "database_connection": "ok",
        "database_notes": [],
    }
    try:
        current, db_note = _current_revisions(service, url)
        if db_note != "ok":
            status["database_notes"].append(db_note)
        status.update(_migration_graph_status(service, revisions, current))
    except SQLAlchemyError as exc:
        status.update(_migration_graph_status(service, revisions, []))
        status["database_connection"] = "error"
        status["database_notes"].append(str(exc.__cause__ or exc))
        status["drift"] = True
    return status


def _summary(services: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "service_count": len(services),
        "drift_count": sum(1 for service in services if service["drift"]),
        "pending_count": sum(len(service["pending_migrations"]) for service in services),
        "database_error_count": sum(1 for service in services if service["database_connection"] != "ok"),
        "rollback_metadata_missing_count": sum(len(service["rollback_metadata_missing"]) for service in services),
        "tenant_rls_warning_count": sum(
            1 for service in services if service["tenant_rls_validation"]["status"] != "pass"
        ),
    }


def _markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Database Migration Status",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Mode: `{report['mode']}`",
        "",
        "## Summary",
        "",
        f"- Services checked: **{report['summary']['service_count']}**",
        f"- Services with drift: **{report['summary']['drift_count']}**",
        f"- Pending migrations: **{report['summary']['pending_count']}**",
        f"- Database connection errors: **{report['summary']['database_error_count']}**",
        f"- Rollback metadata gaps: **{report['summary']['rollback_metadata_missing_count']}**",
        f"- Tenant/RLS validation warnings: **{report['summary']['tenant_rls_warning_count']}**",
        "",
        "## Service Details",
        "",
    ]
    for service in report["services"]:
        lines.extend(
            [
                f"### {service['service']}",
                "",
                f"- Versions directory: `{service['versions_dir']}`",
                f"- Database: `{service['database']}` (`{service['database_url_source']}`)",
                f"- Database connection: **{service['database_connection']}**",
                f"- Current migration head(s): `{', '.join(service['current_heads']) or 'none'}`",
                f"- Repository head(s): `{', '.join(service['repository_heads']) or 'none'}`",
                f"- Pending migrations: **{len(service['pending_migrations'])}**",
                f"- Applied migration history entries: **{len(service['applied_history'])}**",
                f"- Drift detected: **{'yes' if service['drift'] else 'no'}**",
                f"- Rollback metadata exists: **{'yes' if service['rollback_metadata_exists'] else 'no'}**",
                f"- Tenant/RLS migration validation: **{service['tenant_rls_validation']['status']}** "
                f"({service['tenant_rls_validation']['tenant_migration_count']} tenant migrations, "
                f"{service['tenant_rls_validation']['rls_migration_count']} RLS migrations)",
            ]
        )
        if service["database_notes"]:
            lines.append("- Database notes:")
            lines.extend(f"  - {note}" for note in service["database_notes"])
        if service["unknown_database_revisions"]:
            lines.append("- Unknown database revisions:")
            lines.extend(f"  - `{revision}`" for revision in service["unknown_database_revisions"])
        if service["missing_repository_heads"]:
            lines.append("- Missing repository heads:")
            lines.extend(f"  - `{revision}`" for revision in service["missing_repository_heads"])
        if service["pending_migrations"]:
            lines.append("- Pending revision IDs:")
            lines.extend(f"  - `{revision}`" for revision in service["pending_migrations"][:50])
            if len(service["pending_migrations"]) > 50:
                lines.append(f"  - … {len(service['pending_migrations']) - 50} additional pending revisions omitted")
        lines.append("")
    return "\n".join(lines).rstrip() + "\n"


def _write_artifacts(report: dict[str, Any], artifact_dir: Path) -> None:
    artifact_dir.mkdir(parents=True, exist_ok=True)
    (artifact_dir / "db-migrate-status.json").write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    (artifact_dir / "db-migrate-status.md").write_text(_markdown(report), encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("status", "check"), default="status")
    parser.add_argument(
        "--database-url",
        default=os.environ.get("DB_MIGRATION_STATUS_DATABASE_URL") or os.environ.get("DB_MIGRATION_DATABASE_URL"),
        help="Optional PostgreSQL URL. The database name is replaced per service for local Docker Compose databases.",
    )
    parser.add_argument("--service", action="append", help="Limit to a service name; may be repeated.")
    parser.add_argument("--artifact-dir", type=Path, default=DEFAULT_ARTIFACT_DIR)
    return parser.parse_args()


def _selected_services(names: list[str] | None) -> tuple[MigrationService, ...]:
    if not names:
        return SERVICES
    requested = set(names)
    unknown = requested - {service.name for service in SERVICES}
    if unknown:
        raise StatusError(f"Unknown service(s): {', '.join(sorted(unknown))}")
    return tuple(service for service in SERVICES if service.name in requested)


def main() -> int:
    args = parse_args()
    try:
        services = [_service_status(service, args.database_url) for service in _selected_services(args.service)]
    except StatusError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 2

    report = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": args.mode,
        "read_only": True,
        "services": services,
        "summary": _summary(services),
    }
    _write_artifacts(report, args.artifact_dir)
    print(_markdown(report), end="")
    print(f"Artifacts written to {args.artifact_dir.relative_to(REPO_ROOT) if args.artifact_dir.is_relative_to(REPO_ROOT) else args.artifact_dir}")

    if args.mode == "check" and report["summary"]["drift_count"]:
        print("ERROR: database migration drift detected", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
