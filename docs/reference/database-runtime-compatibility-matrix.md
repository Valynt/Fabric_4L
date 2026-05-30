# Runtime Database Compatibility Matrix

This document defines the authoritative per-layer DB bootstrap policy and the split
between local/unit database compatibility and production-readiness validation.

## Compatibility split

| Validation category | Allowed database | Required marker / gate | Scope |
|---|---|---|---|
| Pure unit tests | SQLite is allowed when the test does not assert PostgreSQL-specific behavior | `unit` or another non-production marker | Deterministic local tests for pure logic, model serialization, and compatibility shims |
| Production DB invariants | PostgreSQL only | `postgres_only`, `requires_postgres`, and `production_db_invariant`; run by `make db-production-readiness-gate` | RLS, migrations, constraints, indexes, tenant context hooks, pool/transaction behavior, and production URL policy |
| Static adapter conformance | No live DB required, but must prove production behavior structurally | `contract_static` and `production_db_invariant` | `INTENTIONAL_DB_ADAPTER_BYPASS` modules must retain fail-closed source-level guards |

SQLite compatibility is intentionally **not** production-readiness evidence.  A test
may use SQLite only when it validates pure local/unit behavior that is independent of
PostgreSQL semantics.  Any test that claims coverage for RLS, Alembic migrations,
database constraints, indexes, `SET LOCAL app.tenant_id`, connection pool defaults,
fail-closed tenant behavior, or transaction semantics must live in the PostgreSQL-only
suite and be selected by `db-production-readiness-gate`.

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
| Layer 1 ingestion | `services/layer1-ingestion/src/shared/database.py`; `services/layer1-ingestion/src/layer1_ingestion/shared/database.py` | `postgresql`, `postgres`, `postgresql+asyncpg`, `postgresql+psycopg` | none for runtime production invariants; SQLite only in pure unit tests outside runtime bootstrap | Preferred | Yes (intentional legacy, covered by conformance tests) |
| Layer 2.5 signal refinery | `services/layer2-5-signal-refinery/src/layer2_5_signal_refinery/database.py` | `postgresql`, `postgresql+asyncpg`, `postgresql+psycopg` | `sqlite`, `sqlite+aiosqlite` for pure unit tests only | **Yes** | No |
| Layer 4 agents | `services/layer4-agents/src/database.py`; `services/layer4-agents/src/layer4_agents/database.py` | `postgresql`, `postgres`, `postgresql+asyncpg`, `postgresql+psycopg` | none for runtime production invariants; SQLite only in pure unit tests outside production readiness | Preferred | Yes (intentional local implementation, strict conformance) |
| Layer 5 ground truth | `services/layer5-ground-truth/src/layer5_ground_truth/database.py` | `postgresql`, `postgres`, `postgresql+asyncpg`, `postgresql+psycopg` | `sqlite`, `sqlite+aiosqlite` for pure unit tests only | Preferred | Yes (intentional local implementation, strict conformance) |
| Layer 6 benchmarks | `services/layer6-benchmarks/src/database.py` | n/a (Neo4j driver bootstrap) | n/a | n/a | n/a |

## Conformance marker

Runtime DB modules that intentionally bypass the shared adapter must include:

```python
INTENTIONAL_DB_ADAPTER_BYPASS = True
```

and are required to pass `tests/production_readiness/test_db_adapter_bypass_conformance.py`.
Those conformance tests prove each bypass module still enforces:

1. production URL policy (PostgreSQL-only schemes and no RLS-bypassing superuser roles),
2. transaction-local tenant context via `SET LOCAL app.tenant_id` or `set_config(..., true)`,
3. bounded pool defaults (`pool_size`, `max_overflow`, `pool_pre_ping`, and timeout behavior), and
4. fail-closed tenant behavior when authenticated tenant context is absent.

## Gate contract

Run the database production-readiness gate with:

```bash
make db-production-readiness-gate
```

The gate performs three checks:

1. `scripts/ci/check_db_bootstrap_conformance.py` ensures every runtime DB bootstrap either uses the shared adapter or declares `INTENTIONAL_DB_ADAPTER_BYPASS = True`.
2. `scripts/ci/check_db_production_readiness_split.py` ensures PostgreSQL-only production invariants are not validated solely by SQLite compatibility tests.
3. `pytest tests/production_readiness -m "contract_static or postgres_only"` runs static bypass conformance plus the PostgreSQL-backed suite and fails on skipped tests via `scripts/ci/assert_no_pytest_skips.py`.

A missing PostgreSQL URL is a gate failure, not a skip.  Configure `TEST_DATABASE_URL`
(or `DATABASE_URL`) with a PostgreSQL URL before running production-readiness validation.
