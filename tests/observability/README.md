# Observability Contract Suite

## What This Suite Validates

This suite is the centralized fast observability gate for maintained Value Fabric services. It validates request/correlation IDs, structured production logging, critical metrics, trace propagation hooks, error reporting, and sensitive-data redaction without requiring Docker, live services, an OpenTelemetry collector, Redis, PostgreSQL, or Neo4j.

## Production Risks Covered

- Missing request IDs or trace context across service boundaries.
- Logs that are unstructured, hard to correlate, or leak sensitive values.
- RED metrics, service metrics, or error-reporting contracts drifting from dashboards and alerts.
- High-cardinality metric labels that make production monitoring unstable.

## Existing Coverage Aggregated

- `tests/observability/test_structured_logging.py`
- `tests/observability/test_trace_propagation.py`
- `tests/observability/test_metrics_contract.py`
- `tests/observability/test_correlation_ids.py`
- `tests/observability/test_error_reporting.py`
- `tests/observability/test_pii_redaction_in_logs.py`
- `tests/backend_integrated/test_otel_trace_receipt.py`
- `scripts/ci/check_observability_coverage.py`

## Known Gaps

- LIVE_OTEL_COLLECTOR_RECEIPT: live collector receipt remains covered by backend-integrated tests and environment-specific workflows, not this fast suite.
- LIVE_DASHBOARD_RENDERING: dashboard rendering and alert delivery require monitoring infrastructure.

## How To Run

```bash
pytest tests/observability/
pnpm test:observability
pnpm lint:logs
```

## CI Artifact

CI should publish `artifacts/production-readiness/observability/junit.xml`. `pnpm lint:logs` also writes:

```text
artifacts/observability/coverage.json
artifacts/observability/coverage.md
```

