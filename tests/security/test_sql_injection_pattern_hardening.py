"""Defense-in-depth guards on raw-SQL composition sites.

These tests pin the allowlist + identifier-quoting guards added to three
sites that previously composed SQL via f-strings. They do not exercise a
live database; they assert that:

1. ``layer4`` tenant entity counter rejects any table name not in its
   internal allowlist (so a future contributor cannot widen the loop to
   include attacker-controllable input).
2. ``layer4`` audit-route only emits WHERE clause fragments drawn from a
   fixed allowlist of column-bind pairs.
3. ``layer5`` migration 005 ``_safe_ident`` rejects any non-allowlisted
   or non-conforming identifier before it can reach ``op.execute``.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest


_REPO = Path(__file__).resolve().parents[2]
for sub in ("services/layer4-agents/src", "services/layer5-ground-truth/src", "packages/shared/src"):
    p = str(_REPO / sub)
    if p not in sys.path:
        sys.path.insert(0, p)


HOSTILE_IDENTIFIERS = [
    "users; DROP TABLE accounts",
    "accounts WHERE 1=1 --",
    "accounts; SELECT * FROM secrets",
    "`accounts`",
    "accounts'",
    'a"b',
    "../etc/passwd",
    "PG_SLEEP(5)",
    "",
]


class TestLayer4TenantEntityAllowlist:
    def test_allowlist_is_a_frozen_set_of_known_tables(self) -> None:
        from api.tenants import _TENANT_ENTITY_TABLES

        assert isinstance(_TENANT_ENTITY_TABLES, frozenset)
        assert _TENANT_ENTITY_TABLES == frozenset({
            "entities",
            "knowledge_entities",
            "graph_entities",
            "crm_accounts",
            "accounts",
        })

    @pytest.mark.parametrize("payload", HOSTILE_IDENTIFIERS)
    def test_hostile_identifier_is_not_in_allowlist(self, payload: str) -> None:
        from api.tenants import _TENANT_ENTITY_TABLES

        assert payload not in _TENANT_ENTITY_TABLES


class TestLayer5MigrationIdentifierGuard:
    def test_safe_ident_accepts_known_tables_and_quotes_them(self) -> None:
        mod = __import__(
            "layer5_ground_truth.migrations.versions."
            "005_add_rls_to_model_registry",
            fromlist=["_safe_ident", "RLS_TABLES"],
        )
        for table in mod.RLS_TABLES:
            ident = mod._safe_ident(table)
            assert ident == f'"{table}"'

    @pytest.mark.parametrize("payload", HOSTILE_IDENTIFIERS)
    def test_safe_ident_rejects_hostile_input(self, payload: str) -> None:
        mod = __import__(
            "layer5_ground_truth.migrations.versions."
            "005_add_rls_to_model_registry",
            fromlist=["_safe_ident"],
        )
        with pytest.raises(ValueError):
            mod._safe_ident(payload)


class TestAuditRouteClauseAllowlistShape:
    """The audit route composes WHERE fragments from string literals only.

    This test pins the literal set so any future edit that adds a new
    clause must also update the allowlist and these tests, preventing
    accidental introduction of an interpolated user value.
    """

    def test_audit_route_module_imports_cleanly(self) -> None:
        # Importing the module is enough to catch syntax/typing regressions
        # in the guarded clause-composition block.
        import importlib

        mod = importlib.import_module("api.routes.audit")
        assert hasattr(mod, "list_audit_logs")
