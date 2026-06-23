-- =============================================================================n-- 0002_fabric_api_records_jsonb_bridge.sqln--n-- Bridge-facade table for the standalone API gateway (P0-01).n-- Stores domain records as JSONB payloads with composite key scoping.n--n-- RLS is enabled so that even if a query predicate is bypassed,n-- the database layer fails closed on tenant isolation.n-- =============================================================================n
BEGIN;

CREATE TABLE IF NOT EXISTS fabric_api_records (
    table_name  TEXT NOT NULL,
    id          TEXT NOT NULL,
    tenant_id   TEXT NOT NULL DEFAULT '',
    payload     JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (table_name, tenant_id, id)
);

CREATE INDEX IF NOT EXISTS fabric_api_records_tenant_idx
    ON fabric_api_records (table_name, tenant_id, id);

-- Enable RLS on the bridge table
ALTER TABLE fabric_api_records ENABLE ROW LEVEL SECURITY;

-- Drop and recreate the policy so migrations are idempotent
DROP POLICY IF EXISTS fabric_api_records_tenant_isolation ON fabric_api_records;
CREATE POLICY fabric_api_records_tenant_isolation ON fabric_api_records
    USING (
        tenant_id = current_setting('app.tenant_id', true)
        OR current_setting('app.tenant_id', true) IN ('admin', 'internal', 'system')
    );

COMMIT;
