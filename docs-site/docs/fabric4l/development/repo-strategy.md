---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Repo Strategy

Value Fabric is a monorepo that combines a React frontend, six Python backend layers, shared packages, contracts, infrastructure manifests, and operational documentation. This page explains how the repository is organized, why we enforce a pnpm-only policy, and where canonical code lives.

## Monorepo Structure

```
Fabric_4L/
├── apps/
│   └── web/                          # Frontend (React, Vite, Tailwind, shadcn/ui)
├── services/
│   ├── layer1-ingestion/             # L1: Playwright crawling, Celery, Redis (port 8001)
│   ├── layer2-extraction/            # L2: Pydantic v2 extraction, RDF/OWL (port 8002)
│   ├── layer3-knowledge/             # L3: Neo4j, GraphRAG, pgvector (port 8003)
│   ├── layer4-agents/                # L4: LangGraph, ROI calculator (port 8004)
│   ├── layer5-ground-truth/          # L5: TruthObject validation (port 8005)
│   ├── layer6-benchmarks/            # L6: Peer comparison, statistics (port 8006)
│   └── api/                          # Shared API gateway / auth enforcement
├── packages/
│   ├── shared/                       # Tenant context, base models
│   └── platform-contract/            # Cross-layer contract definitions
├── contracts/
│   ├── openapi/                      # OpenAPI specs (source of truth)
│   ├── jsonschema/                   # JSON Schema definitions
│   └── agent-registry/               # Agent tool and skill contracts
├── tests/
│   ├── contract/                     # Cross-layer contract tests
│   ├── security/                     # OWASP / tenant-boundary tests
│   └── backend_integrated/           # Full-stack tests (requires live services)
├── packs/                            # Domain extension packs
├── docs/                             # Diataxis documentation
├── scripts/ci/                       # CI gate scripts
├── config/ci/                        # CI configuration and baselines
├── k8s/                              # Kubernetes manifests
├── monitoring/                       # Observability configuration
└── .github/workflows/                # CI/CD pipeline definitions
```

## pnpm-Only Policy

This monorepo is **pnpm-only**. npm and yarn are prohibited in canonical runtime and workspace directories.

```bash
# Correct
corepack enable
corepack prepare pnpm@10.18.1 --activate
pnpm install --frozen-lockfile

# Incorrect — will fail CI package-manager policy
npm install
npm ci
yarn install
```

!!! warning "Lockfile hygiene"
    Do not modify `pnpm-lock.yaml` casually. Use `pnpm install --frozen-lockfile` in CI and during local setup. If you need to add a dependency, do so intentionally and commit the updated lockfile.

### Runtime Version Matrix

| Runtime | Canonical Version | Source of Truth |
|---------|-------------------|-----------------|
| Node.js | 22.22.2 | Root `package.json` `engines.node` |
| pnpm | 10.18.1 | Root `package.json` `packageManager` |
| Python | 3.11 | Makefile and GitHub Actions |
| Python container base | `python:3.11.13-slim-bookworm` | Service Dockerfiles |

CI pins Node setup to `22.22.2` and Python governance checks to `3.11`. Update all consumers together when refreshing patch levels.

## Key Directories

### Frontend

| Path | Purpose |
|------|---------|
| `apps/web/` | React application source, routes, components, hooks |
| `apps/web/src/api/generated/` | Generated API client types (do not hand-edit) |

### Backend Services

| Path | Purpose |
|------|---------|
| `services/layer1-ingestion/src/layer1_ingestion/` | L1 runtime package |
| `services/layer2-extraction/src/layer2_extraction/` | L2 runtime package |
| `services/layer3-knowledge/src/` | L3 runtime package |
| `services/layer4-agents/src/layer4_agents/` | L4 runtime package |
| `services/layer5-ground-truth/src/layer5_ground_truth/` | L5 runtime package |
| `services/layer6-benchmarks/src/layer6_benchmarks/` | L6 runtime package |

### Shared Packages

| Path | Purpose |
|------|---------|
| `packages/shared/src/value_fabric/shared/` | Tenant context, base models, auth utilities |
| `packages/platform-contract/` | Cross-layer contract test harness |

## Source-of-Truth Paths per Layer

When modifying a layer, use its canonical runtime path first. Do not introduce duplicate logic in compatibility shims unless required by an active deprecation plan.

### Runtime API Modules

```
services/layer1-ingestion/src/layer1_ingestion/api/routes/
services/layer2-extraction/src/layer2_extraction/api/routes/
services/layer3-knowledge/src/api/routes/
services/layer4-agents/src/api/routes/
services/layer5-ground-truth/src/layer5_ground_truth/api/
services/layer6-benchmarks/src/layer6_benchmarks/api/routes/
```

### Maintained Deployable Services

```
services/layer1-ingestion/
services/layer2-extraction/
services/layer3-knowledge/
services/layer4-agents/
services/layer5-ground-truth/
services/layer6-benchmarks/
services/api/
```

Path governance for canonical vs compatibility locations is documented in `docs/reference/layer-runtime-path-governance.md`.

## Compatibility Debt Registry

The compatibility debt registry tracks shims, deprecated imports, and transitional namespaces. It lives at `docs/governance/compatibility-debt-registry.md` and is enforced in CI.

!!! tip "Check the registry before adding new shims"
    If you need a temporary compatibility layer, register it with a planned removal date. Unregistered shims will fail the legacy debt baseline gate.

Key CI gates related to compatibility:

| Gate | Command |
|------|---------|
| Legacy debt baseline | `make check-legacy-debt` |
| Deprecated namespace imports | `python scripts/ci/check_deprecated_namespace_imports.py --strict` |
| Facade import allowlist | `python scripts/ci/check_value_fabric_facade_imports.py --fail` |
| Shared identity canonical imports | `python scripts/ci/check_shared_identity_canonical_imports.py` |

## Migration Rules

Database migrations are managed per service with Alembic.

### Running Migrations

```bash
# All layers
make migrate

# Per-layer
make migrate-layer1
make migrate-layer2
make migrate-layer4
make migrate-layer5
make migrate-api
```

### Migration Policy

- Do not change models without migrations.
- Do not change migrations without checking existing deployed state.
- Preserve tenant fields in every model.
- Prefer additive migrations; avoid destructive migrations unless explicitly required.
- Include downgrades only if your service's repository convention requires them.

### Migration Validation

```bash
# Validate exactly one Alembic head per service
make check-migration-heads

# Validate rollback policy
make check-migration-rollback-policy

# Read-only migration drift gate
make db-migrate-check

# Migration round-trip test
make check-migration-postgres-roundtrip
```

!!! warning "One head per service"
    CI enforces exactly one Alembic head per service. Merge branches before running `make check-migration-heads` if your feature branch introduced a second head.

## Environment and Configuration

- `.env.example` — committed reference templates with safe defaults (no real secrets)
- `.env.generated` — temporary Infisical export (gitignored)
- `.infisical/` — Infisical project configuration
- `config/ci/` — CI baselines, skip allowlists, and legacy debt config

When adding new environment variables:

1. Add them to `.env.example`.
2. Document them in the relevant README or ops doc.
3. Ensure safe defaults.
4. Avoid insecure production defaults.
5. Align tests and Docker Compose files.

## Drift Prevention

The hardest class of bugs in this system is architectural drift. Always check for drift between:

- Agent logic and UI expectations
- API schemas and frontend types
- Database models and migrations
- OpenAPI specs and route handlers
- Documentation and implementation
- Tenant context and repository methods
- Layer-to-layer payload shapes

When fixing a bug, ask: *"Did this fail because one component changed while another still expects the old contract?"* If yes, fix the alignment, not just the symptom.

## Validation

Run these commands to verify repository health:

```bash
# Structural and contract checks
make verify-structure

# Database readiness
make gate-database

# Full verification
make verify
```
