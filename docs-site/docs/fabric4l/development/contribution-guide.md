---
status: active
last_reviewed: 2026-06-07
owner: platform-team
---

# Contribution Guide

This guide covers everything you need to get the Value Fabric monorepo running locally, create a branch, validate your changes, and open a PR that passes CI on the first try.

## Prerequisites

| Tool | Minimum Version | Purpose |
|------|-----------------|---------|
| Python | 3.11+ | Backend services, pytest, migration tooling |
| Node.js | 22.22.2 | Frontend build system, pnpm workspaces, GitHub Actions parity |
| pnpm | 10.18.1 | Package manager (pnpm-only; npm and yarn are prohibited) |
| Docker + Docker Compose | Latest stable | PostgreSQL, Redis, Neo4j, Keycloak local stacks |
| make | GNU Make | Canonical build system interface |

!!! warning "No npm or yarn"
    This monorepo is **pnpm-only**. Using `npm install`, `npm ci`, or `yarn install` will fail the package-manager policy gate in CI.

## First-Time Setup

Run these steps once after cloning:

```bash
# 1. Log in to Infisical (recommended for secret management)
infisical login

# 2. Pin Python to the 3.11 series (optional if python3.11 is already on PATH)
pyenv install --skip-existing "$(pyenv latest -k 3.11)"
pyenv local 3.11

# 3. Enable pnpm via corepack
corepack enable
corepack prepare pnpm@10.18.1 --activate

# 4. Install frontend dependencies
pnpm install --frozen-lockfile

# 5. Install Python service dependencies into the pytest pipx venv
make setup

# 6. Start infrastructure and export environment
pnpm env:dev
docker compose -f docker-compose.dev.yml --env-file .env.generated up -d

# 7. Run all Alembic-managed database migrations
make migrate

# 8. Verify everything passes (this is the canonical pre-PR gate)
make verify
```

!!! tip "One-command bootstrap"
    If you prefer, run `make bootstrap` for the repo's single-command setup path, which includes Infisical-assisted environment export where configured.

## Development Servers

Start only what you need:

| Target | Command | Notes |
|--------|---------|-------|
| Full stack (with Infisical) | `pnpm env:dev && docker compose -f docker-compose.dev.yml --env-file .env.generated up` | Includes frontend + all backend services |
| Frontend only (mock API) | `pnpm dev:web` | Vite on port 3001 |
| Frontend + live backend | `pnpm --dir apps/web run dev:live` | Requires `VITE_API_BASE_URL` and proxy envs |
| Layer 1 only | `pnpm dev:layer1` | Uvicorn reload on port 8001 |
| Layer 2 only | `pnpm dev:layer2` | Uvicorn reload on port 8002 |
| Layer 3 only | `pnpm dev:layer3` | Uvicorn reload on port 8003 |
| Layer 4 only | `pnpm dev:layer4` | Uvicorn reload on port 8004 |
| Layer 5 only | `pnpm dev:layer5` | Uvicorn reload on port 8005 |
| Layer 6 only | `pnpm dev:layer6` | Uvicorn reload on port 8006 |

## Branch Naming

There is no enforced regex pattern, but use descriptive, slash-separated names:

```
feat/layer4-checkpoint-resume
fix/tenant-isolation-l3
refactor/l2-pydantic-v2-migration
docs/api-versioning-policy
```

## Commit Format

Follow [Conventional Commits](https://www.conventionalcommits.org/) where possible:

```
feat(layer4): add checkpoint resume for LangGraph workflows

- Serialize thread state to PostgreSQL
- Add resume endpoint with tenant scoping

Co-authored-by: Ona <no-reply@ona.com>
```

Co-author AI-assisted commits so attribution is preserved in history.

## Pre-Commit Hooks

Install hooks once after setup:

```bash
pre-commit install
```

Hooks run automatically on commit and include:

| Hook | Purpose |
|------|---------|
| gitleaks | Block accidental secret commits |
| black | Python formatting |
| ruff | Python linting and import sorting |
| prettier | Frontend formatting |

Run hooks manually across all files:

```bash
pre-commit run black --all-files
pre-commit run ruff --all-files
```

## Running Tests Locally

### Backend

```bash
# All backend layers
make test

# Single layer
make test-layer1
make test-layer2
make test-layer3
make test-layer4
make test-layer5
make test-layer6

# Fast tests only (exclude slow and e2e)
make test-fast

# Contract + architecture tests (no live services)
make contract-tests

# Security and tenant isolation
make security-test
make security-test-isolation

# Backend-integrated validation (requires running stack)
make test-backend-integrated-validation

# Release smoke (boots full L1–L6 stack)
make test-backend-integrated-release-smoke
```

### Frontend

```bash
# Unit/component tests
pnpm --dir apps/web run test

# Watch mode
pnpm --dir apps/web run test:watch

# Coverage
pnpm --dir apps/web run test:coverage

# Contract tests
pnpm --dir apps/web run test:contracts

# E2E (mocked, Playwright)
pnpm --dir apps/web run test:e2e

# E2E against live backend
pnpm --dir apps/web run test:e2e:live

# Accessibility
pnpm --dir apps/web run test:a11y:components
pnpm --dir apps/web run test:a11y:pages
```

## Lint and Typecheck

### Python

```bash
# All layers
make lint
make typecheck

# Single layer
make lint-layer4
make typecheck-layer4
```

### Frontend

```bash
pnpm --dir apps/web run lint
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run format
```

## PR Requirements

### Required CI Checks

All PRs targeting `main` must pass the checks defined in `.github/workflows/pr-checks.yml`:

| Job | What It Validates |
|-----|-------------------|
| `structural-preflight` | Import topology, Python contract lint, frontend root policy, package-manager enforcement |
| Per-layer checks | Lint, typecheck, tests, and coverage per layer (L1–L6) |
| `contract-checks` | OpenAPI drift detection and related contract coverage |
| `production-readiness-gate` | Canonical gate: `make production-readiness-gate` |

### PR Body Sections

Fill in every section from `.github/pull_request_template.md`:

- **Governance Impact** — contract shape, tenant isolation, compatibility shim impact
- **Release & Policy Checklist** — contracts updated, API versioning, DR runbooks
- **Validation** — confirm `make verify` passed; `make evals` for agent/prompt changes

!!! warning "Do not skip `make verify`"
    `make verify` is the canonical broad local PR gate. Run it before pushing. It is cheaper to catch issues locally than to wait for CI.

## Environment and Secrets

- Never commit real secrets.
- Add new environment variables to `.env.example` with safe defaults.
- Use Infisical for local dev secret injection (`infisical run`).
- Use `.env.generated` (gitignored) for temporary Infisical exports.

!!! danger "Dev Auth Bypass Flags"
    The following flags are for **local development only** and will cause startup failure in production-like environments:

    - `DEV_AUTH_BYPASS=true`
    - `ALLOW_DEV_AUTH_BYPASS=true`
    - `AUTH_BYPASS_ENABLED=true`
    - `ALLOW_INSECURE_DEV_AUTH_BYPASS=true`

## Validation Checklist Before PR

- [ ] `make verify` passes locally
- [ ] `pnpm install --frozen-lockfile` is clean
- [ ] Pre-commit hooks pass
- [ ] New behavior has tests (allowed + denied + failure mode)
- [ ] Cross-tenant isolation is tested if touching data access
- [ ] OpenAPI contracts are updated if API behavior changed
- [ ] Frontend types are regenerated if backend schemas changed (`pnpm run generate:api`)
- [ ] Documentation is updated for public API or operational changes
