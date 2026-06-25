-- Layer 6 Benchmark Service — VMRT trace persistence

CREATE CONSTRAINT vmrt_trace_tenant_trace_id IF NOT EXISTS
FOR (t:VMRTTrace)
REQUIRE (t.trace_id, t.tenant_id) IS UNIQUE;

CREATE CONSTRAINT vmrt_trace_tenant_id_exists IF NOT EXISTS
FOR (t:VMRTTrace)
REQUIRE t.tenant_id IS NOT NULL;

CREATE INDEX vmrt_trace_status IF NOT EXISTS
FOR (t:VMRTTrace)
ON (t.status);
