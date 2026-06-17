from __future__ import annotations

from pathlib import Path

import pytest


def _layer5_script_directory():
    alembic_config = pytest.importorskip("alembic.config")
    alembic_script = pytest.importorskip("alembic.script")
    service_root = Path(__file__).resolve().parents[1]
    migrations_dir = service_root / "src" / "layer5_ground_truth" / "migrations"
    alembic_cfg = alembic_config.Config(str(service_root / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(migrations_dir))
    return alembic_script.ScriptDirectory.from_config(alembic_cfg)


@pytest.mark.anyio
async def test_schema_alignment_reports_aligned_at_head(monkeypatch) -> None:
    from layer5_ground_truth.api import main as main_module

    script = _layer5_script_directory()
    head = script.get_current_head()

    async def _current_heads() -> tuple[str, ...]:
        return (head,)

    monkeypatch.setattr(main_module, "_get_database_migration_heads", _current_heads)

    assert await main_module._check_schema_migration_alignment() == {
        "ready": True,
        "schema": "aligned",
        "reason": "schema_aligned",
        "current_revisions": [head],
        "expected_heads": [head],
    }


@pytest.mark.anyio
async def test_schema_alignment_reports_behind_when_db_is_not_at_head(monkeypatch) -> None:
    from layer5_ground_truth.api import main as main_module

    script = _layer5_script_directory()
    head = script.get_current_head()
    ancestor = next(
        revision.revision
        for revision in script.walk_revisions(base="base", head=head)
        if revision.revision != head
    )

    async def _current_heads() -> tuple[str, ...]:
        return (ancestor,)

    monkeypatch.setattr(main_module, "_get_database_migration_heads", _current_heads)

    assert await main_module._check_schema_migration_alignment() == {
        "ready": False,
        "schema": "behind",
        "reason": "schema_revision_behind",
        "current_revisions": [ancestor],
        "expected_heads": [head],
    }


@pytest.mark.anyio
async def test_schema_alignment_reports_inconsistent_for_unknown_revision(monkeypatch) -> None:
    from layer5_ground_truth.api import main as main_module

    script = _layer5_script_directory()

    async def _current_heads() -> tuple[str, ...]:
        return ("not-a-real-revision",)

    monkeypatch.setattr(main_module, "_get_database_migration_heads", _current_heads)

    assert await main_module._check_schema_migration_alignment() == {
        "ready": False,
        "schema": "inconsistent",
        "reason": "schema_revision_inconsistent",
        "current_revisions": ["not-a-real-revision"],
        "expected_heads": [script.get_current_head()],
    }


async def _get_ready_response(client, monkeypatch, *, schema_state: dict[str, object] | None = None, db_error: Exception | None = None):
    from layer5_ground_truth.api import main as main_module

    async def _reachable() -> None:
        return None

    async def _unreachable() -> None:
        raise db_error or RuntimeError("db down")

    monkeypatch.setattr(
        main_module,
        "_check_database_connectivity",
        _unreachable if db_error is not None else _reachable,
    )
    if schema_state is not None:
        async def _schema_state() -> dict[str, object]:
            return schema_state

        monkeypatch.setattr(main_module, "_check_schema_migration_alignment", _schema_state)

    return await client.get("/ready")


@pytest.mark.anyio
async def test_ready_when_db_reachable_and_schema_aligned(client, monkeypatch) -> None:
    response = await _get_ready_response(
        client,
        monkeypatch,
        schema_state={
            "ready": True,
            "schema": "aligned",
            "reason": "schema_aligned",
            "current_revisions": ["head"],
            "expected_heads": ["head"],
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["status"] == "ready"
    assert payload["database"] == "ok"
    assert payload["service"] == "layer5-ground-truth"
    assert payload["readiness"] == {"is_ready": True, "reason": "dependencies_available"}


@pytest.mark.anyio
async def test_not_ready_when_db_reachable_but_schema_drift(client, monkeypatch) -> None:
    response = await _get_ready_response(
        client,
        monkeypatch,
        schema_state={
            "ready": False,
            "schema": "behind",
            "reason": "schema_revision_behind",
            "current_revisions": ["007_add_missing_truth_object_indexes"],
            "expected_heads": ["008_ensure_truth_objects_tenant_id"],
        },
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["database"] == "ok"
    assert payload["schema"] == "behind"
    assert payload["service"] == "layer5-ground-truth"
    assert payload["readiness"] == {"is_ready": False, "reason": "dependency_unhealthy"}
    assert payload["not_ready"] == {
        "component": "schema",
        "reason": "schema_revision_behind",
        "current_revisions": ["007_add_missing_truth_object_indexes"],
        "expected_heads": ["008_ensure_truth_objects_tenant_id"],
    }


@pytest.mark.anyio
async def test_not_ready_when_db_unreachable(client, monkeypatch) -> None:
    response = await _get_ready_response(
        client,
        monkeypatch,
        db_error=RuntimeError("db down"),
    )

    assert response.status_code == 503
    payload = response.json()
    assert payload["status"] == "not_ready"
    assert payload["database"] == "unavailable"
    assert payload["service"] == "layer5-ground-truth"
    assert payload["readiness"] == {"is_ready": False, "reason": "dependency_unhealthy"}
