BEGIN;

-- Running upgrade 030 -> 031
-- MIGRATION_REVIEW_REQUIRED: This migration creates tables with RLS policies
-- that are Enterprise-only. Community Edition fallback: skip RLS sections if
-- row_security setting is not available.

CREATE TABLE harness_runs (
    id VARCHAR(64) NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    account_id VARCHAR(255), 
    workflow_type VARCHAR(64) NOT NULL, 
    initiated_by VARCHAR(32) NOT NULL, 
    status VARCHAR(32) NOT NULL, 
    current_state VARCHAR(32) NOT NULL, 
    value_pack_id VARCHAR(255), 
    trace_id VARCHAR(64) NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id)
);

CREATE INDEX ix_harness_runs_tenant_status ON harness_runs (tenant_id, status);

CREATE INDEX ix_harness_runs_tenant_state ON harness_runs (tenant_id, current_state);

CREATE INDEX ix_harness_runs_trace_id ON harness_runs (trace_id);

CREATE TABLE harness_tool_contracts (
    id VARCHAR(64) NOT NULL, 
    tool_id VARCHAR(255) NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    layer VARCHAR(32) NOT NULL, 
    version VARCHAR(32) DEFAULT 'v1' NOT NULL, 
    input_schema_ref VARCHAR(255) NOT NULL, 
    output_schema_ref VARCHAR(255) NOT NULL, 
    side_effect_class VARCHAR(64) NOT NULL, 
    risk_level VARCHAR(32) NOT NULL, 
    requires_tenant_context BOOLEAN DEFAULT 'true' NOT NULL, 
    requires_account_context BOOLEAN DEFAULT 'false' NOT NULL, 
    approval_policy_id VARCHAR(255), 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    CONSTRAINT uq_harness_tool_contracts_tenant_tool UNIQUE (tenant_id, tool_id)
);

CREATE INDEX ix_harness_tool_contracts_tenant_layer ON harness_tool_contracts (tenant_id, layer);

CREATE INDEX ix_harness_tool_contracts_tenant_risk ON harness_tool_contracts (tenant_id, risk_level);

CREATE TABLE harness_human_gates (
    id VARCHAR(64) NOT NULL, 
    run_id VARCHAR(64) NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    gate_type VARCHAR(64) NOT NULL, 
    status VARCHAR(32) DEFAULT 'pending' NOT NULL, 
    decision_by VARCHAR(255), 
    decision_reason TEXT, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    decided_at TIMESTAMP WITH TIME ZONE, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES harness_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_harness_human_gates_run_tenant ON harness_human_gates (run_id, tenant_id);

CREATE INDEX ix_harness_human_gates_tenant_status ON harness_human_gates (tenant_id, status);

CREATE TABLE harness_checkpoints (
    id VARCHAR(64) NOT NULL, 
    run_id VARCHAR(64) NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    state_name VARCHAR(32) NOT NULL, 
    state_payload JSONB DEFAULT '{}' NOT NULL, 
    input_hash VARCHAR(64) NOT NULL, 
    output_hash VARCHAR(64), 
    tool_calls JSONB DEFAULT '[]' NOT NULL, 
    created_at TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES harness_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_harness_checkpoints_run_tenant ON harness_checkpoints (run_id, tenant_id);

CREATE INDEX ix_harness_checkpoints_tenant_state ON harness_checkpoints (tenant_id, state_name);

CREATE INDEX ix_harness_checkpoints_input_hash ON harness_checkpoints (input_hash);

CREATE TABLE harness_trace_events (
    id VARCHAR(64) NOT NULL, 
    trace_id VARCHAR(64) NOT NULL, 
    run_id VARCHAR(64) NOT NULL, 
    tenant_id VARCHAR(255) NOT NULL, 
    account_id VARCHAR(255), 
    workflow_type VARCHAR(64) NOT NULL, 
    from_state VARCHAR(32), 
    to_state VARCHAR(32), 
    status VARCHAR(32), 
    value_pack_id VARCHAR(255), 
    validation_state VARCHAR(32), 
    human_gate_id VARCHAR(64), 
    tool_contract_id VARCHAR(64), 
    event_type VARCHAR(64) DEFAULT 'transition' NOT NULL, 
    metadata JSONB DEFAULT '{}' NOT NULL, 
    timestamp TIMESTAMP WITH TIME ZONE NOT NULL, 
    PRIMARY KEY (id), 
    FOREIGN KEY(run_id) REFERENCES harness_runs (id) ON DELETE CASCADE
);

CREATE INDEX ix_harness_trace_events_run_tenant ON harness_trace_events (run_id, tenant_id);

CREATE INDEX ix_harness_trace_events_tenant_type ON harness_trace_events (tenant_id, event_type);

CREATE INDEX ix_harness_trace_events_trace_id ON harness_trace_events (trace_id);

ALTER TABLE harness_runs ENABLE ROW LEVEL SECURITY;

ALTER TABLE harness_runs FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON harness_runs
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.tenant_id', true)
                );

CREATE POLICY admin_bypass_policy ON harness_runs
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
                WITH CHECK (current_setting('app.tenant_id', true) = '');

ALTER TABLE harness_tool_contracts ENABLE ROW LEVEL SECURITY;

ALTER TABLE harness_tool_contracts FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON harness_tool_contracts
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.tenant_id', true)
                );

CREATE POLICY admin_bypass_policy ON harness_tool_contracts
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
                WITH CHECK (current_setting('app.tenant_id', true) = '');

ALTER TABLE harness_human_gates ENABLE ROW LEVEL SECURITY;

ALTER TABLE harness_human_gates FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON harness_human_gates
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.tenant_id', true)
                );

CREATE POLICY admin_bypass_policy ON harness_human_gates
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
                WITH CHECK (current_setting('app.tenant_id', true) = '');

ALTER TABLE harness_checkpoints ENABLE ROW LEVEL SECURITY;

ALTER TABLE harness_checkpoints FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON harness_checkpoints
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.tenant_id', true)
                );

CREATE POLICY admin_bypass_policy ON harness_checkpoints
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
                WITH CHECK (current_setting('app.tenant_id', true) = '');

ALTER TABLE harness_trace_events ENABLE ROW LEVEL SECURITY;

ALTER TABLE harness_trace_events FORCE ROW LEVEL SECURITY;

CREATE POLICY tenant_isolation_policy ON harness_trace_events
                FOR ALL
                TO PUBLIC
                USING (
                    tenant_id::text = current_setting('app.tenant_id', true)
                )
                WITH CHECK (
                    tenant_id::text = current_setting('app.tenant_id', true)
                );

CREATE POLICY admin_bypass_policy ON harness_trace_events
                FOR ALL
                TO admin_role, system_role
                USING (current_setting('app.tenant_id', true) = '')
                WITH CHECK (current_setting('app.tenant_id', true) = '');

UPDATE alembic_version SET version_num='031' WHERE alembic_version.version_num = '030';

COMMIT;

