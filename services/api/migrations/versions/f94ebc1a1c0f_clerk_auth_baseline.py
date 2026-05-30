"""Clerk auth baseline schema.

Revision ID: f94ebc1a1c0f
Revises: 
Create Date: 2026-05-20

"""
from alembic import op

# revision identifiers, used by Alembic.
revision = "f94ebc1a1c0f"
down_revision = None
branch_labels = None
depends_on = None


_UP_SQL = """
-- users table (Clerk sync target)
CREATE TABLE IF NOT EXISTS users (
    id TEXT PRIMARY KEY,
    clerk_user_id TEXT UNIQUE NOT NULL,
    email TEXT NOT NULL,
    first_name TEXT,
    last_name TEXT,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- tenant_memberships (user-to-tenant mapping)
CREATE TABLE IF NOT EXISTS tenant_memberships (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id)
);

-- account_memberships (tenant-to-account mapping)
CREATE TABLE IF NOT EXISTS account_memberships (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    account_id TEXT NOT NULL,
    user_id TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role TEXT NOT NULL DEFAULT 'member',
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, account_id, user_id)
);

-- tenant_entitlements (Phase-1 schema only; enforced in Phase 3)
CREATE TABLE IF NOT EXISTS tenant_entitlements (
    id TEXT PRIMARY KEY,
    tenant_id TEXT NOT NULL,
    entitlement_key TEXT NOT NULL,
    enabled BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, entitlement_key)
);

-- auth_audit_events (append-only)
CREATE TABLE IF NOT EXISTS auth_audit_events (
    id TEXT PRIMARY KEY,
    tenant_id TEXT,
    user_id TEXT,
    clerk_user_id TEXT,
    event_type TEXT NOT NULL,
    resource_type TEXT,
    resource_id TEXT,
    decision TEXT,
    request_id TEXT,
    detail JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS auth_audit_events_tenant_idx
    ON auth_audit_events (tenant_id, created_at DESC);

-- clerk_webhook_events (idempotency dedupe)
CREATE TABLE IF NOT EXISTS clerk_webhook_events (
    id BIGSERIAL PRIMARY KEY,
    event_id TEXT NOT NULL UNIQUE,
    event_type TEXT NOT NULL,
    received_at TIMESTAMPTZ NOT NULL DEFAULT now()
);
"""

_DOWN_SQL = """
DROP TABLE IF EXISTS clerk_webhook_events CASCADE;
DROP TABLE IF EXISTS auth_audit_events CASCADE;
DROP TABLE IF EXISTS tenant_entitlements CASCADE;
DROP TABLE IF EXISTS account_memberships CASCADE;
DROP TABLE IF EXISTS tenant_memberships CASCADE;
DROP TABLE IF EXISTS users CASCADE;
"""


def upgrade() -> None:
    op.execute(_UP_SQL)


def downgrade() -> None:
    op.execute(_DOWN_SQL)
