-- ═══════════════════════════════════════════════════════════════
-- Fabric_4L Feature Flags Schema — v1.2.0
-- PostgreSQL 15+
-- ─────────────────────────────────────────────────────────────
-- Tables:
--   feature_flags          — canonical flag definitions
--   feature_flag_overrides — per-tenant / per-tier overrides
--   feature_flag_audit_log — immutable audit trail
-- ─────────────────────────────────────────────────────────────
-- Design decisions:
--   • All tables are in schema `feature_flags` (create if needed).
--   • `feature_flags.default_value` defaults to FALSE (fail-safe).
--   • `feature_flag_overrides.expires_at` enforces time-boxing.
--   • Audit log is append-only; no UPDATE/DELETE permitted.
--   • Indexes support tenant-scoped lookups and time-range scans.
-- ═══════════════════════════════════════════════════════════════

-- ── Schema ────────────────────────────────────────────────────
CREATE SCHEMA IF NOT EXISTS feature_flags;

-- ── Core flags table ──────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feature_flags.feature_flags (
    id              BIGSERIAL PRIMARY KEY,
    flag_key        VARCHAR(128) NOT NULL UNIQUE,
    description     TEXT NOT NULL DEFAULT '',
    -- Fail-safe: new flags default to FALSE
    default_value   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE feature_flags.feature_flags IS
    'Canonical feature flag definitions. flag_key is the stable identifier used by SDKs.';

COMMENT ON COLUMN feature_flags.feature_flags.default_value IS
    'MUST default to FALSE for fail-safe behaviour. Only flip to TRUE after QA sign-off.';

-- ── Overrides table ───────────────────────────────────────────
CREATE TABLE IF NOT EXISTS feature_flags.feature_flag_overrides (
    id          BIGSERIAL PRIMARY KEY,
    flag_id     BIGINT NOT NULL REFERENCES feature_flags.feature_flags(id) ON DELETE CASCADE,
    -- Exactly one of tenant_id or tier should be non-null (enforced by trigger)
    tenant_id   VARCHAR(64) DEFAULT NULL,
    tier        VARCHAR(16) DEFAULT NULL
                CHECK (tier IS NULL OR tier IN ('shared', 'dedicated', 'enterprise')),
    -- If TRUE the feature is fully on; if FALSE fully off for matched scope.
    -- When enabled=TRUE and percentage IS NOT NULL, partial rollout applies.
    enabled     BOOLEAN NOT NULL DEFAULT FALSE,
    percentage  SMALLINT DEFAULT NULL
                CHECK (percentage IS NULL OR (percentage >= 0 AND percentage <= 100)),
    expires_at  TIMESTAMPTZ DEFAULT NULL,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT NOW(),

    -- Ensure exclusivity: either tenant-scoped OR tier-scoped, not both/neither.
    CONSTRAINT chk_scope_exactly_one
        CHECK ((tenant_id IS NOT NULL AND tier IS NULL) OR
               (tenant_id IS NULL AND tier IS NOT NULL))
);

COMMENT ON TABLE feature_flags.feature_flag_overrides IS
    'Tenant-scoped and tier-scoped overrides. Rules in the SDK map 1:1 to rows here.';

COMMENT ON COLUMN feature_flags.feature_flag_overrides.expires_at IS
    'Auto-expiration for temporary rollouts and kill-switch overrides. NULL = no expiry.';

-- ── Audit log (append-only) ───────────────────────────────────
CREATE TABLE IF NOT EXISTS feature_flags.feature_flag_audit_log (
    id          BIGSERIAL PRIMARY KEY,
    flag_id     BIGINT NOT NULL REFERENCES feature_flags.feature_flags(id) ON DELETE CASCADE,
    -- actor format: "user:<uuid>" | "service:<name>" | "system:<event>"
    actor       VARCHAR(128) NOT NULL,
    action      VARCHAR(32) NOT NULL
                CHECK (action IN (
                    'created',
                    'updated',
                    'deleted',
                    'toggled',
                    'override_added',
                    'override_removed',
                    'kill_switch_activated',
                    'kill_switch_expired'
                )),
    old_value   JSONB DEFAULT NULL,
    new_value   JSONB DEFAULT NULL,
    timestamp   TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

COMMENT ON TABLE feature_flags.feature_flag_audit_log IS
    'Immutable audit trail for all flag mutations. No UPDATE or DELETE allowed.';

-- ── Indexes ───────────────────────────────────────────────────

-- Fast lookup by flag key (hot path for both SDKs)
CREATE INDEX IF NOT EXISTS idx_ff_flag_key
    ON feature_flags.feature_flags(flag_key);

-- Tenant-scoped override lookup (primary eval path)
CREATE INDEX IF NOT EXISTS idx_ffo_lookup
    ON feature_flags.feature_flag_overrides(flag_id, tenant_id, tier);

-- Expiration polling for cron job that prunes stale overrides
CREATE INDEX IF NOT EXISTS idx_ffo_expires_at
    ON feature_flags.feature_flag_overrides(expires_at)
    WHERE expires_at IS NOT NULL;

-- Audit log time-range queries (admin UI / compliance)
CREATE INDEX IF NOT EXISTS idx_ffal_flag_timestamp
    ON feature_flags.feature_flag_audit_log(flag_id, timestamp DESC);

-- Actor search (security investigations)
CREATE INDEX IF NOT EXISTS idx_ffal_actor
    ON feature_flags.feature_flag_audit_log(actor, timestamp DESC);

-- ── Auto-update `updated_at` ──────────────────────────────────
CREATE OR REPLACE FUNCTION feature_flags.trigger_set_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS set_timestamp_feature_flags
    ON feature_flags.feature_flags;
CREATE TRIGGER set_timestamp_feature_flags
    BEFORE UPDATE ON feature_flags.feature_flags
    FOR EACH ROW EXECUTE FUNCTION feature_flags.trigger_set_timestamp();

DROP TRIGGER IF EXISTS set_timestamp_overrides
    ON feature_flags.feature_flag_overrides;
CREATE TRIGGER set_timestamp_overrides
    BEFORE UPDATE ON feature_flags.feature_flag_overrides
    FOR EACH ROW EXECUTE FUNCTION feature_flags.trigger_set_timestamp();

-- ── Append-only audit-log policy ──────────────────────────────
CREATE OR REPLACE FUNCTION feature_flags.prevent_audit_mutation()
RETURNS TRIGGER AS $$
BEGIN
    RAISE EXCEPTION 'feature_flag_audit_log is append-only. UPDATE and DELETE are prohibited.';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_no_update ON feature_flags.feature_flag_audit_log;
CREATE TRIGGER audit_no_update
    BEFORE UPDATE ON feature_flags.feature_flag_audit_log
    FOR EACH ROW EXECUTE FUNCTION feature_flags.prevent_audit_mutation();

DROP TRIGGER IF EXISTS audit_no_delete ON feature_flags.feature_flag_audit_log;
CREATE TRIGGER audit_no_delete
    BEFORE DELETE ON feature_flags.feature_flag_audit_log
    FOR EACH ROW EXECUTE FUNCTION feature_flags.prevent_audit_mutation();

-- ── Convenience view: flag + override summary ─────────────────
CREATE OR REPLACE VIEW feature_flags.flag_summary AS
SELECT
    f.id,
    f.flag_key,
    f.description,
    f.default_value,
    f.created_at,
    f.updated_at,
    COUNT(o.id) AS override_count
FROM feature_flags.feature_flags f
LEFT JOIN feature_flags.feature_flag_overrides o
    ON o.flag_id = f.id
    AND (o.expires_at IS NULL OR o.expires_at > NOW())
GROUP BY f.id, f.flag_key, f.description, f.default_value, f.created_at, f.updated_at;

COMMENT ON VIEW feature_flags.flag_summary IS
    'Denormalised view used by the admin list endpoint. Excludes expired overrides.';

-- ── Seed data (examples; remove or gate in production) ────────
-- INSERT INTO feature_flags.feature_flags (flag_key, description, default_value)
-- VALUES
--     ('new-dashboard-v2', 'Next-generation dashboard UI', FALSE),
--     ('layer4-parallel-execution', 'Enable parallel workflow execution in L4', FALSE),
--     ('otel-enhanced-traces', 'Enrich OpenTelemetry spans with flag metadata', FALSE);
