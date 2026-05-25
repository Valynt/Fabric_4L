-- Layer 6 Benchmark Service — Ownership mode constraints

CREATE CONSTRAINT benchmark_dataset_ownership_mode_exists IF NOT EXISTS
FOR (d:BenchmarkDataset)
REQUIRE d.ownership_mode IS NOT NULL;

CREATE CONSTRAINT benchmark_dataset_tenant_id_exists IF NOT EXISTS
FOR (d:BenchmarkDataset)
REQUIRE d.tenant_id IS NOT NULL;
