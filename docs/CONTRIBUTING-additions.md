# CONTRIBUTING.md — Recommended Additions

> **Note:** This file contains sections intended to be appended or merged into the existing `CONTRIBUTING.md`. Do not replace the existing file — integrate these sections where they fit naturally.

---

## Getting Started in 5 Minutes

New to the codebase? Here is the fastest path from zero to a passing build.

### Option A: GitHub Codespaces (Recommended for first-time contributors)

1. Click [![Open in GitHub Codespaces](https://github.com/codespaces/badge.svg)](https://codespaces.new/bmsull560/Fabric_4L)
2. Wait for the post-create setup to complete (~3–5 minutes)
3. Run `make verify` — everything should pass

### Option B: Local Development

```bash
# 1. Clone and enter the repo
git clone https://github.com/bmsull560/Fabric_4L.git
cd Fabric_4L

# 2. Set up the environment
make setup                    # installs deps, starts services, runs migrations
cp .env.example .env        # configure environment variables

# 3. Validate your setup
make verify
```

If `make verify` passes, you are ready to contribute. If it fails, see the **Common Issues** section below.

---

## Architecture Decision Template (ADR)

For changes that affect cross-layer contracts, data models, deployment topology, or security boundaries, open a brief ADR in `docs/architecture/decisions/` before submitting the PR.

**File name convention:** `NNNN-short-title.md` (e.g., `0009-knowledge-graph-migration.md`)

**Template:**

```markdown
# NNNN. Title

- **Status:** proposed | accepted | deprecated
- **Date:** YYYY-MM-DD
- **Author:** @username

## Context

What problem are you solving? What constraints exist?

## Decision

What is the chosen approach?

## Consequences

- Positive: ...
- Negative: ...
- Risks: ...

## Alternatives Considered

- Alternative A: ... (rejected because ...)
- Alternative B: ... (rejected because ...)
```

**When to use an ADR:**

- Adding a new layer service or changing a layer boundary
- Modifying shared Pydantic models in `packages/shared-models/`
- Changing database schema or migration strategy
- Altering the contract test surface between layers
- Introducing a new external dependency or infrastructure component

**When an ADR is NOT needed:**

- Bug fixes that do not change architecture
- UI component additions
- Test-only changes
- Documentation updates

---

## PR Review Checklist

Every PR must meet this quality bar before merge. The CI runs `make production-readiness-gate` to enforce most of these automatically.

### Before Opening a PR

- [ ] `make verify` passes locally
- [ ] New code has tests (unit or integration) with meaningful assertions
- [ ] Type checks pass (`make typecheck`)
- [ ] Lint is clean (`make lint`)
- [ ] Contract tests pass (`make contract-tests`) if any layer API changed
- [ ] ADR is linked in the PR description if the change is architectural

### PR Description Requirements

- [ ] Clear title summarizing the change (imperative mood: "Add", "Fix", "Refactor")
- [ ] Description explains *what* changed and *why*
- [ ] Linked issue references (e.g., `Closes #123`)
- [ ] Screenshots or output logs included for UI or behavioral changes

### Review Expectations

- **Response time:** Maintainers aim to review within 2 business days
- **Change size:** Prefer PRs under 400 lines of diff. Larger changes should be split
- **Approval policy:** At least one approving review from a maintainer required

---

## Common Issues

### 1. `make verify` fails with "Database connection refused"

**Cause:** PostgreSQL, Neo4j, or Redis is not running.

**Fix:**

```bash
docker compose -f infra/compose/docker-compose.dev.yml up -d
make migrate
make verify
```

---

### 2. Type errors in CI that do not appear locally

**Cause:** CI uses the exact lockfile; local environment may have drifted.

**Fix:**

```bash
# Python
pip install -r requirements.txt --force-reinstall

# Node
cd apps/web && pnpm install --frozen-lockfile
```

---

### 3. Migration conflicts after pulling `main`

**Cause:** Two branches added migrations with the same revision sequence.

**Fix:**

```bash
# For Alembic (PostgreSQL)
alembic merge heads -m "merge_branch_a_and_b"
alembic upgrade head

# Re-generate if needed
alembic revision --autogenerate -m "describe_your_change"
```

---

### 4. Contract tests fail after changing a layer API

**Cause:** Layer-to-layer contracts are versioned and tested separately from unit tests.

**Fix:**

1. Update the contract schema in `packages/shared-models/contracts/`
2. Bump the contract version
3. Update the consumer layer to match the new contract
4. Run `make contract-tests` to ratify

See `docs/architecture/contracts.md` for the full contract governance process.

---

### 5. Frontend dev server shows a blank page or 502 error

**Cause:** The Vite dev server may not have started, or the backend proxy is misconfigured.

**Fix:**

```bash
cd apps/web
pnpm install --frozen-lockfile
pnpm dev
```

Verify the frontend is on port 5173 and the API proxy target in `vite.config.ts` matches your local backend ports.

---

## Mentorship & Onboarding

New contributors are not expected to navigate the six-layer architecture alone.

- **Onboarding buddy:** Every first-time contributor can request an onboarding buddy by commenting `@fabric4l/maintainers onboarding buddy` on their first issue or PR. A maintainer will be assigned to walk you through the codebase, review your first PR with extra context, and answer architecture questions.
- **Office hours:** Maintainers hold office hours every Thursday at 16:00 UTC in the `#dev-help` channel (see repo discussions for the invite link).
- **Good first issues:** Look for issues labeled [`good first issue`](https://github.com/bmsull560/Fabric_4L/labels/good%20first%20issue) — these are scoped, documented, and reviewed with extra care for new contributors.
