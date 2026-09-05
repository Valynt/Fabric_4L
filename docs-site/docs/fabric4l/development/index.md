---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Development

This section is the engineering onboarding and day-to-day reference for contributors to the Value Fabric (Fabric4L) platform. It covers how to set up the monorepo, how we write and test code, what standards govern each layer, and how the repository is organized so you can find canonical paths quickly.

## What You Will Find Here

| Page | Purpose | Who Needs It |
|------|---------|--------------|
| [Contribution Guide](./contribution-guide.md) | First-time setup, branch naming, commit conventions, PR requirements, and local validation commands | Every new contributor |
| [Coding Standards](./coding-standards.md) | Python and TypeScript/React lint and format rules, layer boundary policies, contract-first development, and error handling | Anyone writing or reviewing code |
| [Testing](./testing.md) | Behavior-first testing philosophy, pytest markers, per-layer test commands, contract tests, security tests, frontend tests, and coverage thresholds | Anyone adding or changing behavior |
| [Repo Strategy](./repo-strategy.md) | Monorepo layout, pnpm-only policy, canonical source-of-truth paths per layer, compatibility debt registry, and migration rules | Platform engineers and architects |

## Quick Start

If this is your first time in the repo, run the canonical setup flow:

```bash
# 1. Enable pnpm (do not use npm or yarn)
corepack enable
corepack prepare pnpm@10.18.1 --activate

# 2. Install JavaScript dependencies
pnpm install --frozen-lockfile

# 3. Install Python service dependencies
make setup

# 4. Start infrastructure and export environment
pnpm env:dev
docker compose -f docker-compose.dev.yml --env-file .env.generated up -d

# 5. Run all Alembic-managed database migrations
make migrate

# 6. Verify everything passes (this is the canonical pre-PR gate)
make verify
```

!!! tip "Prerequisites"
    - Python 3.11+ (any patch release)
    - Node.js >= 22.12.0
    - Docker + Docker Compose
    - `make`

## Development Server Quick Reference

Start only what you need:

| Target | Command | Notes |
|--------|---------|-------|
| Full stack | `pnpm env:dev && docker compose -f docker-compose.dev.yml --env-file .env.generated up` | Frontend + all backend services |
| Frontend only | `pnpm dev:web` | Vite on port 3001 with mock API |
| Frontend + live backend | `pnpm --dir apps/web run dev:live` | Requires proxy envs |
| Layer 1 | `pnpm dev:layer1` | Port 8001 |
| Layer 2 | `pnpm dev:layer2` | Port 8002 |
| Layer 3 | `pnpm dev:layer3` | Port 8003 |
| Layer 4 | `pnpm dev:layer4` | Port 8004 |
| Layer 5 | `pnpm dev:layer5` | Port 8005 |
| Layer 6 | `pnpm dev:layer6` | Port 8006 |

## How to Navigate This Section

- **Setting up locally?** Start with the [Contribution Guide](./contribution-guide.md). It contains the first-time setup steps, pre-commit hooks, and the exact commands to run before pushing.
- **Writing a new endpoint or agent tool?** Read [Coding Standards](./coding-standards.md) first, then [Testing](./testing.md). Coding Standards covers layer boundaries, contract-first rules, and provider-agnostic agent code. Testing covers how to prove your behavior with the right markers and coverage.
- **Changing a database model or migration?** Check [Repo Strategy](./repo-strategy.md) for canonical paths and the migration rules, then run `make check-migration-heads` before pushing.
- **Debugging a CI failure?** Use the command tables in [Contribution Guide](./contribution-guide.md) and [Testing](./testing.md) to reproduce the exact gate locally. CI job names map directly to local `make` and `pnpm` commands.
- **Adding a new dependency?** See [Repo Strategy](./repo-strategy.md) for the pnpm-only policy and runtime version matrix.

## Layer Overview

Value Fabric uses a six-layer pipeline. When you change code, preserve the responsibility of the layer you are in.

| Layer | Port | Responsibility |
|-------|------|----------------|
| Layer 1 — Ingestion | 8001 | Playwright crawling, Celery jobs, Redis queues, compliance-aware ingestion |
| Layer 2 — Extraction | 8002 | Pydantic v2 extraction, LLM extraction, RDF/OWL, provenance |
| Layer 3 — Knowledge | 8003 | Neo4j, GraphRAG, hybrid retrieval, pgvector, subgraph APIs |
| Layer 4 — Agents | 8004 | LangGraph workflows, ROI calculator, checkpoints, agent orchestration |
| Layer 5 — Ground Truth | 8005 | TruthObject validation, maturity ladder, evidence-backed claims |
| Layer 6 — Benchmarks | 8006 | Peer comparison, statistical validation, datasets, benchmark policies |

## Essential Validation Commands

```bash
# Full pre-PR gate
make verify

# Fast checks (structural + contracts)
make verify-structure

# Single layer test
make test-layer4

# Contract tests (no live services needed)
make contract-tests

# Security smoke
make security-smoke

# Frontend checks
pnpm --dir apps/web run test
pnpm --dir apps/web run lint
pnpm --dir apps/web run typecheck
```

!!! warning "Run `make verify` before every PR"
    `make verify` is the canonical broad local gate. It is cheaper to catch issues locally than to wait for the full CI pipeline.

## Source of Truth

This documentation is authoritative for local development workflows. If a command here diverges from the repo, the repo wins. When you find a drift, fix the docs in the same PR that changes the behavior.

## Related References

- [`docs/development/BUILD_SYSTEM.md`](https://github.com/BBB/Fabric_4L/blob/main/docs/development/BUILD_SYSTEM.md) — Canonical build system and command hierarchy
- [`docs/development/COMMANDS.md`](https://github.com/BBB/Fabric_4L/blob/main/docs/development/COMMANDS.md) — Complete command inventory
- [`docs/development/DISCOVERY_MAP.md`](https://github.com/BBB/Fabric_4L/blob/main/docs/development/DISCOVERY_MAP.md) — Route issue types to validation commands and evidence
- [`AGENTS.md`](https://github.com/BBB/Fabric_4L/blob/main/AGENTS.md) — concise AI agent entry point and progressive-disclosure links
- [`DESIGN.md`](https://github.com/BBB/Fabric_4L/blob/main/DESIGN.md) — Frontend design system and UX governance
- [`docs/governance/behavior-first-testing.md`](https://github.com/BBB/Fabric_4L/blob/main/docs/governance/behavior-first-testing.md) — Testing philosophy and readiness ladder
