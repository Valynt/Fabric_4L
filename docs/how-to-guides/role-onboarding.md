---
title: "Role-Based Onboarding"
category: "how-to-guides"
audience: "all"
last-reviewed: "2026-05-27"
freshness: "current"
related: ["./setup-local-dev", "../AGENTS", "../../AGENTS"]
---

# Role-Based Onboarding (Frontend, Backend, Platform, Security)

Use this quick map when onboarding to Value Fabric. Each role includes:

- **Required commands** (run in order)
- **Expected artifacts** (files or outputs you should produce)

> All commands are run from repository root: `Fabric_4L/`.

---

## Shared bootstrap for every role

```bash
infisical login
corepack enable
corepack prepare pnpm@10.34.5 --activate
pnpm install --frozen-lockfile
make setup
pnpm env:dev
docker compose -f docker-compose.dev.yml --env-file .env.generated up -d
make migrate
```

### Expected artifacts

- `.env.generated` present with injected non-secret dev values.
- Docker services healthy (`postgres`, `redis`, `neo4j`, `keycloak`).
- Database migrations applied without errors.

---

## Frontend role

### Required commands

```bash
pnpm --dir apps/web run lint
pnpm --dir apps/web run typecheck
pnpm --dir apps/web run test
pnpm --dir apps/web run build
```

### Expected artifacts

- Clean lint/typecheck/test output.
- Production bundle in `apps/web/dist/`.
- If UI behavior changed: updated tests under `apps/web` and any required contract type updates.

---

## Backend role

### Required commands

```bash
make lint
make typecheck
make test
make contract-tests
```

For a single layer, run the scoped variant first (example Layer 4):

```bash
make test-layer4
make typecheck-layer4
```

### Expected artifacts

- Passing backend tests and contract tests.
- If API shape changed: updated OpenAPI/contract artifacts and matching tests.
- If persistence changed: corresponding Alembic migration files.

---

## Platform role (cross-layer / CI / release)

### Required commands

```bash
make check-conflict-markers
make check-pytest-skip-governance
pnpm run check:contract-compliance
pnpm run check:api-types
make verify
```

### Expected artifacts

- No unresolved merge markers.
- Governance checks pass.
- Contract/API type drift checks pass.
- Full verification gate passes (`make verify`).

---

## Security role

### Required commands

```bash
pytest -m "security"
pytest -m "tenant_boundary"
pnpm --dir apps/web run test:prod-auth-bypass
```

Optional full-stack hardening pass (requires live stack):

```bash
make test-backend-integrated-validation
```

### Expected artifacts

- Passing OWASP and tenant-isolation tests.
- Frontend production auth-bypass guard test passes.
- If findings exist: documented remediation notes and regression tests.

---

## Troubleshooting: secret/bootstrap failures

### 1) `infisical login` or `pnpm env:dev` fails

**Symptoms**
- Authentication error from Infisical CLI.
- `.env.generated` is missing or empty.

**Fix**

```bash
infisical login
pnpm env:dev
```

Then confirm artifact:

```bash
test -s .env.generated && echo ".env.generated OK"
```

### 2) Docker compose fails after env generation

**Symptoms**
- `docker compose ... up -d` exits early.
- Services restart/crash immediately.

**Fix**

```bash
docker compose -f docker-compose.dev.yml --env-file .env.generated config >/tmp/compose.rendered.yaml
cat /tmp/compose.rendered.yaml >/dev/null
```

If render succeeds, inspect service logs:

```bash
docker compose -f docker-compose.dev.yml --env-file .env.generated logs --tail=100
```

### 3) Migration fails during bootstrap

**Symptoms**
- `make migrate` fails with connection/auth errors.

**Fix**

```bash
docker compose -f docker-compose.dev.yml --env-file .env.generated ps
make migrate
```

If dependencies are unhealthy, restart stack:

```bash
docker compose -f docker-compose.dev.yml --env-file .env.generated down
docker compose -f docker-compose.dev.yml --env-file .env.generated up -d
```

### 4) Fast failure checklist

Run this minimal sequence before escalating:

```bash
test -s .env.generated
pnpm --version
docker compose -f docker-compose.dev.yml --env-file .env.generated ps
make migrate
make verify
```

If one step fails, attach:

- failing command
- exact stderr snippet
- `docker compose ... ps` output
- whether `.env.generated` exists and is non-empty
