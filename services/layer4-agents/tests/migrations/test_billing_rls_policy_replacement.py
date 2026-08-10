"""Regression tests for repeatable billing RLS policy migrations."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from unittest.mock import patch

import pytest

VERSIONS = Path(__file__).parents[2] / "migrations" / "versions"


def _load_revision(revision: str) -> ModuleType:
    path = next(VERSIONS.glob(f"{revision}_*.py"))
    spec = importlib.util.spec_from_file_location(f"migration_{revision}", path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize("revision", ["018", "025"])
def test_billing_policy_migrations_replace_existing_policies(revision: str) -> None:
    """Fresh upgrades must replace policies created by earlier revisions."""
    module = _load_revision(revision)
    statements: list[str] = []

    with patch.object(module.op, "execute", side_effect=statements.append):
        module.upgrade()

    normalized = [" ".join(statement.split()) for statement in statements]
    for index, statement in enumerate(normalized):
        if not statement.startswith("CREATE POLICY"):
            continue
        policy_name = statement.split()[2]
        table = statement.split(" ON ", maxsplit=1)[1].split()[0]
        expected_drop = f"DROP POLICY IF EXISTS {policy_name} ON {table}"
        assert expected_drop in normalized[:index], (
            f"revision {revision} creates {policy_name} on {table} "
            "without first replacing an earlier policy"
        )
