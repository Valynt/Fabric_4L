# Runtime Database Compatibility Matrix

This document defines the authoritative per-layer DB bootstrap policy.

## Canonical shared interface

Runtime SQL services should use `value_fabric.shared.database.runtime_adapter.RuntimeDatabaseAdapter` for:

- engine/session creation
- URL-scheme enforcement for production/non-production
- tenant RLS hook (`SET LOCAL app.tenant_id`)
- pool/retry-safe defaults
- health-check semantics (`SELECT 1`)

## Allowed URL drivers

| Service / layer | Runtime DB module | Allowed production drivers | Allowed test-only drivers | Shared adapter required | Bypass allowed |
|---|---|---|---|---|---|
| Layer 1 ingestion | `services/layer1-ingestion/src/shared/database.py` | `postgresql`, `postgresql+asyncpg`, `postgresql+psycopg` | none | Preferred | Yes (intentional legacy, covered by conformance tests) |
| Layer 2.5 signal refinery | `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/database.py` | `postgresql`, `postgresql+asyncpg`, `postgresql+psycopg` | `sqlite`, `sqlite+aiosqlite` | **Yes** | No |
| Layer 4 agents | `services/layer4-agents/src/database.py` | `postgresql`, `postgresql+asyncpg`, `postgresql+psycopg` | none | Preferred | Yes (intentional local implementation, strict conformance) |
| Layer 5 ground truth | `services/layer5-ground-truth/src/layer5_ground_truth/database.py` | `postgresql`, `postgresql+asyncpg`, `postgresql+psycopg` | `sqlite`, `sqlite+aiosqlite` | Preferred | Yes (intentional local implementation, strict conformance) |
| Layer 6 benchmarks | `services/layer6-benchmarks/src/database.py` | n/a (Neo4j driver bootstrap) | n/a | n/a | n/a |

## Conformance marker

Runtime DB modules that intentionally bypass the shared adapter must include:

```python
INTENTIONAL_DB_ADAPTER_BYPASS = True
```

and be covered by conformance tests.
