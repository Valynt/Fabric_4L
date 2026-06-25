-- Layer 6 Benchmark Service - ValueOS metric governance metadata

CREATE INDEX benchmark_metric_value_type IF NOT EXISTS
FOR (m:BenchmarkMetric)
ON (m.value_type);

CREATE INDEX benchmark_metric_lifecycle_stage IF NOT EXISTS
FOR (m:BenchmarkMetric)
ON (m.lifecycle_stage);

CREATE INDEX benchmark_metric_governance_status IF NOT EXISTS
FOR (m:BenchmarkMetric)
ON (m.governance_status);

CREATE INDEX benchmark_metric_vintage IF NOT EXISTS
FOR (m:BenchmarkMetric)
ON (m.vintage);
