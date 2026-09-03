"""Add authorization control-plane tables and RLS.

Revision ID: a1c93fb0a2c4
Revises: 6f3b9c2d4a91
Create Date: 2026-05-30

Creates the PBAC persistence model (principals, role assignments, resource
bindings, delegation grants, external access grants, break-glass grants, and
decision records). Every tenant-owned table is RLS-enabled and FORCEd, and its
tenant predicate reads the ``app.tenant_id`` GUC exactly like the existing
``fabric_api_records`` tenant-isolation policy so that a privileged maintenance
session must operate on an explicit tenant and cannot impersonate owner-level
access.

Domain command protections are layered on policy in the application; this
migration provides the tenant-containment backstop only.
"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "a1c93fb0a2c4"
down_revision = "6f3b9c2d4a91"
branch_labels = None
depends_on = None


_CREATE = """
-- 13.1 Principals and memberships
CREATE TABLE authz_principals (
    id uuid PRIMARY KEY,
    tenant_id uuid NULL,
    principal_type text NOT NULL,
    external_subject text NULL,
    canonical_name text NOT NULL,
    status text NOT NULL,
    authz_revision bigint NOT NULL DEFAULT 1,
    created_at timestamptz NOT NULL,
    deactivated_at timestamptz NULL
);

CREATE TABLE authz_role_assignments (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    principal_id uuid NOT NULL,
    role_id text NOT NULL,
    scope_type text NOT NULL DEFAULT 'tenant',
    scope_id uuid NULL,
    approval_ceiling_usd numeric(19,2) NULL,
    effective_at timestamptz NOT NULL,
    expires_at timestamptz NULL,
    assigned_by uuid NOT NULL,
    assignment_reason text NOT NULL,
    revision bigint NOT NULL DEFAULT 1,
    CONSTRAINT authz_role_assignments_tenant_principal_role_unique
        UNIQUE (tenant_id, principal_id, role_id, scope_type, scope_id)
);

-- 13.2 Relationships (typed, validated resource relations)
CREATE TABLE authz_resource_bindings (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    resource_type text NOT NULL,
    resource_id uuid NOT NULL,
    relation text NOT NULL,
    principal_id uuid NOT NULL,
    effective_at timestamptz NOT NULL,
    expires_at timestamptz NULL,
    assigned_by uuid NOT NULL,
    revision bigint NOT NULL DEFAULT 1,
    CONSTRAINT authz_resource_bindings_tenant_resource_relation_principal_unique
        UNIQUE (tenant_id, resource_type, resource_id, relation, principal_id)
);

-- 13.3 Delegation and external grants
CREATE TABLE authz_delegation_grants (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    subject_principal_id uuid NOT NULL,
    actor_principal_id uuid NOT NULL,
    scopes text[] NOT NULL,
    resource_constraints jsonb NOT NULL,
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz NULL,
    issued_by uuid NOT NULL,
    revision bigint NOT NULL DEFAULT 1
);

CREATE TABLE authz_external_access_grants (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    token_hash bytea NOT NULL UNIQUE,
    deliverable_id uuid NOT NULL,
    deliverable_version text NOT NULL,
    actions text[] NOT NULL,
    audience_constraints jsonb NOT NULL,
    issued_by uuid NOT NULL,
    issued_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz NULL,
    revision bigint NOT NULL DEFAULT 1
);

-- 13.4 Break-glass (dual control enforced at the data layer)
CREATE TABLE authz_break_glass_grants (
    id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    beneficiary_principal_id uuid NOT NULL,
    requested_by uuid NOT NULL,
    approved_by_primary uuid NOT NULL,
    approved_by_secondary uuid NOT NULL,
    scopes text[] NOT NULL,
    resource_constraints jsonb NOT NULL,
    reason_code text NOT NULL,
    narrative text NOT NULL,
    starts_at timestamptz NOT NULL,
    expires_at timestamptz NOT NULL,
    revoked_at timestamptz NULL,
    status text NOT NULL,
    CONSTRAINT authz_break_glass_requestor_not_primary
        CHECK (requested_by <> approved_by_primary),
    CONSTRAINT authz_break_glass_beneficiary_not_primary
        CHECK (beneficiary_principal_id <> approved_by_primary),
    CONSTRAINT authz_break_glass_primary_not_secondary
        CHECK (approved_by_primary <> approved_by_secondary)
);

-- 13.5 Decision records (immutable, correlated, no raw JWTs/secrets/prompts)
CREATE TABLE authz_decisions (
    decision_id uuid PRIMARY KEY,
    tenant_id uuid NOT NULL,
    request_id text NOT NULL,
    trace_id text NULL,
    principal_id uuid NOT NULL,
    actor_principal_id uuid NULL,
    action text NOT NULL,
    resource_type text NOT NULL,
    resource_id uuid NOT NULL,
    allowed boolean NOT NULL,
    reason_codes text[] NOT NULL,
    obligations jsonb NOT NULL,
    policy_version text NOT NULL,
    bundle_digest text NOT NULL,
    input_fingerprint text NOT NULL,
    resource_authz_revision bigint NOT NULL,
    membership_revision bigint NOT NULL,
    evaluated_at timestamptz NOT NULL,
    latency_ms numeric(12,3) NOT NULL
);

"""

# Note: Domain-object authz_revision/author/validator/approver bookkeeping
# (design §13.6) lives in the owning service migrations (e.g. L5 `value_claims`
# table adds its columns there), not in the API control-plane chain, because
# the domain tables are not owned by this Alembic chain.

_TENANT_TABLES = [
    "authz_principals",
    "authz_role_assignments",
    "authz_resource_bindings",
    "authz_delegation_grants",
    "authz_external_access_grants",
    "authz_break_glass_grants",
    "authz_decisions",
]


def _rlst() -> str:
    """Return per-table FORCE RLS + tenant predicate policy SQL."""
    stmts = []
    for table in _TENANT_TABLES:
        stmts.append(f"""
ALTER TABLE {table} ENABLE ROW LEVEL SECURITY;
ALTER TABLE {table} FORCE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS {table}_tenant_isolation ON {table};
CREATE POLICY {table}_tenant_isolation ON {table}
    USING (tenant_id = current_setting('app.tenant_id', true))
    WITH CHECK (tenant_id = current_setting('app.tenant_id', true));
""")
    return "\n".join(stmts)


_DROP = "\n".join(f"DROP TABLE IF EXISTS {t};" for t in reversed(_TENANT_TABLES))


def upgrade() -> None:
    op.execute(_CREATE)
    op.execute(_rlst())


def downgrade() -> None:
    # Drop tenant policies first so the tables can be removed cleanly.
    for t in _TENANT_TABLES:
        op.execute(
            f"DROP POLICY IF EXISTS {t}_tenant_isolation ON {t};"
            f"ALTER TABLE {t} NO FORCE ROW LEVEL SECURITY;"
        )
    op.execute(_DROP)