"""Regression contract for ORM columns required by the live E2E service."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import call, patch

VERSIONS = Path(__file__).parents[2] / "migrations" / "versions"


def _load_revision() -> ModuleType:
    path = next(VERSIONS.glob("046_*.py"))
    spec = importlib.util.spec_from_file_location("migration_046", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_upgrade_adds_columns_required_by_runtime_models() -> None:
    migration = _load_revision()

    with patch.object(migration.op, "add_column") as add_column:
        migration.upgrade()

    assert [entry.args[0] for entry in add_column.call_args_list] == [
        "accounts",
        "harness_human_gates",
    ]
    account_column = add_column.call_args_list[0].args[1]
    gate_column = add_column.call_args_list[1].args[1]
    assert account_column.name == "employees"
    assert isinstance(account_column.type, migration.sa.Integer)
    assert account_column.nullable is True
    assert gate_column.name == "action_class"
    assert isinstance(gate_column.type, migration.sa.String)
    assert gate_column.type.length == 64
    assert gate_column.nullable is True


def test_downgrade_removes_runtime_columns_in_reverse_order() -> None:
    migration = _load_revision()

    with patch.object(migration.op, "drop_column") as drop_column:
        migration.downgrade()

    assert drop_column.call_args_list == [
        call("harness_human_gates", "action_class"),
        call("accounts", "employees"),
    ]
