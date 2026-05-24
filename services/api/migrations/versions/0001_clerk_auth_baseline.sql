-- =============================================================================
-- 0001_clerk_auth_baseline.sql
--
-- Phase 1 Clerk + Fabric4L baseline schema for the API gateway service.
-- This migration is *additive*; it does not touch existing tables.
--
-- Tables in this migration:
--   users                    Internal user records mirrored from Clerk.
--   tenants                  Internal tenant records mirrored from Clerk Orgs.
--   tenant_memberships       (user, tenant) -> role/status mapping.
--   account_memberships      Phase-1 schema only; enforced in Phase 3.
--   tenant_entitlements      Phase-1 schema only; enforced in Phase 3.
--   auth_audit_events        Append-only audit trail; populated in Phase 4.
--   clerk_webhook_events     Webhook idempotency dedupe.
--
-- RLS:
--   ``app.tenant_id`` is the canonical session GUC, set by the
--   FabricAuthMiddleware via :func:`apply_tenant_rls`. Every tenant-scoped
--   table here has RLS enabled with the same canonical USING clause.
--
-- IMPORTANT: This file is intended to be wrapped by an Alembic revision
-- once the gateway adopts Postgres. Until then it serves as the canonical
-- DDL artifact and is exercised by the Phase-1 schema-parity test.
-- =============================================================================

BEGIN;

-- ---------------------------------------------------------------------------
-- users
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS users (
    id              TEXT PRIMARY KEY,
    clerk_user_id   TEXT NOT NULL UNIQUE,
    email           TEXT,
    display_name    TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS users_email_idx ON users (email);

-- ---------------------------------------------------------------------------
-- tenants
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenants (
    id              TEXT PRIMARY KEY,
    clerk_org_id    TEXT NOT NULL UNIQUE,
    slug            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    plan            TEXT,
    status          TEXT NOT NULL DEFAULT 'active',
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ---------------------------------------------------------------------------
-- tenant_memberships
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant_memberships (
    id                      TEXT PRIMARY KEY,
    tenant_id               TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    user_id                 TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    clerk_membership_id     TEXT NOT NULL UNIQUE,
    role                    TEXT NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'active',
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, user_id)
);

CREATE INDEX IF NOT EXISTS tenant_memberships_user_idx ON tenant_memberships (user_id);

ALTER TABLE tenant_memberships ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_memberships_tenant_isolation ON tenant_memberships;
CREATE POLICY tenant_memberships_tenant_isolation ON tenant_memberships
    USING (tenant_id = current_setting('app.tenant_id', true));

-- ---------------------------------------------------------------------------
-- account_memberships  (Phase-1 schema only; enforced in Phase 3)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS account_memberships (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    account_id      TEXT NOT NULL,
    user_id         TEXT NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    access_level    TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, account_id, user_id)
);

ALTER TABLE account_memberships ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS account_memberships_tenant_isolation ON account_memberships;
CREATE POLICY account_memberships_tenant_isolation ON account_memberships
    USING (tenant_id = current_setting('app.tenant_id', true));

-- ---------------------------------------------------------------------------
-- tenant_entitlements (Phase-1 schema only; enforced in Phase 3)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS tenant_entitlements (
    id                  TEXT PRIMARY KEY,
    tenant_id           TEXT NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    entitlement_key     TEXT NOT NULL,
    enabled             BOOLEAN NOT NULL DEFAULT FALSE,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (tenant_id, entitlement_key)
);

ALTER TABLE tenant_entitlements ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS tenant_entitlements_tenant_isolation ON tenant_entitlements;
CREATE POLICY tenant_entitlements_tenant_isolation ON tenant_entitlements
    USING (tenant_id = current_setting('app.tenant_id', true));

-- ---------------------------------------------------------------------------
-- auth_audit_events (append-only)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS auth_audit_events (
    id              TEXT PRIMARY KEY,
    tenant_id       TEXT,
    user_id         TEXT,
    clerk_user_id   TEXT,
    event_type      TEXT NOT NULL,
    resource_type   TEXT,
    resource_id     TEXT,
    decision        TEXT,
    request_id      TEXT,
    detail          JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS auth_audit_events_tenant_idx
    ON auth_audit_events (tenant_id, created_at DESC);

ALTER TABLE auth_audit_events ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS auth_audit_events_tenant_isolation ON auth_audit_events;
CREATE POLICY auth_audit_events_tenant_isolation ON auth_audit_events
    USING (
        tenant_id IS NULL  -- system-level events are visible to operators
        OR tenant_id = current_setting('app.tenant_id', true)
    );

-- ---------------------------------------------------------------------------
-- clerk_webhook_events (idempotency dedupe)
-- ---------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS clerk_webhook_events (
    id              BIGSERIAL PRIMARY KEY,
    event_id        TEXT NOT NULL UNIQUE,
    event_type      TEXT NOT NULL,
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

COMMIT;
