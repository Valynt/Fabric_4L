---
owner: platform-team
status: active
last_reviewed: 2026-06-07
---

# Links

This page is a curated directory of internal source-of-truth files and external references. Use it to resolve "where does X live?" questions quickly.

## Internal source-of-truth files

### Architecture and governance

| Document | Purpose | Path |
|---|---|---|
| Agent Entry Point | Shared package map and links to scoped agent guidance | `AGENTS.md` |
| Design System | Frontend UX, component, and layout governance | `DESIGN.md` |
| Platform Contract | Tenant context, middleware, and agent output shape | `docs/contract.md` |
| Behavior-First Testing | Canonical testing strategy and readiness ladder | `docs/governance/behavior-first-testing.md` |
| Compatibility Debt Registry | Tracking for legacy shims and redirects | `docs/governance/compatibility-debt-registry.md` |
| Discovery Map | Issue-to-implementation routing for source-of-truth files | `docs/development/DISCOVERY_MAP.md` |
| Build System | When to use `make`, `pnpm`, or Python CI runners | `docs/development/BUILD_SYSTEM.md` |
| Commands Reference | Every public root script and Makefile target | `docs/development/COMMANDS.md` |

### Configuration and baselines

| Document | Purpose | Path |
|---|---|---|
| pytest configuration | Markers, test paths, timeouts, and profiles | `pytest.ini` |
| Behavior contract baseline | Ratchet baseline (32 capabilities, 10 domains) | `config/ci/behavior_contract_baseline.json` |
| Readiness waivers | Skip/xfail waiver register with owners and expirations | `config/ci/behavior_readiness_waivers.yaml` |
| Pre-commit hooks | gitleaks, black, ruff, prettier | `.pre-commit-config.yaml` |
| Environment template | All required env vars with safe defaults | `.env.example` |
| Required status checks | CI checks that must pass for `main` | `config/ci/required-status-checks.json` |

### Runtime source-of-truth paths

| Layer | Runtime package | API routes |
|---|---|---|
| L1 Ingestion | `services/layer1-ingestion/src/layer1_ingestion/` | `services/layer1-ingestion/src/layer1_ingestion/api/routes/` |
| L2 Extraction | `services/layer2-extraction/src/layer2_extraction/` | `services/layer2-extraction/src/layer2_extraction/api/routes/` |
| L3 Knowledge | `services/layer3-knowledge/src/` | `services/layer3-knowledge/src/api/routes/` |
| L4 Agents | `services/layer4-agents/src/layer4_agents/` | `services/layer4-agents/src/api/routes/` |
| L5 Ground Truth | `services/layer5-ground-truth/src/layer5_ground_truth/` | `services/layer5-ground-truth/src/layer5_ground_truth/api/` |
| L6 Benchmarks | `services/layer6-benchmarks/src/layer6_benchmarks/` | `services/layer6-benchmarks/src/layer6_benchmarks/api/routes/` |
| API Gateway | `services/api/` | `services/api/` |
| Shared library | `packages/shared/src/value_fabric/shared/` | — |

### Contract artifacts

| Artifact | Purpose | Path |
|---|---|---|
| OpenAPI specs | Source of truth for API contracts | `contracts/openapi/` |
| JSON Schemas | Schema definitions for agent outputs and tools | `contracts/jsonschema/` |
| Tool manifests | Agent tool definitions and versions | `contracts/tool-manifests/` |
| Behavior contract | Capability registry (allowed + denied + failure mode) | `contracts/behavior-contract.yaml` |

### Test suite directories

| Suite | Purpose | Path |
|---|---|---|
| Contract tests | Cross-layer API and schema contracts | `tests/contract/` |
| Security tests | OWASP, tenant boundary, auth | `tests/security/` |
| Backend integrated | Full live-stack validation | `tests/backend_integrated/` |
| Architecture tests | Import topology, module sentinels | `tests/arch/` |
| Audit tests | Audit log emission and tamper resistance | `tests/audit/` |
| Abuse tests | Quotas, throttling, replay | `tests/abuse/` |
| Chaos tests | Failure injection and resilience | `tests/chaos/` |
| Production readiness | Release, recovery, reliability | `tests/production_readiness/` |
| Frontend behavior | Component and hook behavior contracts | `apps/web/src/**/*.behavior.test.*` |
| Frontend E2E | Playwright journey tests | `apps/web/e2e/behaviors/` |

## External references

### Frameworks and libraries

| Technology | Reference |
|---|---|
| MkDocs Material | <https://squidfunk.github.io/mkdocs-material/> |
| FastAPI | <https://fastapi.tiangolo.com/> |
| Pydantic v2 | <https://docs.pydantic.dev/latest/> |
| Neo4j Python Driver | <https://neo4j.com/docs/python-manual/current/> |
| SQLAlchemy | <https://docs.sqlalchemy.org/en/20/> |
| Alembic | <https://alembic.sqlalchemy.org/en/latest/> |
| Celery | <https://docs.celeryq.dev/en/stable/> |
| pytest | <https://docs.pytest.org/en/stable/> |
| Playwright | <https://playwright.dev/> |
| LangGraph | <https://langchain-ai.github.io/langgraph/> |
| TanStack Query | <https://tanstack.com/query/latest/> |
| React | <https://react.dev/> |
| Vite | <https://vitejs.dev/> |
| Tailwind CSS | <https://tailwindcss.com/> |
| shadcn/ui | <https://ui.shadcn.com/> |

### Infrastructure and security

| Technology | Reference |
|---|---|
| PostgreSQL | <https://www.postgresql.org/docs/current/index.html> |
| Redis | <https://redis.io/docs/latest/> |
| Keycloak | <https://www.keycloak.org/documentation.html> |
| Infisical | <https://infisical.com/docs/cli/overview> |
| OWASP Top 10 | <https://owasp.org/www-project-top-ten/> |

## Quick reference card

### Most-visited paths

```text
# Setup and validation
make setup
make verify
make production-readiness-gate

# Testing
pytest -m unit
pytest -m contract_static
pytest -m tenant_boundary
pytest -m security
make contract-tests
make test-backend-integrated-validation

# Frontend
pnpm --dir apps/web run test
pnpm --dir apps/web run test:e2e
pnpm --dir apps/web run build

# Lint and typecheck
make lint
make typecheck
pnpm --dir apps/web run lint
pnpm --dir apps/web run typecheck

# Migrations
make migrate
make check-migration-heads

# Behavior readiness
make check-behavior-contract
pnpm run test:critical-behaviors
make check-behavior-readiness-audit
```

### Key file paths at a glance

```text
AGENTS.md                                    # Concise agent entry point
DESIGN.md                                    # Frontend design system
docs/contract.md                             # Platform contract
docs/governance/behavior-first-testing.md    # Testing governance
pytest.ini                                   # pytest markers and config
config/ci/behavior_contract_baseline.json    # Capability ratchet
config/ci/behavior_readiness_waivers.yaml    # Skip/xfail waivers
contracts/openapi/                           # API contracts
contracts/behavior-contract.yaml             # Behavior capability registry
services/layer{1-6}/src/                     # Runtime source code
tests/contract/                              # Cross-layer contract tests
tests/security/                              # OWASP and tenant boundary tests
apps/web/src/                                # Frontend source
apps/web/e2e/                                # Playwright E2E tests
```

!!! tip "Bookmark this page"
    If you find yourself grepping for "where does X live?", add the answer here. This page is maintained by every team, not just the docs team.

## Related documentation

- [Glossary](glossary.md) — Definitions of platform terms
- [Documentation Rules](documentation-rules.md) — How to write and maintain docs
- `docs/development/DISCOVERY_MAP.md` — Issue-to-implementation routing
