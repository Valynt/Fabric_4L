# Layer 6: Benchmark Service
> Routing/versioning reference: see the canonical [Service Routing and API Version Matrix](../../docs/reference/service-routing-and-api-version-matrix.md).

> Runtime path governance: per [ADR-027](../../docs/explanations/adr/ADR-027-shim-removal.md), net-new Layer 6 logic must go to `services/layer6-benchmarks/src/`. The legacy `value_fabric/layer6/` namespace has been removed. See [`docs/reference/layer-runtime-path-governance.md`](../../docs/reference/layer-runtime-path-governance.md).

Standalone service for comparative intelligence and peer benchmarking.

## Overview

The Benchmark Service provides curated datasets for peer comparison and statistical validation. Unlike Ground Truth (validated claims), benchmarks are reference datasets for comparative analysis.

## Features

- **Benchmark Dataset Management**: By industry and segment
- **Peer Comparison APIs**: Percentile ranking against peers
- **Range Validation**: Sanity checks against benchmark ranges
- **Manufacturing Reference Dataset**: Included as seed data

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health` | Process liveness only (no dependency checks) |
| GET | `/ready` | Dependency readiness (DB/connectivity/config checks) |
| GET | `/v1/benchmarks/datasets` | List datasets |
| GET | `/v1/benchmarks/datasets/{id}` | Get dataset details |
| POST | `/v1/benchmarks/compare` | Peer comparison |
| POST | `/v1/benchmarks/validate` | Range validation |
| GET | `/v1/benchmarks/industries` | List industries |

## Quick Start

```bash
# Run with Docker
docker build -t layer6-benchmarks .
docker run -p 8006:8006 layer6-benchmarks

# Or run locally
cd services/layer6-benchmarks
python -m uvicorn src.api.main:app --port 8006
```

## Integration

Layer 6 integrates with Layer 4 Agents via the `IBenchmarkClient` interface (see `layer4-agents/src/interfaces/benchmark_client.py`).

## Source ownership

Canonical runtime location for Layer 6 implementation logic: **`services/layer6-benchmarks/src/`** (per [ADR-027](../../docs/explanations/adr/ADR-027-shim-removal.md)).

`value_fabric/layer6/` has been removed. It must not be restored, resolve `value_fabric.layer6.*` imports to the service tree, append paths, or contain implementation files. CI gates (`scripts/ci/check_layer6_imports.py`, `scripts/ci/check_stale_namespace_dirs.py`) reject regressions.

Where wrapper files still exist under `services/layer6-benchmarks/src/` to preserve historical import paths, they must remain byte-aligned thin re-exports declared in `scripts/mirrored_files.json` and enforced by:

- `scripts/check_mirrored_files.py`
- `scripts/ci/check_layer6_wrapper_drift.py`

Use canonical imports (`layer6_benchmarks.*`) for all new Layer 6 runtime code.

Contributor placement rule:

- Add or change Layer 6 runtime logic under `services/layer6-benchmarks/src/`.
- Do not add files to `value_fabric/layer6/`; the namespace has been removed.
- Mirrored compatibility wrappers (if registered in `scripts/mirrored_files.json`) must stay aligned to the generated re-export template.

This section previously recommended the opposite; treat the rule above as authoritative.

Targeted validation for wrapper drift:

```bash
python scripts/ci/check_layer6_wrapper_drift.py
python scripts/check_mirrored_files.py
pytest tests/ci/test_mirrored_files_drift_guard.py
```


## Dependency locking

- Canonical Python lock artifact for this service: `uv.lock` (source of truth).
- Regenerate lock state after dependency edits in `pyproject.toml`:

```bash
cd services/layer6-benchmarks
uv lock
uv export --locked --no-dev --format requirements-txt -o requirements.lock
```

- CI and Docker builds must consume `uv.lock` deterministically (`uv sync --locked` or equivalent).


## Migration reproducibility reference

- `docs/reference/migration-reproducibility-invariants.md` (mandatory migration invariants and incident-state reconstruction)

## Operational observability

See `docs/operations/layer6/observability.md` for Layer 6 metrics, SLO indicators, and troubleshooting.

## Health and readiness semantics

- `/health` is a **lightweight liveness probe**: it reports whether the process is up and able to serve HTTP. It must not perform expensive or flaky downstream checks.
- `/ready` is a **readiness probe**: it validates critical dependencies and startup invariants such as database connectivity, graph connectivity, and required runtime configuration.
- `/ready` evaluates these deterministic checks:
  - `config`: fail-fast startup configuration validation
  - `neo4j`: graph connectivity health
  - `benchmark_store`: repository availability plus seeded benchmark presence
  - `startup`: whether canonical startup completed without a recorded dependency failure
- Deterministic failure behavior: if any critical readiness dependency fails, `/ready` returns HTTP `503` with a stable `{"status":"not_ready", ...}` payload including per-check status; `/health` remains `200` unless the process itself is unhealthy.
- Alerting expectations:
  - Page on sustained `/ready` failures because the service should be removed from traffic until dependencies recover.
  - Treat `/health` failures as process-level incidents; investigate restart loops or repeated liveness failures immediately.
  - Do not page solely because `/health` remains green during a dependency outage; that split is expected by design.

## Environment variables (Layer 6)

The Layer 6 service uses a centralized Pydantic settings module at `services/layer6-benchmarks/src/layer6_benchmarks/settings.py`, with compatibility-only service-local import surfaces under `services/layer6-benchmarks/src/` where retained. Startup calls `validate_layer6_startup_settings()` at import time so missing or invalid critical configuration fails closed before the API begins serving traffic.

Use the service-local template at `services/layer6-benchmarks/.env.example` for local bootstrapping and mirror the same variables in deployment secrets/config maps.

| Variable | Required | Default | Example | Security notes |
|---|---|---|---|---|
| `ENVIRONMENT` | Optional | `development` | `production` | `staging` and `production` enable strict fail-closed validation. |
| `APP_ENV` | Optional | none | `staging` | Compatibility alias for environment detection; keep aligned with `ENVIRONMENT` if used. |
| `TESTING` | Optional | `false` | `true` | Test-only toggle; do not enable in shared deployments. |
| `AUTH_REQUIRED` | Optional | `true` | `true` | Must stay `true` in `staging`/`production`. |
| `PORT` | Optional | `8006` | `8006` | Must match `API_PORT` when both are set. |
| `API_PORT` | Optional | `8006` | `8006` | Keep identical to `PORT` to avoid drift between launcher and settings. |
| `API_HOST` | Optional | `0.0.0.0` | `0.0.0.0` | Bind address only; not secret. |
| `LOG_LEVEL` | Optional | `INFO` | `WARNING` | Operational only; avoid verbose debug logging in production. |
| `LAYER6_SERVICE_NAME` | Optional | `layer6-benchmarks` | `layer6-benchmarks` | Used in startup metadata; not secret. |
| `LAYER6_VERSION` | Optional | `dev` | `1.4.2` | Build metadata only; not secret. |
| `LAYER6_BUILD_SHA` | Optional | `unknown` | `abc123def456` | Build metadata only; not secret. |
| `DATABASE_URL` | Required | none | `postgresql+asyncpg://layer6_app:***@postgres:5432/benchmarks?sslmode=verify-full` | Must target PostgreSQL. In `staging`/`production`, `sslmode` is required and must be `require`, `verify-ca`, or `verify-full`. |
| `DATABASE_URL_SYNC` | Required | none | `postgresql+psycopg2://layer6_app:***@postgres:5432/benchmarks?sslmode=verify-full` | Required for migrations/admin tooling. Apply the same TLS rules as `DATABASE_URL`. |
| `DB_HOST` | Optional | none | `postgres.value-fabric.svc.cluster.local` | Deployment metadata only; treat as infrastructure inventory, not auth. |
| `DB_PORT` | Optional | none | `5432` | Deployment metadata only; integer validation enforced when set. |
| `DB_NAME` | Optional | none | `benchmarks` | Deployment metadata only; keep consistent with DB URLs. |
| `DB_USER` | Optional | none | `layer6_app` | Deployment metadata only; do not use superuser credentials in shared environments. |
| `DB_PASSWORD` | Optional | none | `<vault-managed-secret>` | Sensitive deployment metadata; never commit. |
| `NEO4J_URI` | Required | none | `neo4j+s://xxxx.databases.neo4j.io` | In `staging`/`production`, startup requires managed Neo4j Aura over `neo4j+s://`. |
| `NEO4J_USER` | Optional | `neo4j` | `layer6_reader` | Non-secret identifier; use least-privilege accounts. |
| `NEO4J_PASSWORD` | Required | none | `<vault-managed-secret>` | Secret; minimum 12 chars and no default password values. |
| `NEO4J_DATABASE` | Optional | `neo4j` | `neo4j` | Database name only; not secret. |
| `NEO4J_MAX_POOL_SIZE` | Optional | `50` | `25` | Integer range validation enforced. |
| `JWT_SECRET` | Required | none | `<openssl rand -hex 32>` | Secret; minimum 32 chars and weak placeholder values are rejected. |
| `API_KEY_HMAC_SECRET` | Required | none | `<openssl rand -hex 32>` | Secret; minimum 32 chars and weak placeholder values are rejected. |
| `SERVICE_AUTH_SECRET` | Required | none | `<openssl rand -hex 32>` | Secret; minimum 32 chars and weak placeholder values are rejected. |
| `LAYER3_API_KEY` | Required | none | `<vault-managed-secret>` | Secret used for inter-service auth; missing values fail startup. |
| `LAYER5_API_KEY` | Required | none | `<vault-managed-secret>` | Secret used for inter-service auth; missing values fail startup. |
| `ALLOW_INSECURE_DEV_AUTH_BYPASS` | Optional | `false` | `true` | Local-dev only; rejected in `staging`/`production`. |
| `DEV_AUTH_BYPASS` | Optional | `false` | `true` | Test-only; rejected in `staging`/`production`. |
| `AUTH_BYPASS_ENABLED` | Optional | `false` | `true` | Local-dev compatibility flag only; rejected in `staging`/`production`. |
| `JWT_FALLBACK_TO_QUERY_PARAM` | Optional | `false` | `true` | Test-only fallback; rejected in `staging`/`production`. |
| `ALLOW_EPHEMERAL_ENCRYPTION` | Optional | `false` | `true` | Local-dev only; rejected in `staging`/`production`. |
| `ALLOW_DEV_AUTH_BYPASS` | Optional | none | `I_UNDERSTAND_RISK` | Legacy explicit opt-in token; rejected in `staging`/`production`. |
