#!/usr/bin/env python3
"""Report read-only database migration status and drift artifacts.

This command intentionally performs only metadata reads against the target
PostgreSQL databases. It never runs Alembic upgrade/downgrade commands and never
writes to the inspected database state.
"""

from __future__ import annotations

import argparse
import ast
import dataclasses
import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACT_DIR = REPO_ROOT / "artifacts" / "database"
ROLLBACK_RUNBOOK = REPO_ROOT / "docs" / "operations" / "runbooks" / "database-migration-rollback.md"


@dataclasses.dataclass(frozen=True)
class ServiceConfig:
    name: str
    versions_dir: Path
    database_env: tuple[str, ...]
    default_url: str
    version_table: str = "alembic_version"
    notes: str = ""


SERVICES: tuple[ServiceConfig, ...] = (
    ServiceConfig(
        "layer1-ingestion",
        Path("services/layer1-ingestion/migrations/versions"),
        ("LAYER1_DATABASE_URL_SYNC", "LAYER1_DATABASE_URL", "DATABASE_URL"),
        "postgresql://postgres:postgres@localhost:5432/ingestion",
    ),
    ServiceConfig(
        "layer2-extraction",
        Path("services/layer2-extraction/migrations/versions"),
        ("LAYER2_DATABASE_URL_SYNC", "LAYER2_DATABASE_URL", "DATABASE_URL"),
        "postgresql://postgres:postgres@localhost:5432/extraction",
    ),
    ServiceConfig(
        "layer2-5-signal-refinery",
        Path("services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/migrations/versions"),
        ("LAYER2_5_DATABASE_URL_SYNC", "LAYER2_5_DATABASE_URL", "DATABASE_URL"),
        "postgresql://postgres:postgres@localhost:5432/signal_refinery",
    ),
    ServiceConfig(
        "layer4-agents",
        Path("services/layer4-agents/migrations/versions"),
        ("LAYER4_DATABASE_URL_SYNC", "LAYER4_DATABASE_URL", "CHECKPOINT_DATABASE_URL"),
        "postgresql://postgres:postgres@localhost:5432/layer4_agents",
    ),
    ServiceConfig(
        "layer5-ground-truth",
        Path("services/layer5-ground-truth/src/layer5_ground_truth/migrations/versions"),
        ("LAYER5_DATABASE_URL_SYNC", "LAYER5_DATABASE_URL", "DATABASE_URL_SYNC"),
        "postgresql://postgres:postgres@localhost:5432/ground_truth",
    ),
    ServiceConfig(
        "api",
        Path("services/api/migrations/versions"),
        ("API_DATABASE_URL_SYNC", "API_DATABASE_URL", "DATABASE_URL_SYNC", "DATABASE_URL"),
        "postgresql://postgres:postgres@localhost:5432/valuefabric",
    ),
)


@dataclasses.dataclass(frozen=True)
class Revision:
    revision: str
    down_revisions: tuple[str, ...]
    path: str
    has_downgrade: bool
    unsupported_downgrade: bool
    has_tenant_marker: bool
    has_rls_marker: bool


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


def _extract_down_revisions(value: object | None) -> tuple[str, ...]:
    if isinstance(value, str) and value:
        return (value,)
    if isinstance(value, tuple):
        return tuple(item for item in value if isinstance(item, str) and item)
    return ()


def _has_downgrade(tree: ast.Module) -> bool:
    return any(isinstance(node, ast.FunctionDef) and node.name == "downgrade" for node in tree.body)


def _unsupported_downgrade(source: str) -> bool:
    lowered = source.lower()
    return any(
        marker in lowered
        for marker in (
            "downgrade_unsupported",
            "unsupported_downgrade",
            "notimplementederror",
            "restore from backup",
            "explicit production approval",
        )
    )


def _parse_revisions(service: ServiceConfig) -> tuple[dict[str, Revision], list[str]]:
    errors: list[str] = []
    revisions: dict[str, Revision] = {}
    versions_dir = REPO_ROOT / service.versions_dir
    if not versions_dir.exists():
        return revisions, [f"missing versions directory: {service.versions_dir}"]

    for path in sorted(p for p in versions_dir.glob("*.py") if not p.name.startswith("__")):
        rel = path.relative_to(REPO_ROOT).as_posix()
        source = path.read_text(encoding="utf-8", errors="ignore")
        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            errors.append(f"{rel}: cannot parse Python migration: {exc}")
            continue
        revision_value = _literal_assignment(tree, "revision")
        if not isinstance(revision_value, str) or not revision_value:
            errors.append(f"{rel}: missing literal revision")
            continue
        if revision_value in revisions:
            errors.append(f"{rel}: duplicate revision {revision_value}")
        lowered = source.lower()
        revisions[revision_value] = Revision(
            revision=revision_value,
            down_revisions=_extract_down_revisions(_literal_assignment(tree, "down_revision")),
            path=rel,
            has_downgrade=_has_downgrade(tree),
            unsupported_downgrade=_unsupported_downgrade(source),
            has_tenant_marker="tenant_id" in lowered or "tenant id" in lowered,
            has_rls_marker="row level security" in lowered or "enable row level security" in lowered or "create policy" in lowered or "rls" in lowered,
        )

    if not revisions:
        errors.append(f"no Python Alembic migrations found in {service.versions_dir}")
    return revisions, errors


def _ordered_history(revisions: dict[str, Revision]) -> list[str]:
    if not revisions:
        return []
    children: dict[str | None, list[str]] = {}
    for rev in revisions.values():
        parent = rev.down_revisions[0] if len(rev.down_revisions) == 1 else None
        children.setdefault(parent, []).append(rev.revision)
    ordered: list[str] = []
    current: str | None = None
    visited: set[str] = set()
    while children.get(current):
        nxt = sorted(children[current])[0]
        if nxt in visited:
            break
        ordered.append(nxt)
        visited.add(nxt)
        current = nxt
    ordered.extend(sorted(set(revisions) - visited))
    return ordered


def _heads(revisions: dict[str, Revision]) -> list[str]:
    down = {parent for rev in revisions.values() for parent in rev.down_revisions}
    return sorted(set(revisions) - down)


def _lineage_to(revisions: dict[str, Revision], revision: str) -> list[str]:
    if revision not in revisions:
        return []
    lineage = [revision]
    current = revisions[revision]
    while len(current.down_revisions) == 1 and current.down_revisions[0] in revisions:
        parent = current.down_revisions[0]
        lineage.append(parent)
        current = revisions[parent]
    return list(reversed(lineage))


def _pending_from_current(revisions: dict[str, Revision], current: list[str], heads: list[str]) -> list[str]:
    if not revisions:
        return []
    ordered = _ordered_history(revisions)
    if not current:
        return ordered
    current_set = set(current)
    if any(rev not in revisions for rev in current_set):
        return []
    applied = {rev for cur in current_set for rev in _lineage_to(revisions, cur)}
    return [rev for rev in ordered if rev not in applied]


def _selected_url(service: ServiceConfig) -> tuple[str, str]:
    for env_name in service.database_env:
        value = os.environ.get(env_name)
        if value:
            return env_name, value
    return "default-local-compose", service.default_url


def _sync_postgres_url(raw_url: str) -> str:
    try:
        from sqlalchemy.engine import make_url
    except Exception:
        return raw_url.replace("postgresql+asyncpg://", "postgresql://").replace("postgresql+psycopg://", "postgresql://")
    url = make_url(raw_url)
    if url.drivername.startswith("postgresql+") or url.drivername == "postgresql":
        return str(url.set(drivername="postgresql"))
    if url.drivername == "postgres":
        return str(url.set(drivername="postgresql"))
    return raw_url


def _read_current_versions(service: ServiceConfig, url: str) -> tuple[list[str], dict[str, Any]]:
    diagnostics: dict[str, Any] = {"connected": False, "error": None, "version_table_exists": False}
    try:
        from sqlalchemy import create_engine, text
    except Exception as exc:  # pragma: no cover - environment dependent
        diagnostics["error"] = f"sqlalchemy unavailable: {exc}"
        return [], diagnostics

    engine = None
    try:
        engine = create_engine(_sync_postgres_url(url), pool_pre_ping=True, connect_args={"connect_timeout": 2})
        with engine.connect() as conn:
            diagnostics["connected"] = True
            table_exists = conn.execute(
                text(
                    "select exists ("
                    "select 1 from information_schema.tables "
                    "where table_schema = 'public' and table_name = :table_name)"
                ),
                {"table_name": service.version_table},
            ).scalar()
            diagnostics["version_table_exists"] = bool(table_exists)
            if not table_exists:
                return [], diagnostics
            rows = conn.execute(text(f"select version_num from public.{service.version_table} order by version_num")).fetchall()
            return [str(row[0]) for row in rows], diagnostics
    except Exception as exc:  # pragma: no cover - environment dependent
        diagnostics["error"] = str(exc)
        return [], diagnostics
    finally:
        if engine is not None:
            engine.dispose()


def _rollback_status(revisions: dict[str, Revision]) -> dict[str, Any]:
    runbook = ROLLBACK_RUNBOOK.read_text(encoding="utf-8", errors="ignore") if ROLLBACK_RUNBOOK.exists() else ""
    missing = []
    unsupported_documented = []
    for rev in revisions.values():
        if not rev.has_downgrade:
            missing.append(f"{rev.revision} ({rev.path}) lacks downgrade()")
        if rev.unsupported_downgrade:
            documented = rev.path in runbook
            unsupported_documented.append({"revision": rev.revision, "path": rev.path, "documented": documented})
            if not documented:
                missing.append(f"{rev.revision} ({rev.path}) has unsupported downgrade not listed in rollback runbook")
    return {
        "exists": not missing,
        "missing": missing,
        "unsupported_downgrades": unsupported_documented,
        "runbook": ROLLBACK_RUNBOOK.relative_to(REPO_ROOT).as_posix(),
    }


def _tenant_rls_status(revisions: dict[str, Revision]) -> dict[str, Any]:
    tenant_files = [rev.path for rev in revisions.values() if rev.has_tenant_marker]
    rls_files = [rev.path for rev in revisions.values() if rev.has_rls_marker]
    return {
        "tenant_migration_markers": len(tenant_files),
        "rls_migration_markers": len(rls_files),
        "status": "present" if tenant_files and rls_files else "missing_markers",
        "tenant_files": tenant_files,
        "rls_files": rls_files,
    }


def inspect_service(service: ServiceConfig) -> dict[str, Any]:
    revisions, parse_errors = _parse_revisions(service)
    heads = _heads(revisions)
    env_name, url = _selected_url(service)
    current, db = _read_current_versions(service, url)
    pending = _pending_from_current(revisions, current, heads) if db.get("connected") else []

    drift: list[str] = []
    if parse_errors:
        drift.extend(parse_errors)
    if len(heads) != 1:
        drift.append(f"expected exactly one migration head, found {len(heads)}: {heads}")
    if db.get("connected"):
        unknown = sorted(set(current) - set(revisions))
        if unknown:
            drift.append(f"database has revision(s) absent from migration files: {unknown}")
        if db.get("version_table_exists") and current and set(current) != set(heads):
            drift.append(f"database current revision(s) {current} do not match file head(s) {heads}")
        if not db.get("version_table_exists"):
            drift.append(f"database is missing {service.version_table}; all migrations appear pending")
    else:
        drift.append(f"database status unavailable: {db.get('error') or 'not connected'}")

    return {
        "service": service.name,
        "versions_dir": service.versions_dir.as_posix(),
        "database_url_source": env_name,
        "database": db,
        "current_database_revisions": current,
        "current_migration_heads": heads,
        "pending_migrations": pending,
        "applied_history": {rev: revisions[rev].path for rev in _lineage_to(revisions, current[0])} if len(current) == 1 else {},
        "migration_file_history": [{"revision": rev, "path": revisions[rev].path} for rev in _ordered_history(revisions)],
        "drift": drift,
        "rollback_metadata": _rollback_status(revisions),
        "tenant_rls_validation": _tenant_rls_status(revisions),
        "notes": service.notes,
    }


def render_markdown(report: dict[str, Any]) -> str:
    lines = [
        "# Database Migration Status",
        "",
        f"Generated: `{report['generated_at']}`",
        f"Mode: `{report['mode']}`",
        "",
        "| Service | DB Connected | DB Current | File Head | Pending | Drift | Rollback Metadata | Tenant/RLS |",
        "|---|---:|---|---|---:|---:|---:|---|",
    ]
    for service in report["services"]:
        lines.append(
            "| {service} | {connected} | {current} | {heads} | {pending} | {drift} | {rollback} | {tenant} |".format(
                service=service["service"],
                connected="yes" if service["database"].get("connected") else "no",
                current=", ".join(service["current_database_revisions"]) or "not applied",
                heads=", ".join(service["current_migration_heads"]) or "none",
                pending=(len(service["pending_migrations"]) if service["database"].get("connected") else "unknown"),
                drift=len(service["drift"]),
                rollback="yes" if service["rollback_metadata"]["exists"] else "no",
                tenant=service["tenant_rls_validation"]["status"],
            )
        )
    lines.extend(["", "## Service Details", ""])
    for service in report["services"]:
        lines.extend(
            [
                f"### {service['service']}",
                "",
                f"- Versions directory: `{service['versions_dir']}`",
                f"- Database URL source: `{service['database_url_source']}`",
                f"- Current migration head(s): `{', '.join(service['current_migration_heads']) or 'none'}`",
                f"- Current database revision(s): `{', '.join(service['current_database_revisions']) or 'not applied'}`",
                f"- Pending migrations: `{len(service['pending_migrations']) if service['database'].get('connected') else 'unknown'}`",
                f"- Rollback metadata exists: `{service['rollback_metadata']['exists']}`",
                f"- Tenant/RLS migration validation status: `{service['tenant_rls_validation']['status']}`",
                "",
            ]
        )
        if service["pending_migrations"]:
            lines.append("Pending revisions:")
            lines.extend(f"- `{rev}`" for rev in service["pending_migrations"])
            lines.append("")
        if service["applied_history"]:
            lines.append("Applied migration history inferred from Alembic revision graph:")
            lines.extend(f"- `{rev}` — `{path}`" for rev, path in service["applied_history"].items())
            lines.append("")
        else:
            lines.append("Applied migration history: not available beyond current revision table state.")
            lines.append("")
        if service["drift"]:
            lines.append("Drift findings:")
            lines.extend(f"- {finding}" for finding in service["drift"])
            lines.append("")
    return "\n".join(lines) + "\n"


def build_report(mode: str, selected: set[str] | None = None) -> dict[str, Any]:
    services = [svc for svc in SERVICES if selected is None or svc.name in selected]
    return {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "mode": mode,
        "read_only": True,
        "services": [inspect_service(service) for service in services],
    }


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("status", "check"), default="status")
    parser.add_argument("--service", action="append", help="Limit to a service name; may be repeated.")
    parser.add_argument("--artifact-dir", default=str(DEFAULT_ARTIFACT_DIR))
    parser.add_argument("--fail-on-unavailable-db", action="store_true", help="Treat database connection failures as check failures.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    selected = set(args.service) if args.service else None
    known = {service.name for service in SERVICES}
    unknown = (selected - known) if selected else set()
    if unknown:
        print(f"Unknown service(s): {', '.join(sorted(unknown))}", file=sys.stderr)
        return 2

    report = build_report(args.mode, selected)
    artifact_dir = Path(args.artifact_dir)
    artifact_dir.mkdir(parents=True, exist_ok=True)
    json_path = artifact_dir / "migration-status.json"
    md_path = artifact_dir / "migration-status.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md = render_markdown(report)
    md_path.write_text(md, encoding="utf-8")
    print(md)
    print(f"Artifacts written: {json_path.relative_to(REPO_ROOT)} {md_path.relative_to(REPO_ROOT)}")

    if args.mode == "check":
        failures: list[str] = []
        for service in report["services"]:
            drift = list(service["drift"])
            if not args.fail_on_unavailable_db:
                drift = [finding for finding in drift if not finding.startswith("database status unavailable:")]
            if drift:
                failures.extend(f"{service['service']}: {finding}" for finding in drift)
        if failures:
            print("Migration check failed:", file=sys.stderr)
            for failure in failures:
                print(f" - {failure}", file=sys.stderr)
            return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
