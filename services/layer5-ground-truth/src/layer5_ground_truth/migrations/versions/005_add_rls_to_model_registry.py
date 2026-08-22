"""Add RLS policies to model registry tables.

Revision ID: 005
Revises: 004
Create Date: 2026-04-25

Model registry tables (model_versions, model_deployments, model_evaluations)
were added in migration 003 with tenant_id columns but without RLS policies.
This migration closes that gap (Phase 1, Task 1.6).

Note: The tenant column normalization was handled in migration 004. The RLS
policies here reference tenant_id.
"""

try:
    from alembic import op
except ImportError:  # pragma: no cover
    op = None

revision = "005"
down_revision = "004"
branch_labels = None
depends_on = None

# Whitelisted, lowercase ASCII identifiers only. Used as a guard so the
# DDL string composition below cannot become an injection sink if the list
# is later extended from a non-static source.
RLS_TABLES = [
    "model_versions",
    "model_deployments",
    "model_evaluations",
]

_IDENT_RE = __import__("re").compile(r"^[a-z_][a-z0-9_]*$")


def _safe_ident(name: str) -> str:
    """Return ``name`` if it is a safe lowercase SQL identifier, else raise."""
    if name not in RLS_TABLES or not _IDENT_RE.match(name):
        raise ValueError(f"Refusing to emit DDL for unknown identifier: {name!r}")
    # Double-quote to force exact-case lookup and neutralize any reserved words.
    return f'"{name}"'


def upgrade() -> None:
    """Enable RLS and create tenant isolation policies on model registry tables."""
    for table in RLS_TABLES:
        ident = _safe_ident(table)
        op.execute(f"ALTER TABLE {ident} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {ident} FORCE ROW LEVEL SECURITY")

        op.execute(f"""
            CREATE POLICY tenant_isolation_policy ON {ident}
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
        """)

        op.execute(f"""
            CREATE POLICY admin_bypass_policy ON {ident}
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
        """)


def downgrade() -> None:
    """Remove RLS policies and disable RLS on model registry tables."""
    for table in RLS_TABLES:
        ident = _safe_ident(table)
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation_policy ON {ident}")
        op.execute(f"DROP POLICY IF EXISTS admin_bypass_policy ON {ident}")
        op.execute(f"ALTER TABLE {ident} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {ident} DISABLE ROW LEVEL SECURITY")
