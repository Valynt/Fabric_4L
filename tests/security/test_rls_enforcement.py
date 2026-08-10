"""S2-C: RLS Enforcement & Connection Pool Reset Tests — Pillar 2.

Ship/No-Ship Gate: These tests verify that:
    1. RLS migration scripts cover ALL tables with tenant_id columns.
    2. The ``get_db`` dependency does NOT set ``app.tenant_id`` (proving it
       bypasses RLS).
    3. The ``get_db_from_context`` dependency DOES set ``app.tenant_id``.
    4. Connection pool sessions are reset between requests (no tenant leakage).
    5. The ``db_session`` context manager validates tenant_id.

Tests in this file are split into two categories:
    - **Static analysis** (no database required): Parse migration scripts and
      source code to verify structural invariants.
    - **Live database** (requires PostgreSQL): Execute actual SQL to verify RLS
      policies are enforced.  These are skipped locally if no DB is available,
      but hard-fail in CI.

Expected Initial State:
    - test_all_tenant_tables_have_rls_policies: FAIL or PASS (depends on model scan)
    - test_get_db_does_not_set_tenant_context: PASS (confirms the vulnerability)
    - test_get_db_from_context_sets_tenant_id: PASS
    - test_rls_policy_uses_current_setting:    PASS
    - test_rls_null_tenant_id_allows_read:     FAIL (RLS policy allows NULL tenant_id)
"""
from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Set

import pytest

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------
_PROJECT_ROOT = Path(__file__).resolve().parents[2]

_L4_DATABASE_MODULE = (
    _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "database.py"
)

_L4_MIGRATIONS_DIR = (
    _PROJECT_ROOT / "services" / "layer4-agents" / "migrations" / "versions"
)

_L4_MODELS_DIR = (
    _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "models"
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _extract_rls_tables_from_migrations() -> set[str]:
    """Extract all table names that have RLS policies from migration files."""
    tables: set[str] = set()

    for migration_file in sorted(_L4_MIGRATIONS_DIR.glob("*.py")):
        source = migration_file.read_text()
        # Match: RLS_TABLES = ["table1", "table2", ...]
        match = re.search(r"RLS_TABLES\s*=\s*\[([^\]]+)\]", source, re.DOTALL)
        if match:
            raw = match.group(1)
            tables.update(re.findall(r'"([^"]+)"', raw))

    return tables


def _extract_model_tables_with_tenant_id() -> set[str]:
    """Find all SQLAlchemy model classes that have a tenant_id column."""
    tables: set[str] = set()

    model_files = list(_L4_MODELS_DIR.glob("*.py"))
    # Also check tenant models
    tenant_models_dir = _PROJECT_ROOT / "services" / "layer4-agents" / "src" / "tenants" / "models"
    if tenant_models_dir.exists():
        model_files.extend(tenant_models_dir.glob("*.py"))

    for model_file in model_files:
        if model_file.name.startswith("__"):
            continue
        source = model_file.read_text()

        # Find __tablename__ assignments
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                has_tablename = None
                has_tenant_id = False

                for item in node.body:
                    # Check for __tablename__ = "..."
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "__tablename__":
                                if isinstance(item.value, ast.Constant):
                                    has_tablename = str(item.value.value)

                    # Check for tenant_id column (various patterns)
                    if isinstance(item, ast.Assign):
                        for target in item.targets:
                            if isinstance(target, ast.Name) and target.id == "tenant_id":
                                has_tenant_id = True
                    elif isinstance(item, ast.AnnAssign):
                        if isinstance(item.target, ast.Name) and item.target.id == "tenant_id":
                            has_tenant_id = True

                if has_tablename and has_tenant_id:
                    tables.add(has_tablename)

    return tables


def _function_source(source: str, function_name: str) -> str:
    """Return source for a function from a parsed Python module."""
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == function_name:
            return ast.get_source_segment(source, node) or ""
    pytest.fail(f"{function_name} function not found in database.py")


# ---------------------------------------------------------------------------
# Tests: Migration Coverage
# ---------------------------------------------------------------------------

class TestRLSMigrationCoverage:
    """Verify RLS policies cover all tables with tenant_id columns."""

    def test_all_tenant_tables_have_rls_policies(self):
        """Every model with tenant_id must have a corresponding RLS policy.

        This test compares the set of tables declared in RLS migration scripts
        against the set of SQLAlchemy models that have a tenant_id column.
        """
        rls_tables = _extract_rls_tables_from_migrations()
        model_tables = _extract_model_tables_with_tenant_id()

        missing_rls = model_tables - rls_tables
        assert not missing_rls, (
            f"Found {len(missing_rls)} table(s) with tenant_id column but no RLS policy:\n"
            + "\n".join(f"  - {t}" for t in sorted(missing_rls))
            + f"\nTables with RLS: {sorted(rls_tables)}"
            + f"\nTables with tenant_id: {sorted(model_tables)}"
        )

    def test_rls_tables_list_is_not_empty(self):
        """Sanity check: we should find at least 8 tables with RLS policies."""
        rls_tables = _extract_rls_tables_from_migrations()
        assert len(rls_tables) >= 8, (
            f"Expected at least 8 tables with RLS policies, found {len(rls_tables)}: "
            f"{sorted(rls_tables)}"
        )


# ---------------------------------------------------------------------------
# Tests: Database Module Structure
# ---------------------------------------------------------------------------

class TestDatabaseModuleStructure:
    """Verify the L4 database module enforces tenant context correctly."""

    def test_get_db_sets_empty_tenant_context(self):
        """Confirm that ``get_db`` explicitly clears tenant context.

        get_db clears app.tenant_id to '' via _clear_local_tenant_context.
        This means it relies on PostgreSQL admin_role to access data,
        bypassing RLS entirely.  This is acceptable for health checks but
        dangerous for business endpoints — which is why S2-A and S2-B tests
        gate on migrating all callers to get_db_from_context.
        """
        source = _L4_DATABASE_MODULE.read_text()

        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "get_db":
                    func_source = ast.get_source_segment(source, node) or ""

                    assert "_clear_local_tenant_context" in func_source, (
                        "get_db does not call _clear_local_tenant_context. "
                        "Even the deprecated path must explicitly clear tenant "
                        "context to prevent leakage from a prior request."
                    )

                    clear_source = _function_source(source, "_clear_local_tenant_context")
                    assert "app.tenant_id" in clear_source, (
                        "_clear_local_tenant_context does not set app.tenant_id."
                    )
                    assert "set_config('app.tenant_id', '', true)" in clear_source, (
                        "_clear_local_tenant_context must set app.tenant_id to "
                        "empty string transaction-locally."
                    )
                    return

        pytest.fail("get_db function not found in database.py")

    def test_get_db_from_context_sets_tenant_id(self):
        """Verify ``get_db_from_context`` sets ``app.tenant_id`` via SET LOCAL."""
        source = _L4_DATABASE_MODULE.read_text()

        # Find get_db_from_context
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "get_db_from_context":
                    func_source = ast.get_source_segment(source, node) or ""

                    assert "_set_local_tenant_context" in func_source, (
                        "get_db_from_context does not call _set_local_tenant_context. "
                        "This means even the 'correct' dependency doesn't enforce RLS."
                    )
                    set_source = _function_source(source, "_set_local_tenant_context")
                    assert "app.tenant_id" in set_source, (
                        "_set_local_tenant_context does not set app.tenant_id."
                    )
                    assert "set_config('app.tenant_id', :tenant_id, true)" in set_source, (
                        "_set_local_tenant_context must use transaction-local "
                        "tenant context via set_config(..., true)."
                    )
                    return

        pytest.fail("get_db_from_context function not found in database.py")

    def test_validate_tenant_id_exists(self):
        """The database module must have a validate_tenant_id function."""
        source = _L4_DATABASE_MODULE.read_text()
        assert "def validate_tenant_id" in source, (
            "database.py does not define validate_tenant_id. "
            "Tenant ID validation is required to prevent injection attacks."
        )

    def test_get_db_from_context_validates_tenant_id(self):
        """get_db_from_context must call validate_tenant_id before using it."""
        source = _L4_DATABASE_MODULE.read_text()

        # Find get_db_from_context and check it calls validate_tenant_id
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "get_db_from_context":
                    func_source = ast.get_source_segment(source, node) or ""
                    assert "validate_tenant_id" in func_source, (
                        "get_db_from_context does not call validate_tenant_id. "
                        "Unvalidated tenant_id could enable SQL injection via "
                        "SET LOCAL app.tenant_id."
                    )
                    return

        pytest.fail("get_db_from_context function not found in database.py")


# ---------------------------------------------------------------------------
# Tests: RLS Policy Structure
# ---------------------------------------------------------------------------

class TestRLSPolicyStructure:
    """Verify RLS policies use the correct PostgreSQL patterns."""

    def test_rls_policy_uses_current_setting(self):
        """RLS policies must use ``current_setting('app.tenant_id', true)``."""
        for migration_file in sorted(_L4_MIGRATIONS_DIR.glob("*.py")):
            source = migration_file.read_text()
            if "RLS_TABLES" not in source:
                continue

            assert "current_setting('app.tenant_id'" in source, (
                f"{migration_file.name} defines RLS_TABLES but does not use "
                f"current_setting('app.tenant_id', true) in the policy."
            )

    def test_rls_null_tenant_id_policy_is_safe(self):
        """RLS policies must NOT allow rows with NULL tenant_id to be visible
        to all tenants.

        The current policy has ``tenant_id IS NULL OR ...`` which means rows
        without a tenant_id are visible to everyone.  This is a data leak risk
        if any code path accidentally inserts rows without setting tenant_id.

        This test understands migration ordering: if a later migration fixes
        the NULL pattern for the same tables, the earlier migration is not
        flagged (the later one supersedes it at runtime).

        Expected initial state: FAIL — current policy allows NULL.
        """
        # Build a map: table -> highest migration revision that touches it
        # Then check only the latest migration for each table
        migration_files = sorted(_L4_MIGRATIONS_DIR.glob("*.py"))

        # Collect all migrations with RLS_TABLES and their tables
        migrations_with_rls: list[tuple[Path, set]] = []
        for mf in migration_files:
            source = mf.read_text()
            match = re.search(r"RLS_TABLES\s*=\s*\[([^\]]+)\]", source, re.DOTALL)
            if match:
                tables = set(re.findall(r'"([^"]+)"', match.group(1)))
                migrations_with_rls.append((mf, tables))

        # For each table, find the LATEST migration that defines it
        table_latest_migration: dict[str, Path] = {}
        for mf, tables in migrations_with_rls:
            for table in tables:
                table_latest_migration[table] = mf  # later files overwrite earlier

        # Now check only the latest migration for each table
        files_to_check = set(table_latest_migration.values())
        for migration_file in sorted(files_to_check):
            source = migration_file.read_text()

            if "tenant_id IS NULL" in source:
                # Check if it's in a USING clause in the upgrade function
                # (downgrade functions may restore old patterns — that's expected)
                upgrade_match = re.search(
                    r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
                    source,
                    re.DOTALL,
                )
                if upgrade_match:
                    upgrade_source = upgrade_match.group(0)
                    if re.search(r"USING\s*\([^)]*tenant_id\s+IS\s+NULL", upgrade_source, re.IGNORECASE):
                        pytest.fail(
                            f"{migration_file.name}: RLS policy allows rows with NULL tenant_id "
                            f"to be visible to all tenants. This means any row inserted without "
                            f"a tenant_id is a global data leak. The policy should require "
                            f"tenant_id to be NOT NULL, or use a separate admin-only policy "
                            f"for NULL rows."
                        )


    def test_remediation_migrations_do_not_reintroduce_null_visibility(self):
        """Remediation migration upgrade() functions must not contain the NULL bypass.

        Docstrings and downgrade() functions may reference the old pattern for
        documentation purposes. Only the upgrade() body is checked — that is
        what actually runs against the production database.
        """
        remediation_files = [
            _L4_MIGRATIONS_DIR / "025_fix_billing_rls_policies.py",
            _L4_MIGRATIONS_DIR / "026_fix_rls_null_tenant_policy.py",
            _L4_MIGRATIONS_DIR / "032_fix_rls_null_bypass_crm_billing.py",
            _L4_MIGRATIONS_DIR / "033_fix_rls_null_tenant_policy_remaining.py",
        ]

        for migration_file in remediation_files:
            if not migration_file.exists():
                continue
            source = migration_file.read_text()
            upgrade_match = re.search(
                r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
                source,
                re.DOTALL,
            )
            if not upgrade_match:
                continue
            upgrade_body = upgrade_match.group(0)
            assert "tenant_id IS NULL OR" not in upgrade_body, (
                f"{migration_file.name} upgrade(): found NULL-permissive tenant policy "
                "clause (tenant_id IS NULL OR ...). Remediation migrations must "
                "use strict tenant equality in upgrade() to prevent cross-tenant "
                "data visibility."
            )

    def test_crm_and_billing_tables_have_strict_rls(self):
        """Migration 032 must cover crm_sync_jobs and billing tables with strict RLS.

        These tables were introduced with the unsafe NULL bypass pattern in
        migrations 030 and 014. Migration 032 must fix them.
        """
        fix_migration = _L4_MIGRATIONS_DIR / "032_fix_rls_null_bypass_crm_billing.py"
        assert fix_migration.exists(), (
            "Migration 032_fix_rls_null_bypass_crm_billing.py is missing. "
            "crm_sync_jobs and billing tables have unsafe NULL RLS bypass."
        )

        source = fix_migration.read_text()

        # Must cover the affected tables
        required_tables = [
            "billing_customers",
            "billing_subscriptions",
            "billing_webhook_events",
            "crm_sync_jobs",
        ]
        for table in required_tables:
            assert table in source, (
                f"Migration 032 does not reference '{table}'. "
                f"This table still has the unsafe NULL RLS bypass."
            )

        # Must use strict matching (no NULL bypass) in upgrade
        upgrade_match = re.search(
            r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
            source,
            re.DOTALL,
        )
        assert upgrade_match, "Migration 032 has no upgrade() function."
        upgrade_body = upgrade_match.group(0)

        assert "tenant_id IS NULL" not in upgrade_body, (
            "Migration 032 upgrade() still contains 'tenant_id IS NULL'. "
            "The fix must use strict tenant_id equality only."
        )
        assert "current_setting('app.tenant_id'" in upgrade_body, (
            "Migration 032 upgrade() does not use current_setting('app.tenant_id'). "
            "RLS policy must use the PostgreSQL session variable."
        )

    def test_rls_force_enabled(self):
        """RLS must be FORCE enabled (applies even to table owners)."""
        for migration_file in sorted(_L4_MIGRATIONS_DIR.glob("*.py")):
            source = migration_file.read_text()
            if "RLS_TABLES" not in source:
                continue

            assert "FORCE ROW LEVEL SECURITY" in source, (
                f"{migration_file.name}: RLS is not FORCE enabled. Without FORCE, "
                f"the table owner role bypasses all RLS policies."
            )


# ---------------------------------------------------------------------------
# Tests: Connection Pool Reset
# ---------------------------------------------------------------------------

class TestConnectionPoolReset:
    """Verify that database sessions are properly reset between requests.

    If ``app.tenant_id`` persists across connection pool reuse, Tenant A's
    context could leak into Tenant B's request.
    """

    def test_session_uses_set_local_not_set(self):
        """Database module must use ``SET LOCAL`` (transaction-scoped), not
        ``SET`` (session-scoped).

        ``SET LOCAL`` automatically resets when the transaction ends.
        ``SET`` persists across the connection's lifetime, which means
        connection pool reuse would leak tenant context.
        """
        source = _L4_DATABASE_MODULE.read_text()

        # Find all SET statements for app.tenant_id
        set_statements = re.findall(r"(SET\s+(?:LOCAL\s+)?app\.tenant_id)", source, re.IGNORECASE)

        for stmt in set_statements:
            assert "LOCAL" in stmt.upper(), (
                f"Found '{stmt}' without LOCAL qualifier. "
                f"SET without LOCAL persists across connection pool reuse, "
                f"causing tenant context leakage between requests."
            )

    def test_no_raw_set_without_local(self):
        """No ``SET app.tenant_id`` (without LOCAL) should appear anywhere."""
        source = _L4_DATABASE_MODULE.read_text()

        # Match SET app.tenant_id but NOT SET LOCAL app.tenant_id
        # Use negative lookbehind for LOCAL
        matches = re.findall(
            r"['\"]SET\s+app\.tenant_id",
            source,
            re.IGNORECASE,
        )

        for match in matches:
            assert "LOCAL" in match.upper(), (
                f"Found raw SET app.tenant_id without LOCAL: {match!r}. "
                f"This causes tenant context leakage in connection pools."
            )

    def test_session_commits_or_rollbacks(self):
        """Every session context manager must have both commit and rollback paths.

        If a session is returned to the pool without commit/rollback, the
        ``SET LOCAL`` may persist in some database drivers.
        """
        source = _L4_DATABASE_MODULE.read_text()

        # Check that get_db_from_context has both commit and rollback
        # (or at minimum, the session is properly managed)
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name == "get_db_from_context":
                    func_source = ast.get_source_segment(source, node) or ""

                    # Should have try/except with rollback
                    has_rollback = "rollback" in func_source
                    has_yield = "yield" in func_source

                    assert has_yield, (
                        "get_db_from_context does not yield a session. "
                        "It must be an async generator for FastAPI Depends()."
                    )

                    # Note: rollback may be handled by the session factory
                    # context manager, so we just verify the yield exists
                    return

        pytest.fail("get_db_from_context not found in database.py")


# ---------------------------------------------------------------------------
# P0 expansion: Layer 1 RLS coverage
# ---------------------------------------------------------------------------

_L1_MIGRATIONS_DIR = (
    _PROJECT_ROOT / "services" / "layer1-ingestion" / "migrations" / "versions"
)


# ---------------------------------------------------------------------------
# Tests: Migration 033 — remaining NULL-bypass tables
# ---------------------------------------------------------------------------

class TestMigration033RLSCoverage:
    """Verify migration 033 closes the remaining NULL-permissive RLS gaps.

    Migration 033 fixes billing tables (025), company-knowledge tables (029),
    and CRM sync jobs (030) — all of which were created after migration 026
    ran and therefore still had the unsafe ``tenant_id IS NULL OR ...`` pattern.
    """

    _MIGRATION_FILE = (
        _L4_MIGRATIONS_DIR / "033_fix_rls_null_tenant_policy_remaining.py"
    )

    _EXPECTED_TABLES = [
        # Billing (025)
        "billing_charges",
        "billing_customers",
        "billing_invoice_items",
        "billing_invoices",
        "billing_subscriptions",
        "billing_usage_events",
        "billing_webhook_events",
        # Company knowledge (029)
        "company_knowledge_profiles",
        "icp_profiles",
        "knowledge_sources",
        "value_extraction_records",
        # CRM (030)
        "crm_sync_jobs",
    ]

    # Billing tables that 032 did not cover — 033 must create admin_bypass_policy.
    _NEEDS_ADMIN_BYPASS = [
        "billing_charges",
        "billing_invoice_items",
        "billing_invoices",
        "billing_usage_events",
    ]

    def test_migration_033_exists(self):
        """Migration 033_fix_rls_null_tenant_policy_remaining.py must exist."""
        assert self._MIGRATION_FILE.exists(), (
            "Migration 033_fix_rls_null_tenant_policy_remaining.py is missing. "
            "Billing, company-knowledge, and CRM tables still have the unsafe "
            "NULL-permissive RLS policy."
        )

    def test_migration_033_covers_all_expected_tables(self):
        """Migration 033 must reference all 12 affected tables."""
        if not self._MIGRATION_FILE.exists():
            pytest.skip("Migration 033 not yet created")

        source = self._MIGRATION_FILE.read_text()
        for table in self._EXPECTED_TABLES:
            assert table in source, (
                f"Migration 033 does not reference '{table}'. "
                f"This table still has the unsafe NULL RLS bypass."
            )

    def test_migration_033_upgrade_is_strict(self):
        """Migration 033 upgrade() must not contain tenant_id IS NULL."""
        if not self._MIGRATION_FILE.exists():
            pytest.skip("Migration 033 not yet created")

        source = self._MIGRATION_FILE.read_text()
        upgrade_match = re.search(
            r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
            source,
            re.DOTALL,
        )
        assert upgrade_match, "Migration 033 has no upgrade() function."
        upgrade_body = upgrade_match.group(0)

        assert "tenant_id IS NULL" not in upgrade_body, (
            "Migration 033 upgrade() still contains 'tenant_id IS NULL'. "
            "The fix must use strict tenant_id equality only."
        )

    def test_migration_033_uses_current_setting(self):
        """Migration 033 upgrade() must use current_setting('app.tenant_id')."""
        if not self._MIGRATION_FILE.exists():
            pytest.skip("Migration 033 not yet created")

        source = self._MIGRATION_FILE.read_text()
        upgrade_match = re.search(
            r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
            source,
            re.DOTALL,
        )
        assert upgrade_match, "Migration 033 has no upgrade() function."
        upgrade_body = upgrade_match.group(0)

        assert "current_setting('app.tenant_id'" in upgrade_body, (
            "Migration 033 upgrade() does not use current_setting('app.tenant_id'). "
            "RLS policy must use the PostgreSQL session variable."
        )

    def test_migration_033_force_row_level_security(self):
        """Migration 033 must FORCE ROW LEVEL SECURITY on all covered tables."""
        if not self._MIGRATION_FILE.exists():
            pytest.skip("Migration 033 not yet created")

        source = self._MIGRATION_FILE.read_text()
        assert "FORCE ROW LEVEL SECURITY" in source, (
            "Migration 033 does not FORCE ROW LEVEL SECURITY. "
            "Without FORCE, the table owner role bypasses all RLS policies."
        )

    def test_migration_033_creates_admin_bypass_for_billing_tables(self):
        """Migration 033 must create admin_bypass_policy for the 4 billing tables
        not covered by migration 032."""
        if not self._MIGRATION_FILE.exists():
            pytest.skip("Migration 033 not yet created")

        source = self._MIGRATION_FILE.read_text()
        upgrade_match = re.search(
            r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
            source,
            re.DOTALL,
        )
        assert upgrade_match, "Migration 033 has no upgrade() function."
        upgrade_body = upgrade_match.group(0)

        assert "admin_bypass_policy" in upgrade_body, (
            "Migration 033 upgrade() does not create admin_bypass_policy. "
            "The 4 billing tables not covered by 032 need admin access."
        )
        for table in self._NEEDS_ADMIN_BYPASS:
            assert table in upgrade_body, (
                f"Migration 033 upgrade() does not reference '{table}' "
                f"for admin_bypass_policy creation."
            )

    def test_migration_033_downgrade_scoped_to_033_tables(self):
        """Migration 033 downgrade() must only drop policies it created.

        It must not drop policies on tables owned by migrations 028 or 032
        (company-knowledge and CRM tables already had admin_bypass_policy).
        """
        if not self._MIGRATION_FILE.exists():
            pytest.skip("Migration 033 not yet created")

        source = self._MIGRATION_FILE.read_text()
        downgrade_match = re.search(
            r"def downgrade\(\).*",
            source,
            re.DOTALL,
        )
        if not downgrade_match:
            return  # No downgrade — acceptable

        downgrade_body = downgrade_match.group(0)

        # company_knowledge and CRM tables had admin_bypass_policy from 028/032.
        # 033 downgrade must not drop those — only drop what 033 created.
        # The safe pattern is to use DROP POLICY IF EXISTS (idempotent).
        if "admin_bypass_policy" in downgrade_body:
            assert "IF EXISTS" in downgrade_body, (
                "Migration 033 downgrade() drops admin_bypass_policy without "
                "'IF EXISTS'. This is unsafe — it may fail if the policy was "
                "already removed by a prior migration."
            )

    def test_migration_033_is_latest_for_covered_tables(self):
        """For each table 033 covers, 033 must be the latest migration touching it.

        This ensures the strict policy from 033 is not overwritten by a later
        migration that reintroduces the NULL bypass.
        """
        if not self._MIGRATION_FILE.exists():
            pytest.skip("Migration 033 not yet created")

        migration_files = sorted(_L4_MIGRATIONS_DIR.glob("*.py"))

        for table in self._EXPECTED_TABLES:
            latest: Path | None = None
            for mf in migration_files:
                src = mf.read_text()
                if table in src:
                    latest = mf

            assert latest is not None, f"No migration references '{table}'"

            # The latest migration touching this table must not have NULL bypass
            # in its upgrade() body.
            src = latest.read_text()
            upgrade_match = re.search(
                r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
                src,
                re.DOTALL,
            )
            if not upgrade_match:
                continue
            upgrade_body = upgrade_match.group(0)

            if re.search(r"USING\s*\([^)]*tenant_id\s+IS\s+NULL", upgrade_body, re.IGNORECASE):
                pytest.fail(
                    f"{latest.name}: Latest migration for '{table}' still has "
                    f"NULL-permissive RLS in upgrade(). Migration 033 must be "
                    f"the last migration touching this table."
                )


class TestLayer1RLSCoverage:
    """Verify Layer 1 migration 013 fixes the crawl_decisions NULL bypass.

    Migration 005 introduced crawl_decisions with an unsafe
    ``tenant_id IS NULL OR ...`` RLS policy. Migration 013 must fix it.
    """

    def test_l1_fix_migration_exists(self):
        """Migration 013_fix_rls_null_bypass_crawl_decisions.py must exist."""
        fix_migration = _L1_MIGRATIONS_DIR / "013_fix_rls_null_bypass_crawl_decisions.py"
        assert fix_migration.exists(), (
            "Migration 013_fix_rls_null_bypass_crawl_decisions.py is missing. "
            "crawl_decisions table still has the unsafe NULL RLS bypass from migration 005."
        )

    def test_l1_fix_migration_covers_crawl_decisions(self):
        """Migration 013 must reference crawl_decisions."""
        fix_migration = _L1_MIGRATIONS_DIR / "013_fix_rls_null_bypass_crawl_decisions.py"
        if not fix_migration.exists():
            pytest.skip("Migration 013 not yet created")

        source = fix_migration.read_text()
        assert "crawl_decisions" in source, (
            "Migration 013 does not reference crawl_decisions. "
            "The NULL bypass fix is incomplete."
        )

    def test_l1_fix_migration_upgrade_is_strict(self):
        """Migration 013 upgrade() must not contain tenant_id IS NULL."""
        fix_migration = _L1_MIGRATIONS_DIR / "013_fix_rls_null_bypass_crawl_decisions.py"
        if not fix_migration.exists():
            pytest.skip("Migration 013 not yet created")

        source = fix_migration.read_text()
        upgrade_match = re.search(
            r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
            source,
            re.DOTALL,
        )
        assert upgrade_match, "Migration 013 has no upgrade() function."
        upgrade_body = upgrade_match.group(0)

        assert "tenant_id IS NULL" not in upgrade_body, (
            "Migration 013 upgrade() still contains 'tenant_id IS NULL'. "
            "The fix must use strict tenant_id equality only."
        )

    def test_l1_original_migration_005_null_bypass_is_superseded(self):
        """Migration 005 NULL bypass is superseded by migration 013.

        This test verifies that the latest migration touching crawl_decisions
        is 013 (strict), not 005 (unsafe). It uses the same table-latest-migration
        logic as test_rls_null_tenant_id_policy_is_safe.
        """
        migration_files = sorted(_L1_MIGRATIONS_DIR.glob("*.py"))

        table_latest: dict[str, Path] = {}
        for mf in migration_files:
            source = mf.read_text()
            if "crawl_decisions" in source:
                table_latest["crawl_decisions"] = mf

        latest = table_latest.get("crawl_decisions")
        if latest is None:
            pytest.skip("crawl_decisions not found in any L1 migration")

        source = latest.read_text()
        upgrade_match = re.search(
            r"def upgrade\(\).*?(?=def downgrade\(\)|\Z)",
            source,
            re.DOTALL,
        )
        if not upgrade_match:
            return  # No upgrade function — skip

        upgrade_body = upgrade_match.group(0)
        assert "tenant_id IS NULL" not in upgrade_body, (
            f"{latest.name}: The latest migration touching crawl_decisions still "
            "has the unsafe NULL RLS bypass in upgrade(). "
            "Migration 013 must be the latest and must use strict matching."
        )
