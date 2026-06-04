# Test Suite Guide

## Quick Reference

### Fast path — no infrastructure required
```bash
# First-class tenant isolation gate
pnpm test:isolation

# Marker-based tenant isolation selection
pytest -m tenant_isolation -v --tb=short
```

### Exclude infrastructure-dependent tests
```bash
# Run everything that does not need live Postgres/Redis/Neo4j
pytest tests/ -m "not requires_infra"
```

### Chaos / performance tests only
```bash
pytest tests/chaos tests/performance -v
```

### Full infrastructure-backed suite
Requires the Docker Compose dev stack:
```bash
docker compose -f docker-compose.dev.yml up -d
pytest tests/ -m "requires_infra or chaos or performance or slow"
```

## Markers

| Marker | Meaning |
|---|---|
| `unit` | Fast, no I/O |
| `contract` | OpenAPI / schema contract tests |
| `security` | OWASP / tenant-boundary tests |
| `tenant_isolation` | First-class tenant isolation gate coverage |
| `tenant_boundary` | Cross-tenant isolation regression |
| `chaos` | Failure-mode / degradation tests |
| `performance` | Connection pool / SLO benchmarks |
| `slow` | >1 s or heavy deps |
| `requires_postgres` | Needs live PostgreSQL |
| `requires_redis` | Needs live Redis |
| `requires_neo4j` | Needs live Neo4j |
| `requires_infra` | Umbrella: any live infrastructure dependency |
| `quarantine` | Temporarily isolated (stale imports, etc.) |

## Infrastructure skip behavior

- **Locally**: tests skip with `[INFRA_GATE:...]` messages when services are down.
- **CI** (`CI=true`): missing required infrastructure is a hard failure.

## Layer 3 import-path note

A subset of `tests/layer3/` and `tests/security/` tests that import directly from `value_fabric.layer3.*` route modules are currently skipped via `[LAYER3_IMPORT_PATH]` because those modules use direct `logging_config` imports that conflict with the multi-layer `sys.path` layout. They are **not** skipped because of missing Postgres/Redis/Neo4j.
