# Observability Contract Suite

This directory is the centralized fast observability gate for maintained Value Fabric services.

## Scope

The suite covers static and unit-level contracts for:

- `services/api`
- `services/layer1-ingestion`
- `services/layer2-extraction`
- `services/layer3-knowledge`
- `services/layer4-agents`
- `services/layer5-ground-truth`
- `services/layer6-benchmarks`

It validates request/correlation IDs, structured production logging, critical metrics, trace propagation hooks, error reporting, and sensitive-data redaction. It intentionally does not require Docker, live services, an OpenTelemetry collector, Redis, PostgreSQL, or Neo4j.

## Commands

```bash
pytest tests/observability/
pnpm test:observability
pnpm lint:logs
```

`pnpm lint:logs` writes coverage evidence to:

```text
artifacts/observability/coverage.json
artifacts/observability/coverage.md
```

## Runtime Trace Validation

Live trace receipt and collector behavior remain covered by backend-integrated tests such as `tests/backend_integrated/test_otel_trace_receipt.py`. Keep this directory fast and deterministic so it can run on PRs without a live stack.
